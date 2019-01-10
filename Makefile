
init:
	pip install pipenv
	pipenv install --dev

test:
	pipenv run py.test -v tests

.PHONY: docs
docs:
	cd docs && make html
