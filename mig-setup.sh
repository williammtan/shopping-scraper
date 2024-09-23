gcloud compute instance-groups managed update shopping-scrapers --region us-central1  \
    --update-policy-replacement-method=recreate \
    --update-policy-type=opportunistic \
    --update-policy-max-surge=0