import sys
import pkg_resources
import inspect
import re
import os
from subprocess import call
from PyQt5 import uic, QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QThread, QSettings
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import time as ttime
import numpy as np
import datetime
from timeit import default_timer as timer
from skimage import exposure
import matplotlib as mpl
from isstools.elements.figure_update import update_figure
import bluesky.plan_stubs as bps
from bluesky.plan_stubs import mv
import sys
# Libs needed by the ZMQ communication
import json
import pandas as pd
import numpy as np

timenow = datetime.datetime.now()

# ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_run_diff.ui')
ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_run_diff_dafs.ui')


from isstools.xiaparser import xiaparser
from isstools.xasdata.xasdata import XASdataGeneric


class UIRunDiff(*uic.loadUiType(ui_path)):
    def __init__(self,
                 RE,
                 db,
                 pe1,
                 plans_diff,
                 parent_gui,
                 mono,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)

        mpl.rcParams['agg.path.chunksize'] = 10000
        self.RE = RE
        self.db = db
        self.pe1 = pe1
        self.plans_diff = plans_diff[0]
        self.plans_diff_pilatus = plans_diff[2]
        self.plans_diff_pilatus_dafs = plans_diff[3]
        self.mono = mono
        self.parent_gui = parent_gui
        self.comboBox_detector_list.addItems(['Perkin', 'Pilatus'])
        self.run_start.clicked.connect(self.run_diffraction)

        self.settings = QSettings(parent_gui.window_title, 'XLive')
        self.user_dir = self.settings.value('usr_dir', defaultValue = '/nsls2/data/qas-new/legacy/processed', type = str)

        self.sample_to_detector_distance()

        self.push_open_pattern.clicked.connect(self.open_tiff_files)

        self.comboBox_detector_list.currentTextChanged.connect(self.update_plan_limits)
        self.pe1.sample_to_detector_distance.subscribe(self.current_sample_to_detector_distance)
        self.spinBox_s2d_distance.editingFinished.connect(self.update_sample_to_detector_distance)
        self.addCanvas()


    def update_plan_limits(self):
        if self.comboBox_detector_list.currentIndex() == 1:
            self.doubleSpinBox_subframe_time.setMaximum(60)
        else:
            self.doubleSpinBox_subframe_time.setMaximum(5)

    def sample_to_detector_distance(self):
        _value = self.pe1.sample_to_detector_distance.get()
        self.label_s2d_distance.setText(f"Sample to detector distance \n current value: {_value:.0f} mm")


    def current_sample_to_detector_distance(self, value, **kwargs):
        self.label_s2d_distance.setText(f"Sample to detector distance \n current value: {value:.0f} mm")

    def update_sample_to_detector_distance(self):
        _value = self.spinBox_s2d_distance.value()
        self.pe1.sample_to_detector_distance.put(_value)
        _value = self.pe1.sample_to_detector_distance.get()
        print(f'Sample to detector distance is now set to: {_value}')

    def run_diffraction(self,db):

        sys.stdout = self.parent_gui.emitstream_out
        run_parameters = []

        # for shutter in [self.shutter_dictionary[shutter] for shutter in self.shutter_dictionary if
        #                 self.shutter_dictionary[shutter].shutter_type != 'SP']:
        #     if shutter.state.get():
        #         print(self, 'Shutter closed')
        #         break

        current_energy = self.mono.energy.read()['mono1_energy']['value']
        print("Current Energy is: ",  current_energy)

        desired_energy = self.doubleSpinBox_energy.value()
        self.RE(bps.mv(self.mono.energy, desired_energy))

        changed_energy = self.mono.energy.read()['mono1_energy']['value']
        print("Energy changed to: ", changed_energy)

        name_provided = self.lineEdit_sample_name.text()
        if name_provided:
            timenow = datetime.datetime.now()
            print('\nStarting scan at {}'.format(timenow.strftime("%H:%M:%S"), flush='true'))
            start_scan_timer = timer()
            run_parameters = {'sample_name'   : self.lineEdit_sample_name.text(),
                              'frame_count'   : self.spinBox_frame_count.value(),
                              'subframe_time' : self.doubleSpinBox_subframe_time.value(),
                              'subframe_count': self.spinBox_subframe_count.value(),
                              'delay'         : self.doubleSpinBox_delay.value()
                              }


            # Run the scan using the dict created before
            self.run_mode_uids = []

            # if self.comboBox_detector_list.currentIndex() == 0:
            #     self.run_mode_uids = self.RE(self.plans_diff(**run_parameters))
            # else:
            #     self.run_mode_uids = self.RE(self.plans_diff_pilatus(**run_parameters))

            if self.comboBox_detector_list.currentIndex() == 0:
                self.run_mode_uids = self.RE(self.plans_diff(**run_parameters))
            else:
                if self.checkBox_dafs_mode.isChecked():
                    parameters = {'e0' : float(self.doubleSpinBox_e0.value()),
                    'below_edge' : float(self.doubleSpinBox_below_edge.value()),
                    'above_edge': float(self.doubleSpinBox_above_edge.value()),
                    'edge_start' : float(self.doubleSpinBox_edge_start.value()),
                    'edge_end' : float(self.doubleSpinBox_edge_end.value()),
                    'pre_edge_spacing' : float(self.doubleSpinBox_pre_edge_spacing.value()),
                    'xanes_spacing' : float(self.doubleSpinBox_xanes_spacing.value()),
                    'exafs_k_spacing' : float(self.doubleSpinBox_exafs_k_spacing.value()),
                    'dafs_mode': self.checkBox_dafs_mode.isChecked()}

                    final_dict = {**run_parameters, **parameters}

                    self.run_mode_uids = self.RE(self.plans_diff_pilatus_dafs(**final_dict))
                else:
                    self.run_mode_uids = self.RE(self.plans_diff_pilatus(**run_parameters))






            timenow = datetime.datetime.now()
            print('Scan complete at {}'.format(timenow.strftime("%H:%M:%S")))
            stop_scan_timer = timer()
            print('Scan duration {} s'.format(stop_scan_timer - start_scan_timer))

            self.RE(bps.mv(self.mono.energy, current_energy))
            print("Energy changed to: ", self.mono.energy.read()['mono1_energy']['value'])


        else:
            print('Error', 'Please provide the name for the scan')

    def run_diffraction_in_batch(self, sample_name, frame_count, subframe_time, subframe_count, delay=None):
        run_parameters = []

        # for shutter in [self.shutter_dictionary[shutter] for shutter in self.shutter_dictionary if
        #                 self.shutter_dictionary[shutter].shutter_type != 'SP']:
        #     if shutter.state.get():
        #         print(self, 'Shutter closed')
        #         break

        # name_provided = self.lineEdit_sample_name.text()

        current_energy = mono1.energy.read()['mono1_energy']['value']
        name_provided = sample_name
        if name_provided:
            timenow = datetime.datetime.now()
            print('\nStarting scan at {}'.format(timenow.strftime("%H:%M:%S"), flush='true'))
            start_scan_timer = timer()
            run_parameters = {'sample_name'   : sample_name,
                              'frame_count'   : frame_count,
                              'subframe_time' : subframe_time,
                              'subframe_count': subframe_count,
                              'delay'         : delay
                              }


            # Run the scan using the dict created before
            self.run_mode_uids = []
            self.run_mode_uids = self.RE(self.plans_diff(**run_parameters))



            timenow = datetime.datetime.now()
            print('Scan complete at {}'.format(timenow.strftime("%H:%M:%S")))
            stop_scan_timer = timer()
            print('Scan duration {} s'.format(stop_scan_timer - start_scan_timer))


        else:
            print('Error', 'Please provide the name for the scan')


    def open_tiff_files(self):

        self.tiff_file_to_view = QtWidgets.QFileDialog.getOpenFileName(directory = self.user_dir,
                                                              filter = '*.tiff', parent = self)[0]

        img = plt.imread(self.tiff_file_to_view)
        logarithmic_corrected = exposure.adjust_log(img, 1)

        self.figure_tiff_image.ax.clear()
        self.figure_tiff_image.ax.imshow(logarithmic_corrected, cmap='BuPu_r', vmax=2000)
        self.canvas_tiff_image.draw_idle()

    def addCanvas(self):
        self.figure_tiff_image = Figure()
        self.figure_tiff_image.set_facecolor(color='#FcF9F6')
        self.canvas_tiff_image = FigureCanvas(self.figure_tiff_image)
        self.figure_tiff_image.ax = self.figure_tiff_image.add_subplot(111)
        self.toolbar_tiff_image = NavigationToolbar(self.canvas_tiff_image, self, coordinates=True)
        self.plot_tiff_image.addWidget(self.toolbar_tiff_image)
        self.plot_tiff_image.addWidget(self.canvas_tiff_image)
        self.canvas_tiff_image.draw_idle()
