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
@click.option('--batch', type=int, default=None, help='Upload changes in groups of "batch" edits per changeset. Ignored in --dry-run mode.')
@click.option('--changeset-comment', type=str, help='Comment for the changeset.')
@click.option('--changeset-hashtags', type=str, help='#hashtags for the changeset. Semicolon delimited (e.g. "#toponimsCat;#Calle-Carrer").')
@click.option('--changeset-source', type=str, help='Source tag value for the changeset.')
@click.option('--confirmed-edits', default=False, is_flag=True, help='Do not ask for confirmation for every object edition. Review carfully the input-file before using this option.')
@click.option('--confirm-overwrites', default=False, is_flag=True, help='Ask for confirmation for updates that overwrite any tag value.')
@click.option('--dry-run', default=False, is_flag=True, help='Run the program without saving any change to OSM. Useful for testing. No login required.')
@click.option('--input-file', type=click.Path(dir_okay=False), help='Path of the file with the tags to update. You can generate a template with write_osm_objects_report.')
@click.option('--input-format', type=click.Choice(['csv', 'mediawiki'], case_sensitive=False), default='csv', help='Format of the input file.')
@click.option('--no-interaction', default=False, is_flag=True, help='Do not ask any interactive question.')
@click.option('--passwordfile', default=None, type=str, help='Path to a passwordfile, where on the first line username and password must be colon-separated (:). If provided, username option is ignored.')
@click.option('--username', type=str, help='OSM user name to login and commit changes. Ignored in --dry-run mode.')
@click.option('--verbose', '-v', count=True, help='Print all the tags of the features that you are currently editing.')
def update_osm_objects_from_reportcommand(batch, changeset_comment, changeset_hashtags, changeset_source, confirmed_edits, confirm_overwrites, dry_run, input_file, input_format, no_interaction, passwordfile, username, upload_tags, verbose):
    """Upload changed tags from an edited report file to OSM. UPLOAD_TAGS must match column names in the input file.
    You can generate a report file with write_osm_objects_report."""
    if upload_tags is None:
        print('DONE! No change send to OSM because no UPLOAD_TAGS selected.')
        print('See "update_osm_objects_from_report --help" for details.')
        exit()
    upload_tags = list(upload_tags)
    if dry_run:
        api = osmapi.OsmApi()
    else:
        api = lt.login_osm(username=username, passwordfile=passwordfile)

    print('After the first object edition a changeset with the following tags will be created:')
    changeset_tags = {u'comment': f'Update tags {upload_tags}', u'created_by': f'LangToolsOSM {__version__}'}
    if changeset_comment:
        changeset_tags.update({'comment': changeset_comment})
    if changeset_hashtags:
        changeset_tags.update({'hashtags': changeset_hashtags})
    if changeset_source:
        changeset_tags.update({'source': changeset_source})
    print(changeset_tags)

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
    if n_objects > 200 and batch is not None and batch > 200:  # TODO: count tags with value
        print(Fore.RED + 'Changesets with more than 200 modifications are considered mass modifications in OSMCha.\n'
                         'Reduce the number of objects in the input file, add batch option < 200 or stop when you want by pressing Ctrl+c.' + Style.RESET_ALL)
    if no_interaction:
        start = 'yes'
    else:
        start = input('Start editing [Y/n]: ').lower()
    if start not in ['y', 'yes', '']:
        exit()

    changeset = None
    n_edits = 0
    total_edits = 0
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

            if no_interaction and len(overwrite_tags) > 0:
                print(Fore.RED + 'SKIP overwrites in no-interaction mode.' + Style.RESET_ALL)
                continue

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
                if batch and n_edits >= batch:
                    print(f'{n_edits} edits DONE! https://www.osm.org/changeset/{changeset}. Opening a new changeset.')
                    total_edits = total_edits + n_edits
                    api.ChangesetClose()
                    changeset = None
                    n_edits = 0

    finally:
        print('######################################################')
        if changeset and not dry_run:
            total_edits = total_edits + n_edits
            print(f'DONE! {total_edits} objects modified from {n_objects} objects ({round(total_edits / n_objects * 100)}%)'
                  f' https://www.osm.org/changeset/{changeset}')
            api.ChangesetClose()
        elif dry_run:
            print('DONE! No change send to OSM (--dry-run).')
        else:
            print('DONE! No change send to OSM.')
