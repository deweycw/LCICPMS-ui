import sys 
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial
import lcicpms_classes as icpms

__version__ = '0.1'
__author__ = 'Christian Dewey'

'''
LCICPMS data GUI

2022-04-21
programming/lcicpms-ui/env/bin/python3 -c "import PyQt5"
Christian Dewey
'''

# Create a subclass of QMainWindow to setup the calculator's GUI
class PyLCICPMSUi(QMainWindow):
    """PyCalc's View (GUI)."""
    def __init__(self):
        """View initializer."""
        super().__init__()
        # Set some main window's properties
        self.setWindowTitle('PyCalc')
        self.setFixedSize(500, 535)
        # Set the central widget
        self.generalLayout = QVBoxLayout()
        self.topLayout = QFormLayout()
        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.generalLayout)

        self.homeDir = '/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
        self.activeMetals = []
        self.metalOptions = ['55Mn','56Fe','59Co','60Ni','63Cu','66Zn','111Cd','208Pb']
        # Create the display and the buttons
        self._createDirEntry()
        self._createButtons()
        self._createListbox()
        self._createCheckBoxes()
        self._createDisplay()

    def _createDirEntry(self):
        self.DirEntry = QLineEdit()
        self.DirEntry.setFixedHeight(35)
        self.DirEntry.setAlignment(Qt.AlignRight)
        self.topLayout.addRow("Enter directory:", self.DirEntry)

    def _createDisplay(self):
        '''Create the display'''
        # Create the display widget
        self.display = QLineEdit()
        self.display.setFixedHeight(35)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        self.generalLayout.addWidget(self.display)


    def _createCheckBoxes(self):
        # Add some checkboxes to the layout  
        self.checkBoxes = []      
        optionsLayout = QHBoxLayout()
        for m in self.metalOptions:
            cbox = QCheckBox(m)
            self.checkBoxes.append(cbox)
            optionsLayout.addWidget(cbox)
       # optionwidget.stateChanged.connect(self.clickBox)
        self.generalLayout.addLayout(optionsLayout)

    def _createListbox(self):
        '''Create listbox'''
        listBoxLayout = QGridLayout()
        self.listwidget = QListWidget()

        test_dir = self.homeDir #'/Users/christiandewey/presentations/DOE-PI-22/day6/day6/'
        i = 0
        for name in os.listdir(test_dir):
            if '.csv' in name: 
                self.listwidget.insertItem(i, name)
                i = i + 1

        self.listwidget.clicked.connect(self.clicked)
        listBoxLayout.addWidget(self.listwidget)
        self.generalLayout.addLayout(listBoxLayout)

    def _createButtons(self):
        """Create the buttons."""
        self.buttons = {}
        buttonsLayout = QGridLayout()
        # Button text | position on the QGridLayout
        buttons = {'Import': (0, 0),
                   'Plot': (0, 1),
                   'Reset': (0, 2),
                  }
        # Create the buttons and add them to the grid layout
        for btnText, pos in buttons.items():
            self.buttons[btnText] = QPushButton(btnText)
            self.buttons[btnText].setFixedSize(80, 40)
            buttonsLayout.addWidget(self.buttons[btnText], pos[0], pos[1])
        # Add buttonsLayout to the general layout
        self.generalLayout.addLayout(buttonsLayout)
    
    def clicked(self):
        item = self.listwidget.currentItem()
        print('clicked: ' + item.text())
        return self.listwidget.currentItem()
    
    def setDisplayText(self, text):
        """Set display's text."""
        self.display.setText(text)
        self.display.setFocus()

    def displayText(self):
        """Get display's text."""
        return self.display.text()

    def clearChecks(self):
        """Clear the display."""
        for cbox in self.checkBoxes:
            cbox.setCheckState(Qt.Unchecked)

    def clickBox(self, cbox, state):
        if state == Qt.Checked:
            print('checked: ' + cbox.text())
            self.activeMetals.append(cbox.text())
            print(self.activeMetals)
            return self.activeMetals
        elif state == Qt.Unchecked:
            print('Unchecked: ' + cbox.text())
            self.activeMetals.remove(cbox.text())
            print(self.activeMetals)
            return self.activeMetals
        else:
            print('Unchecked')
            return self.activeMetals



# Create a Controller class to connect the GUI and the model
class PyLCICPMSCtrl:
    """PyCalc Controller class."""
    def __init__(self, model, view):
        """Controller initializer."""
        self._model = model
        self._view = view
        self._data = None
        # Connect signals and slots
        self._connectSignals()

    def _buildExpression(self, sub_exp):
        """Build expression."""
        expression = self._view.displayText() + sub_exp
        self._view.setDisplayText(expression)

    def _clearForm(self):
        ''' clears check boxes and nulls data '''
        self._view.clearChecks()
        self._data = None
        self._view.buttons['Plot'].setEnabled(False)
        print('data cleared')

    def _importAndActivatePlotting(self):
        '''activates plotting function after data imported'''
        self._model.importData()
        self._view.buttons['Plot'].setEnabled(True)
        self._view.setDisplayText(self._view.listwidget.currentItem().text())

    def _connectSignals(self):
        """Connect signals and slots."""
        for btnText, btn in self._view.buttons.items():
            if btnText  in {'Import'}:
                if self._view.listwidget.currentItem() is None:
                    text = ''
                else:
                    text = self._view.listwidget.currentItem().text()

                btn.clicked.connect(partial(self._buildExpression, text))
            #if btnText in {'Plot'}:
            #    btn.clicked.connect(self._importData)
            #elif btnText in {'Reset'}:
            #    btn.clicked.connect(self._view.clearChecks)
            #    print('here22')


        for cbox in self._view.checkBoxes:
            cbox.stateChanged.connect(partial( self._view.clickBox, cbox) )

        

       # for l in self._view.listwidget
        
        #self._view.setDisplayText(testindex)

        #if self._view.listwidget.currentItem() is not None:
        self._view.buttons['Import'].clicked.connect(self._importAndActivatePlotting)
        self._view.buttons['Plot'].setEnabled(False)
        self._view.buttons['Plot'].clicked.connect(self._model.plotActiveMetals)
        self._view.buttons['Reset'].clicked.connect(self._clearForm)
        #if self._data is not None:
        #    testindex = self._data.iloc[0,1]
        #    self._view.setDisplayText(testindex)

class LICPMSfunctions:
    ''' model class for LCICPMS functions'''
    def __init__(self, view):
        """Controller initializer."""
        self._view = view
        
    def importData(self):
        '''imports LCICPMS .csv file'''
    #if self._view.listwidget.currentItem() is not None:
        #fdir = self._view.homeDir + self._view.listwidget.currentItem()
        print(self._view.listwidget.currentItem().text())
        fdir = self._view.homeDir + self._view.listwidget.currentItem().text()
        #df = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)
        self._data = pd.read_csv(fdir,sep=';',skiprows = 0, header = 1)
        testindex = self._data
        print(testindex)
    #self._view.setDisplayText(str(testindex))

    def plotActiveMetals(self):
        '''plots active metals for selected file'''
        activeMetalsPlot = icpms.ICPMS_Data_Class(self._data,self._view.activeMetals)
        activeMetalsPlot.chroma().show()

# Client code
def main():
    """Main function."""
    # Create an instance of QApplication
    pycalc = QApplication(sys.argv)
    # Show the calculator's GUI
    view = PyLCICPMSUi()
    model = LICPMSfunctions(view = view)
    view.show()

    # Create instances of the model and the controller
    PyLCICPMSCtrl(model=model, view=view)
    # Execute the calculator's main loop
    sys.exit(pycalc.exec_())

if __name__ == '__main__':
    main()