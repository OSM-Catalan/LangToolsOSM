import click
import lib.LangToolsOSM as lt
from lib import __version__
import re
from tqdm import tqdm


@click.command()
@click.option('--find', prompt='Regular expression to search at name tags', type=str, help='Regular expression to search at name tags.')
@click.option('--replace', prompt='Regular expression to replace object name and fill name:{LANG}', type=str, help='Regular expression to replace object name and fill name:{LANG}.')
@click.option('--area', prompt='Bounding box (South,West,North,East) or the exact name value of an area', type=str, help='Eg. "42.49,2.43,42.52,2.49" or "Le Canigou".')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', default=False, is_flag=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def regex_name_langcommand(find, replace, area, dry_run, lang, username, verbose):
    """Look for features with «name» matching a regular expression and fill «name:LANG» with a modified version of «name» by a regular expression."""
    if not dry_run:
        api = lt.login_OSM(username=username)
    changeset_tags = {u"comment": f"Fill empty name:{lang} tags with regex name:«" +
                                  find + f"» -> name:{lang}=«" + replace + "».",
                      u"source": u"name tag", u"created_by=": f"LangToolsOSM {__version__}"}
    if verbose:
        print(changeset_tags)
    result = lt.get_overpass_result(area=area, filters=f'nwr["name"~"{find}"][!"name:{lang}"]')
    regex = re.compile(find, )
    changeset = None
    for rn in tqdm(result.nodes):
        if "name" in rn.tags:
            tags = {}
            tags["name:" + lang] = regex.sub(replace, rn.tags["name"])

            if tags:
                lt.print_element(rn, verbose=verbose)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    lt.update_element(element=rn, tags=tags, api=api)

    for rw in tqdm(result.ways):
        if "name" in rw.tags:
            tags = {}
            tags["name:" + lang] = regex.sub(replace, rw.tags["name"])

            if tags:
                lt.print_element(rw, verbose=verbose)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    lt.update_element(element=rw, tags=tags, api=api)

    for rr in tqdm(result.relations):
        if "name:" in rr.tags:
            tags = {}
            tags["name:" + lang] = regex.sub(replace, rr.tags["name"])

            if tags:
                lt.print_element(rr, verbose=verbose)
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    lt.update_element(element=rr, tags=tags, api=api)

    if changeset and not dry_run:
        api.ChangesetClose()
