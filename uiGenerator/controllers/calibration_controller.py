import sys 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd


__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
control for calibration 

2022-04-21
Christian Dewey
'''


# Create a Controller class to connect the GUI and the model
class CalCtrlFunctions:
	"""PyCalc Controller class."""
	def __init__(self, model, view, mainview):
		"""Controller initializer."""
		self._model = model
		self._calview = view
		self._mainview = mainview

		self.calibrationDir = self._calview.calibrationDir
		self._intRange = []
		self.n_clicks = 0
		self._n = 0
		self._xMin = 0
		self._xMax = 0
		self.button_is_checked = False
		self.calibrationDir = ''
		
		# Connect signals and slots
		self._connectSignals()

	def _selectDirectory(self):
		dialog = QFileDialog()
		dialog.setWindowTitle("Select Calibration Directory")
		dialog.setViewMode(QFileDialog.ViewMode.Detail)
		self._calview.calibrationDir = str(dialog.getExistingDirectory(self._calview,"Select Directory:")) + '/'
		print(self._calview.calibrationDir)
		self._createListbox()
	
	def _createListbox(self):
	
		test_dir = self._calview.calibrationDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
		i = 0
		for name in sorted(os.listdir(test_dir)):
			if '.csv' in name: 
				self._calview.listwidget.insertItem(i, name)
				i = i + 1

		self._calview.listwidget.clicked.connect(self._calview.clicked)
		#listBoxLayout.addWidget(self.listwidget)
		#self.listwidget.setMaximumHeight(250)
		#self.generalLayout.addLayout(listBoxLayout)
	
	def _buildExpression(self, sub_exp):
		"""Build expression."""
		expression = self._calview.displayText() + sub_exp
		self._calview.setDisplayText(expression)
	
	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		self._model.importData()
		#self._calview.buttons['Plot'].setEnabled(True)
		self._calview.setDisplayText(self._calview.listwidget.currentItem().text())

	def _selectCalPeak(self,rbutton):
		'''select integration range'''
		if rbutton.isChecked() == True:
			self.currentStd = rbutton.text()
			self._calview.proxy = pg.SignalProxy(self._calview.chroma.scene().sigMouseClicked, rateLimit=60, slot=self._onClick)
		else:
			self._view.proxy = None
		

	def _clearForm(self):
		''' clears check boxes and nulls data '''
		self._calview.integrateButtons['Enter'].setEnabled(False)
		self._calview.integrateButtons['Enter'].setStyleSheet("background-color: light gray")
		self._calview.stdConcEntry.clear()
		self._mainview.activeElements.clear()
		self._mainview.calCurves = {}
		self._calview.plotSpace.clear()
		self.currentStd = None
		for k in self._calview.standards.keys(): self._calview.standards[k] = []
		self._n = 0
		for rbutton in self._calview.stdsRadioButtons.values():
			rbutton.setCheckable(True)
			rbutton.setEnabled(True)
		print('data cleared')

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		self._model.importData()
		self._calview.setDisplayText(self._calview.listwidget.currentItem().text())
		self._model.plotActiveElements()

	def _mouseover(self, pos):
		''' selects range for integration'''
		act_pos = self._calview.chroma.mapFromScene(pos)
		self._intPointX = act_pos.x()
		self._intPointY = act_pos.y()

	def _onClick(self, event):
		''' selects range for integration'''
		self._act_pos = self._calview.chroma.mapFromScene(event[0].scenePos())
		cc = len(self._intRange)
		cc = cc + 1
		
		if cc == 1: 
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			print('\txmin selection: '+str(self._act_pos.x()))
			self._model.plotLowRange(self._act_pos.x(),self._n)
			self._minAssigned = True
			
		if (cc == 2) and self._minAssigned is True:
			self._intRange.append(self._act_pos.x()) #.x() / 60 # in minutes
			print('\txmax selection: '+str(self._act_pos.x()))
			self._model.plotHighRange(self._act_pos.x(),self._n)
			self._calview.integrateButtons['Enter'].setEnabled(True)
			self._calview.integrateButtons['Enter'].setStyleSheet("background-color: red")
			self._n = self._n + 1

		self.n_clicks = 1

			
	def _Integrate(self):
		''' call integration function'''
		print(self._calview.stdConcEntry.text())
		if self._calview.stdConcEntry.text() != '':
			self._model.integrate(self._intRange)
			self._intRange = []
			self._calview.integrateButtons['Enter'].setStyleSheet("background-color: light gray")
			self._calview.stdConcEntry.setStyleSheet("background-color: light gray")
			self._calview.standards[self.currentStd].append(self._calview.n_area )
			print(self._calview.standards)

			self.getStdConc()

			self._calview.integrateButtons['Enter'].setEnabled(False)
		else:
			self._calview.stdConcEntry.setStyleSheet("background-color: yellow")
	def _clearPlot(self):
		''' clears plot area'''
		self._calview.plotSpace.clear()

	def getStdConc(self):
		print(self.currentStd)
		stdConc = self._calview.stdConcEntry.text()
		self._calview.standards[self.currentStd].append(float(stdConc))
		self._calview.stdConcEntry.clear()
		print(self._calview.standards)
		print('here',self.currentStd)
		self._calview.stdsRadioButtons[self.currentStd].setCheckable(False)
		self._calview.stdsRadioButtons[self.currentStd].setEnabled(False)

	def _makePlot(self):
		'''makes plot & activates integration'''
		self._model.plotActiveElements()


	def _calcCurve(self):
		self._model.calcLinearRegression()

	def _connectSignals(self):
		"""Connect signals and slots."""
		for btnText, btn in self._calview.buttons.items():
			if btnText  in {'Plot'}:
				if self._calview.listwidget.currentItem() is None:
					text = ''
				else:
					text = self._calview.listwidget.currentItem().text()

				btn.clicked.connect(partial(self._buildExpression, text))

		self._calview.buttons['Directory'].clicked.connect(self._selectDirectory)
		for rbutton in self._calview.stdsRadioButtons.values():
			rbutton.toggled.connect(partial(self._selectCalPeak, rbutton) )

		self._calview.listwidget.currentItemChanged.connect(self._importAndActivatePlotting)
		self._calview.integrateButtons['Enter'].setEnabled(False)
		self._calview.buttons['Reset'].clicked.connect(self._clearForm)
		self._calview.buttons['Clear Plot'].clicked.connect(self._clearPlot)
		self._calview.integrateButtons['Enter'].clicked.connect(self._Integrate)
		self._calview.integrateButtons['Calculate Curve'].clicked.connect(self._calcCurve)



