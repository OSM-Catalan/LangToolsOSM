import csv
import pytablewriter
import re
import requests


def get_translations_from_wikidata(ids, lang, batch_size=50) -> dict:
    data = {}
    for ndx in range(0, len(ids), batch_size):
        batch_ids = ids[ndx:min(ndx + batch_size, len(ids))]
        query = 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=' + '|'.join(batch_ids) +\
                '&props=labels|aliases&languages=' + lang + '&format=json'
        response = requests.get(query)
        batch_data = response.json()
        if 'error' in batch_data.keys():
            raise Exception('Wrong response from wikidata: ' + batch_data)
        data.update(batch_data['entities'])

    out = {}
    for wikidata_id, value in data.items():
        translations = {'label': None, 'aliases': None}
        if 'labels' in value.keys() and lang in value['labels'].keys():
            translations['label'] = value['labels'][lang]
        if 'aliases' in value.keys() and lang in value['aliases'].keys():
            translations['aliases'] = value['aliases'][lang]

        if not translations['label'] and not translations['aliases']:
            translations = None
        else:  # Generate new translation options
            extra_translations = list_translations(translations)
            # Remove brackets and the text inside
            pattern = re.compile(r'\s*\(.+\)\s*')
            for i in extra_translations:
                if pattern.search(i):
                    if not translations['aliases']:
                        translations['aliases'] = []
                    # first case without brackets as a first option
                    if 'value' in translations.keys():
                        translations['aliases'].append(translations['value'])
                    translations['label'] = {'lang': lang, 'value': pattern.sub('', i)}
            extra_translations = list_translations(translations)
            # Capitalize all words
            for i in extra_translations:
                if not i.title() == i:
                    if not translations['aliases']:
                        translations['aliases'] = []
                    translations['aliases'].append({'lang': lang, 'value': i.title()})

        out.update({wikidata_id: {'translations': translations}})
    return out


def list_translations(translations) -> list:
    if translations and translations['label']:
        translations_list = [translations['label']['value']]
    else:
        translations_list = []
    if translations and translations['aliases']:
        translations_list = translations_list + [x['value'] for x in translations['aliases']]
    return translations_list
