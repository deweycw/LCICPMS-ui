import sys 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
import json
from ..ui.calibration_window import Calibration
from ..controllers.calibration_controller import CalCtrlFunctions
from ..models.calibration import CalibrateFunctions
from PTBuilder.PTView import PTView
from PTBuilder.PTCtrl import PTCtrl
from PTBuilder.PTModel import PTModel

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


# Create a Controller class to connect the GUI and the model
class PyLCICPMSCtrl:
	"""PyCalc Controller class."""
	def __init__(self, model, view, calwindow):
		"""Controller initializer."""
		self._model = model
		self._view = view
		self._calWindow = calwindow
		self._intRange = []
		self.n_clicks = 0
		self._n = 0
		self._xMin = 0
		self._xMax = 0
		self.button_is_checked = False
		self._update_thread = None  # Store update checker thread

		# Connect signals and slots
		self._connectSignals()

		# Check for updates on startup (in background)
		QTimer.singleShot(500, self._check_for_updates)

		# Automatically show directory selection dialog on startup
		QTimer.singleShot(1000, self._selectDirectory)

	def _selectDirectory(self):
		self._view.homeDir = ''
		self._view.listwidget.clear()
		dialog = QFileDialog()
		dialog.setWindowTitle("Select LC-ICPMS Directory")
		dialog.setViewMode(QFileDialog.ViewMode.Detail)
		# Start in home directory (platform-independent)
		home_dir = os.path.expanduser('~')
		self._view.homeDir = str(dialog.getExistingDirectory(self._view, "Select Directory:", home_dir)) + '/'

		self._createListbox()
		self._view.integrateButtons['Calibrate'].setEnabled(True)
		self._view.integrateButtons['Load Cal.'].setEnabled(True)
		self._view.integrateButtons['115In Correction'].setEnabled(True)
		self._view.buttons['Load'].setEnabled(True)

	def _createListbox(self):

		self._view.listwidget.clear()

		test_dir = self._view.homeDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		i = 0
		for name in sorted(os.listdir(test_dir)):
			if '.csv' in name:
				# Add item to list
				self._view.listwidget.insertItem(i, name)

				# Add tooltip with file information
				try:
					file_path = os.path.join(test_dir, name)
					file_size = os.path.getsize(file_path)
					mod_time = os.path.getmtime(file_path)
					from datetime import datetime
					mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')

					# Format file size
					if file_size < 1024:
						size_str = f"{file_size} B"
					elif file_size < 1024 * 1024:
						size_str = f"{file_size / 1024:.1f} KB"
					else:
						size_str = f"{file_size / (1024 * 1024):.1f} MB"

					tooltip = f"Path: {file_path}\nSize: {size_str}\nModified: {mod_date}"
					self._view.listwidget.item(i).setToolTip(tooltip)
				except:
					pass

				i = i + 1

	def _buildExpression(self, sub_exp):
		"""Build expression."""
		expression = self._view.displayText() + sub_exp
		self._view.setDisplayText(expression)

	def _clearForm(self):
		''' clears selection and nulls data '''
		self._view.activeElements = []
		self._view.buttons['Plot'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")

		self._intRange = []
		self._view.plotSpace.clear()
		self._n = 0

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		if self._view.listwidget.currentItem() is not None:
			filename = self._view.listwidget.currentItem().text()
			self._view.setDisplayText(filename)
			self._model.importData()

			# Update window title with filename
			self._view.setWindowTitle(f'LC-ICP-MS Data Viewer - {filename}')

			# Update status bar
			file_path = os.path.join(self._view.homeDir, filename)
			self._view.updateStatusBar(file_path)

			# Auto-select all available elements if none selected
			if self._view.activeElements == []:
				self._view.activeElements = self._view._elements_in_file.copy()

			self._view.buttons['Plot'].setEnabled(True)
			self._makePlot()
			self._view.buttons['Reset'].setEnabled(True)
			self._view.listwidget.setFocus()

	def _mouseover(self, pos):
		''' selects range for integration'''
		act_pos = self._view.chroma.mapFromScene(pos)
		self._intPointX = act_pos.x()
		self._intPointY = act_pos.y()

	def _onClick(self, event):
		''' selects range for integration'''
		self._act_pos = self._view.chroma.mapFromScene(event[0].scenePos())
		cc = len(self._intRange)
		cc = cc + 1
		
		if cc == 1:
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			self._view.statusBar.showMessage(f'Integration start: {self._act_pos.x():.2f} min', 3000)
			self._model.plotLowRange(self._act_pos.x(),self._n)
			self._minAssigned = True

		if (cc == 2) and self._minAssigned is True:
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			self._view.statusBar.showMessage(f'Integration end: {self._act_pos.x():.2f} min | Range: {self._intRange[-1] - self._intRange[-2]:.2f} min', 5000)
			self._model.plotHighRange(self._act_pos.x(),self._n)
			self._view.integrateButtons['Integrate'].setEnabled(True)
			self._view.integrateButtons['Integrate'].setStyleSheet("background-color: red")
			self._n = self._n + 1

		self.n_clicks = 1

	def _selectIntRange(self,checked):
		'''select integration range'''
		if self._view.intbox.isChecked() == True:
			self._view.proxy = pg.SignalProxy(self._view.chroma.scene().sigMouseClicked, rateLimit=60, slot=self._onClick)
			self._view.statusBar.showMessage('Click plot to select integration range', 3000)
		else:
			self._view.proxy = None
			self._view.statusBar.showMessage('Integration range selection disabled', 2000)

	def _selectOneFile(self,checked):
		'''select integration range'''
		if self._view.oneFileBox.isChecked() == True:
			self._view.singleOutputFile = True
		else:
			self._view.singleOutputFile = False

	def _baselineSubtraction(self,checked):
		'''select integration range'''
		if self._view.baseSubtractBox.isChecked() == True:
			#print('base subtract box')
			self._view.baseSubtract = True
		else:
			self._view.baseSubtract = False
			
	def _Integrate(self):
		''' call integration function'''
		if len(self._view.calCurves) > 0:
			self._model.integrate(self._intRange)
			#self._intRange = []
			self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")
		else:
			self._view.integrateButtons['Load Cal.'].setStyleSheet("background-color: yellow")

	def _makePlot(self):
		'''makes plot & activates integration'''
		self._model.plotActiveElements()
	
	def _showCalWindow(self):
		''' opens calibration window '''
		#self.dialog = Calibration(view = self._view)


		self.calWindow = Calibration(view = self._view)
		calmodel = CalibrateFunctions(calview= self.calWindow, mainview = self._view)
		CalCtrlFunctions(model=calmodel, mainview = self._view,view= self.calWindow)
		self.calWindow.show()

	def _showPeriodicTable(self):
		''' opens periodic table for element selection '''
		self._ptview = PTView(mainview=self._view)
		ptmodel = PTModel(ptview=self._ptview, mainview=self._view, maincontrol=self)
		PTCtrl(model=ptmodel, mainview=self._view, ptview=self._ptview, mainctrl=self)
		self._ptview.show()

	def _loadCalFile(self):
		''' loads cal file and saves to self._mainview.calCurves '''
		self._view.integrateButtons['Load Cal.'].setStyleSheet("background-color: light gray")
		for root, dirs, files in os.walk(self._view.homeDir):
			for ff in files:
				if '.calib' in ff:
					calfile = os.path.join(root,ff)

		with open(calfile) as file:
			self._view.calCurves = json.load(file)

		# Update status bar and label
		self._view.statusBar.showMessage(f'Loaded calibration file: {os.path.basename(calfile)}', 5000)
		self._view.calib_label.setText('Calibration loaded')

	def _selectInNormFile(self):
		''' opens window to select normalization file for 115In correction; saves average 115In signal from norm file'''
		dialog = QFileDialog()
		dialog.setWindowTitle("Select Normalization File")
		dialog.setViewMode(QFileDialog.ViewMode.Detail)
		filepath = dialog.getOpenFileName(self._view,"Openfile")[0]
		normData = self._model.importData_generic(fdir = filepath )
		self._view.normAvIndium = np.average(normData['115In'])
		#print(self._view.normAvIndium)
		self._view.integrateButtons['115In Correction'].setEnabled(False)
		
	def _resetIntegrate(self):
		self._intRange = []
		self._model.removeIntRange()
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")
		self._view.integrateButtons['Integrate'].setEnabled(False)

	def _confirmReset(self):
		"""Show confirmation dialog before resetting plot."""
		from PyQt6.QtWidgets import QMessageBox

		# Check if there's anything to reset
		if not self._view.activeElements and not self._intRange:
			# Nothing to reset, just clear
			self._clearForm()
			return

		# Show confirmation dialog
		reply = QMessageBox.question(
			self._view,
			'Confirm Reset',
			'Are you sure you want to reset the plot?\n\nThis will clear:\n- Current plot view\n- Integration ranges\n- Selected elements',
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)

		if reply == QMessageBox.StandardButton.Yes:
			self._clearForm()
			self._view.statusBar.showMessage('Plot reset', 2000)

	def _check_for_updates(self):
		"""Check for updates on startup"""
		try:
			from ..utils.update_checker import check_updates_on_startup
			self._update_thread = check_updates_on_startup(parent=self._view, silent=True)
			# Store thread to prevent garbage collection
		except ImportError:
			# Update checker not available (might be in development mode)
			pass
		except Exception as e:
			# Silently fail - update check is not critical
			pass

	def _connectSignals(self):
		"""Connect signals and slots."""
		for btnText, btn in self._view.buttons.items():
			if btnText  in {'Load'}:
				if self._view.listwidget.currentItem() is None:
					text = ''
				else:
					text = self._view.listwidget.currentItem().text()

				btn.clicked.connect(partial(self._buildExpression, text))

		self._view.buttons['Load'].setEnabled(False)
		self._view.buttons['Plot'].setEnabled(False)
		self._view.buttons['Reset'].setEnabled(False)
		# Select Elements button is always enabled - periodic table can be opened anytime
		self._view.integrateButtons['Calibrate'].setEnabled(False)
		self._view.integrateButtons['Load Cal.'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.integrateButtons['115In Correction'].setEnabled(False)

		self._view.listwidget.setCurrentItem(None)
		self._view.buttons['Directory'].clicked.connect(self._selectDirectory)
		self._view.buttons['Select Elements'].clicked.connect(self._showPeriodicTable)
		
		self._view.buttons['Load'].clicked.connect(self._importAndActivatePlotting)
		self._view.listwidget.currentItemChanged.connect(self._importAndActivatePlotting)
		self._view.listwidget.itemDoubleClicked.connect(lambda: self._importAndActivatePlotting())

		self._view.intbox.stateChanged.connect(self._selectIntRange)
		self._view.oneFileBox.stateChanged.connect(self._selectOneFile)
		self._view.baseSubtractBox.stateChanged.connect(self._baselineSubtraction)

		self._view.buttons['Plot'].clicked.connect(self._makePlot)
		self._view.buttons['Reset'].clicked.connect(self._confirmReset)	

		self._view.integrateButtons['Calibrate'].clicked.connect(self._showCalWindow)
		self._view.integrateButtons['Load Cal.'].clicked.connect(self._loadCalFile)
		self._view.integrateButtons['Integrate'].clicked.connect(self._Integrate)
		self._view.integrateButtons['115In Correction'].clicked.connect(self._selectInNormFile)
		self._view.integrateButtons['Reset Integration'].clicked.connect(self._resetIntegrate)
		



