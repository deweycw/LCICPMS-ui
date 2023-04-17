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
from functools import partial
import seaborn as sns
import csv
from .chroma import *
from .pgChroma import *
import re
import copy

__version__ = '2.1'
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
		
	def importData(self):
		'''imports LCICPMS .csv file'''
		if self._view.listwidget.currentItem() is not None:
			self.fdir = self._view.homeDir + self._view.listwidget.currentItem().text()
			self._data = pd.read_csv(self.fdir,sep=';|,',skiprows = 0, header = 1,engine='python')

		if self._view._metals_in_file == []:
			for c in self._data.columns:
				if 'Time' in c:
					ic = c.split(' ')[1]
					self._view._metals_in_file.append(ic)
					self._view.activeMetals.append(ic)
		self._view.active_metal_isotopes = self._view.activeMetals
	
	def importData_generic(self,fdir):
		'''imports LCICPMS .csv file'''
		data = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)

		return data 
	
	def plotActiveMetals(self):
		'''plots active metals for selected file'''

		self._view.chroma = plotChroma(self._view, self._view.activeMetals, self._data, self._view.activeMetals)._plotChroma()
		if self.minline != None:
			self._view.plotSpace.addItem(self.minline)
		if self.maxline != None:
			self._view.plotSpace.addItem(self.maxline)

	def integrate(self, intRange):
		'''integrates over specified x range'''
		self.intRange = intRange
		time_holders = {'start_time': 0, 'stop_time' : 0}
		metals_no_indium = copy.deepcopy(self._view._metals_in_file)
		metals_no_indium.remove('115In')
		metal_dict= {m: None for m in metals_no_indium}
		corr_dict = {'correction': None}
		tstamp = {'timestamp': None}
		metalConcs = {**tstamp,**time_holders,**corr_dict,**metal_dict}
		peakAreas = {**tstamp,**time_holders,**corr_dict,**metal_dict}

		if self._view.normAvIndium > 0:
			indium_col_ind = self._data.columns.get_loc('115In')
			if len(self._data['Time 115In']) > 2000:
				corr_factor = np.average(self._data.iloc[550:2500,indium_col_ind]) / self._view.normAvIndium  #550:2500 indices correspond to ~ 150 to 350 sec
			else:
				corr_factor = np.average(self._data.iloc[:,indium_col_ind]) / self._view.normAvIndium  #550:2500 indices correspond to ~ 150 to 350 sec
			print('\ncorrection factor: %.4f' % corr_factor)
		else:
			corr_factor = 1

		for metal in metals_no_indium: 

			try:
				
				if metal in self._view.activeMetals:

					time = self._data['Time ' + metal] / 60
					range_min = self.intRange[0]
					range_max = self.intRange[1]
					min_delta = min(abs(time - range_min))
					max_delta = min(abs(time - range_max))
					i_tmin = int(np.where(abs(time - range_min) == min_delta )[0][0])
					i_tmax = int(np.where(abs(time - range_max) == max_delta )[0][0])
					minval = self._data.iloc[i_tmin]
					minval = minval['Time ' + metal]

					maxval = self._data.iloc[i_tmax]
					maxval = maxval['Time ' + metal]

					metalConcs['start_time'] = '%.2f' % range_min
					metalConcs['stop_time'] = '%.2f' % range_max
					peakAreas['start_time'] = '%.2f' % range_min
					peakAreas['stop_time'] = '%.2f' % range_max

					metalConcs['correction'] = '%.3f' % corr_factor 
					peakAreas['correction'] = '%.3f' % corr_factor 

					dateTimeObj = datetime.now()
					timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
					metalConcs['timestamp'] = timestampStr
					peakAreas['timestamp'] = timestampStr

					me_col_ind = self._data.columns.get_loc(metal)
					summed_area = 0
					timeDelta = 0
					for i in range(i_tmin, i_tmax+1):
						icp_1 = self._data.iloc[i,me_col_ind] / corr_factor# cps
						icp_2 = self._data.iloc[i+1,me_col_ind] / corr_factor
						min_height = min([icp_1,icp_2])
						max_height = max([icp_1,icp_2])
						
						timeDelta = (self._data.iloc[i+1,me_col_ind - 1] - self._data.iloc[i,me_col_ind - 1])/60 # minutes; time is always to left of metal signal
						rect_area = timeDelta * min_height
						top_area = timeDelta * (max_height - min_height) * 0.5
						An = rect_area + top_area
						summed_area = summed_area + An  # area =  cps * sec = counts
					
					if self._view.baseSubtract == True:
						baseline_height_1 = self._data.iloc[i_tmin,me_col_ind] / corr_factor
						baseline_height_2 =  self._data.iloc[i_tmax,me_col_ind] / corr_factor
						baseline_timeDelta = (self._data.iloc[i_tmax,me_col_ind - 1] - self._data.iloc[i_tmin,me_col_ind - 1])/60 #minutes

						min_base_height = min([baseline_height_1, baseline_height_2])
						max_base_height = max([baseline_height_1, baseline_height_2])
						baseline_area_1 = min_base_height * baseline_timeDelta
						baseline_area_2 = (max_base_height - min_base_height) * baseline_timeDelta * 0.5
						
						baseline_area = baseline_area_1 + baseline_area_2
						summed_area = summed_area - baseline_area
						summed_area = max(summed_area,0)					

					cal_curve = self._view.calCurves[metal]	
					slope = cal_curve['m']
					intercept = cal_curve['b']
					conc_ppb = slope * summed_area + intercept
					
					mass = re.split(r"\D+",metal)[0]
					conc_uM = conc_ppb / float(mass)
					
					peakAreas[metal] = '%.1f' % summed_area
					metalConcs[metal] = '%.3f' % conc_uM
					
					print('\n' + metal + ' uM: %.3f' % conc_uM)
					print(metal  + ' peak area: %.1f' % summed_area)

				else:
					peakAreas[metal] = 'NA' 
					metalConcs[metal] = 'NA' 
				
			except:

				print('\nNo calibration data for %s' %metal)
				peakAreas[metal] = 'nocal'
				metalConcs[metal] = 'nocal'

		
		if self._view.singleOutputFile == False:
			filename =  self._view.homeDir + 'peaks_uM_' + self.fdir.split('/')[-1].split(',')[0]

			if os.path.exists(filename):
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=metalConcs.keys())
					fwriter.writerow(metalConcs) 		
			else:
				csv_cols = ['start_time', 'stop_time','correction'] + metals_no_indium
				with open(filename, 'w', newline = '') as csvfile:
					fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
					if self._view.normAvIndium > 0:
						fwriter.writerow(['115In correction applied: %.3f' % corr_factor,''])
					fwriter.writerow(['concentrations in uM',''])
					fwriter.writerow(['time in minutes',''])
					fwriter.writerow(csv_cols)
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=metalConcs.keys())
					fwriter.writerow(metalConcs) 	
		else:
			filename =  self._view.homeDir + 'concentrations_uM_all.csv' 

			metalConcs = {**{'filename':self.fdir.split('/')[-1].split(',')[0]},**metalConcs}
			if os.path.exists(filename):
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=metalConcs.keys())
					fwriter.writerow(metalConcs) 		
			else:
				csv_cols = ['filename','tstamp','start_time', 'stop_time','correction'] + metals_no_indium
				with open(filename, 'w', newline = '') as csvfile:
					fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
					fwriter.writerow(['concentrations in uM',''])
					fwriter.writerow(['time in minutes',''])
					fwriter.writerow(csv_cols)
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=metalConcs.keys())
					fwriter.writerow(metalConcs) 

			filename =  self._view.homeDir + 'peakareas_counts_all.csv' 

			peakAreas = {**{'filename':self.fdir.split('/')[-1].split(',')[0]},**peakAreas}
			if os.path.exists(filename):
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas.keys())
					fwriter.writerow(peakAreas) 		
			else:
				csv_cols = ['filename','tstamp','start_time', 'stop_time', 'correction'] + metals_no_indium
				with open(filename, 'w', newline = '') as csvfile:
					fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
					if self._view.normAvIndium > 0:
						fwriter.writerow(['115In correction applied: %.3f' % corr_factor,''])
					fwriter.writerow(['time in minutes',''])
					fwriter.writerow(csv_cols)
				with open(filename, 'a', newline = '') as csvfile:
					fwriter = csv.DictWriter(csvfile, fieldnames=peakAreas.keys())
					fwriter.writerow(peakAreas) 

	def plotLowRange(self,xmin,n):
		'''plots integration range'''
		col = self.intColors[0]
		self.minline = pg.InfiniteLine(xmin, pen = col, angle = 90)
		self._view.plotSpace.addItem(self.minline) 
		
	def plotHighRange(self,xmax,n):
		col = self.intColors[0]
		self.maxline = pg.InfiniteLine(xmax, pen=col,angle = 90)
		self._view.plotSpace.addItem(self.maxline)

	def removeIntRange(self):
		self._view.plotSpace.removeItem(self.maxline)
		self._view.plotSpace.removeItem(self.minline)


