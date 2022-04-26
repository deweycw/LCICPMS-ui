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

# Create a subclass of QMainWindow to setup the calibration GUI
class Calibration(QWidget):
	"""Calibration GUI"""
	def __init__(self,view):
		"""View initializer."""
		super().__init__()
		# Set some main window's properties
		self._view = view
		self.activeMetals = []
		self.n_area = []
		self.standards = {'Blank':[], 'Std 1':[], 'Std 2':[], 'Std 3':[], 'Std 4':[], 'Std 5':[]}
		self.metalOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','115In', '208Pb']
		self.setWindowTitle('LC-ICP-MS Calibration')
		self.setFixedSize(700, 1000)
		# Set the central widget
		self.generalLayout = QVBoxLayout()
		self.topLayout = QFormLayout()
		self._centralWidget = QWidget(self)
		self._centralWidget.setLayout(self.generalLayout)

		self.metalOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','115In', '208Pb']
		# Create the display and the buttons
		#self._selectDirectory()
		self._createButtons()
		self._createListbox()
		self._createCheckBoxes()
		self._createDisplay()
		self._createPlot()
		self._createStandardsCheckBoxes()
		self._createstandardsLayout()
		self._createStdConcEntry()


	def _selectDirectory(self):
		dialog = QFileDialog()
		dialog.setWindowTitle("Select LC-ICPMS Directory")
		dialog.setViewMode(QFileDialog.Detail)
		self._view.homeDir = str(dialog.getExistingDirectory(self,"Select Directory:")) + '/'
   
	def _createPlot(self):
		self.plotSpace = pg.PlotWidget()
		self.plotSpace.setBackground('w')
		styles = { 'font-size':'15px'}
		self.plotSpace.setLabel('left', 'ICP-MS signal intensity (cps x 1000)', **styles)
		self.plotSpace.setLabel('bottom', "Retention time (min)", **styles)
		self.chroma = self.plotSpace
		self.generalLayout.addWidget(self.plotSpace)

	def _createStdConcEntry(self):
		self.stdEntryLayout = QVBoxLayout()
		self.stdConcEntry = QLineEdit()
		self.stdConcEntry.setFixedHeight(35)
		self.stdConcEntry.setFixedWidth(100)
		self.stdConcEntry.setAlignment(Qt.AlignRight)
		#self.standardsLayout.addRow("Enter standard concentration:", self.stdConcEntry)
		self.stdlabel = QLabel()
		stdlabel = 'Standard concentration:'
		self.stdlabel.setText(stdlabel)

		self.ok_button = QPushButton('Enter')
		self.ok_button.setFixedSize(80, 40)
		
		self.stdEntryLayout.addWidget(self.stdlabel)
		self.stdEntryLayout.addWidget(self.stdConcEntry)
		self.stdEntryLayout.addWidget(self.ok_button)

		
		self.generalLayout.addLayout(self.stdEntryLayout)

	def _createDisplay(self):
		'''Create the display'''
		# Create the display widget
		self.display = QLineEdit()
		self.display.setFixedHeight(35)
		self.display.setAlignment(Qt.AlignRight)
		self.display.setReadOnly(True)
		self.generalLayout.addWidget(self.display)

	def _createCheckBoxes(self):
		self.checkBoxes = []      
		optionsLayout = QHBoxLayout()
		for m in self.metalOptions:
			cbox = QCheckBox(m)
			self.checkBoxes.append(cbox)
			optionsLayout.addWidget(cbox)
	   # optionwidget.stateChanged.connect(self.clickBox)
		self.generalLayout.addLayout(optionsLayout)

	def _createStandardsCheckBoxes(self):  
		self.stdsRadioButtons = []
		self.standardsLayout = QHBoxLayout()
		for s in self.standards.keys():
			rbutton = QRadioButton(s)
			self.stdsRadioButtons.append(rbutton)
			self.standardsLayout.addWidget(rbutton)
		#self.checkBoxes.append(self.intbox)
		#self.standardsLayout.addWidget(self.intbox)
   #    # optionwidget.stateChanged.connect(self.clickBox)
   #     self.generalLayout.addLayout(self.standardsLayout)
	
	def _createstandardsLayout(self):
		"""Create the integrate buttons."""



		self.integrateButtons = {}

		# Button text | position on the QGridLayout
		intbuttons = {'Integrate': (0,0), 'Assign Conc.': (0,1)}
		# Create the buttons and add them to the grid layout
		for btnText, pos in intbuttons.items():
			self.integrateButtons[btnText] = QPushButton(btnText)
			self.integrateButtons[btnText].setFixedSize(80, 40)
			self.standardsLayout.addWidget(self.integrateButtons[btnText], pos[1])
		# Add buttonsLayout to the general layout
		self.generalLayout.addLayout(self.standardsLayout)

	def _createListbox(self):
		'''Create listbox'''
		listBoxLayout = QGridLayout()
		self.listwidget = QListWidget()

		test_dir = self._view.homeDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		i = 0
		for name in os.listdir(test_dir):
			if '.csv' in name: 
				self.listwidget.insertItem(i, name)
				i = i + 1

		self.listwidget.clicked.connect(self.clicked)
		listBoxLayout.addWidget(self.listwidget)
		self.generalLayout.addLayout(listBoxLayout)

	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout
		buttons = {'Import': (0, 0),
				   'Plot': (0, 1),
				 #  'Integrate': (0,2),
				   'Reset': (0, 3)
				  }
		# Create the buttons and add them to the grid layout
		for btnText, pos in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			self.buttons[btnText].setFixedSize(80, 40)
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
			cbox.setCheckState(Qt.Unchecked)

	def clickBox(self, cbox, state):
		if state == Qt.Checked:
			print('checked: ' + cbox.text())
			self.activeMetals.append(cbox.text())
		   # print(self.activeMetals)
			return self.activeMetals
		elif state == Qt.Unchecked:
			print('Unchecked: ' + cbox.text())
			self.activeMetals.remove(cbox.text())
			#print(self.activeMetals)
			return self.activeMetals
		else:
			print('Unchecked')
			return self.activeMetals


