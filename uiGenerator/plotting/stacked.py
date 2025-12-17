import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.ticker import (MultipleLocator, MaxNLocator,PercentFormatter)
import os

class ICPMS_Data_Class:
	def __init__(self,icpms_data=None,metals=None,plt_title = None, nax = None, fname = None):
		self.metals = metals
		self.icpms_data = icpms_data
		self.max_time = max(self.icpms_data['Time ' + metals[0]]) / 60
		self.min_time = 0	
		self.max_icp = None
		self.min_icp = 0
		self.plt_title = plt_title
		self._nax = nax 
		self._fname = fname

	def chroma(self):
		fig, host = plt.subplots()

		fig.subplots_adjust(right=0.75)
		colors = sns.color_palette()
		c_keys = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','208Pb']
		c_values = colors[0:8]
		color_dict = {c_keys[i]: c_values[i] for i in range(len(c_keys))}
		icpms_max = 0
		labels = []
		lines = []
		for m in self.metals:
			icpms_time = self.icpms_data['Time ' + m] / 60
			icpms_signal = self.icpms_data[m] / 1000
			msize = len(m)
			mass = m[:msize-2]
			element = m[msize-2:]
			print(mass)
			print(element)
			p, = host.plot(icpms_time, icpms_signal, color = color_dict[m], linewidth  = 0.75, label=r'$^{%s}$' % mass + element)
			if icpms_max < max(icpms_signal): 
				icpms_max = 1.1 * max(icpms_signal)
			lines.append(p)
			labels.append(r'$^{%s}$' % mass + element)
		
		host.set_title(self.plt_title) 
		host.set_xlabel("Retention time (min)")
		host.set_ylabel('ICP-MS signal intensity (cps x 1000)')
		
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

	def chroma_subplot(self):
		fig, axes = plt.subplots(nrows=self._nax,figsize=(4,10),sharex = True)

		fig.subplots_adjust(right=0.75)
		colors = sns.color_palette()
		c_keys = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','208Pb']
		c_values = colors[0:8]
		color_dict = {c_keys[i]: c_values[i] for i in range(len(c_keys))}
		icpms_max = 0
		labels = []
		lines = []
		for m,ax in zip(self.metals, axes):
			icpms_time = self.icpms_data['Time ' + m] / 60
			icpms_signal = self.icpms_data[m] / 10000
			msize = len(m)
			mass = m[:msize-2]
			element = m[msize-2:]
			print(mass)
			print('icpmax: %.2f' % icpms_max )
			p, = ax.plot(icpms_time, icpms_signal, color = color_dict[m], linewidth  = 0.75, label=r'$^{%s}$' % mass + element)

			icpms_max = 1.1 * max(icpms_signal)
			labels = [r'$^{%s}$' % mass + element]

			self.max_icp = icpms_max

			ax.set_xlim(self.min_time, self.max_time)
			ax.set_ylim(0, self.max_icp)

			tkw = dict(size=4, width=1.5)
			ax.tick_params(axis='y',  **tkw)
			ax.tick_params(axis='x', **tkw)

			ax.xaxis.set_major_locator(MaxNLocator(4))

			ax.ticklabel_format(style='plain', axis='y', useMathText=True,scilimits=(0,0))
			ax.annotate(labels[0], xy=(0.9, 0.9),color = color_dict[m], xycoords='axes fraction', ha='right', va='top')
		
		plt.xlabel("Retention time (min)")
		plt.subplots_adjust(left=0.18)

		fig.text(0.01, 0.5, 'ICP-MS signal intensity (10'+r'$^{4}$'+ ' cps)', va='center', rotation='vertical')
		sns.despine()
		plt.savefig('/Users/christiandewey/manuscripts/in progress/LC-ICPMS/data/python/column-test/data-for-retention-plot/' + self._fname, dpi=300,bbox_inches='tight',format='eps')
