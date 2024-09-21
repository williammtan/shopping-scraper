sudo apt update && sudo apt -y install python3-pip
git clone https://github.com/williammtan/shopping-scraper.git
cd shopping-scraper
pip3 install -r requirements.txt
if  pgrep -fl scrapyd ; then
    git pull # just update repo
else 
    sudo nohup scrapyd & # start scrapyd
fi
