import json
import re

def get_cache(html):
    data = html.css("body > script:nth-child(4)::text").get()
    start_index = re.search("window.__cache=", data).end()
    end_index = re.search('}};', data).end() - 1  # end index of dict
    cache = data[start_index:end_index]  # eg: 667:384807
    cache_data = json.loads(cache)  # convert json to dict=
    return cache_data

def calculate_weight(weight, weight_unit):
    # weight_unit: GRAM | KILOGRAM
    if weight_unit == 'KILOGRAM':
        weight *= 1000
    return weight

def parse_price(price_str):
    # eg Rp12.999.000 -> 12999000
    removed = price_str.replace('Rp', '').replace('.', '')
    if removed != "":
        return int(removed)
    return None

def parse_url(url):
    split = url.replace('https://www.tokopedia.com/', '').split('/')
    return split[0], split[1].split('?')[0] # shop_alias, prod_slug