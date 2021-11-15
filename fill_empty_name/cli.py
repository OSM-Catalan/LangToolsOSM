import click
import lib.LangToolsOSM as lt
from tqdm import tqdm


@click.command()
@click.option("--verbose", default=False, is_flag=True)
@click.option("--dry-run", default=False, is_flag=True)
def fill_empty_namecommand(verbose, dry_run):
    if not dry_run:
        api = lt.login_OSM()
    area = input("Bounding box(South,West,North,East) or name value: ")
    lang = input("Name language to add (e.g. ca, en, ...): ") or "ca"
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
