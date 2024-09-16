import scrapy
from scrapy.spidermiddlewares.httperror import HttpError

from urllib import parse

BASE_API_URL = "https://www.blibli.com/backend/search/products"
BASE_PRODUCT_URL = "https://www.blibli.com"

PRODUCTS_PER_PAGE = 8*5 # 8-9 lines per page
MAX_PAGE_SEARCH = 20

def extract_category(url):
    return url.split('/')[-1]

def make_url(category, pmin, pmax, page):
    start = (page-1)*40
    return BASE_API_URL + "?" + f"category={category}&minPrice={pmin}&maxPrice={pmax}&page={page}&start={start}"

class BlibliDiscovery(scrapy.Spider):
    name = "blibli_discovery"
    MAX = 10000000 # default
    browser = "chrome"

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_impersonate.ImpersonateDownloadHandler",
            "https": "scrapy_impersonate.ImpersonateDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        'ITEM_PIPELINES': {
            "shopping.pipelines.DuplicatesUrlPipeline": 301
        },
        "CONCURRENT_REQUESTS": 64
    }

    def start_requests(self):
        with open(self.categories) as f:
            urls = f.read().split('\n')
            # eg. https://www.blibli.com/c4/retro-game-arcade/RE-1000100

        for url in urls:
            category = extract_category(url)
            yield scrapy.Request(make_url(category, pmin=0, pmax=self.MAX, page=1), dont_filter=True, meta={"impersonate": self.browser}, errback=self.errback_httpbin)
            yield scrapy.Request(make_url(category, pmin=self.MAX, pmax="", page=1), dont_filter=True, meta={"impersonate": self.browser}, errback=self.errback_httpbin)


    
    def parse(self, response):
        url_params = parse.parse_qs(parse.urlparse(response.url).query)
        pmin = int((url_params.get('minPrice') or [0])[0])
        pmax = int((url_params.get('maxPrice') or [0])[0])
        page = int((url_params.get('page') or [0])[0])
        category = url_params.get('category')[0]

        data = response.json()["data"]

        total_product_count = data["paging"]["total_item"]
        if total_product_count > PRODUCTS_PER_PAGE*MAX_PAGE_SEARCH:
            # split into 2
            if pmax == 0:
                # make max 2x
                url = make_url(category, page=1, pmin=pmin*2, pmax="") 
                yield scrapy.Request(url=url, dont_filter=True, meta={"impersonate": self.browser}, errback=self.errback_httpbin)
                print(f"WARN: MAX value of {self.MAX} is not big enough, trying {pmin*2}")
            else:
                mid = (pmax + pmin) // 2
                url1 = make_url(category, page=1, pmin=pmin, pmax=mid) # pmin to mid
                url2 = make_url(category, page=1, pmin=mid+1, pmax=pmax) # mid+1 to pmax
                yield scrapy.Request(url=url1, dont_filter=True, meta={"impersonate": self.browser}, errback=self.errback_httpbin)
                yield scrapy.Request(url=url2, dont_filter=True, meta={"impersonate": self.browser}, errback=self.errback_httpbin)
                return

        products = data["products"]

        for prod in products:
            product_detail_api = f"https://www.blibli.com/backend/product-detail/products/{prod['formattedId']}/_summary?defaultItemSku={prod['itemSku']}"
            yield {"url": product_detail_api}
        
        total_page = data["paging"]["total_page"]
        if page < total_page:
            # run next page
            yield scrapy.Request(url=make_url(category, page=page+1, pmin=pmin, pmax=pmax), dont_filter=True, meta={"impersonate": self.browser}, errback=self.errback_httpbin)
    
    def errback_httpbin(self, failure):
        # log all failures

        if failure.check(HttpError):
            response = failure.value.response
            if response.status == 422:
                # no products returned
                return
        
        self.logger.error(repr(failure))
            
    