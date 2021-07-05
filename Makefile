.PHONY: build
build:
	python setup.py build_ext --inplace
	rm -f psygnal/*.c

.PHONY: build-trace
build-trace:
	python setup.py build_ext --force --inplace --define CYTHON_TRACE
	rm -f psygnal/*.c

.PHONY: check
check:
	pre-commit run --all-files

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	rm -f psygnal/*.c psygnal/*.so
	python setup.py clean
	rm -rf coverage.xml
