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

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_run_diff.ui')

from isstools.xiaparser import xiaparser
from isstools.xasdata.xasdata import XASdataGeneric


class UIRunDiff(*uic.loadUiType(ui_path)):
    def __init__(self,
                 RE,
                 db,
                 plans_diff,
                 parent_gui,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)

        mpl.rcParams['agg.path.chunksize'] = 10000
        self.RE = RE
        self.db = db
        self.plans_diff = plans_diff[0]
        self.run_start.clicked.connect(self.run_diffraction)

        # TODO : remove hhm dependency

    def run_diffraction(self,db):
        run_parameters = []

        # for shutter in [self.shutter_dictionary[shutter] for shutter in self.shutter_dictionary if
        #                 self.shutter_dictionary[shutter].shutter_type != 'SP']:
        #     if shutter.state.value:
        #         print(self, 'Shutter closed')
        #         break

        name_provided = self.lineEdit_filename.text()
        if name_provided:
            timenow = datetime.datetime.now()
            print('\nStarting scan at {}'.format(timenow.strftime("%H:%M:%S"), flush='true'))
            start_scan_timer = timer()
            run_parameters = {'filename': self.lineEdit_filename.text(),
                              'exposure': self.spinBox_exposure.value(),
                              'num_images': self.spinBox_num_frames.value(),
                              'num_dark_images': self.spinBox_num_dark_frames.value(),
                              'num_repetitions': self.spinBox_num_repetitions.value(),
                              'delay': self.spinBox_delay.value()
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
