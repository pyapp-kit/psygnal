# Changelog

## [v0.10.0rc0](https://github.com/pyapp-kit/psygnal/tree/v0.10.0rc0) (2024-02-16)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.9.5...v0.10.0rc0)

**Implemented enhancements:**

- refactor!: New SignalGroup that does not subclass SignalInstance [\#269](https://github.com/pyapp-kit/psygnal/pull/269) ([tlambert03](https://github.com/tlambert03))
- feat: emit the old value as second argument in Signals from SignalGroupDescriptor \(evented dataclass\) [\#257](https://github.com/pyapp-kit/psygnal/pull/257) ([getzze](https://github.com/getzze))

**Fixed bugs:**

- fix: fix connect\_setattr on dataclass field signals [\#258](https://github.com/pyapp-kit/psygnal/pull/258) ([tlambert03](https://github.com/tlambert03))
- fix: add and fix copy operators [\#255](https://github.com/pyapp-kit/psygnal/pull/255) ([Czaki](https://github.com/Czaki))
- fix: fix 3.7 build [\#250](https://github.com/pyapp-kit/psygnal/pull/250) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- ci: inherit secrets in reusable workflow [\#266](https://github.com/pyapp-kit/psygnal/pull/266) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- docs: Update README.md with evented containers [\#272](https://github.com/pyapp-kit/psygnal/pull/272) ([tlambert03](https://github.com/tlambert03))
- docs: Update README.md with `make build` [\#270](https://github.com/pyapp-kit/psygnal/pull/270) ([tlambert03](https://github.com/tlambert03))
- Drop python 3.7 [\#268](https://github.com/pyapp-kit/psygnal/pull/268) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.16.4 to 2.16.5 [\#263](https://github.com/pyapp-kit/psygnal/pull/263) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.16.2 to 2.16.4 [\#256](https://github.com/pyapp-kit/psygnal/pull/256) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump actions/cache from 3 to 4 [\#253](https://github.com/pyapp-kit/psygnal/pull/253) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump actions/upload-artifact from 3 to 4 [\#249](https://github.com/pyapp-kit/psygnal/pull/249) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump actions/setup-python from 4 to 5 [\#248](https://github.com/pyapp-kit/psygnal/pull/248) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump CodSpeedHQ/action from 1 to 2 [\#246](https://github.com/pyapp-kit/psygnal/pull/246) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump conda-incubator/setup-miniconda from 2 to 3 [\#245](https://github.com/pyapp-kit/psygnal/pull/245) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci: use reusable ci workflow [\#241](https://github.com/pyapp-kit/psygnal/pull/241) ([tlambert03](https://github.com/tlambert03))

## [v0.9.5](https://github.com/pyapp-kit/psygnal/tree/v0.9.5) (2023-11-13)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.9.4...v0.9.5)

**Implemented enhancements:**

- feat: better repr for WeakCallback objects [\#236](https://github.com/pyapp-kit/psygnal/pull/236) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- fix: fix py37 build [\#243](https://github.com/pyapp-kit/psygnal/pull/243) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.16.1 to 2.16.2 [\#240](https://github.com/pyapp-kit/psygnal/pull/240) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.15.0 to 2.16.1 [\#238](https://github.com/pyapp-kit/psygnal/pull/238) ([dependabot[bot]](https://github.com/apps/dependabot))
- refactor: make EmitLoop error message clearer [\#232](https://github.com/pyapp-kit/psygnal/pull/232) ([tlambert03](https://github.com/tlambert03))

## [v0.9.4](https://github.com/pyapp-kit/psygnal/tree/v0.9.4) (2023-09-19)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.9.3...v0.9.4)

**Implemented enhancements:**

- perf: don't compare before/after values in evented dataclass/model when no signals connected [\#235](https://github.com/pyapp-kit/psygnal/pull/235) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: emission of events from root validators and extraneous emission of dependent fields [\#234](https://github.com/pyapp-kit/psygnal/pull/234) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump actions/checkout from 3 to 4 [\#231](https://github.com/pyapp-kit/psygnal/pull/231) ([dependabot[bot]](https://github.com/apps/dependabot))
- test: python 3.12 [\#225](https://github.com/pyapp-kit/psygnal/pull/225) ([tlambert03](https://github.com/tlambert03))

## [v0.9.3](https://github.com/pyapp-kit/psygnal/tree/v0.9.3) (2023-08-15)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.9.2...v0.9.3)

**Fixed bugs:**

- fix: fix signature inspection on debounced/throttled, update typing and wrapped [\#228](https://github.com/pyapp-kit/psygnal/pull/228) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- build: restrict py versions on cibuildwheel [\#229](https://github.com/pyapp-kit/psygnal/pull/229) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.14.1 to 2.15.0 [\#227](https://github.com/pyapp-kit/psygnal/pull/227) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.9.2](https://github.com/pyapp-kit/psygnal/tree/v0.9.2) (2023-08-12)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.9.1...v0.9.2)

**Fixed bugs:**

- fix: add deepcopy method for mypyc support, don't copy weakly connected slots [\#222](https://github.com/pyapp-kit/psygnal/pull/222) ([tlambert03](https://github.com/tlambert03))
- Fix imports of typing extensions [\#221](https://github.com/pyapp-kit/psygnal/pull/221) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- ci: fix linux wheels [\#226](https://github.com/pyapp-kit/psygnal/pull/226) ([tlambert03](https://github.com/tlambert03))
- ci: change concurrency [\#224](https://github.com/pyapp-kit/psygnal/pull/224) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- build: remove setuppy [\#223](https://github.com/pyapp-kit/psygnal/pull/223) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.13.1 to 2.14.1 [\#218](https://github.com/pyapp-kit/psygnal/pull/218) ([dependabot[bot]](https://github.com/apps/dependabot))
- fix: fix duplicated derived events [\#216](https://github.com/pyapp-kit/psygnal/pull/216) ([tlambert03](https://github.com/tlambert03))
- feat: support pydantic v2 [\#214](https://github.com/pyapp-kit/psygnal/pull/214) ([tlambert03](https://github.com/tlambert03))
- ci\(pre-commit.ci\): autoupdate [\#213](https://github.com/pyapp-kit/psygnal/pull/213) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.13.0 to 2.13.1 [\#212](https://github.com/pyapp-kit/psygnal/pull/212) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(pre-commit.ci\): autoupdate [\#211](https://github.com/pyapp-kit/psygnal/pull/211) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))

## [v0.9.1](https://github.com/pyapp-kit/psygnal/tree/v0.9.1) (2023-05-29)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.9.0...v0.9.1)

**Implemented enhancements:**

- feat: Support toolz [\#210](https://github.com/pyapp-kit/psygnal/pull/210) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: better error message with keyword only partials [\#209](https://github.com/pyapp-kit/psygnal/pull/209) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- build: add test dep [\#206](https://github.com/pyapp-kit/psygnal/pull/206) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump pypa/cibuildwheel from 2.12.3 to 2.13.0 [\#207](https://github.com/pyapp-kit/psygnal/pull/207) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(pre-commit.ci\): autoupdate [\#205](https://github.com/pyapp-kit/psygnal/pull/205) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.12.1 to 2.12.3 [\#204](https://github.com/pyapp-kit/psygnal/pull/204) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.9.0](https://github.com/pyapp-kit/psygnal/tree/v0.9.0) (2023-04-07)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.8.1...v0.9.0)

**Implemented enhancements:**

- feat: add thread parameter to connection method, allowed "queued connections" [\#200](https://github.com/pyapp-kit/psygnal/pull/200) ([tlambert03](https://github.com/tlambert03))
- build: add pyinstaller hook to simplify frozing apps using pyinstaller  [\#194](https://github.com/pyapp-kit/psygnal/pull/194) ([Czaki](https://github.com/Czaki))

**Merged pull requests:**

- docs: add docs on connecting across thread [\#203](https://github.com/pyapp-kit/psygnal/pull/203) ([tlambert03](https://github.com/tlambert03))
- chore: deprecate async keyword in emit method [\#201](https://github.com/pyapp-kit/psygnal/pull/201) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.12.0 to 2.12.1 [\#197](https://github.com/pyapp-kit/psygnal/pull/197) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump actions/setup-python from 3 to 4 [\#193](https://github.com/pyapp-kit/psygnal/pull/193) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.8.1](https://github.com/pyapp-kit/psygnal/tree/v0.8.1) (2023-02-23)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.8.0...v0.8.1)

**Fixed bugs:**

- fix: fix strict signal group checking when signatures aren't hashable [\#192](https://github.com/pyapp-kit/psygnal/pull/192) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- test: add back typesafety tests [\#190](https://github.com/pyapp-kit/psygnal/pull/190) ([tlambert03](https://github.com/tlambert03))

## [v0.8.0](https://github.com/pyapp-kit/psygnal/tree/v0.8.0) (2023-02-23)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.7.2...v0.8.0)

**Implemented enhancements:**

- feat: compile throttler module, improve typing [\#187](https://github.com/pyapp-kit/psygnal/pull/187) ([tlambert03](https://github.com/tlambert03))
- feat: improved `monitor_events` [\#181](https://github.com/pyapp-kit/psygnal/pull/181) ([tlambert03](https://github.com/tlambert03))
- feat: make SignalGroupDescriptor public [\#173](https://github.com/pyapp-kit/psygnal/pull/173) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: fix inheritance of classes with a SignalGroupDescriptor [\#186](https://github.com/pyapp-kit/psygnal/pull/186) ([tlambert03](https://github.com/tlambert03))
- fix: minor typing fixes on `connect` [\#180](https://github.com/pyapp-kit/psygnal/pull/180) ([tlambert03](https://github.com/tlambert03))
- fix: add getattr to signalgroup for typing [\#174](https://github.com/pyapp-kit/psygnal/pull/174) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- ci: add dataclasses benchmarks [\#189](https://github.com/pyapp-kit/psygnal/pull/189) ([tlambert03](https://github.com/tlambert03))
- test: no cover compile funcs [\#185](https://github.com/pyapp-kit/psygnal/pull/185) ([tlambert03](https://github.com/tlambert03))
- ci: add evented benchmark [\#175](https://github.com/pyapp-kit/psygnal/pull/175) ([tlambert03](https://github.com/tlambert03))
- ci: add codspeed benchmarks [\#170](https://github.com/pyapp-kit/psygnal/pull/170) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- refactor: change patching of \_\_setattr\_\_ in SignalGroupDescriptor, make more explicit [\#188](https://github.com/pyapp-kit/psygnal/pull/188) ([tlambert03](https://github.com/tlambert03))
- docs: small docs updates, document EmissionLoopError [\#184](https://github.com/pyapp-kit/psygnal/pull/184) ([tlambert03](https://github.com/tlambert03))
- refactor: remove PSYGNAL\_UNCOMPILED flag. [\#183](https://github.com/pyapp-kit/psygnal/pull/183) ([tlambert03](https://github.com/tlambert03))
- docs: adding spellchecking to docs [\#182](https://github.com/pyapp-kit/psygnal/pull/182) ([tlambert03](https://github.com/tlambert03))
- docs: update evented docs to descript SignalGroupDescriptor [\#179](https://github.com/pyapp-kit/psygnal/pull/179) ([tlambert03](https://github.com/tlambert03))
- refactor: split out SlotCaller logic into new `weak_callable` module... maybe public eventually [\#178](https://github.com/pyapp-kit/psygnal/pull/178) ([tlambert03](https://github.com/tlambert03))
- refactor: split out dataclass utils [\#176](https://github.com/pyapp-kit/psygnal/pull/176) ([tlambert03](https://github.com/tlambert03))
- refactor: use weakmethod instead of \_get\_method\_name [\#168](https://github.com/pyapp-kit/psygnal/pull/168) ([tlambert03](https://github.com/tlambert03))

## [v0.7.2](https://github.com/pyapp-kit/psygnal/tree/v0.7.2) (2023-02-11)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.7.1...v0.7.2)

**Fixed bugs:**

- fix: use weakref when instance is passed to SignalGroup [\#167](https://github.com/pyapp-kit/psygnal/pull/167) ([tlambert03](https://github.com/tlambert03))

## [v0.7.1](https://github.com/pyapp-kit/psygnal/tree/v0.7.1) (2023-02-11)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.7.0...v0.7.1)

**Implemented enhancements:**

- feat: add `is_evented` and `get_evented_namespace` [\#166](https://github.com/pyapp-kit/psygnal/pull/166) ([tlambert03](https://github.com/tlambert03))
- feat: add support for msgspec Struct classes to evented decorator [\#165](https://github.com/pyapp-kit/psygnal/pull/165) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: fix clobbering of SignalGroup name in EventedModel [\#158](https://github.com/pyapp-kit/psygnal/pull/158) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump pypa/cibuildwheel from 2.11.4 to 2.12.0 [\#164](https://github.com/pyapp-kit/psygnal/pull/164) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.11.3 to 2.11.4 [\#159](https://github.com/pyapp-kit/psygnal/pull/159) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.7.0](https://github.com/pyapp-kit/psygnal/tree/v0.7.0) (2022-12-20)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.6.1...v0.7.0)

**Implemented enhancements:**

- build:  use mypyc instead of cython, move to hatch [\#149](https://github.com/pyapp-kit/psygnal/pull/149) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- fix: add dataclass\_transform to maintain IDE typing support for EventedModel.\_\_init\_\_ [\#154](https://github.com/pyapp-kit/psygnal/pull/154) ([tlambert03](https://github.com/tlambert03))
- Don't unblock/resume within nested contexts [\#150](https://github.com/pyapp-kit/psygnal/pull/150) ([hanjinliu](https://github.com/hanjinliu))

**Merged pull requests:**

- ci\(pre-commit.ci\): autoupdate [\#155](https://github.com/pyapp-kit/psygnal/pull/155) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.11.2 to 2.11.3 [\#153](https://github.com/pyapp-kit/psygnal/pull/153) ([dependabot[bot]](https://github.com/apps/dependabot))
- style: use ruff instead of flake8, isort, pyupgrade, autoflake, etc... [\#146](https://github.com/pyapp-kit/psygnal/pull/146) ([tlambert03](https://github.com/tlambert03))
- chore: add deps to setup.py [\#145](https://github.com/pyapp-kit/psygnal/pull/145) ([tlambert03](https://github.com/tlambert03))
- refactor: remove PartialMethodMeta for TypeGuard func [\#144](https://github.com/pyapp-kit/psygnal/pull/144) ([tlambert03](https://github.com/tlambert03))
- refactor: don't use metaclass for signal group [\#143](https://github.com/pyapp-kit/psygnal/pull/143) ([tlambert03](https://github.com/tlambert03))

## [v0.6.1](https://github.com/pyapp-kit/psygnal/tree/v0.6.1) (2022-11-13)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.6.0.post0...v0.6.1)

**Fixed bugs:**

- fix: fix failed weakref in connect\_setattr [\#142](https://github.com/pyapp-kit/psygnal/pull/142) ([tlambert03](https://github.com/tlambert03))
- fix: fix disconnection of partials [\#134](https://github.com/pyapp-kit/psygnal/pull/134) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- chore: rename org to pyapp-kit [\#141](https://github.com/pyapp-kit/psygnal/pull/141) ([tlambert03](https://github.com/tlambert03))

## [v0.6.0.post0](https://github.com/pyapp-kit/psygnal/tree/v0.6.0.post0) (2022-11-09)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.6.0...v0.6.0.post0)

**Merged pull requests:**

- build: unskip cibuildwheel py311 [\#140](https://github.com/pyapp-kit/psygnal/pull/140) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.11.1 to 2.11.2 [\#138](https://github.com/pyapp-kit/psygnal/pull/138) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.6.0](https://github.com/pyapp-kit/psygnal/tree/v0.6.0) (2022-10-29)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.5.0...v0.6.0)

**Implemented enhancements:**

- build: drop py3.7 add py3.11 [\#135](https://github.com/pyapp-kit/psygnal/pull/135) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- chore: changelog v0.6.0 [\#137](https://github.com/pyapp-kit/psygnal/pull/137) ([tlambert03](https://github.com/tlambert03))
- build: support 3.7 again [\#136](https://github.com/pyapp-kit/psygnal/pull/136) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.10.2 to 2.11.1 [\#133](https://github.com/pyapp-kit/psygnal/pull/133) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.5.0](https://github.com/pyapp-kit/psygnal/tree/v0.5.0) (2022-10-14)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.4.2...v0.5.0)

**Implemented enhancements:**

- feat: add warning for poor usage [\#132](https://github.com/pyapp-kit/psygnal/pull/132) ([tlambert03](https://github.com/tlambert03))
- feat: add `@evented` decorator, turn any dataclass, attrs model, or pydantic model into evented [\#129](https://github.com/pyapp-kit/psygnal/pull/129) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- docs: update readme [\#131](https://github.com/pyapp-kit/psygnal/pull/131) ([tlambert03](https://github.com/tlambert03))
- docs:  documentation for evented decorator [\#130](https://github.com/pyapp-kit/psygnal/pull/130) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.10.1 to 2.10.2 [\#127](https://github.com/pyapp-kit/psygnal/pull/127) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.4.2](https://github.com/pyapp-kit/psygnal/tree/v0.4.2) (2022-09-25)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.4.1...v0.4.2)

**Fixed bugs:**

- fix: fix inheritance of property setters [\#126](https://github.com/pyapp-kit/psygnal/pull/126) ([tlambert03](https://github.com/tlambert03))
- fix: fix bug in setattr with private attrs [\#125](https://github.com/pyapp-kit/psygnal/pull/125) ([tlambert03](https://github.com/tlambert03))

## [v0.4.1](https://github.com/pyapp-kit/psygnal/tree/v0.4.1) (2022-09-22)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.4.0...v0.4.1)

**Implemented enhancements:**

- feat: Add ability to disconnect slots from Signal group directly [\#118](https://github.com/pyapp-kit/psygnal/pull/118) ([alisterburt](https://github.com/alisterburt))

**Fixed bugs:**

- fix: fix listevents docstring parameter mismatch [\#119](https://github.com/pyapp-kit/psygnal/pull/119) ([alisterburt](https://github.com/alisterburt))

**Tests & CI:**

- ci: skip building py311 wheel [\#124](https://github.com/pyapp-kit/psygnal/pull/124) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- ci\(dependabot\): bump pypa/cibuildwheel from 2.9.0 to 2.10.1 [\#123](https://github.com/pyapp-kit/psygnal/pull/123) ([dependabot[bot]](https://github.com/apps/dependabot))
- ci\(dependabot\): bump pypa/cibuildwheel from 2.8.1 to 2.9.0 [\#121](https://github.com/pyapp-kit/psygnal/pull/121) ([dependabot[bot]](https://github.com/apps/dependabot))
- build: pin cython [\#120](https://github.com/pyapp-kit/psygnal/pull/120) ([tlambert03](https://github.com/tlambert03))
- ci\(dependabot\): bump pypa/gh-action-pypi-publish from 1.5.0 to 1.5.1 [\#116](https://github.com/pyapp-kit/psygnal/pull/116) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.4.0](https://github.com/pyapp-kit/psygnal/tree/v0.4.0) (2022-07-26)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.3.5...v0.4.0)

**Implemented enhancements:**

- feat: raise exceptions as EmitLoopError [\#115](https://github.com/pyapp-kit/psygnal/pull/115) ([tlambert03](https://github.com/tlambert03))
- feat: add connect\_setitem [\#108](https://github.com/pyapp-kit/psygnal/pull/108) ([tlambert03](https://github.com/tlambert03))
- build: move entirely to pyproject, and src setup [\#101](https://github.com/pyapp-kit/psygnal/pull/101) ([tlambert03](https://github.com/tlambert03))
- add readthedocs config, make EventedCallableObjectProxy public [\#86](https://github.com/pyapp-kit/psygnal/pull/86) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- refactor: guard paramspec import [\#112](https://github.com/pyapp-kit/psygnal/pull/112) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- replace docs/requirements with extra, fix rtd install [\#87](https://github.com/pyapp-kit/psygnal/pull/87) ([tlambert03](https://github.com/tlambert03))

## [v0.3.5](https://github.com/pyapp-kit/psygnal/tree/v0.3.5) (2022-05-25)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.3.4...v0.3.5)

**Merged pull requests:**

- \[pre-commit.ci\] pre-commit autoupdate [\#85](https://github.com/pyapp-kit/psygnal/pull/85) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))
- Add documentation [\#84](https://github.com/pyapp-kit/psygnal/pull/84) ([tlambert03](https://github.com/tlambert03))
- Evented pydantic model [\#83](https://github.com/pyapp-kit/psygnal/pull/83) ([tlambert03](https://github.com/tlambert03))
- \[pre-commit.ci\] pre-commit autoupdate [\#82](https://github.com/pyapp-kit/psygnal/pull/82) ([pre-commit-ci[bot]](https://github.com/apps/pre-commit-ci))

## [v0.3.4](https://github.com/pyapp-kit/psygnal/tree/v0.3.4) (2022-05-02)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.3.3...v0.3.4)

**Implemented enhancements:**

- Add `EventedDict` [\#79](https://github.com/pyapp-kit/psygnal/pull/79) ([alisterburt](https://github.com/alisterburt))
- add `SelectableEventedList` [\#78](https://github.com/pyapp-kit/psygnal/pull/78) ([alisterburt](https://github.com/alisterburt))
- Add Throttler class [\#75](https://github.com/pyapp-kit/psygnal/pull/75) ([tlambert03](https://github.com/tlambert03))
- Add Selection model ported from napari [\#64](https://github.com/pyapp-kit/psygnal/pull/64) ([alisterburt](https://github.com/alisterburt))

**Fixed bugs:**

- Make SignalInstance weak referenceable \(Fix forwarding signals\) [\#71](https://github.com/pyapp-kit/psygnal/pull/71) ([tlambert03](https://github.com/tlambert03))

## [v0.3.3](https://github.com/pyapp-kit/psygnal/tree/v0.3.3) (2022-02-14)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.3.2...v0.3.3)

**Fixed bugs:**

- Used custom tuple for cython compatibility [\#69](https://github.com/pyapp-kit/psygnal/pull/69) ([tlambert03](https://github.com/tlambert03))

## [v0.3.2](https://github.com/pyapp-kit/psygnal/tree/v0.3.2) (2022-02-14)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.3.1...v0.3.2)

**Implemented enhancements:**

- work with older cython [\#67](https://github.com/pyapp-kit/psygnal/pull/67) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- generate gh release in CI [\#68](https://github.com/pyapp-kit/psygnal/pull/68) ([tlambert03](https://github.com/tlambert03))

## [v0.3.1](https://github.com/pyapp-kit/psygnal/tree/v0.3.1) (2022-02-12)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.3.0...v0.3.1)

**Fixed bugs:**

- Don't use `repr(obj)` when checking for Qt emit signature [\#66](https://github.com/pyapp-kit/psygnal/pull/66) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- add a magicgui test to CI [\#65](https://github.com/pyapp-kit/psygnal/pull/65) ([tlambert03](https://github.com/tlambert03))
- skip cibuildwheel tests on musllinux and i686 [\#63](https://github.com/pyapp-kit/psygnal/pull/63) ([tlambert03](https://github.com/tlambert03))

## [v0.3.0](https://github.com/pyapp-kit/psygnal/tree/v0.3.0) (2022-02-10)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.2.0...v0.3.0)

**Implemented enhancements:**

- Add EventedObjectProxy [\#62](https://github.com/pyapp-kit/psygnal/pull/62) ([tlambert03](https://github.com/tlambert03))
- Misc small changes, add iter\_signal\_instances to utils [\#61](https://github.com/pyapp-kit/psygnal/pull/61) ([tlambert03](https://github.com/tlambert03))
- Add EventedSet and EventedOrderedSet [\#59](https://github.com/pyapp-kit/psygnal/pull/59) ([tlambert03](https://github.com/tlambert03))
- add SignalGroup blocked context manager, improve inheritance, and fix strong refs [\#57](https://github.com/pyapp-kit/psygnal/pull/57) ([tlambert03](https://github.com/tlambert03))
- Add evented list \(more evented containers coming\) [\#56](https://github.com/pyapp-kit/psygnal/pull/56) ([tlambert03](https://github.com/tlambert03))
- add debug\_events util \(later changed to `monitor_events`\) [\#55](https://github.com/pyapp-kit/psygnal/pull/55) ([tlambert03](https://github.com/tlambert03))
- support Qt SignalInstance Emit [\#49](https://github.com/pyapp-kit/psygnal/pull/49) ([tlambert03](https://github.com/tlambert03))
- Add SignalGroup [\#42](https://github.com/pyapp-kit/psygnal/pull/42) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- add typesafety tests to evented containers [\#60](https://github.com/pyapp-kit/psygnal/pull/60) ([tlambert03](https://github.com/tlambert03))
- deal with changing API in benchmarks [\#43](https://github.com/pyapp-kit/psygnal/pull/43) ([tlambert03](https://github.com/tlambert03))

## [v0.2.0](https://github.com/pyapp-kit/psygnal/tree/v0.2.0) (2021-11-07)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.1.4...v0.2.0)

**Implemented enhancements:**

- Add `connect/disconnect_settattr` [\#39](https://github.com/pyapp-kit/psygnal/pull/39) ([tlambert03](https://github.com/tlambert03))
- Enable uncompiled import with PSYGNAL\_UNCOMPILED env var  [\#33](https://github.com/pyapp-kit/psygnal/pull/33) ([tlambert03](https://github.com/tlambert03))
- Add asv benchmark to CI [\#31](https://github.com/pyapp-kit/psygnal/pull/31) ([tlambert03](https://github.com/tlambert03))
- Avoid holding strong reference to decorated and partial methods [\#29](https://github.com/pyapp-kit/psygnal/pull/29) ([Czaki](https://github.com/Czaki))
- Change confusing variable name in \_acceptable\_posarg\_range [\#25](https://github.com/pyapp-kit/psygnal/pull/25) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Set SignalInstances directly as attributes on objects \(fix bug with hashable signal holders\) [\#28](https://github.com/pyapp-kit/psygnal/pull/28) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Add benchmarks for connect\_setattr [\#41](https://github.com/pyapp-kit/psygnal/pull/41) ([Czaki](https://github.com/Czaki))
- Extend emit benchmarks to include methods [\#40](https://github.com/pyapp-kit/psygnal/pull/40) ([tlambert03](https://github.com/tlambert03))
- Fix codecov CI and bring coverage back to 100 [\#34](https://github.com/pyapp-kit/psygnal/pull/34) ([tlambert03](https://github.com/tlambert03))
- Change benchmark publication approach [\#32](https://github.com/pyapp-kit/psygnal/pull/32) ([tlambert03](https://github.com/tlambert03))

**Merged pull requests:**

- Misc-typing and minor reorg [\#35](https://github.com/pyapp-kit/psygnal/pull/35) ([tlambert03](https://github.com/tlambert03))

## [v0.1.4](https://github.com/pyapp-kit/psygnal/tree/v0.1.4) (2021-10-17)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.1.3...v0.1.4)

**Implemented enhancements:**

- support python 3.10 [\#24](https://github.com/pyapp-kit/psygnal/pull/24) ([tlambert03](https://github.com/tlambert03))
- Add ability to pause & resume/reduce signals [\#23](https://github.com/pyapp-kit/psygnal/pull/23) ([tlambert03](https://github.com/tlambert03))

## [v0.1.3](https://github.com/pyapp-kit/psygnal/tree/v0.1.3) (2021-10-01)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.1.2...v0.1.3)

**Implemented enhancements:**

- add \_\_call\_\_ as alias for `emit` on SignalInstance [\#18](https://github.com/pyapp-kit/psygnal/pull/18) ([tlambert03](https://github.com/tlambert03))

## [v0.1.2](https://github.com/pyapp-kit/psygnal/tree/v0.1.2) (2021-07-12)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.1.1...v0.1.2)

**Implemented enhancements:**

- Provide signatures for common builtins [\#7](https://github.com/pyapp-kit/psygnal/pull/7) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- Add more typing tests [\#9](https://github.com/pyapp-kit/psygnal/pull/9) ([tlambert03](https://github.com/tlambert03))
- test working with qtbot [\#8](https://github.com/pyapp-kit/psygnal/pull/8) ([tlambert03](https://github.com/tlambert03))

## [v0.1.1](https://github.com/pyapp-kit/psygnal/tree/v0.1.1) (2021-07-07)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/v0.1.0...v0.1.1)

**Implemented enhancements:**

- connect decorator, optional args [\#5](https://github.com/pyapp-kit/psygnal/pull/5) ([tlambert03](https://github.com/tlambert03))

**Fixed bugs:**

- Catch inspection failures on connect \(e.g. `print`\), and improve maxargs syntax [\#6](https://github.com/pyapp-kit/psygnal/pull/6) ([tlambert03](https://github.com/tlambert03))

## [v0.1.0](https://github.com/pyapp-kit/psygnal/tree/v0.1.0) (2021-07-06)

[Full Changelog](https://github.com/pyapp-kit/psygnal/compare/bd037d2cb3cdc1c9423fd7d88ac6edfdd40f39d9...v0.1.0)

**Implemented enhancements:**

- Add readme, add `@connect` decorator [\#3](https://github.com/pyapp-kit/psygnal/pull/3) ([tlambert03](https://github.com/tlambert03))

**Tests & CI:**

- fix ci [\#2](https://github.com/pyapp-kit/psygnal/pull/2) ([tlambert03](https://github.com/tlambert03))
- ci [\#1](https://github.com/pyapp-kit/psygnal/pull/1) ([tlambert03](https://github.com/tlambert03))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
