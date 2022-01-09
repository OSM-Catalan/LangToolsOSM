import click
import requests
from tqdm import tqdm
from colorama import Fore, Style

import lib.osm_utils as lt
from lib import __version__


# TODO: move to lib/wikimedia.py
def get_links(ident) -> dict:
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
    

def filter_wikidata_tag(data) -> dict:
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
@click.option('--area', prompt='Bounding box (South,West,North,East), overpass filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr[!wikipedia][wikidata]".""")
@click.option('--lang', prompt='Language of the wikipedia page to add (e.g. ca, en, ...)', type=str, help='A language code matching the prefix of a wikipedia site. (eg. "ca" for https://ca.wikipedia.org)')
@click.option('--all-langs', default=False, is_flag=True, help='Add all available wikipedia pages for all languages. WARNING: this is not recommended. See https://wiki.openstreetmap.org/wiki/Key:wikipedia#Secondary_languages')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def fill_wikipedia_from_wikidatacommand(area, batch, dry_run, filters, lang, all_langs,  username, verbose):
    """Add «wikipedia» from «wikidata» tag."""
    if not dry_run:
        api = lt.login_osm(username=username)
    if not filters:
        filters = 'nwr[!wikipedia][wikidata]'
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Fill empty wikipedia tags resolving wikidata id in {area} for {filters}',
                      u'source': u'wikipedia', u'created_by': f'LangToolsOSM {__version__}'}
    print(changeset_tags)
    result = lt.get_overpass_result(area=area, filters=filters)
    n_objects = len(result.nodes) + len(result.ways) + len(result.relations)
    print('######################################################')
    print(f'{str(n_objects)} objects found ({str(len(result.nodes))} nodes, {str(len(result.ways))}'
          f' ways and {str(len(result.relations))} relations).')
    print('######################################################')
    if n_objects > 200 and batch is not None and batch > 200:
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
              'Reduce the area, add batch option < 200 or stop translating when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    # TODO print and prefetch wikimedia info
    changeset = None
    n_edits = 0
    total_edits = 0
    try:
        for osm_object in tqdm(result.nodes + result.ways + result.relations):
            lt.print_osm_object(osm_object, verbose=verbose)
            if 'wikidata' in osm_object.tags:
                links = get_links(osm_object.tags['wikidata'])
                if links:
                    tags = {}
                    if links['id'] != osm_object.tags['wikidata']:
                        print(f"Wikidata points to a redirected item. Updating wikidata tag {osm_object.tags['wikidata']} -> {links['id']}")
                        tags['wikidata'] = links['id']

                    for language, value in links['langs'].items():
                        if language == lang:
                            tags['wikipedia'] = f'{language}:{value}'
                        elif all_langs:
                            tags[f'wikipedia:{language}'] = value
                    if tags:
                        if not dry_run:
                            if changeset is None:
                                changeset = api.ChangesetCreate(changeset_tags)
                            committed = lt.update_osm_object(osm_object=osm_object, tags=tags, api=api)
                            if committed:
                                n_edits = n_edits + 1
                            if n_edits > batch:
                                print(
                                    f'{n_edits} edits DONE! https://www.osm.org/changeset/{changeset}. Opening a new changeset.')
                                total_edits = total_edits + n_edits
                                api.ChangesetClose()
                                changeset = None
                                n_edits = 0

    finally:
        print('######################################################')
        if changeset and not dry_run:
            if not batch:
                total_edits = n_edits
            print(f'DONE! {total_edits} objects modified' # from {n_objects_with_wikidata}'
                  # f' objects with available translations ({round(total_edits / n_objects_with_wikidata * 100)}%)'
                  f' https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
