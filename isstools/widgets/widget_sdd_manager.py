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
        self.roi_plots = []

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
        checkboxes = [
            self.checkBox_roi1_show,
            self.checkBox_roi2_show,
            self.checkBox_roi3_show,
            self.checkBox_roi4_show,
        ]

        for checkbox in checkboxes:
            checkbox.stateChanged.connect(self.update_roi_plot)

        self.roi_spinbox_dict = {
            'spinBox_roi1_lo': {'roi': [self.xs.channel1.rois.roi01.bin_low],  'value': 0, 'color': 'r', 'checkbox': self.checkBox_roi1_show},
            'spinBox_roi1_hi': {'roi': [self.xs.channel1.rois.roi01.bin_high], 'value': 0, 'color': 'r', 'checkbox': self.checkBox_roi1_show},
            'spinBox_roi2_lo': {'roi': [self.xs.channel1.rois.roi02.bin_low],  'value': 0, 'color': 'b', 'checkbox': self.checkBox_roi2_show},
            'spinBox_roi2_hi': {'roi': [self.xs.channel1.rois.roi02.bin_high], 'value': 0, 'color': 'b', 'checkbox': self.checkBox_roi2_show},
            'spinBox_roi3_lo': {'roi': [self.xs.channel1.rois.roi03.bin_low],  'value': 0, 'color': 'g', 'checkbox': self.checkBox_roi3_show},
            'spinBox_roi3_hi': {'roi': [self.xs.channel1.rois.roi03.bin_high], 'value': 0, 'color': 'g', 'checkbox': self.checkBox_roi3_show},
            'spinBox_roi4_lo': {'roi': [self.xs.channel1.rois.roi04.bin_low],  'value': 0, 'color': 'm', 'checkbox': self.checkBox_roi4_show},
            'spinBox_roi4_hi': {'roi': [self.xs.channel1.rois.roi04.bin_high], 'value': 0, 'color': 'm', 'checkbox': self.checkBox_roi4_show},
        }

        self.update_spinboxes()
        for spinbox in spinboxes:
            spinbox.valueChanged.connect(self.set_roi_value)

    def update_roi_plot(self):
        for roi_plot in self.roi_plots:
            self.figure_xs3_mca.ax.lines.remove(roi_plot[0])

        self.roi_plots = []
        ylims=self.figure_xs3_mca.ax.get_ylim()
        spinboxes = self.roi_spinbox_dict.keys()
        for spinbox in spinboxes:
            value = self.roi_spinbox_dict[spinbox]['value']
            color = self.roi_spinbox_dict[spinbox]['color']
            checkbox = self.roi_spinbox_dict[spinbox]['checkbox']
            if checkbox.isChecked():
                h=self.figure_xs3_mca.ax.plot([value, value], [ylims[0]*0.90, ylims[1]*0.90], color)
                self.roi_plots.append(h)
        self.canvas_xs3_mca.draw_idle()



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
        rois = self.roi_spinbox_dict[sender_object]['roi']
        value =  sender.sender().value()
        self.roi_spinbox_dict[sender_object]['value']=value
        for roi in rois:
            roi.put(value)
        self.update_roi_plot()




    def run_xs3_acquire(self):
        self.roi_plots = []
        print('acquiring...')
        plan = self.plan_funcs[3]
        acq_time = self.spinBox_acq_time.value()
        self.RE(plan(acq_time = acq_time))


        update_figure([self.figure_xs3_mca.ax], self.toolbar_xs3_mca, self.canvas_xs3_mca)
        self.figure_xs3_mca.ax.plot(self.xs.mca1_sum.get(),'b')
        self.figure_xs3_mca.ax.plot(self.xs.mca2_sum.get(), 'r')
        self.figure_xs3_mca.ax.plot(self.xs.mca3_sum.get(), 'g')
        self.figure_xs3_mca.ax.plot(self.xs.mca4_sum.get(), 'm')
        self.update_roi_plot()
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

    def update_spinboxes(self):
        spinboxes = self.roi_spinbox_dict.keys()
        for spinbox in spinboxes:
            spinbox_object = getattr(self, spinbox)
            value = self.roi_spinbox_dict[spinbox]['roi'][0].get()
            spinbox_object.setValue(value)
            self.roi_spinbox_dict[spinbox]['value']=value
        self.update_roi_plot()



    '''
    
    
    def toggle_xia_checkbox(self, value):
        if value:
            self.xia_tog_channels.append(self.sender().text())
        elif self.sender().text() in self.xia_tog_channels:
            self.xia_tog_channels.remove(self.sender().text())
        self.erase_xia_graph()
        for chan in self.xia_tog_channels:
            self.update_xia_graph(getattr(self.xia, 'mca{}.array.value'.format(chan)),
                                  obj=getattr(self.xia, 'mca{}.array'.format(chan)))

    def toggle_xia_all(self):
        if len(self.xia_tog_channels) != len(self.xia.read_attrs):
            for index, mca in enumerate(self.xia.read_attrs):
                if getattr(self, 'checkBox_gm_ch{}'.format(index + 1)).isEnabled():
                    getattr(self, 'checkBox_gm_ch{}'.format(index + 1)).setChecked(True)
        else:
            for index, mca in enumerate(self.xia.read_attrs):
                if getattr(self, 'checkBox_gm_ch{}'.format(index + 1)).isEnabled():
                    getattr(self, 'checkBox_gm_ch{}'.format(index + 1)).setChecked(False)

    def update_xia_params(self, value, **kwargs):
        if kwargs['obj'].name == 'xia1_real_time':
            self.edit_xia_acq_time.setText('{:.2f}'.format(round(value, 2)))
        elif kwargs['obj'].name == 'xia1_real_time_rb':
            self.label_acq_time_rbv.setText('{:.2f}'.format(round(value, 2)))
        elif kwargs['obj'].name == 'xia1_mca_max_energy':
            self.edit_xia_energy_range.setText('{:.0f}'.format(value * 1000))

    def erase_xia_graph(self):
        self.figure_xia_all_graphs.ax.clear()

        for roi in range(12):
            if hasattr(self.figure_xia_all_graphs.ax, 'roi{}l'.format(roi)):
                exec('del self.figure_xia_all_graphs.ax.roi{}l,\
                    self.figure_xia_all_graphs.ax.roi{}h'.format(roi, roi))

        self.toolbar_xia_all_graphs.update()
        self.xia_graphs_names.clear()
        self.xia_graphs_labels.clear()
        self.xia_handles.clear()
        self.canvas_xia_all_graphs.draw_idle()

    def start_xia_spectra(self):
        if self.xia.collect_mode.value != 0:
            self.xia.collect_mode.put(0)
            ttime.sleep(2)
        self.xia.erase_start.put(1)

    def update_xia_rois(self):
        energies = np.linspace(0, float(self.edit_xia_energy_range.text()) / 1000, 2048)

        for roi in range(12):
            if float(getattr(self, 'edit_roi_from_{}'.format(roi)).text()) < 0 or float(
                    getattr(self, 'edit_roi_to_{}'.format(roi)).text()) < 0:
                exec('start{} = -1'.format(roi))
                exec('end{} = -1'.format(roi))
            else:
                indexes_array = np.where(
                    (energies >= float(getattr(self, 'edit_roi_from_{}'.format(roi)).text()) / 1000) & (
                    energies <= float(getattr(self, 'edit_roi_to_{}'.format(roi)).text()) / 1000) == True)[0]
                if len(indexes_array):
                    exec('start{} = indexes_array.min()'.format(roi))
                    exec('end{} = indexes_array.max()'.format(roi))
                else:
                    exec('start{} = -1'.format(roi))
                    exec('end{} = -1'.format(roi))
            exec('roi{}x = [float(self.edit_roi_from_{}.text()), float(self.edit_roi_to_{}.text())]'.format(roi, roi,
                                                                                                            roi))
            exec('label{} = self.edit_roi_name_{}.text()'.format(roi, roi))

        for channel in self.xia_channels:
            for roi in range(12):
                getattr(self.xia, "mca{}.roi{}".format(channel, roi)).low.put(eval('start{}'.format(roi)))
                getattr(self.xia, "mca{}.roi{}".format(channel, roi)).high.put(eval('end{}'.format(roi)))
                getattr(self.xia, "mca{}.roi{}".format(channel, roi)).label.put(eval('label{}'.format(roi)))

        for roi in range(12):
            if not hasattr(self.figure_xia_all_graphs.ax, 'roi{}l'.format(roi)):
                exec(
                    'self.figure_xia_all_graphs.ax.roi{}l = self.figure_xia_all_graphs.ax.axvline(x=roi{}x[0], color=self.roi_colors[roi])'.format(
                        roi, roi))
                exec(
                    'self.figure_xia_all_graphs.ax.roi{}h = self.figure_xia_all_graphs.ax.axvline(x=roi{}x[1], color=self.roi_colors[roi])'.format(
                        roi, roi))

            else:
                exec('self.figure_xia_all_graphs.ax.roi{}l.set_xdata([roi{}x[0], roi{}x[0]])'.format(roi, roi, roi))
                exec('self.figure_xia_all_graphs.ax.roi{}h.set_xdata([roi{}x[1], roi{}x[1]])'.format(roi, roi, roi))

        self.figure_xia_all_graphs.ax.grid(True)
        self.canvas_xia_all_graphs.draw_idle()

    def update_xia_acqtime_pv(self):
        self.xia.real_time.put(float(self.edit_xia_acq_time.text()))

    def update_xia_energyrange_pv(self):
        self.xia.mca_max_energy.put(float(self.edit_xia_energy_range.text()) / 1000)

    def update_xia_graph(self, value, **kwargs):
        curr_name = kwargs['obj'].name
        curr_index = -1
        if len(self.figure_xia_all_graphs.ax.lines):
            if float(self.edit_xia_energy_range.text()) != self.figure_xia_all_graphs.ax.lines[0].get_xdata()[-1]:
                self.figure_xia_all_graphs.ax.clear()
                for roi in range(12):
                    if hasattr(self.figure_xia_all_graphs.ax, 'roi{}l'.format(roi)):
                        exec('del self.figure_xia_all_graphs.ax.roi{}l,\
                            self.figure_xia_all_graphs.ax.roi{}h'.format(roi, roi))

                self.toolbar_xia_all_graphs.update()
                self.xia_graphs_names.clear()
                self.xia_graphs_labels.clear()
                self.canvas_xia_all_graphs.draw_idle()

        if curr_name in self.xia_graphs_names:
            for index, name in enumerate(self.xia_graphs_names):
                if curr_name == name:
                    curr_index = index
                    line = self.figure_xia_all_graphs.ax.lines[curr_index]
                    line.set_ydata(value)
                    break

        else:
            ch_number = curr_name.split('_')[1].split('mca')[1]
            if ch_number in self.xia_tog_channels:
                self.xia_graphs_names.append(curr_name)
                label = 'Chan {}'.format(ch_number)
                self.xia_graphs_labels.append(label)
                handles, = self.figure_xia_all_graphs.ax.plot(
                    np.linspace(0, float(self.edit_xia_energy_range.text()), 2048), value, label=label)
                self.xia_handles.append(handles)
                self.figure_xia_all_graphs.ax.legend(self.xia_handles, self.xia_graphs_labels)

            if len(self.figure_xia_all_graphs.ax.lines) == len(self.xia_tog_channels) != 0:
                for roi in range(12):
                    exec('roi{}x = [float(self.edit_roi_from_{}.text()), float(self.edit_roi_to_{}.text())]'.format(roi,
                                                                                                                    roi,
                                                                                                                    roi))

                for roi in range(12):
                    if not hasattr(self.figure_xia_all_graphs.ax, 'roi{}l'.format(roi)):
                        exec(
                            'self.figure_xia_all_graphs.ax.roi{}l = self.figure_xia_all_graphs.ax.axvline(x=roi{}x[0], color=self.roi_colors[roi])'.format(
                                roi, roi))
                        exec(
                            'self.figure_xia_all_graphs.ax.roi{}h = self.figure_xia_all_graphs.ax.axvline(x=roi{}x[1], color=self.roi_colors[roi])'.format(
                                roi, roi))

                self.figure_xia_all_graphs.ax.grid(True)

        self.figure_xia_all_graphs.ax.relim()
        self.figure_xia_all_graphs.ax.autoscale(True, True, True)
        y_interval = self.figure_xia_all_graphs.ax.get_yaxis().get_data_interval()
       
        if len(y_interval):
            if y_interval[0] != 0 or y_interval[1] != 0:
                self.figure_xia_all_graphs.ax.set_ylim([y_interval[0] - (y_interval[1] - y_interval[0]) * 0.05,
       
        self.canvas_xia_all_graphs.draw_idle()

    def run_gain_matching(self):
        ax = self.figure_gain_matching.add_subplot(111)
        gain_adjust = [0.001] * len(self.xia_channels)  # , 0.001, 0.001, 0.001]
        diff = [0] * len(self.xia_channels)  # , 0, 0, 0]
        diff_old = [0] * len(self.xia_channels)  # , 0, 0, 0]

        # Run number of iterations defined in the text edit edit_gain_matching_iterations:
        for i in range(int(self.edit_gain_matching_iterations.text())):
            self.xia.collect_mode.put('MCA spectra')
            ttime.sleep(0.25)
            self.xia.mode.put('Real time')
            ttime.sleep(0.25)
            self.xia.real_time.put('1')
            self.xia.capt_start_stop.put(1)
            ttime.sleep(0.05)
            self.xia.erase_start.put(1)
            ttime.sleep(2)
            ax.clear()
            self.toolbar_gain_matching.update()

            # For each channel:
            for chann in self.xia_channels:
                # If checkbox of current channel is checked:
                if getattr(self, "checkBox_gm_ch{}".format(chann)).checkState() > 0:

                    # Get current channel pre-amp gain:
                    curr_ch_gain = getattr(self.xia, "pre_amp_gain{}".format(chann))

                    coeff = self.xia_parser.gain_matching(self.xia, self.edit_center_gain_matching.text(),
                                                          self.edit_range_gain_matching.text(), chann, ax)
                    # coeff[0] = Intensity
                    # coeff[1] = Fitted mean
                    # coeff[2] = Sigma

                    diff[chann - 1] = float(self.edit_gain_matching_target.text()) - float(coeff[1] * 1000)

                    if i != 0:
                        sign = (diff[chann - 1] * diff_old[chann - 1]) / math.fabs(
                            diff[chann - 1] * diff_old[chann - 1])
                        if int(sign) == -1:
                            gain_adjust[chann - 1] /= 2
                    print('Chan ' + str(chann) + ': ' + str(diff[chann - 1]) + '\n')

                    # Update current channel pre-amp gain:
                    curr_ch_gain.put(curr_ch_gain.value - diff[chann - 1] * gain_adjust[chann - 1])
                    diff_old[chann - 1] = diff[chann - 1]

                    self.canvas_gain_matching.draw_idle()
    '''