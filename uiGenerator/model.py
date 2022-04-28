from curses import meta
from datetime import timedelta
import sys 
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import * 
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
		
	def importData(self):
		'''imports LCICPMS .csv file'''
		self.fdir = self._view.homeDir + self._view.listwidget.currentItem().text()
		self._data = pd.read_csv(self.fdir,sep=';',skiprows = 0, header = 1)

	def plotActiveMetalsMP(self):
		'''plots active metals for selected file'''
		activeMetalsPlot = ICPMS_Data_Class(self._data,self._view.activeMetals)
		activeMetalsPlot.chroma().show()
	
	def plotActiveMetals(self):
		'''plots active metals for selected file'''
		self._view.chroma = plotChroma(self._view, self._view.metalOptions, self._data, self._view.activeMetals)._plotChroma()

	def integrate(self, intRange):
		'''integrates over specified x range'''
		self.intRange = intRange
		time_holders = {'start_time': 0, 'stop_time' : 0}
		metalList = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd', '208Pb']
		metal_dict= {key: None for key in metalList}
		metalConcs = {**time_holders,**metal_dict}

		for metal in self._view.activeMetals:
			if metal != '115In':
				time = self._data['Time ' + metal] / 60
				range_min = self.intRange[0]
				range_max = self.intRange[1]
				min_delta = min(abs(time - range_min))
				max_delta = min(abs(time - range_max))
				i_tmin = int(np.where(abs(time - range_min) == min_delta )[0][0])
				i_tmax = int(np.where(abs(time - range_max) == max_delta )[0][0])
				minval = self._data.iloc[i_tmin]
				minval = minval['Time ' + metal]
				#print( i_tmin, minval/60, range_min)

				maxval = self._data.iloc[i_tmax]
				maxval = maxval['Time ' + metal]
				#print( i_tmax, maxval/60, range_max)

				#print(icpms_dataToSum)
				metalConcs['start_time'] = '%.2f' % range_min
				metalConcs['stop_time'] = '%.2f' % range_max

				me_col_ind = self._data.columns.get_loc(metal)
				summed_area = 0
				timeDelta = 0
				for i in range(i_tmin, i_tmax):
					icp_1 = self._data.iloc[i,me_col_ind] # cps
					icp_2 = self._data.iloc[i+1,me_col_ind]
					min_height = min([icp_1,icp_2])
					max_height = max([icp_1,icp_2])
					#print('min height: %.2f' % min_height) 
					#print('max height: %.2f' % max_height) 
					
					timeDelta = (self._data.iloc[i+1,me_col_ind - 1] - self._data.iloc[i,me_col_ind - 1])/60 # minutes; time is always to left of metal signal
					#print('time step: %.4f' % timeDelta) 
					#print(i, i+1, timeDelta)
					#print(min_height, max_height)
					rect_area = timeDelta * min_height
					top_area = timeDelta * (max_height - min_height) * 0.5
					An = rect_area + top_area
					#print('rect area: %.2f' % rect_area)
					#print('top area: %.2f' % top_area)
					#print('dArea: %.2f' % An)
					summed_area = summed_area + An  # area =  cps * sec = counts
					
				print('\n' + metal  + ' peak area: %.2f' % summed_area)

				cal_curve = self._view.calCurves[metal]	
				slope = cal_curve['m']
				intercept = cal_curve['b']
				conc_ppb = slope * summed_area + intercept
				conc_uM = conc_ppb / self._view.masses[metal]
				
				metalConcs[metal] = '%.2f' % conc_uM
			print(metal + ' uM: %.4f' % conc_uM)

		filename =  self._view.homeDir + 'peaks_uM_' + self.fdir.split('/')[-1].split(',')[0] + '.csv'

		if os.path.exists(filename):
			with open(filename, 'a', newline = '') as csvfile:
				fwriter = csv.DictWriter(csvfile, fieldnames=metalConcs.keys())
				fwriter.writerow(metalConcs) 		
		else:
			csv_cols = ['start_time', 'stop_time'] + metalList
			with open(filename, 'w', newline = '') as csvfile:
				fwriter = csv.writer(csvfile, delimiter = ',', quotechar = '|')
				fwriter.writerow(['concentrations in uM',''])
				fwriter.writerow(['time in minutes',''])
				fwriter.writerow(csv_cols)
			with open(filename, 'a', newline = '') as csvfile:
				fwriter = csv.DictWriter(csvfile, fieldnames=metalConcs.keys())
				fwriter.writerow(metalConcs) 	

			#print('Intercept: %.4f' % intercept)
			#print('Slope: %.8f' % slope) 

	def plotLowRange(self,xmin,n):
		'''plots integration range'''
		col = self.intColors[n]
		minline = pg.InfiniteLine(xmin, pen = col, angle = 90)
		self._view.plotSpace.addItem(minline) #InfiniteLine(minInt,angle = 90)
		
	def plotHighRange(self,xmax,n):
		col = self.intColors[n]
		maxline = pg.InfiniteLine(xmax, pen=col,angle = 90)
		self._view.plotSpace.addItem(maxline)