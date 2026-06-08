#!/bin/bash

set -e

echo "Setting up autograder environment..."

# Update and install dependencies
apt-get update
apt-get install -y wget gnupg ca-certificates git curl xvfb

# Install Google Chrome (faster with --no-install-recommends)
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
apt-get update
apt-get install -y --no-install-recommends google-chrome-stable

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# Install Python packages
pip3 install requests

# Pre-install common npm packages globally for caching
npm install -g http-server

# Pre-warm Chrome to reduce first-launch time
google-chrome-stable --version

echo "Setup completed"