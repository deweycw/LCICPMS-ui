import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.ticker import (MultipleLocator, MaxNLocator,PercentFormatter)


class ICPMS_Data_Class:
	def __init__(self,icpms_data=None,metals=None,plt_title = None):
		self.metals = metals
		self.icpms_data = icpms_data
		self.max_time = max(self.icpms_data['Time ' + metals[0]]) / 60
		self.min_time = 0	
		self.max_icp = None
		self.min_icp = 0
		self.plt_title = plt_title

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
		'''
		if ((self.max_time - self.min_time) > 20 ) & ((self.max_time - self.min_time) < 50 ):
			xmajtickloc = 10
			xmintickloc = 2
		elif ((self.max_time - self.min_time) > 5 ) & ((self.max_time - self.min_time) <= 20 ):
			xmajtickloc = 5
			xmintickloc = 1
		elif ((self.max_time - self.min_time) > 2 ) & ((self.max_time - self.min_time) <= 5 ):
			xmajtickloc = 1
			xmintickloc = 0.25
		elif ((self.max_time - self.min_time) > 0.5 ) & ((self.max_time - self.min_time) <= 2 ):
			xmajtickloc = 0.5
			xmintickloc = 0.1	
		'''
		host.xaxis.set_major_locator(MaxNLocator(4))
		host.xaxis.set_minor_locator(MaxNLocator(20))
		#host.xaxis.set_minor_locator(MultipleLocator(xmintickloc))
		#host.xaxis.set_major_locator(MultipleLocator(xmajtickloc))
		'''
		if ((self.max_icp - self.min_icp) > 1000 ) & ((self.max_icp - self.min_icp) < 5000 ):
			ymajtickloc = 1000
			ymintickloc = 250
		elif ((self.max_icp - self.min_icp) > 100 ) & ((self.max_icp - self.min_icp) < 1000 ):
			ymajtickloc = 100
			ymintickloc = 25
		elif ((self.max_icp - self.min_icp) > 20 ) & ((self.max_icp - self.min_icp) < 100 ):
			ymajtickloc = 10
			ymintickloc = 2
		elif ((self.max_icp - self.min_icp) > 12 ) & ((self.max_icp - self.min_icp) <= 20 ):
			ymajtickloc = 5
			ymintickloc = 1
		elif ((self.max_icp - self.min_icp) > 5 ) & ((self.max_icp - self.min_icp) <= 12 ):
			ymajtickloc = 2
			ymintickloc = 0.5
		elif ((self.max_icp - self.min_icp) > 2 ) & ((self.max_icp - self.min_icp) <= 5 ):
			ymajtickloc = 1
			ymintickloc = 0.25
		elif ((self.max_icp - self.min_icp) > 0.5 ) & ((self.max_icp - self.min_icp) <= 2 ):
			ymajtickloc = 0.5
			ymintickloc = 0.1	
		host.yaxis.set_minor_locator(MultipleLocator(ymintickloc))
		host.yaxis.set_major_locator(MultipleLocator(ymajtickloc))
		'''
		host.yaxis.set_major_locator(MaxNLocator(4))
		host.yaxis.set_minor_locator(MaxNLocator(20))

		host.legend(lines, labels,frameon = False,bbox_to_anchor=(1.04,0.5), loc="center left", borderaxespad=0)
		host.ticklabel_format(style='plain', axis='y', useMathText=True,scilimits=(0,0))
		sns.despine()
		return fig

'''
import pandas as pd

dir = '/Users/christiandewey/presentations/DOE-PI-22/day6/day6/cwd_211018_day6_13_kinnetex_er2040_10uL.csv'
df = pd.read_csv(dir,sep=';',skiprows = 0, header = 1)
metals_p = ICPMS_Data_Class( df,['56Fe','60Ni'])

metals_p.min_time = 0
metals_p.max_time = 12
#metals_p.max_icp = 

metals_p.chroma().show()



dir3800 = '/Users/christiandewey/manuscripts/in progress/LC-ICPMS/manuscript-data/soil-samples/soil_samples+SA_zorbax/cwd_220208_day1_24_zorbax_3800-filter_50uL.csv'
df = pd.read_csv(dir3800,sep=';',skiprows = 0, header = 1)
metals_p = ICPMS_Data_Class( df,['56Fe','60Ni'])

metals_p.min_time = 0
metals_p.max_time = 12
#metals_p.max_icp = 

metals_p.chroma().show()


dir3801 = '/Users/christiandewey/manuscripts/in progress/LC-ICPMS/manuscript-data/soil-samples/soil_samples+SA_zorbax/cwd_220208_day1_27_zorbax_3801-filter_50uL.csv'
df = pd.read_csv(dir3801,sep=';',skiprows = 0, header = 1)


metals_p = ICPMS_Data_Class( df,['56Fe','60Ni'])

metals_p.min_time = 0
metals_p.max_time = 12
#metals_p.max_icp = 

metals_p.chroma().show()



plt.close('all')


'''