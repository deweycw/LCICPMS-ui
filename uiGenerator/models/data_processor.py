from curses import meta
import time
from datetime import datetime
from datetime import timedelta
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
import numpy as np
import seaborn as sns
import csv
from lcicpms.raw_icpms_data import RawICPMSData
from lcicpms.integrate import Integrate
from ..plotting.static import ICPMS_Data_Class
from ..plotting.interactive import plotChroma

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


class LICPMSfunctions:
	''' model class for LCICPMS functions'''

	def __init__(self, view):
		"""Controller initializer."""
		self._view = view
		self.intColors = sns.color_palette(n_colors=6)  # Returns list of RGB tuples
		self.minline = None
		self.maxline = None
		self.region = None
		
	def importData(self):
		'''imports LCICPMS .csv file using lcicpms.RawICPMSData'''
		print(self._view.listwidget.currentItem().text())
		if self._view.listwidget.currentItem() is not None:
			self.fdir = self._view.homeDir + self._view.listwidget.currentItem().text()
			try:
				# Use lcicpms RawICPMSData for intelligent CSV parsing
				raw_data = RawICPMSData(self.fdir)
				self._data = raw_data.raw_data_df
				self._raw_icpms = raw_data  # Store for later use

				# Populate _elements_in_file from RawICPMSData (these are full analyte names)
				self._view._elements_in_file = raw_data.elements.copy()

				# Build mapping from element symbols to available analytes
				# This handles both simple isotopes (e.g., "56Fe") and TQ mode analytes (e.g., "32S | 32S.16O")
				self._view._analytes_by_element = {}
				for analyte in raw_data.elements:
					# Extract the isotope from the analyte name
					# Format can be: "56Fe" or "32S | 32S.16O" or "238U | 238U.16O2"
					isotope = analyte.split(' | ')[0] if ' | ' in analyte else analyte

					# Extract element symbol from isotope (e.g., "Fe" from "56Fe")
					import re
					match = re.search(r'(\d+)([A-Z][a-z]?)', isotope)
					if match:
						element_symbol = match.group(2)
						if element_symbol not in self._view._analytes_by_element:
							self._view._analytes_by_element[element_symbol] = []
						self._view._analytes_by_element[element_symbol].append(analyte)

				# Remove any activeElements that are not in the new file
				self._view.activeElements = [elem for elem in self._view.activeElements
				                              if elem in self._view._elements_in_file]
			except FileNotFoundError:
				print(f'Error: File not found: {self.fdir}')
				raise
			except pd.errors.ParserError as e:
				print(f'Error parsing CSV file {self.fdir}: {e}')
				raise
			except Exception as e:
				print(f'Error reading file {self.fdir}: {e}')
				raise

	def importData_generic(self,fdir):
		'''imports LCICPMS .csv file using lcicpms.RawICPMSData'''
		try:
			raw_data = RawICPMSData(fdir)
			return raw_data.raw_data_df
		except FileNotFoundError:
			print(f'Error: File not found: {fdir}')
			raise
		except pd.errors.ParserError as e:
			print(f'Error parsing CSV file {fdir}: {e}')
			raise
		except Exception as e:
			print(f'Error reading file {fdir}: {e}')
			raise 

	def plotActiveElementsMP(self):
		'''plots active elements for selected file'''
		activeElementsPlot = ICPMS_Data_Class(self._data,self._view.activeElements)
		activeElementsPlot.chroma().show()
	
	def plotActiveElements(self):
		'''plots active elements for selected file'''
		# Pass comparison data if in compare mode (now supports multiple files)
		compare_data_list = self._view.comparisonData if self._view.compareMode else None
		compare_files_list = self._view.comparisonFiles if self._view.compareMode else None
		compare_labels = self._view.comparisonLabels if self._view.compareMode else None

		self._view.chroma = plotChroma(
			self._view,
			self._view.elementOptions,
			self._data,
			self._view.activeElements,
			compare_data=compare_data_list,
			compare_files=compare_files_list,
			compare_labels=compare_labels
		)._plotChroma()

		if self.minline != None:
			self._view.plotSpace.addItem(self.minline)
		if self.maxline != None:
			self._view.plotSpace.addItem(self.maxline)

	def integrate(self, intRange, has_calibration=True, data=None, filename=None):
		'''integrates over specified x range

		Args:
			intRange: tuple of (start_time, end_time) in minutes
			has_calibration: whether calibration curves are available
			data: optional dataframe to integrate (for comparison mode)
			filename: optional filename for the data (for comparison mode)

		Returns:
			dict:
				'results':     {element: {'peak_area', 'conc_ppb', 'conc_uM'}}
				'peakAreas':   flat dict for CSV export (peak areas per element)
				'elementConcs':      flat dict for CSV export (uM concentrations)
				'elementConcs_ppb':  flat dict for CSV export (ppb concentrations)
				'corr_factor': 115In correction factor applied
				'filename':    basename of the file that was integrated
				'timestamp':   human-readable timestamp
				'has_calibration': whether calibration was available
				'range': (start_min, stop_min)

		This method no longer writes any CSV files. Persistence is done via
		saveIntegration() when the user explicitly saves.
		'''
		self.intRange = intRange

		# Use provided data or default to loaded data
		integrate_data = data if data is not None else self._data

		# Seed the output dicts from the elements that will actually be
		# integrated (activeElements minus 115In). No hardcoded element list —
		# so 238U, TQ-mode analytes, etc. all end up in the CSV. No timestamp
		# column either (per user request; the save filename carries the date).
		integrated_elements = [
			el for el in self._view.activeElements
			if not el.startswith('115In')
		]
		element_dict = {key: None for key in integrated_elements}
		meta = {'start_time': 0, 'stop_time': 0, 'correction': None}
		elementConcs = {**meta, **element_dict}      # uM concentrations
		elementConcs_ppb = {**meta, **element_dict}  # ppb concentrations
		peakAreas = {**meta, **element_dict}
		# Per-element baseline area subtracted (counts·s); None when disabled.
		baselineAreas = {**meta, **element_dict}

		# Results to return for display
		results = {}

		if self._view.normAvIndium > 0:
			# Find indium column (handles both '115In' and '115In | 115In' formats)
			indium_col = None
			for col in integrate_data.columns:
				if col.startswith('115In') and 'Time' not in col:
					indium_col = col
					break

			if indium_col:
				indium_col_ind = integrate_data.columns.get_loc(indium_col)
				time_col = 'Time ' + indium_col
				if len(integrate_data[time_col]) > 2000:
					corr_factor = np.average(integrate_data.iloc[550:2500,indium_col_ind]) / self._view.normAvIndium
				else:
					corr_factor = np.average(integrate_data.iloc[:,indium_col_ind]) / self._view.normAvIndium
				print('\ncorrection factor: %.4f' % corr_factor)
			else:
				print('\nWarning: 115In not found in file, no correction applied')
				corr_factor = 1
		else:
			corr_factor = 1

		for element in self._view.activeElements:
			# Skip indium (handles both '115In' and '115In | 115In' formats)
			if not element.startswith('115In'):
				# Get time and intensity arrays (time in seconds, convert to minutes for range)
				time_seconds = integrate_data['Time ' + element].values
				time_minutes = time_seconds / 60
				intensity = integrate_data[element].values / corr_factor  # Apply correction factor

				# Set up time range for integration (convert minutes to seconds for lcicpms)
				range_min = self.intRange[0]  # minutes
				range_max = self.intRange[1]  # minutes
				time_range_seconds = (range_min * 60, range_max * 60)  # convert to seconds

				# Store metadata
				elementConcs['start_time'] = '%.2f' % range_min
				elementConcs['stop_time'] = '%.2f' % range_max
				elementConcs_ppb['start_time'] = '%.2f' % range_min
				elementConcs_ppb['stop_time'] = '%.2f' % range_max
				peakAreas['start_time'] = '%.2f' % range_min
				peakAreas['stop_time'] = '%.2f' % range_max
				elementConcs['correction'] = '%.3f' % corr_factor
				elementConcs_ppb['correction'] = '%.3f' % corr_factor
				peakAreas['correction'] = '%.3f' % corr_factor

				# Use lcicpms Integrate.integrate() for peak area calculation
				summed_area = Integrate.integrate(intensity, time_seconds, time_range=time_range_seconds)

				# Baseline subtraction (if enabled).
				# summed_area comes out in counts·seconds because Integrate.integrate
				# is called with `time_seconds`, so the trapezoidal baseline area we
				# subtract must also be in counts·seconds — previously it was
				# divided by 60 (counts·minutes), so it was 60× too small and had
				# essentially no effect.
				baseline_area = None
				if self._view.baseSubtract == True:
					# Find the sample indices closest to the selected range endpoints
					min_delta = min(abs(time_minutes - range_min))
					max_delta = min(abs(time_minutes - range_max))
					i_tmin = int(np.where(abs(time_minutes - range_min) == min_delta)[0][0])
					i_tmax = int(np.where(abs(time_minutes - range_max) == max_delta)[0][0])

					h1 = intensity[i_tmin]
					h2 = intensity[i_tmax]
					dt_seconds = time_seconds[i_tmax] - time_seconds[i_tmin]

					# Trapezoidal area under the straight line between (t_min, h1)
					# and (t_max, h2), in counts·seconds — matches summed_area units.
					baseline_area = 0.5 * (h1 + h2) * dt_seconds

					summed_area = max(summed_area - baseline_area, 0)
				# Record the baseline (or None if not used) so it flows into
				# both the popup and the saved CSV.
				baselineAreas[element] = (
					'%.1f' % baseline_area if baseline_area is not None else None
				)
					

				peakAreas[element] = '%.1f' % summed_area

				# Only calculate concentrations if calibration is loaded
				# Try exact match first, then try base isotope (handles "56Fe | 56Fe.16O" format)
				cal_element = None
				if has_calibration:
					if element in self._view.calCurves:
						cal_element = element
					else:
						# Try base isotope (before " | ")
						base_isotope = element.split(' | ')[0].strip() if ' | ' in element else element
						if base_isotope in self._view.calCurves:
							cal_element = base_isotope
							print(f'  Using calibration for {base_isotope} (matched from {element})')

				if cal_element is not None:
					cal_curve = self._view.calCurves[cal_element]
					slope = cal_curve['m']
					intercept = cal_curve['b']
					conc_ppb = slope * summed_area + intercept

					# Extract base isotope from element name (handle "238U | 238U.16O2" format)
					base_isotope = element.split(' | ')[0].strip() if ' | ' in element else element
					# Look up mass - try exact match first, then base isotope
					if element in self._view.masses:
						mass = self._view.masses[element]
					elif base_isotope in self._view.masses:
						mass = self._view.masses[base_isotope]
					else:
						# Try to extract mass number from isotope name (e.g., "238U" -> 238)
						import re
						match = re.match(r'(\d+)', base_isotope)
						mass = int(match.group(1)) if match else 1
						print(f"Warning: Mass not found for {element}, using {mass}")

					conc_uM = conc_ppb / mass

					elementConcs[element] = '%.3f' % conc_uM
					elementConcs_ppb[element] = '%.3f' % conc_ppb

					# Store results for display
					results[element] = {
						'peak_area': summed_area,
						'conc_ppb': conc_ppb,
						'conc_uM': conc_uM,
						'baseline_area': baseline_area,
					}

					print(f'\n{element}:')
					print(f'  Peak area: {summed_area:.2e} counts')
					print(f'  Concentration: {conc_ppb:.3f} ppb | {conc_uM:.3f} uM')
				else:
					# No calibration match - just report peak area in scientific notation
					# Store results for display (peak area only)
					results[element] = {
						'peak_area': summed_area,
						'conc_ppb': None,
						'conc_uM': None,
						'baseline_area': baseline_area,
					}

					print(f'\n{element}:')
					print(f'  Peak area: {summed_area:.2e} counts')
					if not has_calibration:
						print(f'  (No calibration loaded - concentrations not calculated)')
					else:
						base_isotope = element.split(' | ')[0].strip() if ' | ' in element else element
						print(f'  (No calibration found for {element} or {base_isotope} - concentrations not calculated)')

		# Resolve the filename we integrated: prefer explicit arg (comparison
		# mode), otherwise use the currently-loaded file's basename.
		if filename:
			base_name = os.path.basename(filename).split(',')[0]
		elif hasattr(self, 'fdir') and self.fdir:
			base_name = os.path.basename(self.fdir).split(',')[0]
		else:
			base_name = 'unknown.csv'

		return {
			'results': results,
			'peakAreas': peakAreas,
			'elementConcs': elementConcs,
			'elementConcs_ppb': elementConcs_ppb,
			'baselineAreas': baselineAreas,
			'baseline_applied': bool(self._view.baseSubtract),
			'corr_factor': corr_factor,
			'filename': base_name,
			'timestamp': datetime.now().strftime("%d-%b-%Y (%H:%M:%S)"),
			'has_calibration': has_calibration,
			'range': (self.intRange[0], self.intRange[1]),
		}

	def saveIntegration(self, records, output_path):
		'''Write accumulated integration records to a single wide CSV that
		mirrors the multi-file results popup: one row per file, grouped
		columns per element (Peak area / ppb / µM if calibrated). Metadata
		columns (range, 115In correction) are also included.

		Args:
			records:     list of dicts produced by integrate()
			output_path: full path of the CSV to write

		Returns:
			list of paths written (single entry).
		'''
		if not records:
			return []

		out_dir = os.path.dirname(output_path)
		if out_dir:
			os.makedirs(out_dir, exist_ok=True)

		# Union of integrated elements across records, preserving first-seen
		# order. 115In is already excluded upstream.
		META_COLS = {'start_time', 'stop_time', 'correction'}
		element_order = []
		for rec in records:
			for k in rec['peakAreas']:
				if k not in META_COLS and k not in element_order:
					element_order.append(k)

		has_any_cal = any(r.get('has_calibration') for r in records)
		# Include a baseline column per element whenever any record used it,
		# so the user can see what was subtracted.
		has_any_baseline = any(r.get('baseline_applied') for r in records)

		# Header row: 'File', metadata, then per-element groups.
		sub_headers = ['peak_area']
		if has_any_baseline:
			sub_headers.append('baseline')
		if has_any_cal:
			sub_headers.extend(['ppb', 'uM'])

		header = ['file', 'start_min', 'stop_min', '115In_correction']
		if has_any_baseline:
			header.append('baseline_subtracted')
		for el in element_order:
			for sub in sub_headers:
				header.append(f'{el}_{sub}')

		with open(output_path, 'w', newline='') as csvfile:
			fwriter = csv.writer(csvfile)
			fwriter.writerow(header)
			for rec in records:
				start = rec['peakAreas'].get('start_time', '')
				stop = rec['peakAreas'].get('stop_time', '')
				corr = rec.get('corr_factor', 1)
				row = [rec['filename'], start, stop, f'{corr:.3f}']
				if has_any_baseline:
					row.append('yes' if rec.get('baseline_applied') else 'no')
				pa = rec['peakAreas']
				ec_uM = rec.get('elementConcs') or {}
				ec_ppb = rec.get('elementConcs_ppb') or {}
				baselines = rec.get('baselineAreas') or {}
				has_cal = rec.get('has_calibration', False)
				for el in element_order:
					row.append(pa.get(el, ''))
					if has_any_baseline:
						row.append(baselines.get(el, ''))
					if has_any_cal:
						row.append(ec_ppb.get(el, '') if has_cal else '')
						row.append(ec_uM.get(el, '') if has_cal else '')
				fwriter.writerow(row)

		return [output_path]

	def plotLowRange(self, xmin, n):
		'''plots integration range'''
		col = self.intColors[n % len(self.intColors)]
		# Convert to RGB 0-255 for pyqtgraph
		r, g, b = int(col[0]*255), int(col[1]*255), int(col[2]*255)
		pen = pg.mkPen(color=(r, g, b), width=2)
		self.minline = pg.InfiniteLine(xmin, pen=pen, angle=90)
		self._view.plotSpace.addItem(self.minline)

	def plotHighRange(self, xmax, n):
		col = self.intColors[n % len(self.intColors)]
		# Convert to RGB 0-255 for pyqtgraph
		r, g, b = int(col[0]*255), int(col[1]*255), int(col[2]*255)
		pen = pg.mkPen(color=(r, g, b), width=2)
		self.maxline = pg.InfiniteLine(xmax, pen=pen, angle=90)
		self._view.plotSpace.addItem(self.maxline)

		# Add shaded region between min and max lines
		if self.minline is not None:
			xmin = self.minline.value()
			# Create LinearRegionItem with semi-transparent fill
			self.region = pg.LinearRegionItem(
				values=(xmin, xmax),
				orientation='vertical',
				brush=pg.mkBrush(r, g, b, 50),  # Semi-transparent
				pen=pg.mkPen(None),  # No border lines (we already have the InfiniteLines)
				movable=False  # Make it non-movable
			)
			self._view.plotSpace.addItem(self.region)

	def removeIntRange(self):
		if self.maxline is not None:
			self._view.plotSpace.removeItem(self.maxline)
		if self.minline is not None:
			self._view.plotSpace.removeItem(self.minline)
		if self.region is not None:
			self._view.plotSpace.removeItem(self.region)


