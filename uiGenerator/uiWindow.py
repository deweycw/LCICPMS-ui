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

# Create a subclass of QMainWindow to setup the calculator's GUI
class PyLCICPMSUi(QMainWindow):
	"""PyCalc's View (GUI)."""
	def __init__(self):
		"""View initializer."""
		super().__init__()
		# Set some main window's properties
		self.setWindowTitle('LC-ICP-MS Data Viewer')
		self.setGeometry(100, 60,600, 600)
		# Set the central widget
		self.generalLayout = QVBoxLayout()
		self.topLayout = QFormLayout()
		self._centralWidget = QWidget(self)
		self.setCentralWidget(self._centralWidget)
		self._centralWidget.setLayout(self.generalLayout)

		self.calCurves = {}
		self.masses = {'55Mn': 55, '56Fe': 56, '59Co': 59, '60Ni': 60, '63Cu': 63, '66Zn': 66, '111Cd': 111, '127I': 127, '208Pb': 208}
		
		self.filepath = ''
		self.normAvIndium = -999.99
		self.homeDir = '' #/Users/christiandewey/'# '/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		self.activeMetals = []
		self.metalOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','115In', '208Pb']
		self.singleOutputFile = False		
		self.baseSubtract = False 

		self._createButtons()
		self._createListbox()
		self._createCheckBoxes()
		self._createDisplay()
		self._createPlot()
		self._createIntegrateCheckBoxes()
		self._createIntegrateLayout()
		self._showActiveCalibFile()
		self._createResizeHandle()

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		#self.generalLayout.addWidget(handle)
		self.generalLayout.addWidget(handle, 0, Qt.AlignBottom | Qt.AlignRight)
	   # self.__corner = Qt.BottomRightCorner

		self.resize(self.sizeHint())

	   # self.__updatePos()
	'''
	def _selectDirectory(self):
		dialog = QFileDialog()
		dialog.setWindowTitle("Select LC-ICPMS Directory")
		dialog.setViewMode(QFileDialog.Detail)      
		self.homeDir = str(dialog.getExistingDirectory(self,"Select Directory:")) + '/'
	'''
	def _createPlot(self):
		self.plotSpace = pg.PlotWidget()
		self.plotSpace.setBackground('w')
		styles = { 'font-size':'15px'}
		self.plotSpace.setLabel('left', 'ICP-MS signal (1000s cps)', **styles)
		self.plotSpace.setLabel('bottom', "Retention time (min)", **styles)
		self.chroma = self.plotSpace
		self.generalLayout.addWidget(self.plotSpace)

	def _createDirEntry(self):
		self.DirEntry = QLineEdit()
		self.DirEntry.setFixedHeight(35)
		self.DirEntry.setAlignment(Qt.AlignRight)
		self.topLayout.addRow("Enter directory:", self.DirEntry)
		self.topLayout.addWidget(self.DirEntry)

	def _createDisplay(self):
		'''Create the display'''
		# Create the display widget
		self.display = QLineEdit()
		self.display.setFixedHeight(35)
		self.display.setAlignment(Qt.AlignRight)
		self.display.setReadOnly(True)
		self.generalLayout.addWidget(self.display)

	def _createCheckBoxes(self):
		# Add some checkboxes to the layout  
		self.checkBoxes = {}      
		optionsLayout = QHBoxLayout()
		for m in self.metalOptions:
			cbox = QCheckBox(m)
			self.checkBoxes[m] = cbox
			optionsLayout.addWidget(cbox)
	   # optionwidget.stateChanged.connect(self.clickBox)
		self.generalLayout.addLayout(optionsLayout)

	def _createIntegrateCheckBoxes(self):
		# Add some checkboxes to the layout  
		#self.integrateBox= []      
		self.integrateLayout = QHBoxLayout()
		checkboxLayout =QVBoxLayout()
		self.intbox = QCheckBox('Select integration range?')
		self.oneFileBox = QCheckBox('Single output file?')
		self.baseSubtractBox = QCheckBox('Baseline subtraction?')
		checkboxLayout.addWidget(self.intbox)
		checkboxLayout.addWidget(self.oneFileBox)
		checkboxLayout.addWidget(self.baseSubtractBox)
		self.integrateLayout.addLayout(checkboxLayout)

	
	def _createIntegrateLayout(self):
		"""Create the integrate buttons."""
		self.integrateButtons = {}
		self.intButtonLayout = QGridLayout()
		# Button text | position on the QGridLayout
		intbuttons = {'Integrate': (0,0),'Load Cal.': (0,2),'Calibrate': (0,3), '115In Correction': (0,1), 'Reset Integration': (1,0)}
		# Create the buttons and add them to the grid layout
		for btnText, pos in intbuttons.items():
			self.integrateButtons[btnText] = QPushButton(btnText)			
			if 'Reset' not in btnText:
				self.integrateButtons[btnText].setFixedSize(122, 40)
			else:
				self.integrateButtons[btnText].setFixedSize(130, 40)
			self.intButtonLayout.addWidget(self.integrateButtons[btnText], pos[0],pos[1])

			
			
		self.integrateLayout.addLayout(self.intButtonLayout)
		# Add buttonsLayout to the general layout
		self.generalLayout.addLayout(self.integrateLayout)

	def _createListbox(self):
	
		listBoxLayout = QGridLayout()
		self.listwidget = QListWidget()
		listBoxLayout.addWidget(self.listwidget)
		self.listwidget.setMaximumHeight(250)
		self.generalLayout.addLayout(listBoxLayout)

	def _showActiveCalibFile(self):
		self.calib_label = QLabel()
		self.calib_label.setAlignment(Qt.AlignRight)
		label_text = 'No calibration file'
		self.calib_label.setText(label_text)
		#label_text = 
		self.intButtonLayout.addWidget(self.calib_label,1,3)	
	'''
	def _createListbox(self):
	
		listBoxLayout = QGridLayout()
		self.listwidget = QListWidget()

		test_dir = self.homeDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		i = 0
		for name in os.listdir(test_dir):
			if '.csv' in name: 
				self.listwidget.insertItem(i, name)
				i = i + 1

		self.listwidget.clicked.connect(self.clicked)
		listBoxLayout.addWidget(self.listwidget)
		self.listwidget.setMaximumHeight(250)
		self.generalLayout.addLayout(listBoxLayout)
	'''
	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout
		buttons = {'Load': (0, 0),
				   'Plot': (0, 1),
				   'Reset': (0,2),
				   'Directory': (0, 3)
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
		for cbox in self.checkBoxes.values():
			cbox.setCheckState(Qt.Unchecked)

	def clickBox(self, cbox, state):
		if state == Qt.Checked:
			print('checked: ' + cbox.text())
			if cbox.text() not in self.activeMetals:
				self.activeMetals.append(cbox.text())
			# print(self.activeMetals)
				#return self.activeMetals
		elif state == Qt.Unchecked:
			print('Unchecked: ' + cbox.text())
			self.activeMetals.remove(cbox.text())
			#print(self.activeMetals)
		else:
			print('Unchecked')

