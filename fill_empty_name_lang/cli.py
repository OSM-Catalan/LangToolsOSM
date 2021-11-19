import click
import lib.LangToolsOSM as lt
from lib import __version__
from tqdm import tqdm


@click.command()
@click.option('--area', prompt='Bounding box (South,West,North,East), filters or the exact name value of an area', type=str, help='Search area (eg. "42.49,2.43,42.52,2.49", "[name_int=Kobane]" or "Le Canigou").')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--filters', type=str, help="""Overpass filters to search for objects. Default to "nwr['name'][~'name:[a-z]+'~'.'][!'name:{lang}']""""")
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', default=False, is_flag=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def fill_empty_name_langcommand(area, dry_run, filters, lang, username, verbose):
    """Looks for features with «name» & without «name:LANG» tags and copy «name» value to «name:LANG»."""
    if not dry_run:
        api = lt.login_OSM(username=username)
    changeset_tags = {u"comment": f"Fill empty name:{lang} tags with name in {area} for {filters}",
                      u"source": u"name tag", u"created_by": f"LangToolsOSM {__version__}"}
    if verbose:
        print(changeset_tags)

    if not filters:
        filters = f"nwr['name'][~'name:[a-z]+'~'.'][!'name:{lang}']"
    result = lt.get_overpass_result(area=area, filters=filters)
    changeset = None
    n_edits = 0
    for rn in tqdm(result.nodes + result.ways + result.relations):
        if "name" in rn.tags:
            tags = {}
            tags["name:" + lang] = rn.tags["name"]

            if tags:
                if not dry_run:
                    print(f'Number of editions in the current changeset: {n_edits}')
                lt.print_element(rn, verbose=verbose)
                if changeset is None and not dry_run:
                    changeset_id = api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    committed = lt.update_element(element=rn, tags=tags, api=api)
                    if committed:
                        n_edits = n_edits + 1

    if changeset and not dry_run:
        print(f'DONE! {n_edits} objects modified https://www.osm.org/changeset/{changeset_id}')
        api.ChangesetClose()
    else:
        print('DONE! No change to OSM (--dry-run mode)')
