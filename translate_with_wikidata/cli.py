import click
import csv
from colorama import Fore, Style
import lib.LangToolsOSM as lt
from lib import __version__
import pytablewriter
import re
import requests
from tqdm import tqdm


def get_translations(ident, lang) -> dict:
    response = requests.get(f'https://www.wikidata.org/wiki/Special:EntityData/{ident}.json')
    data = response.json()
    ret = {}
    wikidata_id = list(data['entities'].keys())[0]
    ret['label'] = None
    ret['aliases'] = None
    if lang in data['entities'][wikidata_id]['labels'].keys():
        ret['label'] = data['entities'][wikidata_id]['labels'][lang]
    if lang in data['entities'][wikidata_id]['aliases'].keys():
        ret['aliases'] = data['entities'][wikidata_id]['aliases'][lang]

    if not ret['label'] and not ret['aliases']:
        ret = None
    else:  # Generate new translation options
        extra_translations = list_translations(ret)
        # Remove brackets and the text inside
        pattern = re.compile(r'\s*\(.+\)\s*')
        for i in extra_translations:
            if pattern.search(i):
                if not ret['aliases']:
                    ret['aliases'] = []
                ret['aliases'].append({'lang': lang, 'value': pattern.sub('', i)})

        extra_translations = list_translations(ret)
        # Capitalize all words
        for i in extra_translations:
            if not i.title() == i:
                if not ret['aliases']:
                    ret['aliases'] = []
                ret['aliases'].append({'lang': lang, 'value': i.title()})

    return {
        'id': wikidata_id,
        'translations': ret}


def list_translations(translations):
    if translations and translations['label']:
        translations_list = [translations['label']['value']]
    else:
        translations_list = []
    if translations and translations['aliases']:
        translations_list = translations_list + [x['value'] for x in translations['aliases']]
    return translations_list


def write_db(db, file, format='csv', table_name=None):
    headers = ['wikidata', 'nameOSM', 'answer', 'committed', 'translations', 'objects']
    try:
        with open(file, 'w', newline='') as f:
            if format in 'csv':
                writer = csv.writer(f, dialect='unix', delimiter='\t')
                if table_name:
                    writer.writerow(table_name)
                writer.writerow(headers)
                for wikidata, values in db.items():
                    row = db_item_row(wikidata, values)
                    writer.writerow(row)
            elif format in 'mediawiki':
                writer = pytablewriter.MediaWikiTableWriter()
                writer.stream = f
                writer.headers = headers
                writer.table_name = table_name
                matrix = []
                pattern = re.compile(r'((node|way|relation)\|[0-9]+),*')
                for wikidata, values in db.items():
                    row = db_item_row(wikidata, values)
                    row[0] = f'[https://www.wikidata.org/wiki/{row[0]} {row[0]}]'
                    row[5] = pattern.sub(repl=r'{{\1}}', string=row[5])
                    matrix.append(row)
                writer.value_matrix = matrix
                writer.write_table()
    except IOError:
        print("I/O error")


def db_item_row(db_key, db_item):
    translation_list = list_translations(db_item['translations'])
    translations_str = ', '.join(translation_list)
    objects = [x['type'] + '|' + str(x['id']) for x in iter(db_item['objects'])]
    objects = ', '.join(objects)
    names = list(dict.fromkeys([x['name'] for x in iter(db_item['objects'])]))  # dict keys -> unique in the same order
    names = ', '.join(names)
    row = [db_key, names, db_item['answer']['value'], str(db_item['answer']['committed']), translations_str, objects]
    return row


@click.command()
@click.option('--area', prompt='Bounding box (South,West,North,East), overpass filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--cache-answers', default=False, is_flag=True, help='Remember the answers for objects with the same wikidata value.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name'][~'name:[a-z]+'~'.']['wikidata'][!'name:{lang}']".""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--output', type=click.Path(dir_okay=False, writable=True), help='Path of the file to write db of wikidata translations and user answers.')
@click.option('--output-format', type=click.Choice(['csv', 'mediawiki'], case_sensitive=False), default='csv', help='Format of the output file.')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def translate_with_wikidatacommand(area, dry_run, cache_answers, filters, lang, output, output_format, username, verbose):
    """Add «name:LANG» selecting the label or alias from «wikidata»."""
    if not dry_run:
        api = lt.login_OSM(username=username)
    if not filters:
        filters = f"nwr['name'][~'name:[a-z]+'~'.']['wikidata'][!'name:{lang}']"
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u"comment": f"Fill empty name:{lang} tags translations from wikidata in {area} for {filters}",
                      u"source": u"wikidata", u"created_by": f"LangToolsOSM {__version__}"}
    print(changeset_tags)
    result = lt.get_overpass_result(area=area, filters=filters)
    print('######################################################')
    print(str(len(result.nodes)) + ' nodes ' + str(len(result.ways)) + 'ways; ' + str(len(result.relations)) + ' relations found.')
    print('######################################################')

    changeset = None
    db = dict()
    n_edits = 0
    try:
        for osm_object in tqdm(result.nodes + result.ways + result.relations):
            if osm_object.tags['wikidata'] in db.keys():
                translations = {'id': osm_object.tags['wikidata'], 'translations': db[osm_object.tags['wikidata']]['translations']}
                if output:
                    db[translations['id']]['objects'].append({'name': osm_object.tags['name'], 'type': osm_object._type_value,
                                                              'id': osm_object.id, 'modified': False})
            else:
                translations = get_translations(osm_object.tags['wikidata'], lang)
                db.update({translations['id']: {'translations': translations['translations'],
                                                'answer': {'value': None, 'committed': False},
                                                'objects': []}})
                if output:
                    db[translations['id']]['objects'].append({'name': osm_object.tags['name'], 'type': osm_object._type_value,
                                                              'id': osm_object.id, 'modified': False})
            if verbose > 2:
                print(translations['translations'])
            if not dry_run:
                lt.print_changeset_status(changeset=changeset, n_edits=n_edits, verbose=verbose)

            tags = {}

            if cache_answers and db[translations['id']]['answer']['committed']:
                print(Fore.BLUE + 'Remembering your response...' + Style.RESET_ALL)
                tags["name:" + lang] = db[translations['id']]['answer']['value']
            else:
                if (
                        cache_answers and db[translations['id']]['answer']['committed'] is None and
                        db[translations['id']]['answer']['value'] == '-'
                ):
                    print(Fore.BLUE + 'Remembering your response... SKIP.' + Style.RESET_ALL)
                    continue

                if translations['translations']:
                    if translations['translations'] and translations['translations']['label']['value']:
                        print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
                        translation_options = [translations['translations']['label']['value']]
                    else:
                        translation_options = []

                    if translations['translations']['aliases']:
                        i = 1
                        for alias in translations['translations']['aliases']:
                            print(str(i) + ' = ' + alias['value'])
                            translation_options.append(alias['value'])
                            i = i + 1

                    if verbose > 2:
                        print('translation_options: ' + str(translation_options))

                    if translation_options:
                        select_translation = input("Select translation ('-' to skip, 'e' to edit): ") or '0'
                        while select_translation not in [str(x) for x in range(len(translation_options))] + ['-'] + ["e"]:
                            print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                            select_translation = input("Select translation ('-' to skip): ") or '0'

                else:
                    select_translation = '-'

                if select_translation in '-':
                    db[translations['id']]['answer']['value'] = '-'
                    db[translations['id']]['answer']['committed'] = None
                    if translations['translations']:
                        print(Fore.BLUE + 'SKIP.' + Style.RESET_ALL)
                    else:
                        print(Fore.BLUE + 'SKIP: No translations from wikidata.' + Style.RESET_ALL)
                    continue
                elif select_translation in 'e':
                    tags["name:" + lang] = input(f'Enter a value for tag "name:{lang}": ')
                else:
                    select_translation = int(select_translation)
                    tags["name:" + lang] = translation_options[select_translation]
                db[translations['id']]['answer']['value'] = tags["name:" + lang]

            if changeset is None and not dry_run:
                changeset = api.ChangesetCreate(changeset_tags)

            if not dry_run:
                committed = lt.update_element(element=osm_object, tags=tags, api=api)
                if committed:
                    n_edits = n_edits + 1
                    db[translations['id']]['answer']['committed'] = True
                    object_db = db[translations['id']]['objects'].pop()
                    object_db['modified'] = True
                    db[translations['id']]['objects'].append(object_db)

    finally:
        if changeset and not dry_run:
            print(f'DONE! {n_edits} objects modified https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')

        if output:
            table_name = f'Generated by LangToolsOSM {__version__} with parameters: lang={lang}, area={area}, ' \
                         f'filters={filters}, cache_answers={cache_answers}'
            write_db(db, file=output, format=output_format, table_name=table_name)
