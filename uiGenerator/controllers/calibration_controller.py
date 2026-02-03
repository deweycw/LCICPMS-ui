import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
import pyqtgraph as pg
import os


__version__ = '0.2'
__author__ = 'Christian Dewey'

'''
control for calibration

2022-04-21
Christian Dewey

Updated 2024 - Table-based standard entry
'''


# Create a Controller class to connect the GUI and the model
class CalCtrlFunctions:
	"""Calibration Controller class."""
	def __init__(self, model, view, mainview):
		"""Controller initializer."""
		print("\n=== Calibration Controller Initializing ===")
		self._model = model
		self._calview = view
		self._mainview = mainview

		self._intRange = []
		self.n_clicks = 0
		self._n = 0
		self._xMin = 0
		self._xMax = 0
		self._minAssigned = False
		self._integrationEnabled = False

		# Connect signals and slots
		self._connectSignals()

		# Auto-load the main window's directory if available
		self._autoLoadDirectory()
		# Verify listwidget is working
		print(f"Listwidget item count: {self._calview.listwidget.count()}")
		print(f"Listwidget object id: {id(self._calview.listwidget)}")
		print("=== Calibration Controller Ready ===\n")

	def _autoLoadDirectory(self):
		"""Auto-load the main window's directory if available."""
		print(f"_autoLoadDirectory called")
		main_dir = self._mainview.homeDir
		print(f"Main window homeDir: '{main_dir}'")
		if main_dir:
			# Remove trailing slash for consistent path handling
			main_dir = main_dir.rstrip('/')
			if os.path.isdir(main_dir):
				self._calview.calibrationDir = main_dir
				print(f"Auto-loaded directory: {self._calview.calibrationDir}")
				self._calview.listwidget.clear()
				self._createListbox()
			else:
				print(f"Directory not found: {main_dir}")
		else:
			print("No homeDir set in main window")

	def _selectDirectory(self):
		"""Open dialog to select calibration directory."""
		dialog = QFileDialog()
		dialog.setWindowTitle("Select Calibration Directory")
		dialog.setViewMode(QFileDialog.ViewMode.Detail)

		# Start in current calibration directory, or main window's directory, or home
		start_dir = self._calview.calibrationDir
		if not start_dir or not os.path.isdir(start_dir):
			start_dir = self._mainview.homeDir.rstrip('/') if self._mainview.homeDir else ''
		if not start_dir or not os.path.isdir(start_dir):
			start_dir = os.path.expanduser('~')

		selected_dir = str(dialog.getExistingDirectory(self._calview, "Select Directory:", start_dir))

		if selected_dir:
			self._calview.calibrationDir = selected_dir  # No trailing slash - use os.path.join
			print(f"Calibration directory: {self._calview.calibrationDir}")
			self._calview.listwidget.clear()
			self._calview.elements_in_stdfile = []  # Reset elements when changing directory
			self._createListbox()

	def _createListbox(self):
		"""Populate the file list with CSV files from the calibration directory."""
		print("_createListbox called")
		cal_dir = self._calview.calibrationDir
		print(f"  Calibration directory: '{cal_dir}'")

		if not cal_dir:
			print("  ERROR: No calibration directory set")
			return

		if not os.path.isdir(cal_dir):
			print(f"  ERROR: Directory does not exist: {cal_dir}")
			return

		try:
			all_files = os.listdir(cal_dir)
			print(f"  Total files in directory: {len(all_files)}")

			i = 0
			for name in sorted(all_files):
				if name.lower().endswith('.csv'):
					self._calview.listwidget.insertItem(i, name)
					i = i + 1

			print(f"  Found {i} CSV files")

			# Enable Add Standard button when files are loaded
			if i > 0:
				self._calview.addStandardBtn.setEnabled(True)

			# Re-connect signals after populating (in case they weren't connected properly)
			try:
				self._calview.listwidget.itemClicked.disconnect()
			except:
				pass

			# Connect with lambda that calls our method directly
			def on_click_wrapper(item, ctrl=self):
				print(f"WRAPPER: item clicked: {item.text()}")
				ctrl._onFileClicked(item)

			self._calview.listwidget.itemClicked.connect(on_click_wrapper)
			print(f"  Connected itemClicked via wrapper to listwidget {id(self._calview.listwidget)}")

		except Exception as e:
			print(f"  ERROR listing directory: {e}")
			import traceback
			traceback.print_exc()

	def _onFileClicked(self, item):
		"""Handle file click in list widget."""
		try:
			print(f"_onFileClicked called with: {item}")
			print(f"_onFileClicked: {item.text()}")
			self._importAndActivatePlotting()
		except Exception as e:
			print(f"ERROR in _onFileClicked: {e}")
			import traceback
			traceback.print_exc()

	def _onSelectionChanged(self):
		"""Handle selection change in list widget."""
		print("_onSelectionChanged called")
		if self._calview.listwidget.currentItem():
			print(f"  Current item: {self._calview.listwidget.currentItem().text()}")
		self._importAndActivatePlotting()

	def _importAndActivatePlotting(self):
		'''Activates plotting function after data imported.'''
		print("_importAndActivatePlotting called")

		if self._calview.listwidget.currentItem() is None:
			print("No file selected")
			return

		filename = self._calview.listwidget.currentItem().text()
		print(f"Selected file: {filename}")
		print(f"Calibration dir: {self._calview.calibrationDir}")

		try:
			self._model.importData()
			self._calview.setDisplayText(filename)
			self._model.plotActiveElements()

			# Enable Add Standard button
			self._calview.addStandardBtn.setEnabled(True)

			# Enable integration mode (click on plot to select range)
			self._enableIntegration()
		except Exception as e:
			print(f"ERROR in _importAndActivatePlotting: {e}")
			import traceback
			traceback.print_exc()

	def _enableIntegration(self):
		"""Enable clicking on plot to select integration range."""
		if not self._integrationEnabled:
			self._calview.proxy = pg.SignalProxy(
				self._calview.chroma.scene().sigMouseClicked,
				rateLimit=60,
				slot=self._onClick
			)
			self._integrationEnabled = True

	def _disableIntegration(self):
		"""Disable integration mode."""
		self._calview.proxy = None
		self._integrationEnabled = False

	def _addStandard(self):
		"""Add the currently loaded file as a calibration standard."""
		if self._calview.listwidget.currentItem() is None:
			return

		filename = self._calview.listwidget.currentItem().text()

		# Check if this file is already in the table
		for row in range(self._calview.standardsTable.rowCount()):
			if self._calview.standardsTable.item(row, 0).text() == filename:
				# Select the existing row instead
				self._calview.standardsTable.selectRow(row)
				print(f"File {filename} already in standards table, selecting row {row}")
				return

		# Add new row
		row = self._calview.addStandardRow(filename)
		print(f"Added standard: {filename} at row {row}")

		# Update button states
		self._updateButtonStates()

	def _removeStandard(self):
		"""Remove the selected standard from the table."""
		selected_rows = self._calview.standardsTable.selectedItems()
		if not selected_rows:
			return

		row = self._calview.standardsTable.currentRow()
		self._calview.standardsTable.removeRow(row)
		print(f"Removed standard at row {row}")

		# Update button states
		self._updateButtonStates()

	def _updateButtonStates(self):
		"""Update button enabled states based on current selection."""
		# Remove button - enabled if a row is selected
		has_selection = len(self._calview.standardsTable.selectedItems()) > 0
		self._calview.removeStandardBtn.setEnabled(has_selection)

		# Integrate button - enabled if range is selected and row is selected
		has_range = len(self._intRange) >= 2
		self._calview.integrateButtons['Integrate'].setEnabled(has_range and has_selection)

	def _onTableSelectionChanged(self):
		"""Handle table selection changes."""
		self._updateButtonStates()

	def _clearForm(self):
		'''Clears all calibration data and resets the form.'''
		# Clear the standards table
		self._calview.clearStandardsTable()

		# Clear main view data
		self._mainview.activeElements.clear()
		self._mainview.calCurves = {}

		# Clear plot
		self._calview.plotSpace.clear()
		self._calview.elements_in_stdfile = []

		# Reset integration
		self._intRange = []
		self._n = 0
		self._minAssigned = False

		# Reset button states
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setStyleSheet("")
		self._calview.removeStandardBtn.setEnabled(False)

		print('Calibration data cleared')

	def _onClick(self, event):
		'''Handles clicks on plot to select integration range.'''
		# Check if a standard is selected in the table
		if self._calview.standardsTable.currentRow() < 0:
			print("Please select a standard in the table first")
			return

		self._act_pos = self._calview.chroma.mapFromScene(event[0].scenePos())
		cc = len(self._intRange)
		cc = cc + 1

		if cc == 1:
			self._intRange.append(self._act_pos.x())
			print(f'\tIntegration start: {self._act_pos.x():.2f} min')
			self._model.plotLowRange(self._act_pos.x(), self._n)
			self._minAssigned = True

		if (cc == 2) and self._minAssigned is True:
			self._intRange.append(self._act_pos.x())
			print(f'\tIntegration end: {self._act_pos.x():.2f} min')
			self._model.plotHighRange(self._act_pos.x(), self._n)

			# Enable integrate button
			self._calview.integrateButtons['Integrate'].setEnabled(True)
			self._calview.integrateButtons['Integrate'].setStyleSheet("background-color: #ff6b6b")
			self._n = self._n + 1

		self.n_clicks = 1

	def _Integrate(self):
		'''Perform integration and store peak area in selected table row.'''
		selected_row = self._calview.standardsTable.currentRow()
		if selected_row < 0:
			print("Please select a standard in the table")
			return

		if len(self._intRange) < 2:
			print("Please select integration range on plot")
			return

		# Perform integration
		self._model.integrate(self._intRange)

		# Store peak area in table
		peak_area_dict = self._calview.n_area
		self._calview.setStandardPeakArea(selected_row, peak_area_dict)

		# Get standard name for logging
		std_name = self._calview.standardsTable.item(selected_row, 1).text()
		print(f"Integrated {std_name}: {peak_area_dict}")

		# Reset for next integration
		self._intRange = []
		self._minAssigned = False
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setStyleSheet("")

	def _clearPlot(self):
		'''Clears plot area and integration markers.'''
		self._calview.plotSpace.clear()
		self._intRange = []
		self._n = 0
		self._minAssigned = False
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setStyleSheet("")

		# Re-plot the data if a file is selected
		if self._calview.listwidget.currentItem() is not None:
			self._model.plotActiveElements()

	def _calcCurve(self):
		"""Calculate calibration curves from standards table data."""
		standards_data = self._calview.getStandardsData()

		# Validate data
		valid_standards = []
		for std in standards_data:
			if std['concentration'] is not None and std['peak_areas'] is not None:
				valid_standards.append(std)
			else:
				print(f"Skipping {std['name']}: missing concentration or peak area")

		if len(valid_standards) < 2:
			from PyQt6.QtWidgets import QMessageBox
			QMessageBox.warning(
				self._calview,
				'Insufficient Data',
				'Need at least 2 standards with concentration and peak area to calculate calibration curve.',
				QMessageBox.StandardButton.Ok
			)
			return

		# Pass data to model for calculation
		self._model.calcLinearRegression(valid_standards)

	def _connectSignals(self):
		"""Connect signals and slots."""
		print("Connecting calibration signals...")

		# Directory and file selection
		self._calview.buttons['Directory'].clicked.connect(self._selectDirectory)
		# Connect multiple signals to ensure we catch file selection
		self._calview.listwidget.currentItemChanged.connect(self._importAndActivatePlotting)
		self._calview.listwidget.itemClicked.connect(self._onFileClicked)
		self._calview.listwidget.itemDoubleClicked.connect(self._onFileClicked)
		self._calview.listwidget.itemSelectionChanged.connect(self._onSelectionChanged)
		print("  - File list signals connected")

		# Table management buttons
		self._calview.addStandardBtn.clicked.connect(self._addStandard)
		self._calview.removeStandardBtn.clicked.connect(self._removeStandard)
		self._calview.standardsTable.itemSelectionChanged.connect(self._onTableSelectionChanged)
		print("  - Table signals connected")

		# Action buttons
		self._calview.buttons['Reset'].clicked.connect(self._clearForm)
		self._calview.buttons['Clear Plot'].clicked.connect(self._clearPlot)
		self._calview.integrateButtons['Integrate'].clicked.connect(self._Integrate)
		self._calview.integrateButtons['Calculate Curve'].clicked.connect(self._calcCurve)
		print("  - Action button signals connected")

		print("All calibration signals connected")
