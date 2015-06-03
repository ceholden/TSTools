import os

import matplotlib as mpl
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas

from tstools import settings


# Note: FigureCanvas is also a QWidget
class BasePlot(FigureCanvas):

    def setup_plots(self):
        # matplotlib
        mpl.style.use('ggplot')
        self.fig = mpl.figure.Figure()
        self.axes = self.fig.add_subplot(111)

        FigureCanvas.__init__(self, self.fig)

        self.setAutoFillBackground(False)
        self.axes.set_ylim([0, 10000])
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
