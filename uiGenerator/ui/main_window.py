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

		# File comparison mode (supports up to 12 files)
		self.compareMode = False
		self.comparisonFiles = []  # List of filenames
		self.comparisonData = []  # List of dataframes
		self.comparisonLabels = {}  # Dictionary mapping filename to custom legend label

		# Periodic table data structures for PTBuilder
		self._createPeriodicTableData()

		self._createMenuBar()
		self._createButtons()
		self._createListbox()
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

		# Enhanced styling with darker text and larger font
		styles = {'font-size': '16px', 'color': '#000'}
		self.plotSpace.setLabel('left', 'Signal Intensity (cps)', **styles)
		self.plotSpace.setLabel('bottom', 'Time (min)', **styles)

		# Make axes and ticks darker and more visible
		axis_pen = pg.mkPen(color='#000', width=2)
		for axis in ['left', 'bottom', 'right', 'top']:
			self.plotSpace.getAxis(axis).setPen(axis_pen)
			self.plotSpace.getAxis(axis).setTextPen('#000')
			# Increase tick font size and make darker
			self.plotSpace.getAxis(axis).setStyle(tickFont=pg.QtGui.QFont('Arial', 12))

		# Add custom tick formatter for y-axis to handle large values
		left_axis = self.plotSpace.getAxis('left')

		def custom_tick_strings(values, scale, spacing):
			"""Custom formatter for y-axis: integers for < 10000, proper exponential notation for >= 10000."""
			# Unicode superscript mapping
			superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
			                   '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
			                   '-': '⁻', '+': '⁺'}

			def to_superscript(text):
				"""Convert text to Unicode superscripts."""
				return ''.join(superscript_map.get(c, c) for c in str(text))

			strings = []
			for v in values:
				if abs(v) >= 10000:
					# Use proper mathematical exponential notation: 1×10⁴
					import math
					if v == 0:
						strings.append('0')
						continue

					# Calculate exponent and mantissa
					exponent = int(math.floor(math.log10(abs(v))))
					mantissa = v / (10 ** exponent)

					# Format mantissa (remove .0 if it's a whole number)
					if mantissa == int(mantissa):
						mantissa_str = str(int(mantissa))
					else:
						mantissa_str = f'{mantissa:.1f}'

					# Create formatted string: mantissa × 10^exponent
					exp_str = f'{mantissa_str}×10{to_superscript(exponent)}'
					strings.append(exp_str)
				else:
					# Normal formatting for values < 10000 (up to 4 digits), no decimals
					strings.append(f'{int(v)}')
			return strings

		# Apply custom tick formatter
		left_axis.tickStrings = custom_tick_strings

		# Enable mouse zoom: drag to create zoom box, right-click to reset view
		self.plotSpace.setMouseEnabled(x=True, y=True)
		vb = self.plotSpace.getViewBox()
		vb.setMouseMode(pg.ViewBox.RectMode)  # Rectangular zoom mode
		vb.enableAutoRange(enable=True)  # Auto-range on first plot

		# Set axis ranges to not go below 0
		vb.setLimits(xMin=0, yMin=0)
		self.plotSpace.setXRange(0, 10, padding=0.02)  # Small padding to prevent cutoff
		self.plotSpace.setYRange(0, 100, padding=0.05)  # 5% padding at top and bottom

		# Add crosshair cursor with coordinates display
		self._setupCrosshair()

		# Create horizontal layout for plot and legend
		plotLayout = QHBoxLayout()
		plotLayout.setContentsMargins(5, 5, 5, 5)
		plotLayout.setSpacing(15)  # Space between plot and legend
		plotLayout.addWidget(self.plotSpace, stretch=4)

		# Create separate legend panel
		self._createLegendPanel()
		plotLayout.addWidget(self.legendPanel, stretch=1)

		# Create a container widget for plot + legend (needed for export)
		self.plotContainer = QWidget()
		self.plotContainer.setStyleSheet("background-color: white;")
		self.plotContainer.setLayout(plotLayout)

		self.chroma = self.plotSpace
		self.generalLayout.addWidget(self.plotContainer)

	def _createLegendPanel(self):
		"""Create a separate panel for the legend with polished styling."""
		self.legendPanel = QWidget()
		self.legendPanel.setMinimumWidth(250)
		self.legendPanel.setMaximumWidth(400)  # Increased to accommodate comparison mode labels

		# Set white background and border for professional appearance
		self.legendPanel.setStyleSheet("""
			QWidget {
				background-color: white;
				border: 2px solid #000;
				border-radius: 5px;
			}
		""")

		legendLayout = QVBoxLayout()
		legendLayout.setContentsMargins(12, 12, 12, 12)
		legendLayout.setSpacing(8)
		self.legendPanel.setLayout(legendLayout)

		# Container for legend items (will be wrapped in scroll area if needed)
		self.legendContainer = QWidget()
		self.legendContainer.setStyleSheet("background-color: white;")
		self.legendItemsLayout = QVBoxLayout()
		self.legendItemsLayout.setSpacing(12)  # Increased spacing between items
		self.legendItemsLayout.setContentsMargins(12, 12, 12, 12)
		self.legendContainer.setLayout(self.legendItemsLayout)

		# Store reference to layout so we can add scroll area later if needed
		self.legendContentLayout = legendLayout
		legendLayout.addWidget(self.legendContainer)

		# Add spacer at bottom
		legendLayout.addStretch()

	def updateLegend(self, elements, color_dict, format_isotopes=True):
		"""Update the legend with current elements and colors.

		Args:
			elements: List of element names or file labels
			color_dict: Dictionary mapping elements to colors
			format_isotopes: If True, apply subscript/superscript formatting for isotopes.
			                 If False, display labels as plain text (for file names).
		"""
		# Clear existing legend items
		while self.legendItemsLayout.count():
			item = self.legendItemsLayout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()

		# Check if we need a scroll area (more than 6 items)
		needs_scroll = len(elements) > 6

		# Remove existing scroll area or container from layout if present
		# First, check what's currently in the layout and remove it
		while self.legendContentLayout.count() > 0:  # No title anymore, so clear everything
			item = self.legendContentLayout.takeAt(0)  # Remove first item (scroll area or container)
			if item.widget():
				widget = item.widget()
				widget.setParent(None)  # Remove from parent instead of deleteLater

		# Add new legend items with enhanced styling
		from uiGenerator.utils.analyte_formatter import format_analyte_html
		for element in elements:
			itemWidget = QWidget()
			itemWidget.setStyleSheet("""
				QWidget {
					background-color: white;
					padding: 6px;
					border-radius: 3px;
				}
				QWidget:hover {
					background-color: #f0f0f0;
				}
			""")
			itemLayout = QHBoxLayout()
			itemLayout.setContentsMargins(6, 6, 6, 6)
			itemLayout.setSpacing(10)
			itemWidget.setLayout(itemLayout)

			# Color indicator box with enhanced styling
			colorBox = QLabel()
			color = color_dict.get(element, (0.5, 0.5, 0.5))

			# Convert color to RGB values
			if isinstance(color, str):
				# Handle string color names
				if color == 'gray' or color == 'grey':
					r, g, b = 128, 128, 128
				else:
					# Default for unknown string colors
					r, g, b = 128, 128, 128
			elif hasattr(color, '__iter__') and len(color) >= 3:
				# Handle tuple/list of RGB values (0-1 range from seaborn)
				r, g, b = int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
			else:
				# Default fallback
				r, g, b = 128, 128, 128

			colorBox.setStyleSheet(f"""
				QLabel {{
					background-color: rgb({r},{g},{b});
					border: 2px solid #000;
					border-radius: 2px;
				}}
			""")
			colorBox.setFixedSize(18, 18)
			itemLayout.addWidget(colorBox)

			# Element label with formatted text and enhanced styling
			# Only apply isotope formatting if requested (not for file names in comparison mode)
			formatted_name = format_analyte_html(element) if format_isotopes else element
			elementLabel = QLabel(formatted_name)
			elementLabel.setStyleSheet("""
				QLabel {
					font-size: 13px;
					font-weight: 500;
					color: #000;
					padding-left: 2px;
					background-color: transparent;
					border: none;
				}
			""")
			elementLabel.setTextFormat(Qt.TextFormat.RichText)
			# Don't wrap - use eliding instead for cleaner look
			elementLabel.setWordWrap(False)
			elementLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
			elementLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
			# Set minimum width to prevent extreme shrinking
			elementLabel.setMinimumWidth(150)
			itemLayout.addWidget(elementLabel, stretch=1)

			self.legendItemsLayout.addWidget(itemWidget)

		# Wrap in scroll area if needed
		if needs_scroll:
			if not hasattr(self, 'legendScrollArea') or self.legendScrollArea is None:
				self.legendScrollArea = QScrollArea()
				self.legendScrollArea.setWidgetResizable(True)
				self.legendScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
				self.legendScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
				self.legendScrollArea.setStyleSheet("""
					QScrollArea {
						background-color: white;
						border: none;
					}
				""")
			self.legendScrollArea.setWidget(self.legendContainer)
			self.legendContentLayout.addWidget(self.legendScrollArea)
		else:
			# Add container directly without scroll area
			self.legendScrollArea = None
			self.legendContentLayout.addWidget(self.legendContainer)

		# Add spacer back if it was removed
		if self.legendContentLayout.count() < 2:
			self.legendContentLayout.addStretch()

	def _setupCrosshair(self):
		"""Setup crosshair cursor and coordinates display."""
		# Create crosshair lines
		self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.PenStyle.DashLine))
		self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.PenStyle.DashLine))
		self.plotSpace.addItem(self.vLine, ignoreBounds=True)
		self.plotSpace.addItem(self.hLine, ignoreBounds=True)

		# Create text label for coordinates
		self.coordLabel = pg.TextItem(anchor=(0, 1), color='black', fill=pg.mkBrush(255, 255, 255, 200))
		self.plotSpace.addItem(self.coordLabel)

		# Initially hide crosshair
		self.vLine.setVisible(False)
		self.hLine.setVisible(False)
		self.coordLabel.setVisible(False)

		# Connect mouse movement
		self.plotSpace.scene().sigMouseMoved.connect(self._updateCrosshair)
		self.proxy = pg.SignalProxy(self.plotSpace.scene().sigMouseMoved, rateLimit=60, slot=self._updateCrosshair)

	def _updateCrosshair(self, evt):
		"""Update crosshair position and coordinates display."""
		# Get mouse position
		if isinstance(evt, tuple):
			pos = evt[0]
		else:
			pos = evt

		if self.plotSpace.sceneBoundingRect().contains(pos):
			mousePoint = self.plotSpace.plotItem.vb.mapSceneToView(pos)
			x, y = mousePoint.x(), mousePoint.y()

			# Update crosshair position
			self.vLine.setPos(x)
			self.hLine.setPos(y)

			# Update coordinate label
			self.coordLabel.setText(f'Time: {x:.2f} min\nIntensity: {y:.0f} cps')
			self.coordLabel.setPos(x, y)

			# Show crosshair
			self.vLine.setVisible(True)
			self.hLine.setVisible(True)
			self.coordLabel.setVisible(True)
		else:
			# Hide crosshair when mouse leaves plot
			self.vLine.setVisible(False)
			self.hLine.setVisible(False)
			self.coordLabel.setVisible(False)

	def _createDirEntry(self):
		self.DirEntry = QLineEdit()
		self.DirEntry.setFixedHeight(35)
		self.DirEntry.setAlignment(Qt.AlignmentFlag.AlignRight)
		self.topLayout.addRow("Enter directory:", self.DirEntry)
		self.topLayout.addWidget(self.DirEntry)


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
		"""Create file list and comparison list side by side."""
		listBoxLayout = QHBoxLayout()

		# Left side: Main file list
		leftLayout = QVBoxLayout()
		fileListLabel = QLabel("Data Files")
		fileListLabel.setStyleSheet("font-weight: bold;")
		leftLayout.addWidget(fileListLabel)

		self.listwidget = QListWidget()
		self.listwidget.setMaximumHeight(250)
		leftLayout.addWidget(self.listwidget)

		listBoxLayout.addLayout(leftLayout)

		# Middle: Transfer buttons
		buttonLayout = QVBoxLayout()
		buttonLayout.addStretch()

		self.addToCompareBtn = QPushButton("Add →")
		self.addToCompareBtn.setToolTip("Add selected file to comparison list")
		self.addToCompareBtn.setMaximumWidth(80)
		self.addToCompareBtn.setEnabled(False)
		buttonLayout.addWidget(self.addToCompareBtn)

		self.removeFromCompareBtn = QPushButton("← Remove")
		self.removeFromCompareBtn.setToolTip("Remove selected file from comparison list")
		self.removeFromCompareBtn.setMaximumWidth(80)
		self.removeFromCompareBtn.setEnabled(False)
		buttonLayout.addWidget(self.removeFromCompareBtn)

		self.clearCompareBtn = QPushButton("Clear All")
		self.clearCompareBtn.setToolTip("Clear all files from comparison list")
		self.clearCompareBtn.setMaximumWidth(80)
		self.clearCompareBtn.setEnabled(False)
		buttonLayout.addWidget(self.clearCompareBtn)

		buttonLayout.addStretch()
		listBoxLayout.addLayout(buttonLayout)

		# Right side: Comparison list
		rightLayout = QVBoxLayout()
		compareListLabel = QLabel("Comparison Files (up to 12)")
		compareListLabel.setStyleSheet("font-weight: bold;")
		rightLayout.addWidget(compareListLabel)

		self.compareListWidget = QListWidget()
		self.compareListWidget.setMaximumHeight(250)
		self.compareListWidget.setStyleSheet("""
			QListWidget {
				background-color: #f0f8ff;
				border: 2px solid #4682b4;
			}
		""")
		rightLayout.addWidget(self.compareListWidget)

		listBoxLayout.addLayout(rightLayout)

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
			'Reset': (0, 0, 'Reset plot view to original scale'),
			'Export Plot': (0, 1, 'Export plot as PNG, SVG, or PDF'),
			'Directory': (0, 2, 'Select directory containing data files (Ctrl+O)'),
			'Select Elements': (0, 3, 'Open periodic table to select elements (Ctrl+E)')
		}
		# Create the buttons and add them to the grid layout
		for btnText, (row, col, tooltip) in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			self.buttons[btnText].setToolTip(tooltip)
			if btnText == 'Select Elements':
				self.buttons[btnText].setFixedSize(120, 40)
			elif btnText == 'Export Plot':
				self.buttons[btnText].setFixedSize(90, 40)
			else:
				self.buttons[btnText].setFixedSize(80, 40)
			buttonsLayout.addWidget(self.buttons[btnText], row, col)

		# Add comparison mode button to button row for prominence
		self.compareFilesBtn = QPushButton('Compare')
		self.compareFilesBtn.setCheckable(True)
		self.compareFilesBtn.setToolTip('Compare data from multiple files (up to 12 files, requires 2+ files in comparison list, 1 element only)')
		self.compareFilesBtn.setEnabled(False)  # Disabled until 2+ files added
		self.compareFilesBtn.setStyleSheet("""
			QPushButton {
				font-weight: bold;
				padding: 5px;
			}
			QPushButton:checked {
				background-color: #4682b4;
				color: white;
			}
		""")
		if 'Export Plot' in self.buttons:
			self.compareFilesBtn.setFixedSize(self.buttons['Export Plot'].size())
		buttonsLayout.addWidget(self.compareFilesBtn, 0, 4)

		# Add buttonsLayout to the general layout
		self.generalLayout.addLayout(buttonsLayout)
	
	def clicked(self):
		print('hh')
		item = self.listwidget.currentItem()
		print('\nfile: ' + item.text())
		return self.listwidget.currentItem()
	

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

	def _restoreWindowState(self):
		"""Restore window size and position from settings."""
		settings = QSettings("LCICPMS", "DataViewer")
		geometry = settings.value("geometry")
		if geometry:
			self.restoreGeometry(geometry)

	def _createMenuBar(self):
		"""Create menu bar with File menu and recent directories."""
		menubar = self.menuBar()

		# File menu
		file_menu = menubar.addMenu('&File')

		# Open Directory action
		open_dir_action = QAction('&Open Directory...', self)
		open_dir_action.setShortcut('Ctrl+O')
		open_dir_action.triggered.connect(lambda: self.buttons['Directory'].click())
		file_menu.addAction(open_dir_action)

		file_menu.addSeparator()

		# Recent Directories submenu
		self.recent_menu = file_menu.addMenu('Recent Directories')
		self._updateRecentDirectoriesMenu()

		# Clear Recent action
		file_menu.addSeparator()
		clear_recent_action = QAction('Clear Recent Directories', self)
		clear_recent_action.triggered.connect(self._clearRecentDirectories)
		file_menu.addAction(clear_recent_action)

		file_menu.addSeparator()

		# Workspace actions
		save_workspace_action = QAction('&Save Workspace...', self)
		save_workspace_action.setShortcut('Ctrl+S')
		save_workspace_action.triggered.connect(self._saveWorkspace)
		file_menu.addAction(save_workspace_action)

		load_workspace_action = QAction('&Load Workspace...', self)
		load_workspace_action.setShortcut('Ctrl+Shift+O')
		load_workspace_action.triggered.connect(self._loadWorkspace)
		file_menu.addAction(load_workspace_action)

		file_menu.addSeparator()

		# Exit action
		exit_action = QAction('E&xit', self)
		exit_action.setShortcut('Ctrl+Q')
		exit_action.triggered.connect(self.close)
		file_menu.addAction(exit_action)

	def _updateRecentDirectoriesMenu(self):
		"""Update the recent directories menu."""
		self.recent_menu.clear()

		settings = QSettings("LCICPMS", "DataViewer")
		recent_dirs = settings.value("recentDirectories", [])

		if not recent_dirs:
			no_recent = QAction('No recent directories', self)
			no_recent.setEnabled(False)
			self.recent_menu.addAction(no_recent)
			return

		for directory in recent_dirs[:5]:  # Show max 5
			if os.path.exists(directory):
				action = QAction(directory, self)
				action.triggered.connect(lambda checked, d=directory: self._openRecentDirectory(d))
				self.recent_menu.addAction(action)

	def _openRecentDirectory(self, directory):
		"""Open a recent directory."""
		self.homeDir = directory + '/'
		# Trigger the directory loading logic from controller
		if hasattr(self, '_controller'):
			self._controller._createListbox()
			self.integrateButtons['Calibrate'].setEnabled(True)
			self.integrateButtons['Load Cal.'].setEnabled(True)
			self.integrateButtons['115In Correction'].setEnabled(True)
			self.statusBar.showMessage(f'Loaded directory: {directory}', 3000)

	def _clearRecentDirectories(self):
		"""Clear the recent directories list."""
		settings = QSettings("LCICPMS", "DataViewer")
		settings.setValue("recentDirectories", [])
		self._updateRecentDirectoriesMenu()
		self.statusBar.showMessage('Recent directories cleared', 2000)

	def addRecentDirectory(self, directory):
		"""Add a directory to the recent list."""
		settings = QSettings("LCICPMS", "DataViewer")
		recent_dirs = settings.value("recentDirectories", [])

		# Remove if already exists
		if directory in recent_dirs:
			recent_dirs.remove(directory)

		# Add to front of list
		recent_dirs.insert(0, directory)

		# Keep only last 5
		recent_dirs = recent_dirs[:5]

		settings.setValue("recentDirectories", recent_dirs)
		self._updateRecentDirectoriesMenu()

	def _saveWorkspace(self):
		"""Save current workspace state to a file."""
		from PyQt6.QtWidgets import QFileDialog, QMessageBox
		import json

		# Show file dialog
		default_name = "workspace.lcicpms"
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"Save Workspace",
			default_name,
			"LC-ICP-MS Workspace (*.lcicpms);;All Files (*)"
		)

		if not file_path:
			return  # User cancelled

		try:
			# Collect workspace state
			workspace = {
				'version': '1.0',
				'homeDir': self.homeDir,
				'activeElements': self.activeElements,
				'calCurves': self.calCurves,
				'singleOutputFile': self.singleOutputFile,
				'baseSubtract': self.baseSubtract,
			}

			# Add current file if one is selected
			if self.listwidget.currentItem() is not None:
				workspace['currentFile'] = self.listwidget.currentItem().text()

			# Add integration ranges if controller is available
			if hasattr(self, '_controller'):
				workspace['intRange'] = self._controller._intRange

			# Save to file
			with open(file_path, 'w') as f:
				json.dump(workspace, f, indent=2)

			self.statusBar.showMessage(f'Workspace saved to {file_path}', 5000)

		except Exception as e:
			QMessageBox.warning(
				self,
				'Save Error',
				f'Failed to save workspace: {str(e)}',
				QMessageBox.StandardButton.Ok
			)

	def _loadWorkspace(self):
		"""Load workspace state from a file."""
		from PyQt6.QtWidgets import QFileDialog, QMessageBox
		import json

		# Show file dialog
		file_path, _ = QFileDialog.getOpenFileName(
			self,
			"Load Workspace",
			"",
			"LC-ICP-MS Workspace (*.lcicpms);;All Files (*)"
		)

		if not file_path:
			return  # User cancelled

		try:
			# Load workspace file
			with open(file_path, 'r') as f:
				workspace = json.load(f)

			# Restore directory
			if 'homeDir' in workspace and workspace['homeDir']:
				self.homeDir = workspace['homeDir']
				if hasattr(self, '_controller'):
					self._controller._createListbox()
					self.integrateButtons['Calibrate'].setEnabled(True)
					self.integrateButtons['Load Cal.'].setEnabled(True)
					self.integrateButtons['115In Correction'].setEnabled(True)

			# Restore selected elements
			if 'activeElements' in workspace:
				self.activeElements = workspace['activeElements']

			# Restore calibration curves
			if 'calCurves' in workspace:
				self.calCurves = workspace['calCurves']
				if self.calCurves:
					self.calib_label.setText('Calibration loaded')

			# Restore settings
			if 'singleOutputFile' in workspace:
				self.singleOutputFile = workspace['singleOutputFile']
				self.oneFileBox.setChecked(workspace['singleOutputFile'])

			if 'baseSubtract' in workspace:
				self.baseSubtract = workspace['baseSubtract']
				self.baseSubtractBox.setChecked(workspace['baseSubtract'])

			# Restore current file and plot
			if 'currentFile' in workspace and workspace['currentFile']:
				# Find and select the file in the list
				items = self.listwidget.findItems(workspace['currentFile'], Qt.MatchFlag.MatchExactly)
				if items:
					self.listwidget.setCurrentItem(items[0])
					# This will trigger auto-load and plot

			# Restore integration ranges
			if 'intRange' in workspace and hasattr(self, '_controller'):
				self._controller._intRange = workspace['intRange']
				# Redraw integration markers if ranges exist
				if len(workspace['intRange']) >= 2:
					from ..models.data_processor import LICPMSfunctions
					model = self._controller._model
					for i in range(0, len(workspace['intRange']), 2):
						if i + 1 < len(workspace['intRange']):
							model.plotLowRange(workspace['intRange'][i], i // 2)
							model.plotHighRange(workspace['intRange'][i + 1], i // 2)

			self.statusBar.showMessage(f'Workspace loaded from {file_path}', 5000)

		except Exception as e:
			QMessageBox.warning(
				self,
				'Load Error',
				f'Failed to load workspace: {str(e)}',
				QMessageBox.StandardButton.Ok
			)

	def closeEvent(self, event):
		"""Save window state before closing."""
		settings = QSettings("LCICPMS", "DataViewer")
		settings.setValue("geometry", self.saveGeometry())
		event.accept()

