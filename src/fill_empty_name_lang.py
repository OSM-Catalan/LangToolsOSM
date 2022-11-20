import click
from colorama import Fore, Style
import lib.osm_utils as lt
from lib import __version__
from tqdm import tqdm


@click.command()
@click.option('--area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou"). Ignored if query is present.')
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--changeset-comment', type=str, help='Comment for the changeset.')
@click.option('--changeset-hashtags', type=str, help='#hashtags for the changeset. Semicolon delimited (e.g. "#toponimsCat;#Calle-Carrer").')
@click.option('--changeset-source', default='name tag', type=str, help='Source tags for the changeset.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name'][~'name:[a-z]+'~'.'][!'name:{lang}']". Ignored if query is present.""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--passwordfile', default=None, type=str, help='Path to a passwordfile, where on the first line username and password must be colon-separated (:). If provided, username option is ignored.')
@click.option('--query', type=str, help="""Overpass query to search for objects.""")
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def fill_empty_name_langcommand(area, batch, changeset_comment, changeset_hashtags, changeset_source, dry_run, filters, lang, passwordfile, query, username, verbose):
    """Looks for features with «name» & without «name:LANG» tags and copy «name» value to «name:LANG»."""
    if not dry_run:
        api = lt.login_osm(username=username, passwordfile=passwordfile)
    if not filters:
        filters = f"nwr['name'][~'name:[a-z]+'~'.'][!'name:{lang}']"
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Fill empty name:{lang} tags with name in {area} for {filters}',
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
    print(str(len(result.nodes)) + ' nodes, ' + str(len(result.ways)) + ' ways and ' + str(len(result.relations)) + ' relations found.')
    print('######################################################')
    if n_objects > 200 and ((batch is not None and batch > 200) or batch is None):
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
                         'Reduce the area, add batch option < 200 or stop translating when you want by pressing Ctrl+c.' + Style.RESET_ALL)
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
            if 'name' in osm_object.tags.keys():
                tags = {'name:' + lang: osm_object.tags['name']}
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
            else:
                print(Fore.BLUE + 'SKIP: object without "name" tag.' + Style.RESET_ALL)

    finally:
        if changeset and not dry_run:
            total_edits = total_edits + n_edits
            print(f'DONE! {total_edits} objects modified https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
