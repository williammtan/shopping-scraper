import scrapy
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.project import get_project_settings
from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str

from shopping.items import ProductItem

import os
GCS_BUCKET = os.environ.get('GCS_BUCKET')

class BlibliProducts(RedisSpider):
    name = 'blibli_products'

    redis_batch_size = get_project_settings()['REQUEST_CUE']
    max_idle_time = 7
    
    browser = "chrome"
    custom_settings = {
        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_impersonate.ImpersonateDownloadHandler",
            "https": "scrapy_impersonate.ImpersonateDownloadHandler",
        },
        'ITEM_PIPELINES': {
            "shopping.pipelines.DuplicatesUrlPipeline": 301,
            'scrapy_redis.pipelines.RedisPipeline': 500,
        },
        "CONCURRENT_REQUESTS": 64,
        "FEED_URI": f'gs://{GCS_BUCKET}/feeds/%(name)s/%(time)s.jl',
        "FEED_FORMAT": 'jsonlines'
    }

    def make_request_from_data(self, url):
        url = bytes_to_str(url, self.redis_encoding)
        return scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'scrape_variants': True, "impersonate": self.browser},
                errback=self.errback_httpbin
            )

    def parse(self, response):
        data = response.json()['data']

        item = ProductItem()

        item['name'] = data.get('name')
        item['options'] = []
        for option in data.get('options'):
            if option["selected"]:
                # do this item
                for attribute in option['attributes']:
                    item['options'].append({"key": attribute['name'], "value": attribute['value']})
            elif response.meta.get('scrape_variants'):
                # run requests to scrape variants
                yield scrapy.Request(
                    url=f"https://www.blibli.com/backend/product-detail/products/{option['id']}/_summary",
                    meta={"impersonate": self.browser},
                    errback=self.errback_httpbin
                )

        item['url'] = data.get('url')
        item['marketplace'] = "blibli"  # Hardcoded
        item['brand'] = data.get('brand')['name']
        if item['brand'] == "no brand":
            item['brand'] = None

        # Constructing category breadcrumb
        item['categories'] = [
            c["name"]
            for c in data.get('categories', [])
        ]
        item['category_breadcrumb'] = data['categories'][-1]['url']

        item['price'] = data.get('price', {}).get('offered')
        if item['price']:
            item['price'] = int(item['price'])
        item['strike_price'] = data.get('price', {}).get('listed')
        if item['strike_price']:
            item['strike_price'] = int(item['strike_price'])

        item['weight'] = data.get('weight')
        item['stock'] = data.get('stock')

        item['shop_name'] = data.get('merchant', {}).get('name')
        item['shop_domain'] = data.get('merchant', {}).get('url').replace('/merchant/', '')  # Assuming blibli.com as the shop domain

        # Extracting image URLs
        item['image_urls'] = [image.get('full') for image in data.get('images', [])]

        item['rating'] = data.get('review', {}).get('rating')
        item['review_count'] = data.get('review', {}).get('count', 0)
        item['view_count'] = data.get('statistics', {}).get('seen', 0)
        item['sale_count'] = data.get('statistics', {}).get('sold', 0)

        yield item
    
    def errback_httpbin(self, failure):
        # log all failures

        if failure.check(HttpError):
            response = failure.value.response
            if response.status == 422:
                # no products returned
                return
        
        self.logger.error(repr(failure))
