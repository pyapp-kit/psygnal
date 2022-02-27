# Changelog

## [v0.3.3](https://github.com/tlambert03/psygnal/tree/v0.3.3) (2022-02-14)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.3.2...v0.3.3)

**Merged pull requests:**

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
