import click
from colorama import Fore, Style
import lib.osm_utils as lt
from lib import __version__
import re
from tqdm import tqdm


@click.command()
@click.option('--find', prompt='Regular expression to search at name tags', type=str, help='Regular expression to search at name tags.')
@click.option('--replace', prompt='Regular expression to replace object name and fill name:{LANG}', type=str, help='Regular expression to replace object name and fill name:{LANG}.')
@click.option('--area', prompt='Bounding box (South,West,North,East), filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name'~'{find}'][!'name:{lang}']".""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def regex_name_langcommand(find, replace, area, batch, dry_run, filters, lang, username, verbose):
    """Look for features with «name» matching a regular expression and fill «name:LANG» with a modified version of «name» by a regular expression."""
    if not dry_run:
        api = lt.login_osm(username=username)
    if not filters:
        filters = f"nwr['name'~'{find}'][!'name:{lang}']"
    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Fill empty name:{lang} tags with regex name:«' +
                                  find + f'» -> name:{lang}=«' + replace + f'»  in {area} for {filters}',
                      u'source': u'name tag', u'created_by': f'LangToolsOSM {__version__}'}
    print(changeset_tags)
    result = lt.get_overpass_result(area=area, filters=filters)
    n_objects = len(result.nodes) + len(result.ways) + len(result.relations)
    print('######################################################')
    print(str(len(result.nodes)) + ' nodes, ' + str(len(result.ways)) + ' ways and ' + str(len(result.relations)) + ' relations found.')
    print('######################################################')
    if n_objects > 200 and batch is not None and batch > 200:
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
              'Reduce the area, add batch option < 200 or stop translating when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    regex = re.compile(find, )
    changeset = None
    n_edits = 0
    total_edits = 0
    try:
        for osm_object in tqdm(result.nodes + result.ways + result.relations):
            if 'name' in osm_object.tags:
                tags = {'name:' + lang: regex.sub(replace, osm_object.tags['name'])}

                if tags:
                    if not dry_run:
                        lt.print_changeset_status(changeset=changeset, n_edits=n_edits, verbose=verbose)
                    lt.print_osm_object(osm_object, verbose=verbose)
                    if changeset is None and not dry_run:
                        changeset = api.ChangesetCreate(changeset_tags)

                    if not dry_run:
                        committed = lt.update_osm_object(osm_object=osm_object, tags=tags, api=api)
                        if committed:
                            n_edits = n_edits + 1
                        if batch and n_edits > batch:
                            print(f'{n_edits} edits DONE! https://www.osm.org/changeset/{changeset}. Opening a new changeset.')
                            total_edits = total_edits + n_edits
                            api.ChangesetClose()
                            changeset = None
                            n_edits = 0
                    else:
                        print(Fore.GREEN + Style.BRIGHT + '\n+ ' + str(tags) + Style.RESET_ALL)

    finally:
        if changeset and not dry_run:
            if not batch:
                total_edits = n_edits
            print(f'DONE! {total_edits} objects modified https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
