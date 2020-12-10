.PHONY: init install test-figs tests docs build clean shell help

POETRY_VERSION := $(shell command poetry --version 2> /dev/null)

help: ## List all commands
	@echo -e "\n\033[1mAVAILABLE COMMANDS"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9 -]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-poetry: ## Check if poetry is installed
ifndef POETRY_VERSION
	@echo "Please install poetry first"
	@exit 1
else
	@echo "Found ${POETRY_VERSION}";
endif

install: check-poetry ## Install this project and it's dependancies in a virtual environment
	poetry install

test-figs: check-poetry ## Generate baseline figures for testing
	poetry run py.test --mpl-generate-path=tests/baseline

tests: check-poetry ## Run tests with pytest
	poetry run py.test --cov=pysmo --mpl -v tests

docs: install check-poetry ## Build html docs
	poetry run make -C docs html

build: clean check-poetry ## Build distribution
	poetry build

clean: ## Remove existing builds
	rm -rf build dist .egg pysmo.egg-info docs/build

shell: check-poetry ## Start a shell in the project virtual environment
	poetry shell
