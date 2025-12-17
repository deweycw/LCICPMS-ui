# LC-ICP-MS Data Viewer

A PyQt5-based desktop application for analyzing and visualizing LC-ICP-MS (Liquid Chromatography Inductively Coupled Plasma Mass Spectrometry) chromatography data.

## Features

- **Interactive Data Visualization**: Real-time chromatogram plotting using PyQtGraph
- **Multi-Metal Analysis**: Simultaneous analysis of multiple metal isotopes (Mn, Fe, Co, Ni, Cu, Zn, Cd, Pb)
- **Peak Integration**: Automatic and manual peak area calculation with baseline subtraction
- **Calibration Curves**: Linear regression-based calibration with R² and MSE metrics
- **Data Export**: Export results to CSV format with timestamps
- **115In Normalization**: Optional indium correction for signal drift

## Requirements

- **Python**: 3.8 or higher
- **Operating Systems**: Windows, macOS, Linux
- **Dependencies**: See `requirements.txt`

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/deweycw/LCICPMS-ui.git
cd LCICPMS-ui

# Create and activate virtual environment
python3 -m venv env
source env/bin/activate  # Windows: .\env\Scripts\activate

# Install the package
pip install -e .
```

### Running the Application

```bash
# After installation, run from anywhere
lcicpms-ui
```

**Alternative**: Run as Python module
```bash
python -m uiGenerator
```

## Usage

1. **Select Directory**: Click "Directory" to choose folder containing CSV data files
2. **Load Data**: Select a CSV file from the list
3. **Select Metals**: Check boxes for metals to analyze
4. **View Chromatogram**: Interactive plot displays automatically
5. **Integrate Peaks**:
   - Check "Select integration range?"
   - Click plot to set start/end points
   - Click "Integrate" to calculate peak areas
6. **Calibration** (optional):
   - Click "Calibrate" to open calibration window
   - Select directory with standard samples
   - Integrate peaks for each standard
   - Click "Calculate Curve" to generate calibration

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

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is available for scientific research and educational purposes.

## Contact

Christian Dewey - [@deweycw](https://github.com/deweycw)

Project Link: [https://github.com/deweycw/LCICPMS-ui](https://github.com/deweycw/LCICPMS-ui)

## Acknowledgments

- PyQt5 for the GUI framework
- PyQtGraph for interactive plotting
- scikit-learn for calibration curve fitting
