from curses import meta
import time
from datetime import datetime
from datetime import timedelta
import sys 
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial
import seaborn as sns
import csv
from uiGenerator.pgChroma import *
__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


class PTModel:
	''' model class for LCICPMS functions'''

	def __init__(self, ptview, mainview, maincontrol):
		"""Controller initializer."""
		self._ptview = ptview
		self._mainview = mainview
		self._maincontrol = maincontrol
		self.ntime = True
		self.intColors = sns.color_palette(n_colors = 6, as_cmap = True)

	def plotActiveMetals(self):
		'''plots active metals for selected file'''
		self._maincontrol._makePlot()
		

