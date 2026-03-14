# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
