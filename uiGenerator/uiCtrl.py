import sys 
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial
import json
from uiGenerator.calWindowUI import *
from uiGenerator.calCntrl import *
from uiGenerator.calibrate import *

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
		#self._data = None
		self._intRange = []		
		#self._intPointX = 0
		#self._intPointY = 0 
		#self._intX = []
		#self._intY = []
		self.n_clicks = 0
		self._n = 0
		self._xMin = 0
		self._xMax = 0
		self.button_is_checked = False
		
		# Connect signals and slots
		self._connectSignals()

	def _selectDirectory(self):
		print('here')
		dialog = QFileDialog()
		dialog.setWindowTitle("Select LC-ICPMS Directory")
		dialog.setViewMode(QFileDialog.Detail)
		self._view.homeDir = str(dialog.getExistingDirectory(self._view,"Select Directory:")) + '/'
		self._createListbox()
		self._view.integrateButtons['Calibrate'].setEnabled(True)
		self._view.integrateButtons['Load Cal.'].setEnabled(True)
		self._view.integrateButtons['115In Correction'].setEnabled(True)
		self._view.buttons['Load'].setEnabled(True)

	def _createListbox(self):
	
		test_dir = self._view.homeDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		i = 0
		for name in sorted(os.listdir(test_dir)):
			if '.csv' in name: 
				self._view.listwidget.insertItem(i, name)
				i = i + 1

		self._view.listwidget.clicked.connect(self._view.clicked)
		#listBoxLayout.addWidget(self.listwidget)
		#self.listwidget.setMaximumHeight(250)
		#self.generalLayout.addLayout(listBoxLayout)

	def _buildExpression(self, sub_exp):
		"""Build expression."""
		expression = self._view.displayText() + sub_exp
		self._view.setDisplayText(expression)

	def _clearForm(self):
		''' clears check boxes and nulls data '''
		self._view.clearChecks()
		#self._data = None
		self._view.buttons['Plot'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")

		self._intRange = []
		self._view.plotSpace.clear()
		self._n = 0
		#self._view.integrateButtons['115In Correction'].setEnabled(True)
		#self._view.normAvIndium = -999.99

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		#self._view.activeMetals.clear()
		if self._view.activeMetals == []: 
			for cbox in self._view.checkBoxes.values():
				cbox.setChecked(True)
		self._model.importData()
		self._view.buttons['Plot'].setEnabled(True)
		self._view.setDisplayText(self._view.listwidget.currentItem().text())
		#self._view.activeMetals.append('115In')
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
			print('\txmin selection: %.2f' % self._act_pos.x())
			self._model.plotLowRange(self._act_pos.x(),self._n)
			self._minAssigned = True
			
		if (cc == 2) and self._minAssigned is True:
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			print('\txmax selection: %.2f' % self._act_pos.x())
			self._model.plotHighRange(self._act_pos.x(),self._n)
			self._view.integrateButtons['Integrate'].setEnabled(True)
			self._view.integrateButtons['Integrate'].setStyleSheet("background-color: red")
			self._n = self._n + 1

		self.n_clicks = 1

	def _selectIntRange(self,checked):
		'''select integration range'''
		if self._view.intbox.isChecked() == True:
			self._view.proxy = pg.SignalProxy(self._view.chroma.scene().sigMouseClicked, rateLimit=60, slot=self._onClick)
		else:
			print(self._view.intbox.isChecked())
			self._view.proxy = None
			
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
		self._model.plotActiveMetals()
	
	def _showCalWindow(self):
		''' opens calibration window '''
		#self.dialog = Calibration(view = self._view)
		
		
		self.calWindow = Calibration(view = self._view)
		calmodel = CalibrateFunctions(calview= self.calWindow, mainview = self._view)
		CalCtrlFunctions(model=calmodel, mainview = self._view,view= self.calWindow)
		self.calWindow.show()

	def _loadCalFile(self):
		''' loads cal file and saves to self._mainview.calCurves '''
		self._view.integrateButtons['Load Cal.'].setStyleSheet("background-color: light gray")
		for root, dirs, files in os.walk(self._view.homeDir):
			for ff in files:
				if '.calib' in ff:
					calfile = os.path.join(root,ff)

		with open(calfile) as file:
			self._view.calCurves = json.load(file)

		print('Loaded calibration file: ' + calfile)

		self._view.calib_label.setText('Calibration file loaded')

	def _selectInNormFile(self):
		''' opens window to select normalization file for 115In correction; saves average 115In signal from norm file'''
		dialog = QFileDialog()
		dialog.setWindowTitle("Select Normalization File")
		dialog.setViewMode(QFileDialog.Detail)
		filepath = dialog.getOpenFileName(self._view,"Openfile")[0]
		normData = self._model.importData_generic(fdir = filepath )
		self._view.normAvIndium = np.average(normData['115In'])
		print(self._view.normAvIndium)
		self._view.integrateButtons['115In Correction'].setEnabled(False)
		

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
		self._view.integrateButtons['Calibrate'].setEnabled(False)
		self._view.integrateButtons['Load Cal.'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.integrateButtons['115In Correction'].setEnabled(False)
		
		self._view.listwidget.setCurrentItem(None)
		self._view.buttons['Directory'].clicked.connect(self._selectDirectory)
		
		self._view.buttons['Load'].clicked.connect(self._importAndActivatePlotting)
		self._view.listwidget.currentItemChanged.connect(self._importAndActivatePlotting)

		for cbox in self._view.checkBoxes.values():
			cbox.stateChanged.connect(partial( self._view.clickBox, cbox) )

		self._view.intbox.stateChanged.connect(self._selectIntRange)

		self._view.buttons['Plot'].clicked.connect(self._makePlot)
		self._view.buttons['Reset'].clicked.connect(self._clearForm)	

		self._view.integrateButtons['Calibrate'].clicked.connect(self._showCalWindow)
		self._view.integrateButtons['Load Cal.'].clicked.connect(self._loadCalFile)
		self._view.integrateButtons['Integrate'].clicked.connect(self._Integrate)
		self._view.integrateButtons['115In Correction'].clicked.connect(self._selectInNormFile)
		



