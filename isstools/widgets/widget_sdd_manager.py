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
import numpy


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
        self.timer_update_time.timeout.connect(self.update_roi_labels)
        self.timer_update_time.start()

        self.push_xs3_acquire.clicked.connect(self.xs3_acquire)

        self.colors = ['r', 'b', 'g', 'm']
        self.num_channels = 4
        self.num_rois = 4
        self.roi_values = numpy.zeros((4, 4, 2))
        self.roi_plots = []
        self.acquired = 0


        self.checkbox_ch = 'checkBox_ch{}_show'

        for indx in range(self.num_channels):
             getattr(self, self.checkbox_ch.format(indx + 1)).stateChanged.connect(self.plot_traces)

        self.checkbox_roi = 'checkBox_roi{}_show'
        for indx in range(self.num_rois):
             getattr(self, self.checkbox_roi.format(indx + 1)).stateChanged.connect(self.update_roi_plot)

        self.lo_hi = ['lo','hi']
        self.lo_hi_def = {'lo':'low', 'hi':'high'}

        self.spinbox_roi = 'spinBox_ch{}_roi{}_{}'

        self.label_roi_rbk = 'label_ch{}_roi{}_{}_rbk'

        self.update_spinboxes()
        for indx_ch in range(self.num_channels):
            for indx_roi in range(self.num_rois):
                for indx_lo_hi in range(2):
                    spinbox_name = self.spinbox_roi.format(indx_ch + 1, indx_roi + 1, self.lo_hi[indx_lo_hi])
                    spinbox_object = getattr(self, spinbox_name)
                    spinbox_object.valueChanged.connect(self.set_roi_value)


    def set_roi_value(self):
        sender = QObject()
        sender_object = sender.sender().objectName()
        indx_ch = sender_object[10]
        indx_roi = sender_object[15]
        lo_hi = sender_object[17:]
        signal = self.get_roi_signal(indx_ch, indx_roi, self.lo_hi.index(lo_hi))
        value = sender.sender().value()
        signal.put(value)
        self.roi_values[int(indx_ch), int(indx_roi), self.lo_hi.index(lo_hi)] = value
        self.update_roi_plot()


    def get_roi_signal(self, indx_ch,indx_roi,indx_lo_hi):
        signal_ch = getattr(self.xs, 'channel{}'.format(indx_ch))
        signal_roi = getattr(signal_ch.rois, 'roi0{}'.format(indx_roi))
        signal = getattr(signal_roi, 'bin_{}'.format(self.lo_hi_def[self.lo_hi[indx_lo_hi]]))
        return signal


    def update_roi_labels(self):
        for indx_ch in range(self.num_channels):
            for indx_roi in range(self.num_rois):
                for indx_lo_hi in range(2):
                    label_name =self.label_roi_rbk.format(indx_ch+1, indx_roi+1, self.lo_hi[indx_lo_hi])
                    label_object = getattr(self,label_name)
                    value = self.get_roi_signal( indx_ch+1, indx_roi+1, indx_lo_hi).get()
                    label_object.setText(str(value))


    def update_spinboxes(self):
        for indx_ch in range(self.num_channels):
            for indx_roi in range(self.num_rois):
                for indx_lo_hi in range(2):
                    spinbox_name = self.spinbox_roi.format(indx_ch+1,indx_roi+1,self.lo_hi[indx_lo_hi])
                    spinbox_object = getattr(self,spinbox_name)
                    value = self.get_roi_signal(indx_ch+1, indx_roi+1, indx_lo_hi).get()
                    spinbox_object.setValue(value)
                    self.roi_values[indx_ch,indx_roi,indx_lo_hi] = value
        self.update_roi_plot()

    def update_roi_plot(self):
        for roi_plot in self.roi_plots:
            self.figure_xs3_mca.ax.lines.remove(roi_plot[0])
        self.roi_plots = []
        ylims=self.figure_xs3_mca.ax.get_ylim()
        for indx_ch in range(self.num_channels):
            show_ch = getattr(self, 'checkBox_ch{}_show'.format(indx_ch + 1)).isChecked()
            for indx_roi in range(self.num_rois):
                show_roi = getattr(self, 'checkBox_roi{}_show'.format(indx_roi + 1)).isChecked()
                for indx_hi_lo in range(2):
                    if show_ch and show_roi:
                        color = self.colors[indx_ch]
                        value = self.roi_values[indx_ch,indx_roi,indx_hi_lo]
                        h = self.figure_xs3_mca.ax.plot([value, value], [0, ylims[1] * 0.85], color, linestyle='dashed',
                                                        linewidth=0.5)
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

    def xs3_acquire(self):
        self.roi_plots = []
        print('acquiring...')
        plan = self.plan_funcs[3]
        acq_time = self.spinBox_acq_time.value()
        self.RE(plan(acq_time = acq_time))
        self.acquired = True


        update_figure([self.figure_xs3_mca.ax], self.toolbar_xs3_mca, self.canvas_xs3_mca)
        self.plot_traces()
        self.update_roi_plot()
        self.canvas_xs3_mca.draw_idle()

    def plot_traces(self):
        if self.acquired:
            for indx in range(self.num_channels):
                if getattr(self, self.checkbox_ch.format(indx+1)).isChecked():
                    ch = getattr(self.xs,'mca{}_sum'.format(indx+1))
                    self.figure_xs3_mca.ax.plot(ch.get(),self.colors[indx])
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