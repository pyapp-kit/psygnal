# Changelog

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

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.0rc3...v0.1.0)

## [v0.1.0rc3](https://github.com/tlambert03/psygnal/tree/v0.1.0rc3) (2021-07-05)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.0rc2...v0.1.0rc3)

## [v0.1.0rc2](https://github.com/tlambert03/psygnal/tree/v0.1.0rc2) (2021-07-05)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.0rc1...v0.1.0rc2)

## [v0.1.0rc1](https://github.com/tlambert03/psygnal/tree/v0.1.0rc1) (2021-07-05)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/v0.1.0rc0...v0.1.0rc1)

## [v0.1.0rc0](https://github.com/tlambert03/psygnal/tree/v0.1.0rc0) (2021-07-05)

[Full Changelog](https://github.com/tlambert03/psygnal/compare/bd037d2cb3cdc1c9423fd7d88ac6edfdd40f39d9...v0.1.0rc0)

**Implemented enhancements:**

- Add readme, add `@connect` decorator [\#3](https://github.com/tlambert03/psygnal/pull/3) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- fix ci [\#2](https://github.com/tlambert03/psygnal/pull/2) ([tlambert03](https://github.com/tlambert03))
- ci [\#1](https://github.com/tlambert03/psygnal/pull/1) ([tlambert03](https://github.com/tlambert03))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
