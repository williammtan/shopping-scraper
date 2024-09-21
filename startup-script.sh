bin_dir=$(dirname $(which python))
project_id=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

sudo apt update && sudo apt -y install python3 python3-pip python3-venv git
git clone https://github.com/williammtan/shopping-scraper.git
cd shopping-scraper
git pull

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

echo "REDIS_SECRET_VERSION=projects/$project_id/secrets/shopping-redis/versions/1" > .env

cd shopping/

if ! pgrep -fl scrapyd ; then
    sudo nohup "$bin_dir/scrapyd" & # start scrapyd
fi

$bin_dir/scrapyd-deploy