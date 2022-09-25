# Changelog

## [v0.4.2](https://github.com/tlambert03/psygnal/tree/v0.4.2) (2022-09-25)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.4.1...v0.4.2)

**Fixed bugs:**

- fix: fix inheritance of property setters [\#126](https://github.com/tlambert03/psygnal/pull/126) ([tlambert03](https://github.com/tlambert03))
- fix: fix bug in setattr with private attrs [\#125](https://github.com/tlambert03/psygnal/pull/125) ([tlambert03](https://github.com/tlambert03))

## [v0.4.1](https://github.com/tlambert03/psygnal/tree/v0.4.1) (2022-09-22)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.4.0...v0.4.1)

**Implemented enhancements:**

- feat: Add ability to disconnect slots from Signal group directly [\#118](https://github.com/tlambert03/psygnal/pull/118) ([alisterburt](https://github.com/alisterburt))

**Fixed bugs:**

- fix: fix listevents docstring parameter mismatch [\#119](https://github.com/tlambert03/psygnal/pull/119) ([alisterburt](https://github.com/alisterburt))

**Tests & CI:**

- ci: skip building py311 wheel [\#124](https://github.com/tlambert03/psygnal/pull/124) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump pypa/cibuildwheel from 2.9.0 to 2.10.1 [\#123](https://github.com/tlambert03/psygnal/pull/123) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.8.1 to 2.9.0 [\#121](https://github.com/tlambert03/psygnal/pull/121) ([dependabot[bot]](https://github.com/apps/dependabot))
- build: pin cython [\#120](https://github.com/tlambert03/psygnal/pull/120) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/gh-action-pypi-publish from 1.5.0 to 1.5.1 [\#116](https://github.com/tlambert03/psygnal/pull/116) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.4.0](https://github.com/tlambert03/psygnal/tree/v0.4.0) (2022-07-26)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.5...v0.4.0)

**Implemented enhancements:**

- feat: raise exceptions as EmitLoopError [\#115](https://github.com/tlambert03/psygnal/pull/115) ([tlambert03](https://github.com/tlambert03))
- feat: add connect\_setitem [\#108](https://github.com/tlambert03/psygnal/pull/108) ([tlambert03](https://github.com/tlambert03))
- build: move entirely to pyproject, and src setup [\#101](https://github.com/tlambert03/psygnal/pull/101) ([tlambert03](https://github.com/tlambert03))
- add readthedocs config, make EventedCallableObjectProxy public [\#86](https://github.com/tlambert03/psygnal/pull/86) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- refactor: guard paramspec import [\#112](https://github.com/tlambert03/psygnal/pull/112) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- replace docs/requirements with extra, fix rtd install [\#87](https://github.com/tlambert03/psygnal/pull/87) ([tlambert03](https://github.com/tlambert03))

## [v0.3.5](https://github.com/tlambert03/psygnal/tree/v0.3.5) (2022-05-25)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.4...v0.3.5)

**Merged pull requests:**

- \[pre-commit.ci\] pre-commit autoupdate [\#85](https://github.com/tlambert03/psygnal/pull/85) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))
- Add documentation [\#84](https://github.com/tlambert03/psygnal/pull/84) ([tlambert03](https://github.com/tlambert03))
- Evented pydantic model [\#83](https://github.com/tlambert03/psygnal/pull/83) ([tlambert03](https://github.com/tlambert03))
- \[pre-commit.ci\] pre-commit autoupdate [\#82](https://github.com/tlambert03/psygnal/pull/82) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))

## [v0.3.4](https://github.com/tlambert03/psygnal/tree/v0.3.4) (2022-05-02)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.3...v0.3.4)

**Implemented enhancements:**

- Add `EventedDict` [\#79](https://github.com/tlambert03/psygnal/pull/79) ([alisterburt](https://github.com/alisterburt))
- add `SelectableEventedList` [\#78](https://github.com/tlambert03/psygnal/pull/78) ([alisterburt](https://github.com/alisterburt))
- Add Throttler class [\#75](https://github.com/tlambert03/psygnal/pull/75) ([tlambert03](https://github.com/tlambert03))
- Add Selection model ported from napari [\#64](https://github.com/tlambert03/psygnal/pull/64) ([alisterburt](https://github.com/alisterburt))

**Fixed bugs:**

- Make SignalInstance weak referenceable \(Fix forwarding signals\) [\#71](https://github.com/tlambert03/psygnal/pull/71) ([tlambert03](https://github.com/tlambert03))

## [v0.3.3](https://github.com/tlambert03/psygnal/tree/v0.3.3) (2022-02-14)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.2...v0.3.3)

**Fixed bugs:**

- Used custom tuple for cython compatibility [\#69](https://github.com/tlambert03/psygnal/pull/69) ([tlambert03](https://github.com/tlambert03))

## [v0.3.2](https://github.com/tlambert03/psygnal/tree/v0.3.2) (2022-02-14)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.1...v0.3.2)

**Implemented enhancements:**

- work with older cython [\#67](https://github.com/tlambert03/psygnal/pull/67) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- generate gh release in CI [\#68](https://github.com/tlambert03/psygnal/pull/68) ([tlambert03](https://github.com/tlambert03))

## [v0.3.1](https://github.com/tlambert03/psygnal/tree/v0.3.1) (2022-02-12)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.0...v0.3.1)

**Fixed bugs:**

- Don't use `repr(obj)` when checking for Qt emit signature [\#66](https://github.com/tlambert03/psygnal/pull/66) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- add a magicgui test to CI [\#65](https://github.com/tlambert03/psygnal/pull/65) ([tlambert03](https://github.com/tlambert03))
- skip cibuildwheel tests on musllinux and i686 [\#63](https://github.com/tlambert03/psygnal/pull/63) ([tlambert03](https://github.com/tlambert03))

## [v0.3.0](https://github.com/tlambert03/psygnal/tree/v0.3.0) (2022-02-10)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.2.0...v0.3.0)

**Implemented enhancements:**

- Add EventedObjectProxy [\#62](https://github.com/tlambert03/psygnal/pull/62) ([tlambert03](https://github.com/tlambert03))
- Misc small changes, add iter\_signal\_instances to utils [\#61](https://github.com/tlambert03/psygnal/pull/61) ([tlambert03](https://github.com/tlambert03))
- Add EventedSet and EventedOrderedSet [\#59](https://github.com/tlambert03/psygnal/pull/59) ([tlambert03](https://github.com/tlambert03))
- add SignalGroup blocked context manager, improve inheritance, and fix strong refs [\#57](https://github.com/tlambert03/psygnal/pull/57) ([tlambert03](https://github.com/tlambert03))
- Add evented list \(more evented containers coming\) [\#56](https://github.com/tlambert03/psygnal/pull/56) ([tlambert03](https://github.com/tlambert03))
- add debug\_events util \(later changed to `monitor_events`\) [\#55](https://github.com/tlambert03/psygnal/pull/55) ([tlambert03](https://github.com/tlambert03))
- support Qt SignalInstance Emit [\#49](https://github.com/tlambert03/psygnal/pull/49) ([tlambert03](https://github.com/tlambert03))
- Add SignalGroup [\#42](https://github.com/tlambert03/psygnal/pull/42) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- add typesafety tests to evented containers [\#60](https://github.com/tlambert03/psygnal/pull/60) ([tlambert03](https://github.com/tlambert03))
- deal with changing API in benchmarks [\#43](https://github.com/tlambert03/psygnal/pull/43) ([tlambert03](https://github.com/tlambert03))

## [v0.2.0](https://github.com/tlambert03/psygnal/tree/v0.2.0) (2021-11-07)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.4...v0.2.0)

**Implemented enhancements:**

- Add `connect/disconnect_settattr` [\#39](https://github.com/tlambert03/psygnal/pull/39) ([tlambert03](https://github.com/tlambert03))
- Enable uncompiled import with PSYGNAL\_UNCOMPILED env var  [\#33](https://github.com/tlambert03/psygnal/pull/33) ([tlambert03](https://github.com/tlambert03))
- Add asv benchmark to CI [\#31](https://github.com/tlambert03/psygnal/pull/31) ([tlambert03](https://github.com/tlambert03))
- Avoid holding strong reference to decorated and partial methods [\#29](https://github.com/tlambert03/psygnal/pull/29) ([Czaki](https://github.com/Czaki))
- Change confusing variable name in \_acceptable\_posarg\_range [\#25](https://github.com/tlambert03/psygnal/pull/25) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Set SignalInstances directly as attributes on objects \(fix bug with hashable signal holders\) [\#28](https://github.com/tlambert03/psygnal/pull/28) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Add benchmarks for connect\_setattr [\#41](https://github.com/tlambert03/psygnal/pull/41) ([Czaki](https://github.com/Czaki))
- Extend emit benchmarks to include methods [\#40](https://github.com/tlambert03/psygnal/pull/40) ([tlambert03](https://github.com/tlambert03))
- Fix codecov CI and bring coverage back to 100 [\#34](https://github.com/tlambert03/psygnal/pull/34) ([tlambert03](https://github.com/tlambert03))
- Change benchmark publication approach [\#32](https://github.com/tlambert03/psygnal/pull/32) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- Misc-typing and minor reorg [\#35](https://github.com/tlambert03/psygnal/pull/35) ([tlambert03](https://github.com/tlambert03))

## [v0.1.4](https://github.com/tlambert03/psygnal/tree/v0.1.4) (2021-10-17)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.3...v0.1.4)

**Implemented enhancements:**

- support python 3.10 [\#24](https://github.com/tlambert03/psygnal/pull/24) ([tlambert03](https://github.com/tlambert03))
- Add ability to pause & resume/reduce signals [\#23](https://github.com/tlambert03/psygnal/pull/23) ([tlambert03](https://github.com/tlambert03))

## [v0.1.3](https://github.com/tlambert03/psygnal/tree/v0.1.3) (2021-10-01)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.2...v0.1.3)

**Implemented enhancements:**

- add \_\_call\_\_ as alias for `emit` on SignalInstance [\#18](https://github.com/tlambert03/psygnal/pull/18) ([tlambert03](https://github.com/tlambert03))

## [v0.1.2](https://github.com/tlambert03/psygnal/tree/v0.1.2) (2021-07-12)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.1...v0.1.2)

**Implemented enhancements:**

- Provide signatures for common builtins [\#7](https://github.com/tlambert03/psygnal/pull/7) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Add more typing tests [\#9](https://github.com/tlambert03/psygnal/pull/9) ([tlambert03](https://github.com/tlambert03))
- test working with qtbot [\#8](https://github.com/tlambert03/psygnal/pull/8) ([tlambert03](https://github.com/tlambert03))

## [v0.1.1](https://github.com/tlambert03/psygnal/tree/v0.1.1) (2021-07-07)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.0...v0.1.1)

**Implemented enhancements:**

- connect decorator, optional args [\#5](https://github.com/tlambert03/psygnal/pull/5) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Catch inspection failures on connect \(e.g. `print`\), and improve maxargs syntax [\#6](https://github.com/tlambert03/psygnal/pull/6) ([tlambert03](https://github.com/tlambert03))

## [v0.1.0](https://github.com/tlambert03/psygnal/tree/v0.1.0) (2021-07-06)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/bd037d2cb3cdc1c9423fd7d88ac6edfdd40f39d9...v0.1.0)

**Implemented enhancements:**

- Add readme, add `@connect` decorator [\#3](https://github.com/tlambert03/psygnal/pull/3) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- fix ci [\#2](https://github.com/tlambert03/psygnal/pull/2) ([tlambert03](https://github.com/tlambert03))
- ci [\#1](https://github.com/tlambert03/psygnal/pull/1) ([tlambert03](https://github.com/tlambert03))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
