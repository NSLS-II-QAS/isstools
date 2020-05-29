import re
import time as ttime
import bluesky.plan_stubs as bps

import numpy as np
import pkg_resources

from PyQt5 import uic,  QtCore
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
from PyQt5.Qt import QSplashScreen, QObject


from isstools.xiaparser import xiaparser
from isstools.elements.figure_update import update_figure


ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_sdd_manager.ui')


class UISDDManager(*uic.loadUiType(ui_path)):

    def __init__(self,
                 plan_funcs,
                 xs,
                 RE,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.addCanvas()
        self.plan_funcs = plan_funcs
        self.RE = RE
        self.xs = xs

        self.timer_update_time = QtCore.QTimer(self)
        self.timer_update_time.setInterval(1000)
        self.timer_update_time.timeout.connect(self.update_xs_parameters)
        self.timer_update_time.start()


        self.push_xs3_acquire.clicked.connect(self.run_xs3_acquire)
        spinboxes = [
            self.spinBox_roi1_lo,
            self.spinBox_roi1_hi,
            self.spinBox_roi2_lo,
            self.spinBox_roi2_hi,
            self.spinBox_roi3_lo,
            self.spinBox_roi3_hi,
            self.spinBox_roi4_lo,
            self.spinBox_roi4_hi,
        ]


        self.roi_spinbox_dict = {
            'spinBox_roi1_lo': [self.xs.channel1.rois.roi01.bin_low],
            'spinBox_roi1_hi': [self.xs.channel1.rois.roi01.bin_high],
            'spinBox_roi2_lo': [self.xs.channel1.rois.roi02.bin_low],
            'spinBox_roi2_hi': [self.xs.channel1.rois.roi02.bin_high],
            'spinBox_roi3_lo': [self.xs.channel1.rois.roi03.bin_low],
            'spinBox_roi3_hi': [self.xs.channel1.rois.roi03.bin_high],
            'spinBox_roi4_lo': [self.xs.channel1.rois.roi04.bin_low],
            'spinBox_roi4_hi': [self.xs.channel1.rois.roi04.bin_high],
        }
        self.update_spinboxes()
        for spinbox in spinboxes:
            spinbox.valueChanged.connect(self.set_roi_value)

    def addCanvas(self):
        self.figure_xs3_mca = Figure()
        self.figure_xs3_mca.set_facecolor(color='#FcF9F6')
        self.canvas_xs3_mca = FigureCanvas(self.figure_xs3_mca)
        self.figure_xs3_mca.ax = self.figure_xs3_mca.add_subplot(111)
        self.toolbar_xs3_mca = NavigationToolbar(self.canvas_xs3_mca, self, coordinates=True)
        self.plot_xs3_mca.addWidget(self.toolbar_xs3_mca)
        self.plot_xs3_mca.addWidget(self.canvas_xs3_mca)
        self.canvas_xs3_mca.draw_idle()
        #self.cursor_xs3_mca = Cursor(self.figure_xia_all_graphs.ax, useblit=True, color='green', linewidth=0.75)
        self.figure_xs3_mca.ax.clear()


    def set_roi_value(self):
        sender = QObject()
        sender_object = sender.sender().objectName()
        rois = self.roi_spinbox_dict[sender_object]
        value =  sender.sender().value()
        for roi in rois:
            roi.put(value)

    def run_xs3_acquire(self):
        print('acquiring...')
        plan = self.plan_funcs[3]
        acq_time = self.spinBox_acq_time.value()
        self.RE(plan(acq_time = acq_time))


        update_figure([self.figure_xs3_mca.ax], self.toolbar_xs3_mca,
                      self.canvas_xs3_mca)
        self.figure_xs3_mca.ax.plot(self.xs.mca1_sum.get(),'b')
        self.figure_xs3_mca.ax.plot(self.xs.mca2_sum.get(), 'r')
        self.figure_xs3_mca.ax.plot(self.xs.mca3_sum.get(), 'g')
        self.figure_xs3_mca.ax.plot(self.xs.mca4_sum.get(), 'm')
        self.canvas_xs3_mca.draw_idle()

    def update_roi_plot(self):
        ylims=self.figure_xs3_mca.ax.get_ylim()
        roi1_lo = self.xs.channel1.rois.roi01.bin_low.get()
        roi1_hi = self.xs.channel1.rois.roi01.bin_high.get()
        self.figure_xs3_mca.ax.plot([roi1_lo, roi1_lo], [ylims[0], ylims[1]])
        self.figure_xs3_mca.ax.plot([roi1_hi, roi1_hi], [ylims[0], ylims[1]])
        self.canvas_xs3_mca.draw_idle()

    def update_xs_parameters(self):
        self.label_roi1_lo_rbk.setText(str(self.xs.channel1.rois.roi01.bin_low.get()))
        self.label_roi2_lo_rbk.setText(str(self.xs.channel1.rois.roi02.bin_low.get()))
        self.label_roi3_lo_rbk.setText(str(self.xs.channel1.rois.roi03.bin_low.get()))
        self.label_roi4_lo_rbk.setText(str(self.xs.channel1.rois.roi04.bin_low.get()))


        self.label_roi1_hi_rbk.setText(str(self.xs.channel1.rois.roi01.bin_high.get()))
        self.label_roi2_hi_rbk.setText(str(self.xs.channel1.rois.roi02.bin_high.get()))
        self.label_roi3_hi_rbk.setText(str(self.xs.channel1.rois.roi03.bin_high.get()))
        self.label_roi4_hi_rbk.setText(str(self.xs.channel1.rois.roi04.bin_high.get()))

