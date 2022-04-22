import sys 
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial

from uiGenerator.uiWindow import *
from uiGenerator.uiCtrl import *
from uiGenerator.model import *


# Client code
def main():
    """Main function."""
    # Create an instance of QApplication
    pycalc = QApplication(sys.argv)
    # Show the calculator's GU
    view = PyLCICPMSUi()
    model = LICPMSfunctions(view = view)
    view.show()

    # Create instances of the model and the controller
    PyLCICPMSCtrl(model=model, view=view)
    # Execute the calculator's main loop
    sys.exit(pycalc.exec_())

if __name__ == '__main__':
    main()