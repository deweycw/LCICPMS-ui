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

	def integrate(self, intRange, has_calibration=True):
		'''integrates over specified x range'''
		self.intRange = intRange
		time_holders = {'start_time': 0, 'stop_time' : 0}
		elementList = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd', '208Pb']
		element_dict= {key: None for key in elementList}
		corr_dict = {'correction': None}
		tstamp = {'timestamp': None}
		elementConcs = {**tstamp,**time_holders,**corr_dict,**element_dict}  # uM concentrations
		elementConcs_ppb = {**tstamp,**time_holders,**corr_dict,**element_dict}  # ppb concentrations
		peakAreas = {**tstamp,**time_holders,**corr_dict,**element_dict}

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
				elementConcs_ppb['start_time'] = '%.2f' % range_min
				elementConcs_ppb['stop_time'] = '%.2f' % range_max
				peakAreas['start_time'] = '%.2f' % range_min
				peakAreas['stop_time'] = '%.2f' % range_max
				elementConcs['correction'] = '%.3f' % corr_factor
				elementConcs_ppb['correction'] = '%.3f' % corr_factor
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
					

				peakAreas[element] = '%.1f' % summed_area

				# Only calculate concentrations if calibration is loaded
				if has_calibration and element in self._view.calCurves:
					cal_curve = self._view.calCurves[element]
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

					print(f'\n{element}:')
					print(f'  Peak area: {summed_area:.2e} counts')
					print(f'  Concentration: {conc_ppb:.3f} ppb | {conc_uM:.3f} uM')
				else:
					# No calibration - just report peak area in scientific notation
					print(f'\n{element}:')
					print(f'  Peak area: {summed_area:.2e} counts')
					if not has_calibration:
						print(f'  (No calibration loaded - concentrations not calculated)')

		
		if self._view.singleOutputFile == False:
			# Always save peak areas (counts)
			filename_areas = self._view.homeDir + 'peaks_counts_' + self.fdir.split('/')[-1].split(',')[0]
			if os.path.exists(filename_areas):
				with open(filename_areas, 'a', newline='') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas.keys())
					fwriter.writerow(peakAreas)
			else:
				csv_cols = ['start_time', 'stop_time', 'correction'] + elementList
				with open(filename_areas, 'w', newline='') as csvfile:
					fwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
					if self._view.normAvIndium > 0:
						fwriter.writerow(['115In correction applied: %.3f' % corr_factor, ''])
					fwriter.writerow(['peak areas (counts)', ''])
					fwriter.writerow(['time in minutes', ''])
					fwriter.writerow(csv_cols)
				with open(filename_areas, 'a', newline='') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas.keys())
					fwriter.writerow(peakAreas)

			# Only save concentration files if calibration is loaded
			if has_calibration:
				# Save uM concentrations
				filename_uM = self._view.homeDir + 'peaks_uM_' + self.fdir.split('/')[-1].split(',')[0]
				if os.path.exists(filename_uM):
					with open(filename_uM, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs.keys())
						fwriter.writerow(elementConcs)
				else:
					csv_cols = ['start_time', 'stop_time', 'correction'] + elementList
					with open(filename_uM, 'w', newline='') as csvfile:
						fwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
						if self._view.normAvIndium > 0:
							fwriter.writerow(['115In correction applied: %.3f' % corr_factor, ''])
						fwriter.writerow(['concentrations in uM', ''])
						fwriter.writerow(['time in minutes', ''])
						fwriter.writerow(csv_cols)
					with open(filename_uM, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs.keys())
						fwriter.writerow(elementConcs)

				# Save ppb concentrations
				filename_ppb = self._view.homeDir + 'peaks_ppb_' + self.fdir.split('/')[-1].split(',')[0]
				if os.path.exists(filename_ppb):
					with open(filename_ppb, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs_ppb.keys())
						fwriter.writerow(elementConcs_ppb)
				else:
					csv_cols = ['start_time', 'stop_time', 'correction'] + elementList
					with open(filename_ppb, 'w', newline='') as csvfile:
						fwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
						if self._view.normAvIndium > 0:
							fwriter.writerow(['115In correction applied: %.3f' % corr_factor, ''])
						fwriter.writerow(['concentrations in ppb', ''])
						fwriter.writerow(['time in minutes', ''])
						fwriter.writerow(csv_cols)
					with open(filename_ppb, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs_ppb.keys())
						fwriter.writerow(elementConcs_ppb)
		else:
			# Always save peak areas (single file mode)
			filename_areas = self._view.homeDir + 'peakareas_counts_all.csv'
			peakAreas_with_file = {**{'filename': self.fdir.split('/')[-1].split(',')[0]}, **peakAreas}
			if os.path.exists(filename_areas):
				with open(filename_areas, 'a', newline='') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas_with_file.keys())
					fwriter.writerow(peakAreas_with_file)
			else:
				csv_cols = ['filename', 'tstamp', 'start_time', 'stop_time', 'correction'] + elementList
				with open(filename_areas, 'w', newline='') as csvfile:
					fwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
					if self._view.normAvIndium > 0:
						fwriter.writerow(['115In correction applied: %.3f' % corr_factor, ''])
					fwriter.writerow(['peak areas (counts)', ''])
					fwriter.writerow(['time in minutes', ''])
					fwriter.writerow(csv_cols)
				with open(filename_areas, 'a', newline='') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas_with_file.keys())
					fwriter.writerow(peakAreas_with_file)

			# Only save concentration files if calibration is loaded
			if has_calibration:
				# Save uM concentrations (single file mode)
				filename_uM = self._view.homeDir + 'concentrations_uM_all.csv'
				elementConcs_with_file = {**{'filename': self.fdir.split('/')[-1].split(',')[0]}, **elementConcs}
				if os.path.exists(filename_uM):
					with open(filename_uM, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs_with_file.keys())
						fwriter.writerow(elementConcs_with_file)
				else:
					csv_cols = ['filename', 'tstamp', 'start_time', 'stop_time', 'correction'] + elementList
					with open(filename_uM, 'w', newline='') as csvfile:
						fwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
						fwriter.writerow(['concentrations in uM', ''])
						fwriter.writerow(['time in minutes', ''])
						fwriter.writerow(csv_cols)
					with open(filename_uM, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs_with_file.keys())
						fwriter.writerow(elementConcs_with_file)

				# Save ppb concentrations (single file mode)
				filename_ppb = self._view.homeDir + 'concentrations_ppb_all.csv'
				elementConcs_ppb_with_file = {**{'filename': self.fdir.split('/')[-1].split(',')[0]}, **elementConcs_ppb}
				if os.path.exists(filename_ppb):
					with open(filename_ppb, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs_ppb_with_file.keys())
						fwriter.writerow(elementConcs_ppb_with_file)
				else:
					csv_cols = ['filename', 'tstamp', 'start_time', 'stop_time', 'correction'] + elementList
					with open(filename_ppb, 'w', newline='') as csvfile:
						fwriter = csv.writer(csvfile, delimiter=',', quotechar='|')
						fwriter.writerow(['concentrations in ppb', ''])
						fwriter.writerow(['time in minutes', ''])
						fwriter.writerow(csv_cols)
					with open(filename_ppb, 'a', newline='') as csvfile:
						fwriter = csv.DictWriter(csvfile, fieldnames=elementConcs_ppb_with_file.keys())
						fwriter.writerow(elementConcs_ppb_with_file)
				with open(filename_areas, 'a', newline='') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas_with_file.keys())
					fwriter.writerow(peakAreas_with_file) 

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


