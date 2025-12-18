# LC-ICP-MS Data Viewer

A PyQt6-based desktop application for analyzing and visualizing LC-ICP-MS (Liquid Chromatography Inductively Coupled Plasma Mass Spectrometry) chromatography data.

## Features

### Core Functionality
- **Interactive Data Visualization**: Real-time chromatogram plotting using PyQtGraph
- **Multi-Metal Analysis**: Simultaneous analysis of multiple metal isotopes (Mn, Fe, Co, Ni, Cu, Zn, Cd, Pb)
- **Peak Integration**: Automatic and manual peak area calculation with baseline subtraction
- **Calibration Curves**: Linear regression-based calibration with R² and MSE metrics
- **115In Normalization**: Optional indium correction for signal drift

### File Comparison (v1.0.0)
- **Compare up to 12 files** simultaneously with color-coded traces
- **Custom legend labels**: Double-click to edit file labels in the plot legend
- **Dynamic updates**: Plot automatically refreshes as files are added/removed
- **Dedicated comparison interface** with intuitive Add/Remove controls

### Enhanced Export (v1.0.0)
- **Flexible export options**: Choose to export plot image, data CSV, and/or Python script
- **Exact reproduction**: Exported plots match your current zoom level and view
- **Publication-ready**: High-DPI PNG/SVG/PDF output with proper formatting
- **Standalone scripts**: Generated Python scripts recreate plots with minimal dependencies

## Requirements

- **Python**: 3.8 or higher
- **Operating Systems**: Windows, macOS, Linux
- **Dependencies**: See `requirements.txt`

## Quick Start

### Installation from Source (Recommended)

**For maximum security and transparency, we recommend running from source:**

```bash
# 1. Clone the repository
git clone https://github.com/deweycw/LCICPMS-ui.git
cd LCICPMS-ui

# 2. Create and activate virtual environment (recommended)
python3 -m venv env
source env/bin/activate  # On Windows: .\env\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python run_lcicpms.py
```

**Alternative**: Install as package
```bash
pip install -e .
lcicpms-ui
```

### Security Note

> ⚠️ **About Standalone Executables**: This application is currently distributed as open-source Python code. If you download pre-built executables (when available), please note:
>
> - Windows SmartScreen may show warnings for unsigned applications
> - This is normal for applications without expensive code-signing certificates
> - **We recommend running from source** to verify the code yourself
> - Always download from official GitHub releases only
> - Check SHA256 checksums before running (provided in releases)
>
> Running from source (as shown above) is the most secure option and allows you to inspect the code before execution.

## Usage

### Basic Workflow

1. **Select Directory**: Click "Directory" to choose folder containing CSV data files
2. **Load Data**: Select a CSV file from the list
3. **Select Elements**: Click "Select Elements" to open periodic table and choose elements to analyze
4. **View Chromatogram**: Interactive plot displays automatically with zoom/pan controls
5. **Export Plot**: Click "Export Plot" to save as PNG/SVG/PDF with optional data and script

### File Comparison Mode

1. **Select one element** from the periodic table (comparison mode requires exactly 1 element)
2. **Add files**: Select files from the main list and click "Add →" (up to 12 files)
3. **Customize labels** (optional): Double-click files in the comparison list to edit legend labels
4. **Activate comparison**: Click the "Compare" button
5. **Dynamic updates**: Add or remove files - the plot updates automatically!

### Peak Integration

1. **Enable selection**: Check "Select integration range?"
2. **Mark range**: Click plot to set start and end points
3. **Integrate**: Click "Integrate" to calculate peak areas
4. **Baseline subtraction** (optional): Check "Baseline subtraction?" for background correction

### Calibration

1. Click "Calibrate" to open calibration window
2. Select directory with standard samples
3. Integrate peaks for each standard concentration
4. Click "Calculate Curve" to generate calibration with R² and MSE metrics

## Data Format

Input CSV files should have semicolon-separated values with format:
```
Header line
Time 56Fe;56Fe;Time 60Ni;60Ni;...
0.0;1000;0.0;1200;...
0.1;1050;0.1;1250;...
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black .
flake8 uiGenerator tests --max-line-length=120
```

### Project Structure

```
LCICPMS-ui/
├── uiGenerator/              # Main package
│   ├── ui/                   # User interface components
│   │   ├── main_window.py
│   │   └── calibration_window.py
│   ├── controllers/          # Application controllers
│   │   ├── main_controller.py
│   │   └── calibration_controller.py
│   ├── models/               # Business logic
│   │   ├── data_processor.py
│   │   └── calibration.py
│   └── plotting/             # Visualization utilities
│       ├── interactive.py    # PyQtGraph plots
│       ├── static.py         # Matplotlib plots
│       └── stacked.py
├── tests/                    # Test suite
├── setup.py                  # Package configuration
├── requirements.txt          # Dependencies
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=uiGenerator --cov-report=term

# Run specific test file
pytest tests/test_data_processor.py
```

## Output Files

The application generates:
- **Concentration files**: `concentrations_uM_all.csv` - Metal concentrations in µM
- **Peak area files**: `peakareas_counts_all.csv` - Integrated peak areas
- **Calibration files**: `calibration_curve.calib` - JSON format calibration data
- **Calibration plots**: `{metal}_calibration.png` - Visualization of calibration curves

## Troubleshooting

### Windows Execution Policy Error
If you encounter an error when activating the virtual environment on Windows:
```powershell
Set-ExecutionPolicy AllSigned
```
Run this command as Administrator, then retry activation.

### Import Errors
Ensure the package is installed:
```bash
pip install -e .
```

### GUI Not Displaying
Make sure PyQt5 is properly installed:
```bash
pip install --force-reinstall PyQt5
```

## Building and Distribution

### For End Users

Download pre-built executables from the [Releases page](https://github.com/deweycw/LCICPMS-ui/releases/latest).

### For Developers

See detailed build instructions:
- **[DISTRIBUTION.md](DISTRIBUTION.md)** - Quick start guide for building and releasing
- **[BUILDING.md](BUILDING.md)** - Comprehensive build documentation

**Quick build:**
```bash
# Linux/macOS
./build.sh

# Windows
build.bat
```

**Create a release:**
```bash
git tag v0.3.0
git push origin v0.3.0
# GitHub Actions automatically builds and publishes
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Citing

If you use LCICPMS-ui in your research, please cite it:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

```bibtex
@software{dewey_lcicpms_ui,
  author       = {Dewey, Christian and Boiteau, Rene},
  title        = {LCICPMS-ui: LC-ICP-MS Data Viewer},
  year         = {2025},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.XXXXXXX},
  url          = {https://doi.org/10.5281/zenodo.XXXXXXX}
}
```

> **Note**: Replace `XXXXXXX` with the actual Zenodo DOI after the first release is archived.

## License

This project is available for scientific research and educational purposes.

## Contact

Christian Dewey - [@deweycw](https://github.com/deweycw)

Project Link: [https://github.com/deweycw/LCICPMS-ui](https://github.com/deweycw/LCICPMS-ui)

## Acknowledgments

- PyQt6 for the GUI framework
- PyQtGraph for interactive plotting
- scikit-learn for calibration curve fitting
