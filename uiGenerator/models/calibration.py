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
from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
import json
import matplotlib.pyplot as plt
from lcicpms.raw_icpms_data import RawICPMSData
from lcicpms.integrate import Integrate
from ..plotting.static import ICPMS_Data_Class
from ..plotting.interactive import plotChroma
import csv

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
runs calibration

2022-04-26
Christian Dewey
'''

class CalibrateFunctions:
	''' class for calibration functions'''

	def __init__(self, calview, mainview):
		"""Controller initializer."""
		self._calview = calview
		self._mainview = mainview
		self.ntime = True
		self.intColors = sns.color_palette(n_colors=6)  # Returns list of RGB tuples
		# 115In normalization details, populated by the calibration controller
		# after the user runs "Normalize to 115In". Consumed by
		# calcLinearRegression to include a section in the PDF report.
		self._in_norm_results = None
		
	def importData(self):
		'''imports cal .csv file using lcicpms.RawICPMSData'''
		print("importData called")

		# Build file path - ensure proper path joining
		cal_dir = self._calview.calibrationDir
		print(f"  Calibration dir: '{cal_dir}'")

		if self._calview.listwidget.currentItem() is None:
			print("  ERROR: No file selected in listwidget")
			return

		filename = self._calview.listwidget.currentItem().text()
		print(f"  Filename: '{filename}'")

		fdir = os.path.join(cal_dir, filename)
		print(f"  Full path: '{fdir}'")

		if not os.path.exists(fdir):
			print(f"  ERROR: File does not exist: {fdir}")
			self._data = None
			return

		try:
			raw_data = RawICPMSData(fdir)
			self._data = raw_data.raw_data_df
			print(f"  Data loaded: {self._data.shape[0]} rows, {self._data.shape[1]} columns")

			all_elements = raw_data.elements.copy()

			# Sync the periodic-table view state with what the newly loaded
			# file actually contains, so the PT reflects the file next time
			# the user opens it (mirrors uiGenerator/models/data_processor.py).
			import re
			self._mainview._elements_in_file = all_elements
			analytes_by_element = {}
			for analyte in all_elements:
				isotope = analyte.split(' | ')[0] if ' | ' in analyte else analyte
				match = re.search(r'(\d+)([A-Z][a-z]?)', isotope)
				if not match:
					continue
				symbol = match.group(2)
				analytes_by_element.setdefault(symbol, []).append(analyte)
			self._mainview._analytes_by_element = analytes_by_element

			# Drop any active elements that don't exist in the new file.
			self._mainview.activeElements = [
				el for el in self._mainview.activeElements if el in all_elements
			]

			# If the selection is now empty (either never set, or none of the
			# previously selected isotopes are in this file), plot everything
			# so the user sees the chromatogram instead of a blank plot.
			selected_elements = self._mainview.activeElements or all_elements
			self._calview.elements_in_stdfile = [
				el for el in all_elements if el in selected_elements
			]

			print(f"  Elements in file: {all_elements}")
			print(f"  Elements selected for calibration: {selected_elements}")
			print(f"  Elements to use: {self._calview.elements_in_stdfile}")

		except Exception as e:
			print(f"  ERROR loading file: {e}")
			import traceback
			traceback.print_exc()
			self._data = None
			self._calview.elements_in_stdfile = []

	def suggestIntegrationRange(self):
		"""Suggest an integration range that spans the dominant peak feature.

		For each active element, finds the max signal, estimates a baseline from
		the first and last 10% of the trace, and walks outward from the peak until
		the signal drops to baseline + 5% of the peak-above-baseline height. The
		returned range is the union of per-element bounds (with a small padding),
		so it spans the feature across all elements.

		Returns: (start_time_min, end_time_min) or None if no data.
		"""
		if self._data is None or not self._calview.elements_in_stdfile:
			return None

		try:
			elements = self._calview.elements_in_stdfile
			# Ignore 115In (internal standard) when detecting the analyte peak.
			# Handles both '115In' and TQ-mode variants like '115In | 115In.16O'.
			analyte_elements = [e for e in elements if not e.startswith('115In')] or elements

			starts = []
			ends = []
			fallback_time = None

			for element in analyte_elements:
				time_seconds = self._data['Time ' + element].values
				intensity = self._data[element].values
				time_minutes = time_seconds / 60
				n = len(time_minutes)
				if fallback_time is None:
					fallback_time = time_minutes
				if n < 5:
					continue

				edge = max(1, n // 10)
				baseline = float(np.median(
					np.concatenate([intensity[:edge], intensity[-edge:]])
				))
				peak_idx = int(np.argmax(intensity))
				peak_val = float(intensity[peak_idx])
				height = peak_val - baseline
				if height <= 0:
					continue
				# Skip weak/noisy traces: peak should be well above baseline
				if peak_val < baseline * 1.5 and height < 3 * float(np.std(intensity[:edge])):
					continue

				threshold = baseline + 0.05 * height

				left = peak_idx
				while left > 0 and intensity[left] > threshold:
					left -= 1
				right = peak_idx
				while right < n - 1 and intensity[right] > threshold:
					right += 1

				starts.append(time_minutes[left])
				ends.append(time_minutes[right])

			if not starts:
				# No clear peak — fall back to a conservative interior range
				if fallback_time is None or len(fallback_time) < 3:
					return None
				return (float(fallback_time[0]), float(fallback_time[-2]))

			start_time = min(starts)
			end_time = max(ends)

			# Add small padding (5% of span) but stay within the trace
			pad = 0.05 * max(end_time - start_time, 0.05)
			t_min = float(fallback_time[0])
			t_max = float(fallback_time[-1])
			start_time = max(t_min, start_time - pad)
			end_time = min(t_max, end_time + pad)

			print(f"  Suggested integration range: {start_time:.2f} - {end_time:.2f} min")
			return (float(start_time), float(end_time))

		except Exception as e:
			print(f"  Error getting integration range: {e}")
			return None

	def plotActiveElements(self):
		'''plots active elements for selected file'''
		print("plotActiveElements called")

		if self._data is None:
			print("  ERROR: No data to plot (_data is None)")
			return

		if not self._calview.elements_in_stdfile:
			print("  ERROR: No elements to plot (elements_in_stdfile is empty)")
			return

		print(f"  Elements to plot: {self._calview.elements_in_stdfile}")
		print(f"  Data shape: {self._data.shape}")
		print(f"  Data columns: {list(self._data.columns)[:5]}...")  # First 5 columns

		try:
			self._calview.chroma = plotChroma(
				self._calview,
				self._calview.elements_in_stdfile,
				self._data,
				self._calview.elements_in_stdfile
			)._plotChroma()
			print("  Plot created successfully")
		except Exception as e:
			print(f"  ERROR in plotChroma: {e}")
			import traceback
			traceback.print_exc()

	def integrate(self, intRange):
		'''integrates over specified x range using lcicpms.Integrate'''
		self.intRange = intRange
		pa_dict = {}
		for element in self._calview.elements_in_stdfile:
			# Get time and intensity arrays
			time_seconds = self._data['Time ' + element].values
			intensity = self._data[element].values

			# Set up time range (convert minutes to seconds for lcicpms)
			range_min = self.intRange[0]  # minutes
			range_max = self.intRange[1]  # minutes
			time_range_seconds = (range_min * 60, range_max * 60)

			# Use lcicpms Integrate.integrate() for peak area calculation
			summed_area = Integrate.integrate(intensity, time_seconds, time_range=time_range_seconds)
			print(element + ': ' + str(summed_area))

			pa_dict[element] = summed_area

			self._calview.n_area = pa_dict

		filename = os.path.join(self._calview.calibrationDir, 'calibration_areas.txt')
		with open(filename, 'a', newline='') as csvfile:
			fwriter = csv.DictWriter(csvfile, fieldnames=pa_dict.keys())
			if self.ntime == True:
				fwriter.writeheader()
				self.ntime = False
			fwriter.writerow(pa_dict) 

	def plotLowRange(self, xmin, n):
		'''plots integration range'''
		col = self.intColors[n % len(self.intColors)]
		# Convert to RGB 0-255 for pyqtgraph
		r, g, b = int(col[0]*255), int(col[1]*255), int(col[2]*255)
		pen = pg.mkPen(color=(r, g, b), width=2)
		minline = pg.InfiniteLine(xmin, pen=pen, angle=90)
		self._calview.plotSpace.addItem(minline)

	def plotHighRange(self, xmax, n):
		col = self.intColors[n % len(self.intColors)]
		# Convert to RGB 0-255 for pyqtgraph
		r, g, b = int(col[0]*255), int(col[1]*255), int(col[2]*255)
		pen = pg.mkPen(color=(r, g, b), width=2)
		maxline = pg.InfiniteLine(xmax, pen=pen, angle=90)
		self._calview.plotSpace.addItem(maxline)

	def calcLinearRegression(self, standards_data):
		"""Calculate linear regression calibration curves from standards data.

		Args:
			standards_data: List of dicts with keys:
				- 'filename': source file name
				- 'name': standard name (e.g., 'Blank', 'Std 1')
				- 'concentration': concentration in ppb
				- 'peak_areas': dict mapping element to peak area

		Writes a single multi-page PDF report containing a summary table and
		one calibration plot per element (115In is skipped — it's the internal
		standard and no cal curve is needed for it).
		"""
		from matplotlib.backends.backend_pdf import PdfPages
		from datetime import datetime

		saveDict = {}
		archived_calibs = []
		skipped_elements = []  # (element, reason) tuples
		pdf_path_out = None
		# Exclude 115In and any TQ-mode variant ('115In | ...') — internal standard, no cal curve needed.
		elements = [e for e in self._calview.elements_in_stdfile if not e.startswith('115In')]

		# Find blank if present (concentration = 0 or name contains 'blank')
		blank_dict = {}
		blank_name = None
		for std in standards_data:
			if std['concentration'] == 0 or 'blank' in std['name'].lower():
				blank_dict = std['peak_areas'] or {}
				blank_name = std['name']
				print(f"Found blank: {std['name']}")
				break

		fit_rows = []  # (element, slope, r2, mse, n_points, X, y, y_pred, blank_value)
		for m in elements:
			pas = []
			concs = []

			blank_value = blank_dict.get(m, 0) if blank_dict else 0
			if blank_value:
				print(f'Blank PA for {m} = {blank_value:.2f}')

			for std in standards_data:
				if std['peak_areas'] is None or m not in std['peak_areas']:
					continue
				peak_area = std['peak_areas'][m] - blank_value
				concentration = std['concentration']
				if concentration > 0:
					pas.append(peak_area)
					concs.append(concentration)

			if len(pas) < 2:
				reason = f'only {len(pas)} standard(s) with peak areas'
				print(f"Skipping {m}: insufficient data points ({len(pas)})")
				skipped_elements.append((m, reason))
				continue

			X = np.array(pas).reshape(-1, 1)
			y = np.array(concs)
			regr = linear_model.LinearRegression(fit_intercept=False)
			regr.fit(X, y)
			y_pred = regr.predict(X)
			mse = mean_squared_error(y, y_pred)
			r2 = r2_score(y, y_pred)

			print(f"{m}: slope={regr.coef_[0]:.4e}, r2={r2:.4f}, mse={mse:.2f}")

			saveDict[m] = {'m': regr.coef_[0], 'b': regr.intercept_, 'r2': r2, 'mse': mse}
			fit_rows.append((m, regr.coef_[0], r2, mse, len(pas), X, y, y_pred, blank_value))

		self._mainview.calCurves = saveDict

		# One-shot consume the normalization results so a subsequent
		# calculation doesn't re-print stale ones.
		in_norm = self._in_norm_results
		self._in_norm_results = None

		# Build the PDF report ------------------------------------------------
		if fit_rows:
			from ..utils.analyte_formatter import format_analyte_latex
			timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
			pdf_path = os.path.join(
				self._calview.calibrationDir, f'calibration_report_{timestamp}.pdf'
			)
			pdf_path_out = pdf_path

			PAGE_W, PAGE_H = 8.5, 11  # portrait letter
			HEADER_COLOR = '#4682b4'
			ROW_ALT = '#f2f6fa'
			TITLE_FS = 22
			BODY_FS = 11  # everything except the title uses this size

			def _pretty(analyte):
				"""LaTeX-formatted isotope label, robust to ' | ' separators."""
				return format_analyte_latex(analyte.replace(' ', ''))

			def _style_table(tbl, n_rows, n_cols):
				tbl.auto_set_font_size(False)
				tbl.set_fontsize(BODY_FS)
				# Vertical scale gives cells breathing room so wrapped headers
				# and body text don't collide with borders.
				tbl.scale(1, 2.0)
				# Header row
				for c in range(n_cols):
					cell = tbl[0, c]
					cell.set_facecolor(HEADER_COLOR)
					cell.set_text_props(color='white', fontweight='bold')
					cell.set_edgecolor('white')
				# Body rows
				for r in range(1, n_rows + 1):
					bg = ROW_ALT if r % 2 == 0 else 'white'
					for c in range(n_cols):
						cell = tbl[r, c]
						cell.set_facecolor(bg)
						cell.set_edgecolor('#d0d0d0')

			# Left-aligned layout: everything hangs off a single left margin at
			# x = LEFT. No centered text, no centered tables. Body text is a
			# single font size (BODY_FS); only the title is larger.
			LEFT = 0.08
			RIGHT = 0.94
			WIDTH = RIGHT - LEFT

			with PdfPages(pdf_path) as pdf:
				# ---- Page 1: header + summary table ----------------------
				fig = plt.figure(figsize=(PAGE_W, PAGE_H))
				fig.text(
					LEFT, 0.955, 'LC-ICP-MS Calibration Report',
					ha='left', va='top', fontsize=TITLE_FS, fontweight='bold',
				)
				meta_lines = [
					f"Generated:            {datetime.now().strftime('%Y-%m-%d %H:%M')}",
					f"Standards used:       {len(standards_data)}",
					f"Elements fitted:      {len(fit_rows)}   (115In excluded)",
				]
				if blank_name:
					meta_lines.append(f"Blank reference:      {blank_name}")
				meta_lines.append(
					f"115In normalization:  {'applied' if in_norm else 'not applied'}"
				)
				fig.text(
					LEFT, 0.885, '\n'.join(meta_lines),
					ha='left', va='top', fontsize=BODY_FS, family='monospace',
					linespacing=1.5,
				)

				# Section heading above the table (same body font size,
				# just bold — no larger font size).
				fig.text(
					LEFT, 0.720,
					'Calibration curves (linear, zero intercept)',
					ha='left', va='top', fontsize=BODY_FS, fontweight='bold',
				)

				# Table area — plenty of space, well below the heading.
				ax = fig.add_axes([LEFT, 0.10, WIDTH, 0.58])
				ax.axis('off')

				# Plain-ASCII headers so all fonts render cleanly.
				col_labels = ['Element', 'Slope', 'R2', 'MSE', 'N', 'Blank PA']
				# Widths sum ≤ 1.0, giving each header room to fit its label.
				col_widths = [0.20, 0.24, 0.12, 0.14, 0.10, 0.18]

				cell_text = []
				for (m, slope, r2, mse, n, _, _, _, blank_v) in fit_rows:
					cell_text.append([
						_pretty(m),
						f'{slope:.3e}',
						f'{r2:.4f}',
						f'{mse:.2f}',
						f'{n}',
						f'{blank_v:.0f}' if blank_v else '—',
					])

				tbl = ax.table(
					cellText=cell_text,
					colLabels=col_labels,
					colWidths=col_widths,
					loc='upper left',
					cellLoc='left',
					colLoc='left',
				)
				_style_table(tbl, len(cell_text), len(col_labels))

				# Small footnote so 'Slope' units aren't ambiguous.
				fig.text(
					LEFT, 0.07,
					'Slope units: ppb / count.  N = number of non-blank '
					'standards used in the fit.',
					ha='left', va='top', fontsize=BODY_FS, style='italic',
					color='#555',
				)
				pdf.savefig(fig)
				plt.close(fig)

				# ---- Optional page: 115In normalization details ----------
				if in_norm:
					fig = plt.figure(figsize=(PAGE_W, PAGE_H))
					fig.text(
						LEFT, 0.955, '115In Normalization',
						ha='left', va='top', fontsize=TITLE_FS, fontweight='bold',
					)
					blurb = (
						f"Reference:     blank '{in_norm['blank_name']}'\n"
						f"Avg 115In:     {in_norm['blank_avg_in']:.1f} counts\n"
						"Each standard's peak areas were scaled by "
						"(blank_avg / std_avg) before fitting."
					)
					fig.text(
						LEFT, 0.885, blurb, ha='left', va='top',
						fontsize=BODY_FS, family='monospace', linespacing=1.5,
					)
					next_y = 0.760
					if in_norm.get('skipped'):
						fig.text(
							LEFT, 0.780,
							'Skipped: ' + '; '.join(in_norm['skipped']),
							ha='left', va='top', fontsize=BODY_FS,
							color='#a04040',
						)
						next_y = 0.730

					fig.text(
						LEFT, next_y, 'Correction factors',
						ha='left', va='top', fontsize=BODY_FS, fontweight='bold',
					)
					ax = fig.add_axes([LEFT, 0.08, WIDTH, next_y - 0.10])
					ax.axis('off')

					norm_rows = []
					for r in in_norm['results']:
						label = r['name'] + (' (ref)' if r['is_blank'] else '')
						norm_rows.append([
							label,
							f"{r['avg_in']:.1f}",
							f"{r['factor']:.4f}",
						])
					tbl = ax.table(
						cellText=norm_rows,
						colLabels=['Standard', 'Avg 115In (counts)',
						           'Correction factor'],
						colWidths=[0.44, 0.28, 0.24],
						loc='upper left',
						cellLoc='left',
						colLoc='left',
					)
					_style_table(tbl, len(norm_rows), 3)
					pdf.savefig(fig)
					plt.close(fig)

				# ---- One calibration plot per element (portrait) ---------
				for (m, slope, r2, mse, n, X, y, y_pred, blank_v) in fit_rows:
					fig = plt.figure(figsize=(PAGE_W, PAGE_H))
					fig.text(
						LEFT, 0.955, _pretty(m),
						ha='left', va='top', fontsize=TITLE_FS, fontweight='bold',
					)
					fig.text(
						LEFT, 0.895, 'Calibration curve',
						ha='left', va='top', fontsize=BODY_FS, color='#555',
					)

					# Plot in the upper portion, well clear of the header and
					# the stats block below. Leave enough room under the ax
					# for the xlabel and tick labels before the stats heading.
					ax = fig.add_axes([LEFT, 0.50, WIDTH, 0.34])
					Xk = (X / 1000).ravel()
					x_line = np.linspace(0, Xk.max() * 1.05, 100)
					y_line = slope * (x_line * 1000)
					ax.plot(
						x_line, y_line, color=HEADER_COLOR, linewidth=2.5,
						label='Linear fit  (y = m·x)', zorder=2,
					)
					ax.scatter(
						Xk, y, s=90, facecolor='white', edgecolor='black',
						linewidth=1.5, zorder=3, label='Standards',
					)
					ax.set_xlabel(
						r'Peak Area  ($10^{3}$ ICP-MS counts)',
						fontsize=BODY_FS,
					)
					ax.set_ylabel('Concentration  (ppb)', fontsize=BODY_FS)
					ax.set_xlim(left=0, right=Xk.max() * 1.08)
					ax.set_ylim(bottom=0, top=max(y) * 1.15)
					ax.grid(True, linestyle='--', alpha=0.4)
					ax.tick_params(axis='both', which='major', labelsize=BODY_FS)
					for spine in ('top', 'right'):
						ax.spines[spine].set_visible(False)
					ax.legend(loc='upper left', frameon=True, fontsize=BODY_FS)

					# Stats heading + block, both same body font size.
					fig.text(
						LEFT, 0.40, 'Fit statistics',
						ha='left', va='top', fontsize=BODY_FS, fontweight='bold',
					)
					stats = [
						f'Slope         =  {slope:.4e}  ppb / count',
						f'R2            =  {r2:.4f}',
						f'MSE           =  {mse:.2f}',
						f'N             =  {n}',
					]
					if blank_v:
						stats.append(f'Blank PA      =  {blank_v:.0f}  (subtracted)')
					if in_norm:
						stats.append('115In norm.   =  applied')
					fig.text(
						LEFT, 0.35, '\n'.join(stats),
						ha='left', va='top', fontsize=BODY_FS, family='monospace',
						linespacing=1.6,
					)

					pdf.savefig(fig)
					plt.close(fig)

			print(f"Saved calibration report to {pdf_path}")

		# Save calibration file. If a calibration_curve.calib already exists in
		# the target directory, rename it to
		#     calibration_curve_<YYYYMMDD_HHMMSS>.calib
		# using its last-modified time, so historic curves stay paired with
		# the timestamped PDF report from when they were generated. The new
		# file is always written as calibration_curve.calib so downstream
		# loading is unchanged.
		def _archive_existing_calib(path):
			if not os.path.exists(path):
				return
			from datetime import datetime as _dt
			mtime = os.path.getmtime(path)
			stamp = _dt.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')
			root, ext = os.path.splitext(path)
			archived = f'{root}_{stamp}{ext}'
			# Guard against collision (multiple runs in the same second).
			counter = 1
			while os.path.exists(archived):
				archived = f'{root}_{stamp}_{counter}{ext}'
				counter += 1
			os.rename(path, archived)
			archived_calibs.append(archived)
			print(f'Archived previous calibration to {archived}')

		# Only overwrite the .calib file when we actually calculated curves —
		# a failed run should not archive and replace a valid historic file.
		savefile = None
		if saveDict:
			if self._mainview.homeDir:
				home_dir = self._mainview.homeDir.rstrip('/\\')
				home_savefile = os.path.join(home_dir, 'calibration_curve.calib')
				_archive_existing_calib(home_savefile)
				with open(home_savefile, 'w') as file:
					file.write(json.dumps(saveDict))
				print(f"Saved calibration to {home_savefile}")

			savefile = os.path.join(
				self._calview.calibrationDir, 'calibration_curve.calib'
			)
			_archive_existing_calib(savefile)
			with open(savefile, 'w') as file:
				file.write(json.dumps(saveDict))
			print(f"Saved calibration to {savefile}")

		# Summary consumed by the calibration controller to show a popup.
		return {
			'fitted': [
				{'element': m, 'slope': slope, 'r2': r2, 'mse': mse, 'n': n}
				for (m, slope, r2, mse, n, _, _, _, _) in fit_rows
			],
			'skipped': skipped_elements,
			'pdf_path': pdf_path_out,
			'calib_path': savefile,
			'archived_calibs': archived_calibs,
			'in_norm_applied': in_norm is not None,
			'blank_name': blank_name,
			'standards_count': len(standards_data),
		}
