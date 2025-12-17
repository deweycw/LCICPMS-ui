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
		self._model.plotActiveElements()
		self._view.close()

	def _clearPeriodicTable(self):
		self._mainview.activeElements = []
		for element, btn in self._view.periodicTable.items():
			col = self._mainview.periodicTableDict[element][2]
			self._view.periodicTable[element].setStyleSheet('background-color : '+ col)
			self._mainview.periodicTableDict[element][3] = 0

	def _resetPeriodicTable(self):
		self._mainview.activeElements = self._mainview._elements_in_file.copy()
		for element in self._mainview.activeElements:
			buttonkey = self._mainview.ptDictEls[self._mainview.rev[element]]
			self._view.periodicTable[buttonkey].setStyleSheet('background-color : yellow')
			self._mainview.periodicTableDict[buttonkey][3] = 1

	def _alterElementList(self, element):
		from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel

		split_el = element.split('\n')[1]  # Element symbol like "Fe", "S", "U"

		# Get available analytes for this element
		if split_el not in self._mainview._analytes_by_element:
			return

		available_analytes = self._mainview._analytes_by_element[split_el]

		# Create dialog to select analytes
		dialog = QDialog(self._view)
		dialog.setWindowTitle(f'Select Analytes for {split_el}')
		layout = QVBoxLayout()

		label = QLabel(f'Select analytes/isotopes for {split_el}:')
		layout.addWidget(label)

		# Create checkboxes for each available analyte
		checkboxes = {}
		for analyte in available_analytes:
			cb = QCheckBox(analyte)
			cb.setChecked(analyte in self._mainview.activeElements)
			checkboxes[analyte] = cb
			layout.addWidget(cb)

		# Add OK and Cancel buttons
		button_layout = QHBoxLayout()
		ok_button = QPushButton('OK')
		cancel_button = QPushButton('Cancel')
		button_layout.addWidget(ok_button)
		button_layout.addWidget(cancel_button)
		layout.addLayout(button_layout)

		dialog.setLayout(layout)

		# Connect buttons
		ok_button.clicked.connect(dialog.accept)
		cancel_button.clicked.connect(dialog.reject)

		# Show dialog and process result
		if dialog.exec() == QDialog.DialogCode.Accepted:
			# Update activeElements based on checkbox states
			for analyte, cb in checkboxes.items():
				if cb.isChecked() and analyte not in self._mainview.activeElements:
					self._mainview.activeElements.append(analyte)
				elif not cb.isChecked() and analyte in self._mainview.activeElements:
					self._mainview.activeElements.remove(analyte)

			# Update button color based on whether any analytes are active
			any_active = any(analyte in self._mainview.activeElements for analyte in available_analytes)
			if any_active:
				self._mainview.periodicTableDict[element][3] = 1
				self._view.periodicTable[element].setStyleSheet('background-color : yellow')
			else:
				self._mainview.periodicTableDict[element][3] = 0
				col = self._mainview.periodicTableDict[element][2]
				self._view.periodicTable[element].setStyleSheet('background-color : ' + col)


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

