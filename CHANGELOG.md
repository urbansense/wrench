# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-03-21

### Added
- Multidatastreams support for SensorThings harvester (#53)
- Tools CLI with experiment, evaluate, and pipeline commands (#45, #56)
- PR meta checks workflow enforcing Conventional Commits and PR hygiene (#67)
- Renovate config for automated dependency updates (#59)

### Fixed
- YAKE keyword extraction bug (#55)
- Tools CLI using `items` instead of `devices` (#46)
- Minor inconsistencies across components (#47)

### Changed
- License changed to Apache 2.0 (#44)

## [0.3.0] - 2025-09-17

### Added
- BERTopic and LDA groupers (#43)
- Clustering grouper (#34)
- KINETIC grouper improvements (#35)
- SensorThings metadata builder improvements (#37)
- Basic scheduler for periodic pipeline execution (#31)
- Early stopping support in pipeline (#30)
- Pipeline loading from config file (#32)

## [0.2.0] - 2025-01-01

### Added
- Multidatastreams support for SensorThings harvester
- Refactored tools CLI with new experiment, evaluate, and pipeline commands
- KINETIC grouper with hierarchical clustering and LLM integration
- LDA and BERTopic grouper implementations
- SensorThings metadata enricher
- SDDI/CKAN cataloger
- Scheduler for periodic pipeline execution
- Modular pipeline architecture with async support

### Fixed
- YAKE keyword extraction bug in KINETIC grouper

## [0.1.0] - 2024-01-01

### Added
- Initial release
- Base pipeline architecture
- SensorThings harvester
- SDDI cataloger

[Unreleased]: https://github.com/urbansense/wrench/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/urbansense/wrench/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/urbansense/wrench/releases/tag/v0.1.0
