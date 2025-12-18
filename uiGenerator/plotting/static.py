import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.ticker import (MultipleLocator, MaxNLocator,PercentFormatter)
from uiGenerator.utils.analyte_formatter import format_analyte_latex


class ICPMS_Data_Class:
	def __init__(self,icpms_data=None,elements=None,plt_title = None):
		self.elements = elements
		self.icpms_data = icpms_data
		self.max_time = max(self.icpms_data['Time ' + elements[0]]) / 60
		self.min_time = 0	
		self.max_icp = None
		self.min_icp = 0
		self.plt_title = plt_title

	def chroma(self):
		fig, host = plt.subplots()

		fig.subplots_adjust(right=0.75)
		# Generate colors based on actual elements being plotted
		num_colors = max(len(self.elements), 1)
		colors = sns.color_palette(n_colors=num_colors)
		color_dict = {self.elements[i]: colors[i] if i < len(colors) else 'gray' for i in range(len(self.elements))}
		icpms_max = 0
		labels = []
		lines = []
		for m in self.elements:
			icpms_time = self.icpms_data['Time ' + m] / 60
			icpms_signal = self.icpms_data[m]  # Keep in cps, don't divide by 1000
			formatted_label = format_analyte_latex(m)
			p, = host.plot(icpms_time, icpms_signal, color = color_dict[m], linewidth=2.5, label=formatted_label)
			if icpms_max < max(icpms_signal):
				icpms_max = 1.1 * max(icpms_signal)
			lines.append(p)
			labels.append(formatted_label)
		
		host.set_title(self.plt_title)
		host.set_xlabel("Time (min)", fontsize=12)
		host.set_ylabel('Signal Intensity (cps)', fontsize=12)
		
		if self.max_icp == None:
			self.max_icp = icpms_max

		host.set_xlim(self.min_time, self.max_time)
		host.set_ylim(0, self.max_icp)

		tkw = dict(size=4, width=1.5)
		host.tick_params(axis='y',  **tkw)
		host.tick_params(axis='x', **tkw)

		host.xaxis.set_major_locator(MaxNLocator(4))
		host.xaxis.set_minor_locator(MaxNLocator(20))

		host.yaxis.set_major_locator(MaxNLocator(4))
		host.yaxis.set_minor_locator(MaxNLocator(20))

		host.legend(lines, labels,frameon = False,bbox_to_anchor=(1.04,0.5), loc="center left", borderaxespad=0)
		host.ticklabel_format(style='plain', axis='y', useMathText=True,scilimits=(0,0))
		sns.despine()
		return fig