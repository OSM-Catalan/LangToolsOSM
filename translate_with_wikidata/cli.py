import click
from colorama import Fore, Style
import lib.LangToolsOSM as lt
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
@click.option("--verbose", default=False, is_flag=True)
@click.option("--dry-run", default=False, is_flag=True)
def translate_with_wikidatacommand(verbose, dry_run):
    if not dry_run:
        api = lt.login_OSM()
    area = input("Bounding box(South,West,North,East) or name value: ")
    lang = input("Name language to add (e.g. ca, en, ...): ") or "ca"
    changeset_tags = {u"comment": f"Fill empty name:{lang} tags translations from wikidata", u"source": u"wikidata"}
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
