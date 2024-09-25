import os
import redis
import time
import json
import requests
from google.cloud import compute_v1, bigquery, secretmanager
import googleapiclient.discovery

# Configuration


client = secretmanager.SecretManagerServiceClient()

REDIS_URI = client.access_secret_version(request={"name":os.getenv("REDIS_SECRET_VERSION")}).payload.data.decode("utf-8")
INSTANCE_GROUP_NAME = os.getenv('INSTANCE_GROUP_NAME')
PROJECT_ID = os.getenv('PROJECT_ID')
GCS_BUCKET = os.getenv('GCS_BUCKET')
REGION = os.getenv('REGION')
SCRAPYD_PROJECT_NAME = os.getenv('SCRAPYD_PROJECT_NAME')

# Initialize Redis connection
redis_client = redis.from_url(REDIS_URI)

compute = googleapiclient.discovery.build("compute", "v1")

def resize_instance_group(num_vms):
    instance_group_manager = compute_v1.RegionInstanceGroupsClient()
    instances = instance_group_manager.list_instances(
        instance_group=INSTANCE_GROUP_NAME,
        project=PROJECT_ID,
        region=REGION
    )
    if len(list(instances)) == num_vms:
        return

    instance_group_manager_client = compute_v1.RegionInstanceGroupManagersClient()
    operation = instance_group_manager_client.resize(
        project=PROJECT_ID,
        region=REGION,
        instance_group_manager=INSTANCE_GROUP_NAME,
        size=num_vms
    )
    while True:
        region_operations_client = compute_v1.RegionOperationsClient()
        result = region_operations_client.get(
            project=PROJECT_ID,
            region=REGION,
            operation=operation.name
        )

        if result.status == compute_v1.types.Operation.Status.DONE:
            if result.error:
                raise Exception(result["error"])
            break
    
    # waited for region operations, some instances just got set up
    # so we need to wait for a bit more
    time.sleep(int(os.getenv('INSTANCE_SPINUP_TIME')))

# Function to get all internal IPs of VMs in Managed Instance Group
def get_instance_internal_ips():
    instance_group_manager = compute_v1.RegionInstanceGroupsClient()
    instances = instance_group_manager.list_instances(
        instance_group=INSTANCE_GROUP_NAME,
        project=PROJECT_ID,
        region=REGION
    )

    internal_ips = []
    instance_client = compute_v1.InstancesClient()
    for instance in instances:
        instance_name = instance.instance.split('/')[-1]
        instance_zone = instance.instance.split('/')[-3]
        instance_obj = instance_client.get(
            project=PROJECT_ID, zone=instance_zone, instance=instance_name
        )
        internal_ips.append(instance_obj.network_interfaces[0].network_i_p)
    return internal_ips

# Function to trigger a scraper on a specific Scrapyd instance, returns the job_id
def trigger_scraper(scrapyd_url, spider_name, redis_in=None, settings={}):
    url = f'http://{scrapyd_url}/schedule.json'
    data = [
        ('project', SCRAPYD_PROJECT_NAME),
        ('spider', spider_name),
    ]
    data.extend([('setting', f"{k}={v}") for k, v in settings.items()])
    if redis_in:
        data.append(('setting', "REDIS_START_URLS_KEY="+redis_in))
    response = requests.post(url, data=data)
    return response.json()["jobid"]

# Function to wait for all scrapers to finish on a specific Scrapyd instance
def wait_for_jobs(scrapyd_url, job_id):
    url = f'http://{scrapyd_url}/listjobs.json?project={SCRAPYD_PROJECT_NAME}'
    while True:
        response = requests.get(url).json()
        finished_ids = [j["id"] for j in response['finished']]
        if job_id in finished_ids:
            break
        time.sleep(10)  # Wait 10 seconds before checking again

def run_and_wait_multiple(scrapyd_ips, spider_name, redis_in=None, settings=None):
    job_mapping = {}
    for i, scrapyd_ip in enumerate(scrapyd_ips):
        s = settings[i] if settings else {}
        job_id = trigger_scraper(scrapyd_ip, spider_name, redis_in, s)
        job_mapping[scrapyd_ip] = job_id
    for scrapyd_ip, job_id in job_mapping.items():
        wait_for_jobs(scrapyd_ip, job_id)
    
    return job_mapping # return ip: job_id mapping

# Function to push data to Redis queue
def push_to_redis_queue(key, values, remove_previous=True): # TODO: remove latest?
    if remove_previous:
        for key in redis_client.scan_iter(key+"*"):
            redis_client.delete(key)
    for v in values:
        redis_client.lpush(key, v)

# Function to get data from Redis queue
def get_from_redis_queue(key):
    objs = redis_client.lrange(key, 0, -1)
    return [json.loads(obj) for obj in objs]

# Function to save data to BigQuery
def save_to_bigquery(table_id, gcs_uri):
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[
            {
                "name": "name",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "description",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "options",
                "type": "RECORD",
                "mode": "NULLABLE",
                "fields": [
                {
                    "name": "key",
                    "type": "STRING",
                    "mode": "NULLABLE"
                },
                {
                    "name": "value",
                    "type": "STRING",
                    "mode": "NULLABLE"
                }
                ]
            },
            {
                "name": "url",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "marketplace",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "category_breadcrumb",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "price",
                "type": "INTEGER",
                "mode": "NULLABLE"
            },
            {
                "name": "strike_price",
                "type": "INTEGER",
                "mode": "NULLABLE"
            },
            {
                "name": "weight",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "brand",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "stock",
                "type": "INTEGER",
                "mode": "NULLABLE"
            },
            {
                "name": "shop_name",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "shop_domain",
                "type": "STRING",
                "mode": "NULLABLE"
            },
            {
                "name": "image_urls",
                "type": "STRING",
                "mode": "REPEATED"
            },
            {
                "name": "rating",
                "type": "FLOAT",
                "mode": "NULLABLE"
            },
            {
                "name": "review_count",
                "type": "INTEGER",
                "mode": "NULLABLE"
            },
            {
                "name": "view_count",
                "type": "INTEGER",
                "mode": "NULLABLE"
            },
            {
                "name": "sale_count",
                "type": "INTEGER",
                "mode": "NULLABLE"
            },
            {
                "name": "categories",
                "type": "STRING",
                "mode": "REPEATED"
            }
            ],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    load_job = client.load_table_from_uri(
        gcs_uri, table_id, job_config=job_config
    )  # Make an API request.

    load_job.result()  # Waits for the job to complete.


def get_feed_output(scrapyd_url, job_id):
    url = f'http://{scrapyd_url}/listjobs.json?project={SCRAPYD_PROJECT_NAME}'
    response = requests.get(url).json()
    for job in response["finished"]:
        if job["id"] == job_id:
            return job["items_url"]
    
def create_gcs_uri(spider_name):
    current_time = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    return f"gs://{GCS_BUCKET}/feeds/{spider_name}/{current_time}/"
