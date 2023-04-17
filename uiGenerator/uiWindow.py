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
		self.filepath = ''
		self.normAvIndium = -999.99
		self.homeDir = '' #/Users/christiandewey/'# '/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		self.activeMetals = []
		self.singleOutputFile = False		
		self.baseSubtract = False 
		self.active_metal_isotopes = []
		self._metals_in_file =[]

		self._createPTDict()
		self._createButtons()
		self._createListbox()
		self._createPlot()
		self._createIntegrateCheckBoxes()
		self._createIntegrateLayout()
		self._showActiveCalibFile()
		self._createResizeHandle()

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		self.generalLayout.addWidget(handle, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
		self.resize(self.sizeHint())

	def _createPlot(self):
		self.plotSpace = pg.PlotWidget()
		self.plotSpace.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)

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

	def _createCheckBoxes(self):
		self.checkBoxes = {}      
		optionsLayout = QHBoxLayout()
		for m in self.metalOptions:
			cbox = QCheckBox(m)
			self.checkBoxes[m] = cbox
			optionsLayout.addWidget(cbox)
		self.generalLayout.addLayout(optionsLayout)

	def _createIntegrateCheckBoxes(self):
		self.integrateLayout = QHBoxLayout()
		self.checkboxLayout =QVBoxLayout()
		checkboxLayout = self.checkboxLayout
		self.intbox = QCheckBox('Select integration range?')
		self.oneFileBox = QCheckBox('Single output file?')
		self.baseSubtractBox = QCheckBox('Baseline subtraction?')
		checkboxLayout.addWidget(self.intbox)
		checkboxLayout.addWidget(self.oneFileBox)
		checkboxLayout.addWidget(self.baseSubtractBox)
		self.integrateLayout.addLayout(checkboxLayout)

	def _createIntegrateLayout(self):
		self.integrateButtons = {}
		self.intButtonLayout = QGridLayout()
		intbuttons = {'Integrate': (0,0),'Load Cal.': (0,2),'Reset': (0,3), '115In Correction': (0,1)}
		for btnText, pos in intbuttons.items():
			self.integrateButtons[btnText] = QPushButton(btnText)			
			if 'Reset' not in btnText:
				self.integrateButtons[btnText].setFixedSize(122, 40)
			else:
				self.integrateButtons[btnText].setFixedSize(130, 40)
			self.intButtonLayout.addWidget(self.integrateButtons[btnText], pos[0],pos[1])
			
		self.integrateLayout.addLayout(self.intButtonLayout)
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

	def _createButtons(self):
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout
		buttons = {'Directory': (0, 0),
	     		   'Calibrate': (0,1),
				   'Select Elements': (0,3)
				  }
		for btnText, pos in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			if btnText == 'Directory':
				self.buttons[btnText].setFixedSize(80, 40)
			else:
				self.buttons[btnText].setFixedSize(110, 40)
			buttonsLayout.addWidget(self.buttons[btnText], pos[0], pos[1])
		self.generalLayout.addLayout(buttonsLayout)
	
	def clicked(self):
		item = self.listwidget.currentItem()
		print('\nfile: ' + item.text())
		return self.listwidget.currentItem()

	def clearChecks(self):
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
				'Cs': ['133Cs'],
				'Ba': ['132Ba','134Ba','135Ba','136Ba','137Ba','138Ba'],
				'Fr': ['223Fr'],
				'Ra': ['223Ra' ,'224Ra','226Ra','228Ra'],
				'Sc': ['45Sc'],
				'Ti': ['46Ti','47Ti','48Ti','49Ti','50Ti'],
				'V': ['50V','51V'],
				'Cr': ['50Cr','51Cr','53Cr','54Cr'],
				'Mn': ['55Mn'],
				'Fe': ['54Fe', '56Fe', '57Fe', '58Fe'],
				'Co': ['59Co'],
				'Ni': ['58Ni','60Ni','61Ni','62Ni','64Ni'],
				'Cu': ['63Cu','65Cu'],
				'Zn': ['64Zn','66Zn','67Zn','68Zn','70Zn'],
				'Y': ['89Y'], 
				'Zr': ['90Zr','91Zr','92Zr','94Zr','96Zr'],
				'Nb': ['93Nb'],
				'Mo': ['92Mo','94Mo','95Mo','96Mo','97Mo','98Mo','100Mo'],
				'Tc': ['97Tc','98Tc','99Tc'],
				'Ru': ['96Ru','98Ru','99Ru','100Ru','101Ru','102Ru','104Ru'],
				'Rh': ['103Rh'],
				'Pd': ['102Pd','104Pd','108Pd','110Pd'],
				'Ag': ['107Ag','109Ag'],
				'Cd': ['106Cd','108Cd','110Cd','111Cd','112Cd','113Cd','114Cd','116Cd'],
				'Lu': ['175Lu','176Lu'],  ##
				'Hf': ['174Hf','176Hf','177Hf','178Hf','179Hf','180Hf'],
				'Ta': ['180Ta','181Ta'],
				'W': ['180W','182W','183W','184W','186W'],
				'Re': ['185Re', '187Re'],
				'Os': ['184Os','186Os','187Os','188Os','189Os','190Os','192Os'],
				'Ir': ['191Ir','193Ir'],
				'Pt': ['190Pt','192Pt','194Pt','195Pt','196Pt','198Pt'],
				'Au': ['197Au'],
				'Hg': ['196Hg','198Hg','199Hg','200Hg','201Hg','202Hg','204Hg'],
				'Lr': ['262Lr'],  ##
				'Rf': ['267Rf'],
				'Db': ['268Db'],
				'Sg': ['271Sg'],
				'Bh': ['272Bh'],
				'Hs': ['270Hs'],
				'Mt': ['276Mt'],
				'Ds': ['281Ds'],
				'Rg': ['280Rg'],
				'Cn': ['285Cn'],
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
				'Ga': ['69Ga','71Ga'],  ##
				'Ge': ['70Ge','72Ge','73Ge','74Ge','76Ge'],
				'As': ['75As'],
				'Se': ['80Se','82Se'],
				'Br': ['79Br','81Br'],
				'Kr': ['78Kr','80Kr','82Kr','83Kr','84Kr','86Kr'],
				'In': ['113In', '115In'],  ##
				'Sn': ['112Sn','114Sn','115Sn','116Sn','117Sn','118Sn','119Sn','120Sn','122Sn','124Sn'],
				'Sb': ['121Sb','123Sb'],
				'Te': ['120Te','122Te','123Te','124Te','125Te','126Te','128Te','130Te'],
				'I': ['127I'],
				'Xe': ['124Xe','126Xe','128Xe','129Xe','130Xe','131Xe','132Xe','134Xe','136Xe'],
				'Tl': ['203Tl','205Tl'],  ##
				'Pb': ['204Pb','206Pb','207Pb','208Pb'],
				'Bi': ['209Bi'],
				'Po': ['209Po','210Po'],
				'At': ['210At','211At'],
				'Rn': ['211Rn','220Rn'],
				'Nh': ['284Nh'],  ##
				'Fl': ['289Fl'],
				'Mc': ['288Mc'],
				'U': ['233U','234U','235U','236U','238U'],
				'Np': ['236Np','237Np'],
				'Pu': ['238Pu','239Pu','240Pu','241Pu','242Pu','244Pu'],
				'Am': ['241Am','243Am'],
				'Cm': ['243Cm','244Cm','245Cm','246Cm','247Cm','248Cm'],
				'Bk': ['247Bk','249Bk'],  ##
				'Cf': ['249Cf','250Cf','251Cf','252Cf'],
				'Es': ['252Es'],
				'Fm': ['257Fm'],
				'Md': ['258Md'],
				'No': ['259No'],
				'Lv': ['293Lv'],
				'Ts': ['292Ts'],
				'Og': ['294Og'],
				'La': ['138La','139La'], ##
				'Ce': ['136Ce','138Ce','140Ce','142Ce'],
				'Pr': ['141Pr'],  ##
				'Nd': ['142Nd','143Nd','144Nd','145Nd','146Nd','148Nd','150Nd'],
				'Pm': ['145Pm','147Pm'],
				'Sm': ['144Sm','147Sm','148Sm','149Sm','150Sm','152Sm','154Sm'],
				'Eu': ['151Eu','153Eu'],
				'Gd': ['152Gd','154Gd','155Gd','156Gd','157Gd','158Gd','160Gd'],
				'Tb': ['159Tb'],  ##
				'Dy': ['156Dy','158Dy','160Dy','161Dy','162Dy','163Dy','164Dy'],
				'Ho': ['165Ho'],
				'Er': ['162Er','164Er','166Er','167Er','168Er','170Er'],
				'Tm': ['169Tm'],
				'Yb': ['168Yb','170Yb','171Yb','172Yb','173Yb','174Yb','176Yb'],
				'Ac': ['227Ac'], ##
				'Th': ['230Th','232Th'],
				'Pa': ['231Pa']
		}

		self.rev = {}
		for k,v in zip(self.isotopes.keys(), self.isotopes.values()):
			for vi in v:
				self.rev[vi] = k

		self.ptDictEls = {}
		for k,el in zip(self.periodicTableDict.keys(), self.isotopes.keys()):
			self.ptDictEls[el] = k
