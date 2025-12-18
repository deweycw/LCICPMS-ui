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
		self.intColors = sns.color_palette(n_colors = 6, as_cmap = True)
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

	def integrate(self, intRange):
		'''integrates over specified x range'''
		self.intRange = intRange
		time_holders = {'start_time': 0, 'stop_time' : 0}
		elementList = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd', '208Pb']
		element_dict= {key: None for key in elementList}
		corr_dict = {'correction': None}
		tstamp = {'timestamp': None}
		elementConcs = {**tstamp,**time_holders,**corr_dict,**element_dict}
		peakAreas = {**tstamp,**time_holders,**corr_dict,**element_dict}

		print(self._view.normAvIndium)
		if self._view.normAvIndium > 0:
			# Find indium column (handles both '115In' and '115In | 115In' formats)
			indium_col = None
			for col in self._data.columns:
				if col.startswith('115In') and 'Time' not in col:
					indium_col = col
					break

			if indium_col:
				indium_col_ind = self._data.columns.get_loc(indium_col)
				time_col = 'Time ' + indium_col
				if len(self._data[time_col]) > 2000:
					corr_factor = np.average(self._data.iloc[550:2500,indium_col_ind]) / self._view.normAvIndium
				else:
					corr_factor = np.average(self._data.iloc[:,indium_col_ind]) / self._view.normAvIndium
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
				time_seconds = self._data['Time ' + element].values
				time_minutes = time_seconds / 60
				intensity = self._data[element].values / corr_factor  # Apply correction factor

				# Set up time range for integration (convert minutes to seconds for lcicpms)
				range_min = self.intRange[0]  # minutes
				range_max = self.intRange[1]  # minutes
				time_range_seconds = (range_min * 60, range_max * 60)  # convert to seconds

				# Store metadata
				elementConcs['start_time'] = '%.2f' % range_min
				elementConcs['stop_time'] = '%.2f' % range_max
				peakAreas['start_time'] = '%.2f' % range_min
				peakAreas['stop_time'] = '%.2f' % range_max
				elementConcs['correction'] = '%.3f' % corr_factor
				peakAreas['correction'] = '%.3f' % corr_factor

				dateTimeObj = datetime.now()
				timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
				elementConcs['timestamp'] = timestampStr
				peakAreas['timestamp'] = timestampStr

				# Use lcicpms Integrate.integrate() for peak area calculation
				summed_area = Integrate.integrate(intensity, time_seconds, time_range=time_range_seconds)

				# Baseline subtraction (if enabled)
				if self._view.baseSubtract == True:
					# Find indices for baseline points
					min_delta = min(abs(time_minutes - range_min))
					max_delta = min(abs(time_minutes - range_max))
					i_tmin = int(np.where(abs(time_minutes - range_min) == min_delta)[0][0])
					i_tmax = int(np.where(abs(time_minutes - range_max) == max_delta)[0][0])

					baseline_height_1 = intensity[i_tmin]
					baseline_height_2 = intensity[i_tmax]
					baseline_timeDelta = (time_seconds[i_tmax] - time_seconds[i_tmin]) / 60  # minutes

					min_base_height = min([baseline_height_1, baseline_height_2])
					max_base_height = max([baseline_height_1, baseline_height_2])
					baseline_area_1 = min_base_height * baseline_timeDelta
					baseline_area_2 = (max_base_height - min_base_height) * baseline_timeDelta * 0.5

					baseline_area = baseline_area_1 + baseline_area_2
					summed_area = summed_area - baseline_area
					summed_area = max(summed_area, 0)
					

				cal_curve = self._view.calCurves[element]	
				slope = cal_curve['m']
				intercept = cal_curve['b']
				conc_ppb = slope * summed_area + intercept
				conc_uM = conc_ppb / self._view.masses[element]
				
				peakAreas[element] = '%.1f' % summed_area
				elementConcs[element] = '%.3f' % conc_uM
				print('\n' + element + ' uM: %.3f' % conc_uM)
				print(element  + ' peak area: %.1f' % summed_area)

		
		if self._view.singleOutputFile == False:
			filename =  self._view.homeDir + 'peaks_uM_' + self.fdir.split('/')[-1].split(',')[0]

			if os.path.exists(filename):
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs.keys())
					fwriter.writerow(elementConcs) 		
			else:
				csv_cols = ['start_time', 'stop_time','correction'] + elementList
				with open(filename, 'w', newline = '') as csvfile:
					fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
					if self._view.normAvIndium > 0:
						fwriter.writerow(['115In correction applied: %.3f' % corr_factor,''])
					fwriter.writerow(['concentrations in uM',''])
					fwriter.writerow(['time in minutes',''])
					fwriter.writerow(csv_cols)
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs.keys())
					fwriter.writerow(elementConcs) 	
		else:
			filename =  self._view.homeDir + 'concentrations_uM_all.csv' 

			elementConcs = {**{'filename':self.fdir.split('/')[-1].split(',')[0]},**elementConcs}
			if os.path.exists(filename):
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs.keys())
					fwriter.writerow(elementConcs) 		
			else:
				csv_cols = ['filename','tstamp','start_time', 'stop_time','correction'] + elementList
				with open(filename, 'w', newline = '') as csvfile:
					fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
				#	if self._view.normAvIndium > 0:
			#		fwriter.writerow(['115In correction applied: %.3f' % corr_factor,''])
					fwriter.writerow(['concentrations in uM',''])
					fwriter.writerow(['time in minutes',''])
					fwriter.writerow(csv_cols)
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs.keys())
					fwriter.writerow(elementConcs) 

			filename =  self._view.homeDir + 'peakareas_counts_all.csv' 

			peakAreas = {**{'filename':self.fdir.split('/')[-1].split(',')[0]},**peakAreas}
			if os.path.exists(filename):
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas.keys())
					fwriter.writerow(peakAreas) 		
			else:
				csv_cols = ['filename','tstamp','start_time', 'stop_time', 'correction'] + elementList
				with open(filename, 'w', newline = '') as csvfile:
					fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
					if self._view.normAvIndium > 0:
						fwriter.writerow(['115In correction applied: %.3f' % corr_factor,''])
					fwriter.writerow(['time in minutes',''])
					fwriter.writerow(csv_cols)
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas.keys())
					fwriter.writerow(peakAreas) 
			#print('Intercept: %.4f' % intercept)
			#print('Slope: %.8f' % slope) 

	def plotLowRange(self,xmin,n):
		'''plots integration range'''
		col = self.intColors[0]
		self.minline = pg.InfiniteLine(xmin, pen = col, angle = 90)
		self._view.plotSpace.addItem(self.minline) #InfiniteLine(minInt,angle = 90)
		
	def plotHighRange(self,xmax,n):
		col = self.intColors[0]
		self.maxline = pg.InfiniteLine(xmax, pen=col,angle = 90)
		self._view.plotSpace.addItem(self.maxline)

		# Add shaded region between min and max lines
		if self.minline is not None:
			xmin = self.minline.value()
			# Create LinearRegionItem with semi-transparent fill
			self.region = pg.LinearRegionItem(
				values=(xmin, xmax),
				orientation='vertical',
				brush=pg.mkBrush(col[0]*255, col[1]*255, col[2]*255, 50),  # Semi-transparent
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


