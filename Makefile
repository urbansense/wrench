.PHONY: clean test install

setup:
	poetry install --extras "teleclass-classifier sensorthings"

clean: clean-build clean-pyc clean-test

clean-build: # remove build artifacts
	rm -fr build/ dist/ .eggs/
	find . -name '*.egg-info' -o -name '*.egg' -exec rm -fr {} +

clean-pyc: # remove Python file artifacts
	find . -name '*.pyc' -o -name '*.pyo' -o -name '*~' -exec rm -rf {} +

clean-test: # remove test and coverage artifacts
	rm -fr .tox/ .coverage coverage.* htmlcov/ .pytest_cache

clean-cache: # remove test and coverage artifacts
	find . -name '*cache*' -exec rm -rf {} +

install: clean
	poetry install --extras "teleclass-classifier"
	poetry lock

test: ## run tests quickly with the default Python
	poetry shell
	pytest tests/
