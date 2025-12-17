import sys 
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''

# Create a subclass of QMainWindow to setup the calibration GUI
class Calibration(QWidget):
	"""Calibration GUI"""
	def __init__(self,view):
		"""View initializer."""
		super().__init__()
		# Set some main window's properties
		self._view = view
		self.calibrationDir = ''
		self.n_area = []
		self.standards = {'Blank':[], 'Std 1':[], 'Std 2':[], 'Std 3':[], 'Std 4':[], 'Std 5':[]}
		self.metalOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd', '208Pb']
		self.activeMetals =  self.metalOptions
		#self.calCurves = self._view.calCurves

    # self.setLayout(mainLayout)
		self.setWindowTitle('LC-ICP-MS Calibration')
		self.setGeometry(100, 60, 700, 600)
		# Set the central widget
		self.generalLayout = QVBoxLayout()
		self.topLayout = QFormLayout()
		#self.midLayout = QHBoxLayout()
		self.bottomLayout = QHBoxLayout()
		self._centralWidget = QWidget(self)
		self._centralWidget.setLayout(self.generalLayout)

		self.setLayout(self.generalLayout)

		self.metalOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','115In', '208Pb']
		# Create the display and the buttons
		#self._selectDirectory()
		self._createButtons()
		self._createListbox()
		#self._createCheckBoxes()
		self._createDisplay()
		self._createPlot()
		self._createStandardsCheckBoxes()
		
		self._createStdConcEntry()
		self._createstandardsLayout()
		#self._showActiveCalibFile()
		#self._createResizeHandle()

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		self.generalLayout.addWidget(handle, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
		self.resize(self.sizeHint())

	def _createPlot(self):
		self.plotSpace = pg.PlotWidget()
		self.plotSpace.setBackground('w')
		styles = { 'font-size':'15px'}
		self.plotSpace.setLabel('left', 'ICP-MS signal (cps x 1000)', **styles)
		self.plotSpace.setLabel('bottom', "Retention time (min)", **styles)
		self.chroma = self.plotSpace
		self.generalLayout.addWidget(self.plotSpace)

	def _createStdConcEntry(self):
		self.stdEntryLayout = QVBoxLayout()
		self.stdConcEntry = QLineEdit()
		self.stdConcEntry.setFixedHeight(35)
		self.stdConcEntry.setFixedWidth(100)
		self.stdConcEntry.setAlignment(Qt.AlignmentFlag.AlignRight)
		#self.standardsLayout.addRow("Enter standard concentration:", self.stdConcEntry)
		self.stdlabel = QLabel()
		stdlabel = 'Standard conc. (ppb):'
		self.stdlabel.setText(stdlabel)

		self.stdEntryLayout.addWidget(self.stdlabel)
		self.stdEntryLayout.addWidget(self.stdConcEntry)

		self.bottomLayout.addLayout(self.stdEntryLayout)



	def _createDisplay(self):
		'''Create the display'''
		# Create the display widget
		self.display = QLineEdit()
		self.display.setFixedHeight(35)
		self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
		self.display.setReadOnly(True)
		self.generalLayout.addWidget(self.display)

	def _createCheckBoxes(self):
		self.checkBoxes = []
		optionsLayout = QHBoxLayout()
		for m in self.metalOptions:
			cbox = QCheckBox(m)
			self.checkBoxes.append(cbox)
			optionsLayout.addWidget(cbox)
		self.generalLayout.addLayout(optionsLayout)

	def _createStandardsCheckBoxes(self):  
		self.stdsRadioButtons = {}
		rbuttonLayout = QGridLayout()
		pos = [[0,0],[0,1],[0,2],[1,0],[1,1],[1,2]] 
		for s,p in zip(self.standards.keys(),pos):
			rbutton = QRadioButton(s)
			self.stdsRadioButtons[s] = rbutton
			rbuttonLayout.addWidget(rbutton, p[0], p[1])
		self.bottomLayout.addLayout(rbuttonLayout)

	def _createstandardsLayout(self):
		"""Create the integrate buttons."""
		self.integrateButtons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout
		intbuttons = {'Enter': (0,0), 'Calculate Curve': (1,0)}
		# Create the buttons and add them to the grid layout
		for btnText, pos in intbuttons.items():
			self.integrateButtons[btnText] = QPushButton(btnText)
			self.integrateButtons[btnText].setFixedSize(120, 40)
			buttonsLayout.addWidget(self.integrateButtons[btnText], pos[0], pos[1])
		# Add buttonsLayout to the general layout
		self.bottomLayout.addLayout(buttonsLayout)
		self.generalLayout.addLayout(self.bottomLayout)

	def _createListbox(self):
	
		listBoxLayout = QGridLayout()
		self.listwidget = QListWidget()
		listBoxLayout.addWidget(self.listwidget)
		self.listwidget.setMaximumHeight(250)
		self.generalLayout.addLayout(listBoxLayout)

	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout
		buttons = {#'Load': (0, 0),
				   #'Plot': (0, 1),
				   'Directory': (0,0),
				   'Reset': (0, 1),
				   'Clear Plot': (0, 2)
				  }
		# Create the buttons and add them to the grid layout
		for btnText, pos in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			self.buttons[btnText].setFixedSize(100, 40)
			buttonsLayout.addWidget(self.buttons[btnText], pos[0], pos[1])
		# Add buttonsLayout to the general layout
		self.generalLayout.addLayout(buttonsLayout)
	
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

	def clearChecks(self):
		"""Clear the display."""
		for cbox in self.checkBoxes:
			cbox.setCheckState(Qt.CheckState.Unchecked)

	def clickBox(self, cbox, state):
		if state == Qt.CheckState.Checked:
			print('checked: ' + cbox.text())
			self.activeMetals.append(cbox.text())
		   # print(self.activeMetals)
			return self.activeMetals
		elif state == Qt.CheckState.Unchecked:
			print('Unchecked: ' + cbox.text())
			self.activeMetals.remove(cbox.text())
			#print(self.activeMetals)
			return self.activeMetals
		else:
			print('Unchecked')
			return self.activeMetals


