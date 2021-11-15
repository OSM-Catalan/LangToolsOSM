from colorama import Fore, Style
import getpass
import osmapi
import overpy
import re
import requests


def login_OSM(user=None) -> osmapi.OsmApi:
    if not user:
        user = input("User: ")
    password = getpass.getpass("Password: ")
    api = osmapi.OsmApi(username=user, password=password)
    return api


def get_overpass_result(area: str, filters: str) -> overpy.Result:
    overpass_api = overpy.Overpass()
    # filters = f"""
    #     nwr["name"]["wikidata"][!"name:{lang}"]
    # """
    if re.search('([0-9.-]+,){3}[0-9.-]+', area) is None:
        query = f"""
        area[name="{area}"]->.searchArea;
        (
            {filters}(area.searchArea);
        );
        out tags;
        """
        # TODO: [~"name:[a-z]+"~"."]
    else:
        area = area.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        south = area.split(",")[0]
        west = area.split(",")[1]
        north = area.split(",")[2]
        east = area.split(",")[3]

        query = f"""
        (
            {filters}({south},{west},{north},{east});
        );
        out tags;
        """
        # TODO: [~"name:[a-z]+"~"."]

    result = overpass_api.query(query=query)
    return result


def print_element(element, remark='name', verbose=False):
    if isinstance(element, overpy.Element):  # overpass element
        tags = element.tags
        element_id = element.id
        element_type = element._type_value
    else:  # osmapi element
        tags = element['tag']
        element_id = element['id']
        element_type = '???'  # TODO: get type for osmapi elements ?osmapi.OsmApi.ParseOsm(element, element)["type"]
    if verbose:
        print(tags)

    print(f"OSM id:{element_id}({element_type})\t https://osm.org/{element_type}/{element_id}" + Style.BRIGHT)
    for key, value in tags.items():
        if key.startswith(remark):
            print(key + "=" + value, end=", ")
    print(Style.RESET_ALL)
    print("------------------------------------------------------")


def update_element(element, tags, api):
    if not isinstance(element, overpy.Element):
        raise TypeError("element must inherits 'overpy.Element'")
    print(Fore.GREEN + Style.BRIGHT + "\n+ " + str(tags) + Style.RESET_ALL)
    allow_update = input("Add tags [Y/n]:")
    if allow_update in ["y", "Y", "yes", ""]:
        if element._type_value in 'node':
            node = api.NodeGet(element.id)
            node_data = {
                'id': node["id"],
                'lat': node["lat"],
                'lon': node["lon"],
                'tag': node["tag"],
                'version': node["version"],
            }
            node_data["tag"].update(tags)
            api.NodeUpdate(node_data)
        elif element._type_value in 'way':
            way = api.WayGet(element.id)
            way_data = {
                'id': way["id"],
                'nd': way["nd"],
                'tag': way["tag"],
                'version': way["version"],
            }
            way_data["tag"].update(tags)
            api.WayUpdate(way_data)
        elif element._type_value in 'relation':
            rel = api.RelationGet(element.id)
            rel_data = {
                'id': rel["id"],
                'member': rel["member"],
                'tag': rel["tag"],
                'version': rel["version"],
            }
            rel_data["tag"].update(tags)
            api.RelationUpdate(rel_data)

    print("\n")

