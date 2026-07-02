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
	def __init__(self, model, view, mainview, mainctrl=None):
		"""Controller initializer."""
		print("\n=== Calibration Controller Initializing ===")
		self._model = model
		self._calview = view
		self._mainview = mainview
		self._mainctrl = mainctrl

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
			# Remove trailing slash for consistent path handling (both / and \ for cross-platform)
			main_dir = main_dir.rstrip('/\\')
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
			start_dir = self._mainview.homeDir.rstrip('/\\') if self._mainview.homeDir else ''
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

			# Reset any previous integration range selection so the user can
			# click to define a new range on this sample without first hitting
			# "Reset Range". The suggested default is still available via the
			# "Suggest Range" button.
			self._intRange = []
			self._minAssigned = False
			self._n = 0
			self._calview.integrateButtons['Integrate'].setEnabled(False)
			self._calview.integrateButtons['Integrate'].setStyleSheet("")

			# Enable integration mode (click on plot to select range)
			self._enableIntegration()
		except Exception as e:
			print(f"ERROR in _importAndActivatePlotting: {e}")
			import traceback
			traceback.print_exc()

	def _showDefaultRange(self):
		'''Show the default integration range (10th to 10th-to-last point).'''
		# Get suggested range from model
		suggested_range = self._model.suggestIntegrationRange()

		if suggested_range is None:
			return

		start_time, end_time = suggested_range

		# Reset any existing range
		self._intRange = [start_time, end_time]
		self._minAssigned = True
		self._n = 0

		# Plot the range lines
		self._model.plotLowRange(start_time, self._n)
		self._model.plotHighRange(end_time, self._n)

		# Enable integrate button if a standard is selected
		if self._calview.standardsTable.currentRow() >= 0:
			self._calview.integrateButtons['Integrate'].setEnabled(True)
			self._calview.integrateButtons['Integrate'].setStyleSheet("background-color: #ff6b6b")

	def _enableIntegration(self):
		"""Enable clicking on plot to select integration range.

		Bind to plotSpace.scene() (stable PlotWidget scene) rather than
		self._calview.chroma, which gets reassigned to a PlotDataItem each
		time plotActiveElements runs and can be None if plotting fails.
		"""
		if not self._integrationEnabled:
			self._calview.proxy = pg.SignalProxy(
				self._calview.plotSpace.scene().sigMouseClicked,
				rateLimit=60,
				slot=self._onClick,
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

		# Reset integration range selector for next standard
		self._intRange = []
		self._minAssigned = False
		self._n = 0  # Reset color index
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setStyleSheet("")

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
		'''Clears calibration data and resets the form. Preserves element selection.'''
		# Clear the standards table
		self._calview.clearStandardsTable()

		# Clear calibration curves only (preserve activeElements for periodic table)
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

		print('Calibration data cleared (elements preserved)')

	def _onClick(self, event):
		'''Handles clicks on plot to select integration range.

		Uses plotSpace's ViewBox to map scene coords to data coords, so this
		works regardless of what self._calview.chroma currently points at.
		'''
		vb = self._calview.plotSpace.getViewBox()
		self._act_pos = vb.mapSceneToView(event[0].scenePos())
		cc = len(self._intRange) + 1

		if cc == 1:
			self._intRange.append(self._act_pos.x())
			print(f'\tIntegration start: {self._act_pos.x():.2f} min')
			self._model.plotLowRange(self._act_pos.x(), self._n)
			self._minAssigned = True

		elif cc == 2 and self._minAssigned:
			self._intRange.append(self._act_pos.x())
			print(f'\tIntegration end: {self._act_pos.x():.2f} min')
			self._model.plotHighRange(self._act_pos.x(), self._n)

			# Enable integrate only when a standard row is also selected
			if self._calview.standardsTable.currentRow() >= 0:
				self._calview.integrateButtons['Integrate'].setEnabled(True)
				self._calview.integrateButtons['Integrate'].setStyleSheet(
					"background-color: #ff6b6b"
				)
			else:
				print('  (add/select a standard row to enable Integrate)')
			self._n += 1

		self.n_clicks = 1

	def _Integrate(self):
		'''Perform integration and store peak area in selected table row.'''
		from PyQt6.QtWidgets import QMessageBox

		selected_row = self._calview.standardsTable.currentRow()
		if selected_row < 0:
			print("Please select a standard in the table")
			return

		if len(self._intRange) < 2:
			print("Please select integration range on plot")
			return

		# Warn if the currently loaded sample doesn't match the selected row,
		# or the selected row already has a peak area — integrating would
		# overwrite the existing standard's area.
		current_item = self._calview.listwidget.currentItem()
		current_file = current_item.text() if current_item else ''
		row_file = self._calview.standardsTable.item(selected_row, 0).text()
		row_area_item = self._calview.standardsTable.item(selected_row, 3)
		row_has_area = bool(row_area_item and row_area_item.data(Qt.ItemDataRole.UserRole))

		if row_has_area or (current_file and current_file != row_file):
			row_name = self._calview.standardsTable.item(selected_row, 1).text()
			msg = QMessageBox(self._calview)
			msg.setIcon(QMessageBox.Icon.Warning)
			msg.setWindowTitle('Overwrite Standard?')
			msg.setText(f'This will overwrite the peak area for "{row_name}".')
			details = []
			if current_file and current_file != row_file:
				details.append(
					f'Selected row file:  {row_file}\n'
					f'Currently loaded:   {current_file}\n\n'
					'You may have moved to a new sample without adding it as a '
					'new standard. Add it via "Add Standard" first if you want '
					'to keep the current row.'
				)
			elif row_has_area:
				details.append(f'"{row_name}" already has an integrated peak area.')
			msg.setInformativeText('\n\n'.join(details))
			msg.setStandardButtons(
				QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
			)
			msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
			if msg.exec() != QMessageBox.StandardButton.Ok:
				print('Integration cancelled by user')
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
		self._n = 0  # Reset color index so next integration starts with first color
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setStyleSheet("")

	def _resetIntegration(self):
		'''Resets integration range selection without clearing the plot data.'''
		self._intRange = []
		self._n = 0
		self._minAssigned = False
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setStyleSheet("")

		# Clear plot and re-plot to remove integration range lines
		self._calview.plotSpace.clear()
		if self._calview.listwidget.currentItem() is not None:
			self._model.plotActiveElements()

		print('Integration range reset')

	def _suggestRange(self):
		'''Reset to default integration range (10th to 10th-to-last point).'''
		# Check if data is loaded
		if self._calview.listwidget.currentItem() is None:
			print("Please select a file first")
			return

		# Clear plot and re-plot to remove old range lines
		self._calview.plotSpace.clear()
		self._model.plotActiveElements()

		# Show the default range
		self._showDefaultRange()

		print(f'Reset to default integration range: {self._intRange[0]:.2f} - {self._intRange[1]:.2f} min')

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
		"""Calculate calibration curves from ALL standards in table (no selection required)."""
		from PyQt6.QtWidgets import QMessageBox

		# Get ALL standards from table (not just selected ones)
		standards_data = self._calview.getStandardsData()

		if len(standards_data) == 0:
			QMessageBox.warning(
				self._calview,
				'No Standards',
				'No standards in the table. Add standards and integrate them first.',
				QMessageBox.StandardButton.Ok
			)
			return

		# Validate data - check each standard has required fields
		valid_standards = []
		missing_info = []
		for std in standards_data:
			if std['concentration'] is not None and std['peak_areas'] is not None:
				valid_standards.append(std)
			else:
				missing = []
				if std['concentration'] is None:
					missing.append('concentration')
				if std['peak_areas'] is None:
					missing.append('peak area')
				missing_info.append(f"{std['name']}: missing {', '.join(missing)}")
				print(f"Skipping {std['name']}: missing concentration or peak area")

		if len(valid_standards) < 2:
			msg = 'Need at least 2 standards with concentration and peak area to calculate calibration curve.'
			if missing_info:
				msg += '\n\nIncomplete standards:\n• ' + '\n• '.join(missing_info)
			QMessageBox.warning(
				self._calview,
				'Insufficient Data',
				msg,
				QMessageBox.StandardButton.Ok
			)
			return

		print(f"Calculating calibration curve from {len(valid_standards)} standards (all table data, no selection required)")

		# Pass data to model for calculation
		summary = self._model.calcLinearRegression(valid_standards)
		self._showCalCurveSummary(summary, missing_info)
		# Main window's Calibrate button should no longer be highlighted now
		# that a calibration exists.
		if self._mainctrl is not None:
			self._mainctrl._updateCalibrateButtonStyle()

	def _showCalCurveSummary(self, summary, missing_info):
		"""Popup summarizing the Calculate Curve run: what fit, what didn't,
		where the PDF report and .calib file landed, whether 115In norm was
		applied. Icon shifts to warning if there were any skips.
		"""
		from PyQt6.QtWidgets import QMessageBox

		if not summary:
			QMessageBox.warning(
				self._calview,
				'Calibration Failed',
				'The calibration model returned no summary. Check the console.',
				QMessageBox.StandardButton.Ok,
			)
			return

		fitted = summary.get('fitted', [])
		skipped = summary.get('skipped', [])
		pdf_path = summary.get('pdf_path')
		calib_path = summary.get('calib_path')
		archived = summary.get('archived_calibs', [])
		in_norm = summary.get('in_norm_applied', False)
		std_count = summary.get('standards_count', 0)

		if not fitted:
			QMessageBox.warning(
				self._calview,
				'No Curves Calculated',
				'No elements could be fitted. '
				+ ('\n\n' + '\n'.join(f"• {el}: {reason}" for el, reason in skipped)
				   if skipped else ''),
				QMessageBox.StandardButton.Ok,
			)
			return

		# Compose an HTML body so we get bullet lists + monospace numbers.
		lines = [
			f"<b>{len(fitted)}</b> element(s) fitted from "
			f"<b>{std_count}</b> standard(s)."
		]
		if in_norm:
			lines.append('<b>115In normalization:</b> applied.')
		if missing_info:
			lines.append(
				f"<b>Excluded standards</b> ({len(missing_info)}): "
				+ ', '.join(missing_info)
			)
		if skipped:
			lines.append('<b>Skipped elements:</b>')
			lines.append('<ul style="margin-top:2px">'
			             + ''.join(f'<li>{el} — {reason}</li>'
			                       for el, reason in skipped) + '</ul>')

		# Fit table
		rows = ''.join(
			f'<tr>'
			f'<td>{f["element"]}</td>'
			f'<td align="right">{f["slope"]:.3e}</td>'
			f'<td align="right">{f["r2"]:.4f}</td>'
			f'<td align="right">{f["n"]}</td>'
			f'</tr>'
			for f in fitted
		)
		table_html = (
			'<table cellpadding="4" cellspacing="0" '
			'style="border-collapse:collapse;margin-top:6px">'
			'<tr style="background:#4682b4;color:white">'
			'<th align="left">Element</th>'
			'<th>Slope (ppb/count)</th>'
			'<th>R²</th>'
			'<th>N</th>'
			'</tr>' + rows + '</table>'
		)
		lines.append(table_html)

		if pdf_path:
			lines.append(f'<b>PDF report:</b> {os.path.basename(pdf_path)}')
		if calib_path:
			lines.append(f'<b>Calibration file:</b> {os.path.basename(calib_path)}')
		if archived:
			lines.append(
				f'<b>Archived previous:</b> '
				+ ', '.join(os.path.basename(a) for a in archived)
			)

		msg = QMessageBox(self._calview)
		icon = QMessageBox.Icon.Warning if skipped else QMessageBox.Icon.Information
		msg.setIcon(icon)
		msg.setWindowTitle('Calibration Complete')
		msg.setTextFormat(Qt.TextFormat.RichText)
		msg.setText('Calibration curves calculated.')
		msg.setInformativeText('<br>'.join(lines))
		msg.setStandardButtons(QMessageBox.StandardButton.Ok)
		msg.exec()

	def _reorderListWidget(self, key):
		'''Re-sort the cal file list in place using the provided key fn.'''
		lw = self._calview.listwidget
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
		numerically; items without that suffix sort alphabetically after all
		numbered ones.'''
		import re as _re
		num_re = _re.compile(r'_(\d+)\.csv$', _re.IGNORECASE)

		def key(fn):
			m = num_re.search(fn)
			if m:
				return (0, int(m.group(1)), fn.lower())
			return (1, 0, fn.lower())

		self._reorderListWidget(key)

	def _openPeriodicTable(self):
		"""Open the periodic table so the user can select elements to calibrate.

		If no data file has been loaded yet, `_analytes_by_element` is empty
		and every button in the periodic table would render as disabled/gray.
		Seed the map from the calibration window's canonical isotope list so
		users can pick elements before loading any files.
		"""
		if self._mainctrl is None:
			print('ERROR: no main controller reference; cannot open periodic table')
			return

		if not self._mainview._analytes_by_element:
			import re
			# Broad default set of common ICP-MS analytes (most-abundant isotope
			# for each element typically measured). Used only when no data file
			# has been loaded yet; a real file replaces this with its own list.
			default_isotopes = [
				'7Li', '9Be', '11B', '23Na', '24Mg', '27Al', '28Si', '31P', '34S',
				'39K', '43Ca', '45Sc', '47Ti', '51V', '52Cr', '55Mn', '56Fe',
				'59Co', '60Ni', '63Cu', '66Zn', '69Ga', '72Ge', '75As', '78Se',
				'85Rb', '88Sr', '89Y', '90Zr', '93Nb', '95Mo', '107Ag', '111Cd',
				'115In', '118Sn', '121Sb', '125Te', '127I', '133Cs', '137Ba',
				'139La', '140Ce', '141Pr', '146Nd', '147Sm', '153Eu', '157Gd',
				'159Tb', '163Dy', '165Ho', '166Er', '169Tm', '172Yb', '175Lu',
				'178Hf', '181Ta', '182W', '185Re', '192Os', '193Ir', '195Pt',
				'197Au', '202Hg', '205Tl', '208Pb', '209Bi', '232Th', '238U',
			]
			analytes_by_element = {}
			elements_in_file = []
			for analyte in default_isotopes:
				isotope = analyte.split(' | ')[0] if ' | ' in analyte else analyte
				match = re.search(r'(\d+)([A-Z][a-z]?)', isotope)
				if not match:
					continue
				symbol = match.group(2)
				analytes_by_element.setdefault(symbol, []).append(analyte)
				elements_in_file.append(analyte)
			self._mainview._analytes_by_element = analytes_by_element
			self._mainview._elements_in_file = elements_in_file
			print(f'Seeded periodic table with {len(elements_in_file)} default isotopes')

		self._mainctrl._showPeriodicTable()

	def _normalizeIn(self):
		"""Automated 115In normalization for calibration.

		Uses the blank standard's average 115In intensity (over the entire
		acquisition) as the reference. For every other standard, loads the raw
		file, averages its 115In signal, and computes:

		    factor = ref_avg_In / std_avg_In

		Each element's stored peak area on that standard's row is multiplied by
		the factor so `Calculate Curve` uses the drift-corrected areas. The
		blank is left unchanged (it defines the reference). Results are shown
		in a popup.
		"""
		from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTableWidget, \
			QTableWidgetItem, QDialogButtonBox, QLabel
		from lcicpms.raw_icpms_data import RawICPMSData
		import numpy as np

		standards = self._calview.getStandardsData()
		if not standards:
			QMessageBox.warning(
				self._calview,
				'No Standards',
				'Add standards to the table before normalizing.',
				QMessageBox.StandardButton.Ok,
			)
			return

		cal_dir = self._calview.calibrationDir

		def _avg_indium(filename):
			"""Average 115In intensity across the whole trace of a standard file.

			Returns (avg, column_name) or (None, None) on any failure.
			"""
			path = os.path.join(cal_dir, filename)
			if not os.path.exists(path):
				print(f'  115In norm: file not found: {path}')
				return None, None
			try:
				raw = RawICPMSData(path)
				df = raw.raw_data_df
			except Exception as e:
				print(f'  115In norm: error reading {filename}: {e}')
				return None, None
			col = next(
				(c for c in df.columns if c.startswith('115In') and 'Time' not in c),
				None,
			)
			if col is None:
				return None, None
			values = df[col].dropna()
			if len(values) == 0:
				return None, col
			return float(np.mean(values)), col

		# Identify the blank row (concentration == 0 or name contains "blank")
		blank_idx = None
		for i, std in enumerate(standards):
			name = (std.get('name') or '').lower()
			if std.get('concentration') == 0 or 'blank' in name or 'blk' in name:
				blank_idx = i
				break

		if blank_idx is None:
			QMessageBox.warning(
				self._calview,
				'No Blank',
				'Cannot find a blank standard. Add a row named "Blank" '
				'(or with concentration 0) before running 115In normalization.',
				QMessageBox.StandardButton.Ok,
			)
			return

		blank_avg, blank_col = _avg_indium(standards[blank_idx]['filename'])
		if blank_avg is None or blank_avg <= 0:
			QMessageBox.warning(
				self._calview,
				'Blank 115In Missing',
				f"Could not read 115In from the blank file "
				f"'{standards[blank_idx]['filename']}'. "
				'Make sure 115In was recorded and the file is present.',
				QMessageBox.StandardButton.Ok,
			)
			return

		print(f"115In reference (blank): {blank_avg:.2f} (column: {blank_col})")

		results = []
		skipped = []
		for i, std in enumerate(standards):
			if i == blank_idx:
				results.append({
					'name': std['name'],
					'avg_in': blank_avg,
					'factor': 1.0,
					'raw': std['peak_areas'] or {},
					'normalized': std['peak_areas'] or {},
					'is_blank': True,
				})
				continue

			std_avg, _ = _avg_indium(std['filename'])
			if std_avg is None or std_avg <= 0:
				skipped.append(f"{std['name']} ({std['filename']}): no 115In signal")
				continue

			factor = blank_avg / std_avg
			raw_areas = std['peak_areas'] or {}
			normalized = {el: area * factor for el, area in raw_areas.items()}
			if normalized:
				self._calview.setStandardPeakArea(i, normalized)

			results.append({
				'name': std['name'],
				'avg_in': std_avg,
				'factor': factor,
				'raw': raw_areas,
				'normalized': normalized,
				'is_blank': False,
			})

		if len(results) <= 1:
			QMessageBox.warning(
				self._calview,
				'115In Normalization Failed',
				'No standards could be normalized. '
				+ ('\n\n' + '\n'.join(skipped) if skipped else ''),
				QMessageBox.StandardButton.Ok,
			)
			return

		# Stash on the model so the PDF report can include this section.
		self._model._in_norm_results = {
			'blank_name': standards[blank_idx]['name'],
			'blank_avg_in': blank_avg,
			'blank_col': blank_col,
			'results': results,
			'skipped': skipped,
		}

		# Build element column list (union across rows), stable order
		element_order = []
		for r in results:
			for el in r['raw']:
				if el not in element_order:
					element_order.append(el)

		dlg = QDialog(self._calview)
		dlg.setWindowTitle('115In Normalization Results')
		dlg.resize(760, 440)
		layout = QVBoxLayout(dlg)

		summary_lines = [
			f"Reference: blank '{standards[blank_idx]['name']}' avg 115In = {blank_avg:.2f} counts.",
			f"Normalized {sum(1 for r in results if not r['is_blank'])} standard(s); "
			f"factor = blank_avg / std_avg applied to each element's peak area.",
			'Blank areas are unchanged. Peak areas in the table have been updated — '
			'run Calculate Curve to use them.',
		]
		if skipped:
			summary_lines.append('Skipped: ' + '; '.join(skipped))
		layout.addWidget(QLabel('\n'.join(summary_lines)))

		table = QTableWidget()
		table.setColumnCount(3 + 2 * len(element_order))
		headers = ['Standard', 'Avg 115In', 'Factor']
		for el in element_order:
			headers.extend([f'{el} raw', f'{el} norm'])
		table.setHorizontalHeaderLabels(headers)
		table.setRowCount(len(results))
		table.setAlternatingRowColors(True)

		for r_idx, r in enumerate(results):
			label = r['name'] + (' (blank ref)' if r['is_blank'] else '')
			table.setItem(r_idx, 0, QTableWidgetItem(label))
			table.setItem(r_idx, 1, QTableWidgetItem(f"{r['avg_in']:.2f}"))
			table.setItem(r_idx, 2, QTableWidgetItem(f"{r['factor']:.4f}"))
			col = 3
			for el in element_order:
				raw_val = r['raw'].get(el)
				norm_val = r['normalized'].get(el)
				table.setItem(
					r_idx, col,
					QTableWidgetItem(f"{raw_val:.0f}" if raw_val is not None else '—'),
				)
				table.setItem(
					r_idx, col + 1,
					QTableWidgetItem(f"{norm_val:.0f}" if norm_val is not None else '—'),
				)
				col += 2

		table.resizeColumnsToContents()
		layout.addWidget(table)

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		buttons.accepted.connect(dlg.accept)
		layout.addWidget(buttons)
		dlg.exec()

	def _connectSignals(self):
		"""Connect signals and slots."""
		print("Connecting calibration signals...")

		# Directory and file selection
		self._calview.buttons['Directory'].clicked.connect(self._selectDirectory)
		self._calview.buttons['Select Elements'].clicked.connect(self._openPeriodicTable)
		self._calview.buttons['Sort By Name'].clicked.connect(self._sortListByName)
		self._calview.buttons['Sort By Number'].clicked.connect(self._sortListByNumber)
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
		self._calview.integrateButtons['Suggest Range'].clicked.connect(self._suggestRange)
		self._calview.integrateButtons['Reset Integration'].clicked.connect(self._resetIntegration)
		self._calview.integrateButtons['Calculate Curve'].clicked.connect(self._calcCurve)
		self._calview.integrateButtons['Normalize In'].clicked.connect(self._normalizeIn)
		print("  - Action button signals connected")

		print("All calibration signals connected")
