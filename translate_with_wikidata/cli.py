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
@click.option('--area', prompt='Bounding box (South,West,North,East) or the exact name value of an area', type=str, help='Eg. "42.49,2.43,42.52,2.49" or "Le Canigou".')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', default=False, is_flag=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def translate_with_wikidatacommand(area, dry_run, lang, username, verbose):
    """Add «name:LANG» selecting the label or alias from «wikidata»."""
    if not dry_run:
        api = lt.login_OSM(username=username)
    changeset_tags = {u"comment": f"Fill empty name:{lang} tags translations from wikidata",
                      u"source": u"wikidata", u"created_by=": f"LangToolsOSM {__version__}"}
    if verbose:
        print(changeset_tags)

    result = lt.get_overpass_result(area=area, filters=f'nwr["name"]["wikidata"][!"name:{lang}"]')
    # TODO: [~"name:[a-z]+"~"."] as default?
    changeset = None
    for rn in tqdm(result.nodes):
        translations = get_translations(rn.tags["wikidata"], lang)
        if translations["translations"]:
            tags = {}
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
                continue
            else:
                select_translation = int(select_translation)

            tags["name:" + lang] = translation_options[select_translation]
            if changeset is None and not dry_run:
                api.ChangesetCreate(changeset_tags)
                changeset = True

            if not dry_run:
                lt.update_element(element=rn, tags=tags, api=api)

    for rw in tqdm(result.ways):
        translations = get_translations(rw.tags["wikidata"], lang)
        if translations["translations"]:
            tags = {}
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
                continue
            else:
                select_translation = int(select_translation)

            tags["name:" + lang] = translation_options[select_translation]
            if changeset is None and not dry_run:
                api.ChangesetCreate(changeset_tags)
                changeset = True

            if not dry_run:
                lt.update_element(element=rw, tags=tags, api=api)

    for rr in tqdm(result.relations):
        translations = get_translations(rr.tags["wikidata"], lang)
        if translations["translations"]:
            tags = {}
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
                continue
            else:
                select_translation = int(select_translation)

            tags["name:" + lang] = translation_options[select_translation]
            if changeset is None and not dry_run:
                api.ChangesetCreate(changeset_tags)
                changeset = True

            if not dry_run:
                lt.update_element(element=rr, tags=tags, api=api)

    if changeset and not dry_run:
        api.ChangesetClose()
