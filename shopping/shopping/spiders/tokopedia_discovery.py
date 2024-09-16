import math
import re

from ..utils import get_cache
import scrapy

# cookies
# _abck=69423C84F30D0A8EB37ACE1DC97107DF~-1~YAAQxjLdF0U+fbyRAQAAVNXDwAyZOvub8gSqYfuAMUdS/jreZtgDTt3hQAWeJuKbw2/ES1vP9/Y4VreuYe9X5da91HJ7PQNyoOsEdK8/7f3pzPk5YzDCzplhcJ8MLiErZ1sGVOHZBTiN/MDXWBb0b+QhzNPOr4SdMdk/y9xX9aCzG63wwGQxrHWNj2G4E9SkRGT5mS7amgrfOJr1mQGWlebrHrOCgg+vsZi6piVSTwu1ghRIgd4BvBk78xXWGAXVPWlnwbNR0Eug1ZRbMwOvNlJyIf8pe6G+UgDT/bdNGr7dNpniiRoAEuVeRc79Fmgq0eFXpwBSRXhMS6xKBtCU3af86++kG9PkaiCkQRHeXeqR6iBhfCY/OVBNn7CO2S6LSojJLFRQd8TNFR9aBPkkUY2tzL5i3DPpL1W+LlnqFemZKdZFYyltHiv+VIABxKAE2kS15iLC3hOudimnJiOuRPnAHKXhRtM=~0~-1~-1; Path=/; Domain=tokopedia.com; Secure; Expires=Fri, 05 Sep 2025 05:59:05 GMT;

"""
TOKOPEDIA DISCOVERY SCRAPER ALGORITHM

INPUTS:
MAX
Category ID (subcat)

Scrape(a, b) {
	fetch page=1&pmin=a&pmax=b
	runScrape = True
	IF pages > 100:
		IF b == 0:			WARN "max not big enough"
			// still scrape but till 100
		ELSE
			runScrape = False
			Scrape(a, mid)
			Scrape(mid, b)
	ELSE
		... run scraping across pages until 100 ...

Scrape(0, MAX) // 0-MAX
Scrape(Max, 0) // MAX-inf
"""

PRODUCTS_PER_PAGE = 60
MAX_PAGE_SEARCH = 100

class TokopediaDiscovery(scrapy.Spider):
    name = "tokopedia_discovery"
    MAX = 10000000 # default

    custom_settings = {
        'ITEM_PIPELINES': {
            "shopping.pipelines.DuplicatesUrlPipeline": 301
        }
    }
    
    def make_url(self, category_slug, page=1, pmin='', pmax=''):
        return f"https://www.tokopedia.com/p/{category_slug}?page={page}&pmin={pmin}&pmax={pmax}"

    def start_requests(self):
        with open(self.categories) as f:
            categories = f.read().split('\n')
        urls = []

        for c in categories:
            urls.extend([
                self.make_url(category_slug=c, page=1, pmin=0, pmax=self.MAX),# 0-MAX
                self.make_url(category_slug=c, page=1, pmin=self.MAX, pmax=""),# MAX-inf
            ])

        for i, url in enumerate(urls):
            slug = categories[i // 2]
            yield scrapy.Request(url=url, callback=self.parse, meta={"cookiejar": i, "category_slug": slug})

    def parse(self, response):
        # parse a search result
        page = int(response.url.split("?")[1].split("&")[0].replace('page=', ''))
        pmin = response.url.split("&")[1].replace('pmin=', '')
        pmax = response.url.split("&")[2].replace('pmax=', '') or 0

        pmin = int(pmin)
        pmax = int(pmax)
        product_count = response.css('.css-1dq1dix')[0].css('div div div strong::text')
        if len(list(product_count)) == 0:
            # no product found done
            return
        product_count = int(str(product_count[-1]))
        page_count = math.ceil(product_count / PRODUCTS_PER_PAGE)

        if page == 1:
            # run checks first!
            if page_count > MAX_PAGE_SEARCH:
                if pmax == 0:
                    print(f"WARN: MAX value of {self.MAX} is not big enough")
                else:
                    mid = (pmax + pmin) // 2
                    url1 = self.make_url(category_slug=response.meta["category_slug"], page=1, pmin=pmin, pmax=mid) # pmin to mid
                    url2 = self.make_url(category_slug=response.meta["category_slug"], page=1, pmin=mid+1, pmax=pmax) # mid+1 to pmax
                    yield scrapy.Request(url=url1, callback=self.parse, meta={"cookiejar": response.meta['cookiejar'], "category_slug": response.meta["category_slug"]})
                    yield scrapy.Request(url=url2, callback=self.parse, meta={"cookiejar": response.meta['cookiejar'], "category_slug": response.meta["category_slug"]})
                    return # stop

        
        # run scraping for all products!
        cache_data = get_cache(response)
        r_query = re.compile(r"^\$ROOT_QUERY\.searchProduct")
        query_key = list(filter(r_query.match, cache_data.keys()))[0]

        # get list of products
        products = cache_data[query_key]["products"]
        product_ids = [product["id"]
                       for product in products]  # get product ids
        
        for id in product_ids:
            product_url = cache_data[id]['url']
            yield {"url": product_url}
        
        # move to next page when page in limits
        if page < page_count:
            next_url = self.make_url(category_slug=response.meta["category_slug"], page=page+1, pmin=pmin, pmax=pmax)
            yield scrapy.Request(url=next_url, callback=self.parse, meta={"cookiejar": response.meta['cookiejar'], "category_slug": response.meta["category_slug"]})
