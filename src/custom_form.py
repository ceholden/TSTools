# -*- coding: utf-8 -*
# vim: set expandtab:ts=4
"""
/***************************************************************************
 CCDCToolsDialog
                                 A QGIS plugin
 Plotting & visualization tools for CCDC Landsat time series analysis
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Chris Holden
        email                : ceholden@bu.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import copy

import numpy as np

from PyQt4.QtCore import * # TODO remove *
from PyQt4.QtGui import * #TODO

def list_repr(l):
    """ custom string repr for a list or numpy array using commas """
    # handle 2d arrays
    if isinstance(l, np.ndarray):
        if len(l.shape) > 1:
            l = l[0]

    return ', '.join(map(repr, l))


def str2list(s, dtype):
    """ return list parsed from space, or comma, separated string """
    l = [_s for _s in s.replace(',', ' ').split(' ') if _s != '']
    return map(dtype, l)


class CustomForm(QWidget):
    """ Easily creates a form in FormLayoutfrom a dict of names and
    example data

    Class is heavily inspired by "formlayout" module by Pierre Raybut
        See: https://code.google.com/p/formlayout/
    """

    def __init__(self, defaults, title=None, parent=None):
        QWidget.__init__(self, parent)

        # validate input data
        if not isinstance(defaults, dict):
            raise ValueError('Input data is not dict')
        else:
            if len(defaults) == 0:
                raise ValueError('Input data has no elements')

        # copy over data
        self.defaults = copy.deepcopy(defaults)
        self.last_known_good = copy.deepcopy(defaults)
        self.title = title

        # list to store corresponding widgets
        self.widgets = []
        # store layout
        self.form_layout = QFormLayout(self)

        self.init_form()

    def init_form(self):
        """ Loop through input data initializing widgets """

        if self.title:
            self.form_layout.addRow(QLabel('<b>' + self.title + '</b>'))
            self.form_layout.addRow(QLabel(''))

        for name, value in self.defaults.itervalues():
            # int
            if isinstance(value, int) and not isinstance(value, bool):
                field = QLineEdit(repr(value), self)
                field.setValidator(QIntValidator(field))
            # float
            elif isinstance(value, float):
                field = QLineEdit(repr(value), self)
                field.setValidator(QDoubleValidator(field))
            # string
            elif isinstance(value, str):
                field = QLineEdit(value, self)
            # list or numpy array
            elif isinstance(value, list) or isinstance(value, np.ndarray):
                field = QLineEdit(list_repr(value))
            # boolean
            elif isinstance(value, bool):
                field = QCheckBox(self)
                field.setCheckState(QtChecked if value else Qt.Unchecked)
            # blank space
            elif name is None and value is None:
                self.form_layout.addRow(QLabel(''), QLabel(''))
                self.widgets.append(None)
                field = None
            # comment / section header
            elif value is None:
                self.form_layout.addRow(QLabel(value))
                self.widgets.append(None)
                field = None
            else:
                print '{f} - UNRECOGNIZED CUSTOM FORM GIVEN'.format(f=__file__)
                field = None

            if field is not None:
                self.form_layout.addRow(name, field)
                self.widgets.append(field)

        self.error_label = QLabel('')
        self.form_layout.addRow(self.error_label)

    def get(self):
        """ Loop through widgets returning current data from widgets as list """
        values = []

        for i, (name, default) in enumerate(self.defaults.itervalues()):
            field = self.widgets[i]
            # int
            if isinstance(default, int) and not isinstance(default, bool):
                value = int(field.text())
            # float
            elif isinstance(default, float):
                value = float(field.text())
            # string
            elif isinstance(default, str):
                value = str(field.text())
            # list or numpy array
            elif isinstance(default, list) or isinstance(default, np.ndarray):
                # lists and 1d np.arrays
                if isinstance(default[0], int):
                    value = str2list(field.text(), int)
                elif isinstance(default[0], float):
                    value = str2list(field.text(), float)
                # 2d np.arrays
                elif isinstance(default[0], np.ndarray):
                    if isinstance(default[0][0], int):
                        value = np.array([str2list(field.text(), int)])
                    elif isinstance(default[0][0], float):
                        value = np.array([str2list(field.text(), float)])
                # turn 1d np.array back into np.array
                if isinstance(default, np.ndarray) and len(default.shape) == 1:
                    value = np.array(value)
            # boolean
            elif isinstance(default, bool):
                value = field.checkState() == Qt.Checked
            # blank space
            elif name is None or default is None:
                value = None
            # unsupported field
            else:
                value = None

            values.append(value)

        return values

    def set(self, values):
        """ Set values """
        for i, (name, value) in enumerate(values.itervalues()):
            field = self.widgets[i]
            # int
            if isinstance(value, int) and not isinstance(value, bool):
                field.setText(str(value))
            # float
            elif isinstance(value, float):
                field.setText(str(value))
            # string
            elif isinstance(value, str):
                field.setText(value)
            # list or numpy array
            elif isinstance(value, list) or isinstance(value, np.ndarray):
                field.setText(list_repr(value))
            # boolean
            elif isinstance(value, bool):
                field.setCheckState(QtChecked if value else Qt.Unchecked)
            # blank space / comment / section header
            elif name is None or value is None:
                continue
            else:
                print '{f} - UNRECOGNIZED CUSTOM FORM GIVEN'.format(f=__file__)

        self.last_known_good = copy.deepcopy(values)

    def reset(self):
        """ Reset to last known good values

        "Good" value determined by successful set
        """
        self.set(self.last_known_good)

    def push_error(self, text):
        """ Add error message """
        self.error_label.setText('<b>' + text + '</b>')
