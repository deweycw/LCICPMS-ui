import sys 
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial

from uiGenerator.uiWindow import *
from uiGenerator.uiCtrl import *
from uiGenerator.model import *
from uiGenerator.calWindowUI import *
from uiGenerator.calCntrl import *
from uiGenerator.calibrate import *

# Client code
def main():
    """Main function."""
    # Create an instance of QApplication
    pycalc = QApplication(sys.argv)
    # Show the calculator's GU
    view = PyLCICPMSUi()
    model = LICPMSfunctions(view = view)
    calWindow = Calibration(view = view)
    calmodel = CalibrateFunctions(mainview = view, calview = calWindow)
    calCtrl = CalCtrlFunctions(view = calWindow, model = calmodel, mainview = view)
    view.show()

    # Create instances of the model and the controller
    PyLCICPMSCtrl(model=model, view=view,calwindow= calWindow)
    # Execute the main loop
    if (sys.flags.interactive != 1) or not hasattr(Qt, 'PYQT_VERSION'):
        pycalc.exec()
    #sys.exit(pycalc.exec_())

if __name__ == '__main__':
    main()