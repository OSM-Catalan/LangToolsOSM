import click
from colorama import Fore, Style
import lib.LangToolsOSM as lt
from lib import __version__
import requests
from tqdm import tqdm


def get_translations(ident, lang) -> dict:
    response = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{ident}.json")
    data = response.json()
    ret = {}
    wikidata_id = list(data["entities"].keys())[0]

    if lang in data["entities"][wikidata_id]["labels"].keys():
        ret["label"] = data["entities"][wikidata_id]["labels"][lang]

    if lang in data["entities"][wikidata_id]["aliases"].keys():
        ret["aliases"] = data["entities"][wikidata_id]["aliases"][lang]

    return {
        "id": wikidata_id,
        "translations": ret}


@click.command()
@click.option('--area', prompt='Bounding box (South,West,North,East), overpass filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--cache-answers', default=False, is_flag=True, help='Remember the answers for objects with the same wikidata value.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name'][~'name:[a-z]+'~'.']['wikidata'][!'name:{lang}']""""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', default=False, is_flag=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def translate_with_wikidatacommand(area, dry_run, cache_answers, filters, lang, username, verbose):
    """Add «name:LANG» selecting the label or alias from «wikidata»."""
    if not dry_run:
        api = lt.login_OSM(username=username)
    changeset_tags = {u"comment": f"Fill empty name:{lang} tags translations from wikidata in {area} for {filters}",
                      u"source": u"wikidata", u"created_by": f"LangToolsOSM {__version__}"}
    if verbose:
        print(changeset_tags)

    if not filters:
        filters = f"nwr['name'][~'name:[a-z]+'~'.']['wikidata'][!'name:{lang}']"
    result = lt.get_overpass_result(area=area, filters=filters)
    changeset = None
    db = dict()
    n_edits = 0
    for rn in tqdm(result.nodes):
        if rn.tags['wikidata'] in db.keys():
            translations = {'id': rn.tags['wikidata'], 'translations': db[rn.tags['wikidata']]['translations']}
        else:
            translations = get_translations(rn.tags['wikidata'], lang)
            db.update({translations['id']: {'translations': translations['translations'],
                                            'answer': {'value': None, 'committed': False}}})

        if translations['translations']:
            tags = {}
            if cache_answers and db[translations['id']]['answer']['committed']:
                tags["name:" + lang] = db[translations['id']]['answer']['value']
            else:
                if cache_answers and db[translations['id']]['answer']['committed'] is None and db[translations['id']]['answer']['value'] == '-':
                    continue
                if not dry_run:
                    print(f'Number of editions in the current changeset: {n_edits}')
                lt.print_element(rn, verbose=verbose)
                print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
                translation_options = [translations['translations']['label']['value']]
                if 'aliases' in translations['translations'].keys():
                    i = 1
                    for alias in translations['translations']['aliases']:
                        print(str(i) + ' = ' + alias['value'])
                        translation_options.append(alias['value'])
                        i = i + 1

                select_translation = input("Select translation ('-' to skip): ") or '0'
                while select_translation not in [str(x) for x in range(len(translation_options))] + ['-']:
                    print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                    select_translation = input("Select translation ('-' to skip): ") or '0'

                if select_translation in '-':
                    db[translations['id']]['answer']['value'] = '-'
                    db[translations['id']]['answer']['committed'] = None
                    continue
                else:
                    select_translation = int(select_translation)
                    tags["name:" + lang] = translation_options[select_translation]
                    db[translations['id']]['answer']['value'] = translation_options[select_translation]

            if changeset is None and not dry_run:
                changeset_id = api.ChangesetCreate(changeset_tags)
                changeset = True

            if not dry_run:
                committed = lt.update_element(element=rn, tags=tags, api=api)
                if committed:
                    n_edits = n_edits + 1
                    db[translations['id']]['answer']['committed'] = True

    for rw in tqdm(result.ways):
        if rw.tags['wikidata'] in db.keys():
            translations = {'id': rw.tags['wikidata'], 'translations': db[rw.tags['wikidata']]['translations']}
        else:
            translations = get_translations(rw.tags['wikidata'], lang)
            db.update({translations['id']: {'translations': translations['translations'],
                                            'answer': {'value': None, 'committed': False}}})

        if translations['translations']:
            tags = {}
            if cache_answers and db[translations['id']]['answer']['committed']:
                tags["name:" + lang] = db[translations['id']]['answer']['value']
            else:
                if cache_answers and db[translations['id']]['answer']['committed'] is None and db[translations['id']]['answer']['value'] == '-':
                    continue
                if not dry_run:
                    print(f'Number of editions in the current changeset: {n_edits}')
                lt.print_element(rw, verbose=verbose)
                print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
                translation_options = [translations['translations']['label']['value']]
                if 'aliases' in translations['translations'].keys():
                    i = 1
                    for alias in translations['translations']['aliases']:
                        print(str(i) + ' = ' + alias['value'])
                        translation_options.append(alias['value'])
                        i = i + 1

                select_translation = input("Select translation ('-' to skip): ") or '0'
                while select_translation not in [str(x) for x in range(len(translation_options))] + ['-']:
                    print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                    select_translation = input("Select translation ('-' to skip): ") or '0'

                if select_translation in '-':
                    db[translations['id']]['answer']['value'] = '-'
                    db[translations['id']]['answer']['committed'] = None
                    continue
                else:
                    select_translation = int(select_translation)
                    tags["name:" + lang] = translation_options[select_translation]
                    db[translations['id']]['answer']['value'] = translation_options[select_translation]

            if changeset is None and not dry_run:
                changeset_id = api.ChangesetCreate(changeset_tags)
                changeset = True

            if not dry_run:
                committed = lt.update_element(element=rw, tags=tags, api=api)
                if committed:
                    n_edits = n_edits + 1
                    db[translations['id']]['answer']['committed'] = True

    for rr in tqdm(result.relations):
        if rr.tags['wikidata'] in db.keys():
            translations = {'id': rr.tags['wikidata'], 'translations': db[rr.tags['wikidata']]['translations']}
        else:
            translations = get_translations(rr.tags['wikidata'], lang)
            db.update({translations['id']: {'translations': translations['translations'],
                                            'answer': {'value': None, 'committed': False}}})

        if translations['translations']:
            tags = {}
            if cache_answers and db[translations['id']]['answer']['committed']:
                tags["name:" + lang] = db[translations['id']]['answer']['value']
            else:
                if cache_answers and db[translations['id']]['answer']['committed'] is None and db[translations['id']]['answer']['value'] == '-':
                    continue
                if not dry_run:
                    print(f'Number of editions in the current changeset: {n_edits}')
                lt.print_element(rr, verbose=verbose)
                print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
                translation_options = [translations['translations']['label']['value']]
                if 'aliases' in translations['translations'].keys():
                    i = 1
                    for alias in translations['translations']['aliases']:
                        print(str(i) + ' = ' + alias['value'])
                        translation_options.append(alias['value'])
                        i = i + 1

                select_translation = input("Select translation ('-' to skip): ") or '0'
                while select_translation not in [str(x) for x in range(len(translation_options))] + ['-']:
                    print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                    select_translation = input("Select translation ('-' to skip): ") or '0'

                if select_translation in '-':
                    db[translations['id']]['answer']['value'] = '-'
                    db[translations['id']]['answer']['committed'] = None
                    continue
                else:
                    select_translation = int(select_translation)
                    tags["name:" + lang] = translation_options[select_translation]
                    db[translations['id']]['answer']['value'] = translation_options[select_translation]

            if changeset is None and not dry_run:
                changeset_id = api.ChangesetCreate(changeset_tags)
                changeset = True

            if not dry_run:
                committed = lt.update_element(element=rr, tags=tags, api=api)
                if committed:
                    n_edits = n_edits + 1
                    db[translations['id']]['answer']['committed'] = True

    if changeset and not dry_run:
        print(f'DONE! {n_edits} objects modified https://www.osm.org/changeset/{changeset_id}')
        api.ChangesetClose()
    else:
        print('DONE! No change to OSM (--dry-run mode)')
