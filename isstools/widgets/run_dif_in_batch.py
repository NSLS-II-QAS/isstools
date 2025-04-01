import numpy as np
import bluesky.plan_stubs as bps
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

# Libs needed by the ZMQ communication
import json
import pandas as pd
import numpy as np

timenow = datetime.datetime.now()

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_batch_manual.ui')

class Run_diff_in_batch(*uic.loadUiType(ui_path)):
    def __init__(self,
                 RE,
                 db,
                 mono,
                 plans_diff,
                 parent_gui,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Test class is created")
        mpl.rcParams['agg.path.chunksize'] = 10000
        self.RE = RE
        self.db = db
        self.mono = mono
        self.plans_diff = plans_diff[0]

        self.settings = QSettings(parent_gui.window_title, 'XLive')
        self.user_dir = self.settings.value('usr_dir', defaultValue='/nsls2/data/qas-new/legacy/processed', type=str)
        print("test initalization")
    def run_diff_batch(self,db):
        run_parameters = []

        # for shutter in [self.shutter_dictionary[shutter] for shutter in self.shutter_dictionary if
        #                 self.shutter_dictionary[shutter].shutter_type != 'SP']:
        #     if shutter.state.get():
        #         print(self, 'Shutter closed')
        #         break

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
            self.run_mode_uids = self.RE(self.plans_diff(**run_parameters))



            timenow = datetime.datetime.now()
            print('Scan complete at {}'.format(timenow.strftime("%H:%M:%S")))
            stop_scan_timer = timer()
            print('Scan duration {} s'.format(stop_scan_timer - start_scan_timer))


        else:
            print('Error', 'Please provide the name for the scan')