import getpass
import re
import click
import osmapi
import overpy
from colorama import Fore, Style
from tqdm import tqdm


@click.command()
@click.option("--verbose",default=False,is_flag=True)
@click.option("--dry-run",default=False,is_flag=True)
def regex_name_langcommand(verbose, dry_run):
    overpass_api = overpy.Overpass()

    user = input("User: ")
    password = getpass.getpass("Password: ")
    area = input("Bounding box(South,West,North,East) or name value: ")
    lang = input("Name language to add (e.g. ca, en, ...): ") or "ca"
    find = input("Regular expression to search at name tags: ")
    replace = input(f"Regular expression to replace object name and fill name:{lang} : ")
    api = osmapi.OsmApi(username=user, password=password)

    changeset_tags= {u"comment": f"Fill empty name:{lang} tags with regex name:«" +
                         find + f"» -> name:{lang}=«" + replace + "».",
                     u"source": u"name tag"}

    if verbose:
        print(changeset_tags)

    if re.search('([0-9.-]+,){3}[0-9.-]+', area) is None:
        result = overpass_api.query(f"""
        area[name="{area}"]->.searchArea;
        (
            nwr["name"~"{find}"][!"name:{lang}"](area.searchArea);
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
            nwr["name"~"{find}"][!"name:{lang}"]({south},{west},{north},{east});
        );
        out tags;
        """)


    regex = re.compile(find, )
    changeset = None

    for rn in tqdm(result.nodes):
        if "name" in rn.tags:
            tags = {}
            tags["name:" + lang] = regex.sub(replace, rn.tags["name"])

            if tags:
                if verbose:
                    print(rn.tags)
                print(f"OSM id:{rn.id}(node)" + Style.BRIGHT)
                for key, value in rn.tags.items():
                    if key.startswith('name'):
                        print(key + "=" + value, end=", ")
                print(Fore.GREEN + "\n+ " + str(tags) + Style.RESET_ALL)
                print("------------------------------------------------------")

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
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                allow_node = input("It's correct[Y/n]:")
                if allow_node in ["","y","Y","yes"] and not dry_run:
                    api.NodeUpdate(node_data)
                print("\n")


    for rw in tqdm(result.ways):
        if "name" in rw.tags:
            tags = {}
            tags["name:" + lang] = regex.sub(replace, rw.tags["name"])

            if tags:
                if verbose:
                    print(rw.tags)
                print(f"OSM id:{rw.id}(node)" + Style.BRIGHT)
                for key, value in rw.tags.items():
                    if key.startswith('name'):
                        print(key + "=" + value, end=", ")
                print(Fore.GREEN + "\n+ " + str(tags) + Style.RESET_ALL)
                print("------------------------------------------------------")

                way = api.WayGet(rw.id)
                way_data = {
                    'id': way["id"],
                    'nd': way["nd"],
                    'tag': way["tag"],
                    'version': way["version"],
                }
                way_data["tag"].update(tags)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                allow_way = input("It's correct[Y/n]:")
                if allow_way in ["","y","Y","yes"] and not dry_run:
                    api.WayUpdate(way_data)
                print("\n")


    for rr in tqdm(result.relations):
        if "name:" in rr.tags:
            tags = {}
            tags["name:" + lang] = regex.sub(replace, rr.tags["name"])

            if tags:
                if verbose:
                    print(rr.tags)
                print(f"OSM id:{rr.id}(node)" + Style.BRIGHT)
                for key, value in rr.tags.items():
                    if key.startswith('name'):
                        print(key + "=" + value, end=", ")
                print(Fore.GREEN + "\n+ " + str(tags) + Style.RESET_ALL)
                print("------------------------------------------------------")

                rel = api.RelationGet(rr.id)
                rel_data = {
                    'id': rel["id"],
                    'member': rel["member"],
                    'tag': rel["tag"],
                    'version': rel["version"],
                }
                rel_data["tag"].update(tags)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                allow_rel = input("It's correct[Y/n]:")
                if allow_rel in ["","y","Y","yes"] and not dry_run:
                    api.RelationUpdate(rel_data)
                print("\n")

    if changeset and not dry_run:
        api.ChangesetClose()
