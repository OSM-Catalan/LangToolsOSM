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
def fill_empty_name_langcommand(debug, verbose, dry_run):
    overpass_api = overpy.Overpass()

    user = input("User: ")
    password = getpass.getpass("Password: ")

    area = input("Bounding box(South,West,North,East) or name value: ")
    lang = input("Name language to add (e.g. ca, en, ...): ") or "ca"
    api = osmapi.OsmApi(username=user, password=password)

    changesetTags= {u"comment": f"Fill empty name:{lang} tags with name", u"source": u"name tag"}

    if verbose:
        print(changesetTags)

    if re.search('([0-9.-]+,){3}[0-9.-]+', area) is None:
        result = overpass_api.query(f"""
        area[name="{area}"]->.searchArea;
        (
            nwr["name"][~"name:.*"~"."][!"name:{lang}"](area.searchArea);
        );
        (._;>;);
        out body;
        """)
    else:
        area = area.replace("[","").replace("]","").replace("(","").replace(")","")
        south = area.split(",")[0]
        west = area.split(",")[1]
        north = area.split(",")[2]
        east = area.split(",")[3]

        result = overpass_api.query(f"""
        (
            nwr["name"][~"name:.*"~"."][!"name:{lang}"]({south},{west},{north},{east});
        );
        (._;>;);
        out body;
        """)

    changeset = None
    for rn in tqdm(result.nodes):
        if "name" in rn.tags:
                tags = {}

                if verbose:
                    print(rn.tags)
                print(f"OSM id:{rn.id}(node) name=" + rn.tags.get("name", ""))
                tags["name:{lang}"] = rn.tags["name"]
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

                    allow_node = input("It's correct[y/N]:")
                    if allow_node in ["y","Y","yes"] and not dry_run:
                        api.NodeUpdate(node_data)
                    print("\n")


    for rw in tqdm(result.ways):
        if "name" in rw.tags:
                tags = {}

                if verbose:
                    print(rw.tags)
                print(f"OSM id:{rw.id}(way) name=" + rw.tags.get("name", ""))
                tags["name:" + {lang}] = rw.tags["name"]
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

                    allow_way = input("It's correct[y/N]:")
                    if allow_way in ["y","Y","yes"] and not dry_run:
                        api.WayUpdate(way_data)
                    print("\n")


    for rr in tqdm(result.relations):
        if "name:" in rr.tags:
                tags = {}

                if verbose:
                    print(rr.tags)
                print(f"OSM id:{rr.id}(relation) name:=" + rr.tags.get("name", ""))
                tags["name:" + lang] = rr.tags["name"]
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

                    allow_rel = input("It's correct[y/N]:")
                    if allow_rel in ["y","Y","yes"] and not dry_run:
                        api.RelationUpdate(rel_data)
                    print("\n")

    if changeset and not dry_run:
        api.ChangesetClose()
