from scrapy_playwright.page import PageMethod
import scrapy

URL = "https://www.blibli.com/categories"

class BlibliCategories(scrapy.Spider):
    name = "blibli_categories"
    start_urls = ["file:///Users/williamtan/Projects/shopping-scraper/shopping/blibli_categories.html"]
    # custom_settings = {
    #     "DOWNLOAD_HANDLERS": {
    #         "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    #         "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    #     },
    #     "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    #     "PLAYWRIGHT_LAUNCH_OPTIONS": {
    #         "headless": False,
    #     } 
    # }

    # def start_requests(self):
    #     yield scrapy.Request(url=URL, callback=self.parse, meta=dict(
	# 			playwright = True,
	# 			# playwright_include_page = True, 
	# 			playwright_page_methods =[PageMethod('wait_for_selector', '.categories')],
    #             cookiejar = 0
	# 		))

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

