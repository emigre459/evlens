FROM python:3.11.5

# Make sure we have the latest and greatest
RUN apt update && apt upgrade -y

# install google chrome
#TODO: need to update this to a newer key method, as apt-key is deprecated
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable=126.0.6478.126-1

# install chromedriver
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/126.0.6478.126/linux64/chromedriver-linux64.zip
RUN unzip /tmp/chromedriver.zip -d /usr/local/bin/

# Install poetry
# RUN pip install --upgrade pip poetry

# Copy over code
RUN mkdir code/
WORKDIR code/
COPY tests/ ./tests
COPY scripts/ ./scripts

# Install the project and dependencies
# RUN poetry install --no-dev --no-interaction
RUN pip install --upgrade pip
ARG SDIST
ADD $SDIST $SDIST
RUN pip install $SDIST

CMD ["python", "tests/test_scraping.py"]