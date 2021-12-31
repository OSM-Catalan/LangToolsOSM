# coding: utf-8

from setuptools import setup, find_packages

NAME = 'LangToolsOSM'
VERSION = '0.0.12'

REQUIRES = [
    'click',
    'colorama',
    'osmapi',
    'overpy',
    'pandas',
    'pytablereader',
    'pytablewriter',
    'requests',
    'tqdm'
]

setup(
    name=NAME,
    version=VERSION,
    description='CLI tools to help with localisation of multilingual names and completion of wikidata and wikipedia tags in OpenStreetMap',
    author='Joan Maspons',
    author_email='joanmaspons@gmail.com',
    license='GPL3+',
    url='https://github.com/OSM-Catalan/LangToolsOSM',
    keywords=['OpenStreetMap', 'localisation', 'wikidata', 'wikipedia'],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={},
    include_package_data=True,
    entry_points={
        'console_scripts': ['fill_empty_name=src.fill_empty_name:fill_empty_namecommand',
                            'fill_empty_name_lang=src.fill_empty_name_lang:fill_empty_name_langcommand',
                            'regex_name_lang=src.regex_name_lang:regex_name_langcommand',
                            'translate_with_wikidata=src.translate_with_wikidata:translate_with_wikidatacommand',
                            'update_osm_objects_from_report=src.update_osm_objects_from_report:update_osm_objects_from_reportcommand',
                            'write_osm_objects_report=src.write_osm_objects_report:write_osm_objects_reportcommand',
                            'fill_wikidata_from_wikipedia=src.fill_wikidata_from_wikipedia:fill_wikidata_from_wikipediacommand',
                            'fill_wikipedia_from_wikidata=src.fill_wikipedia_from_wikidata:fill_wikipedia_from_wikidatacommand'
                            ]},
    long_description='Fill empty wikidata, wikipedia, name:LANG or name tags with translations from wikidata, regex, '
                     'or copy from name to name:LANG or the reverse. See '
                     'https://wiki.openstreetmap.org/wiki/Multilingual_names '
)
