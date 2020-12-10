.PHONY: init install test-figs tests docs build clean shell

POETRY := $(shell command -v poetry 2> /dev/null)

init:
ifndef POETRY
	pip install poetry
endif
	poetry init

install:
	poetry install

test-figs:
	poetry run py.test --mpl-generate-path=tests/baseline

tests:
	poetry run py.test --cov=pysmo --mpl -v tests

docs: install
	poetry run make -C docs html

build: clean
	poetry build

clean:
	rm -rf build dist .egg pysmo.egg-info docs/build

shell:
	poetry shell
