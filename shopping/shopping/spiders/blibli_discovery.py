from urllib import parse
import time

from scrapy_selenium_ud.http import SeleniumRequestUc
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains
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
    name = "blibli_discovery"
    MAX = 10000000 # default

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_selenium_ud.SeleniumUcMiddleware": 500
            # "scrapy_selenium.SeleniumMiddleware": 800
        },
        'ITEM_PIPELINES': {
            # "shopping.pipelines.DuplicatesUrlPipeline": 301
        },
        "SPIDER_MIDDLEWARES": {"shopping.middlewares.TololMiddleware":200},
        "SELENIUM_DRIVER_ARGUMENTS": [],
        # "DOWNLOAD_HANDLERS": {
        #     "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        #     "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        # },
        # "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        #     "PLAYWRIGHT_LAUNCH_OPTIONS": {
        #     "headless": False,
        # } 
        "CONCURRENT_REQUESTS": 1,
        "REACTOR_THREADPOOL_MAXSIZE": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "CONCURRENT_REQUESTS_PER_IP": 1
    }

    def start_requests(self):
        with open(self.categories) as f:
            urls = f.read().split('\n')
        
        # yield SeleniumRequestUc(url="https://www.blibli.com/c3/aksesoris-komputer-lainnya/AK-1000006?sort=7&minPrice=129000000000", callback=self.parse) # test empty
        # yield SeleniumRequestUc(url="https://www.blibli.com/c3/aksesoris-komputer-laixwnnya/AK-1000006?sort=7&minPrice=129000000", callback=self.parse) # test one page
        # yield SeleniumRequestUc(url="https://www.blibli.com/c3/aksesoris-komputer-lainnya/AK-1000006?sort=7&minPrice=100000000", callback=self.parse) # test multiplage < 20
        yield SeleniumRequestUc(url="https://www.blibli.com/c3/aksesoris-komputer-lainnya/AK-1000006?sort=7&minPrice=0&maxPrice=100000000", callback=self.parse) # test multiplage >= 20
        # yield SeleniumRequestUc(url=make_url(urls[0], page=1, pmin=0, pmax=self.MAX), callback=self.parse)
        # yield scrapy.Request(url=make_url(urls[0], page=1, pmin=0, pmax=self.MAX), callback=self.parse, meta={"playwright": True, 'cookiejar': 0, 'playwright_page_methods': [PageMethod("wait_for_selector", "div.quote")]})

        # for i, url in enumerate(urls):
            # yield SeleniumRequestUc(url=make_url(url, page=1, pmin=0, pmax=self.MAX), callback=self.parse)
            # yield SeleniumRequestUc(url=make_url(url, page=1, pmin=self.MAX, pmax=""), callback=self.parse)
            # yield scrapy.Request(url=make_url(url, page=1, pmin=0, pmax=self.MAX), callback=self.parse, meta={"playwright": True, 'cookiejar': i})
            # yield scrapy.Request(url=make_url(url, page=1, pmin=self.MAX, pmax=""), callback=self.parse, meta={"playwright": True, 'cookiejar': i})
        
    def parse(self, response):
        """
        3 Types of pages;
            - empty: contains "empty-state" class
            - one page: no pagination
            - multiple: has pagination
        """
        print("parse: ", response.url)
        # parse current search result
        base_url = response.url.split('?')[0]
        url_params = parse.parse_qs(parse.urlparse(response.url).query)
        pmin = int((url_params.get('minPrice') or [0])[0])
        pmax = int((url_params.get('maxPrice') or [0])[0])

        driver = response.request.meta["driver"]
        wait = WebDriverWait(driver, timeout=10)

        # wait for main div to appear
        wait.until(EC.visibility_of_element_located((By.ID, "catalogProductListContentDiv")))

        # check if empty
        if len(driver.find_elements(By.CLASS_NAME, 'empty-state')) > 0:
            # empty
            return

        # get product count
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "product-count")))
        product_count = extract_digits_from_string(driver.find_element(By.CLASS_NAME, 'product-count').text)
        
        if product_count <= 40:
            # one page, no pagination
            page_count = 1
        else:
            # multipage, has pagination
            wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "blu-pagination__button")))
            page_count = int([div.text for div in driver.find_elements(By.CLASS_NAME, 'blu-pagination__button') if div.text != "..."][-1])
    
        if page_count >= MAX_PAGE_SEARCH:
            if pmax == 0:
                print(f"WARN: MAX value of {self.MAX} is not big enough")
            else:
                mid = (pmax + pmin) // 2
                url1 = make_url(base_url, page=1, pmin=pmin, pmax=mid) # pmin to mid
                url2 = make_url(base_url, page=1, pmin=mid+1, pmax=pmax) # mid+1 to pmax
                print(url1, url2)
                # yield SeleniumRequestUc(url=url1, callback=self.parse)
                yield SeleniumRequestUc(url=url2, callback=self.parse)
                yield SeleniumRequestUc(url="https://www.blibli.com/c3/aksesoris-komputer-lainnya/AK-1000006?sort=7&minPrice=129000000000", callback=self.parse)
                return # stop
        
        while True:
            # run for each webpage, for page > 1

            wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "product-list")))

            # tries = 0
            # while tries < MAX_PRODUCT_ACCESS_TRIES:
            #     try:
            #         products_urls = [p.get_attribute("href") for p in driver.find_elements(By.CSS_SELECTOR, '.product-card a')]
            #         # for product_element in products:
            #         #     product_url = product_element.get_attribute('href')
            #         for product_url in products_urls:
            #             yield {"url": product_url}
            #     except WebDriverException:
            #         tries += 1
            #         time.sleep(1)
            #         continue

            #     # no exception: break
            #     break
            
            # if tries == MAX_PRODUCT_ACCESS_TRIES:
            #     print("Max product access tries exceeded!")

            products_urls = [p.get_attribute("href") for p in driver.find_elements(By.CSS_SELECTOR, '.product-card a')]
            # for product_element in products:
            #     product_url = product_element.get_attribute('href')
            for product_url in products_urls:
                yield {"url": product_url}
            
            if page_count == 1:
                break
            
            wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "blu-pagination__button-nav")))
            next_page_button = driver.find_elements(By.CLASS_NAME, 'blu-pagination__button-nav')[-1]
            pagination_area = driver.find_element(By.CLASS_NAME, "blu-pagination__button")
            ActionChains(driver) \
                    .move_to_element(pagination_area) \
                    .perform()
            
            if next_page_button.is_enabled():
                next_page_button.click()
            else:
                break
