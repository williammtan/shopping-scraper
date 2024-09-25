import scrapy
import os

from scrapy_redis.spiders import RedisSpider

URL = "https://www.blibli.com/categories"

class BlibliCategories(RedisSpider):
    name = "blibli_categories"
    # start_urls = [https://storage.cloud.google.com/shopping-scraper-outputs/public/blibli_categories/{subcat}.html]


    def parse(self, response):

        categories = response.css('.categories')
        
        # Find the deepest category links within the selected elements
        for category in categories:
            # Recursively select the deepest links by identifying the most nested a tags
            deepest_links = category.css('a[class*="category__name-level-4"]::attr(href)').getall()

            for link in deepest_links:
                # Yielding the URLs of the deepest categories
                yield {
                    'url': response.urljoin(link),
                }

