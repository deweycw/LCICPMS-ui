# Changelog

All notable changes to LCICPMS-ui will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automatic update checker with GitHub Releases integration
- Standalone executable builds for Windows, macOS, and Linux
- Automated build system with GitHub Actions
- Comprehensive build documentation

## [0.2.0] - 2024-XX-XX

### Added
- Integration with lcicpms library for data processing
- Intelligent CSV parsing with automatic format detection
- Support for TQ (Triple Quad) mode data files
- Periodic table element selection with analyte dialogs
- Analyte-specific selection for TQ mode (oxides, isotopes, etc.)
- Thicker plot lines for better visibility (4px instead of 2px)
- Auto-open directory selection dialog on startup
- Directory dialog starts in home directory by default
- Mouse-drag zoom functionality on plots

### Changed
- Replaced manual integration loops with lcicpms.Integrate
- Replaced hardcoded CSV parsing with RawICPMSData
- Updated all "metals" terminology to "elements"
- Improved periodic table to support any element detected by ICP-MS
- Element mapping now groups analytes by element symbol

### Fixed
- Periodic table now correctly detects TQ mode analytes
- Indium correction works with both standard and TQ mode formats
- Active elements cleared when loading new files to prevent errors
- Color palette generation now dynamic based on active elements

## [0.1.0] - 2022-04-21

### Added
- Initial release
- PyQt5-based GUI for LC-ICP-MS data visualization
- Peak integration functionality
- Calibration curve generation
- Export to CSV

[Unreleased]: https://github.com/deweycw/LCICPMS-ui/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/deweycw/LCICPMS-ui/releases/tag/v0.2.0
[0.1.0]: https://github.com/deweycw/LCICPMS-ui/releases/tag/v0.1.0
