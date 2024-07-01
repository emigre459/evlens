#!/bin/bash
curl https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz -o ~/Downloads/gcloud.tar.gz

# Unzip the downloaded file to ~/Downloads/ directory
tar -xvzf ~/Downloads/gcloud.tar.gz -C ~/Downloads/

# Install the Google Cloud SDK
~/Downloads/google-cloud-sdk/install.sh --usage-reporting true --rc-path ~/.bashrc_gcloud --bash-completion true --path-update true --install-python false

echo "Making a backup of ~/.bash_profile as ~/.bash_profile_backup before adding content..."
cp ~/.bash_profile ~/.bash_profile_backup
cat ~/.bashrc_gcloud >> ~/.bash_profile

echo "You need to open a new terminal shell for the changes to take effect"
echo "After opening a new shell, run 'gcloud init' to configure the Google Cloud SDK"