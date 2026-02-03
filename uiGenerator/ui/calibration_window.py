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
		self.elementOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd', '208Pb']
		self.activeElements =  self.elementOptions
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

		self.elementOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','115In', '208Pb']
		self.elements_in_stdfile = []  # Elements found in the loaded standard file
		# Create the display and the buttons
		self._createButtons()
		self._createListbox()
		self._createDisplay()
		self._createPlot()
		self._createStandardsTable()
		self._createActionButtons()

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		self.generalLayout.addWidget(handle, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
		self.resize(self.sizeHint())

	def _createPlot(self):
		self.plotSpace = pg.PlotWidget()
		self.plotSpace.setBackground('w')

		# Enhanced styling with darker text and larger font (matching main window)
		styles = {'font-size': '16px', 'color': '#000'}
		self.plotSpace.setLabel('left', 'Signal Intensity (cps)', **styles)
		self.plotSpace.setLabel('bottom', 'Time (min)', **styles)

		# Make axes and ticks darker and more visible (matching main window)
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
			import math
			# Unicode superscript mapping
			superscript_map = {'0': '\u2070', '1': '\u00b9', '2': '\u00b2', '3': '\u00b3', '4': '\u2074',
			                   '5': '\u2075', '6': '\u2076', '7': '\u2077', '8': '\u2078', '9': '\u2079',
			                   '-': '\u207b', '+': '\u207a'}

			def to_superscript(text):
				"""Convert text to Unicode superscripts."""
				return ''.join(superscript_map.get(c, c) for c in str(text))

			strings = []
			for v in values:
				if abs(v) >= 10000:
					if v == 0:
						strings.append('0')
						continue
					exponent = int(math.floor(math.log10(abs(v))))
					mantissa = v / (10 ** exponent)
					if mantissa == int(mantissa):
						mantissa_str = str(int(mantissa))
					else:
						mantissa_str = f'{mantissa:.1f}'
					exp_str = f'{mantissa_str}\u00d710{to_superscript(exponent)}'
					strings.append(exp_str)
				else:
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
		self.plotSpace.setXRange(0, 10, padding=0.02)
		self.plotSpace.setYRange(0, 100, padding=0.05)

		self.chroma = self.plotSpace
		self.generalLayout.addWidget(self.plotSpace)

	def _createStandardsTable(self):
		"""Create the standards table for entering calibration data."""
		tableLayout = QVBoxLayout()

		# Label for the table
		tableLabel = QLabel("Calibration Standards")
		tableLabel.setStyleSheet("font-weight: bold;")
		tableLayout.addWidget(tableLabel)

		# Create the table widget
		self.standardsTable = QTableWidget()
		self.standardsTable.setColumnCount(4)
		self.standardsTable.setHorizontalHeaderLabels(['File', 'Standard Name', 'Conc. (ppb)', 'Peak Area'])

		# Set column widths
		self.standardsTable.setColumnWidth(0, 150)  # File
		self.standardsTable.setColumnWidth(1, 100)  # Standard Name
		self.standardsTable.setColumnWidth(2, 80)   # Concentration
		self.standardsTable.setColumnWidth(3, 100)  # Peak Area

		# Configure table behavior
		self.standardsTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.standardsTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		self.standardsTable.setAlternatingRowColors(True)
		self.standardsTable.setMaximumHeight(200)

		# Make File and Peak Area columns read-only (handled in addStandardRow)

		tableLayout.addWidget(self.standardsTable)

		# Buttons for table management
		tableButtonLayout = QHBoxLayout()

		self.addStandardBtn = QPushButton("Add Standard")
		self.addStandardBtn.setToolTip("Add the current file as a calibration standard")
		self.addStandardBtn.setFixedSize(100, 30)
		self.addStandardBtn.setEnabled(False)
		tableButtonLayout.addWidget(self.addStandardBtn)

		self.removeStandardBtn = QPushButton("Remove")
		self.removeStandardBtn.setToolTip("Remove the selected standard from the table")
		self.removeStandardBtn.setFixedSize(80, 30)
		self.removeStandardBtn.setEnabled(False)
		tableButtonLayout.addWidget(self.removeStandardBtn)

		tableButtonLayout.addStretch()
		tableLayout.addLayout(tableButtonLayout)

		self.generalLayout.addLayout(tableLayout)

	def addStandardRow(self, filename, standard_name=""):
		"""Add a new row to the standards table."""
		row = self.standardsTable.rowCount()
		self.standardsTable.insertRow(row)

		# File column (read-only)
		file_item = QTableWidgetItem(filename)
		file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
		self.standardsTable.setItem(row, 0, file_item)

		# Standard Name column (editable)
		name_item = QTableWidgetItem(standard_name if standard_name else f"Std {row + 1}")
		self.standardsTable.setItem(row, 1, name_item)

		# Concentration column (editable)
		conc_item = QTableWidgetItem("")
		self.standardsTable.setItem(row, 2, conc_item)

		# Peak Area column (read-only, will be filled after integration)
		area_item = QTableWidgetItem("")
		area_item.setFlags(area_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
		area_item.setBackground(Qt.GlobalColor.lightGray)
		self.standardsTable.setItem(row, 3, area_item)

		# Select the new row
		self.standardsTable.selectRow(row)

		return row

	def setStandardPeakArea(self, row, peak_area_dict):
		"""Set the peak area for a standard row (stores dict, displays summary)."""
		if row >= 0 and row < self.standardsTable.rowCount():
			# Store the full dict as item data
			area_item = self.standardsTable.item(row, 3)
			area_item.setData(Qt.ItemDataRole.UserRole, peak_area_dict)
			# Display a summary (e.g., average or first value)
			if peak_area_dict:
				avg_area = sum(peak_area_dict.values()) / len(peak_area_dict)
				area_item.setText(f"{avg_area:.0f}")
			area_item.setBackground(Qt.GlobalColor.white)

	def getStandardsData(self):
		"""Get all standards data from the table for calibration calculation."""
		standards = []
		for row in range(self.standardsTable.rowCount()):
			filename = self.standardsTable.item(row, 0).text()
			name = self.standardsTable.item(row, 1).text()

			# Get concentration
			conc_text = self.standardsTable.item(row, 2).text()
			try:
				concentration = float(conc_text) if conc_text else None
			except ValueError:
				concentration = None

			# Get peak area dict from item data
			area_item = self.standardsTable.item(row, 3)
			peak_area_dict = area_item.data(Qt.ItemDataRole.UserRole) if area_item else None

			standards.append({
				'filename': filename,
				'name': name,
				'concentration': concentration,
				'peak_areas': peak_area_dict
			})
		return standards

	def clearStandardsTable(self):
		"""Clear all rows from the standards table."""
		self.standardsTable.setRowCount(0)



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
		for m in self.elementOptions:
			cbox = QCheckBox(m)
			self.checkBoxes.append(cbox)
			optionsLayout.addWidget(cbox)
		self.generalLayout.addLayout(optionsLayout)

	def _createActionButtons(self):
		"""Create the action buttons for integration and calibration."""
		self.integrateButtons = {}
		buttonsLayout = QHBoxLayout()

		# Integrate button - integrates the selected range for the selected standard
		self.integrateButtons['Integrate'] = QPushButton("Integrate")
		self.integrateButtons['Integrate'].setToolTip("Integrate the selected range and store peak area for selected standard")
		self.integrateButtons['Integrate'].setFixedSize(100, 40)
		self.integrateButtons['Integrate'].setEnabled(False)
		buttonsLayout.addWidget(self.integrateButtons['Integrate'])

		# Calculate Curve button
		self.integrateButtons['Calculate Curve'] = QPushButton("Calculate Curve")
		self.integrateButtons['Calculate Curve'].setToolTip("Calculate calibration curves from all standards")
		self.integrateButtons['Calculate Curve'].setFixedSize(120, 40)
		buttonsLayout.addWidget(self.integrateButtons['Calculate Curve'])

		buttonsLayout.addStretch()

		self.generalLayout.addLayout(buttonsLayout)

	def _createListbox(self):
		listBoxLayout = QVBoxLayout()

		# Add label for the file list (matching main window style)
		fileListLabel = QLabel("Calibration Standard Files")
		fileListLabel.setStyleSheet("font-weight: bold;")
		listBoxLayout.addWidget(fileListLabel)

		self.listwidget = QListWidget()
		listBoxLayout.addWidget(self.listwidget)
		self.listwidget.setMaximumHeight(250)
		self.generalLayout.addLayout(listBoxLayout)

	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QGridLayout()
		# Button text | position on the QGridLayout | tooltip
		buttons = {
			'Directory': (0, 0, 'Select directory containing calibration standard files'),
			'Reset': (0, 1, 'Reset calibration data and clear selections'),
			'Clear Plot': (0, 2, 'Clear the plot display')
		}
		# Create the buttons and add them to the grid layout
		for btnText, (row, col, tooltip) in buttons.items():
			self.buttons[btnText] = QPushButton(btnText)
			self.buttons[btnText].setToolTip(tooltip)
			self.buttons[btnText].setFixedSize(100, 40)
			buttonsLayout.addWidget(self.buttons[btnText], row, col)
		# Add buttonsLayout to the general layout
		self.generalLayout.addLayout(buttonsLayout)
	
	def clicked(self):
		item = self.listwidget.currentItem()
		if item:
			print('VIEW clicked method called - file: ' + item.text())
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
			self.activeElements.append(cbox.text())
		   # print(self.activeElements)
			return self.activeElements
		elif state == Qt.CheckState.Unchecked:
			print('Unchecked: ' + cbox.text())
			self.activeElements.remove(cbox.text())
			#print(self.activeElements)
			return self.activeElements
		else:
			print('Unchecked')
			return self.activeElements

	def updateLegend(self, elements, color_dict, format_isotopes=True):
		"""Update the legend - simplified version for calibration window.

		This method is called by plotChroma._plotChroma() to update the legend.
		For the calibration window, we use pyqtgraph's built-in legend.
		"""
		# Remove existing legend if any
		if hasattr(self, '_legend') and self._legend is not None:
			self._legend.close()
			self._legend = None

		# Create new legend if there are elements to display
		if elements and len(elements) > 0:
			self._legend = self.plotSpace.addLegend(offset=(10, 10))
			self._legend.setParentItem(self.plotSpace.graphicsItem())


