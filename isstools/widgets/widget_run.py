import pkg_resources
import inspect
import re
import os
import sys
from subprocess import call
from PyQt5 import uic, QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import time as ttime
import numpy as np
import datetime
from timeit import default_timer as timer
import matplotlib as mpl
from isstools.elements.figure_update import update_figure

from .widget_beamline_status import get_state

from isstools.elements.parameter_handler import parse_plan_parameters, return_parameters_from_widget
from isstools.dialogs.BasicDialogs import message_box, question_message_box


# Libs needed by the ZMQ communication
import json
import pandas as pd

timenow = datetime.datetime.now()

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_run.ui')

from isstools.xiaparser import xiaparser
from isstools.xasdata.xasdata import XASdataGeneric

class UIRun(*uic.loadUiType(ui_path)):
    def __init__(self,
                 RE,
                 plan_funcs,
                 db,
                 shutters,
                 adc_list,
                 enc_list,
                 xia,
                 html_log_func,
                 parent_gui,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.addCanvas()
        mpl.rcParams['agg.path.chunksize'] = 10000
        # TODO : remove hhm dependency


        self.plan_funcs = plan_funcs

        self.db = db
        if self.db is None:
            self.run_start.setEnabled(False)

        self.shutters = shutters
        self.adc_list = adc_list
        self.enc_list = enc_list
        self.xia = xia
        self.html_log_func = html_log_func
        self.parent_gui = parent_gui
        self.RE = RE

        self.filepaths = []
        self.xia_parser = xiaparser.xiaparser()

        self.plan_funcs = plan_funcs
        self.plan_funcs_names = plan_funcs.keys()
        self.comboBox_scan_type.addItems(self.plan_funcs_names)

        self.pushButton_scantype_help.clicked.connect(self.show_scan_help)
        self.run_start.clicked.connect(self.run_scan)
        self.comboBox_scan_type.currentIndexChanged.connect(self.populate_parameter_grid)

        # List with uids of scans created in the "run" mode:
        self.run_mode_uids = []

        self.parameter_values = []
        self.parameter_descriptions = []
        self.populate_parameter_grid(0)

    def addCanvas(self):
        self.figure = Figure()
        self.figure.set_facecolor(color='#FcF9F6')
        self.canvas = FigureCanvas(self.figure)
        self.figure.ax1 = self.figure.add_subplot(111)

        self.figure.ax2 = self.figure.ax1.twinx()
        self.figure.ax3 = self.figure.ax1.twinx()
        self.toolbar = NavigationToolbar(self.canvas, self, coordinates=True)
        self.toolbar.setMaximumHeight(25)
        self.plots.addWidget(self.toolbar)
        self.plots.addWidget(self.canvas)
        self.figure.ax3.grid(alpha = 0.4)
        self.canvas.draw_idle()

    def run_scan(self):
        sys.stdout = self.parent_gui.emitstream_out
        ignore_shutter = False


        for shutter in [self.shutters[shutter] for shutter in self.shutters if
                        self.shutters[shutter].shutter_type != 'SP']:
            shutter_state = get_state(shutter)
            if shutter_state != 'Open':
                ret = self.questionMessage('Shutter closed',
                                           'Would you like to run the scan with the shutter closed?')
                if not ret:
                    print('Aborted!')
                    return False
                ignore_shutter = True
                break

        name_provided = self.parameter_values[0].text()
        if name_provided:
            if self.parent_gui.hutch == 'c':
                for indx, description in enumerate(self.parameter_descriptions):
                    if description.text().startswith('hutch'):
                        self.parameter_values[indx].setChecked(True)                        
            elif self.parent_gui.hutch == 'b':
                for indx, description in enumerate(self.parameter_descriptions):
                    if description.text().startswith('hutch'):
                        self.parameter_values[indx].setChecked(False)                        
            timenow = datetime.datetime.now()
            print('\nStarting scan at {}'.format(timenow.strftime("%H:%M:%S"), flush='true'))
            start_scan_timer = timer()

            # Get parameters from the widgets and organize them in a dictionary (run_params)
            run_parameters = return_parameters_from_widget(self.parameter_descriptions, self.parameter_values,
                                                           self.parameter_types)

            # Run the scan using the dict created before
            self.run_mode_uids = []
            plan_key = self.comboBox_scan_type.currentText()
            plan_func = self.plan_funcs[plan_key]

            RE_args = [plan_func(**run_parameters,
                                 ignore_shutter=ignore_shutter,
                                 )]


            self.run_mode_uids = self.RE(*RE_args)

            timenow = datetime.datetime.now()
            print('Scan complete at {}'.format(timenow.strftime("%H:%M:%S")))
            stop_scan_timer = timer()
            print('Scan duration {} s'.format(stop_scan_timer - start_scan_timer))


        else:
            message_box('Error', 'Please provide the name for the scan')

    def show_scan_help(self):
        title = self.run_type.currentText()
        message = self.plan_funcs[self.run_type.currentIndex()].__doc__
        QtWidgets.QMessageBox.question(self,
                                       'Help! - {}'.format(title),
                                       message,
                                       QtWidgets.QMessageBox.Ok)

    def create_log_scan(self, uid, figure):
        self.canvas.draw_idle()
        if self.html_log_func is not None:
            self.html_log_func(uid, figure)

    def populate_parameter_grid(self, index):
        for i in range(len(self.parameter_values)):
            self.gridLayout_parameters.removeWidget(self.parameter_values[i])
            self.gridLayout_parameters.removeWidget(self.parameter_descriptions[i])
            self.parameter_values[i].deleteLater()
            self.parameter_descriptions[i].deleteLater()

        plan_key = self.comboBox_scan_type.currentText()
        plan_func = self.plan_funcs[plan_key]
        [self.parameter_values, self.parameter_descriptions, self.parameter_types] = parse_plan_parameters(plan_func)

        for i in range(len(self.parameter_values)):
            self.gridLayout_parameters.addWidget(self.parameter_values[i], i, 0, QtCore.Qt.AlignTop)
            self.gridLayout_parameters.addWidget(self.parameter_descriptions[i], i, 1, QtCore.Qt.AlignTop)




    def addParamControl(self, name, default, annotation, grid, params):
        rows = int((grid.count()) / 3)
        param1 = QtWidgets.QLabel(str(rows + 1))

        param2 = None
        def_val = ''
        if default.find('=') != -1:
            def_val = re.sub(r'.*=', '', default)
        if annotation == int:
            param2 = QtWidgets.QSpinBox()
            param2.setMaximum(100000)
            param2.setMinimum(-100000)
            def_val = int(def_val)
            param2.setValue(def_val)
        elif annotation == float:
            param2 = QtWidgets.QDoubleSpinBox()
            param2.setMaximum(100000)
            param2.setMinimum(-100000)
            def_val = float(def_val)
            param2.setValue(def_val)
        elif annotation == bool:
            param2 = QtWidgets.QCheckBox()
            if def_val == 'True':
                def_val = True
            else:
                def_val = False
            param2.setCheckState(def_val)
            param2.setTristate(False)
        elif annotation == str:
            param2 = QtWidgets.QLineEdit()
            def_val = str(def_val)
            param2.setText(def_val)

        if param2 is not None:
            param3 = QtWidgets.QLabel(default)
            grid.addWidget(param1, rows, 0, QtCore.Qt.AlignTop)
            grid.addWidget(param2, rows, 1, QtCore.Qt.AlignTop)
            grid.addWidget(param3, rows, 2, QtCore.Qt.AlignTop)
            params[0].append(param1)
            params[1].append(param2)
            params[2].append(param3)

    def questionMessage(self, title, question):
        reply = QtWidgets.QMessageBox.question(self, title,
                                               question,
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            return True
        elif reply == QtWidgets.QMessageBox.No:
            return False
        else:
            return False

    def setAnalogSampTime(self, text):
        self.analog_samp_time = text

    def setEncSampTime(self, text):
        self.enc_samp_time = text

    def setXiaSampTime(self, text):
        self.xia_samp_time = text


    def draw_interpolated_data(self, df):
        old = np.seterr(invalid='ignore')
        update_figure([self.figure.ax2, self.figure.ax1, self.figure.ax3], self.toolbar, self.canvas)
        if 'i0' in df and 'it' in df and 'energy' in df:
            transmission = np.nan_to_num(np.log(np.nan_to_num(np.array(df['i0'])/np.array(df['it']))))
            # transmission = np.array(np.log(df['i0'] / df['it']))

        if 'i0' in df and 'pips' in df and 'energy' in df:
            fluorescence = np.nan_to_num(np.array(df['pips']) / np.array(df['i0']))

            # fluorescence = np.array(df['pips'] / df['i0'])
        if 'i0' in df and 'iff' in df and 'energy' in df:
            fluorescence = np.nan_to_num(np.array(df['iff'])/np.array(df['i0']))

            # fluorescence = np.array(df['iff'] / df['i0'])
        if 'it' in df and 'ir' in df and 'energy' in df:
            reference = np.nan_to_num(np.log(np.nan_to_num(np.array(df['it']) / np.array(df['ir']))))
            reference = np.array(np.log(df['it'] / df['ir']))

        energy = np.array(df['energy'])
        edge = int(len(energy) * 0.02)

        self.figure.ax1.plot(energy[edge:-edge], transmission[edge:-edge], color='r', label='Transmission')
        self.figure.ax1.legend(loc=2)
        self.figure.ax2.plot(energy[edge:-edge], fluorescence[edge:-edge], color='g', label='Total fluorescence')
        self.figure.ax2.legend(loc=1)
        self.figure.ax3.plot(energy[edge:-edge], reference[edge:-edge], color='b', label='Reference')
        self.figure.ax3.legend(loc=3)
        self.canvas.draw_idle()
