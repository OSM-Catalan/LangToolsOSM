import click
from colorama import Fore, Style
import re
from tqdm import tqdm

import lib.osm_utils as lt
import lib.wikimedia as wikimedia
from lib import __version__


@click.command()
@click.option('--area', prompt='Bounding box (South,West,North,East), overpass filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr[wikipedia][!wikidata]".""")
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def fill_wikidata_from_wikipediacommand(area, batch, dry_run, filters, username, verbose):
    """Add «wikidata» from «wikipedia» tag."""
    if not dry_run:
        api = lt.login_osm(username=username)
    if not filters:
        filters = 'nwr[wikipedia][!wikidata]'
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Fill empty wikidata tags from wikipedia tag in {area} for {filters}',
                      u'source': u'wikipedia', u'created_by': f'LangToolsOSM {__version__}'}
    print(changeset_tags)
    result = lt.get_overpass_result(area=area, filters=filters)
    n_objects = len(result.nodes) + len(result.ways) + len(result.relations)
    print('######################################################')
    print(f'{str(n_objects)} objects found ({str(len(result.nodes))} nodes, {str(len(result.ways))}'
          f' ways and {str(len(result.relations))} relations).')
    print('######################################################')

    wikipedia = []
    pattern = re.compile(r'^([a-z])+:(.+)')
    for osm_object in result.nodes + result.ways + result.relations:
        if 'wikipedia' in osm_object.tags.keys():
            wikipedia.append(osm_object.tags['wikipedia'])
    wikipedia_unique = list(set(wikipedia))
    db = wikimedia.get_wikidata_from_wikipedia(wikipedia=wikipedia_unique)
    n_matches = 0
    n_objects_with_wikidata = 0
    for key in db.keys():
        db[key].update({'objects': [], 'answer': {'value': None, 'committed': False}})
        if db[key]['translations']:
            n_objects_with_wikidata = n_objects_with_wikidata + wikipedia.count(key)
            n_matches = n_matches + 1
    if n_objects_with_wikidata > 0:
        percent_objects_with_wikidata = round(n_objects_with_wikidata / n_objects * 100)
    else:
        percent_objects_with_wikidata = 0
        print(f'{n_matches} translations available from wikidata. Nothing to work on here.')
        print('######################################################')
        exit()
    print(f'{n_matches} translations available from wikidata for {n_objects_with_wikidata}'
          f' OSM objects ({percent_objects_with_wikidata}%).')
    print('######################################################')
    if n_objects_with_wikidata > 200:
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
                         'Reduce the area or stop translating when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    #     TODO: query to view the selection in overpass-turbo
    start = input('Start editing [Y/n]: ').lower()
    if start not in ['y', 'yes', '']:
        exit()

    changeset = None
    n_edits = 0
    total_edits = 0
    try:
        for osm_object in tqdm(result.nodes + result.ways + result.relations):
            if not dry_run:
                lt.print_changeset_status(changeset=changeset, n_edits=n_edits, verbose=verbose)
            lt.print_osm_object(osm_object, verbose=verbose)
            if 'wikipedia' in osm_object.tags.keys and osm_object.tags['wikipedia'] in db.keys():
                wikidata = db[osm_object.tags['wikipedia']]
                tags = {'wikidata': wikidata}
                if not dry_run:
                    if changeset is None:
                        changeset = api.ChangesetCreate(changeset_tags)
                    committed = lt.update_osm_object(osm_object=osm_object, tags=tags, api=api)
                    if committed:
                        n_edits = n_edits + 1
                    if batch and n_edits >= batch:
                        print(f'{n_edits} edits DONE! https://www.osm.org/changeset/{changeset}. Opening a new changeset.')
                        total_edits = total_edits + n_edits
                        api.ChangesetClose()
                        changeset = None
                        n_edits = 0
                else:
                    print(Fore.GREEN + Style.BRIGHT + '\n+ ' + str(tags) + Style.RESET_ALL)
            else:
                print(Fore.BLUE + 'SKIP: object without "wikipedia" tag.' + Style.RESET_ALL)

    finally:
        print('######################################################')
        if changeset and not dry_run:
            total_edits = total_edits + n_edits
            print(f'DONE! {total_edits} objects modified from {n_objects_with_wikidata}'
                  f' objects with available translations ({round(total_edits / n_objects_with_wikidata * 100)}%)'
                  f' https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
