import os

import matplotlib as mpl
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas

from .. import settings


# Note: FigureCanvas is also a QWidget
class BasePlot(FigureCanvas):
    """ Base plot class for methods common to all subclass plots """

    def __str__(self):
        return "Base plot"

    def __init__(self):
        # matplotlib
        style = settings.plot.get('style')
        if style:
            if style == 'xkcd':
                mpl.pyplot.xkcd()
            else:
                mpl.style.use(style)
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

    def save_plot(self):
        """ Save the matplotlib figure
        """
        # Parse options from settings
        fname = settings.save_plot['fname']
        fformat = settings.save_plot['format']
        facecolor = settings.save_plot['facecolor']
        edgecolor = settings.save_plot['edgecolor']
        transparent = settings.save_plot['transparent']

        # Format the output path
        directory = os.path.split(fname)[0]

        # Check for file extension
        if '.' not in os.path.split(fname)[1]:
            filename = '{f}.{e}'.format(f=os.path.split(fname)[1], e=fformat)

        # Add in directory if none
        if directory == '':
            directory = '.'

        # If directory does not exist, return False
        if not os.path.exists(directory):
            return False

        # Join and save
        filename = os.path.join(directory, filename)

        self.fig.savefig(filename, format=fformat,
                         facecolor=facecolor, edgecolor=edgecolor,
                         transparent=transparent)

        return True
