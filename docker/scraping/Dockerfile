FROM python:3.11.5-slim

# Make sure we have the latest and greatest
RUN apt update && apt upgrade -y

# Install poetry
RUN pip install --upgrade pip poetry

# Copy over code
RUN mkdir code/
WORKDIR code/
COPY pyproject.toml poetry.lock .
COPY tests/ ./tests
COPY scripts/ ./scripts
COPY evlens/ ./evlens
COPY README.md .

# Install the project and dependencies
RUN poetry install --no-dev --no-interaction

CMD ["poetry", "run", "python", "tests/test_scraping_not_headless_parallelized.py"] 