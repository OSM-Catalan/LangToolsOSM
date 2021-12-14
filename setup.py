# coding: utf-8

from setuptools import setup, find_packages

NAME = 'LangToolsOSM'
VERSION = '0.0.10'

REQUIRES = [
    'click',
    'colorama',
    'osmapi',
    'overpy',
    'pytablewriter',
    'requests',
    'tqdm'
]

setup(
    name=NAME,
    version=VERSION,
    description='CLI tools to help with localisation of multilingual names in OpenStreetMap',
    author='Joan Maspons',
    author_email='joanmaspons@gmail.com',
    license='GPL3+',
    url='https://github.com/OSM-Catalan/LangToolsOSM',
    keywords=['OpenStreetMap', 'localisation'],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={},
    include_package_data=True,
    entry_points={
        'console_scripts': ['fill_empty_name=src.fill_empty_name:fill_empty_namecommand',
                            'fill_empty_name_lang=src.fill_empty_name_lang:fill_empty_name_langcommand',
                            'regex_name_lang=src.regex_name_lang:regex_name_langcommand',
                            'translate_with_wikidata=src.translate_with_wikidata:translate_with_wikidatacommand']},
    long_description='Fill empty name:LANG or name tags with translations from wikidata, regex, or copy from name to '
                     'name:LANG or the reverse. See https://wiki.openstreetmap.org/wiki/Multilingual_names'
)

