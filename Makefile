.PHONY: docs dist clean test

init:
	pip install pipenv
	pipenv install --dev

test:
	pipenv run py.test -v tests

docs: dist
	cd docs && pipenv run make html

dist: clean
	pipenv run python setup.py sdist bdist_wheel

clean:
	rm -rf build dist .egg pysmo.egg-info docs/build
