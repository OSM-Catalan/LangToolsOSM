import click
import osmapi
import pandas as pd
import pytablereader
from colorama import Fore, Style
from tqdm import tqdm

import lib.osm_utils as lt
from lib import __version__

@click.command()
@click.argument('upload-tags', nargs=-1)
@click.option('--confirmed-edits', default=False, is_flag=True, help='Do not ask for confirmation for every object edition. Review carfully the input-file before using this option.')
@click.option('--confirm-overwrites', default=False, is_flag=True, help='Ask for confirmation for updates that overwrite any tag value.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--input-file', type=click.Path(dir_okay=False), help='Path of the file with the tags to update. You can generate a template with write_osm_objects_report.')
@click.option('--input-format', type=click.Choice(['csv', 'mediawiki'], case_sensitive=False), default='csv', help='Format of the input file.')
@click.option('--source', type=str, help='Source tag value for the changeset. Ignored in --dry-run mode.')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def update_osm_objects_from_reportcommand(confirmed_edits, confirm_overwrites, dry_run, input_file, input_format, source, upload_tags, username, verbose):
    """Upload changed tags from an edited report file to OSM. UPLOAD_TAGS must match column names in the input file.
    You can generate a report file with write_osm_objects_report."""
    upload_tags = list(upload_tags)
    if dry_run:
        api = osmapi.OsmApi()
    else:
        api = lt.login_osm(username=username)

    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Update tags {upload_tags}', u'created_by': f'LangToolsOSM {__version__}'}
    if source:
        changeset_tags.update({'source': source})
    print(changeset_tags)
    changeset = None

    if input_format == 'csv':
        data = pd.read_table(input_file, skiprows=1)
    elif input_format == 'mediawiki':
        loader = pytablereader.MediaWikiTableFileLoader(file_path=input_file)
        for table_data in loader.load():
            data = table_data.as_dataframe()
    else:
        raise ValueError('File format must be "csv" or "mediawiki".')

    n_objects = data.shape[0]
    print('######################################################')
    print(f'{n_objects} objects to edit.')
    print('######################################################')
    if not set(upload_tags).issubset(data.columns):
        print('File columns:')
        print(data.columns)
        print('Tags to upload:')
        print(upload_tags)
        raise ValueError('tags must include column names present in the input_file. Missing columns ' +
                         str(set(upload_tags).difference(data.columns)))
    if n_objects > 200:  # TODO: count tags with value
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
                         'Reduce the number of objects in the input file or stop when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    start = input('Start editing [Y/n]: ').lower()
    if start not in ['y', 'yes', '']:
        exit()

    n_edits = 0
    try:
        for row in tqdm(data.iterrows()):
            if not dry_run:
                lt.print_changeset_status(changeset=changeset, n_edits=n_edits, verbose=verbose)
            tags = row[1][upload_tags]
            tags = dict(tags.dropna())

            if row[1]['typeOSM'] == 'node':
                osm_object = api.NodeGet(row[1]['idOSM'])
                osm_object_data = {
                    'id': osm_object['id'],
                    'lat': osm_object['lat'],
                    'lon': osm_object['lon'],
                    'tag': osm_object['tag'],
                    'version': osm_object['version'],
                }
            elif row[1]['typeOSM'] == 'way':
                osm_object = api.WayGet(row[1]['idOSM'])
                osm_object_data = {
                    'id': osm_object['id'],
                    'nd': osm_object['nd'],
                    'tag': osm_object['tag'],
                    'version': osm_object['version'],
                }
            elif row[1]['typeOSM'] == 'relation':
                osm_object = api.RelationGet(row[1]['idOSM'])
                osm_object_data = {
                    'id': osm_object['id'],
                    'member': osm_object['member'],
                    'tag': osm_object['tag'],
                    'version': osm_object['version'],
                }
            lt.print_osm_object(osm_object, verbose=verbose)

            overwrite_keys = list(set.intersection(set(tags.keys()), set(osm_object_data['tag'].keys())))
            overwrite_tags = dict()
            if overwrite_keys:
                overwrite_keys.sort()
                overwrite_tags = {key: osm_object_data['tag'][key] for key in overwrite_keys}
                for key in list(overwrite_tags.keys()):
                    if overwrite_tags[key] == tags[key]:  # omit if the tag has the same value as the osm_object
                        overwrite_tags.pop(key)
                        tags.pop(key)
                if len(overwrite_tags) > 0:
                    print(Fore.RED + Style.BRIGHT + '- ' + str(overwrite_tags) + Style.RESET_ALL)
            if len(tags) == 0:
                if verbose > 0:
                    print(Fore.BLUE + 'SKIP: No tag updates.' + Style.RESET_ALL)
                continue

            if verbose > 0:
                print(Fore.GREEN + Style.BRIGHT + '+ ' + str(tags) + Style.RESET_ALL)

            if not confirmed_edits or (confirm_overwrites and len(overwrite_tags) > 0):
                allow_update = input('Update tags [Y/n]: ').lower()
                if allow_update not in ['y', 'yes', '']:
                    print(Fore.BLUE + 'SKIP.' + Style.RESET_ALL)
                    continue

            osm_object_data['tag'].update(tags)

            if not dry_run:
                if changeset is None:
                    changeset = api.ChangesetCreate(changeset_tags)
                if row[1]['typeOSM'] == "node":
                    committed = api.NodeUpdate(osm_object_data)
                elif row[1]['typeOSM'] == "way":
                    committed = api.WayUpdate(osm_object_data)
                elif row[1]['typeOSM'] == "relation":
                    committed = api.RelationUpdate(osm_object_data)
                if committed:
                    n_edits = n_edits + 1

    finally:
        print('######################################################')
        if changeset and not dry_run:
            print(f'DONE! {n_edits} objects modified from {n_objects} objects ({round(n_edits / n_objects * 100)}%)'
                  f' https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
