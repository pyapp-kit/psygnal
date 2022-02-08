.PHONY: build build-trace check clean benchmark-all benchmark-compare

build:
	python setup.py build_ext --inplace
	rm -f psygnal/*.c

build-trace:
	python setup.py build_ext --force --inplace --define CYTHON_TRACE
	rm -f psygnal/*.c

check:
	pre-commit run --all-files

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
	rm -f `find psygnal -type f -name '*.c' `
	rm -f `find psygnal -type f -name '*.so' `
	python setup.py clean
	rm -rf coverage.xml

# run benchmarks for all commits since v0.1.0
benchmark-all:
	pip install asv
	asv run -j 4 --show-stderr --interleave-processes --skip-existing v0.1.0..HEAD

# compare HEAD against main
benchmark-compare:
	asv run --interleave-processes --skip-existing main^!
	asv run --interleave-processes HEAD^!
	asv compare --split --factor 1.15 main HEAD
