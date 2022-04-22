import sys 
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial


__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


# Create a Controller class to connect the GUI and the model
class PyLCICPMSCtrl:
    """PyCalc Controller class."""
    def __init__(self, model, view):
        """Controller initializer."""
        self._model = model
        self._view = view
        self._data = None
        # Connect signals and slots
        self._connectSignals()

    def _buildExpression(self, sub_exp):
        """Build expression."""
        expression = self._view.displayText() + sub_exp
        self._view.setDisplayText(expression)

    def _clearForm(self):
        ''' clears check boxes and nulls data '''
        self._view.clearChecks()
        self._data = None
        self._view.buttons['Plot'].setEnabled(False)
        self._view.plotSpace.clear()
        print('data cleared')

    def _importAndActivatePlotting(self):
        '''activates plotting function after data imported'''
        self._model.importData()
        self._view.plotSpace.clear()
        self._view.buttons['Plot'].setEnabled(True)
        self._view.setDisplayText(self._view.listwidget.currentItem().text())

    def _connectSignals(self):
        """Connect signals and slots."""
        for btnText, btn in self._view.buttons.items():
            if btnText  in {'Import'}:
                if self._view.listwidget.currentItem() is None:
                    text = ''
                else:
                    text = self._view.listwidget.currentItem().text()

                btn.clicked.connect(partial(self._buildExpression, text))
            #if btnText in {'Plot'}:
            #    btn.clicked.connect(self._importData)
            #elif btnText in {'Reset'}:
            #    btn.clicked.connect(self._view.clearChecks)
            #    print('here22')


        for cbox in self._view.checkBoxes:
            cbox.stateChanged.connect(partial( self._view.clickBox, cbox) )

       # for l in self._view.listwidget
        
        #self._view.setDisplayText(testindex)

        #if self._view.listwidget.currentItem() is not None:
        self._view.buttons['Import'].clicked.connect(self._importAndActivatePlotting)
        self._view.buttons['Plot'].setEnabled(False)
        self._view.buttons['Plot'].clicked.connect(self._model.plotActiveMetals)
        self._view.buttons['Reset'].clicked.connect(self._clearForm)
        #if self._data is not None:
        #    testindex = self._data.iloc[0,1]
        #    self._view.setDisplayText(testindex)