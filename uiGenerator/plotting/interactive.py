import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib.ticker import (MultipleLocator, MaxNLocator,PercentFormatter)
import pyqtgraph as pg
from uiGenerator.utils.analyte_formatter import format_analyte_html

class plotChroma:
	def __init__(self,view = None,elementList=None,icpms_data=None,activeElements=None,plt_title = None):
		self._view = view
		self.elementList= elementList
		self.activeElements = activeElements
		self.icpms_data = icpms_data
		self.max_time = max(self.icpms_data['Time ' + self.activeElements[0]]) / 60
		self.min_time = 0	
		self.max_icp = None
		self.min_icp = 0
		self.plt_title = plt_title

	def _plotChroma(self):
		# Build color palette based on active elements, not the hardcoded elementOptions
		num_colors = max(len(self.activeElements), 1)  # Ensure at least 1 color
		colors = sns.color_palette(n_colors = num_colors, as_cmap = True)

		# Create color dictionary for all active elements
		color_dict = {}
		for i, metal in enumerate(self.activeElements):
			if i < 10:
				color_dict[metal] = colors[i]
			else:
				color_dict[metal] = 'gray'

		self._view.plotSpace.clear()
		chromaplots = []
		for m in self.activeElements:
			icpms_time = self.icpms_data['Time ' + m] / 60
			icpms_signal = self.icpms_data[m] / 1000
			self.max_icp = max(icpms_signal)
			# Format the analyte name with superscripts/subscripts for the legend
			formatted_name = format_analyte_html(m)
			self._view.plotSpace.setBackground('w')
			pen = color_dict[m]
			self._view.plotSpace.addLegend(offset = [-1,1])
			chromaPlot = self._view.plotSpace.plot(icpms_time, icpms_signal, pen=pen, width=4, name=formatted_name)
		return chromaPlot


			


		
