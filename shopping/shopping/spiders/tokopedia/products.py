import scrapy
from scrapy.utils.project import get_project_settings
from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str

from shopping.gql import BaseSpiderGQL, TokpedGQL
from shopping.items import ProductItem
from shopping.utils import parse_price, parse_url

class TokopediaProducts(BaseSpiderGQL, RedisSpider):
    name = 'tokopedia_products'
    query = 'shopping/queries/tokopedia_pdp_query.gql'

    redis_key = 'tokopedia_products:start_urls'
    redis_batch_size = get_project_settings()['REQUEST_CUE']
    max_idle_time = 7

    def next_requests(self):
        """Returns a request to be scheduled or none."""

        datas = self.fetch_data(self.redis_key, self.redis_batch_size)
        requests = []
        for url in datas:
            requests.append(self.make_request_from_data(url))
        
        if len(requests) > 0:
            # print(json.loads(self.gql.merge_requests(requests).body))
            yield self.gql.merge_requests(requests)
        
    
    def make_request_from_data(self, url):
        url = bytes_to_str(url, self.redis_encoding)
        shop_alias, product_alias = parse_url(url)

        return self.gql.request(
                callback=self.parse_split,
                headers={'x-tkpd-akamai': 'pdpGetData'},
                shopDomain=shop_alias, productKey=product_alias,
            )
        
    def parse(self, response):
        data = response['pdpGetLayout']
        if data is None:
            return

        def find_component(name):
            component = [comp for comp in data['components']
                         if comp['name'] == name]
            if len(component) != 0:
                return component[0]
            else:
                return None
        
        item = ProductItem()

        basic_info = data['basicInfo']
        product_content = find_component('product_content')
        product_media = find_component('product_media')
        variant_options = find_component('new_variant_options')

        item['url'] = basic_info.get('url')
        item['marketplace'] = 'tokopedia'  # Hardcoded for this example
        item['categories'] = [c['name'] for c in basic_info['category']['detail']]
        item['shop_name'] = basic_info.get('shopName')
        item['shop_domain'] = parse_url(basic_info.get('url'))[0]
        item['weight'] = basic_info.get('weight', '') + basic_info.get('weightUnit', '')

        # Extract common media images
        if product_media:
            media_data = product_media['data'][0].get('media', [])
            item['image_urls'] = [media['urlOriginal'] for media in media_data if media['type'] == 'image']

        # Extract additional stats
        stats = basic_info.get('stats', {})
        tx_stats = basic_info.get('txStats', {})
        item['view_count'] = stats.get('countView', 0)
        item['review_count'] = stats.get('countReview', 0)
        item['rating'] = stats.get('rating', 0)
        item['sale_count'] = tx_stats.get('countSold', 0)

        # Get category breadcrumb
        item['category_breadcrumb'] = basic_info['category']["breadcrumbURL"].replace("https://www.tokopedia.com/p/", "")


        # Check if there are variants
        if variant_options:
            # Iterate over each variant and yield a ProductItem for each
            variants = variant_options['data'][0].get('children', [])
            for child in variants:
                child_item = item.copy()
                child_item['name'] = child.get('productName')
                child_item['price'] = child.get('price')
                child_item['strike_price'] = parse_price(child.get('slashPriceFmt'))
                child_item['stock'] = int(child['stock'].get('stock'))
                child_item['url'] = child.get('productURL')
                child_item['image_urls'] = [child['picture']['urlOriginal']]

                # Extract options for each variant
                child_item['options'] = {}
                product_variant_ids = child.get("optionID", [])
                child_item['options'] = {}
                # print(product_variant_ids)
                for variant_type in variant_options["data"][0].get('variants', []):
                    # print(variant_type)
                    for option in variant_type["option"]:
                        if int(option["productVariantOptionID"]) in product_variant_ids:
                            # yes
                            child_item["options"][variant_type["name"]] = option["value"]

                # Yield the item for each child variant
                yield child_item

        else:
            # If no variants, yield a single ProductItem using product_content
            content_data = product_content['data'][0]
            item = ProductItem()

            # Extract basic fields
            item['name'] = content_data.get('name')
            item['price'] = content_data['price'].get('value')
            item['strike_price'] = parse_price(content_data['price'].get('slashPriceFmt'))
            item['stock'] = int(content_data['stock'].get('value'))
            
            item['options'] = {}

            # Extract images
            if product_media:
                media_data = product_media['data'][0].get('media', [])
                item['image_urls'] = [media['urlOriginal'] for media in media_data if media['type'] == 'image']

            # Yield the single item
            yield item

    gql = TokpedGQL("PDPGetLayoutQuery", query=open(query).read(), 
    default_variables={
            # "shopDomain": "kiosmatraman",
            # "productKey": "susu-dyco-colostrum-isi-30-saset",
            "layoutID": "",
            "apiVersion": 1,
            "userLocation": {
                "addressID": "0",
                "districtID": "2274",
                "postalCode": "",
                "latlon": ""
            }
        }
    )


