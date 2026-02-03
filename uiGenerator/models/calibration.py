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

			# Filter elements to only those selected in the main view's activeElements
			all_elements = raw_data.elements.copy()
			selected_elements = self._mainview.activeElements if self._mainview.activeElements else all_elements

			# Only include elements that are both in the file AND selected for calibration
			self._calview.elements_in_stdfile = [el for el in all_elements if el in selected_elements]

			print(f"  Elements in file: {all_elements}")
			print(f"  Elements selected for calibration: {selected_elements}")
			print(f"  Elements to use: {self._calview.elements_in_stdfile}")

		except Exception as e:
			print(f"  ERROR loading file: {e}")
			import traceback
			traceback.print_exc()
			self._data = None
			self._calview.elements_in_stdfile = []

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
			print(element + ': ' + str(summed_area/60))

			pa_dict[element] = summed_area/60

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
		"""
		calCurve_dict = {}
		saveDict = {}
		elements = self._calview.elements_in_stdfile

		# Find blank if present (concentration = 0 or name contains 'blank')
		blank_dict = {}
		for std in standards_data:
			if std['concentration'] == 0 or 'blank' in std['name'].lower():
				blank_dict = std['peak_areas']
				print(f"Found blank: {std['name']}")
				break

		for m in elements:
			pas = []
			concs = []

			# Get blank value for this element
			blank_value = blank_dict.get(m, 0) if blank_dict else 0
			if blank_value > 0:
				print(f'Blank PA for {m} = {blank_value:.2f}')

			# Collect data from all standards
			for std in standards_data:
				if std['peak_areas'] is None:
					continue
				if m not in std['peak_areas']:
					continue

				# Subtract blank and add to list
				peak_area = std['peak_areas'][m] - blank_value
				concentration = std['concentration']

				# Skip blank in regression (concentration = 0)
				if concentration > 0:
					pas.append(peak_area)
					concs.append(concentration)

			if len(pas) < 2:
				print(f"Skipping {m}: insufficient data points ({len(pas)})")
				continue

			print(f"{m}: peak areas={pas}, concentrations={concs}")

			X = np.array(pas).reshape(-1, 1)
			y = np.array(concs)
			regr = linear_model.LinearRegression(fit_intercept=False)
			regr.fit(X, y)

			y_pred = regr.predict(X)

			# Print results
			print(f"Element: {m}")
			print(f'Intercept: {regr.intercept_}')
			print(f'Slope: {regr.coef_[0]}')

			mse = mean_squared_error(y, y_pred)
			print(f"Mean squared error: {mse:.2f}")

			r2 = r2_score(y, y_pred)
			print(f"Coefficient of determination: {r2:.2f}")

			# Create calibration plot
			fig, host = plt.subplots()
			host.scatter(X/1000, y, color="black", s=50, zorder=5)
			host.plot(X/1000, y_pred, color="blue", linewidth=2)

			host.set_xlabel(r'Peak Area ($10^3$ ICP-MS counts)')
			host.set_ylabel('Standard Conc. (ppb)')
			host.text(0.05, 0.95, f'$R^2$ = {r2:.4f}', transform=host.transAxes, verticalalignment='top')
			host.text(0.05, 0.88, f'MSE = {mse:.2f}', transform=host.transAxes, verticalalignment='top')
			host.text(0.05, 0.81, f'Slope = {regr.coef_[0]:.4e}', transform=host.transAxes, verticalalignment='top')

			host.set_title(m)
			host.set_xlim(left=0)
			host.set_ylim(bottom=0)

			fname = os.path.join(self._calview.calibrationDir, f'{m}_calibration.png')
			plt.savefig(fname, dpi=300, bbox_inches='tight')
			plt.show()

			calCurve_dict[m] = [regr, (mse, r2)]
			saveDict[m] = {'m': regr.coef_[0], 'b': regr.intercept_, 'r2': r2, 'mse': mse}

		self._mainview.calCurves = saveDict

		# Save calibration file
		if self._mainview.homeDir:
			home_dir = self._mainview.homeDir.rstrip('/')
			savefile = os.path.join(home_dir, 'calibration_curve.calib')
			with open(savefile, 'w') as file:
				file.write(json.dumps(saveDict))
			print(f"Saved calibration to {savefile}")

		savefile = os.path.join(self._calview.calibrationDir, 'calibration_curve.calib')
		with open(savefile, 'w') as file:
			file.write(json.dumps(saveDict))
		print(f"Saved calibration to {savefile}")
		
		