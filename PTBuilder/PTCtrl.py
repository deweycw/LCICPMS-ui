from posixpath import split
import sys 
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial
import json

from PTBuilder.PTView import *
from PTBuilder.PTCtrl import *
from PTBuilder.PTModel import *

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''

# Create a Controller class to connect the GUI and the model
class PTCtrl:
	"""Main Control class """
	def __init__(self, model, mainview, ptview, mainctrl):
		"""Controller initializer."""
		self._model = model
		self._view = ptview
		self._mainview = mainview
		self._mainctrl = mainctrl
		
		# Connect signals and slots
		self._connectSignals()

	def _saveElementList(self):
		self._model.plotActiveMetals()
		self._view.close()

	def _clearPeriodicTable(self):
		self._mainview.activeMetals = []
		for element, btn in self._view.periodicTable.items():
			col = self._mainview.periodicTableDict[element][2]
			self._view.periodicTable[element].setStyleSheet('background-color : '+ col)
			self._mainview.periodicTableDict[element][3] = 0

	def _resetPeriodicTable(self):
		self._mainview.activeMetals = self._mainview._metals_in_file.copy()
		print(self._mainview._metals_in_file)
		for element in self._mainview.activeMetals:
			buttonkey = self._mainview.ptDictEls[self._mainview.rev[element]]
			self._view.periodicTable[buttonkey].setStyleSheet('background-color : yellow')
			self._mainview.periodicTableDict[buttonkey][3] = 1

	def _alterElementList(self, element):
		
		split_el = element.split('\n')[1]

		isActive = self._mainview.periodicTableDict[element][3]
		print(self._mainview._metals_in_file)
		if isActive == 0:
			
			self._mainview.periodicTableDict[element][3] = 1
			self._view.periodicTable[element].setStyleSheet('background-color : yellow')
			
			isotopes = self._mainview.isotopes[split_el]

			for i in isotopes:
				self._mainview.activeMetals.append(i)
			

		elif isActive == 1:

			self._mainview.periodicTableDict[element][3] = 0
			col = self._mainview.periodicTableDict[element][2]
			self._view.periodicTable[element].setStyleSheet('background-color : '+ col)
			isotopes = self._mainview.isotopes[split_el]
			for i in isotopes:
				if i in self._mainview.activeMetals:
					self._mainview.activeMetals.remove(i)


	def _connectSignals(self):
		"""Connect signals and slots."""
		for btnText, btn in self._view.periodicTable.items():
			if btnText  in {'H'}:
				if self._view.listwidget.currentItem() is None:
					text = ''
				else:
					text = self._view.listwidget.currentItem().text()
		
				btn.clicked.connect(partial(self._buildExpression, text))

		for element, btn in self._view.periodicTable.items():
			self._view.periodicTable[element].clicked.connect(partial(self._alterElementList, element))

		self._view.buttons['Clear'].clicked.connect(self._clearPeriodicTable)
		self._view.buttons['Save'].clicked.connect(self._saveElementList)
		self._view.buttons['Select All'].clicked.connect(self._resetPeriodicTable)

