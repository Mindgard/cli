
help: # Show this help
	@egrep -h '\s#\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check-no-unstaged-changes:
	git diff-index --quiet HEAD -- || (echo "There are unstaged changes, please commit or stash them"; exit 1)
	git branch --show-current | grep -q main || (echo "You must be on the main branch to release"; exit 1)

increment-patch-number-and-build: # increment version
	python3 release.py 
	python3 -m build

increment-minor-number-and-build: # increment version
	python3 release.py --minor
	python3 -m build

upload-to-testpypi: # Upload current dist directory to testpypi
	python3 -m twine upload --repository testpypi dist/*

system-tests: # Run system tests
	./run_system_tests.sh

upload-to-pypi:
	python3 -m twine upload dist/*

git-release:
	git add .
	git commit -nm "Release $(TARGET_TAG)"
	git push

release:
	check-no-unstaged-changes increment-patch-number-and-build upload-to-testpypi
	sleep 5
	system-tests
	# upload-to-pypi
	# git-release
	echo "Still went ahead"