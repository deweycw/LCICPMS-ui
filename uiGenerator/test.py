import sys 
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import * 
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import os
import pandas as pd
from functools import partial
import seaborn as sns
from sklearn import  linear_model
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import numpy as np

pas = [0.10140832152037953, 0.21666795284382942, 0.3399643531510066, 0.5734846379738416, 1.019680843026314]

concs = [0.0, 25.0, 50.0, 100.0, 200.0]


X = np.array(pas).reshape(-1, 1)
y = np.array(concs)
print(X)
print(y)
regr = linear_model.LinearRegression()
regr.fit(X, y)
#x_test = np.arange(0,500,0.1).reshape(-1, 1)
y_pred = regr.predict(X)
# Print the Intercept:
print('Intercept:', regr.intercept_)

# Print the Slope:
print('Slope:', regr.coef_) 
# The mean squared error
mse = mean_squared_error(y, y_pred)
print("Mean squared error: %.2f" % mse)
# The coefficient of determination: 1 is perfect prediction
n = 3 # obs
p = 1 # num ind vars
r2 = r2_score(y, y_pred)
#r2 = regr.score(X,y)
adjR2 = 1 - (1-r2_score(X, y)) * ( (n-1) / (n-p-1))
print("R-squared: %.4f" % r2)

#calCurve_dict[m] = [regr,(mean_squared_error(pas, concs),r2_score(pas, concs))]

plt.scatter(X, y, color="black")
plt.plot(X, y_pred, color="blue", linewidth=3)

plt.xticks(())
plt.yticks(())

plt.show()