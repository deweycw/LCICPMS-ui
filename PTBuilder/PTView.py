import sys 
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import * 
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

# Create a subclass of QMainWindow to setup the periodic table gui
class PTView(QWidget):
	
	window_closed = pyqtSignal()

	def __init__(self,mainview):
		"""View initializer."""
		super(PTView,self).__init__()
		self._mainview = mainview
		self._elementLabels = []
		self.setWindowTitle('Periodic Table')
		self.setGeometry(100, 60, 800, 600)
		
		self.generalLayout = QVBoxLayout()
		self.topLayout = QVBoxLayout()
		self.bottomLayout = QHBoxLayout()
		self._centralWidget = QWidget(self)

		self.setLayout(self.generalLayout)

		self.generalLayout.addLayout(self.topLayout)
		self.generalLayout.addLayout(self.bottomLayout)

		self._createPeriodicTable()
		self._createButtons()
	
	def closeEvent(self, event):
		print(self._mainview._metals_in_file)
		self.window_closed.emit()
		event.accept()

	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout
		buttons = {'Save': (0, 0),
			'Clear': (0, 1),
			'Select All':(0,2)}
		# Create the buttons and add them to the grid layout
		for btnText, pos in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			self.buttons[btnText].setFixedSize(100, 40)
			buttonsLayout.addWidget(self.buttons[btnText], pos[0], pos[1])
		# Add buttonsLayout to the general layout
		self.bottomLayout.addLayout(buttonsLayout)

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		self.generalLayout.addWidget(handle, 0, Qt.AlignBottom | Qt.AlignRight)
		self.resize(self.sizeHint())

	def _createPeriodicTable(self):
		"""Create the buttons."""
		self.periodicTable = {}
		ptLayout = QGridLayout()
		# Button text | position on the QGridLayout

		# Create the buttons and add them to the grid layout
		for element, attr in self._mainview.periodicTableDict.items():
			self.periodicTable[element] = QPushButton(element)
			self.periodicTable[element].setFixedSize(40, 40)
			isotope_list = self._mainview.isotopes[element.split('\n')[1]]
			if len(list(set(isotope_list) & set(self._mainview._metals_in_file)))==0:
				if '59Co' in isotope_list:
					print(isotope_list,self._mainview._metals_in_file)
				self.periodicTable[element].setEnabled(False)
				self.periodicTable[element].setStyleSheet('background-color :' + attr[2])
				attr[3] = 0
			elif len(list(set(isotope_list) & set(self._mainview._metals_in_file)))>0:
				self.periodicTable[element].setEnabled(True)
				#self.periodicTable[element].setStyleSheet('background-color : yellow')
				inlist = False
				for i in isotope_list:
					if i in self._mainview.activeMetals:
						self.periodicTable[element].setStyleSheet('background-color : yellow')
						inlist = True
						attr[3] = 1
					if not inlist:
						self.periodicTable[element].setStyleSheet('background-color : ' + attr[2])
						attr[3] = 0
					
					

			ptLayout.addWidget(self.periodicTable[element], attr[0], attr[1])
		# Add buttonsLayout to the general layout
		self.topLayout.addLayout(ptLayout)
	
	def clicked(self):
		item = self.listwidget.currentItem()
		print('file: ' + item.text())
		return self.listwidget.currentItem()
	
	def setDisplayText(self, text):
		"""Set display's text."""
		self.display.setText(text)
		self.display.setFocus()

	def displayText(self):
		"""Get display's text."""
		return self.display.text()

