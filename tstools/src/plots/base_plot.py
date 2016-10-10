""" Base class that sets up plots for TSTools
"""
import os

import matplotlib as mpl
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas
HAS_STYLE = True
try:
    import matplotlib.style
except ImportError:
    HAS_STYLE = False

from .. import settings


# Note: FigureCanvas is also a QWidget
class BasePlot(FigureCanvas):
    """ Base plot class for methods common to all subclass plots """

    def __str__(self):
        return "Base plot"

    def __init__(self):
        # Location of pixel plotted
        self.title = ''

        # matplotlib
        style = settings.plot.get('style')
        if HAS_STYLE and style:
            if style == 'xkcd':
                import matplotlib.pyplot
                mpl.pyplot.xkcd()
            else:
                matplotlib.style.use(style)
        self.fig = mpl.figure.Figure()
        self.axes = []
        self.axis_1 = self.fig.add_subplot(111)
        self.axes.append(self.axis_1)

        FigureCanvas.__init__(self, self.fig)

        self.setAutoFillBackground(False)
        self.fig.tight_layout()

    def plot(self):
        raise NotImplementedError('Subclass must implement `plot`')

    def update_plot(self):
        raise NotImplementedError('Subclass must implement `update_plot`')
