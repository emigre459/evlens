.PHONY: clean data lint requirements sync_data_to_s3 sync_data_from_s3

# SHELL = /usr/bin/env bash

#################################################################################
# GLOBALS                                                                       #
#################################################################################

#TODO: setup for poetry instead of conda (check for poetry, then follow README instructions)

PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
BUCKET = [OPTIONAL] your-bucket-for-syncing-data (do not include 's3://')
PROFILE = default
PROJECT_NAME := evlens
PYTHON_INTERPRETER = python3

ifeq (,$(shell which conda))
HAS_CONDA=False
else
HAS_CONDA=True
endif

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## Install Python Dependencies
requirements: test_environment
	@poetry install

jupyter_kernel:
	$(PYTHON_INTERPRETER) -m ipykernel install --user --name=evlens

## Make Dataset
data: requirements
	$(PYTHON_INTERPRETER) src/data/make_dataset.py data/raw data/processed

## Delete all compiled Python files
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

## Lint using flake8
lint:
	flake8 src

## Upload Data to S3
sync_data_to_s3:
ifeq (default,$(PROFILE))
	aws s3 sync data/ s3://$(BUCKET)/data/
else
	aws s3 sync data/ s3://$(BUCKET)/data/ --profile $(PROFILE)
endif

## Download Data from S3
sync_data_from_s3:
ifeq (default,$(PROFILE))
	aws s3 sync s3://$(BUCKET)/data/ data/
else
	aws s3 sync s3://$(BUCKET)/data/ data/ --profile $(PROFILE)
endif

## Set up python interpreter environment
env_create:
	@echo "Creating new environment"
	@poetry config virtualenvs.in-project true
	@rm -f poetry.lock
	@poetry install


## Strip the venv and start from a blank slate
env_remove:
	@echo "Removing environment and emptying poetry cache"
	@poetry cache clear --all -n pypi
	@poetry cache clear --all -n PyPI
	@rm -f poetry.lock
	@rm -rf $(poetry env list --full-path)
	@rm -rf .venv

## Re-create environment from clean slate
env_rebuild: env_remove env_create

## Build package so it is easily installed via Docker
prepare_package:
	@echo "Don't forget to update your docker-compose files with the new build path arg if you changed anything (e.g. incremented the release)!!"
	@poetry build

## Build poetry package fresh and re-build docker image with test spin-up
rebuild_and_launch_docker_image:
	@poetry build
	@docker compose -f docker/scraping/docker-compose.yml up --build

## Build and push to GH the latest
build_and_push_to_gh:
	@poetry build
	@git add dist/ && git commit -m "Build latest pkg" && git push

## If a new build is passed via GH, refresh the install
refresh_vm_from_new_build:
	@git pull
	@pip install --upgrade --force-reinstall dist/evlens-0.1.0-py3-none-any.whl 


## Test python environment is setup correctly
test_environment:
	$(PYTHON_INTERPRETER) test_environment.py

#################################################################################
# PROJECT RULES                                                                 #
#################################################################################



#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
