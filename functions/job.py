from utils import *
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASK_INDEX = os.getenv("CLOUD_RUN_TASK_INDEX", 0)
TASK_ATTEMPT = os.getenv("CLOUD_RUN_TASK_ATTEMPT", 0)

PROJECT_NAME = os.getenv('PROJECT_NAME')
SCRAPYD_PROJECT_NAME = os.getenv('SCRAPYD_PROJECT_NAME')
DEFAULT_CATEGORY_URL = 'https://www.tokopedia.com/p/komputer-laptop/aksesoris-pc-gaming/meja-gaming'

NUM_VMS_STR = os.getenv('num_vms')
MAIN_CATEGORY_URL = os.getenv('main_category', DEFAULT_CATEGORY_URL)
DRY_RUN = os.getenv('dry_run') # default None

# Main pipeline function
def main():
    logger.info("Starting Tokopedia pipeline")

    gcs_uri = create_gcs_uri("tokopedia_products")

    # Get Requested # of VMs to run
    if NUM_VMS_STR:
        num_vms = int(NUM_VMS_STR)
        logger.info(f"Resizing instance group to {num_vms} VMs")
        resize_instance_group(num_vms)

    # Get first url (main category) from request
    logger.info(f"Main category URL: {MAIN_CATEGORY_URL}")

   # Step 0: Get all VM internal IPs in the managed instance group
    internal_ips = get_instance_internal_ips()
    logger.info(f"Retrieved {len(internal_ips)} VM internal IPs")

    # Step 1: Run tokopedia_categories on 1 VM ONLY
    tokopedia_categories_vm_ip = internal_ips[0]
    logger.info(f"Running tokopedia_categories on VM: {tokopedia_categories_vm_ip}")
    push_to_redis_queue('tokopedia_categories:start_urls', [MAIN_CATEGORY_URL])
    job_id = trigger_scraper(tokopedia_categories_vm_ip, 'tokopedia_categories')
    wait_for_jobs(tokopedia_categories_vm_ip, job_id)

    # Step 2: Retrieve category slugs and push to redis

    category_slugs = get_from_redis_queue('tokopedia_categories:items')
    if DRY_RUN:
        category_slugs = category_slugs[-2:]
    logger.info(f"Retrieved {len(category_slugs)} category slugs")
    push_to_redis_queue('tokopedia_discovery:start_urls', [c['category_slug'] for c in category_slugs])

    # Step 3: Run tokopedia_discovery on each VM
    logger.info("Starting tokopedia_discovery on all VMs")
    run_and_wait_multiple(internal_ips, "tokopedia_discovery")
    logger.info("Completed tokopedia_discovery on all VMs")

    # Step 4: Retrieve discovery URLs and push to redis #UPDATE: SKIP THIS, DIRECTY USE THIS AS START_URLS FOR PRODUCTS
    # discovery_urls = get_from_redis_queue('tokopedia_discovery:items') 
    # logger.info(f"Retrieved {len(discovery_urls)} discovery URLs")
    # push_to_redis_queue('tokopedia_products:start_urls', [d['url'] for d in discovery_urls])

    # Step 5: Run tokopedia_products on each VM
    logger.info("Starting tokopedia_products on all VMs")
    gcs_uris = [
        gcs_uri + f"{i}.jl"
        for i in range(len(internal_ips))
    ]
    settings = [{"FEED_URI": u} for u in gcs_uris]
    run_and_wait_multiple(internal_ips, "tokopedia_products", redis_in="tokopedia_discovery:items", settings=settings)
    logger.info("Completed tokopedia_products on all VMs")

    # Step 6: Retrieve products data and save to BigQuery
    for gcs_uri in gcs_uris:
        save_to_bigquery(f'{PROJECT_NAME}.shopping.products', gcs_uri)
    
    logger.info("Saved product items to BigQuery")

    logger.info("Tokopedia pipeline completed successfully")
    return 'OK'

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        message = (
            f"Task #{TASK_INDEX}, " + f"Attempt #{TASK_ATTEMPT} failed: {str(err)}"
        )

        logging.error(json.dumps({"message": message, "severity": "ERROR"}))
        sys.exit(1)
