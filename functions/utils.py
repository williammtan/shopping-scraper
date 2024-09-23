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
REGION = os.getenv('REGION')

# Initialize Redis connection
redis_client = redis.from_url(REDIS_URI)

compute = googleapiclient.discovery.build("compute", "v1")

def resize_instance_group(num_vms):
    instance_group_manager_client = compute_v1.RegionInstanceGroupManagersClient()
    operation = instance_group_manager_client.resize(
        project=PROJECT_ID,
        region=REGION,
        instance_group_manager=INSTANCE_GROUP_NAME,
        size=num_vms
    )
    i=0
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

        i += 1
        time.sleep(1)
    
    if i > 0:
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

# Function to trigger a scraper on a specific Scrapyd instance
def trigger_scraper(scrapyd_url, spider_name, project_name='default'):
    url = f'http://{scrapyd_url}/schedule.json'
    data = {
        'project': project_name,
        'spider': spider_name
    }
    response = requests.post(url, data=data)
    return response.json()

# Function to wait for all scrapers to finish on a specific Scrapyd instance
def wait_for_jobs(scrapyd_url, project_name='default'):
    url = f'http://{scrapyd_url}/listjobs.json?project={project_name}'
    while True:
        response = requests.get(url).json()
        if not response['pending'] and not response['running']:
            break
        time.sleep(10)  # Wait 10 seconds before checking again

# Function to push data to Redis queue
def push_to_redis_queue(key, values):
    for v in values:
        redis_client.lpush(key, v)

# Function to get data from Redis queue
def get_from_redis_queue(key):
    objs = redis_client.lrange(key, 0, -1)
    return [json.loads(obj) for obj in objs]

# Function to save data to BigQuery
def save_to_bigquery(table_id, rows_to_insert):
    client = bigquery.Client()
    table = client.get_table(table_id)
    errors = client.insert_rows_json(table, rows_to_insert)
    if errors:
        raise RuntimeError(f"Error saving to BigQuery: {errors}")

