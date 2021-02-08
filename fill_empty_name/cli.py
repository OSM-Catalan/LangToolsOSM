import click
import osmapi
import overpy
import getpass
import re
from colorama import Fore, Style
from tqdm import tqdm


@click.command()
@click.option("--verbose",default=False,is_flag=True)
@click.option("--dry-run",default=False,is_flag=True)
def fill_empty_namecommand(verbose, dry_run):
    overpass_api = overpy.Overpass()

    user = input("User: ")
    password = getpass.getpass("Password: ")

    area = input("Bounding box(South,West,North,East) or name value: ")
    default_lang = input("Default lang(ca, en): ") or "ca"
    api = osmapi.OsmApi(username=user, password=password)

    changesetTags= {u"comment": f"Fill empty name tags with name:{default_lang}", u"source": f"name:{default_lang} tag"}

    if verbose:
        print(changesetTags)


    if re.search('([0-9.-]+,){3}[0-9.-]+', area) is None:
        result = overpass_api.query(f"""
        area[name="{area}"]->.searchArea;
        (
            nwr["name:ca"][!"name"](area.searchArea);
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
            nwr["name:ca"][!"name"]({south},{west},{north},{east});
        );
        out tags;
        """)

    changeset = None
    for rn in tqdm(result.nodes):
        if f"name:{default_lang}" in rn.tags:
            tags = {}

            if verbose:
                print(rn.tags)
            print(f"OSM id:{rn.id}(node) name:{default_lang}=" + rn.tags.get(f"name:{default_lang}", ""))
            tags["name"] = rn.tags["name:" + default_lang]
            print(Fore.GREEN + "+ " + str(tags) + Style.RESET_ALL)
            print("------------------------------------------------------")
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
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changesetTags)
                    changeset = True

                allow_node = input("It's correct[Y/n]:")
                if allow_node in ["y","","Y","yes"] and not dry_run:
                    api.NodeUpdate(node_data)
                print("\n")


    for rw in tqdm(result.ways):
        if f"name:{default_lang}" in rw.tags:
            tags = {}

            if verbose:
                print(rw.tags)
            print(f"OSM id:{rw.id}(way) name:{default_lang}=" + rw.tags.get(f"name:{default_lang}", ""))
            tags["name"] = rw.tags["name:" + default_lang]
            print(Fore.GREEN + "+ " + str(tags) + Style.RESET_ALL)
            print("------------------------------------------------------")
            if tags:
                way = api.WayGet(rw.id)
                way_data = {
                    'id': way["id"],
                    'nd': way["nd"],
                    'tag': way["tag"],
                    'version': way["version"],
                }
                way_data["tag"].update(tags)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changesetTags)
                    changeset = True

                allow_way = input("It's correct[Y/n]:")
                if allow_way in ["y","","Y","yes"] and not dry_run:
                    api.WayUpdate(way_data)
                print("\n")


    for rr in tqdm(result.relations):
        if f"name:{default_lang}" in rr.tags:
            tags = {}

            if verbose:
                print(rr.tags)
            print(f"OSM id:{rr.id}(relation) name:{default_lang}=" + rr.tags.get(f"name:{default_lang}", ""))
            tags["name"] = rr.tags["name:" + default_lang]
            print(Fore.GREEN + "+ " + str(tags) + Style.RESET_ALL)
            print("------------------------------------------------------")
            if tags:
                rel = api.RelationGet(rr.id)
                rel_data = {
                    'id': rel["id"],
                    'member': rel["member"],
                    'tag': rel["tag"],
                    'version': rel["version"],
                }
                rel_data["tag"].update(tags)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changesetTags)
                    changeset = True

                allow_rel = input("It's correct[Y/n]:")
                if allow_rel in ["y","","Y","yes"] and not dry_run:
                    api.RelationUpdate(rel_data)
                print("\n")

    if changeset and not dry_run:
        api.ChangesetClose()
