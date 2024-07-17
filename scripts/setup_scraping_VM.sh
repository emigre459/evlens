#!/bin/bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install unzip git install python3.11-venv -y

# install google chrome
#TODO: need to update this to a newer key method, as apt-key is deprecated
# https://stackoverflow.com/a/71384057/8630238
sudo wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get -y update
sudo apt-get install -y google-chrome-stable

# install chromedriver
# Grab version of Chrome installed so we can match chromedriver version
chrome_version=$(apt show google-chrome-stable | grep Version | awk '{print $2}')
sudo wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/126.0.6478.126/linux64/chromedriver-linux64.zip

#TODO: figure out a way to guarantee we get the closest chromedriver version to our actuall chrome install as possible
# sudo wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/$chrome_version/linux64/chromedriver-linux64.zip
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/

# Get python stuff squared away
git clone https://github.com/emigre459/evlens.git
cd evlens
echo "alias python=python3" >> ~/.bashrc
echo "alias pip=pip3" >> ~/.bashrc
source ~/.bashrc
python3 -m venv .venv && source .venv/bin/activate
git switch 14-build-out-tooling-to-talk-to-gcp-cloud-sql
pip install glances
pip install --upgrade --force-reinstall $(ls -t dist/*.whl | head -n 1)