#!/usr/bin/env python3
"""
Entry point for LCICPMS-ui application
This script is used by PyInstaller to create standalone executables
"""

import sys
import os

# Add the package directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function
from uiGenerator.__main__ import main

if __name__ == '__main__':
    main()
