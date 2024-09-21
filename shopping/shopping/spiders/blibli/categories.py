import scrapy
import os

URL = "https://www.blibli.com/categories"

class BlibliCategories(scrapy.Spider):
    name = "blibli_categories"
    start_urls = ["file://" + os.path.join(os.getcwd(), "blibli_categories.html")]

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

