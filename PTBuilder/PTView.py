import sys
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import *
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial

__version__ = '0.2'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI - Periodic Table Element Selector

2022-04-21
Christian Dewey
Updated 2024 - Visual improvements
'''

# Element full names for tooltips
ELEMENT_NAMES = {
	'H': 'Hydrogen', 'He': 'Helium', 'Li': 'Lithium', 'Be': 'Beryllium', 'B': 'Boron',
	'C': 'Carbon', 'N': 'Nitrogen', 'O': 'Oxygen', 'F': 'Fluorine', 'Ne': 'Neon',
	'Na': 'Sodium', 'Mg': 'Magnesium', 'Al': 'Aluminum', 'Si': 'Silicon', 'P': 'Phosphorus',
	'S': 'Sulfur', 'Cl': 'Chlorine', 'Ar': 'Argon', 'K': 'Potassium', 'Ca': 'Calcium',
	'Sc': 'Scandium', 'Ti': 'Titanium', 'V': 'Vanadium', 'Cr': 'Chromium', 'Mn': 'Manganese',
	'Fe': 'Iron', 'Co': 'Cobalt', 'Ni': 'Nickel', 'Cu': 'Copper', 'Zn': 'Zinc',
	'Ga': 'Gallium', 'Ge': 'Germanium', 'As': 'Arsenic', 'Se': 'Selenium', 'Br': 'Bromine',
	'Kr': 'Krypton', 'Rb': 'Rubidium', 'Sr': 'Strontium', 'Y': 'Yttrium', 'Zr': 'Zirconium',
	'Nb': 'Niobium', 'Mo': 'Molybdenum', 'Tc': 'Technetium', 'Ru': 'Ruthenium', 'Rh': 'Rhodium',
	'Pd': 'Palladium', 'Ag': 'Silver', 'Cd': 'Cadmium', 'In': 'Indium', 'Sn': 'Tin',
	'Sb': 'Antimony', 'Te': 'Tellurium', 'I': 'Iodine', 'Xe': 'Xenon', 'Cs': 'Cesium',
	'Ba': 'Barium', 'La': 'Lanthanum', 'Ce': 'Cerium', 'Pr': 'Praseodymium', 'Nd': 'Neodymium',
	'Pm': 'Promethium', 'Sm': 'Samarium', 'Eu': 'Europium', 'Gd': 'Gadolinium', 'Tb': 'Terbium',
	'Dy': 'Dysprosium', 'Ho': 'Holmium', 'Er': 'Erbium', 'Tm': 'Thulium', 'Yb': 'Ytterbium',
	'Lu': 'Lutetium', 'Hf': 'Hafnium', 'Ta': 'Tantalum', 'W': 'Tungsten', 'Re': 'Rhenium',
	'Os': 'Osmium', 'Ir': 'Iridium', 'Pt': 'Platinum', 'Au': 'Gold', 'Hg': 'Mercury',
	'Tl': 'Thallium', 'Pb': 'Lead', 'Bi': 'Bismuth', 'Po': 'Polonium', 'At': 'Astatine',
	'Rn': 'Radon', 'Fr': 'Francium', 'Ra': 'Radium', 'Ac': 'Actinium', 'Th': 'Thorium',
	'Pa': 'Protactinium', 'U': 'Uranium', 'Np': 'Neptunium', 'Pu': 'Plutonium', 'Am': 'Americium',
	'Cm': 'Curium', 'Bk': 'Berkelium', 'Cf': 'Californium', 'Es': 'Einsteinium', 'Fm': 'Fermium'
}

# Create a subclass of QMainWindow to setup the periodic table gui
class PTView(QWidget):

	window_closed = pyqtSignal()

	def __init__(self,mainview):
		"""View initializer."""
		super(PTView,self).__init__()
		self._mainview = mainview
		self._elementLabels = []
		self.setWindowTitle('Select Elements')
		self.setGeometry(100, 60, 950, 540)

		self.generalLayout = QVBoxLayout()
		self.generalLayout.setSpacing(12)
		self.generalLayout.setContentsMargins(16, 16, 16, 16)
		self.topLayout = QVBoxLayout()
		self.bottomLayout = QHBoxLayout()
		self._centralWidget = QWidget(self)

		self.setLayout(self.generalLayout)

		# Selection counter at top
		self._createSelectionCounter()

		self.generalLayout.addLayout(self.topLayout)
		self.generalLayout.addLayout(self.bottomLayout)

		self._createPeriodicTable()
		self._createLegend()
		self._createButtons()

		# Update counter initially
		self.updateSelectionCounter()
	
	def closeEvent(self, event):
		print('\n\nActive elements: ', self._mainview.activeElements)
		self.window_closed.emit()
		event.accept()

	def _createSelectionCounter(self):
		"""Create the selection counter at the top."""
		counterLayout = QHBoxLayout()

		self.selectionLabel = QLabel("0 elements selected")
		self.selectionLabel.setStyleSheet("""
			QLabel {
				font-size: 14px;
				font-weight: bold;
				color: #333;
				padding: 4px 8px;
			}
		""")
		counterLayout.addWidget(self.selectionLabel)
		counterLayout.addStretch()

		self.generalLayout.addLayout(counterLayout)

	def updateSelectionCounter(self):
		"""Update the selection counter display."""
		count = len(self._mainview.activeElements)
		if count == 0:
			self.selectionLabel.setText("No elements selected")
			self.selectionLabel.setStyleSheet("""
				QLabel {
					font-size: 14px;
					font-weight: bold;
					color: #999;
					padding: 4px 8px;
				}
			""")
		elif count == 1:
			self.selectionLabel.setText("1 element selected")
			self.selectionLabel.setStyleSheet("""
				QLabel {
					font-size: 14px;
					font-weight: bold;
					color: #4682b4;
					padding: 4px 8px;
				}
			""")
		else:
			self.selectionLabel.setText(f"{count} elements selected")
			self.selectionLabel.setStyleSheet("""
				QLabel {
					font-size: 14px;
					font-weight: bold;
					color: #4682b4;
					padding: 4px 8px;
				}
			""")

	def _getElementStyle(self, state):
		"""Get stylesheet for element button based on state.

		States: 'selected', 'partial', 'available', 'unavailable'
		"""
		styles = {
			'selected': """
				QPushButton {
					background-color: #4682b4;
					color: white;
					border: 2px solid #3a72a4;
					border-radius: 4px;
					font-weight: bold;
					font-size: 11px;
				}
				QPushButton:hover {
					background-color: #5a9fd4;
					border-color: #4682b4;
				}
			""",
			'partial': """
				QPushButton {
					background-color: #87CEEB;
					color: #333;
					border: 2px solid #4682b4;
					border-radius: 4px;
					font-weight: bold;
					font-size: 11px;
				}
				QPushButton:hover {
					background-color: #a8d8f0;
					border-color: #5a9fd4;
				}
			""",
			'available': """
				QPushButton {
					background-color: #ffffff;
					color: #333;
					border: 1px solid #999;
					border-radius: 4px;
					font-size: 11px;
				}
				QPushButton:hover {
					background-color: #e8f4fc;
					border-color: #4682b4;
					border-width: 2px;
				}
			""",
			'unavailable': """
				QPushButton {
					background-color: #e0e0e0;
					color: #999;
					border: 1px solid #ccc;
					border-radius: 4px;
					font-size: 11px;
				}
			"""
		}
		return styles.get(state, styles['unavailable'])

	def _createLegend(self):
		"""Create a legend explaining the color coding."""
		legendLayout = QHBoxLayout()
		legendLayout.addStretch()

		# Legend items
		legend_items = [
			('#4682b4', 'Selected'),
			('#87CEEB', 'Partial'),
			('#ffffff', 'Available'),
			('#e0e0e0', 'Not in file'),
		]

		for color, label in legend_items:
			box = QLabel()
			box.setFixedSize(16, 16)
			border = '#333' if color == '#ffffff' else color
			box.setStyleSheet(f"background-color: {color}; border: 1px solid {border}; border-radius: 2px;")
			legendLayout.addWidget(box)

			text = QLabel(label)
			text.setStyleSheet("font-size: 11px; color: #666; margin-right: 12px;")
			legendLayout.addWidget(text)

		self.bottomLayout.addLayout(legendLayout)

	def _createButtons(self):
		"""Create the buttons."""
		self.buttons = {}
		buttonsLayout = QHBoxLayout()
		buttonsLayout.setSpacing(8)

		# Common button style
		buttonStyle = """
			QPushButton {
				padding: 8px 16px;
				border: 1px solid #ccc;
				border-radius: 4px;
				background-color: #f8f8f8;
				font-size: 13px;
			}
			QPushButton:hover {
				background-color: #e8e8e8;
				border-color: #999;
			}
			QPushButton:pressed {
				background-color: #d8d8d8;
			}
		"""

		# Clear button
		self.buttons['Clear'] = QPushButton('Clear All')
		self.buttons['Clear'].setToolTip('Deselect all elements')
		self.buttons['Clear'].setStyleSheet(buttonStyle)
		buttonsLayout.addWidget(self.buttons['Clear'])

		# Select All button
		self.buttons['Select All'] = QPushButton('Select All')
		self.buttons['Select All'].setToolTip('Select all available elements in data file')
		self.buttons['Select All'].setStyleSheet(buttonStyle)
		buttonsLayout.addWidget(self.buttons['Select All'])

		buttonsLayout.addStretch()

		# Save button (highlighted)
		self.buttons['Save'] = QPushButton('Save && Close')
		self.buttons['Save'].setToolTip('Save selected elements and close (Enter)')
		self.buttons['Save'].setStyleSheet("""
			QPushButton {
				padding: 8px 20px;
				border: 1px solid #4682b4;
				border-radius: 4px;
				background-color: #4682b4;
				color: white;
				font-size: 13px;
				font-weight: bold;
			}
			QPushButton:hover {
				background-color: #5a9fd4;
			}
			QPushButton:pressed {
				background-color: #3a72a4;
			}
		""")
		buttonsLayout.addWidget(self.buttons['Save'])

		self.bottomLayout.insertLayout(0, buttonsLayout)

	def _createResizeHandle(self):
		handle = QSizeGrip(self)
		self.generalLayout.addWidget(handle, 0, Qt.AlignBottom | Qt.AlignRight)
		self.resize(self.sizeHint())

	def _createPeriodicTable(self):
		"""Create the periodic table buttons with modern styling."""
		self.periodicTable = {}
		ptLayout = QGridLayout()
		ptLayout.setSpacing(3)

		# Create the buttons and add them to the grid layout
		for element, attr in self._mainview.periodicTableDict.items():
			self.periodicTable[element] = QPushButton(element)
			self.periodicTable[element].setFixedSize(44, 44)
			element_symbol = element.split('\n')[1]  # e.g., "Fe" from "56\nFe"

			# Check if this element has any available analytes in the data file
			has_analytes = element_symbol in self._mainview._analytes_by_element and \
			               len(self._mainview._analytes_by_element[element_symbol]) > 0

			# Build tooltip
			element_name = ELEMENT_NAMES.get(element_symbol, element_symbol)
			if has_analytes:
				available_analytes = self._mainview._analytes_by_element[element_symbol]
				selected_analytes = [a for a in available_analytes if a in self._mainview.activeElements]

				tooltip = f"{element_name}\n"
				tooltip += f"Available: {', '.join(available_analytes)}\n"
				if selected_analytes:
					tooltip += f"Selected: {', '.join(selected_analytes)}"
				else:
					tooltip += "Click to select isotopes"

				self.periodicTable[element].setToolTip(tooltip)
				self.periodicTable[element].setEnabled(True)

				# Determine state: all selected, partial, or none
				if len(selected_analytes) == len(available_analytes) and len(selected_analytes) > 0:
					# All available isotopes selected
					self.periodicTable[element].setStyleSheet(self._getElementStyle('selected'))
					attr[3] = 1
				elif len(selected_analytes) > 0:
					# Some isotopes selected
					self.periodicTable[element].setStyleSheet(self._getElementStyle('partial'))
					attr[3] = 1
				else:
					# Available but none selected
					self.periodicTable[element].setStyleSheet(self._getElementStyle('available'))
					attr[3] = 0
			else:
				self.periodicTable[element].setToolTip(f"{element_name}\nNot in data file")
				self.periodicTable[element].setEnabled(False)
				self.periodicTable[element].setStyleSheet(self._getElementStyle('unavailable'))
				attr[3] = 0

			ptLayout.addWidget(self.periodicTable[element], attr[0], attr[1])

		# Add buttonsLayout to the general layout
		self.topLayout.addLayout(ptLayout)

	def updateElementButton(self, element):
		"""Update a single element button's appearance based on current state."""
		if element not in self.periodicTable:
			return

		element_symbol = element.split('\n')[1]
		element_name = ELEMENT_NAMES.get(element_symbol, element_symbol)

		# Check if this element has any available analytes
		has_analytes = element_symbol in self._mainview._analytes_by_element and \
		               len(self._mainview._analytes_by_element[element_symbol]) > 0

		if has_analytes:
			available_analytes = self._mainview._analytes_by_element[element_symbol]
			selected_analytes = [a for a in available_analytes if a in self._mainview.activeElements]

			# Update tooltip
			tooltip = f"{element_name}\n"
			tooltip += f"Available: {', '.join(available_analytes)}\n"
			if selected_analytes:
				tooltip += f"Selected: {', '.join(selected_analytes)}"
			else:
				tooltip += "Click to select isotopes"
			self.periodicTable[element].setToolTip(tooltip)

			# Update style based on selection state
			if len(selected_analytes) == len(available_analytes) and len(selected_analytes) > 0:
				self.periodicTable[element].setStyleSheet(self._getElementStyle('selected'))
			elif len(selected_analytes) > 0:
				self.periodicTable[element].setStyleSheet(self._getElementStyle('partial'))
			else:
				self.periodicTable[element].setStyleSheet(self._getElementStyle('available'))

	def updateAllElementButtons(self):
		"""Update all element buttons to reflect current selection state."""
		for element in self.periodicTable:
			self.updateElementButton(element)
		self.updateSelectionCounter()

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

