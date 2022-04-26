import sys 
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial


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
		self.calDict = {}

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

	def _buildExpression(self, sub_exp):
		"""Build expression."""
		expression = self._calview.displayText() + sub_exp
		self._calview.setDisplayText(expression)
	
	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		self._model.importData()
		#self._calview.plotSpace.clear()
		self._calview.buttons['Plot'].setEnabled(True)
		self._calview.setDisplayText(self._calview.listwidget.currentItem().text())

	def _selectCalPeak(self,cbox):
		'''select integration range'''
		if cbox.isChecked() == True:
			self.current_box = cbox.text()
			#print(self._calview.intbox.isChecked())
			#print('\nselectfunct')
			#print('times through _selectIntRange: ' + str(self._n))
			#self._intRange = []
			#self._clickCounter = 0
			#print(self._intRange)
			#self._calview.chroma.scene().sigMouseMoved.connect(self._mouseover)
			#if self.n_clicks < 2:
			#self._calview.chroma.scene().sigMouseClicked.connect(self._onClick)
			self._calview.proxy = pg.SignalProxy(self._calview.chroma.scene().sigMouseClicked, rateLimit=60, slot=self._onClick)
		else:
			#print(self._calview.intbox.isChecked())
			self._calview.proxy = None
			self.current_box = None
			#self._n = 0

	def _clearForm(self):
		''' clears check boxes and nulls data '''
		self._calview.clearChecks()
		#self._data = None
		self._calview.buttons['Plot'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.plotSpace.clear()
		self.current_box = None
		self._n = 0
		print('data cleared')

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		self._model.importData()
		#self._calview.plotSpace.clear()
		self._calview.buttons['Plot'].setEnabled(True)
		self._calview.setDisplayText(self._calview.listwidget.currentItem().text())

	def _mouseover(self, pos):
		''' selects range for integration'''
		act_pos = self._calview.chroma.mapFromScene(pos)
		self._intPointX = act_pos.x()
		self._intPointY = act_pos.y()
		#print('(x,y) (' + str(act_pos.x()) + ',' + str(act_pos.y()/60) + ')')

	def _onClick(self, event):
		''' selects range for integration'''
		self._act_pos = self._calview.chroma.mapFromScene(event[0].scenePos())
		#print('\tonclick')
		#print('\tact pos: ' + str(self._act_pos.x()))
		#print('\tlen int range: ' + str(len(self._intRange)))
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
			self._calview.integrateButtons['Integrate'].setEnabled(True)
			self._calview.integrateButtons['Integrate'].setStyleSheet("background-color: red")
			self._n = self._n + 1

		self.n_clicks = 1


			
	def _Integrate(self):
		''' call integration function'''
		#print(self._xMin, self._xMax)
		#data_to_integrate = self._data
		self._model.integrate(self._intRange)
		self._intRange = []
		self._calview.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")
		self._calview.standards[self.current_box].append(self._calview.n_area )
		print(self._calview.standards)
		self.current_box = None

	def _makePlot(self):
		'''makes plot & activates integration'''
		self._model.plotActiveMetals()




	def _connectSignals(self):
		"""Connect signals and slots."""
		for btnText, btn in self._calview.buttons.items():
			if btnText  in {'Import'}:
				if self._calview.listwidget.currentItem() is None:
					text = ''
				else:
					text = self._calview.listwidget.currentItem().text()

				#btn.clicked.connect(partial(self._buildExpression, text))

		for cbox in self._calview.checkBoxes:
			cbox.stateChanged.connect(partial( self._calview.clickBox, cbox) )

		for cbox in self._calview.stdsCboxes:
			cbox.stateChanged.connect(partial(self._selectCalPeak, cbox))

		self._calview.buttons['Import'].clicked.connect(self._importAndActivatePlotting)
		self._calview.buttons['Plot'].setEnabled(False)
		self._calview.integrateButtons['Integrate'].setEnabled(False)
		self._calview.buttons['Plot'].clicked.connect(self._makePlot)
		self._calview.buttons['Reset'].clicked.connect(self._clearForm)	
		self._calview.integrateButtons['Integrate'].clicked.connect(self._Integrate)



