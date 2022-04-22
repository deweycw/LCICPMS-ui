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
from .chroma import *

class LICPMSfunctions:
    ''' model class for LCICPMS functions'''
    def __init__(self, view):
        """Controller initializer."""
        self._view = view
        
    def importData(self):
        '''imports LCICPMS .csv file'''
    #if self._view.listwidget.currentItem() is not None:
        #fdir = self._view.homeDir + self._view.listwidget.currentItem()
        print(self._view.listwidget.currentItem().text())
        fdir = self._view.homeDir + self._view.listwidget.currentItem().text()
        #df = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)
        self._data = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)
        testindex = self._data
        print(testindex)
    #self._view.setDisplayText(str(testindex))

    def plotActiveMetals(self):
        '''plots active metals for selected file'''
        activeMetalsPlot = ICPMS_Data_Class(self._data,self._view.activeMetals)
        activeMetalsPlot.chroma().show()