from colorama import Fore, Style
import getpass
import osmapi
import overpy
import re
import requests


def login_osm(username=None) -> osmapi.OsmApi:
    if not username:
        username = input('User: ')
    password = getpass.getpass('Password: ')
    api = osmapi.OsmApi(username=username, password=password)
    return api


def get_overpass_result(area: str, filters: str) -> overpy.Result:
    overpass_api = overpy.Overpass()
    # filters = "nwr['name']['wikidata'][~"name:[a-z]+"~"."]"
    if re.search('([0-9.-]+,){3}[0-9.-]+', area):
        area = area.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
        south = area.split(',')[0]
        west = area.split(',')[1]
        north = area.split(',')[2]
        east = area.split(',')[3]

        query = f"""
        (
            {filters}({south},{west},{north},{east});
        );
        out tags;
        """
    elif re.search(r'^\[.+\]$', area):
        query = f"""
         area{area}->.searchArea;
         (
             {filters}(area.searchArea);
         );
         out tags;
         """
    else:
        query = f"""
        area[name="{area}"]->.searchArea;
        (
            {filters}(area.searchArea);
        );
        out tags;
        """

    result = overpass_api.query(query=query)
    return result


def print_osm_object(osm_object, remark='name', verbose=False):
    if isinstance(osm_object, overpy.Element):  # overpass object
        tags = osm_object.tags
        osm_id = osm_object.id
        osm_type = osm_object._type_value
    else:  # osmapi object
        tags = osm_object['tag']
        osm_id = osm_object['id']
        osm_type = '???'  # TODO: get type for osmapi objects ?osmapi.OsmApi.ParseOsm(element, element)['type']
    if verbose:
        print(tags)
        print('------------------------------------------------------')

    print(f'OSM id:{osm_id}({osm_type})\t https://osm.org/{osm_type}/{osm_id}' + Style.BRIGHT)
    for key, value in tags.items():
        if key.startswith(remark):
            print(key + '=' + value, end=', ')
    print(Style.RESET_ALL)
    print("------------------------------------------------------")


def update_osm_object(osm_object, tags, api):
    if not isinstance(osm_object, overpy.Element):
        raise TypeError('osm_object must inherits "overpy.Element"')
    print(Fore.GREEN + Style.BRIGHT + '\n+ ' + str(tags) + Style.RESET_ALL)
    allow_update = input('Add tags [Y/n]: ').lower()
    if allow_update in ['y', 'yes', '']:
        if isinstance(osm_object, overpy.Node):
            node = api.NodeGet(osm_object.id)
            node_data = {
                'id': node['id'],
                'lat': node['lat'],
                'lon': node['lon'],
                'tag': node['tag'],
                'version': node['version'],
            }
            node_data['tag'].update(tags)
            return api.NodeUpdate(node_data)
        elif isinstance(osm_object, overpy.Way):
            way = api.WayGet(osm_object.id)
            way_data = {
                'id': way['id'],
                'nd': way['nd'],
                'tag': way['tag'],
                'version': way['version'],
            }
            way_data['tag'].update(tags)
            return api.WayUpdate(way_data)
        elif isinstance(osm_object, overpy.Relation):
            rel = api.RelationGet(osm_object.id)
            rel_data = {
                'id': rel['id'],
                'member': rel['member'],
                'tag': rel['tag'],
                'version': rel['version'],
            }
            rel_data['tag'].update(tags)
            return api.RelationUpdate(rel_data)


def print_changeset_status(changeset, n_edits, verbose):
    if n_edits < 195:
        print(f'Number of editions in the current changeset: {n_edits}')
    elif n_edits < 200:
        print(
            Fore.YELLOW + f'Number of editions in the current changeset: {n_edits}'
                          ' (> 200 is considered a mass modification)' + Style.RESET_ALL)
    else:
        print(Fore.RED + f'Too much editions in the current changeset: {n_edits}'
                         '(> 200 is considered a mass modification)')
        print('Press "Ctrl-c" to STOP now.' + Style.RESET_ALL)
    if verbose > 1 and changeset:
        print(Fore.CYAN + f'Changeset opened: https://www.osm.org/changeset/{changeset}' + Style.RESET_ALL)