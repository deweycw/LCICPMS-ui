import sys
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QKeySequence, QAction
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
		self.activeElements = []
		self.elementOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','115In', '208Pb']
		self._elements_in_file = []
		self._analytes_by_element = {}  # Maps element symbol to list of available analytes
		self.singleOutputFile = False
		self.baseSubtract = False

		# Periodic table data structures for PTBuilder
		self._createPeriodicTableData()

		self._createButtons()
		self._createListbox()
		self._createDisplay()
		self._createPlot()
		self._createIntegrateCheckBoxes()
		self._createIntegrateLayout()
		self._showActiveCalibFile()
		self._createStatusBar()
		self._createKeyboardShortcuts()
		self._restoreWindowState()
		self._createResizeHandle()

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		self.generalLayout.addWidget(handle, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
		self.resize(self.sizeHint())

	def _createPlot(self):
		self.plotSpace = pg.PlotWidget()
		self.plotSpace.setBackground('w')
		styles = { 'font-size':'15px'}
		self.plotSpace.setLabel('left', 'ICP-MS signal (1000s cps)', **styles)
		self.plotSpace.setLabel('bottom', "Retention time (min)", **styles)

		# Enable mouse zoom: drag to create zoom box, right-click to reset view
		self.plotSpace.setMouseEnabled(x=True, y=True)
		vb = self.plotSpace.getViewBox()
		vb.setMouseMode(pg.ViewBox.RectMode)  # Rectangular zoom mode
		vb.enableAutoRange(enable=True)  # Auto-range on first plot

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

	def _createIntegrateCheckBoxes(self):
		# Add some checkboxes to the layout
		self.integrateLayout = QHBoxLayout()
		checkboxLayout =QVBoxLayout()
		self.intbox = QCheckBox('Select integration range?')
		self.intbox.setToolTip('Click plot to set integration start and end points')
		self.oneFileBox = QCheckBox('Single output file?')
		self.oneFileBox.setToolTip('Save all integrations to a single output file')
		self.baseSubtractBox = QCheckBox('Baseline subtraction?')
		self.baseSubtractBox.setToolTip('Subtract baseline from peak area calculations')
		checkboxLayout.addWidget(self.intbox)
		checkboxLayout.addWidget(self.oneFileBox)
		checkboxLayout.addWidget(self.baseSubtractBox)
		self.integrateLayout.addLayout(checkboxLayout)

	
	def _createIntegrateLayout(self):
		"""Create the integrate buttons."""
		self.integrateButtons = {}
		self.intButtonLayout = QGridLayout()
		# Button text | position on the QGridLayout | tooltip
		intbuttons = {
			'Integrate': (0, 0, 'Integrate peaks in selected range (Ctrl+I)'),
			'Load Cal.': (0, 2, 'Load calibration file'),
			'Calibrate': (0, 3, 'Open calibration window'),
			'115In Correction': (0, 1, 'Apply indium normalization correction'),
			'Reset Integration': (1, 0, 'Clear integration ranges and results')
		}
		# Create the buttons and add them to the grid layout
		for btnText, (row, col, tooltip) in intbuttons.items():
			self.integrateButtons[btnText] = QPushButton(btnText)
			self.integrateButtons[btnText].setToolTip(tooltip)
			if 'Reset' not in btnText:
				self.integrateButtons[btnText].setFixedSize(122, 40)
			else:
				self.integrateButtons[btnText].setFixedSize(130, 40)
			self.intButtonLayout.addWidget(self.integrateButtons[btnText], row, col)

			
			
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
		self.intButtonLayout.addWidget(self.calib_label,1,3)

	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout | tooltip
		buttons = {
			'Load': (0, 0, 'Load selected file from list (Ctrl+L)'),
			'Plot': (0, 1, 'Plot chromatogram for selected elements (Ctrl+P)'),
			'Reset': (0, 2, 'Reset plot view to original scale'),
			'Directory': (0, 3, 'Select directory containing data files (Ctrl+O)'),
			'Select Elements': (0, 4, 'Open periodic table to select elements (Ctrl+E)')
		}
		# Create the buttons and add them to the grid layout
		for btnText, (row, col, tooltip) in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			self.buttons[btnText].setToolTip(tooltip)
			if btnText == 'Select Elements':
				self.buttons[btnText].setFixedSize(120, 40)
			else:
				self.buttons[btnText].setFixedSize(80, 40)
			buttonsLayout.addWidget(self.buttons[btnText], row, col)
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

	def _createPeriodicTableData(self):
		"""Create periodic table data structures for element selection."""
		# Isotope mappings for all elements (common isotopes for ICP-MS)
		self.isotopes = {
			'H': ['1H', '2H', '3H'],
			'He': ['3He', '4He'],
			'Li': ['6Li', '7Li'],
			'Be': ['9Be'],
			'B': ['10B', '11B'],
			'C': ['12C', '13C', '14C'],
			'N': ['14N', '15N'],
			'O': ['16O', '17O', '18O'],
			'F': ['19F'],
			'Ne': ['20Ne', '21Ne', '22Ne'],
			'Na': ['23Na'],
			'Mg': ['24Mg', '25Mg', '26Mg'],
			'Al': ['27Al'],
			'Si': ['28Si', '29Si', '30Si'],
			'P': ['31P'],
			'S': ['32S', '33S', '34S', '36S'],
			'Cl': ['35Cl', '37Cl'],
			'Ar': ['36Ar', '38Ar', '40Ar'],
			'K': ['39K', '40K', '41K'],
			'Ca': ['40Ca', '42Ca', '43Ca', '44Ca', '46Ca', '48Ca'],
			'Sc': ['45Sc'],
			'Ti': ['46Ti', '47Ti', '48Ti', '49Ti', '50Ti'],
			'V': ['50V', '51V'],
			'Cr': ['50Cr', '52Cr', '53Cr', '54Cr'],
			'Mn': ['55Mn'],
			'Fe': ['54Fe', '56Fe', '57Fe', '58Fe'],
			'Co': ['59Co'],
			'Ni': ['58Ni', '60Ni', '61Ni', '62Ni', '64Ni'],
			'Cu': ['63Cu', '65Cu'],
			'Zn': ['64Zn', '66Zn', '67Zn', '68Zn', '70Zn'],
			'Ga': ['69Ga', '71Ga'],
			'Ge': ['70Ge', '72Ge', '73Ge', '74Ge', '76Ge'],
			'As': ['75As'],
			'Se': ['74Se', '76Se', '77Se', '78Se', '80Se', '82Se'],
			'Br': ['79Br', '81Br'],
			'Kr': ['78Kr', '80Kr', '82Kr', '83Kr', '84Kr', '86Kr'],
			'Rb': ['85Rb', '87Rb'],
			'Sr': ['84Sr', '86Sr', '87Sr', '88Sr'],
			'Y': ['89Y'],
			'Zr': ['90Zr', '91Zr', '92Zr', '94Zr', '96Zr'],
			'Nb': ['93Nb'],
			'Mo': ['92Mo', '94Mo', '95Mo', '96Mo', '97Mo', '98Mo', '100Mo'],
			'Tc': ['97Tc', '98Tc', '99Tc'],
			'Ru': ['96Ru', '98Ru', '99Ru', '100Ru', '101Ru', '102Ru', '104Ru'],
			'Rh': ['103Rh'],
			'Pd': ['102Pd', '104Pd', '105Pd', '106Pd', '108Pd', '110Pd'],
			'Ag': ['107Ag', '109Ag'],
			'Cd': ['106Cd', '108Cd', '110Cd', '111Cd', '112Cd', '113Cd', '114Cd', '116Cd'],
			'In': ['113In', '115In'],
			'Sn': ['112Sn', '114Sn', '115Sn', '116Sn', '117Sn', '118Sn', '119Sn', '120Sn', '122Sn', '124Sn'],
			'Sb': ['121Sb', '123Sb'],
			'Te': ['120Te', '122Te', '123Te', '124Te', '125Te', '126Te', '128Te', '130Te'],
			'I': ['127I'],
			'Xe': ['124Xe', '126Xe', '128Xe', '129Xe', '130Xe', '131Xe', '132Xe', '134Xe', '136Xe'],
			'Cs': ['133Cs'],
			'Ba': ['130Ba', '132Ba', '134Ba', '135Ba', '136Ba', '137Ba', '138Ba'],
			'La': ['138La', '139La'],
			'Ce': ['136Ce', '138Ce', '140Ce', '142Ce'],
			'Pr': ['141Pr'],
			'Nd': ['142Nd', '143Nd', '144Nd', '145Nd', '146Nd', '148Nd', '150Nd'],
			'Pm': ['145Pm', '147Pm'],
			'Sm': ['144Sm', '147Sm', '148Sm', '149Sm', '150Sm', '152Sm', '154Sm'],
			'Eu': ['151Eu', '153Eu'],
			'Gd': ['152Gd', '154Gd', '155Gd', '156Gd', '157Gd', '158Gd', '160Gd'],
			'Tb': ['159Tb'],
			'Dy': ['156Dy', '158Dy', '160Dy', '161Dy', '162Dy', '163Dy', '164Dy'],
			'Ho': ['165Ho'],
			'Er': ['162Er', '164Er', '166Er', '167Er', '168Er', '170Er'],
			'Tm': ['169Tm'],
			'Yb': ['168Yb', '170Yb', '171Yb', '172Yb', '173Yb', '174Yb', '176Yb'],
			'Lu': ['175Lu', '176Lu'],
			'Hf': ['174Hf', '176Hf', '177Hf', '178Hf', '179Hf', '180Hf'],
			'Ta': ['180Ta', '181Ta'],
			'W': ['180W', '182W', '183W', '184W', '186W'],
			'Re': ['185Re', '187Re'],
			'Os': ['184Os', '186Os', '187Os', '188Os', '189Os', '190Os', '192Os'],
			'Ir': ['191Ir', '193Ir'],
			'Pt': ['190Pt', '192Pt', '194Pt', '195Pt', '196Pt', '198Pt'],
			'Au': ['197Au'],
			'Hg': ['196Hg', '198Hg', '199Hg', '200Hg', '201Hg', '202Hg', '204Hg'],
			'Tl': ['203Tl', '205Tl'],
			'Pb': ['204Pb', '206Pb', '207Pb', '208Pb'],
			'Bi': ['209Bi'],
			'Po': ['209Po', '210Po'],
			'At': ['210At', '211At'],
			'Rn': ['222Rn'],
			'Fr': ['223Fr'],
			'Ra': ['226Ra', '228Ra'],
			'Ac': ['227Ac'],
			'Th': ['232Th'],
			'Pa': ['231Pa'],
			'U': ['234U', '235U', '238U'],
			'Np': ['237Np'],
			'Pu': ['239Pu', '240Pu', '241Pu', '242Pu', '244Pu'],
			'Am': ['241Am', '243Am'],
			'Cm': ['243Cm', '244Cm', '245Cm', '246Cm', '247Cm', '248Cm'],
			'Bk': ['247Bk', '249Bk'],
			'Cf': ['249Cf', '250Cf', '251Cf', '252Cf'],
			'Es': ['252Es'],
			'Fm': ['257Fm'],
			'Md': ['258Md'],
			'No': ['259No'],
			'Lr': ['262Lr'],
			'Rf': ['267Rf'],
			'Db': ['268Db'],
			'Sg': ['271Sg'],
			'Bh': ['272Bh'],
			'Hs': ['270Hs'],
			'Mt': ['276Mt'],
			'Ds': ['281Ds'],
			'Rg': ['280Rg'],
			'Cn': ['285Cn'],
			'Nh': ['284Nh'],
			'Fl': ['289Fl'],
			'Mc': ['288Mc'],
			'Lv': ['293Lv'],
			'Ts': ['294Ts'],
			'Og': ['294Og']
		}

		# Periodic table layout: element -> [row, col, color, active_state]
		# Colors: Alkali metals=#CC80FF, Alkaline earth=#C2FF00, Transition=#FFC0C0,
		#         Post-transition=#CCB3B3, Metalloids=#FFB5B5, Nonmetals=#FF6666,
		#         Halogens=#90EE90 (light green), Noble gases=#C0FFFF,
		#         Lanthanides=#FFBFFF, Actinides=#FF99CC
		self.periodicTableDict = {
			# Period 1
			'1\nH': [0, 0, '#FF6666', 0],
			'2\nHe': [0, 17, '#C0FFFF', 0],
			# Period 2
			'3\nLi': [1, 0, '#CC80FF', 0],
			'4\nBe': [1, 1, '#C2FF00', 0],
			'5\nB': [1, 12, '#FFB5B5', 0],
			'6\nC': [1, 13, '#FF6666', 0],
			'7\nN': [1, 14, '#FF6666', 0],
			'8\nO': [1, 15, '#FF6666', 0],
			'9\nF': [1, 16, '#90EE90', 0],  # Halogen - light green
			'10\nNe': [1, 17, '#C0FFFF', 0],
			# Period 3
			'11\nNa': [2, 0, '#CC80FF', 0],
			'12\nMg': [2, 1, '#C2FF00', 0],
			'13\nAl': [2, 12, '#CCB3B3', 0],
			'14\nSi': [2, 13, '#FFB5B5', 0],
			'15\nP': [2, 14, '#FF6666', 0],
			'16\nS': [2, 15, '#FF6666', 0],
			'17\nCl': [2, 16, '#90EE90', 0],  # Halogen - light green
			'18\nAr': [2, 17, '#C0FFFF', 0],
			# Period 4
			'19\nK': [3, 0, '#CC80FF', 0],
			'20\nCa': [3, 1, '#C2FF00', 0],
			'21\nSc': [3, 2, '#FFC0C0', 0],
			'22\nTi': [3, 3, '#FFC0C0', 0],
			'23\nV': [3, 4, '#FFC0C0', 0],
			'24\nCr': [3, 5, '#FFC0C0', 0],
			'25\nMn': [3, 6, '#FFC0C0', 0],
			'26\nFe': [3, 7, '#FFC0C0', 0],
			'27\nCo': [3, 8, '#FFC0C0', 0],
			'28\nNi': [3, 9, '#FFC0C0', 0],
			'29\nCu': [3, 10, '#FFC0C0', 0],
			'30\nZn': [3, 11, '#FFC0C0', 0],
			'31\nGa': [3, 12, '#CCB3B3', 0],
			'32\nGe': [3, 13, '#FFB5B5', 0],
			'33\nAs': [3, 14, '#FFB5B5', 0],
			'34\nSe': [3, 15, '#FF6666', 0],
			'35\nBr': [3, 16, '#90EE90', 0],  # Halogen - light green
			'36\nKr': [3, 17, '#C0FFFF', 0],
			# Period 5
			'37\nRb': [4, 0, '#CC80FF', 0],
			'38\nSr': [4, 1, '#C2FF00', 0],
			'39\nY': [4, 2, '#FFC0C0', 0],
			'40\nZr': [4, 3, '#FFC0C0', 0],
			'41\nNb': [4, 4, '#FFC0C0', 0],
			'42\nMo': [4, 5, '#FFC0C0', 0],
			'43\nTc': [4, 6, '#FFC0C0', 0],
			'44\nRu': [4, 7, '#FFC0C0', 0],
			'45\nRh': [4, 8, '#FFC0C0', 0],
			'46\nPd': [4, 9, '#FFC0C0', 0],
			'47\nAg': [4, 10, '#FFC0C0', 0],
			'48\nCd': [4, 11, '#FFC0C0', 0],
			'49\nIn': [4, 12, '#CCB3B3', 0],
			'50\nSn': [4, 13, '#CCB3B3', 0],
			'51\nSb': [4, 14, '#FFB5B5', 0],
			'52\nTe': [4, 15, '#FFB5B5', 0],
			'53\nI': [4, 16, '#90EE90', 0],  # Halogen - light green
			'54\nXe': [4, 17, '#C0FFFF', 0],
			# Period 6
			'55\nCs': [5, 0, '#CC80FF', 0],
			'56\nBa': [5, 1, '#C2FF00', 0],
			'57\nLa': [5, 2, '#FFBFFF', 0],
			'72\nHf': [5, 3, '#FFC0C0', 0],
			'73\nTa': [5, 4, '#FFC0C0', 0],
			'74\nW': [5, 5, '#FFC0C0', 0],
			'75\nRe': [5, 6, '#FFC0C0', 0],
			'76\nOs': [5, 7, '#FFC0C0', 0],
			'77\nIr': [5, 8, '#FFC0C0', 0],
			'78\nPt': [5, 9, '#FFC0C0', 0],
			'79\nAu': [5, 10, '#FFC0C0', 0],
			'80\nHg': [5, 11, '#FFC0C0', 0],
			'81\nTl': [5, 12, '#CCB3B3', 0],
			'82\nPb': [5, 13, '#CCB3B3', 0],
			'83\nBi': [5, 14, '#CCB3B3', 0],
			'84\nPo': [5, 15, '#FFB5B5', 0],
			'85\nAt': [5, 16, '#90EE90', 0],  # Halogen - light green
			'86\nRn': [5, 17, '#C0FFFF', 0],
			# Period 7
			'87\nFr': [6, 0, '#CC80FF', 0],
			'88\nRa': [6, 1, '#C2FF00', 0],
			'89\nAc': [6, 2, '#FF99CC', 0],
			'104\nRf': [6, 3, '#FFC0C0', 0],
			'105\nDb': [6, 4, '#FFC0C0', 0],
			'106\nSg': [6, 5, '#FFC0C0', 0],
			'107\nBh': [6, 6, '#FFC0C0', 0],
			'108\nHs': [6, 7, '#FFC0C0', 0],
			'109\nMt': [6, 8, '#FFC0C0', 0],
			'110\nDs': [6, 9, '#FFC0C0', 0],
			'111\nRg': [6, 10, '#FFC0C0', 0],
			'112\nCn': [6, 11, '#FFC0C0', 0],
			'113\nNh': [6, 12, '#CCB3B3', 0],
			'114\nFl': [6, 13, '#CCB3B3', 0],
			'115\nMc': [6, 14, '#CCB3B3', 0],
			'116\nLv': [6, 15, '#CCB3B3', 0],
			'117\nTs': [6, 16, '#90EE90', 0],  # Halogen - light green
			'118\nOg': [6, 17, '#C0FFFF', 0],
			# Lanthanides (row 7, offset from main table)
			'58\nCe': [7, 3, '#FFBFFF', 0],
			'59\nPr': [7, 4, '#FFBFFF', 0],
			'60\nNd': [7, 5, '#FFBFFF', 0],
			'61\nPm': [7, 6, '#FFBFFF', 0],
			'62\nSm': [7, 7, '#FFBFFF', 0],
			'63\nEu': [7, 8, '#FFBFFF', 0],
			'64\nGd': [7, 9, '#FFBFFF', 0],
			'65\nTb': [7, 10, '#FFBFFF', 0],
			'66\nDy': [7, 11, '#FFBFFF', 0],
			'67\nHo': [7, 12, '#FFBFFF', 0],
			'68\nEr': [7, 13, '#FFBFFF', 0],
			'69\nTm': [7, 14, '#FFBFFF', 0],
			'70\nYb': [7, 15, '#FFBFFF', 0],
			'71\nLu': [7, 16, '#FFBFFF', 0],
			# Actinides (row 8, offset from main table)
			'90\nTh': [8, 3, '#FF99CC', 0],
			'91\nPa': [8, 4, '#FF99CC', 0],
			'92\nU': [8, 5, '#FF99CC', 0],
			'93\nNp': [8, 6, '#FF99CC', 0],
			'94\nPu': [8, 7, '#FF99CC', 0],
			'95\nAm': [8, 8, '#FF99CC', 0],
			'96\nCm': [8, 9, '#FF99CC', 0],
			'97\nBk': [8, 10, '#FF99CC', 0],
			'98\nCf': [8, 11, '#FF99CC', 0],
			'99\nEs': [8, 12, '#FF99CC', 0],
			'100\nFm': [8, 13, '#FF99CC', 0],
			'101\nMd': [8, 14, '#FF99CC', 0],
			'102\nNo': [8, 15, '#FF99CC', 0],
			'103\nLr': [8, 16, '#FF99CC', 0]
		}

		# Reverse lookup: isotope -> element symbol
		self.rev = {}
		for element, isotope_list in self.isotopes.items():
			for isotope in isotope_list:
				self.rev[isotope] = element

		# Element button key lookup: atomic number -> button key
		self.ptDictEls = {}
		for key in self.periodicTableDict.keys():
			element_symbol = key.split('\n')[1]
			self.ptDictEls[element_symbol] = key

	def _createStatusBar(self):
		"""Create status bar to show current file, elements count, and data info."""
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

		# Create permanent widgets for status bar
		self.status_file_label = QLabel("No file loaded")
		self.status_elements_label = QLabel("Elements: 0")
		self.status_data_label = QLabel("")

		# Add labels to status bar
		self.statusBar.addWidget(self.status_file_label, 1)  # Stretch factor 1
		self.statusBar.addPermanentWidget(self.status_elements_label)
		self.statusBar.addPermanentWidget(self.status_data_label)

		# Set initial status
		self.updateStatusBar()

	def updateStatusBar(self, filename=None):
		"""Update status bar with current information."""
		# Update file name
		if filename:
			self.status_file_label.setText(f"File: {os.path.basename(filename)}")
		elif self.filepath:
			self.status_file_label.setText(f"File: {os.path.basename(self.filepath)}")
		else:
			self.status_file_label.setText("No file loaded")

		# Update elements count
		elem_count = len(self.activeElements)
		self.status_elements_label.setText(f"Elements: {elem_count}")

		# Update data info if available
		if hasattr(self, 'icpms_data') and self.icpms_data is not None and self.activeElements:
			try:
				first_elem = self.activeElements[0]
				time_col = 'Time ' + first_elem
				if time_col in self.icpms_data.columns:
					time_range = self.icpms_data[time_col].max() - self.icpms_data[time_col].min()
					samples = len(self.icpms_data)
					self.status_data_label.setText(f"Time: {time_range/60:.1f} min | Samples: {samples}")
			except:
				pass

	def _createKeyboardShortcuts(self):
		"""Create keyboard shortcuts for common actions."""
		# Directory selection: Ctrl+O
		directory_action = QAction("Open Directory", self)
		directory_action.setShortcut(QKeySequence("Ctrl+O"))
		directory_action.triggered.connect(lambda: self.buttons['Directory'].click())
		self.addAction(directory_action)

		# Select Elements: Ctrl+E
		elements_action = QAction("Select Elements", self)
		elements_action.setShortcut(QKeySequence("Ctrl+E"))
		elements_action.triggered.connect(lambda: self.buttons['Select Elements'].click())
		self.addAction(elements_action)

		# Integrate: Ctrl+I
		integrate_action = QAction("Integrate", self)
		integrate_action.setShortcut(QKeySequence("Ctrl+I"))
		integrate_action.triggered.connect(lambda: self.integrateButtons['Integrate'].click())
		self.addAction(integrate_action)

		# Plot: Ctrl+P
		plot_action = QAction("Plot", self)
		plot_action.setShortcut(QKeySequence("Ctrl+P"))
		plot_action.triggered.connect(lambda: self.buttons['Plot'].click())
		self.addAction(plot_action)

		# Load: Ctrl+L
		load_action = QAction("Load", self)
		load_action.setShortcut(QKeySequence("Ctrl+L"))
		load_action.triggered.connect(lambda: self.buttons['Load'].click())
		self.addAction(load_action)

	def _restoreWindowState(self):
		"""Restore window size and position from settings."""
		settings = QSettings("LCICPMS", "DataViewer")
		geometry = settings.value("geometry")
		if geometry:
			self.restoreGeometry(geometry)

	def closeEvent(self, event):
		"""Save window state before closing."""
		settings = QSettings("LCICPMS", "DataViewer")
		settings.setValue("geometry", self.saveGeometry())
		event.accept()

