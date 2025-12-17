import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib.ticker import (MultipleLocator, MaxNLocator,PercentFormatter)
import pyqtgraph as pg

class plotChroma:
	def __init__(self,view = None,metalList=None,icpms_data=None,activeMetals=None,plt_title = None):
		self._view = view
		self.metalList= metalList
		self.activeMetals = activeMetals
		self.icpms_data = icpms_data
		self.max_time = max(self.icpms_data['Time ' + self.activeMetals[0]]) / 60
		self.min_time = 0	
		self.max_icp = None
		self.min_icp = 0
		self.plt_title = plt_title

	def _plotChroma(self):
		colors = sns.color_palette(n_colors = len(self.metalList),as_cmap = True)
		c_keys = self.metalList
		color_dict = {c_keys[i]: None for i in range(len(c_keys))}

		for i in range(len(c_keys)):
			if i < 10:
				color_dict[c_keys[i]] = colors[i]
			else:
				color_dict[c_keys[i]] = 'gray'
		self._view.plotSpace.clear()
		chromaplots = []
		for m in self.activeMetals:
			icpms_time = self.icpms_data['Time ' + m] / 60
			icpms_signal = self.icpms_data[m] / 1000
			self.max_icp = max(icpms_signal)
			msize = len(m)
			mass = m[:msize-2]
			element = m[msize-2:]
			self._view.plotSpace.setBackground('w')
			pen = color_dict[m]
			self._view.plotSpace.addLegend(offset = [-1,1])
			chromaPlot = self._view.plotSpace.plot(icpms_time, icpms_signal,pen=pen,width = 2,name = m)
		return chromaPlot


			


		
