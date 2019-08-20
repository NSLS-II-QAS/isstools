import pkg_resources
import inspect
import re
import os
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



# Libs needed by the ZMQ communication
import json
import pandas as pd

timenow = datetime.datetime.now()

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_run.ui')

from isstools.xiaparser import xiaparser
from isstools.xasdata.xasdata import XASdataGeneric

class UIRun(*uic.loadUiType(ui_path)):
    def __init__(self,
                 plan_funcs,
                 RE,
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
        self.plan_funcs_names = plan_funcs.keys()
        self.db = db
        self.RE = RE
        if self.db is None:
            self.run_start.setEnabled(False)

        self.shutters = shutters
        self.adc_list = adc_list
        self.enc_list = enc_list
        self.xia = xia
        self.html_log_func = html_log_func
        self.parent_gui = parent_gui

        self.filepaths = []

        self.comboBox_scan_type.addItems(self.plan_funcs_names)

        self.comboBox_scan_type.currentIndexChanged.connect(self.populateParams)

        self.run_start.clicked.connect(self.run_scan)


        # List with uids of scans created in the "run" mode:
        self.run_mode_uids = []

        self.params1 = []
        self.params2 = []
        self.params3 = []
        if len(self.plan_funcs) != 0:
            self.populateParams(0)

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
        ignore_shutter=False

        # Send sampling time to the pizzaboxes:
        value = int(round(float(self.analog_samp_time) / self.adc_list[0].sample_rate.value * 100000))

        for adc in self.adc_list:
            adc.averaging_points.put(str(value))

        for enc in self.enc_list:
            enc.filter_dt.put(float(self.enc_samp_time) * 100000)

        self.comment = self.params2[0].text()
        if (self.comment):
            timenow = datetime.datetime.now()
            print('\nStarting scan at {}'.format(timenow.strftime("%H:%M:%S")))
            start_scan_timer=timer()
            
            # Get parameters from the widgets and organize them in a dictionary (run_params)
            run_params = {}
            for i in range(len(self.params1)):
                if (self.param_types[i] == int):
                    run_params[self.params3[i].text().split('=')[0]] = self.params2[i].value()
                elif (self.param_types[i] == float):
                    run_params[self.params3[i].text().split('=')[0]] = self.params2[i].value()
                elif (self.param_types[i] == bool):
                    run_params[self.params3[i].text().split('=')[0]] = bool(self.params2[i].checkState())
                elif (self.param_types[i] == str):
                    run_params[self.params3[i].text().split('=')[0]] = self.params2[i].text()

            # Erase last graph
            self.figure.ax1.clear()
            #self.figure.ax2.clear()
            #self.figure.ax3.clear()
            self.toolbar.update()
            self.canvas.draw_idle()
            #self.figure.ax3.grid(alpha = 0.4)
            
            # Run the scan using the dict created before
            self.run_mode_uids = []
            self.parent_gui.run_mode = 'run'
            plan_func = self.plan_funcs[self.comboBox_scan_type.currentText()]
            self.run_mode_uids = self.RE(plan_func(**run_params,
                                                   ax=self.figure.ax1,
                                                   ignore_shutter=ignore_shutter,
                                                   stdout=self.parent_gui.emitstream_out))
            timenow = datetime.datetime.now()
            print('Scan complete at {}'.format(timenow.strftime("%H:%M:%S")))
            stop_scan_timer = timer()
            print('Scan duration {} s'.format(stop_scan_timer - start_scan_timer))

            timenow = datetime.datetime.now()    
            print('Scan complete at {}'.format(timenow.strftime("%H:%M:%S")))
            stop_scan_timer=timer()  
            print('Scan duration {}'.format(stop_scan_timer-start_scan_timer))

        else:
            print('\nPlease, type the name of the scan in the field "name"\nTry again')



    def create_log_scan(self, uid, figure):
        self.canvas.draw_idle()
        if self.html_log_func is not None:
            self.html_log_func(uid, figure)

    def populateParams(self, index):
        for i in range(len(self.params1)):
            self.gridLayout_13.removeWidget(self.params1[i])
            self.gridLayout_13.removeWidget(self.params2[i])
            self.gridLayout_13.removeWidget(self.params3[i])
            self.params1[i].deleteLater()
            self.params2[i].deleteLater()
            self.params3[i].deleteLater()
        self.params1 = []
        self.params2 = []
        self.params3 = []
        self.param_types = []
        plan_func = self.plan_funcs[self.comboBox_scan_type.currentText()]

        signature = inspect.signature(plan_func)
        for i in range(0, len(signature.parameters)):
            default = re.sub(r':.*?=', '=', str(signature.parameters[list(signature.parameters)[i]]))
            if default == str(signature.parameters[list(signature.parameters)[i]]):
                default = re.sub(r':.*', '', str(signature.parameters[list(signature.parameters)[i]]))
            self.addParamControl(list(signature.parameters)[i], default,
                                 signature.parameters[list(signature.parameters)[i]].annotation,
                                 grid=self.gridLayout_13, params=[self.params1, self.params2, self.params3])
            self.param_types.append(signature.parameters[list(signature.parameters)[i]].annotation)

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
        update_figure([self.figure.ax2, self.figure.ax1, self.figure.ax3], self.toolbar, self.canvas)
        if 'i0' in df and 'it' in df and 'energy' in df:
            transmission = np.array(np.log(df['i0'] / df['it']))
        if 'i0' in df and 'pips' in df and 'energy' in df:
            fluorescence = np.array(df['pips'] / df['i0'])
        if 'it' in df and 'ir' in df and 'energy' in df:
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
