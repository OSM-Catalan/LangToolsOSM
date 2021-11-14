# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "LangToolsOSM"
VERSION = "0.0.2"



REQUIRES = [
    "click",
    "colorama",
    "osmapi",
    "requests",
    "overpy",
    "tqdm"
]

setup(
    name=NAME,
    version=VERSION,
    description="CLI tool ",
    author_email="joanmaspons@gmail.com",
    url="https://github.com/OSM-Catalan/LangToolsOSM",
    keywords=["OpenStreetMap", "localisation"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={},
    include_package_data=True,
    entry_points={
        'console_scripts': ['fill_empty_name=fill_empty_name.cli:fill_empty_namecommand',
                            'fill_empty_name_lang=fill_empty_name_lang.cli:fill_empty_name_langcommand',
                            'regex_name_lang=regex_name_lang.cli:regex_name_langcommand',
                            'translate_with_wikidata=translate_with_wikidata.cli:translate_with_wikidatacommand']},
    long_description="CLI tool to help with localisation of OpenStreet. Edit name:LANG and name."
)

