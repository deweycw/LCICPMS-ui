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

from .chroma import *
from .pgChroma import *

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
		self.intColors = sns.color_palette(n_colors = 6, as_cmap = True)
		
	def importData(self):
		'''imports cal .csv file'''
		fdir = self._mainview.homeDir + self._calview.listwidget.currentItem().text()
		self._data = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)

	def plotActiveMetals(self):
		'''plots active metals for selected file'''
		self._calview.chroma = plotChroma(self._calview, self._calview.metalOptions, self._data, self._calview.activeMetals)._plotChroma()

	def integrate(self, intRange):
		'''integrates over specified x range'''
		self.intRange = intRange
		pa_dict = {}
		for metal in self._calview.activeMetals:
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

			icpms_dataToSum = self._data[metal].iloc[i_tmin:i_tmax]
			#print(icpms_dataToSum)

			me_col_ind = self._data.columns.get_loc(metal)
			summed_area = 0
			for i in range(i_tmin, i_tmax):
				icp_1 = self._data.iloc[i,me_col_ind] # cps
				icp_2 = self._data.iloc[i+1,me_col_ind]
				min_height = min([icp_1,icp_2])
				max_height = max([icp_1,icp_2])
				timeDelta = self._data.iloc[i+1,me_col_ind - 1] - self._data.iloc[i,me_col_ind - 1] # seconds; time is always to left of metal signal
				#print(i, i+1, timeDelta)
				#print(min_height, max_height)
				rect_area = timeDelta * min_height
				top_area = timeDelta * (max_height - min_height) * 0.5
				An = rect_area + top_area
				summed_area = summed_area + An  # area =  cps * sec = counts
			print(metal + ': ' + str(summed_area/60))
	
			keys = self._calview.activeMetals
			for m in keys:
				pa_dict[m] = summed_area
				
			self._calview.n_area = pa_dict

	def plotLowRange(self,xmin,n):
		'''plots integration range'''
		col = self.intColors[n]
		minline = pg.InfiniteLine(xmin, pen = col, angle = 90)
		self._calview.plotSpace.addItem(minline) #InfiniteLine(minInt,angle = 90)
		
	def plotHighRange(self,xmax,n):
		col = self.intColors[n]
		maxline = pg.InfiniteLine(xmax, pen=col,angle = 90)
		self._calview.plotSpace.addItem(maxline)