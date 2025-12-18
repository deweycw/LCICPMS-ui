import sys 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
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

		# Connect signals and slots
		self._connectSignals()

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

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		if self._view.listwidget.currentItem() is not None:
			# In comparison mode, clicking main list doesn't do anything
			# User must use comparison list instead
			if self._view.compareMode:
				return

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

	def _mouseover(self, pos):
		''' selects range for integration'''
		act_pos = self._view.chroma.mapFromScene(pos)
		self._intPointX = act_pos.x()
		self._intPointY = act_pos.y()

	def _onClick(self, event):
		''' selects range for integration'''
		self._act_pos = self._view.chroma.mapFromScene(event[0].scenePos())
		cc = len(self._intRange)
		cc = cc + 1
		
		if cc == 1:
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			self._view.statusBar.showMessage(f'Integration start: {self._act_pos.x():.2f} min', 3000)
			self._model.plotLowRange(self._act_pos.x(),self._n)
			self._minAssigned = True

		if (cc == 2) and self._minAssigned is True:
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			self._view.statusBar.showMessage(f'Integration end: {self._act_pos.x():.2f} min | Range: {self._intRange[-1] - self._intRange[-2]:.2f} min', 5000)
			self._model.plotHighRange(self._act_pos.x(),self._n)
			self._view.integrateButtons['Integrate'].setEnabled(True)
			self._view.integrateButtons['Integrate'].setStyleSheet("background-color: red")
			self._n = self._n + 1

		self.n_clicks = 1

	def _selectIntRange(self,checked):
		'''select integration range'''
		if self._view.intbox.isChecked() == True:
			self._view.proxy = pg.SignalProxy(self._view.chroma.scene().sigMouseClicked, rateLimit=60, slot=self._onClick)
			self._view.statusBar.showMessage('Click plot to select integration range', 3000)
		else:
			self._view.proxy = None
			self._view.statusBar.showMessage('Integration range selection disabled', 2000)

	def _selectOneFile(self,checked):
		'''select integration range'''
		if self._view.oneFileBox.isChecked() == True:
			self._view.singleOutputFile = True
		else:
			self._view.singleOutputFile = False

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
					# Open periodic table for user to select one element
					self._showPeriodicTable()
				self._view.compareFilesBtn.setChecked(False)
				return

			# Check if comparison list has enough files
			if self._view.compareListWidget.count() < 2:
				QMessageBox.information(
					self._view,
					'Add Files to Compare',
					'Please add at least 2 files to the comparison list using the "Add →" button.\n\n'
					'You can add up to 12 files to compare.',
					QMessageBox.StandardButton.Ok
				)
				self._view.compareFilesBtn.setChecked(False)
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
		from PyQt6.QtWidgets import QMessageBox

		if self._view.listwidget.currentItem() is None:
			return

		# Check if already at max
		if self._view.compareListWidget.count() >= 12:
			QMessageBox.warning(
				self._view,
				'Maximum Reached',
				'Comparison mode supports a maximum of 12 files.',
				QMessageBox.StandardButton.Ok
			)
			return

		filename = self._view.listwidget.currentItem().text()

		# Check if already in comparison list
		for i in range(self._view.compareListWidget.count()):
			if self._view.compareListWidget.item(i).text() == filename:
				self._view.statusBar.showMessage(f'{filename} is already in comparison list', 2000)
				return

		# Add to comparison list
		self._view.compareListWidget.addItem(filename)
		self._view.statusBar.showMessage(f'Added {filename} to comparison ({self._view.compareListWidget.count()}/12)', 2000)

		# Update button states
		self._updateCompareButtons()

		# If comparison mode is already active, reload and replot
		if self._view.compareMode:
			self._loadComparisonFiles()
		# Otherwise, auto-enable comparison mode if we have 2+ files and 1 element
		elif (self._view.compareListWidget.count() >= 2 and
		      len(self._view.activeElements) == 1):
			self._view.compareFilesBtn.setChecked(True)

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

	def _clearComparisonList(self):
		"""Clear all files from comparison list."""
		self._view.compareListWidget.clear()
		self._view.statusBar.showMessage('Cleared comparison list', 2000)
		self._updateCompareButtons()

		# Disable comparison mode
		if self._view.compareMode:
			self._view.compareFilesBtn.setChecked(False)

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

		# Enable Compare Files button if 2+ files in comparison list and 1 element selected
		has_enough_files = self._view.compareListWidget.count() >= 2
		has_one_element = len(self._view.activeElements) == 1
		self._view.compareFilesBtn.setEnabled(has_enough_files and has_one_element)

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
		''' call integration function'''
		if len(self._view.calCurves) > 0:
			self._model.integrate(self._intRange)
			#self._intRange = []
			self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")
		else:
			self._view.integrateButtons['Load Cal.'].setStyleSheet("background-color: yellow")

	def _makePlot(self):
		'''makes plot & activates integration'''
		self._model.plotActiveElements()
	
	def _showCalWindow(self):
		''' opens calibration window '''
		#self.dialog = Calibration(view = self._view)


		self.calWindow = Calibration(view = self._view)
		calmodel = CalibrateFunctions(calview= self.calWindow, mainview = self._view)
		CalCtrlFunctions(model=calmodel, mainview = self._view,view= self.calWindow)
		self.calWindow.show()

	def _showPeriodicTable(self):
		''' opens periodic table for element selection '''
		self._ptview = PTView(mainview=self._view)
		ptmodel = PTModel(ptview=self._ptview, mainview=self._view, maincontrol=self)
		PTCtrl(model=ptmodel, mainview=self._view, ptview=self._ptview, mainctrl=self)
		self._ptview.show()

	def _loadCalFile(self):
		''' loads cal file and saves to self._mainview.calCurves '''
		self._view.integrateButtons['Load Cal.'].setStyleSheet("background-color: light gray")
		for root, dirs, files in os.walk(self._view.homeDir):
			for ff in files:
				if '.calib' in ff:
					calfile = os.path.join(root,ff)

		with open(calfile) as file:
			self._view.calCurves = json.load(file)

		# Update status bar and label
		self._view.statusBar.showMessage(f'Loaded calibration file: {os.path.basename(calfile)}', 5000)
		self._view.calib_label.setText('Calibration loaded')

	def _selectInNormFile(self):
		''' opens window to select normalization file for 115In correction; saves average 115In signal from norm file'''
		dialog = QFileDialog()
		dialog.setWindowTitle("Select Normalization File")
		dialog.setViewMode(QFileDialog.ViewMode.Detail)
		filepath = dialog.getOpenFileName(self._view,"Openfile")[0]
		normData = self._model.importData_generic(fdir = filepath )
		self._view.normAvIndium = np.average(normData['115In'])
		#print(self._view.normAvIndium)
		self._view.integrateButtons['115In Correction'].setEnabled(False)
		
	def _resetIntegrate(self):
		self._intRange = []
		self._model.removeIntRange()
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")
		self._view.integrateButtons['Integrate'].setEnabled(False)

	def _confirmReset(self):
		"""Show confirmation dialog before resetting plot."""
		from PyQt6.QtWidgets import QMessageBox

		# Check if there's anything to reset
		if not self._view.activeElements and not self._intRange:
			# Nothing to reset, just clear
			self._clearForm()
			return

		# Show confirmation dialog
		reply = QMessageBox.question(
			self._view,
			'Confirm Reset',
			'Are you sure you want to reset the plot?\n\nThis will clear:\n- Current plot view\n- Integration ranges\n- Selected elements',
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)

		if reply == QMessageBox.StandardButton.Yes:
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
			"Export Plot",
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
			icpms_time = self._model._data['Time ' + m] / 60
			icpms_signal = self._model._data[m]
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
		self._view.integrateButtons['Calibrate'].setEnabled(False)
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
		self._view.oneFileBox.stateChanged.connect(self._selectOneFile)
		self._view.baseSubtractBox.stateChanged.connect(self._baselineSubtraction)

		self._view.buttons['Reset'].clicked.connect(self._confirmReset)
		self._view.buttons['Export Plot'].clicked.connect(self._exportPlot)

		self._view.integrateButtons['Calibrate'].clicked.connect(self._showCalWindow)
		self._view.integrateButtons['Load Cal.'].clicked.connect(self._loadCalFile)
		self._view.integrateButtons['Integrate'].clicked.connect(self._Integrate)
		self._view.integrateButtons['115In Correction'].clicked.connect(self._selectInNormFile)
		self._view.integrateButtons['Reset Integration'].clicked.connect(self._resetIntegrate)

		# Comparison list buttons and interactions
		self._view.addToCompareBtn.clicked.connect(self._addToComparisonList)
		self._view.removeFromCompareBtn.clicked.connect(self._removeFromComparisonList)
		self._view.clearCompareBtn.clicked.connect(self._clearComparisonList)
		self._view.listwidget.itemSelectionChanged.connect(self._updateCompareButtons)
		self._view.compareListWidget.itemSelectionChanged.connect(self._updateCompareButtons)
		self._view.compareListWidget.itemSelectionChanged.connect(self._updateComparisonPlot)
		self._view.compareListWidget.itemDoubleClicked.connect(self._editComparisonLabel)




