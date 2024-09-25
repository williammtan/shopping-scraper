gcloud run jobs deploy tokopedia-pipeline \
    --source . \
    --tasks 50 \
    --env-vars-file .env.yaml \
    --max-retries 0 \
    --region us-central1 \
    --vpc-connector default-vpc-connector