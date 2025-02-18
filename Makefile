.PHONY: clean test install

setup:
	poetry install --extras "teleclass-classifier sensorthings"

clean: clean-build clean-pyc clean-test clean-cache clean-docs ## remove all build, test, coverage, Python artifacts, cache and docs

clean-docs: # remove docs for update
	rm -fr "docs/$$PACKAGE_NAME.rst" "docs/modules.rst" "docs/conftest.rst" "docs/examples.rst" "docs/tests.rst" "docs/_build" 

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
	poetry install --extras "teleclass-classifier sensorthings"
	poetry lock

test: ## run tests quickly with the default Python
	poetry shell
	pytest tests/
