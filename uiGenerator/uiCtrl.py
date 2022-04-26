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
LCICPMS data GUI

2022-04-21
Christian Dewey
'''


# Create a Controller class to connect the GUI and the model
class PyLCICPMSCtrl:
	"""PyCalc Controller class."""
	def __init__(self, model, view):
		"""Controller initializer."""
		self._model = model
		self._view = view
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
		self._view.plotSpace.clear()
		self._n = 0
		print('data cleared')

	def _importAndActivatePlotting(self):
		'''activates plotting function after data imported'''
		self._model.importData()
		#self._view.plotSpace.clear()
		self._view.buttons['Plot'].setEnabled(True)
		self._view.setDisplayText(self._view.listwidget.currentItem().text())

	def _mouseover(self, pos):
		''' selects range for integration'''
		act_pos = self._view.chroma.mapFromScene(pos)
		self._intPointX = act_pos.x()
		self._intPointY = act_pos.y()
		#print('(x,y) (' + str(act_pos.x()) + ',' + str(act_pos.y()/60) + ')')

	def _onClick(self, event):
		''' selects range for integration'''
		self._act_pos = self._view.chroma.mapFromScene(event[0].scenePos())
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
			self._view.integrateButtons['Integrate'].setEnabled(True)
			self._view.integrateButtons['Integrate'].setStyleSheet("background-color: red")
			self._n = self._n + 1

		self.n_clicks = 1

	def _selectIntRange(self,checked):
		'''select integration range'''
		if self._view.intbox.isChecked() == True:
			print(self._view.intbox.isChecked())
			#print('\nselectfunct')
			#print('times through _selectIntRange: ' + str(self._n))
			#self._intRange = []
			#self._clickCounter = 0
			#print(self._intRange)
			#self._view.chroma.scene().sigMouseMoved.connect(self._mouseover)
			#if self.n_clicks < 2:
			#self._view.chroma.scene().sigMouseClicked.connect(self._onClick)
			self._view.proxy = pg.SignalProxy(self._view.chroma.scene().sigMouseClicked, rateLimit=60, slot=self._onClick)
		else:
			print(self._view.intbox.isChecked())
			self._view.proxy = None
			#self._n = 0
			
	def _Integrate(self):
		''' call integration function'''
		#print(self._xMin, self._xMax)
		#data_to_integrate = self._data
		self._model.integrate(self._intRange)
		self._intRange = []
		self._view.integrateButtons['Integrate'].setStyleSheet("background-color: light gray")

	def _makePlot(self):
		'''makes plot & activates integration'''
		self._model.plotActiveMetals()

	def _connectSignals(self):
		"""Connect signals and slots."""
		for btnText, btn in self._view.buttons.items():
			if btnText  in {'Import'}:
				if self._view.listwidget.currentItem() is None:
					text = ''
				else:
					text = self._view.listwidget.currentItem().text()

				btn.clicked.connect(partial(self._buildExpression, text))

		for cbox in self._view.checkBoxes:
			cbox.stateChanged.connect(partial( self._view.clickBox, cbox) )

		self._view.intbox.stateChanged.connect(self._selectIntRange)

		self._view.buttons['Import'].clicked.connect(self._importAndActivatePlotting)
		self._view.buttons['Plot'].setEnabled(False)
		self._view.integrateButtons['Integrate'].setEnabled(False)
		self._view.buttons['Plot'].clicked.connect(self._makePlot)
		self._view.buttons['Reset'].clicked.connect(self._clearForm)	
		self._view.integrateButtons['Integrate'].clicked.connect(self._Integrate)



