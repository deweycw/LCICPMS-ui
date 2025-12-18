#!/usr/bin/env python3
"""Entry point script for PyInstaller builds."""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from uiGenerator.ui.main_window import PyLCICPMSUi
from uiGenerator.controllers.main_controller import PyLCICPMSCtrl
from uiGenerator.models.data_processor import LICPMSfunctions
from uiGenerator.ui.calibration_window import Calibration
from uiGenerator.controllers.calibration_controller import CalCtrlFunctions
from uiGenerator.models.calibration import CalibrateFunctions


def main():
    """Main application entry point."""
    # Create an instance of QApplication
    app = QApplication(sys.argv)

    # Create the main window and components
    view = PyLCICPMSUi()
    model = LICPMSfunctions(view=view)
    calWindow = Calibration(view=view)
    calmodel = CalibrateFunctions(mainview=view, calview=calWindow)
    calCtrl = CalCtrlFunctions(view=calWindow, model=calmodel, mainview=view)

    # Show the main window
    view.show()

    # Create the main controller
    PyLCICPMSCtrl(model=model, view=view, calwindow=calWindow)

    # Execute the main loop
    if (sys.flags.interactive != 1) or not hasattr(Qt, 'PYQT_VERSION'):
        sys.exit(app.exec())


if __name__ == '__main__':
    main()
