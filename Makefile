include .env

RELEASE_TAG ?= ""


help: # Show this help
	@egrep -h '\s#\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check-no-unstaged-changes:
	git diff-index --quiet HEAD -- || (echo "There are unstaged changes, please commit or stash them"; exit 1)
	git branch --show-current | grep -q main || (echo "You must be on the main branch to release"; exit 1)
	git fetch
	git diff --quiet origin/main || (echo "Local branch is not in sync with remote"; exit 1)

current-version-number : # Show current version number
	$(eval RELEASE_TAG := $(shell python3 release.py --current))
	@echo $(RELEASE_TAG)

increment-patch-number-and-build: # increment version
	$(eval RELEASE_TAG := $(shell python3 release.py --patch))
	python3 -m build

increment-minor-number-and-build: # increment version
	$(eval RELEASE_TAG := $(shell python3 release.py --minor))
	python3 -m build

upload-to-testpypi: # Upload current dist directory to testpypi
	POETRY_PYPI_TOKEN_PYPI=$(TEST_PYPITOKEN) poetry publish -r testpypi

upload-to-pypi: increment-minor-number-and-build # Upload current dist directory to pypi
	POETRY_PYPI_TOKEN_PYPI=$(PYPITOKEN) poetry publish

system-tests: # Run system tests
	./run_system_tests.sh $(RELEASE_TAG)

pytest:	# Run pytest
	python3 -m pytest tests/unit
	python3 -m pytest tests/module

git-release:
	git add .
	git commit -nm "Release $(RELEASE_TAG)"
	git push

release: check-no-unstaged-changes pytest increment-patch-number-and-build upload-to-testpypi system-tests upload-to-pypi git-release
	@echo "Done"
