from urllib import parse
import time
from scrapy_undetectable_playwright.handler import PageMethod, Page
import scrapy

BASE_URL = "https://www.blibli.com/"
PRODUCTS_PER_PAGE = 8*5 # 8-9 lines per page
MAX_PAGE_SEARCH = 20
MAX_PRODUCT_ACCESS_TRIES = 3

def make_url(base_url, page, pmin, pmax):
    return f"{base_url}?page={page}&minPrice={pmin}&maxPrice={pmax}"

def extract_digits_from_string(string):
    if not string:
        return
    else:
        return int(''.join(filter(str.isdigit, string)))

class BlibliDiscovery(scrapy.Spider):
    name = "blibli_discovery_playwright"
    MAX = 10000000 # default

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_undetectable_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_undetectable_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled"]
        },
        "PLAYWRIGHT_MAX_CONTEXTS": 6,
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 6,
        'ITEM_PIPELINES': {
            "shopping.pipelines.DuplicatesUrlPipeline": 301
        },
    }

    def start_requests(self):
        with open(self.categories) as f:
            urls = f.read().split('\n')
    
        yield self.request(
            url="https://www.blibli.com/c3/aksesoris-komputer-lainnya/AK-1000006?sort=7&minPrice=0&maxPrice=100000000",
        ) # test multiplage >= 20
    
    def request(self, *args, **kwargs):
        return scrapy.Request(callback=self.parse, errback=self.close_context_on_error, meta=dict(
                playwright=True,
                playwright_include_page=True,
                playwright_page_methods=[
                    PageMethod("wait_for_selector", "#catalogProductListContentDiv")
                ]
            ), *args, **kwargs)
    
    async def parse(self, response):
        base_url = response.url.split('?')[0]
        url_params = parse.parse_qs(parse.urlparse(response.url).query)
        pmin = int((url_params.get('minPrice') or [0])[0])
        pmax = int((url_params.get('maxPrice') or [0])[0])
        # page_num = int((url_params.get('page') or [1])[0])

        page: Page = response.meta["playwright_page"]

        empty_state = await page.locator('.empty-state').all()
        if len(empty_state) > 0:
            # empty
            return

        await page.wait_for_selector(".product-count")
        product_count_element = await page.locator(".product-count").first.inner_text()
        product_count = extract_digits_from_string(product_count_element)
        
        if product_count <= 40:
            # one page, no pagination
            page_count = 1
        else:
            await page.wait_for_selector('.blu-pagination__button')
            pagination_elements = await page.locator('.blu-pagination__button').all_inner_texts()
            page_count = int([div for div in pagination_elements if div != "..."][-1])
    

        if page_count >= MAX_PAGE_SEARCH:
            if pmax == 0:
                print(f"WARN: MAX value of {self.MAX} is not big enough")
            else:
                mid = (pmax + pmin) // 2
                url1 = make_url(base_url, page=1, pmin=pmin, pmax=mid) # pmin to mid
                url2 = make_url(base_url, page=1, pmin=mid+1, pmax=pmax) # mid+1 to pmax
                await page.close()
                time.sleep(1)
                yield self.request(url=url1)
                yield self.request(url=url2)
                # yield self.request(url="https://www.blibli.com/c3/aksesoris-komputer-lainnya/AK-1000006?sort=7&minPrice=129000000000", callback=self.parse)
                return # stop
            
        while True:

            await page.wait_for_selector(".product-count")

            product_url_elements = await page.locator('.product-card a').all()
            products_urls = [await p.get_attribute("href") for p in product_url_elements]

            for product_url in products_urls:
                yield {"url": product_url}

            await page.wait_for_selector('.blu-pagination__button-nav')
            next_page_button = await page.locator('.blu-pagination__button-nav').all()
            next_page_button = next_page_button[-1]
            await next_page_button.scroll_into_view_if_needed()
            
            if await next_page_button.is_enabled():
                await next_page_button.click()
            else:
                break
        await page.close()
    
    async def close_context_on_error(self, failure):
        page = failure.request.meta["playwright_page"]
        screenshot = await page.screenshot(path="example.png", full_page=True)
        await page.close()
        await page.context.close()
        

        
    
        

    

    


