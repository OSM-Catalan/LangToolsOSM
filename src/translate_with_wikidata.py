import click
import csv
import re
import pytablewriter
from colorama import Fore, Style
from tqdm import tqdm

import lib.osm_utils as lt
import lib.wikimedia as wikimedia
from lib import __version__


def write_db(db, file, file_format='csv', table_name=None):
    headers = ['wikidata', 'nameOSM', 'answer', 'committed', 'translations', 'objects']
    try:
        with open(file, 'w', newline='') as f:
            if file_format in 'csv':
                writer = csv.writer(f, dialect='unix', delimiter='\t')
                if table_name:
                    writer.writerow([table_name])
                writer.writerow(headers)
                for wikidata, values in db.items():
                    row = db_item_row(wikidata, values)
                    writer.writerow(row)
            elif file_format in 'mediawiki':
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
            else:
                raise ValueError('File format must be "csv" or "mediawiki".')
    except IOError:
        print('I/O error')


def db_item_row(db_key, db_item) -> list:
    translation_list = wikimedia.list_translations(db_item['translations'])
    translations_str = ', '.join(translation_list)
    objects = [x['type'] + '|' + str(x['id']) for x in iter(db_item['objects'])]
    objects = ', '.join(objects)
    names = list(dict.fromkeys([x['name'] for x in iter(db_item['objects'])]))  # dict keys -> unique in the same order
    names = ', '.join(names)
    row = [db_key, names, db_item['answer']['value'], str(db_item['answer']['committed']), translations_str, objects]
    return row


@click.command()
@click.option('--area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou"). Ignored if query is present.')
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--changeset-comment', type=str, help='Comment for the changeset.')
@click.option('--changeset-hashtags', type=str, help='#hashtags for the changeset. Semicolon delimited (e.g. "#toponimsCat;#Calle-Carrer").')
@click.option('--changeset-source', default='wikidata', type=str, help='Source tag value for the changeset.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name'][~'name:[a-z]+'~'.']['wikidata'][!'name:{lang}']". Ignored if query is present.""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--name-as-option', default=False, is_flag=True, help='Offer "name" value as an option to fill "name:lang". Useful for areas where "name" is in the language you want to fill "name:lang". See also fill_empty_name_lang program.')
@click.option('--output', type=click.Path(dir_okay=False, writable=True), help='Path of the file to write the db of wikidata translations and user answers.')
@click.option('--output-format', type=click.Choice(['csv', 'mediawiki'], case_sensitive=False), default='csv', help='Format of the output file.')
@click.option('--passwordfile', default=None, type=str, help='Path to a passwordfile, where on the first line username and password must be colon-separated (:). If provided, username option is ignored.')
@click.option('--query', type=str, help="""Overpass query to search for objects.""")
@click.option('--remember-answers', default=False, is_flag=True, help='Remember the answers for objects with the same wikidata value. Still asks for confirmation.')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def translate_with_wikidatacommand(area, batch, changeset_comment, changeset_hashtags, changeset_source, dry_run, remember_answers, filters, lang, name_as_option, output, output_format, passwordfile, query, username, verbose):
    """Add «name:LANG» selecting the label or alias from «wikidata»."""
    if not dry_run:
        api = lt.login_osm(username=username, passwordfile=passwordfile)
    if not filters:
        filters = f"nwr['name'][~'name:[a-z]+'~'.']['wikidata'][!'name:{lang}']"
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Fill empty name:{lang} tags translations from wikidata in {area} for {filters}',
                      u'source': changeset_source, u'created_by': f'LangToolsOSM {__version__}'}
    if changeset_comment:
        changeset_tags.update({'comment': changeset_comment})
    if changeset_hashtags:
        changeset_tags.update({'hashtags': changeset_hashtags})
    print(changeset_tags)

    if not area and not query:
        print('Missing overpass "area" or "query" option. See "write_osm_objects_report --help" for details.')
        exit()
    result = lt.get_overpass_result(area=area, filters=filters, query=query)
    n_objects = len(result.nodes) + len(result.ways) + len(result.relations)
    print('######################################################')
    print(f'{str(n_objects)} objects found ({str(len(result.nodes))} nodes, {str(len(result.ways))}'
          f' ways and {str(len(result.relations))} relations).')
    print('######################################################')

    wikidata_ids = []
    for osm_object in result.nodes + result.ways + result.relations:
        if osm_object.tags['wikidata']:
            wikidata_ids.append(osm_object.tags['wikidata'])
    wikidata_unique_ids = list(dict.fromkeys(wikidata_ids))  # dict keys -> unique in the same order
    db = wikimedia.get_translations(ids=wikidata_unique_ids, lang=lang)
    n_translations = 0
    n_objects_with_translations = 0
    for key in db.keys():
        db[key].update({'objects': [], 'answer': {'value': None, 'committed': False}})
        if db[key]['translations']:
            n_translations = n_translations + 1
            n_objects_with_translations = n_objects_with_translations + wikidata_ids.count(key)
    if n_objects_with_translations > 0:
        percent_objects_with_translations = round(n_objects_with_translations / n_objects * 100)
    else:
        percent_objects_with_translations = 0
        print(f'{n_translations} translations available from wikidata. Nothing to work on here.')
        print('######################################################')
        exit()
    print(f'{n_translations} translations available from wikidata for {n_objects_with_translations}'
          f' OSM objects ({percent_objects_with_translations}%).')
    print('######################################################')
    if n_objects_with_translations > 200 and ((batch is not None and batch > 200) or batch is None:
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
                         'Reduce the area, add batch option < 200 or stop translating when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    start = input('Start translating [Y/n]: ').lower()
    if start not in ['y', 'yes', '']:
        exit()

    changeset = None
    n_changeset = 0
    n_edits = 0
    total_edits = 0
    try:
        for osm_object in tqdm(result.nodes + result.ways + result.relations):
            if not dry_run:
                lt.print_changeset_status(changeset=changeset, n_edits=n_edits, n_changeset=n_changeset, verbose=verbose)
            lt.print_osm_object(osm_object, verbose=verbose)
            if 'wikidata' in osm_object.tags.keys() and osm_object.tags['wikidata'] in db.keys():
                translations = {'id': osm_object.tags['wikidata'],
                                'translations': db[osm_object.tags['wikidata']]['translations']}
                tags = {}
                if output:
                    db[translations['id']]['objects'].append({'name': osm_object.tags['name'],
                                                              'type': osm_object._type_value,
                                                              'id': osm_object.id, 'modified': False})
            else:
                print('wikidata id: ' + osm_object.tags['wikidata'])
                # import json
                # print(json.dumps(db['osm_object.tags['wikidata']'], indent=4))
                raise Exception('Something wrong while fetching the translations from wikidata.')

            if verbose > 2:
                print(Fore.LIGHTBLACK_EX + 'translations: ' + ', '.join(wikimedia.list_translations(translations['translations'])) + Style.RESET_ALL)

            if remember_answers and db[translations['id']]['answer']['committed']:
                print(Fore.BLUE + 'Remembering your answer...' + Style.RESET_ALL)
                tags['name:' + lang] = db[translations['id']]['answer']['value']
            else:
                select_translation = '-'
                if translations['translations']:
                    if (
                            remember_answers and db[translations['id']]['answer']['committed'] is None and
                            db[translations['id']]['answer']['value'] == '-'
                    ):
                        print(Fore.BLUE + 'Remembering your answer... SKIP.' + Style.RESET_ALL)
                        continue

                    translation_options = []
                    i = 0
                    if translations['translations']['wikipedia'] and translations['translations']['wikipedia']['title']:
                        print(Style.BRIGHT + Fore.CYAN + str(i) + ' = ' + translations['translations']['wikipedia']['title'] + Style.RESET_ALL)
                        translation_options.append(translations['translations']['wikipedia']['title'])
                        i = i + 1

                    if name_as_option and osm_object.tags['name']:
                        print(Fore.YELLOW + str(i) + ' = ' + osm_object.tags['name'] + Style.RESET_ALL)
                        translation_options.append(osm_object.tags['name'])
                        i = i + 1

                    if translations['translations']['extra']:
                        for alias in translations['translations']['extra']:
                            print(str(i) + ' = ' + alias['value'])
                            translation_options.append(alias['value'])
                            i = i + 1

                    if translations['translations']['label'] and translations['translations']['label']['value']:
                        print(Style.BRIGHT + str(i) + ' = ' + translations['translations']['label']['value'] + Style.RESET_ALL)
                        translation_options.append(translations['translations']['label']['value'])
                        i = i + 1

                    if translations['translations']['aliases']:
                        for alias in translations['translations']['aliases']:
                            print(str(i) + ' = ' + alias['value'])
                            translation_options.append(alias['value'])
                            i = i + 1

                    if verbose > 2:
                        print(Fore.LIGHTBLACK_EX + 'translation_options: ' + str(translation_options) + Style.RESET_ALL)

                    if translation_options:
                        select_translation = input('Select translation ("-" to skip, "e" to edit): ') or '0'
                        while select_translation not in [str(x) for x in range(len(translation_options))] + ['-'] + ['e']:
                            print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                            select_translation = input('Select translation ("-" to skip, "e" to edit): ') or '0'

                if select_translation in '-':
                    db[translations['id']]['answer']['value'] = '-'
                    db[translations['id']]['answer']['committed'] = None
                    if translations['translations']:
                        print(Fore.BLUE + 'SKIP.' + Style.RESET_ALL)
                    else:
                        print(Fore.BLUE + 'SKIP: No translations from wikidata.' + Style.RESET_ALL)
                    continue
                elif select_translation in 'e':
                    tags['name:' + lang] = input(f'Enter a value for tag "name:{lang}": ')
                else:
                    select_translation = int(select_translation)
                    tags['name:' + lang] = translation_options[select_translation]
                db[translations['id']]['answer']['value'] = tags['name:' + lang]

            if not dry_run:
                if changeset is None:
                    n_changeset = n_changeset + 1
                    if batch and n_objects > batch and changeset_comment:  # TODO predict if more than 1 changeset will be used
                        changeset_tags.update({'comment': changeset_comment + f' (part {n_changeset})'})
                    changeset = api.ChangesetCreate(changeset_tags)
                committed = lt.update_osm_object(osm_object=osm_object, tags=tags, api=api)
                if committed:
                    n_edits = n_edits + 1
                    db[translations['id']]['answer']['committed'] = True
                    object_db = db[translations['id']]['objects'].pop()
                    object_db['modified'] = True
                    db[translations['id']]['objects'].append(object_db)
                if batch and n_edits >= batch:
                    print(f'{n_edits} edits DONE! https://www.osm.org/changeset/{changeset}. Opening a new changeset.')
                    total_edits = total_edits + n_edits
                    api.ChangesetClose()
                    changeset = None
                    n_edits = 0
            else:
                print(Fore.GREEN + Style.BRIGHT + '\n+ ' + str(tags) + Style.RESET_ALL)

    finally:
        print('######################################################')
        if changeset and not dry_run:
            total_edits = total_edits + n_edits
            print(f'DONE! {total_edits} objects modified from {n_objects_with_translations}'
                  f' objects with available translations ({round(total_edits / n_objects_with_translations * 100)}%)'
                  f' https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')

        if output:
            table_name = f'# Generated by translate_with_wikidata from LangToolsOSM {__version__} with parameters: lang={lang}, area={area}, ' \
                         f'filters={filters}, remember_answers={remember_answers}'
            write_db(db, file=output, file_format=output_format, table_name=table_name)
