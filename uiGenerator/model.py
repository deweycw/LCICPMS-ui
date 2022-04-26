import sys 
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial
import seaborn as sns

from .chroma import *
from .pgChroma import *

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


class LICPMSfunctions:
	''' model class for LCICPMS functions'''

	def __init__(self, view):
		"""Controller initializer."""
		self._view = view
		self.intColors = sns.color_palette(n_colors = 6, as_cmap = True)
		
	def importData(self):
		'''imports LCICPMS .csv file'''
		fdir = self._view.homeDir + self._view.listwidget.currentItem().text()
		self._data = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)

	def plotActiveMetalsMP(self):
		'''plots active metals for selected file'''
		activeMetalsPlot = ICPMS_Data_Class(self._data,self._view.activeMetals)
		activeMetalsPlot.chroma().show()
	
	def plotActiveMetals(self):
		'''plots active metals for selected file'''
		self._view.chroma = plotChroma(self._view, self._view.metalOptions, self._data, self._view.activeMetals)._plotChroma()

	def integrate(self, intRange):
		'''integrates over specified x range'''
		self.intRange = intRange
		print('model')
		print('Integration range')
		print(self.intRange)
	
	def plotLowRange(self,xmin,n):
		'''plots integration range'''
		col = self.intColors[n]
		minline = pg.InfiniteLine(xmin, pen = col, angle = 90)
		self._view.plotSpace.addItem(minline) #InfiniteLine(minInt,angle = 90)
		
	def plotHighRange(self,xmax,n):
		col = self.intColors[n]
		maxline = pg.InfiniteLine(xmax, pen=col,angle = 90)
		self._view.plotSpace.addItem(maxline)