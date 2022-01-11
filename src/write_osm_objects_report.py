import click
import csv
from colorama import Fore, Style
import lib.osm_utils as lt
import lib.wikimedia as wt
import pytablewriter
from tqdm import tqdm
from lib import __version__

@click.command()
@click.argument('extra-tags', nargs=-1)
@click.option('--area', prompt='Bounding box (South,West,North,East), overpass filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name']['name:{lang}']".""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--output', type=click.Path(dir_okay=False, writable=True), help='Path of the file to write the db of wikidata translations and user answers.')
@click.option('--output-format', type=click.Choice(['csv', 'mediawiki'], case_sensitive=False), default='csv', help='Format of the output file.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
@click.option('--wikimedia-urls', default=False, is_flag=True, help='Write wikimedia URLs instead of the plain wikidata Id or wikipedia page title.')
def write_osm_objects_reportcommand(area, extra_tags, filters, lang, output, output_format, verbose, wikimedia_urls):
    """Generates a file with names, OSM Id, wikidata translations and EXTRA_TAGS in columns. EXTRA_TAGS Should include
     at least the tags you will want to edit. You can edit and upload the changed tags with upload_osm_objects_from_report"""
    if verbose > 1:
        print(extra_tags)
    if not filters:
        filters = f"nwr['name']['name:{lang}']"
    result = lt.get_overpass_result(area=area, filters=filters)
    print('######################################################')
    print(str(len(result.nodes)) + ' nodes, ' + str(len(result.ways)) + ' ways and ' + str(len(result.relations)) + ' relations found.')
    print('######################################################')

    wikidata_ids = []
    for osm_object in result.nodes + result.ways + result.relations:
        if 'wikidata' in osm_object.tags.keys():
            wikidata_ids.append(osm_object.tags['wikidata'])
    wikidata_ids = list(dict.fromkeys(wikidata_ids))  # dict keys -> unique in the same order
    db_wikidata_translations = wt.get_translations(ids=wikidata_ids, lang=lang)

    db_osm = []
    if output_format == 'csv':
        header = ['typeOSM', 'idOSM', 'name', 'name:' + lang]
    elif output_format == 'mediawiki':
        header = ['OSMobject', 'typeOSM', 'idOSM', 'name', 'name:' + lang]
    else:
        raise ValueError('File format must be "csv" or "mediawiki".')

    if extra_tags is not None:
        header = header + list(extra_tags)
    header = header + ['translations', f'{lang}.wikipedia_page', 'wikidata_id', 'multilang_names', 'all_tags']
    duplicated_fields = list(set([x for x in header if header.count(x) > 1]))
    extra_tags_ori = extra_tags
    for rm_tag in duplicated_fields and extra_tags is not None:
        extra_tags = list(extra_tags)
        extra_tags.remove(rm_tag)

    header = list(dict.fromkeys(header))

    if verbose > 0:
        print('HEADER: ', str(header))
    for osm_object in tqdm(result.nodes + result.ways + result.relations):
        wikidata_id = ''
        wikipedia_page = ''
        translations = ''
        if 'wikidata' in osm_object.tags.keys() and osm_object.tags['wikidata'] in db_wikidata_translations.keys():
            wikidata_id = osm_object.tags['wikidata']
            translations = db_wikidata_translations[osm_object.tags['wikidata']]
            if translations['translations']:
                if translations['translations']['wikipedia']:
                    wikipedia_page = translations['translations']['wikipedia']['title']
                translations['translations']['extra'] = None
                translations = wt.list_translations(translations['translations'])
                translations = list(dict.fromkeys(translations))  # unique keeping order
                translations = ', '.join(translations)
            else:
                translations = ''
        name = ''
        if 'name' in osm_object.tags.keys():
            name = osm_object.tags['name']
        name_lang = ''
        if 'name:' + lang in osm_object.tags.keys():
            name_lang = osm_object.tags['name:' + lang]
        names_tags = []
        for key, value in osm_object.tags.items():
            if key.startswith('name:') or key in ['int_name', 'loc_name', 'short_name', 'official_name']:
                names_tags.append(key + '=' + value)
        names_tags = ', '.join(names_tags)
        extra_tags_values = dict()
        if extra_tags:
            for key in extra_tags:
                tag_value = ''
                if key in osm_object.tags.keys():
                    tag_value = osm_object.tags[key]
                extra_tags_values.update({key: tag_value})

        if output_format == 'csv':
            if wikimedia_urls:
                if wikidata_id != '':
                    wikidata_id = 'https://www.wikidata.org/wiki/' + wikidata_id
                if wikipedia_page != '':
                    wikipedia_page = f'https://{lang}.wikipedia.com/wiki/{wikipedia_page}'
            object_data = [osm_object._type_value, osm_object.id, name, name_lang] + \
                          list(extra_tags_values.values()) + \
                          [translations, wikipedia_page, wikidata_id, names_tags, str(osm_object.tags)]
        elif output_format == 'mediawiki':
            if wikidata_id != '':
                wikidata_id = f'[https://www.wikidata.org/wiki/{wikidata_id} {wikidata_id}]'
            if wikipedia_page != '':
                wikipedia_page = f'[https://{lang}.wikipedia.com/wiki/{wikipedia_page} {wikipedia_page}]'
            osm_object_str = '{{' + osm_object._type_value + '|' + str(osm_object.id) + '}}'
            object_data = [osm_object_str, osm_object._type_value, osm_object.id, osm_object.tags['name'], name_lang] + \
                          list(extra_tags_values.values()) + \
                          [translations, wikipedia_page, wikidata_id, names_tags, str(osm_object.tags)]
        else:
            raise ValueError('File format must be "csv" or "mediawiki".')
        if verbose > 1:
            print(object_data)

        db_osm.append(object_data)

    table_name = f'Generated by write_osm_objects_report from LangToolsOSM {__version__} with parameters: lang={lang}, area={area}, ' \
                 f'filters={filters}, extra_tag={extra_tags_ori}'
    try:
        with open(output, mode='w', newline='') as f:
            if output_format in 'csv':
                writer = csv.writer(f, dialect='unix', delimiter='\t')
                if table_name:
                    writer.writerow(['# ' + table_name] + [''] * (len(header) - 1))
                writer.writerow(header)
                for row in db_osm:
                    writer.writerow(row)
            elif output_format in 'mediawiki':
                writer = pytablewriter.MediaWikiTableWriter()
                writer.stream = f
                writer.headers = header
                writer.table_name = table_name
                matrix = []
                for row in db_osm:
                    matrix.append(row)
                writer.value_matrix = matrix
                writer.write_table()
            else:
                raise ValueError('File format must be "csv" or "mediawiki".')
    except IOError:
        print('I/O error')
