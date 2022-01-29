import getpass
import osmapi
import overpy
import re
import time
from colorama import Fore, Style


def login_osm(username=None) -> osmapi.OsmApi:
    if not username:
        username = input('User: ')
    password = getpass.getpass('Password: ')
    api = osmapi.OsmApi(username=username, password=password)
    return api


def get_overpass_result(area: str, filters: str, query: str = None, retry=5, sleep_retry=10) -> overpy.Result:
    overpass_api = overpy.Overpass()
    # filters = "nwr['name']['wikidata'][~"name:[a-z]+"~"."]"
    if query is None:
        if re.search('([0-9.-]+,){3}[0-9.-]+', area):
            area = area.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            south = area.split(',')[0]
            west = area.split(',')[1]
            north = area.split(',')[2]
            east = area.split(',')[3]

            query = f"""
            [timeout:1000];
            (
                {filters}({south},{west},{north},{east});
            );
            out tags qt;
            """
        elif re.search(r'^\[.+\]$', area):
            query = f"""
            [timeout:1000];
             area{area}->.searchArea;
             (
                 {filters}(area.searchArea);
             );
             out tags qt;
             """
        else:
            query = f"""
            [timeout:1000];
            area[name="{area}"]->.searchArea;
            (
                {filters}(area.searchArea);
            );
            out tags qt;
            """

    try:
        result = overpass_api.query(query=query)
    except (overpy.exception.OverpassTooManyRequests, overpy.exception.OverpassGatewayTimeout) as error:
        result = None
        for t in range(1, retry + 1):
            print('Overpass response: ', str(error).removeprefix("<class 'overpy.exception.").removesuffix("'>"), ' Retry ' + str(t) + ' of ' + str(retry))
            time.sleep(sleep_retry)
            if result is None:
                try:
                    overpass_api.query(query=query)
                except (overpy.exception.OverpassTooManyRequests, overpy.exception.OverpassGatewayTimeout) as error0:
                    pass
            else:
                return result
        if result is None:
            print('No overpass results after ' + str(retry) + ' retries.')
            raise error
    return result


def print_osm_object(osm_object, remark='name', verbose=False):
    if isinstance(osm_object, overpy.Element):  # overpy object
        tags = osm_object.tags
        osm_id = osm_object.id
        osm_type = osm_object._type_value
    else:  # osmapi object
        tags = osm_object['tag']
        osm_id = osm_object['id']
        if set({'id', 'lat', 'lon', 'tag', 'version'}).issubset(osm_object.keys()):
            osm_type = 'node'
        elif set({'id', 'nd', 'tag', 'version'}).issubset(osm_object.keys()):
            osm_type = 'way'
        elif set({'id', 'member', 'tag', 'version'}).issubset(osm_object.keys()):
            osm_type = 'relation'
        else:
            osm_type = '???'
    if verbose:
        print(tags)
        print('------------------------------------------------------')

    if 'wikidata' in tags.keys():
        wikidata_url = '\t https://wikidata.org/wiki/' + tags['wikidata']
    else:
        wikidata_url = ''
    print(f'OSM id: {osm_id}({osm_type})\t https://osm.org/{osm_type}/{osm_id}' + wikidata_url + Style.BRIGHT)
    for key, value in tags.items():
        if key.startswith(remark):
            print(key + '=' + value, end=', ')
    print(Style.RESET_ALL)
    print("------------------------------------------------------")


def update_osm_object(osm_object: overpy.Element, tags: dict, api: osmapi.OsmApi) -> dict:
    if isinstance(osm_object, overpy.Element):
        object_tags = osm_object.tags
    else:
        raise TypeError('osm_object must inherits "overpy.Element"')
    overwrite_keys = list(set.intersection(set(tags.keys()), set(object_tags.keys())))
    if overwrite_keys:
        overwrite_keys.sort()
        overwrite_tags = {key: object_tags[key] for key in overwrite_keys}
        for key in list(overwrite_tags.keys()):
            if overwrite_tags[key] == tags[key]:  # omit if the tag has the same value as the osm_object
                overwrite_tags.pop(key)
                tags.pop(key)
        if len(overwrite_tags) > 0:
            print(Fore.RED + Style.BRIGHT + '- ' + str(overwrite_tags) + Style.RESET_ALL)
    print(Fore.GREEN + Style.BRIGHT + '+ ' + str(tags) + Style.RESET_ALL)
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


def print_changeset_status(changeset: dict, n_edits: int, verbose: int):
    if n_edits < 195:
        print(f'Number of editions in the current changeset: {n_edits}')
    elif n_edits < 200:
        print(
            Fore.YELLOW + f'Number of editions in the current changeset: {n_edits}'
                          ' (> 200 is considered a mass modification in OSMCha)' + Style.RESET_ALL)
    else:
        print(Fore.RED + f'Too much editions in the current changeset: {n_edits}'
                         '(> 200 is considered a mass modification in OSMCha)')
        print('Press "Ctrl-c" to STOP now.' + Style.RESET_ALL)
    if verbose > 1 and changeset:
        print(Fore.LIGHTBLACK_EX + f'Changeset opened: https://www.osm.org/changeset/{changeset}' + Style.RESET_ALL)
