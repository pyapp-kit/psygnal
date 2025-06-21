.PHONY: build check clean benchmark-all benchmark-compare typetest

build:
	HATCH_BUILD_HOOKS_ENABLE=1 uv sync --force-reinstall

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
	rm -rf wheelhouse
	rm -f `find src -type f -name '*.c' `
	rm -f `find src -type f -name '*.so' `
	rm -f `find src -type f -name '*.so_BAK' `
	rm -rf coverage.xml

# run benchmarks for all commits since v0.1.0
benchmark-all:
	pip install asv
	MACOSX_DEPLOYMENT_TARGET=11.0 asv run -j 8 --show-stderr --interleave-processes --skip-existing v0.2.0..HEAD

# compare HEAD against main
benchmark-compare:
	MACOSX_DEPLOYMENT_TARGET=11.0 asv run --interleave-processes --skip-existing main^!
	MACOSX_DEPLOYMENT_TARGET=11.0 asv run --interleave-processes HEAD^!
	asv compare --split --factor 1.15 main HEAD

typetest:
	pytest typesafety --mypy-only-local-stub
