# Change Log

All notable changes will appear in this log that begins with the release of
`v1.0.0`. Changes are categorized into "Added", "Changed", "Fixed", and "Removed". To see a comparison between releases on Github, click or follow the release version number URL.

For information on the style of this change log, see [keepachangelog.com](http://keepachangelog.com/).

## [UNRELEASED](https://github.com/ceholden/TSTools/compare/v1.0.1...HEAD)

### Changed
- API: reorganized timeseries drivers into `tstools.ts_drivers.drivers` submodule [#63](https://github.com/ceholden/TSTools/issues/63)

### Added
- Add timeseries driver information to driver initialization/configuration menu [#74](https://github.com/ceholden/TSTools/issues/74)
- Add timeseries driver dependency information to initialization/configuration menu. Also add broken driver modules to list of drivers, but with clear indication of broken status and the Python exception that caused it to break [#53](https://github.com/ceholden/TSTools/issues/53)

### Fixed
- YATSM: Fix retrieval of ACCA scores from Landsat MTL files for YATSM timeseries drivers [#75](https://github.com/ceholden/TSTools/issues/75)
- YATSM: Fix bug with importing of phenology module ([commit](https://github.com/ceholden/TSTools/commit/feb4b433bfad37baf257a35cc02b3a4cbb8dc842))
- YATSM: Update to YATSM `v0.6.0` and maintain compatibility with `v0.5.0` ([commit](https://github.com/ceholden/TSTools/commit/23b6f2d0f6da099592f9ce064515fe903ae48346))
- YATSM: Fix bug when running in reverse ([commit](https://github.com/ceholden/TSTools/commit/6a21e09aac71fd6abbdc3e1d3d6da5f6bbf5de37))

## [v1.0.1](https://github.com/ceholden/TSTools/compare/v1.0.0...v1.0.1) - 2015-11-24

[Milestone v1.0.1](https://github.com/ceholden/TSTools/milestones/1.0.1)

### Changed
- QGIS 2.4 or above is now required. Reasoning: Upkeep on deprecated QGIS APIs and 2.8 is their long term support release.

### Added
- Add Vagrantfile for installing and running TSTools on Ubuntu 14.04 [#68](https://github.com/ceholden/TSTools/issues/68)

### Fixed
- Plots should include data from maximum year in date range slider [67e6960](https://github.com/ceholden/TSTools/commit/67e696083e9e70f090799a3488e9e32c32534f23)
- Fix for `matplotlib>=1.5.0` [74a12d9](https://github.com/ceholden/TSTools/commit/74a12d91963eb01ae39126e830196ec017d85d9a)
- Fixed disconnect signal for drivers without results [#67](https://github.com/ceholden/TSTools/issues/67)
- Ignore `matplotlib.style` if not available ([commit](https://github.com/ceholden/TSTools/commit/be122b4067a030851741ed87c27b53398cfef34a))
- Update `LongTermMeanPhenology` calculation in `YATSM*` drivers for `yatsm>=0.5.0` [#62](https://github.com/ceholden/TSTools/issues/62)
- Don't show GUI until plugin is loaded ([commit](https://github.com/ceholden/TSTools/commit/99224870fae815baa6418c8dd312ffe0c07b6caa))

## v1.0.0 - 2015-11-09

First official release of TSTools. Also first entry in `CHANGELOG.md`.
