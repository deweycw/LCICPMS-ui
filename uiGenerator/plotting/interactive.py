import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib.ticker import (MultipleLocator, MaxNLocator,PercentFormatter)
import pyqtgraph as pg
from uiGenerator.utils.analyte_formatter import format_analyte_html

class plotChroma:
	def __init__(self,view = None,elementList=None,icpms_data=None,activeElements=None,plt_title = None, compare_data=None, compare_files=None, compare_labels=None):
		self._view = view
		self.elementList= elementList
		self.activeElements = activeElements if activeElements else []
		self.icpms_data = icpms_data
		self.compare_data_list = compare_data  # List of dataframes (or None)
		self.compare_files_list = compare_files  # List of filenames (or None)
		self.compare_labels_dict = compare_labels if compare_labels else {}  # Dictionary of custom labels

		# Set default time range, or calculate from first active element if available
		if self.activeElements and len(self.activeElements) > 0 and self.icpms_data is not None:
			try:
				self.max_time = max(self.icpms_data['Time ' + self.activeElements[0]]) / 60
			except (KeyError, ValueError):
				self.max_time = 10  # Default fallback
		else:
			self.max_time = 10  # Default fallback

		self.min_time = 0
		self.max_icp = None
		self.min_icp = 0
		self.plt_title = plt_title

		# Define line styles for elements (max 2)
		self.element_line_styles = [
			pg.QtCore.Qt.PenStyle.SolidLine,    # Element 1
			pg.QtCore.Qt.PenStyle.DashLine,     # Element 2
		]

	def _plotChroma(self):
		# Handle empty activeElements
		if not self.activeElements or len(self.activeElements) == 0:
			self._view.plotSpace.clear()
			self._view.plotSpace.setBackground('w')
			self._view.updateLegend([], {})
			return None

		self._view.plotSpace.clear()
		self._view.plotSpace.setBackground('w')

		# Comparison mode: colors for files (only 1 element allowed)
		if self.compare_data_list is not None and len(self.compare_data_list) > 0:
			# Generate colors for files
			num_files = len(self.compare_data_list)
			file_colors = sns.color_palette(n_colors=num_files)  # Each file gets a color

			# Build legend with file colors only (no element labels since only 1 element allowed)
			legend_elements = []
			legend_colors = {}

			# Add file legend entries (showing colors)
			for file_idx, filename in enumerate(self.compare_files_list):
				# Use custom label if available, otherwise extract from filename
				if filename in self.compare_labels_dict:
					short_name = self.compare_labels_dict[filename]
				elif "LCICPMS_" in filename and ".csv" in filename:
					# Extract text between "LCICPMS_" and ".csv"
					start = filename.index("LCICPMS_") + len("LCICPMS_")
					end = filename.index(".csv")
					short_name = filename[start:end]
				else:
					# Fallback: just remove .csv extension
					short_name = filename.replace('.csv', '')

				# Truncate if still too long (only if not a custom label)
				if filename not in self.compare_labels_dict and len(short_name) > 20:
					short_name = short_name[:20] + "..."

				legend_elements.append(short_name)
				legend_colors[short_name] = file_colors[file_idx]

			self._view.updateLegend(legend_elements, legend_colors)

			# Plot data: each file gets a color, all use solid lines (only 1 element)
			chromaplots = []
			for element in self.activeElements:  # Should only be 1 element
				for file_idx, compare_data in enumerate(self.compare_data_list):
					try:
						# Get data for this file and element
						icpms_time = compare_data['Time ' + element] / 60
						icpms_signal = compare_data[element]  # Keep in cps, don't divide by 1000
						self.max_icp = max(icpms_signal) if self.max_icp is None else max(self.max_icp, max(icpms_signal))

						# Get color for this file
						file_color = file_colors[file_idx]
						if isinstance(file_color, tuple) and len(file_color) >= 3:
							rgb_255 = tuple(int(c * 255) for c in file_color[:3])
						else:
							rgb_255 = (128, 128, 128)

						# Create pen: file determines color, all solid lines
						pen = pg.mkPen(color=rgb_255, width=4, style=pg.QtCore.Qt.PenStyle.SolidLine)

						# Plot the data
						chromaPlot = self._view.plotSpace.plot(icpms_time, icpms_signal, pen=pen)
						chromaplots.append(chromaPlot)

					except KeyError:
						# Element not found in this comparison file, skip it
						pass

			# Set axis ranges from 0 to data max
			if self.max_icp is not None:
				self._view.plotSpace.setYRange(0, self.max_icp * 1.03, padding=0)
			self._view.plotSpace.setXRange(0, self.max_time, padding=0)

			return chromaplots[0] if chromaplots else None

		# Normal mode: colors for elements
		else:
			# Build color palette based on active elements
			num_colors = max(len(self.activeElements), 1)
			colors = sns.color_palette(n_colors=num_colors)

			# Create color dictionary for all active elements
			color_dict = {}
			for i, metal in enumerate(self.activeElements):
				if i < num_colors:
					color_dict[metal] = colors[i]
				else:
					color_dict[metal] = (0.5, 0.5, 0.5)

			# Update legend with normal elements
			self._view.updateLegend(self.activeElements, color_dict)

			# Plot each element
			chromaplots = []
			for m in self.activeElements:
				# Get data
				icpms_time = self.icpms_data['Time ' + m] / 60
				icpms_signal = self.icpms_data[m]  # Keep in cps, don't divide by 1000
				self.max_icp = max(icpms_signal) if self.max_icp is None else max(self.max_icp, max(icpms_signal))

				# Convert color
				color = color_dict[m]
				if isinstance(color, tuple) and len(color) >= 3:
					rgb_255 = tuple(int(c * 255) for c in color[:3])
				else:
					rgb_255 = (128, 128, 128)

				# Use solid line, width 4 for single file mode
				pen = pg.mkPen(color=rgb_255, width=4, style=pg.QtCore.Qt.PenStyle.SolidLine)

				chromaPlot = self._view.plotSpace.plot(icpms_time, icpms_signal, pen=pen)
				chromaplots.append(chromaPlot)

			# Set axis ranges from 0 to data max
			if self.max_icp is not None:
				self._view.plotSpace.setYRange(0, self.max_icp * 1.03, padding=0)
			self._view.plotSpace.setXRange(0, self.max_time, padding=0)

			return chromaplots[0] if chromaplots else None





		
