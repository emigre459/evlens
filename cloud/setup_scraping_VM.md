gcloud compute instances create plugshare-scraping --project=evlens --zone=us-central1-a --machine-type=c3d-standard-8 --network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default --no-restart-on-failure --maintenance-policy=TERMINATE --provisioning-model=SPOT --instance-termination-action=STOP --service-account=plugshare-scraping@evlens.iam.gserviceaccount.com --scopes=https://www.googleapis.com/auth/cloud-platform --create-disk=auto-delete=yes,boot=yes,device-name=plugshare-scraping,image=projects/debian-cloud/global/images/debian-12-bookworm-v20240709,mode=rw,size=10,type=projects/evlens/zones/us-central1-a/diskTypes/pd-balanced --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --labels=goog-ec-src=vm_add-gcloud --reservation-affinity=any

#NOTE: we got lucky with Debian 12 bookworm version on GCP as of 7/9/24, it's got python 3.11.2 pre-loaded (close to our default 3.11.5 for the project). Would need to find a way to update the version otherwise.
sudo apt update && sudo apt install python3-pip python3-venv git unzip -y

# install google chrome
#TODO: need to update this to a newer key method, as apt-key is deprecated
sudo wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get -y update
sudo apt-get install -y google-chrome-stable=126.0.6478.126-1

# install chromedriver
sudo wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/126.0.6478.126/linux64/chromedriver-linux64.zip
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/

# Get python stuff squared away
git clone https://github.com/emigre459/evlens.git
cd evlens
alias python=python3
alias pip=pip3
python -m venv .venv && source .venv/bin/activate
git switch 14-build-out-tooling-to-talk-to-gcp-cloud-sql
pip install dist/evlens-0.1.0-py3-none-any.whl