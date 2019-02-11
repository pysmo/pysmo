.PHONY: docs dist clean test

PIPENV := $(shell command -v pipenv 2> /dev/null)

init:
ifndef PIPENV
	pip install pipenv
endif
	pipenv install --dev

test:
	pipenv run py.test -v tests

docs: dist
	cd docs && pipenv run make html

dist: clean
	pipenv run python setup.py sdist bdist_wheel

clean:
	rm -rf build dist .egg pysmo.egg-info docs/build
