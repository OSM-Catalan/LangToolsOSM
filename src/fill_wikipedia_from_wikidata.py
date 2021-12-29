import click
import requests
import osmapi
import overpy
import getpass
import re
from tqdm import tqdm
from colorama import Fore, Style


def get_links(ident)->dict:
    response = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{ident}.json")
    data = response.json()
    ret = {}
    wikidata_id = list(data["entities"].keys())[0]

    for sitelink in data["entities"][wikidata_id]["sitelinks"].keys():
        if sitelink.endswith("wiki") and sitelink!= "commonswiki":
            ret[sitelink.replace("wiki","")] = data["entities"][wikidata_id]["sitelinks"][sitelink]["title"]

    return {
        "id": wikidata_id,
        "langs": ret }
    

def filter_wikidata_tag(data)->dict:
    ret = {
        "nodes": [],
        "ways": [],
        "relations": []
    }

    for node in data.nodes:
         if "wikidata" in node.tags:
             ret["nodes"].append(node)

    for way in data.ways:
         if "wikidata" in way.tags:
             ret["ways"].append(way)

    for relation in data.relations:
        if "wikidata" in relation.tags:
            ret["relations"].append(relation)

    return ret

@click.command()
@click.option("--debug",default=False,is_flag=True)
def fill_wikipedia_from_wikidatacommand(debug):
    
    overpass_api = overpy.Overpass()

    user = input("User:")
    password = getpass.getpass("Password:")

    area = input("Bounding box(South,West,North,East) or name value:")
    default_lang = input("Default lang(ca,es,en):")
    all_langs = bool(input("Add all available languages?(Y/n):") in ["y","Y","","yes"])

    try:
        api = osmapi.OsmApi(username=user, password=password)

        if re.search('([0-9.-]+,){3}[0-9.-]+', area) is None:
            result = overpass_api.query(f"""
            area[name="{area}"]->.searchArea;
            (
                nwr["wikidata"][!"wikipedia"](area.searchArea);
            );
            out tags;
            """)
        else:
            area = area.replace("[","").replace("]","").replace("(","").replace(")","")
            south = area.split(",")[0]
            west = area.split(",")[1]
            north = area.split(",")[2]
            east = area.split(",")[3]

            result = overpass_api.query(f"""
            (
                nwr["wikidata"][!"wikipedia"]({south},{west},{north},{east});
            );
            out tags;
            """)
        wikidata_results = filter_wikidata_tag(result)
        changeset = None
        for rn in tqdm(wikidata_results["nodes"]):
            if "wikidata" in rn.tags:
                links = get_links(rn.tags["wikidata"])
                if links:
                    tags = {}
                    if links["id"] != rn.tags["wikidata"]:
                        print(f"Wikidata points to a redirected item. Updating wikidata tag {rn.tags['wikidata']} -> {links['id']}")
                        tags['wikidata'] = links['id']

                    if debug:
                        print(rn.tags)
                    print(f"OSM id:{rn.id}(node) name:{rn.tags.get('name','')} Wikidata id:{rn.tags['wikidata']}")
                    for language, value in links["langs"].items():
                        if language == default_lang:
                            tags["wikipedia"] = f"{language}:{value}"
                        elif all_langs:
                            tags[f"wikipedia:{language}"] = value
                    print(Fore.GREEN + "+ " + str(tags) + Style.RESET_ALL)
                    if tags:
                        node = api.NodeGet(rn.id)
                        node_data = {
                        'id': node["id"],
                            'lat': node["lat"],
                            'lon': node["lon"],
                            'tag': node["tag"],
                            'version': node["version"],
                        }
                        node_data["tag"].update(tags)
                        if changeset is None:
                            api.ChangesetCreate({u"comment": u"Fill wikipedia tags", u"created_by": u"fill_wikipedia_osm", u"source": u"wikidata tag"})
                            changeset = True

                        allow_node = input("It's correct[Y/n]:")
                        if allow_node in ["y","","Y","yes"]:
                            api.NodeUpdate(node_data)
                        print("")

        
        for rw in tqdm(wikidata_results["ways"]):
            if "wikidata" in rw.tags:
                links = get_links(rw.tags["wikidata"])
                if links:
                    tags = {}
                    if links["id"] != rw.tags["wikidata"]:
                        print(f"Wikidata points to a redirected item. Updating wikidata tag {rw.tags['wikidata']} -> {links['id']}")
                        tags['wikidata'] = links['id']

                    if debug:
                        print(rw.tags)
                    print(f"OSM id:{rw.id}(way) name:{rw.tags.get('name','')} Wikidata id:{rw.tags['wikidata']}")
                    for language, value in links["langs"].items():
                        if language == default_lang:
                            tags["wikipedia"] = f"{language}:{value}"
                        elif all_langs:
                            tags[f"wikipedia:{language}"] = value
                    print(Fore.GREEN + "+ " + str(tags) + Style.RESET_ALL)
                    if tags:
                        way = api.WayGet(rw.id)
                        way_data = {
                            'id': way["id"],
                            'nd': way["nd"],
                            'tag': way["tag"],
                            'version': way["version"],
                        }
                        way_data["tag"].update(tags)
                        if changeset is None:
                            api.ChangesetCreate({u"comment": u"Fill wikipedia tags", u"created_by": u"fill_wikipedia_osm", u"source": u"wikidata tag"})
                            changeset = True
                        allow_way = input("It's correct[Y/n]:")
                        if allow_way in ["","y","Y","yes"]:
                            api.WayUpdate(way_data)
                        print("")


        for rr in tqdm(wikidata_results["relations"]):
            if "wikidata" in rr.tags:
                links = get_links(rr.tags["wikidata"])
                if links:
                    tags = {}
                    if links["id"] != rr.tags["wikidata"]:
                        print(f"Wikidata points to a redirected item. Updating wikidata tag {rr.tags['wikidata']} -> {links['id']}")
                        tags['wikidata'] = links['id']

                    if debug:
                        print(rr.tags)
                    print(f"OSM id:{rr.id}(relation) name:{rr.tags.get('name','')} Wikidata id:{rr.tags['wikidata']}")
                    for language, value in links["langs"].items():
                        if language == default_lang:
                            tags["wikipedia"] = f"{language}:{value}"
                        elif all_langs:
                            tags[f"wikipedia:{language}"] = value
                    print(Fore.GREEN + "+ " + str(tags) + Style.RESET_ALL)
                    if tags:
                        rel = api.RelationGet(rr.id)
                        rel_data = {
                            'id': rel["id"],
                            'member': rel["member"],
                            'tag': rel["tag"],
                            'version': rel["version"],
                        }
                        rel_data["tag"].update(tags)
                        if changeset is None:
                            api.ChangesetCreate({u"comment": u"Fill wikipedia tags", u"created_by": u"fill_wikipedia_osm", u"source": u"wikidata tag"})
                            changeset = True
                        allow_relation = input("It's correct[Y/n]:")
                        if allow_relation in ["","y","Y","yes"]:
                            api.RelationUpdate(rel_data)
                        print("")


    finally:        
        if changeset:
            api.ChangesetClose()
