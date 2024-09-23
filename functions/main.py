import functions_framework
from requests import Request
from utils import *
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_NAME = os.getenv('PROJECT_NAME')
DEFAULT_CATEGORY_URL = 'https://www.tokopedia.com/p/komputer-laptop/aksesoris-pc-gaming/meja-gaming'

# Main pipeline function
@functions_framework.http
def tokopedia_pipeline(request: Request):
    logger.info("Starting Tokopedia pipeline")

    # Get Requested # of VMs to run
    num_vms_str = request.args.get('num_vms')
    if num_vms_str:
        num_vms = int(num_vms_str)
        logger.info(f"Resizing instance group to {num_vms} VMs")
        resize_instance_group(num_vms)

    # Get first url (main category) from request
    main_category = request.json.get('main_category', DEFAULT_CATEGORY_URL) if request.json else DEFAULT_CATEGORY_URL
    logger.info(f"Main category URL: {main_category}")

    # Step 0: Get all VM internal IPs in the managed instance group
    internal_ips = get_instance_internal_ips()
    logger.info(f"Retrieved {len(internal_ips)} VM internal IPs")

    # Step 1: Run tokopedia_categories on 1 VM ONLY
    tokopedia_categories_vm_ip = internal_ips[0]
    logger.info(f"Running tokopedia_categories on VM: {tokopedia_categories_vm_ip}")
    push_to_redis_queue('tokopedia_categories:start_urls', [main_category])
    trigger_scraper(tokopedia_categories_vm_ip, 'tokopedia_categories')
    wait_for_jobs(tokopedia_categories_vm_ip)

    # Step 2: Retrieve category slugs and push to redis
    category_slugs = get_from_redis_queue('tokopedia_categories:items')
    logger.info(f"Retrieved {len(category_slugs)} category slugs")
    push_to_redis_queue('tokopedia_discovery:start_urls', [c['category_slug'] for c in category_slugs])

    # Step 3: Run tokopedia_discovery on each VM
    logger.info("Starting tokopedia_discovery on all VMs")
    for scrapyd_ip in internal_ips:
        trigger_scraper(scrapyd_ip, 'tokopedia_discovery')
    for scrapyd_ip in internal_ips:
        wait_for_jobs(scrapyd_ip)
    logger.info("Completed tokopedia_discovery on all VMs")

    # Step 4: Retrieve discovery URLs and push to redis
    discovery_urls = get_from_redis_queue('tokopedia_discovery:items')
    logger.info(f"Retrieved {len(discovery_urls)} discovery URLs")
    push_to_redis_queue('tokopedia_products:start_urls', [d['url'] for d in discovery_urls])

    # Step 5: Run tokopedia_products on each VM
    logger.info("Starting tokopedia_products on all VMs")
    for scrapyd_ip in internal_ips:
        trigger_scraper(scrapyd_ip, 'tokopedia_products')
    for scrapyd_ip in internal_ips:
        wait_for_jobs(scrapyd_ip)
    logger.info("Completed tokopedia_products on all VMs")

    # Step 6: Retrieve products data and save to BigQuery
    product_items = get_from_redis_queue('tokopedia_products:items')
    logger.info(f"Retrieved {len(product_items)} product items")
    save_to_bigquery(f'{PROJECT_NAME}.shopping.tokopedia_products', product_items)
    logger.info("Saved product items to BigQuery")

    logger.info("Tokopedia pipeline completed successfully")
    return 'OK'
