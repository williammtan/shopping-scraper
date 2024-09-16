import scrapy

from shopping.utils import get_cache

def get_cat_ids(categories_list):
    return [
        c["id"]
        for c in categories_list
    ]

class TokopediaCategories(scrapy.Spider):
    name = "tokopedia_categories"
    start_urls = [
        "https://www.tokopedia.com/p/komputer-laptop/aksesoris-pc-gaming/meja-gaming"
    ]



    def parse(self, response):
        cache_data = get_cache(response)
        root_cats = cache_data[[k for k in cache_data.keys() if '$ROOT_QUERY.categoryAllList' in k][0]]["categories"]
        root_cat_ids = get_cat_ids(root_cats)

        category_slugs = []
        
        def rec(obj):
            if "child" in obj:
                # recures
                for c in get_cat_ids(obj["child"]):
                    rec(cache_data[c])
            else:
                category_slugs.append(obj["url"].replace('https://www.tokopedia.com/p/', ''))

        for c in root_cat_ids:
            rec(cache_data[c])

        for slug in category_slugs:
            yield {"category_slug": slug}