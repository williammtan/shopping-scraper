
import redis
import json

# Create a redis client
redisClient = redis.from_url('redis://localhost:6379')

# Remove previous ones

for key in redisClient.scan_iter('tokopedia_products:start_urls*'):
    redisClient.delete(key)


# Push URLs to Redis Queue 

with open('test_multiple.csv') as f:
    for i, url in enumerate(f.readlines()):
        if i != 0:
            redisClient.lpush('tokopedia_products:start_urls', url)


# redisClient.lpush('tokopedia_products:start_urls', "https://www.tokopedia.com/studioponsel/apple-macbook-air-2022-m2-chip-13-inch-512gb-256gb-ram-8gb-apple-256gb-grey-1b7f4?extParam=ivf%3Dtrue&src=topads")
# redisClient.lpush('tokopedia_products:start_urls', "https://www.tokopedia.com/symfyx/microsoft-office-365-original-lifetime-win-mac-macbook-ipad-tab-android-dvd-dea65?src=topads")
# redisClient.lpush('tokopedia_products:start_urls', "https://www.tokopedia.com/kliknkliktangcity/laptop-apple-macbook-air-13-chip-m3-ssd-256gb-512gb-mac-os-resmi-ibox-space-grey-8gb-256gb-ssd-23c4d?extParam=ivf%3Dfalse&src=topads")
# redisClient.lpush('tokopedia_products:start_urls', "https://www.tokopedia.com/dede-zhop/kacang-oke-kacang-goreng-kacang-sanghai-camilan-kacang?extParam=ivf%3Dfalse&src=topads")
# redisClient.lpush('tokopedia_products:start_urls', json.dumps({ "url": "https://www.tokopedia.com/dede-zhop/kacang-oke-kacang-goreng-kacang-sanghai-camilan-kacang?extParam=ivf%3Dfalse&src=topads", "meta": {"job-id":"123xsd", "start-date":"dd/mm/yy"}}))