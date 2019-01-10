.PHONY: docs

init:
	pip install pipenv
	pipenv install --dev

test:
	pipenv run py.test -v tests

docs:
	cd docs && pipenv run make html
