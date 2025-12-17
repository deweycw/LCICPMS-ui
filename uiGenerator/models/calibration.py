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
		self.intColors = sns.color_palette(n_colors = 6, as_cmap = True)
		
	def importData(self):
		'''imports cal .csv file using lcicpms.RawICPMSData'''
		fdir = self._calview.calibrationDir + self._calview.listwidget.currentItem().text()
		raw_data = RawICPMSData(fdir)
		self._data = raw_data.raw_data_df

		if self._calview.elements_in_stdfile == []:
			self._calview.elements_in_stdfile = raw_data.elements.copy()
	def plotActiveElements(self):
		'''plots active elements for selected file'''
		self._calview.chroma = plotChroma(self._calview, self._calview.elements_in_stdfile, self._data, self._calview.elements_in_stdfile)._plotChroma()

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

		filename =  self._calview.calibrationDir + 'calibration_areas.txt' 
		with open(filename, 'a', newline = '') as csvfile:
			fwriter = csv.DictWriter(csvfile, fieldnames=pa_dict.keys())
			if self.ntime == True:
				fwriter.writeheader()
				self.ntime = False
			fwriter.writerow(pa_dict) 

	def plotLowRange(self,xmin,n):
		'''plots integration range'''
		col = self.intColors[n]
		minline = pg.InfiniteLine(xmin, pen = col, angle = 90)
		self._calview.plotSpace.addItem(minline) #InfiniteLine(minInt,angle = 90)
		
	def plotHighRange(self,xmax,n):
		col = self.intColors[n]
		maxline = pg.InfiniteLine(xmax, pen=col,angle = 90)
		self._calview.plotSpace.addItem(maxline)

	def calcLinearRegression(self):
		calCurve_dict = {}
		saveDict = {}
		elements = self._calview.elements_in_stdfile
		blank_value = 0
		blank_dict = {}

		for m in elements:
			pas = []
			concs = [] 
			for std in self._calview.standards.keys():
				std_list_n = self._calview.standards[std]
				if (std == 'Blank') and (len(std_list_n) > 0):
					blank_dict = std_list_n[0] 
					blank_value = blank_dict[m]
					print('blank PA for ' + m + ' = %.2f' % blank_value)
				if len(std_list_n) > 0:
					std_dict = std_list_n[0]
					pas.append(std_dict[m]-blank_value)
					concs.append(std_list_n[1])
			print(pas, concs)
			X = np.array(pas).reshape(-1, 1)
			y = np.array(concs)
			regr = linear_model.LinearRegression(fit_intercept=False)
			regr.fit(X, y)

			y_pred = regr.predict(X)

			# Print the Intercept:
			print("Element: " + m)
			print('Intercept:', regr.intercept_)

			# Print the Slope:
			print('Slope:', regr.coef_[0]) 
			# The mean squared error
			mse = mean_squared_error(y, y_pred)
			print("Mean squared error: %.2f" % mse)
			# The coefficient of determination: 1 is perfect prediction
			r2 = r2_score(y, y_pred)
			print("Coefficient of determination: %.2f" % r2)
			
			fig, host = plt.subplots()
			host.scatter(X/1000, y, color="black")
			host.plot(X/1000, y_pred, color="blue", linewidth=3)

			host.set_xlabel(r'Peak Area ($10^3$ ICP-MS counts)')
			host.set_ylabel('Standard Conc. (ppb)')
			host.text(0.8,0.5,'$R^2$ = %.4f' % r2, transform = host.transAxes)
			host.text(0.8,0.4,'MSE = %.2f' % mse, transform = host.transAxes)
		
			host.set_title(m)

			fname = self._calview.calibrationDir + m + '_calibration.png'
			plt.savefig(fname, dpi = 300)
			plt.show()
		
			calCurve_dict[m] = [regr,(mean_squared_error(X, y),r2_score(X, y))]
			saveDict[m] = {'m': regr.coef_[0], 'b': regr.intercept_, 'r2': r2, 'mse': mse}
			
		self._mainview.calCurves = saveDict

		savefile = self._mainview.homeDir + 'calibration_curve.calib'
		with open(savefile, 'w') as file:
			file.write(json.dumps(saveDict))

		savefile = self._calview.calibrationDir + 'calibration_curve.calib'
		with open(savefile, 'w') as file:
			file.write(json.dumps(saveDict))
		
		