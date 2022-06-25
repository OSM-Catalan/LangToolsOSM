import re
import requests


def get_translations(ids: list, lang: str, batch_size=50) -> dict:
    data = {}
    for ndx in range(0, len(ids), batch_size):
        batch_ids = ids[ndx:min(ndx + batch_size, len(ids))]
        query = 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=' + '|'.join(batch_ids) +\
                '&props=labels|aliases|sitelinks&languages=' + lang + '&format=json'
        response = requests.get(query)
        batch_data = response.json()
        if 'error' in batch_data.keys():
            raise Exception('Wrong response from wikidata: ' + batch_data)
        data.update(batch_data['entities'])
    # import json
    # print(json.dumps(data, indent=2))
    out = {}
    for wikidata_id, value in data.items():
        translations = {'wikipedia': None, 'label': None, 'aliases': None, 'extra': None}
        if 'sitelinks' in value.keys() and lang + 'wiki' in value['sitelinks'].keys():
            translations['wikipedia'] = value['sitelinks'][lang + 'wiki']
        if 'labels' in value.keys() and lang in value['labels'].keys():
            translations['label'] = value['labels'][lang]
        if 'aliases' in value.keys() and lang in value['aliases'].keys():
            translations['aliases'] = value['aliases'][lang]

        if not translations['label'] and not translations['aliases'] and not translations['wikipedia']:
            translations = None
        else:  # Generate new translation options
            extra_translations = list_translations(translations)
            # Remove brackets and the text inside
            pattern = re.compile(r'\s*\(.+\)\s*')
            for i in extra_translations:
                if pattern.search(i):
                    if not translations['extra']:
                        translations['extra'] = []
                        translations_extra = []
                    if pattern.sub('', i) not in translations_extra:
                        translations_extra.append(pattern.sub('', i))
                        translations['extra'].append({'lang': lang, 'value': pattern.sub('', i), 'modifier': 'rm brackets'})

            extra_translations = list_translations(translations)
            # Capitalize all words
            for i in extra_translations:
                if not i.title() == i:
                    if not translations['extra']:
                        translations['extra'] = []
                        translations_extra = []
                    if i.title() not in translations_extra:
                        translations_extra.append(i.title())
                        translations['extra'].append({'lang': lang, 'value': i.title(), 'modifier': 'capitalize'})

        out.update({wikidata_id: {'translations': translations}})
    return out


def list_translations(translations: dict) -> list:
    translations_list = []
    if translations:
        if translations['wikipedia']:
            translations_list = translations_list + [translations['wikipedia']['title']]
        if translations['label']:
            translations_list = translations_list + [translations['label']['value']]
        if translations['aliases']:
            translations_list = translations_list + [x['value'] for x in translations['aliases']]
        if translations['extra']:
            translations_list = translations_list + [x['value'] for x in translations['extra']]
    return list(dict.fromkeys(translations_list).keys())


def get_wikidata_from_wikipedia(wikipedia: list) -> dict:
    db = {}
    pattern_lang = re.compile(r'^([a-z]+):.+')
    pattern_title = re.compile(r'^[a-z]+:(.+)')
    for i in wikipedia:
        try:
            lang = pattern_lang.search(string=i).group(1)
            title = pattern_title.search(string=i).group(1)
        except AttributeError:
            lang = None
            title = None
        if lang:
            if lang not in db.keys():
                db.update({lang: {title}})
            else:
                db[lang].add(title)
    out = {}
    for lang, titles in db.items():
        wikidict = get_wikidata_from_langwikipedia(sitelinks=list(titles), lang=lang)
        out.update(dict((lang + ':' + key, value) for (key, value) in wikidict.items()))
    return out


def get_wikidata_from_langwikipedia(sitelinks: list, lang: str, batch_size=50) -> dict:
    data = {}
    for ndx in range(0, len(sitelinks), batch_size):
        batch_sitelinks = sitelinks[ndx:min(ndx + batch_size, len(sitelinks))]
        query = 'https://' + lang + '.wikipedia.org/w/api.php?action=query&prop=pageprops&ppprop=wikibase_item&' + \
                'redirects=1&format=json&utf8=True&titles=' + '|'.join(batch_sitelinks)
        response = requests.get(query)
        batch_data = response.json()
        if 'error' in batch_data.keys():
            raise Exception('Wrong response from wikidata: ' + batch_data)
        data.update(batch_data['query']['pages'])
    # import json
    # print(json.dumps(data, indent=2))

    out = {}
    for value in data.values():
        dict_item = {value['title']: None}
        if 'pageprops' in value.keys() and value['pageprops']['wikibase_item']:
            dict_item[value['title']] = value['pageprops']['wikibase_item']
        out.update(dict_item)
    return out


def get_wikipedia_from_wikidata(wikidata: list, batch_size=50) -> dict:
    data = {}
    for ndx in range(0, len(wikidata), batch_size):
        batch_ids = wikidata[ndx:min(ndx + batch_size, len(wikidata))]
        query = 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=' + '|'.join(batch_ids) +\
                '&props=sitelinks&format=json'
        response = requests.get(query)
        batch_data = response.json()
        if 'error' in batch_data.keys():
            raise Exception('Wrong response from wikidata: ' + batch_data)
        data.update(batch_data['entities'])
    # import json
    # print(json.dumps(data, indent=2))
    out = {}
    for wikidata_id, value in data.items():
        if 'sitelinks' in value.keys():
            sitelinks = {}
            for sitelink in value["sitelinks"].keys():
                if sitelink.endswith("wiki") and sitelink != "commonswiki":
                    sitelinks.update({sitelink.replace("wiki", ""): value["sitelinks"][sitelink]["title"]})
            if len(sitelinks) > 0:
                out.update({wikidata_id: {'id': value['id'], 'sitelinks': sitelinks}})
    return out


def get_instance_type_from_wikidata(wikidata: list, batch_size=50) -> dict:
    id_instance_type = {}  # P31 (instance of) ids of the wikidata elements
    for ndx in range(0, len(wikidata), batch_size):
        batch_ids = wikidata[ndx:min(ndx + batch_size, len(wikidata))]
        query = 'https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims&languages=en|ca&ids=' + '|'.join(batch_ids)
        response = requests.get(query)
        batch_data = response.json()
        if 'error' in batch_data.keys():
            raise Exception('Wrong response from wikidata: ' + str(batch_data))
        for key, val in batch_data['entities'].items():
            if 'claims' in val.keys() and 'P31' in val['claims'].keys():
                id_P31 = [P31['mainsnak']['datavalue']['value']['id'] for P31 in val['claims']['P31']]
                id_instance_type.update({key: {'P31': id_P31}})
    id_instance_type_unique = list(set(sum([x['P31'] for x in id_instance_type.values()], [])))

    instance_type = {}  # Labels of the P31 ids
    for ndx in range(0, len(id_instance_type_unique), batch_size):
        batch_ids = id_instance_type_unique[ndx:min(ndx + batch_size, len(id_instance_type_unique))]
        query = 'https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=labels&languages=en|ca&ids=' + '|'.join(batch_ids)
        response = requests.get(query)
        batch_data = response.json()
        if 'error' in batch_data.keys():
            raise Exception('Wrong response from wikidata: ' + str(batch_data))
        for key, val in batch_data['entities'].items():
            if 'labels' in val.keys() and 'en' in val['labels'].keys():
                instance_type.update({key: val['labels']['en']['value']})

    out = {}  # Labels of the P31 values of the wikidata elements
    for wikidata_id, types in id_instance_type.items():
        for P31 in types['P31']:
            if P31 in instance_type.keys():
                type_names = [instance_type[P31]]
                out.update({wikidata_id: type_names})

    return out

