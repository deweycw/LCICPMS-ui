import sys 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
import numpy as np
import json
from ..ui.calibration_window import Calibration
from ..controllers.calibration_controller import CalCtrlFunctions
from ..models.calibration import CalibrateFunctions
from PTBuilder.PTView import PTView
from PTBuilder.PTCtrl import PTCtrl
from PTBuilder.PTModel import PTModel

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


# Create a Controller class to connect the GUI and the model
class PyLCICPMSCtrl:
	"""PyCalc Controller class."""
	def __init__(self, model, view, calwindow):
		"""Controller initializer."""
		self._model = model
		self._view = view
		self._view._controller = self  # Allow view to call controller methods
		self._calWindow = calwindow
		self._intRange = []
		self.n_clicks = 0
		self._n = 0
		self._xMin = 0
		self._xMax = 0
		self.button_is_checked = False
		self._update_thread = None  # Store update checker thread
		self._calibrationPending = False  # Flag for calibration element selection
		self._click_proxy = None  # SignalProxy for plot clicks (set up once)

		# Connect signals and slots
		self._connectSignals()

		# Enable clicking on the plot to define an integration range — always,
		# no checkbox needed. Bind to the stable plot scene at startup.
		self._enablePlotClicks()

		# Check for updates on startup (in background)
		QTimer.singleShot(500, self._check_for_updates)

		# Automatically show directory selection dialog on startup
		QTimer.singleShot(1000, self._selectDirectory)

	def _selectDirectory(self):
		self._view.homeDir = ''
		self._view.listwidget.clear()
		dialog = QFileDialog()
		dialog.setWindowTitle("Select LC-ICPMS Directory")
		dialog.setViewMode(QFileDialog.ViewMode.Detail)
		# Start in home directory (platform-independent)
		home_dir = os.path.expanduser('~')
		selected_dir = str(dialog.getExistingDirectory(self._view, "Select Directory:", home_dir))

		if selected_dir:  # Only proceed if user selected a directory
			self._view.homeDir = selected_dir + '/'

			# Add to recent directories
			self._view.addRecentDirectory(selected_dir)

			self._createListbox()
			self._view.integrateButtons['Calibrate'].setEnabled(True)
			self._view.integrateButtons['Load Cal.'].setEnabled(True)
			self._view.integrateButtons['115In Correction'].setEnabled(True)

	def _createListbox(self):

		self._view.listwidget.clear()

		test_dir = self._view.homeDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		i = 0
		for name in sorted(os.listdir(test_dir)):
			if '.csv' in name:
				# Add item to list
				self._view.listwidget.insertItem(i, name)

				# Add tooltip with file information
				try:
					file_path = os.path.join(test_dir, name)
					file_size = os.path.getsize(file_path)
					mod_time = os.path.getmtime(file_path)
					from datetime import datetime
					mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')

					# Format file size
					if file_size < 1024:
						size_str = f"{file_size} B"
					elif file_size < 1024 * 1024:
						size_str = f"{file_size / 1024:.1f} KB"
					else:
						size_str = f"{file_size / (1024 * 1024):.1f} MB"

					tooltip = f"Path: {file_path}\nSize: {size_str}\nModified: {mod_date}"
					self._view.listwidget.item(i).setToolTip(tooltip)
				except:
					pass

				i = i + 1

	def _buildExpression(self, sub_exp):
		"""Build expression - no longer needed with display removed."""
		pass

	def _clearForm(self):
		''' clears selection and nulls data '''
		self._view.activeElements = []
		self._view.buttons['Export Plot'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")

		self._intRange = []
		self._view.plotSpace.clear()
		self._n = 0

		# Clear integration results display
		self._view.hideIntegrationResults()

		# Clear the legend
		self._view.updateLegend([], {})

		# Reset comparison mode so user can select files from main list
		self._view.compareMode = False
		self._view.comparisonFiles = []
		self._view.comparisonData = []
		self._view.comparisonLabels = {}
		if self._view.compareFilesBtn.isChecked():
			self._view.compareFilesBtn.setChecked(False)

		# Drop any accumulated integration results and disable Save button.
		self._view.integrationResults = []
		if 'Save Integration' in self._view.integrateButtons:
			self._view.integrateButtons['Save Integration'].setEnabled(False)

		# Deselect current file so clicking it again will reload
		self._view.listwidget.setCurrentItem(None)

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		if self._view.listwidget.currentItem() is not None:
			# In comparison mode, clicking main list doesn't do anything
			# User must use comparison list instead
			if self._view.compareMode:
				return

			# Clear integration results when selecting a new file
			self._view.hideIntegrationResults()

			# Normal single file mode
			filename = self._view.listwidget.currentItem().text()
			self._model.importData()

			# Update window title with filename
			self._view.setWindowTitle(f'LC-ICP-MS Data Viewer - {filename}')

			# Update status bar
			file_path = os.path.join(self._view.homeDir, filename)
			self._view.updateStatusBar(file_path)

			# Auto-select all available elements if none selected
			if self._view.activeElements == []:
				self._view.activeElements = self._view._elements_in_file.copy()

			self._makePlot()
			self._view.buttons['Reset'].setEnabled(True)
			self._view.buttons['Export Plot'].setEnabled(True)
			self._view.listwidget.setFocus()

			# Update compare button state (now that elements are loaded)
			self._updateCompareButtons()

	def _mouseover(self, pos):
		''' selects range for integration'''
		act_pos = self._view.chroma.mapFromScene(pos)
		self._intPointX = act_pos.x()
		self._intPointY = act_pos.y()

	def _onClick(self, event):
		'''Select integration range from a plot click.

		Uses plotSpace's ViewBox to map scene coords to data coords, so it
		works even after plotActiveElements reassigns self._view.chroma.
		'''
		vb = self._view.plotSpace.getViewBox()
		self._act_pos = vb.mapSceneToView(event[0].scenePos())
		cc = len(self._intRange) + 1

		if cc == 1:
			self._intRange.append(self._act_pos.x())
			self._view.statusBar.showMessage(
				f'Integration start: {self._act_pos.x():.2f} min', 3000,
			)
			self._model.plotLowRange(self._act_pos.x(), self._n)
			self._minAssigned = True

		elif cc == 2 and self._minAssigned:
			self._intRange.append(self._act_pos.x())
			self._view.statusBar.showMessage(
				f'Integration end: {self._act_pos.x():.2f} min | '
				f'Range: {self._intRange[-1] - self._intRange[-2]:.2f} min',
				5000,
			)
			self._model.plotHighRange(self._act_pos.x(), self._n)
			self._view.integrateButtons['Integrate'].setEnabled(True)
			self._view.integrateButtons['Integrate'].setStyleSheet(
				'background-color: red'
			)
			self._n += 1

		self.n_clicks = 1

	def _enablePlotClicks(self):
		'''Bind mouse clicks on the plot to _onClick, once.

		The plot's scene is stable across replots (plotSpace.clear() doesn't
		destroy it), so a single SignalProxy set up on plotSpace.scene() works
		for the app's lifetime — no need for the old intbox gate.
		'''
		if getattr(self, '_click_proxy', None) is not None:
			return
		self._click_proxy = pg.SignalProxy(
			self._view.plotSpace.scene().sigMouseClicked,
			rateLimit=60,
			slot=self._onClick,
		)
		# Keep the old attribute name too, in case anything else reads it.
		self._view.proxy = self._click_proxy

	def _selectIntRange(self, checked):
		'''Legacy no-op — clicks on the plot are always active now.'''
		return

	def _toggleCompareMode(self, checked):
		'''Toggle file comparison mode - uses comparison list'''
		from PyQt6.QtWidgets import QMessageBox

		if self._view.compareFilesBtn.isChecked():
			# Limit to 1 element in compare mode
			if len(self._view.activeElements) > 1:
				reply = QMessageBox.warning(
					self._view,
					'Too Many Elements',
					'Comparison mode supports only 1 element. Please select only 1 element.\n\n'
					'Click OK and the periodic table will open for you to select a single element.',
					QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
					QMessageBox.StandardButton.Ok
				)
				if reply == QMessageBox.StandardButton.Ok:
					self._showPeriodicTable()
				self._view.compareFilesBtn.setChecked(False)
				return

			# Check if comparison list has enough files - show panel silently
			if self._view.compareListWidget.count() < 2:
				# Show comparison panel so user can add files
				self._view.showComparisonPanel(True)
				self._view.statusBar.showMessage('Add 2+ files to comparison list using "+ Add" button', 3000)
				# Keep button checked - it will activate when files are added
				return

			# Enable comparison mode
			self._view.compareMode = True
			self._loadComparisonFiles()

			self._view.statusBar.showMessage(f'Comparing {self._view.compareListWidget.count()} files', 3000)
		else:
			# Disable compare mode
			self._view.compareMode = False
			self._view.comparisonFiles = []
			self._view.comparisonData = []

			self._view.statusBar.showMessage('Comparison mode disabled', 2000)

			# Replot without comparison
			if self._view.activeElements and self._view.listwidget.currentItem():
				self._model.importData()
				self._makePlot()

	def _addToComparisonList(self):
		"""Add selected file from main list to comparison list."""
		if self._view.listwidget.currentItem() is None:
			return

		# Check if already at max
		if self._view.compareListWidget.count() >= 12:
			self._view.statusBar.showMessage('Maximum of 12 files reached', 2000)
			return

		filename = self._view.listwidget.currentItem().text()

		# Check if already in comparison list
		for i in range(self._view.compareListWidget.count()):
			if self._view.compareListWidget.item(i).text() == filename:
				self._view.statusBar.showMessage(f'{filename} is already in comparison list', 2000)
				return

		# Show comparison panel when first file is added
		if self._view.compareListWidget.count() == 0:
			self._view.showComparisonPanel(True)

		# Add to comparison list
		self._view.compareListWidget.addItem(filename)
		self._view.statusBar.showMessage(f'Added {filename} to comparison ({self._view.compareListWidget.count()}/12)', 2000)

		# Update button states
		self._updateCompareButtons()

		# If comparison mode is already active, reload and replot
		if self._view.compareMode:
			self._loadComparisonFiles()
		# If Compare button is checked and we now have 2+ files, activate comparison
		elif (self._view.compareFilesBtn.isChecked() and
		      self._view.compareListWidget.count() >= 2 and
		      len(self._view.activeElements) == 1):
			self._view.compareMode = True
			self._loadComparisonFiles()
		# Otherwise, auto-enable comparison mode if we have 2+ files and 1 element
		elif (self._view.compareListWidget.count() >= 2 and
		      len(self._view.activeElements) == 1):
			self._view.compareFilesBtn.setChecked(True)
			self._view.compareMode = True
			self._loadComparisonFiles()

	def _removeFromComparisonList(self):
		"""Remove selected file from comparison list."""
		if self._view.compareListWidget.currentItem() is None:
			return

		filename = self._view.compareListWidget.currentItem().text()
		row = self._view.compareListWidget.currentRow()
		self._view.compareListWidget.takeItem(row)
		self._view.statusBar.showMessage(f'Removed {filename} from comparison', 2000)

		# Update button states
		self._updateCompareButtons()

		# If comparison mode is active, update the plot
		if self._view.compareMode:
			# If we still have 2+ files, reload and replot
			if self._view.compareListWidget.count() >= 2:
				self._loadComparisonFiles()
			else:
				# Less than 2 files, disable comparison mode
				self._view.compareFilesBtn.setChecked(False)

		# Hide comparison panel when list is empty
		if self._view.compareListWidget.count() == 0:
			self._view.showComparisonPanel(False)

	def _clearComparisonList(self):
		"""Clear all files from comparison list."""
		self._view.compareListWidget.clear()
		self._view.statusBar.showMessage('Cleared comparison list', 2000)

		# Clear comparison data
		self._view.comparisonFiles = []
		self._view.comparisonData = []
		self._view.comparisonLabels = {}

		# Disable comparison mode
		self._view.compareMode = False
		if self._view.compareFilesBtn.isChecked():
			self._view.compareFilesBtn.setChecked(False)

		# Hide comparison panel when list is cleared
		self._view.showComparisonPanel(False)

		# Clear the plot and allow new file selection
		self._clearForm()
		self._updateCompareButtons()

	def _updateCompareButtons(self):
		"""Update state of comparison list buttons."""
		# Enable Add button if a file is selected in main list and not at max
		has_selection = self._view.listwidget.currentItem() is not None
		not_at_max = self._view.compareListWidget.count() < 12
		self._view.addToCompareBtn.setEnabled(has_selection and not_at_max)

		# Enable Remove button if a file is selected in comparison list
		has_compare_selection = self._view.compareListWidget.currentItem() is not None
		self._view.removeFromCompareBtn.setEnabled(has_compare_selection)

		# Enable Clear button if comparison list has items
		has_items = self._view.compareListWidget.count() > 0
		self._view.clearCompareBtn.setEnabled(has_items)

		# Enable Compare Files button if there's at least 1 element selected
		# (clicking it will show the panel and guide user to add files if needed)
		has_elements = len(self._view.activeElements) >= 1
		self._view.compareFilesBtn.setEnabled(has_elements)

	def _editComparisonLabel(self, item):
		"""Edit the legend label for a comparison file."""
		from PyQt6.QtWidgets import QInputDialog

		filename = item.text()

		# Get current label (either custom or auto-extracted)
		if filename in self._view.comparisonLabels:
			current_label = self._view.comparisonLabels[filename]
		else:
			# Extract default label
			if "LCICPMS_" in filename and ".csv" in filename:
				start = filename.index("LCICPMS_") + len("LCICPMS_")
				end = filename.index(".csv")
				current_label = filename[start:end]
			else:
				current_label = filename.replace('.csv', '')

		# Show input dialog
		new_label, ok = QInputDialog.getText(
			self._view,
			'Edit Legend Label',
			f'Enter custom label for {filename}:',
			text=current_label
		)

		if ok and new_label.strip():
			# Store custom label
			self._view.comparisonLabels[filename] = new_label.strip()
			self._view.statusBar.showMessage(f'Updated label for {filename}', 2000)

			# Replot if in comparison mode
			if self._view.compareMode:
				self._makePlot()

	def _updateComparisonPlot(self):
		"""Update plot when comparison list selection changes."""
		if self._view.compareMode and self._view.compareListWidget.count() >= 2:
			self._loadComparisonFiles()

	def _loadComparisonFiles(self):
		"""Load all files from comparison list and update plot."""
		from PyQt6.QtWidgets import QMessageBox
		from lcicpms.raw_icpms_data import RawICPMSData
		import os

		try:
			# Save current view limits before reloading
			current_view_range = self._view.plotSpace.viewRange()
			x_limits = current_view_range[0]
			y_limits = current_view_range[1]

			# Get all filenames from comparison list
			filenames = []
			for i in range(self._view.compareListWidget.count()):
				filenames.append(self._view.compareListWidget.item(i).text())

			# Load all comparison files
			self._view.comparisonFiles = []
			self._view.comparisonData = []

			for filename in filenames:
				file_path = os.path.join(self._view.homeDir, filename)
				raw_data = RawICPMSData(file_path)
				self._view.comparisonFiles.append(filename)
				self._view.comparisonData.append(raw_data.raw_data_df)

			# Load first file as main data
			file_path = os.path.join(self._view.homeDir, filenames[0])
			raw_data = RawICPMSData(file_path)
			self._model._data = raw_data.raw_data_df
			self._view._elements_in_file = raw_data.elements

			# Update window title
			num_files = len(filenames)
			self._view.setWindowTitle(f'LC-ICP-MS Data Viewer - Comparing {num_files} files')

			# Update status bar
			self._view.statusBar.showMessage(f'Comparing {num_files} files', 3000)

			# Make plot
			if self._view.activeElements:
				self._makePlot()

			# Restore the previous view limits
			self._view.plotSpace.setXRange(x_limits[0], x_limits[1], padding=0)
			self._view.plotSpace.setYRange(y_limits[0], y_limits[1], padding=0)

		except Exception as e:
			QMessageBox.warning(
				self._view,
				'Load Error',
				f'Failed to load comparison files: {str(e)}',
				QMessageBox.StandardButton.Ok
			)

	def _baselineSubtraction(self,checked):
		'''select integration range'''
		if self._view.baseSubtractBox.isChecked() == True:
			#print('base subtract box')
			self._view.baseSubtract = True
		else:
			self._view.baseSubtract = False
			
	def _Integrate(self):
		''' Integrate over the current range in every selected file.

		Selection rules:
		  * If the file list has ≥2 rows selected, integrate each of them.
		  * If compareMode is on and comparisonData is populated, integrate
		    those instead (preserves existing comparison-mode behavior).
		  * Otherwise integrate the currently-loaded file (single-select).

		Before running, the user is shown a modal options popup where they
		can toggle baseline subtraction and 115In normalization. Nothing is
		written to disk — records go into self._view.integrationResults and
		the user later hits "Save Integration" to persist them.
		'''
		# Ask the user about baseline subtraction / 115In correction first.
		# Returns False if the user cancels.
		if not self._promptIntegrationOptions():
			return
		has_calibration = len(self._view.calCurves) > 0

		if not has_calibration:
			self._view.statusBar.showMessage(
				'No calibration loaded - calculating peak areas (counts) only', 5000
			)
			print('No calibration loaded - only peak areas will be calculated')
		else:
			cal_elements = set(self._view.calCurves.keys())
			# 115In is never integrated and never needs a cal curve, so it
			# shouldn't count against "unmatched" here even if the user
			# selected it for plotting.
			active_elements = {
				el for el in self._view.activeElements
				if not el.startswith('115In')
			}
			matched = cal_elements & active_elements
			unmatched = active_elements - cal_elements
			if matched:
				print(f'Calibration available for: {list(matched)}')
			if unmatched:
				print(f'No calibration for: {list(unmatched)} (will show counts only)')
				self._view.statusBar.showMessage(
					f'Partial calibration - {len(unmatched)} element(s) will show counts only',
					5000,
				)

		new_records = []
		display_results = {}  # short_name -> results dict (for display)

		# --- Comparison mode --------------------------------------------
		if self._view.compareMode and self._view.comparisonData:
			for compare_data, filename in zip(
				self._view.comparisonData, self._view.comparisonFiles,
			):
				if filename in self._view.comparisonLabels:
					short_name = self._view.comparisonLabels[filename]
				elif 'LCICPMS_' in filename and '.csv' in filename:
					start = filename.index('LCICPMS_') + len('LCICPMS_')
					end = filename.index('.csv')
					short_name = filename[start:end]
				else:
					short_name = filename.replace('.csv', '')

				record = self._model.integrate(
					self._intRange,
					has_calibration=has_calibration,
					data=compare_data,
					filename=filename,
				)
				new_records.append(record)
				display_results[short_name] = record['results']

			source_label = 'comparison mode'

		# --- Multi-select in the file list ------------------------------
		else:
			selected_items = self._view.listwidget.selectedItems()
			multi = len(selected_items) > 1

			if multi:
				for item in selected_items:
					filename = item.text()
					path = os.path.join(self._view.homeDir, filename)
					try:
						df = self._model.importData_generic(fdir=path)
					except Exception as e:
						print(f'  Skipping {filename}: {e}')
						continue
					record = self._model.integrate(
						self._intRange,
						has_calibration=has_calibration,
						data=df,
						filename=filename,
					)
					new_records.append(record)
					display_results[filename] = record['results']

				source_label = f'{len(display_results)} selected file(s)'
			else:
				# Single-file: uses the currently-loaded dataset.
				record = self._model.integrate(
					self._intRange, has_calibration=has_calibration,
				)
				new_records.append(record)
				display_results[record['filename']] = record['results']
				# Inline panel gets the quick-glance version as well.
				self._displayIntegrationResults(record['results'], has_calibration)
				source_label = 'single file'

		# Stash records in memory *before* the popup opens so its Save button
		# has data to write, then show the summary.
		self._view.integrationResults.extend(new_records)
		if new_records:
			self._showMultiFileResultsDialog(
				display_results, has_calibration, source=source_label,
			)
			self._view.integrateButtons['Save Integration'].setEnabled(True)
			self._view.statusBar.showMessage(
				f'Integrated {len(new_records)} file(s). '
				f'{len(self._view.integrationResults)} record(s) in memory.',
				6000,
			)

		self._view.integrateButtons['Integrate'].setStyleSheet(
			'background-color: light gray'
		)

	def _promptIntegrationOptions(self):
		'''Modal popup shown at the start of every Integrate action.

		Lets the user toggle:
		  * Baseline subtraction  (sets self._view.baseSubtract)
		  * 115In normalization   (sets self._view.normAvIndium via file pick)

		Returns True if integration should proceed, False if the user
		cancelled.
		'''
		from PyQt6.QtWidgets import (
			QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QPushButton,
			QDialogButtonBox,
		)

		dlg = QDialog(self._view)
		dlg.setWindowTitle('Integration Options')
		dlg.setMinimumWidth(420)
		layout = QVBoxLayout(dlg)

		# --- Baseline subtraction ---
		base_box = QCheckBox('Subtract baseline')
		base_box.setChecked(bool(self._view.baseSubtract))
		base_box.setToolTip(
			'Subtract a trapezoidal baseline (drawn between the intensities '
			'at the start and end of the integration range) from every '
			'element\'s peak area.'
		)
		layout.addWidget(base_box)

		# --- 115In correction ---
		in_row = QHBoxLayout()
		in_box = QCheckBox('Apply 115In normalization')
		in_row.addWidget(in_box)
		layout.addLayout(in_row)

		in_status = QLabel()
		in_status.setStyleSheet('color: #555; margin-left: 20px;')
		layout.addWidget(in_status)

		pick_btn = QPushButton('Choose reference file…')
		pick_btn.setToolTip(
			'Pick a CSV whose average 115In signal will be used as the '
			'normalization reference.'
		)
		layout.addWidget(pick_btn)

		# Local state so cancel doesn't mutate view.normAvIndium.
		state = {'norm_avg': self._view.normAvIndium if self._view.normAvIndium > 0 else None}

		def _refresh_in_ui():
			has_ref = state['norm_avg'] is not None
			if has_ref:
				in_status.setText(
					f'Reference loaded: avg 115In = {state["norm_avg"]:.1f} counts'
				)
			else:
				in_status.setText('<i>No reference file loaded.</i>')
				in_status.setTextFormat(Qt.TextFormat.RichText)
			pick_btn.setEnabled(in_box.isChecked())
			in_status.setVisible(True)

		# Pre-check the box if a reference is already loaded from a prior run.
		in_box.setChecked(state['norm_avg'] is not None)
		_refresh_in_ui()
		in_box.stateChanged.connect(lambda _s: _refresh_in_ui())

		def _pick_reference():
			from PyQt6.QtWidgets import QFileDialog
			path, _ = QFileDialog.getOpenFileName(
				dlg, 'Select 115In Normalization File',
				self._view.homeDir, 'CSV Files (*.csv);;All Files (*)',
			)
			if not path:
				return
			try:
				df = self._model.importData_generic(fdir=path)
			except Exception as e:
				in_status.setText(f'<span style="color:#a04040">Error: {e}</span>')
				return
			indium_col = next(
				(c for c in df.columns
				 if c.startswith('115In') and 'Time' not in c),
				None,
			)
			if indium_col is None:
				in_status.setText(
					'<span style="color:#a04040">115In column not found in that file.</span>'
				)
				return
			state['norm_avg'] = float(np.average(df[indium_col].dropna()))
			_refresh_in_ui()

		pick_btn.clicked.connect(_pick_reference)

		buttons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Ok
			| QDialogButtonBox.StandardButton.Cancel,
		)
		buttons.accepted.connect(dlg.accept)
		buttons.rejected.connect(dlg.reject)
		layout.addWidget(buttons)

		if dlg.exec() != QDialog.DialogCode.Accepted:
			return False

		# Apply choices to the view.
		self._view.baseSubtract = base_box.isChecked()
		if in_box.isChecked() and state['norm_avg'] is not None:
			self._view.normAvIndium = state['norm_avg']
		else:
			# Not requested (or requested but no file selected) — turn off.
			self._view.normAvIndium = -999.99
		return True

	def _showMultiFileResultsDialog(self, all_results, has_calibration, source=''):
		'''Show a scrollable popup table with per-file, per-element results.

		all_results: dict of {file_or_label: {element: {peak_area, conc_ppb, conc_uM}}}
		'''
		from PyQt6.QtWidgets import (
			QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
			QDialogButtonBox, QHeaderView,
		)

		if not all_results:
			return

		# Ordered, de-duplicated list of elements across all files.
		element_order = []
		for res in all_results.values():
			for el in res:
				if el not in element_order:
					element_order.append(el)

		# Show a Baseline column when any element in any file had a
		# baseline subtracted (i.e. the user checked "Subtract baseline").
		show_baseline = any(
			(data or {}).get('baseline_area') is not None
			for res in all_results.values() for data in res.values()
		)

		sub_headers = ['Peak area']
		if show_baseline:
			sub_headers.append('Baseline')
		if has_calibration:
			sub_headers.extend(['ppb', 'µM'])

		dlg = QDialog(self._view)
		dlg.setWindowTitle('Integration Results')
		dlg.resize(1000, 520)
		layout = QVBoxLayout(dlg)

		range_min, range_max = self._intRange[0], self._intRange[1]
		summary = QLabel(
			f'<b>{len(all_results)} file(s)</b> integrated over '
			f'{range_min:.2f} – {range_max:.2f} min'
			+ (f'  ·  source: {source}' if source else '')
			+ ('' if has_calibration else '  ·  <i>no calibration</i>')
		)
		summary.setTextFormat(Qt.TextFormat.RichText)
		layout.addWidget(summary)

		table = QTableWidget()
		table.setAlternatingRowColors(True)
		table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		total_cols = 1 + len(element_order) * len(sub_headers)
		table.setColumnCount(total_cols)
		table.setRowCount(len(all_results))

		# Two-row header via horizontalHeader by concatenating labels.
		headers = ['File']
		for el in element_order:
			for sub in sub_headers:
				headers.append(f'{el}\n{sub}')
		table.setHorizontalHeaderLabels(headers)
		table.horizontalHeader().setSectionResizeMode(
			QHeaderView.ResizeMode.ResizeToContents,
		)
		table.horizontalHeader().setDefaultAlignment(
			Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
		)

		def _fmt_area(v):
			if v is None:
				return '—'
			return f'{v:.2e}' if abs(v) >= 1e5 else f'{v:.0f}'

		def _fmt(v, digits):
			return '—' if v is None else f'{v:.{digits}f}'

		for r_idx, (fname, res) in enumerate(all_results.items()):
			table.setItem(r_idx, 0, QTableWidgetItem(fname))
			col = 1
			for el in element_order:
				data = res.get(el)
				if data is None:
					for _ in sub_headers:
						table.setItem(r_idx, col, QTableWidgetItem('—'))
						col += 1
					continue
				table.setItem(r_idx, col, QTableWidgetItem(_fmt_area(data['peak_area'])))
				col += 1
				if show_baseline:
					table.setItem(r_idx, col, QTableWidgetItem(_fmt_area(data.get('baseline_area'))))
					col += 1
				if has_calibration:
					table.setItem(r_idx, col, QTableWidgetItem(_fmt(data['conc_ppb'], 3)))
					col += 1
					table.setItem(r_idx, col, QTableWidgetItem(_fmt(data['conc_uM'], 3)))
					col += 1

		layout.addWidget(table)

		hint = QLabel(
			f'<i>{len(self._view.integrationResults)} record(s) in memory. '
			'Click <b>Save to CSV…</b> to write them.</i>'
		)
		hint.setTextFormat(Qt.TextFormat.RichText)
		hint.setStyleSheet('color: #555;')
		layout.addWidget(hint)

		buttons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Close
		)
		save_btn = buttons.addButton(
			'Save to CSV…', QDialogButtonBox.ButtonRole.AcceptRole,
		)
		save_btn.setDefault(True)

		def _on_save():
			# Delegate to the existing save routine. On success it clears the
			# in-memory records; close this dialog either way.
			self._saveIntegration()
			dlg.accept()

		save_btn.clicked.connect(_on_save)
		buttons.rejected.connect(dlg.reject)
		layout.addWidget(buttons)
		dlg.exec()

	def _saveIntegration(self):
		'''Save all in-memory integration records to a single CSV whose columns
		match the multi-file results popup: one row per file, grouped columns
		per element (Peak area, ppb, µM if calibrated).'''
		from PyQt6.QtWidgets import QMessageBox, QFileDialog

		if not self._view.integrationResults:
			QMessageBox.information(
				self._view,
				'Nothing to Save',
				'No integration results in memory yet. Run Integrate first.',
				QMessageBox.StandardButton.Ok,
			)
			return

		start_dir = self._view.homeDir.rstrip('/\\') if self._view.homeDir else ''
		from datetime import datetime as _dt
		default_name = f'integration_{_dt.now().strftime("%Y%m%d_%H%M%S")}.csv'
		default_path = os.path.join(start_dir, default_name) if start_dir else default_name

		file_path, _ = QFileDialog.getSaveFileName(
			self._view, 'Save Integration', default_path, 'CSV Files (*.csv)',
		)
		if not file_path:
			return
		if not file_path.lower().endswith('.csv'):
			file_path += '.csv'

		try:
			self._model.saveIntegration(
				self._view.integrationResults, file_path,
			)
			written = [file_path]
		except Exception as e:
			QMessageBox.critical(
				self._view,
				'Save Failed',
				f'Could not write integration file:\n\n{e}',
				QMessageBox.StandardButton.Ok,
			)
			return

		saved_count = len(self._view.integrationResults)

		# Clear in-memory records now that they've been persisted, and
		# disable Save Integration until the user integrates something new.
		self._view.integrationResults = []
		self._view.integrateButtons['Save Integration'].setEnabled(False)

		msg = QMessageBox(self._view)
		msg.setIcon(QMessageBox.Icon.Information)
		msg.setWindowTitle('Integration Saved')
		msg.setText(f'Saved {saved_count} record(s). In-memory results cleared.')
		msg.setInformativeText(
			'<b>File written:</b><br>' + '<br>'.join(
				os.path.basename(p) for p in written
			)
		)
		msg.setStandardButtons(QMessageBox.StandardButton.Ok)
		msg.exec()

	def _displayIntegrationResults(self, results, has_calibration):
		"""Display integration results in the results panel."""
		if not results:
			return

		lines = []
		for element, data in results.items():
			peak_area = data['peak_area']
			# Format peak area in scientific notation
			if peak_area >= 1e6:
				pa_str = f"{peak_area:.2e}"
			else:
				pa_str = f"{peak_area:.0f}"

			if data['conc_ppb'] is not None:
				conc_ppb = data['conc_ppb']
				conc_uM = data['conc_uM']
				lines.append(f"<b>{element}</b>: {pa_str} counts → {conc_ppb:.2f} ppb ({conc_uM:.3f} µM)")
			else:
				lines.append(f"<b>{element}</b>: {pa_str} counts")

		# Add integration range info
		range_min, range_max = self._intRange[0], self._intRange[1]
		header = f"<b>Integration</b> ({range_min:.2f} - {range_max:.2f} min)"
		if not has_calibration:
			header += " <i>[No calibration]</i>"

		results_text = header + "<br>" + " | ".join(lines)
		self._view.showIntegrationResults(results_text)

	def _displayComparisonResults(self, all_results, has_calibration):
		"""Display integration results for comparison mode (multiple files)."""
		if not all_results:
			return

		lines = []
		# Get the element (only 1 element in compare mode)
		element = self._view.activeElements[0] if self._view.activeElements else None

		if element:
			for filename, results in all_results.items():
				if element in results:
					data = results[element]
					peak_area = data['peak_area']
					# Format peak area in scientific notation
					if peak_area >= 1e6:
						pa_str = f"{peak_area:.2e}"
					else:
						pa_str = f"{peak_area:.0f}"

					if data['conc_ppb'] is not None:
						conc_ppb = data['conc_ppb']
						conc_uM = data['conc_uM']
						lines.append(f"<b>{filename}</b>: {pa_str} → {conc_ppb:.2f} ppb ({conc_uM:.3f} µM)")
					else:
						lines.append(f"<b>{filename}</b>: {pa_str} counts")

		# Add integration range info
		range_min, range_max = self._intRange[0], self._intRange[1]
		header = f"<b>Integration ({element})</b> ({range_min:.2f} - {range_max:.2f} min)"
		if not has_calibration:
			header += " <i>[No calibration]</i>"

		results_text = header + "<br>" + " | ".join(lines)
		self._view.showIntegrationResults(results_text)

	def _makePlot(self):
		'''makes plot & activates integration'''
		self._model.plotActiveElements()
	
	def _showCalWindow(self):
		''' opens the calibration window directly; elements can be selected from within '''
		self._calibrationPending = False
		self._openCalibrationWindow()

	def _openCalibrationWindow(self):
		'''Opens the calibration window. Element selection happens inside the window.'''
		self.calWindow = Calibration(view=self._view)
		calmodel = CalibrateFunctions(calview=self.calWindow, mainview=self._view)
		CalCtrlFunctions(
			model=calmodel, mainview=self._view, view=self.calWindow, mainctrl=self,
		)
		self.calWindow.show()

	def _showPeriodicTable(self):
		''' opens periodic table for element selection '''
		self._ptview = PTView(mainview=self._view)
		ptmodel = PTModel(ptview=self._ptview, mainview=self._view, maincontrol=self)
		PTCtrl(model=ptmodel, mainview=self._view, ptview=self._ptview, mainctrl=self)
		self._ptview.show()

	def _reorderListWidget(self, key):
		'''Re-sort the file listwidget in place using the provided key fn.'''
		lw = self._view.listwidget
		names = [lw.item(i).text() for i in range(lw.count())]
		names.sort(key=key)
		lw.clear()
		for name in names:
			lw.insertItem(lw.count(), name)

	def _sortListByName(self):
		'''Alphabetical (case-insensitive) sort.'''
		self._reorderListWidget(lambda fn: fn.lower())

	def _sortListByNumber(self):
		'''Sort by the trailing "_XX" number so 1, 2, ..., 10 come out
		numerically. Items without that suffix sort alphabetically after
		all numbered ones.'''
		import re as _re
		num_re = _re.compile(r'_(\d+)\.csv$', _re.IGNORECASE)

		def key(fn):
			m = num_re.search(fn)
			if m:
				return (0, int(m.group(1)), fn.lower())
			return (1, 0, fn.lower())

		self._reorderListWidget(key)

	def _updateCalibrateButtonStyle(self):
		'''Blue when no calibration is loaded, neutral once one is.'''
		btn = self._view.integrateButtons['Calibrate']
		if getattr(self._view, 'calCurves', None):
			btn.setStyleSheet(self._view._buttonStyle)
		else:
			btn.setStyleSheet(self._view._calibrateHighlightStyle)

	def _loadCalFile(self):
		''' loads cal file and saves to self._view.calCurves '''
		self._view.integrateButtons['Load Cal.'].setStyleSheet("background-color: light gray")

		# Search for calibration file
		calfile = None
		for root, dirs, files in os.walk(self._view.homeDir):
			for ff in files:
				if ff.endswith('.calib'):
					calfile = os.path.join(root, ff)
					break
			if calfile:
				break

		if calfile is None:
			self._view.statusBar.showMessage('No calibration file (.calib) found in directory', 5000)
			self._view.calib_label.setText('No calibration')
			print('ERROR: No .calib file found in directory')
			return

		try:
			with open(calfile) as file:
				self._view.calCurves = json.load(file)

			# Debug output to verify calibration loaded
			print(f'Loaded calibration from: {calfile}')
			print(f'Calibration elements: {list(self._view.calCurves.keys())}')

			# Update status bar and label
			num_elements = len(self._view.calCurves)
			self._view.statusBar.showMessage(f'Loaded calibration file: {os.path.basename(calfile)} ({num_elements} elements)', 5000)
			self._view.calib_label.setText(f'Calibration loaded ({num_elements} elements)')
			self._updateCalibrateButtonStyle()
		except Exception as e:
			self._view.statusBar.showMessage(f'Error loading calibration: {str(e)}', 5000)
			self._view.calib_label.setText('Calibration error')
			print(f'ERROR loading calibration file: {e}')

	def _selectInNormFile(self):
		''' opens window to select normalization file for 115In correction; saves average 115In signal from norm file'''
		filepath, _ = QFileDialog.getOpenFileName(
			self._view, "Select Normalization File", self._view.homeDir, "CSV Files (*.csv);;All Files (*)"
		)
		if not filepath:
			return
		try:
			normData = self._model.importData_generic(fdir=filepath)
		except Exception as e:
			self._view.statusBar.showMessage(f'Error reading normalization file: {e}', 5000)
			print(f'ERROR reading normalization file: {e}')
			return
		indium_col = next(
			(col for col in normData.columns if col.startswith('115In') and 'Time' not in col),
			None,
		)
		if indium_col is None:
			self._view.statusBar.showMessage('115In not found in normalization file', 5000)
			print('ERROR: 115In column not found in normalization file')
			print(f'  Columns available: {list(normData.columns)}')
			return
		indium_values = normData[indium_col].dropna()
		n_points = len(indium_values)
		avg_in = float(np.average(indium_values))
		std_in = float(np.std(indium_values))
		median_in = float(np.median(indium_values))

		self._view.normAvIndium = avg_in
		print(f'115In normalization loaded: avg = {avg_in:.2f} (column: {indium_col})')
		self._view.statusBar.showMessage(
			f'115In correction loaded (avg = {avg_in:.2f})', 4000
		)
		self._view.integrateButtons['115In Correction'].setEnabled(False)

		msg = QMessageBox(self._view)
		msg.setIcon(QMessageBox.Icon.Information)
		msg.setWindowTitle("115In Normalization Loaded")
		msg.setText("115In normalization reference has been set.")
		msg.setInformativeText(
			f"<b>File:</b> {os.path.basename(filepath)}<br>"
			f"<b>Column used:</b> {indium_col}<br>"
			f"<b>Data points:</b> {n_points}<br><br>"
			f"<b>Mean 115In:</b> {avg_in:.2f} counts<br>"
			f"<b>Median 115In:</b> {median_in:.2f} counts<br>"
			f"<b>Std dev:</b> {std_in:.2f} counts "
			f"({(std_in / avg_in * 100) if avg_in else 0:.1f}% RSD)<br><br>"
			"<b>How the correction is applied:</b><br>"
			"For each integrated sample, a correction factor is computed as "
			"<i>avg(sample 115In) / avg(reference 115In)</i>. "
			"All element intensities are divided by this factor before integration. "
			"For sample files with &gt; 2000 points, only rows 550&ndash;2500 are "
			"averaged to avoid transient regions; shorter files use all rows."
		)
		msg.setStandardButtons(QMessageBox.StandardButton.Ok)
		msg.exec()
		
	def _resetIntegrate(self):
		self._intRange = []
		self._model.removeIntRange()
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")
		self._view.integrateButtons['Integrate'].setEnabled(False)
		# Clear integration results display
		self._view.hideIntegrationResults()

	def _confirmReset(self):
		"""Reset plot without confirmation dialog."""
		self._clearForm()
		self._view.statusBar.showMessage('Plot reset', 2000)

	def _check_for_updates(self):
		"""Check for updates on startup"""
		try:
			from ..utils.update_checker import check_updates_on_startup
			self._update_thread = check_updates_on_startup(parent=self._view, silent=True)
			# Store thread to prevent garbage collection
		except ImportError:
			# Update checker not available (might be in development mode)
			pass
		except Exception as e:
			# Silently fail - update check is not critical
			pass

	def _exportPlot(self):
		"""Export plot to image file (PNG, SVG, or PDF) with optional Python script and data."""
		from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel
		import pyqtgraph.exporters
		import os

		# Show file dialog with format options
		file_filter = "PNG Image (*.png);;SVG Vector (*.svg);;PDF Document (*.pdf)"
		default_name = "plot.png"

		# Get current file name if available
		if self._view.listwidget.currentItem() is not None:
			current_file = self._view.listwidget.currentItem().text()
			base_name = current_file.replace('.csv', '')
			default_name = f"{base_name}_plot.png"

		file_path, selected_filter = QFileDialog.getSaveFileName(
			self._view,
			"Save Plot",
			default_name,
			file_filter
		)

		if not file_path:
			return  # User cancelled

		# Ask user about exporting data and script
		export_dialog = QDialog(self._view)
		export_dialog.setWindowTitle("Export Options")
		layout = QVBoxLayout()

		label = QLabel("Select additional files to export:")
		layout.addWidget(label)

		data_checkbox = QCheckBox("Export data CSV")
		data_checkbox.setChecked(True)
		data_checkbox.setToolTip("Export minimal dataset used in the plot")
		layout.addWidget(data_checkbox)

		script_checkbox = QCheckBox("Export Python script")
		script_checkbox.setChecked(True)
		script_checkbox.setToolTip("Export Python script to recreate the plot")
		layout.addWidget(script_checkbox)

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
		buttons.accepted.connect(export_dialog.accept)
		buttons.rejected.connect(export_dialog.reject)
		layout.addWidget(buttons)

		export_dialog.setLayout(layout)

		if export_dialog.exec() != QDialog.DialogCode.Accepted:
			return  # User cancelled

		export_data = data_checkbox.isChecked()
		export_script = script_checkbox.isChecked()

		try:
			# Get current plot view limits
			view_range = self._view.plotSpace.viewRange()
			x_limits = view_range[0]  # (xmin, xmax)
			y_limits = view_range[1]  # (ymin, ymax)

			# Create appropriate plot based on mode
			if self._view.compareMode and self._view.comparisonData:
				# Comparison mode: create custom matplotlib plot
				fig = self._createComparisonPlot(x_limits, y_limits)
			else:
				# Normal mode: use matplotlib static plot for all exports
				fig = self._createNormalPlot(x_limits, y_limits)

			# Save the figure with high DPI for quality
			fig.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='white')

			# Close the figure to free memory
			import matplotlib.pyplot as plt
			plt.close(fig)

			# Export data and Python script if requested
			if export_data or export_script:
				self._exportDataAndScript(file_path, export_data, export_script)

			# Build status message
			exported_items = ["Plot"]
			if export_data:
				exported_items.append("data")
			if export_script:
				exported_items.append("script")
			items_str = ", ".join(exported_items)

			self._view.statusBar.showMessage(f'{items_str} exported to {os.path.dirname(file_path)}', 5000)

		except Exception as e:
			QMessageBox.warning(
				self._view,
				'Export Error',
				f'Failed to export plot: {str(e)}',
				QMessageBox.StandardButton.Ok
			)

	def _createComparisonPlot(self, x_limits, y_limits):
		"""Create matplotlib figure for comparison mode export."""
		import matplotlib.pyplot as plt
		import seaborn as sns
		from matplotlib.ticker import MaxNLocator, FuncFormatter
		from uiGenerator.utils.analyte_formatter import format_analyte_latex
		import math

		# Get the single element being compared
		element = self._view.activeElements[0]
		formatted_element = format_analyte_latex(element)

		# Create figure
		fig, ax = plt.subplots(figsize=(10, 6))
		fig.subplots_adjust(right=0.75)

		# Generate colors for files
		num_files = len(self._view.comparisonData)
		colors = sns.color_palette(n_colors=num_files)

		# Plot each file
		lines = []
		labels = []
		for i, (compare_data, filename) in enumerate(zip(self._view.comparisonData, self._view.comparisonFiles)):
			# Use custom label if available, otherwise extract from filename
			if filename in self._view.comparisonLabels:
				short_name = self._view.comparisonLabels[filename]
			elif "LCICPMS_" in filename and ".csv" in filename:
				start = filename.index("LCICPMS_") + len("LCICPMS_")
				end = filename.index(".csv")
				short_name = filename[start:end]
			else:
				short_name = filename.replace('.csv', '')

			# Get data
			time_col = f'Time {element}'
			if time_col in compare_data.columns:
				icpms_time = compare_data[time_col] / 60
				icpms_signal = compare_data[element]

				# Plot
				p, = ax.plot(icpms_time, icpms_signal, color=colors[i], linewidth=2.5, label=short_name)
				lines.append(p)
				labels.append(short_name)

		# Formatting
		ax.set_xlabel('Time (min)', fontsize=12)
		ax.set_ylabel('Signal Intensity (cps)', fontsize=12)
		ax.set_title(f'{formatted_element}', fontsize=14)

		# Use current view limits from plot window
		ax.set_xlim(x_limits[0], x_limits[1])
		ax.set_ylim(y_limits[0], y_limits[1])

		# Custom y-axis formatter matching interactive plot
		def custom_y_formatter(value, pos):
			"""Format y-axis: integers for < 10000, exponential with superscripts for >= 10000."""
			superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
			                   '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
			                   '-': '⁻'}

			if abs(value) >= 10000:
				if value == 0:
					return '0'
				exponent = int(math.floor(math.log10(abs(value))))
				mantissa = value / (10 ** exponent)

				if mantissa == int(mantissa):
					mantissa_str = str(int(mantissa))
				else:
					mantissa_str = f'{mantissa:.1f}'

				exp_str = ''.join(superscript_map.get(c, c) for c in str(exponent))
				return f'{mantissa_str}×10{exp_str}'
			else:
				return f'{int(value)}'

		ax.yaxis.set_major_formatter(FuncFormatter(custom_y_formatter))

		# Legend
		ax.legend(lines, labels, frameon=False, bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0)

		# Tick formatting
		tkw = dict(size=4, width=1.5)
		ax.tick_params(axis='y', **tkw)
		ax.tick_params(axis='x', **tkw)

		ax.xaxis.set_major_locator(MaxNLocator(4))
		ax.xaxis.set_minor_locator(MaxNLocator(20))
		ax.yaxis.set_major_locator(MaxNLocator(4))
		ax.yaxis.set_minor_locator(MaxNLocator(20))

		sns.despine()

		return fig

	def _createNormalPlot(self, x_limits, y_limits):
		"""Create matplotlib figure for normal mode export."""
		import matplotlib.pyplot as plt
		import seaborn as sns
		from matplotlib.ticker import MaxNLocator, FuncFormatter
		from uiGenerator.utils.analyte_formatter import format_analyte_latex
		import math

		# Create figure
		fig, ax = plt.subplots(figsize=(10, 6))
		fig.subplots_adjust(right=0.75)

		# Generate colors based on actual elements being plotted
		num_colors = max(len(self._view.activeElements), 1)
		colors = sns.color_palette(n_colors=num_colors)
		color_dict = {self._view.activeElements[i]: colors[i] if i < len(colors) else 'gray' for i in range(len(self._view.activeElements))}

		# Plot each element
		lines = []
		labels = []
		for m in self._view.activeElements:
			icpms_time = np.asarray(self._model._data['Time ' + m], dtype=float) / 60
			icpms_signal = np.asarray(self._model._data[m], dtype=float)
			# Drop points where time == 0 so exported plots don't get phantom
			# line segments diving back to the origin.
			mask = np.isfinite(icpms_time) & (icpms_time > 0)
			icpms_time = icpms_time[mask]
			icpms_signal = icpms_signal[mask]
			if len(icpms_time) == 0:
				continue
			formatted_label = format_analyte_latex(m)
			p, = ax.plot(icpms_time, icpms_signal, color=color_dict[m], linewidth=2.5, label=formatted_label)
			lines.append(p)
			labels.append(formatted_label)

		# Formatting
		ax.set_xlabel('Time (min)', fontsize=12)
		ax.set_ylabel('Signal Intensity (cps)', fontsize=12)

		# Use current view limits from plot window
		ax.set_xlim(x_limits[0], x_limits[1])
		ax.set_ylim(y_limits[0], y_limits[1])

		# Custom y-axis formatter matching interactive plot
		def custom_y_formatter(value, pos):
			"""Format y-axis: integers for < 10000, exponential with superscripts for >= 10000."""
			superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
			                   '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
			                   '-': '⁻'}

			if abs(value) >= 10000:
				if value == 0:
					return '0'
				exponent = int(math.floor(math.log10(abs(value))))
				mantissa = value / (10 ** exponent)

				if mantissa == int(mantissa):
					mantissa_str = str(int(mantissa))
				else:
					mantissa_str = f'{mantissa:.1f}'

				exp_str = ''.join(superscript_map.get(c, c) for c in str(exponent))
				return f'{mantissa_str}×10{exp_str}'
			else:
				return f'{int(value)}'

		ax.yaxis.set_major_formatter(FuncFormatter(custom_y_formatter))

		# Tick formatting
		tkw = dict(size=4, width=1.5)
		ax.tick_params(axis='y', **tkw)
		ax.tick_params(axis='x', **tkw)

		ax.xaxis.set_major_locator(MaxNLocator(4))
		ax.xaxis.set_minor_locator(MaxNLocator(20))
		ax.yaxis.set_major_locator(MaxNLocator(4))
		ax.yaxis.set_minor_locator(MaxNLocator(20))

		ax.legend(lines, labels, frameon=False, bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0)
		sns.despine()

		return fig

	def _exportDataAndScript(self, plot_file_path, export_data=True, export_script=True):
		"""Export minimal data CSV and Python script to recreate the plot."""
		import os
		import pandas as pd

		if not export_data and not export_script:
			return  # Nothing to export

		# Get base path without extension
		base_path = os.path.splitext(plot_file_path)[0]
		data_path = f"{base_path}_data.csv" if export_data else None
		script_path = f"{base_path}_plot.py" if export_script else None

		# Handle comparison mode vs normal mode
		if self._view.compareMode and self._view.comparisonData:
			# Comparison mode: export data for all compared files
			self._exportComparisonDataAndScript(base_path, data_path, script_path, export_data, export_script)
		else:
			# Normal mode: export data for single file
			self._exportNormalDataAndScript(base_path, data_path, script_path, export_data, export_script)

	def _exportNormalDataAndScript(self, base_path, data_path, script_path, export_data, export_script):
		"""Export data and script for normal (single file) mode."""
		import pandas as pd
		import os

		# Export data if requested
		if export_data:
			# Create minimal dataset with only active elements
			data_dict = {}
			for element in self._view.activeElements:
				time_col = f'Time {element}'
				if time_col in self._model._data.columns:
					# Convert time to minutes
					data_dict[f'Time_{element}_min'] = self._model._data[time_col] / 60
					data_dict[element] = self._model._data[element]

			# Save to CSV
			df = pd.DataFrame(data_dict)
			df.to_csv(data_path, index=False)

		# Export script if requested
		if export_script:
			# Generate Python script
			data_filename = os.path.basename(data_path) if export_data else "your_data.csv"
			script_content = self._generateNormalPlotScript(
				data_filename,
				self._view.activeElements
			)

			with open(script_path, 'w') as f:
				f.write(script_content)

	def _exportComparisonDataAndScript(self, base_path, data_path, script_path, export_data_flag, export_script_flag):
		"""Export data and script for comparison mode."""
		import pandas as pd
		import os

		# Get the single element being compared
		element = self._view.activeElements[0]

		# Build label map (needed for both data and script)
		label_map = {}
		for filename in self._view.comparisonFiles:
			if filename in self._view.comparisonLabels:
				short_name = self._view.comparisonLabels[filename]
			elif "LCICPMS_" in filename and ".csv" in filename:
				start = filename.index("LCICPMS_") + len("LCICPMS_")
				end = filename.index(".csv")
				short_name = filename[start:end]
			else:
				short_name = filename.replace('.csv', '')
			label_map[filename] = short_name

		# Export data if requested
		if export_data_flag:
			# Create dataset with all files
			data_dict = {}
			for i, (compare_data, filename) in enumerate(zip(self._view.comparisonData, self._view.comparisonFiles)):
				short_name = label_map[filename]

				time_col = f'Time {element}'
				if time_col in compare_data.columns:
					data_dict[f'Time_{short_name}_min'] = compare_data[time_col] / 60
					data_dict[f'{element}_{short_name}'] = compare_data[element]

			# Save to CSV
			df = pd.DataFrame(data_dict)
			df.to_csv(data_path, index=False)

		# Export script if requested
		if export_script_flag:
			# Generate Python script for comparison mode
			data_filename = os.path.basename(data_path) if export_data_flag else "your_data.csv"
			script_content = self._generateComparisonPlotScript(
				data_filename,
				element,
				self._view.comparisonFiles,
				label_map
			)

			with open(script_path, 'w') as f:
				f.write(script_content)

	def _generateNormalPlotScript(self, data_filename, elements):
		"""Generate Python script for normal mode plotting."""
		from uiGenerator.utils.analyte_formatter import format_analyte_latex

		# Build element list string
		elements_list = ', '.join([f'"{e}"' for e in elements])

		# Build plot commands
		plot_commands = []
		for i, element in enumerate(elements):
			formatted_label = format_analyte_latex(element)
			plot_commands.append(
				f"    plt.plot(data['Time_{element}_min'], data['{element}'], "
				f"linewidth=2.5, label=r'{formatted_label}')"
			)

		script = f'''#!/usr/bin/env python3
"""
Auto-generated script to recreate LC-ICP-MS plot
Generated by LCICPMS-ui
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read data
data = pd.read_csv('{data_filename}')

# Generate colors
elements = [{elements_list}]
num_colors = max(len(elements), 1)
colors = sns.color_palette(n_colors=num_colors)
color_dict = {{elements[i]: colors[i] if i < len(colors) else 'gray' for i in range(len(elements))}}

# Create plot
fig, ax = plt.subplots(figsize=(10, 6))

# Plot each element
{chr(10).join(plot_commands)}

# Formatting
ax.set_xlabel('Time (min)', fontsize=12)
ax.set_ylabel('Signal Intensity (cps)', fontsize=12)
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.legend(frameon=False, bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0)
sns.despine()

plt.tight_layout()
plt.show()
'''
		return script

	def _generateComparisonPlotScript(self, data_filename, element, filenames, label_map):
		"""Generate Python script for comparison mode plotting."""
		from uiGenerator.utils.analyte_formatter import format_analyte_latex

		# Get labels from label_map (already includes custom labels if set)
		short_names = [label_map[filename] for filename in filenames]

		# Build plot commands
		plot_commands = []
		for i, short_name in enumerate(short_names):
			plot_commands.append(
				f"    plt.plot(data['Time_{short_name}_min'], data['{element}_{short_name}'], "
				f"linewidth=4, label='{short_name}')"
			)

		formatted_element = format_analyte_latex(element)

		script = f'''#!/usr/bin/env python3
"""
Auto-generated script to recreate LC-ICP-MS comparison plot
Generated by LCICPMS-ui
Element: {element}
Files compared: {len(filenames)}
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read data
data = pd.read_csv('{data_filename}')

# Generate colors for files
num_files = {len(filenames)}
colors = sns.color_palette(n_colors=num_files)

# Create plot
fig, ax = plt.subplots(figsize=(10, 6))

# Plot each file
{chr(10).join(plot_commands)}

# Formatting
ax.set_xlabel('Time (min)', fontsize=12)
ax.set_ylabel('Signal Intensity (cps)', fontsize=12)
ax.set_title(r'{formatted_element}')
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.legend(frameon=False, bbox_to_anchor=(1.04, 0.5), loc="center left", borderaxespad=0)
sns.despine()

plt.tight_layout()
plt.show()
'''
		return script

	def _connectSignals(self):
		"""Connect signals and slots."""
		self._view.buttons['Reset'].setEnabled(False)
		self._view.buttons['Export Plot'].setEnabled(False)
		# Select Elements button is always enabled - periodic table can be opened anytime
		# Calibrate is always enabled: users can open the calibration window
		# without first choosing a directory and pick elements from within.
		self._view.integrateButtons['Calibrate'].setEnabled(True)
		self._view.integrateButtons['Load Cal.'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.integrateButtons['115In Correction'].setEnabled(False)

		self._view.listwidget.setCurrentItem(None)
		self._view.buttons['Directory'].clicked.connect(self._selectDirectory)
		self._view.buttons['Select Elements'].clicked.connect(self._showPeriodicTable)

		self._view.listwidget.currentItemChanged.connect(self._importAndActivatePlotting)
		self._view.listwidget.itemDoubleClicked.connect(lambda: self._importAndActivatePlotting())

		self._view.intbox.stateChanged.connect(self._selectIntRange)
		self._view.compareFilesBtn.clicked.connect(self._toggleCompareMode)

		self._view.buttons['Reset'].clicked.connect(self._confirmReset)
		self._view.buttons['Export Plot'].clicked.connect(self._exportPlot)
		self._view.buttons['Sort By Name'].clicked.connect(self._sortListByName)
		self._view.buttons['Sort By Number'].clicked.connect(self._sortListByNumber)

		self._view.integrateButtons['Calibrate'].clicked.connect(self._showCalWindow)
		self._view.integrateButtons['Load Cal.'].clicked.connect(self._loadCalFile)
		self._view.integrateButtons['Integrate'].clicked.connect(self._Integrate)
		self._view.integrateButtons['Save Integration'].clicked.connect(self._saveIntegration)
		self._view.integrateButtons['Reset Integration'].clicked.connect(self._resetIntegrate)

		# Comparison list buttons and interactions
		self._view.addToCompareBtn.clicked.connect(self._addToComparisonList)
		self._view.removeFromCompareBtn.clicked.connect(self._removeFromComparisonList)
		self._view.clearCompareBtn.clicked.connect(self._clearComparisonList)
		self._view.listwidget.itemSelectionChanged.connect(self._updateCompareButtons)
		self._view.compareListWidget.itemSelectionChanged.connect(self._updateCompareButtons)
		self._view.compareListWidget.itemSelectionChanged.connect(self._updateComparisonPlot)
		self._view.compareListWidget.itemDoubleClicked.connect(self._editComparisonLabel)




