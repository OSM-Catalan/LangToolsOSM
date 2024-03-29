import click
import requests
from tqdm import tqdm
from colorama import Fore, Style

import lib.osm_utils as lt
from lib import __version__, wikimedia


@click.command()
@click.option('--area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou"). Ignored if query is present.')
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--changeset-comment', type=str, help='Comment for the changeset.')
@click.option('--changeset-hashtags', type=str, help='#hashtags for the changeset. Semicolon delimited (e.g. "#toponimsCat;#Calle-Carrer").')
@click.option('--changeset-source', default='wikipedia', type=str, help='Source tag value for the changeset.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr[!wikipedia][wikidata]". Ignored if query is present.""")
@click.option('--lang', prompt='Language of the wikipedia page to add (e.g. ca, en, ...)', type=str, help='A language code matching the prefix of a wikipedia site. (eg. "ca" for https://ca.wikipedia.org)')
@click.option('--all-langs', default=False, is_flag=True, help='Add all available wikipedia pages for all languages. WARNING: this is not recommended. See https://wiki.openstreetmap.org/wiki/Key:wikipedia#Secondary_languages')
@click.option('--passwordfile', default=None, type=str, help='Path to a passwordfile, where on the first line username and password must be colon-separated (:). If provided, username option is ignored.')
@click.option('--query', type=str, help="""Overpass query to search for objects.""")
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def fill_wikipedia_from_wikidatacommand(area, batch, changeset_comment, changeset_hashtags, changeset_source, dry_run, filters, lang, all_langs, passwordfile, query, username, verbose):
    """Add «wikipedia» from «wikidata» tag."""
    if not dry_run:
        api = lt.login_osm(username=username, passwordfile=passwordfile)
    if not filters:
        filters = 'nwr[!wikipedia][wikidata]'
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Fill empty wikipedia tags resolving wikidata id in {area} for {filters}',
                      u'source': changeset_source, u'created_by': f'LangToolsOSM {__version__}'}
    if changeset_comment:
        changeset_tags.update({'comment': changeset_comment})
    if changeset_hashtags:
        changeset_tags.update({'hashtags': changeset_hashtags})
    print(changeset_tags)

    if not area and not query:
        print('Missing overpass "area" or "query" option. See "write_osm_objects_report --help" for details.')
        exit()
    result = lt.get_overpass_result(area=area, filters=filters, query=query)
    n_objects = len(result.nodes) + len(result.ways) + len(result.relations)
    print('######################################################')
    print(f'{str(n_objects)} objects found ({str(len(result.nodes))} nodes, {str(len(result.ways))}'
          f' ways and {str(len(result.relations))} relations).')
    print('######################################################')

    wikidata = []
    for osm_object in result.nodes + result.ways + result.relations:
        if 'wikidata' in osm_object.tags.keys():
            wikidata.append(osm_object.tags['wikidata'])
    wikidata_unique = list(set(wikidata))

    # Check wikidata type and remove humans. Eg. wikidata_unique = ['Q19367952', 'Q3054042']
    instance_type = wikimedia.get_instance_type_from_wikidata(wikidata_unique)
    for wikidata_id, wikidata_type in instance_type.items():
        if 'human' in wikidata_type:
            wikidata_unique.remove(wikidata_id)

    db = wikimedia.get_wikipedia_from_wikidata(wikidata_unique)
    n_matches = 0
    n_objects_with_wikipedia = 0
    for key in db.keys():
        if lang in db[key]['sitelinks'].keys() or all_langs:
            n_objects_with_wikipedia = n_objects_with_wikipedia + wikidata.count(key)
            n_matches = n_matches + 1
    if n_objects_with_wikipedia > 0:
        percent_objects_with_wikipedia = round(n_objects_with_wikipedia / n_objects * 100)
    else:
        percent_objects_with_wikipedia = 0
        print(f'{n_matches} wikipedia pages available from wikidata. Nothing to work on here.')
        print('######################################################')
        exit()
    print(f'{n_matches} wikipedia pages available from wikidata for {n_objects_with_wikipedia}'
          f' OSM objects ({percent_objects_with_wikipedia}%).')
    print('######################################################')
    if n_objects > 200 and ((batch is not None and batch > 200) or batch is None):
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
              'Reduce the area, add batch option < 200 or stop editing when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    start = input('Start editing [Y/n]: ').lower()
    if start not in ['y', 'yes', '']:
        exit()

    changeset = None
    n_changeset = 0
    n_edits = 0
    total_edits = 0
    try:
        for osm_object in tqdm(result.nodes + result.ways + result.relations):
            if not dry_run:
                lt.print_changeset_status(changeset=changeset, n_edits=n_edits, n_changeset=n_changeset, verbose=verbose)
            lt.print_osm_object(osm_object, verbose=verbose)
            tags = {}
            if 'wikidata' in osm_object.tags.keys() and osm_object.tags['wikidata'] in db.keys():
                links = db[osm_object.tags['wikidata']]
                if links['id'] != osm_object.tags['wikidata']:
                    print(f"Wikidata points to a redirected item. Updating wikidata tag {osm_object.tags['wikidata']} -> {links['id']}")
                    tags['wikidata'] = links['id']
                for language, value in links['sitelinks'].items():
                    if language == lang:
                        tags['wikipedia'] = f'{language}:{value}'
                    elif all_langs:
                        tags[f'wikipedia:{language}'] = value
            if tags:
                if not dry_run:
                    if changeset is None:
                        n_changeset = n_changeset + 1
                        if batch and n_objects > batch and changeset_comment:  # TODO predict if more than 1 changeset will be used
                            changeset_tags.update({'comment': changeset_comment + f' (part {n_changeset})'})
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
            elif verbose > 1:
                print(Fore.BLUE + f'SKIP: object without "wikidata" tag linking to wikipedia pages.' + Style.RESET_ALL)

    finally:
        print('######################################################')
        if changeset and not dry_run:
            total_edits = total_edits + n_edits
            print(f'DONE! {total_edits} objects modified from {n_objects_with_wikipedia}'
                  f' objects with available translations ({round(total_edits / n_objects_with_wikipedia * 100)}%)'
                  f' https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
