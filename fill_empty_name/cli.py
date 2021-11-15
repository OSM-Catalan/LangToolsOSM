import click
import lib.LangToolsOSM as lt
from tqdm import tqdm


@click.command()
@click.option('--area', prompt='Bounding box (South,West,North,East) or the exact name value of an area', type=str, help='Eg. "42.49,2.43,42.52,2.49" or "Le Canigou".')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--lang', prompt='Language to add a multilingual name key (e.g. ca, en, ...)', type=str, help='A language ISO 639-1 Code. See https://wiki.openstreetmap.org/wiki/Multilingual_names .')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', default=False, is_flag=True, help='Print the changeset tags and all the tags of the features that you are currently editing.')
def fill_empty_namecommand(area, dry_run, lang, username, verbose):
    """Looks for features with «name:LANG» & without «name» tags and copy «name:LANG» value to «name»."""
    if not dry_run:
        api = lt.login_OSM(username=username)
    changeset_tags = {u"comment": f"Fill empty name tags with name:{lang}", u"source": f"name:{lang} tag"}
    if verbose:
        print(changeset_tags)

    result = lt.get_overpass_result(area=area, filters=f'nwr["name:{lang}"][!"name"]')
    changeset = None
    for rn in tqdm(result.nodes):
        if f"name:{lang}" in rn.tags:
            tags = {}
            lt.print_element(rn, verbose=verbose)
            tags["name"] = rn.tags["name:" + lang]
            if tags:
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    lt.update_element(element=rn, tags=tags, api=api)

    for rw in tqdm(result.ways):
        if f"name:{lang}" in rw.tags:
            tags = {}
            lt.print_element(rw, verbose=verbose)
            tags["name"] = rw.tags["name:" + lang]
            if tags:
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    lt.update_element(element=rw, tags=tags, api=api)

    for rr in tqdm(result.relations):
        if f"name:{lang}" in rr.tags:
            tags = {}
            lt.print_element(rr, verbose=verbose)
            tags["name"] = rr.tags["name:" + lang]
            if tags:
                if changeset is None and not dry_run:
                    api.ChangesetCreate(changeset_tags)
                    changeset = True

                if not dry_run:
                    lt.update_element(element=rr, tags=tags, api=api)

    if changeset and not dry_run:
        api.ChangesetClose()
