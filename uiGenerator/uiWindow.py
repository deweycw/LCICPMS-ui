import sys 
from PyQt6.QtCore import Qt
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

		self._createPTDict()
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
		self.generalLayout.addWidget(handle, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
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
		self.DirEntry.setAlignment(Qt.AlignmentFlag.AlignRight) 
		self.topLayout.addRow("Enter directory:", self.DirEntry)
		self.topLayout.addWidget(self.DirEntry)

	def _createDisplay(self):
		'''Create the display'''
		# Create the display widget
		self.display = QLineEdit()
		self.display.setFixedHeight(35)
		self.display.setAlignment(Qt.AlignmentFlag.AlignRight) 
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
		self.calib_label.setAlignment(Qt.AlignmentFlag.AlignRight) 
		label_text = 'No calibration'
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
		print('hh')
		item = self.listwidget.currentItem()
		print('\nfile: ' + item.text())
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
			cbox.setCheckState(Qt.CheckState.Unchecked)

	def clickBox(self, cbox, state):
		if state == 2:
			print('checked: ' + cbox.text())
			if cbox.text() not in self.activeMetals:
				self.activeMetals.append(cbox.text())
		elif state == 0:
			print('Unchecked: ' + cbox.text())
			self.activeMetals.remove(cbox.text())
		else:
			print('NO BOXES CHECKED!')

	def _createPTDict(self):
		self.periodicTableDict = {'1\nH': [0, 0, 'salmon',0],
				'2\nHe': [0, 18, 'salmon',0],
				'3\nLi': [1,0, 'salmon',0],
				'4\nBe': [1, 1, 'salmon',0],
				'11\nNa': [2, 0, 'salmon',0],
				'12\nMg': [2, 1, 'salmon',0],
				'19\nK': [3, 0, 'salmon',0],
				'20\nCa': [3, 1, 'salmon',0],
				'37\nRb': [4, 0, 'salmon',0],
				'38\nSr': [4, 1, 'salmon',0],
				'55\nCs': [5, 0, 'salmon',0],
				'56\nBa': [5, 1, 'salmon',0],
				'87\nFr': [6, 0, 'salmon',0],
				'88\nRa': [6, 1, 'salmon',0],
				'21\nSc': [3, 3, 'lightblue',0],
				'22\nTi': [3, 4, 'lightblue',0],
				'23\nV': [3, 5, 'lightblue',0],
				'24\nCr': [3, 6, 'lightblue',0],
				'25\nMn': [3, 7, 'lightblue',0],
				'26\nFe': [3, 8, 'lightblue',0],
				'27\nCo': [3, 9, 'lightblue',0],
				'28\nNi': [3, 10, 'lightblue',0],
				'29\nCu': [3, 11, 'lightblue',0],
				'30\nZn': [3, 12, 'lightblue',0],
				'39\nY': [4, 3, 'lightblue',0],  ##
				'40\nZr': [4, 4, 'lightblue',0],
				'41\nNb': [4, 5, 'lightblue',0],
				'42\nMo': [4, 6, 'lightblue',0],
				'43\nTc': [4, 7, 'lightblue',0],
				'44\nRu': [4, 8, 'lightblue',0],
				'45\nRh': [4, 9, 'lightblue',0],
				'46\nPd': [4, 10, 'lightblue',0],
				'47\nAg': [4, 11, 'lightblue',0],
				'48\nCd': [4, 12, 'lightblue',0],
				'71\nLu': [5, 3, 'lightblue',0],  ##
				'72\nHf': [5, 4, 'lightblue',0],
				'73\nTa': [5, 5, 'lightblue',0],
				'74\nW': [5, 6, 'lightblue',0],
				'75\nRe': [5, 7, 'lightblue',0],
				'76\nOs': [5, 8, 'lightblue',0],
				'77\nIr': [5, 9, 'lightblue',0],
				'78\nPt': [5, 10, 'lightblue',0],
				'79\nAu': [5, 11, 'lightblue',0],
				'80\nHg': [5, 12, 'lightblue',0],
				'103\nLr': [6, 3, 'lightblue',0],  ##
				'104\nRf': [6, 4, 'lightblue',0],
				'105\nDb': [6, 5, 'lightblue',0],
				'106\nSg': [6,6, 'lightblue',0],
				'107\nBh': [6, 7, 'lightblue',0],
				'108\nHs': [6, 8, 'lightblue',0],
				'109\nMt': [6, 9, 'lightblue',0],
				'110\nDs': [6, 10, 'lightblue',0],
				'111\nRg': [6, 11, 'lightblue',0],
				'112\nCn': [6, 12, 'lightblue',0],
				'5\nB': [1, 13, 'green',0],  ##
				'6\nC': [1, 14, 'green',0],
				'7\nN': [1, 15, 'green',0],
				'8\nO': [1,16, 'green',0],
				'9\nF': [1, 17, 'green',0],
				'10\nNe': [1, 18, 'yellow',0],
				'13\nAl': [2, 13, 'green',0],  ##
				'14\nSi': [2, 14, 'green',0],
				'15\nP': [2, 15, 'green',0],
				'16\nS': [2, 16, 'green',0],
				'17\nCl': [2, 17, 'green',0],
				'18\nAr': [2, 18, 'yellow',0],
				'31\nGa': [3, 13, 'green',0],  ##
				'32\nGe': [3, 14, 'green',0],
				'33\nAs': [3, 15, 'green',0],
				'34\nSe': [3, 16, 'green',0],
				'35\nBr': [3, 17, 'green',0],
				'36\nKr': [3, 18, 'yellow',0],
				'49\nIn': [4, 13, 'green',0],  ##
				'50\nSn': [4, 14, 'green',0],
				'51\nSb': [4, 15, 'green',0],
				'52\nTe': [4, 16, 'green',0],
				'53\nI': [4, 17, 'green',0],
				'54\nXe': [4, 18, 'yellow',0],
				'81\nTl': [5, 13, 'green',0],  ##
				'82\nPb': [5, 14, 'green',0],
				'83\nBi': [5, 15, 'green',0],
				'84\nPo': [5, 16, 'green',0],
				'85\nAt': [5, 17, 'green',0],
				'86\nRn': [5, 18, 'yellow',0],
				'113\nNh': [6, 13, 'green',0],  ##
				'114\nFl': [6, 14, 'green',0],
				'115\nMc': [6, 15, 'green',0],
				'116\nLv': [6, 16, 'green',0],
				'117\nTs': [6, 17, 'green',0],
				'118\nOg': [6, 18, 'yellow',0],
				'57\nLa': [7, 2, 'orange',0], ##
				'58\nCe': [7, 3, 'orange',0],
				'59\nPr': [7, 4, 'orange',0],  ##
				'60\nNd': [7, 5, 'orange',0],
				'61\nPm': [7, 6, 'orange',0],
				'62\nSm': [7, 7, 'orange',0],
				'63\nEu': [7, 8, 'orange',0],
				'64\nGd': [7, 9, 'orange',0],
				'65\nTb': [7, 10, 'orange',0],  ##
				'66\nDy': [7, 11, 'orange',0],
				'67\nHo': [7, 12, 'orange',0],
				'68\nEr': [7, 13, 'orange',0],
				'69\nTm': [7, 14, 'orange',0],
				'70\nYb': [7, 15, 'orange',0],
				'89\nAc': [8, 2, 'orange',0], ##
				'90\nTh': [8, 3, 'orange',0],
				'91\nPa': [8, 4, 'orange',0],  ##
				'92\nU': [8, 5, 'orange',0],
				'93\nNp': [8, 6, 'orange',0],
				'94\nPu': [8, 7, 'orange',0],
				'95\nAm': [8, 8, 'orange',0],
				'96\nCm': [8, 9, 'orange',0],
				'97\nBk': [8, 10, 'orange',0],  ##
				'98\nCf': [8, 11, 'orange',0],
				'99\nEs': [8, 12, 'orange',0],
				'100\nFm': [8, 13, 'orange',0],
				'101\nMd': [8, 14, 'orange',0],
				'102\nNo': [8, 15, 'orange',0]
			}
		
		self.isotopes = {'H': ['1H'],
				'He': ['4He', '3He'],
				'Li': ['6Li', '7Li'],
				'Be': ['9Be'],
				'Na': ['22Na'],
				'Mg': ['24Mg', '25Mg','26Mg'],
				'K': ['39K', '40K', '41K'],
				'Ca': ['40Ca', '42Ca','43Ca','44Ca', '48Ca'],
				'Rb': ['85Rb', '87Rb'],
				'Sr': ['84Sr','86Sr','87Sr','88Sr'],
				'Cs': [5, 0, 'salmon',0],
				'Ba': ['132Ba','134Ba','135Ba','136Ba','137Ba','138Ba'],
				'Fr': [6, 0, 'salmon',0],
				'Ra': [6, 1, 'salmon',0],
				'Sc': [3, 3, 'lightblue',0],
				'Ti': [3, 4, 'lightblue',0],
				'V': ['50V','51V'],
				'Cr': ['50Cr','51Cr','53Cr','54Cr'],
				'Mn': ['55Mn'],
				'Fe': ['54Fe', '56Fe', '57Fe', '58Fe'],
				'Co': ['59Co'],
				'Ni': ['58Ni','60Ni','61Ni','62Ni','64Ni'],
				'Cu': ['63Cu','65Cu'],
				'Zn': ['64Zn','66Zn','67Zn','68Zn','70Zn'],
				'Y': [4, 3, 'lightblue',0],  ##
				'Zr': [4, 4, 'lightblue',0],
				'Nb': [4, 5, 'lightblue',0],
				'Mo': [4, 6, 'lightblue',0],
				'Tc': [4, 7, 'lightblue',0],
				'Ru': [4, 8, 'lightblue',0],
				'Rh': [4, 9, 'lightblue',0],
				'Pd': [4, 10, 'lightblue',0],
				'Ag': [4, 11, 'lightblue',0],
				'Cd': ['106Cd','108Cd','110Cd','111Cd','112Cd','113Cd','114Cd','116Cd'],
				'Lu': [5, 3, 'lightblue',0],  ##
				'Hf': [5, 4, 'lightblue',0],
				'Ta': [5, 5, 'lightblue',0],
				'W': [5, 6, 'lightblue',0],
				'Re': [5, 7, 'lightblue',0],
				'Os': [5, 8, 'lightblue',0],
				'Ir': [5, 9, 'lightblue',0],
				'Pt': [5, 10, 'lightblue',0],
				'Au': [5, 11, 'lightblue',0],
				'Hg': [5, 12, 'lightblue',0],
				'Lr': [6, 3, 'lightblue',0],  ##
				'Rf': [6, 4, 'lightblue',0],
				'Db': [6, 5, 'lightblue',0],
				'Sg': [6,6, 'lightblue',0],
				'Bh': [6, 7, 'lightblue',0],
				'Hs': [6, 8, 'lightblue',0],
				'Mt': [6, 9, 'lightblue',0],
				'Ds': [6, 10, 'lightblue',0],
				'Rg': [6, 11, 'lightblue',0],
				'Cn': [6, 12, 'lightblue',0],
				'B': ['10B', '11B'],  ##
				'C': ['12C', '13C', '14C'],
				'N': ['14N', '15N'],
				'O': ['16O', '17O', '18O'],
				'F': ['19F'],
				'Ne': ['20Ne', '21Ne', '22Ne'],
				'Al': ['27Al'],  ##
				'Si': ['28Si', '29Si', '30Si'],
				'P': ['31P'],
				'S': ['32S', '33S', '34S', '36S'],
				'Cl': ['35Cl', '37Cl'],
				'Ar': ['36Ar', '38Ar', '40Ar'],
				'Ga': [3, 13, 'green',0],  ##
				'Ge': [3, 14, 'green',0],
				'As': [3, 15, 'green',0],
				'Se': [3, 16, 'green',0],
				'Br': [3, 17, 'green',0],
				'Kr': [3, 18, 'yellow',0],
				'In': ['113In', '115In'],  ##
				'Sn': [4, 14, 'green',0],
				'Sb': [4, 15, 'green',0],
				'Te': [4, 16, 'green',0],
				'I': [4, 17, 'green',0],
				'Xe': [4, 18, 'yellow',0],
				'Tl': [5, 13, 'green',0],  ##
				'Pb': ['204Pb','206Pb','207Pb','208Pb'],
				'Bi': [5, 15, 'green',0],
				'Po': [5, 16, 'green',0],
				'At': [5, 17, 'green',0],
				'Rn': [5, 18, 'yellow',0],
				'Nh': [6, 13, 'green',0],  ##
				'Fl': [6, 14, 'green',0],
				'Mc': [6, 15, 'green',0],
				'U': ['233U','234U','235U','236U','238U'],
				'Np': [8, 6, 'orange',0],
				'Pu': [8, 7, 'orange',0],
				'Am': [8, 8, 'orange',0],
				'Cm': [8, 9, 'orange',0],
				'Bk': [8, 10, 'orange',0],  ##
				'Cf': [8, 11, 'orange',0],
				'Es': [8, 12, 'orange',0],
				'Fm': [8, 13, 'orange',0],
				'Md': [8, 14, 'orange',0],
				'No': [8, 15, 'orange',0],
				'Lv': [6, 16, 'green',0],
				'Ts': [6, 17, 'green',0],
				'Og': [6, 18, 'yellow',0],
				'La': [7, 2, 'orange',0], ##
				'Ce': [7, 3, 'orange',0],
				'Pr': [7, 4, 'orange',0],  ##
				'Nd': [7, 5, 'orange',0],
				'Pm': [7, 6, 'orange',0],
				'Sm': [7, 7, 'orange',0],
				'Eu': [7, 8, 'orange',0],
				'Gd': [7, 9, 'orange',0],
				'Tb': [7, 10, 'orange',0],  ##
				'Dy': [7, 11, 'orange',0],
				'Ho': [7, 12, 'orange',0],
				'Er': [7, 13, 'orange',0],
				'Tm': [7, 14, 'orange',0],
				'Yb': [7, 15, 'orange',0],
				'Ac': [8, 2, 'orange',0], ##
				'Th': [8, 3, 'orange',0],
				'Pa': [8, 4, 'orange',0]
		}