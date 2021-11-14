import click
from colorama import Fore, Style
import getpass
import osmapi
import overpy
import re
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
    overpass_api = overpy.Overpass()
    area = input("Bounding box(South,West,North,East) or name value: ")
    lang = input("Name language to add (e.g. ca, en, ...): ") or "ca"
    if not dry_run:
        user = input("User: ")
        password = getpass.getpass("Password: ")
        api = osmapi.OsmApi(username=user, password=password)

    changeset_tags = {u"comment": f"Fill empty name:{lang} tags translations from wikidata", u"source": u"wikidata"}

    if verbose:
        print(changeset_tags)

    if re.search('([0-9.-]+,){3}[0-9.-]+', area) is None:
        result = overpass_api.query(f"""
        area[name="{area}"]->.searchArea;
        (
            nwr["name"]["wikidata"][!"name:{lang}"](area.searchArea);
        );
        out tags;
        """)
        # TODO: [~"name:[a-z]+"~"."]
    else:
        area = area.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        south = area.split(",")[0]
        west = area.split(",")[1]
        north = area.split(",")[2]
        east = area.split(",")[3]

        result = overpass_api.query(f"""
        (
            nwr["name"]["wikidata"][!"name:{lang}"]({south},{west},{north},{east});
        );
        out tags;
        """)
        # TODO: [~"name:[a-z]+"~"."]
    changeset = None
    for rn in tqdm(result.nodes):
        translations = get_translations(rn.tags["wikidata"], lang)
        if translations["translations"]:
            tags = {}
            if verbose:
                print(rn.tags)
            print(f"OSM id:{rn.id}(node)" + Style.BRIGHT)
            for key, value in rn.tags.items():
                if key.startswith('name'):
                    print(key + "=" + value, end=", ")
            print(Style.RESET_ALL)
            print("------------------------------------------------------")
            print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
            translation_options = [translations['translations']['label']['value']]
            i = 1
            if 'aliases' in translations['translations'].keys():
                for alias in translations['translations']['aliases']:
                    print(str(i) + ' = ' + alias['value'])
                    translation_options.append(alias['value'])
                    i = i + 1

            select_translation = input("Select translation ('-' to skip): ") or '0'
            while select_translation not in [str(x) for x in range(len(translation_options))] + ['-']:
                print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                select_translation = input("Select translation ('-' to skip): ") or '0'

            if select_translation in '-':
                next
            else:
                select_translation = int(select_translation)

            tags["name:" + lang] = translation_options[select_translation]
            print(Fore.GREEN + Style.BRIGHT + "\n+ " + str(tags) + Style.RESET_ALL)
            if changeset is None and not dry_run:
                api.ChangesetCreate(changeset_tags)
                changeset = True

            allow_node = input("It's correct[Y/n]:")
            if allow_node in ["y", "Y", "yes", ""] and not dry_run:
                node = api.NodeGet(rn.id)
                node_data = {
                    'id': node["id"],
                    'lat': node["lat"],
                    'lon': node["lon"],
                    'tag': node["tag"],
                    'version': node["version"],
                }
                node_data["tag"].update(tags)
                api.NodeUpdate(node_data)
            print("\n")

    for rw in tqdm(result.ways):
        translations = get_translations(rw.tags["wikidata"], lang)
        if translations["translations"]:
            tags = {}
            if verbose:
                print(rw.tags)
            print(f"OSM id:{rw.id}(node)" + Style.BRIGHT)
            for key, value in rw.tags.items():
                if key.startswith('name'):
                    print(key + "=" + value, end=", ")
            print(Style.RESET_ALL)
            print("------------------------------------------------------")
            print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
            translation_options = [translations['translations']['label']['value']]
            i = 1
            if 'aliases' in translations['translations'].keys():
                for alias in translations['translations']['aliases']:
                    print(str(i) + ' = ' + alias['value'])
                    translation_options.append(alias['value'])
                    i = i + 1

            select_translation = input("Select translation ('-' to skip): ") or '0'
            while select_translation not in [str(x) for x in range(len(translation_options))] + ['-']:
                print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                select_translation = input("Select translation ('-' to skip): ") or '0'

            if select_translation in '-':
                next
            else:
                select_translation = int(select_translation)

            tags["name:" + lang] = translation_options[select_translation]
            print(Fore.GREEN + Style.BRIGHT + "\n+ " + str(tags) + Style.RESET_ALL)
            if changeset is None and not dry_run:
                api.ChangesetCreate(changeset_tags)
                changeset = True

            allow_node = input("It's correct[Y/n]:")
            if allow_node in ["y", "Y", "yes", ""] and not dry_run:
                node = api.NodeGet(rw.id)
                node_data = {
                    'id': node["id"],
                    'lat': node["lat"],
                    'lon': node["lon"],
                    'tag': node["tag"],
                    'version': node["version"],
                }
                node_data["tag"].update(tags)
                api.NodeUpdate(node_data)
            print("\n")

    for rr in tqdm(result.relations):
        translations = get_translations(rr.tags["wikidata"], lang)
        if translations["translations"]:
            tags = {}
            if verbose:
                print(rr.tags)
            print(f"OSM id:{rr.id}(node)" + Style.BRIGHT)
            for key, value in rr.tags.items():
                if key.startswith('name'):
                    print(key + "=" + value, end=", ")
            print(Style.RESET_ALL)
            print("------------------------------------------------------")
            print(Style.BRIGHT + f"0 = " + translations['translations']['label']['value'] + Style.RESET_ALL)
            translation_options = [translations['translations']['label']['value']]
            i = 1
            if 'aliases' in translations['translations'].keys():
                for alias in translations['translations']['aliases']:
                    print(str(i) + ' = ' + alias['value'])
                    translation_options.append(alias['value'])
                    i = i + 1

            select_translation = input("Select translation ('-' to skip): ") or '0'
            while select_translation not in [str(x) for x in range(len(translation_options))] + ['-']:
                print('Enter a number from 0 to ' + str(len(translation_options) - 1))
                select_translation = input("Select translation ('-' to skip): ") or '0'

            if select_translation in '-':
                next
            else:
                select_translation = int(select_translation)

            tags["name:" + lang] = translation_options[select_translation]
            print(Fore.GREEN + Style.BRIGHT + "\n+ " + str(tags) + Style.RESET_ALL)
            if changeset is None and not dry_run:
                api.ChangesetCreate(changeset_tags)
                changeset = True

            allow_node = input("It's correct[Y/n]:")
            if allow_node in ["y", "Y", "yes", ""] and not dry_run:
                node = api.NodeGet(rr.id)
                node_data = {
                    'id': node["id"],
                    'lat': node["lat"],
                    'lon': node["lon"],
                    'tag': node["tag"],
                    'version': node["version"],
                }
                node_data["tag"].update(tags)
                api.NodeUpdate(node_data)
            print("\n")

    if changeset and not dry_run:
        api.ChangesetClose()
