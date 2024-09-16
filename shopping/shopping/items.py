# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class ProductItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()
    description = scrapy.Field()
    options = scrapy.Field()
    url = scrapy.Field()
    marketplace = scrapy.Field()
    category_breadcrumb = scrapy.Field()

    price = scrapy.Field()
    strike_price = scrapy.Field()

    weight = scrapy.Field()

    brand = scrapy.Field()

    stock = scrapy.Field()
    shop_name = scrapy.Field()
    shop_domain = scrapy.Field()

    image_urls = scrapy.Field()

    rating = scrapy.Field()
    review_count = scrapy.Field()
    view_count = scrapy.Field()
    sale_count = scrapy.Field()

    categories = scrapy.Field()

