import pkg_resources
import json
import time
import sys

from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
from isstools.dialogs.BasicDialogs import question_message_box, message_box
from datetime import datetime
import numpy as np
import time as ttime
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QThread, QSettings
from isstools.dialogs import (UpdatePiezoDialog, Prepare_BL_Dialog, MoveMotorDialog)
from isstools.elements.figure_update import update_figure
ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_beamline_setup.ui')
from isstools.elements.liveplots import NormPlot

class UIBeamlineSetup(*uic.loadUiType(ui_path)):
    def __init__(self,
                 RE,
                 db,
                 detector_dictionary,
                 plan_funcs,
                 service_plan_funcs,
                 aux_plan_funcs,
                 motor_dictionary,
                 general_scan_func,
                 shutter_dictionary,
                 parent_gui,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.addCanvas()
        self.RE = RE
        self.db = db
        self.detector_dictionary = detector_dictionary
        self.plan_funcs = plan_funcs
        self.aux_plan_funcs = aux_plan_funcs
        self.service_plan_funcs = service_plan_funcs
        self.motor_dictionary = motor_dictionary
        self.gen_scan_func = general_scan_func
        self.shutter_dictionary = shutter_dictionary
        self.parent_gui = parent_gui

        self.settings = QSettings(self.parent_gui.window_title, 'XLive')

        # self.service_plan_funcs_names = [plan.__name__ for plan in service_plan_funcs]
        # if 'get_offsets' in self.service_plan_funcs_names:
        #     self.push_get_offsets.clicked.connect(self.run_get_offsets)
        # else:
        #     self.push_get_offsets.setEnabled(False)

        self.push_get_offsets.clicked.connect(self.get_offsets)

        self.push_set_reference_foil.clicked.connect(self.set_reference_foil)

        self.push_gen_scan.clicked.connect(self.run_gen_scan)
        self.push_gen_scan_save.clicked.connect(self.save_gen_scan)

        self.last_text = '0'
        self.last_gen_scan_uid = ''

        #detectors
        self.det_list = list(detector_dictionary.keys())

        self.comboBox_detectors.addItems(self.det_list)
        self.comboBox_detectors_den.addItem('1')
        self.comboBox_detectors_den.addItems(self.det_list)
        self.comboBox_detectors.currentIndexChanged.connect(self.detector_selected)
        self.comboBox_detectors_den.currentIndexChanged.connect(self.detector_selected_den)
        self.detector_selected()
        self.detector_selected_den()

        self.motor_list = [self.motor_dictionary[motor]['description'] for motor in self.motor_dictionary]
        self.motor_sorted_list = list(self.motor_list)
        self.motor_sorted_list.sort()
        self.add_motors()

        self.cid_gen_scan = self.canvas_gen_scan.mpl_connect('button_press_event', self.getX_gen_scan)

        reference_foils = ['None','Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'W', 'Ir', 'Pt', 'Au', 'Zr', 'Nb', 'Mo', 'Ru', 'Rh', 'Pd', 'Ag', 'Sn']

        for foil in reference_foils:
            self.comboBox_reference_foils.addItem(foil)

    def addCanvas(self):
        self.figure_gen_scan = Figure()
        self.figure_gen_scan.set_facecolor(color='#FcF9F6')
        self.canvas_gen_scan = FigureCanvas(self.figure_gen_scan)
        self.canvas_gen_scan.motor = ''
        self.figure_gen_scan.ax = self.figure_gen_scan.add_subplot(111)
        self.toolbar_gen_scan = NavigationToolbar(self.canvas_gen_scan, self, coordinates=True)
        self.plot_gen_scan.addWidget(self.toolbar_gen_scan)
        self.plot_gen_scan.addWidget(self.canvas_gen_scan)
        self.canvas_gen_scan.draw_idle()
        self.cursor_gen_scan = Cursor(self.figure_gen_scan.ax, useblit=True, color='green', linewidth=0.75)

    def run_gen_scan(self, **kwargs):
        if 'ignore_shutter' in kwargs:
            ignore_shutter = kwargs['ignore_shutter']
        else:
            ignore_shutter = False

        if 'curr_element' in kwargs:
            curr_element = kwargs['curr_element']
        else:
            curr_element = None

        if 'repeat' in kwargs:
            repeat = kwargs['repeat']
        else:
            repeat = False

        if not ignore_shutter:
            for shutter in [self.shutter_dictionary[shutter] for shutter in self.shutter_dictionary if
                            self.shutter_dictionary[shutter].shutter_type != 'Fast Shutter]']:
                if shutter.status.get() !='Open': #different implementation from ISS
                    ret = question_message_box(self, 'Photon shutter closed', 'Proceed with the shutter closed?')
                    if not ret:
                        print('Aborted!')
                        return False
                    break

        if curr_element is not None:
            self.comboBox_detectors.setCurrentText(curr_element['det_name'])
            self.comboBox_channels.setCurrentText(curr_element['det_sig'])
            self.comboBox_detectors_den.setCurrentText('1')
            self.comboBox_motors.setCurrentText(self.motor_dictionary[curr_element['motor_name']]['description'])
            self.edit_gen_range.setText(str(curr_element['scan_range']))
            self.edit_gen_step.setText(str(curr_element['step_size']))

        curr_det = ''
        self.canvas_gen_scan.mpl_disconnect(self.cid_gen_scan)
        detectors = []
        detector_name = self.comboBox_detectors.currentText()
        detector = self.detector_dictionary[detector_name]['device']
        detectors.append(detector)
        channels = self.detector_dictionary[detector_name]['channels']
        channel = channels[self.comboBox_channels.currentIndex()]
        result_name = channel

        detector_name_den = self.comboBox_detectors_den.currentText()
        if detector_name_den != '1':
            detector_den = self.detector_dictionary[detector_name_den]['device']
            channels_den = self.detector_dictionary[detector_name_den]['channels']
            channel_den = channels_den[self.comboBox_channels.currentIndex()]
            detectors.append(detector_den)
            result_name += '/{}'.format(channel_den)
        else:
            channel_den = '1'

        for i in range(self.comboBox_detectors.count()):
            if hasattr(self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device'], 'dev_name'):
                if self.comboBox_detectors.currentText() == \
                        self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device'].dev_name.get():
                    curr_det = self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device']
                    detectors.append(curr_det)
                if self.comboBox_detectors_den.currentText() == \
                        self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device'].dev_name.get():
                    curr_det = self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device']
                    detectors.append(curr_det)
            else:
                if self.comboBox_detectors.currentText() == \
                        self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device'].name:
                    curr_det = self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device']
                    detectors.append(curr_det)
                if self.comboBox_detectors_den.currentText() == \
                        self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device'].name:
                    curr_det = self.detector_dictionary[list(self.detector_dictionary.keys())[i]]['device']
                    detectors.append(curr_det)

        # curr_mot = self.motor_dictionary[self.comboBox_gen_mot.currentText()]['object']
        for motor in self.motor_dictionary:
            if self.comboBox_motors.currentText() == self.motor_dictionary[motor]['description']:
                curr_mot = self.motor_dictionary[motor]['object']
                self.canvas_gen_scan.motor = curr_mot
                break

        rel_start = -float(self.edit_gen_range.text()) / 2
        rel_stop = float(self.edit_gen_range.text()) / 2
        num_steps = int(round(float(self.edit_gen_range.text()) / float(self.edit_gen_step.text()))) + 1

        update_figure([self.figure_gen_scan.ax], self.toolbar_gen_scan, self.canvas_gen_scan)

        # self.push_gen_scan.setEnabled(False)
        uid_list = self.RE(self.aux_plan_funcs['General Scan'](detectors,
                                                               curr_mot,
                                                               rel_start,
                                                               rel_stop,
                                                               num_steps, ),
                           NormPlot(channel, channel_den, result_name, curr_mot.name, ax=self.figure_gen_scan.ax))

        # except Exception as exc:
        #     print('[General Scan] Aborted! Exception: {}'.format(exc))
        #     print('[General Scan] Limit switch reached . Set narrower range and try again.')
        #     uid_list = []

        self.figure_gen_scan.tight_layout()
        self.canvas_gen_scan.draw_idle()
        self.cid_gen_scan = self.canvas_gen_scan.mpl_connect('button_press_event', self.getX_gen_scan)

        # self.push_gen_scan.setEnabled(True)
        self.last_gen_scan_uid = self.db[-1]['start']['uid']
        self.push_gen_scan_save.setEnabled(True)


    def save_gen_scan(self):
        run = self.db[self.last_gen_scan_uid]
        self.user_directory = '/GPFS/xf08id/User Data/{}.{}.{}/' \
            .format(run['start']['year'],
                    run['start']['cycle'],
                    run['start']['PROPOSAL'])

        detectors_names = []
        for detector in run['start']['plan_args']['detectors']:
            text = detector.split('name=')[1]
            detectors_names.append(text[1: text.find('\'', 1)])

        numerator_name = detectors_names[0]
        denominator_name = ''
        if len(detectors_names) > 1:
            denominator_name = detectors_names[1]

        text = run['start']['plan_args']['motor'].split('name=')[1]
        motor_name = text[1: text.find('\'', 1)]

        numerator_devname = ''
        denominator_devname = ''
        for descriptor in run['descriptors']:
            if 'data_keys' in descriptor:
                if numerator_name in descriptor['data_keys']:
                    numerator_devname = descriptor['data_keys'][numerator_name]['devname']
                if denominator_name in descriptor['data_keys']:
                    denominator_devname = descriptor['data_keys'][denominator_name]['devname']

        ydata = []
        xdata = []
        for line in self.figure_gen_scan.ax.lines:
            ydata.extend(line.get_ydata())
            xdata.extend(line.get_xdata())

        filename = QtWidgets.QFileDialog.getSaveFileName(self, 'Save scan...', self.user_directory, '*.txt')[0]
        if filename[-4:] != '.txt':
            filename += '.txt'

        start = run['start']

        year = start['year']
        cycle = start['cycle']
        saf = start['SAF']
        pi = start['PI']
        proposal = start['PROPOSAL']
        scan_id = start['scan_id']
        real_uid = start['uid']
        start_time = start['time']
        stop_time = run['stop']['time']

        human_start_time = str(datetime.fromtimestamp(start_time).strftime('%m/%d/%Y  %H:%M:%S'))
        human_stop_time = str(datetime.fromtimestamp(stop_time).strftime('%m/%d/%Y  %H:%M:%S'))
        human_duration = str(datetime.fromtimestamp(stop_time - start_time).strftime('%M:%S'))

        if len(numerator_devname):
            numerator_name = numerator_devname
        result_name = numerator_name
        if len(denominator_name):
            if len(denominator_devname):
                denominator_name = denominator_devname
            result_name += '/{}'.format(denominator_name)

        header = '{}  {}'.format(motor_name, result_name)
        comments = '# Year: {}\n' \
                   '# Cycle: {}\n' \
                   '# SAF: {}\n' \
                   '# PI: {}\n' \
                   '# PROPOSAL: {}\n' \
                   '# Scan ID: {}\n' \
                   '# UID: {}\n' \
                   '# Start time: {}\n' \
                   '# Stop time: {}\n' \
                   '# Total time: {}\n#\n# '.format(year,
                                                    cycle,
                                                    saf,
                                                    pi,
                                                    proposal,
                                                    scan_id,
                                                    real_uid,
                                                    human_start_time,
                                                    human_stop_time,
                                                    human_duration)

        matrix = np.array([xdata, ydata]).transpose()
        matrix = self.gen_parser.data_manager.sort_data(matrix, 0)

        fmt = ' '.join(
            ['%d' if array.dtype == np.dtype('int64') else '%.6f' for array in [np.array(xdata), np.array(ydata)]])

        np.savetxt(filename,
                   np.array([xdata, ydata]).transpose(),
                   delimiter=" ",
                   header=header,
                   fmt=fmt,
                   comments=comments)

    def getX_gen_scan(self, event):
        if event.button == 3:
            if self.canvas_gen_scan.motor != '':
                dlg = MoveMotorDialog.MoveMotorDialog(new_position=event.xdata, motor=self.canvas_gen_scan.motor,
                                                      parent=self.canvas_gen_scan)
                if dlg.exec_():
                    pass


    def detector_selected(self):
        self.comboBox_channels.clear()
        detector = self.comboBox_detectors.currentText()
        self.comboBox_channels.addItems(self.detector_dictionary[detector]['channels'])

    def detector_selected_den(self):
        self.comboBox_channels_den.clear()
        detector = self.comboBox_detectors_den.currentText()
        if detector == '1':
            self.comboBox_channels_den.addItem('1')
        else:
            self.comboBox_channels_den.addItems(self.detector_dictionary[detector]['channels'])


    def add_motors(self):
        self.comboBox_motors.clear()
        self.comboBox_motors.addItems(self.motor_sorted_list)


    def set_reference_foil(self):
        foil = self.comboBox_reference_foils.currentText()
        self.RE(self.aux_plan_funcs['Set Reference Foil'](element = foil))
        # self.RE.md['foil_element'] = self.aux_plan_funcs['get_reference_foil']()
        pass




    # def run_get_offsets(self):
    #     for shutter in [self.shutters[shutter] for shutter in self.shutters
    #                     if self.shutters[shutter].shutter_type == 'PH' and
    #                     self.shutters[shutter].status.get() == 'Open']:
    #         st = shutter.set('Close')
    #         while not st.done:
    #             QtWidgets.QApplication.processEvents()
    #             ttime.sleep(0.1)
    #     get_offsets = [func for func in self.plan_funcs if func.__name__ == 'get_offsets'][0]
    #
    #     adc_names = [box.text() for box in self.adc_checkboxes if box.isChecked()]
    #     adcs = [adc for adc in self.adc_list if adc.dev_name.value in adc_names]
    #
    #     list(get_offsets(20, *adcs, stdout = self.parent_gui.emitstream_out))


    def get_offsets(self):
        self.push_get_offsets.setEnabled(False)
        sys.stdout = self.parent_gui.emitstream_out
        if self.parent_gui.hutch == 'b':
            self.RE(self.service_plan_funcs['get_offsets'](hutch_c = False))
        if self.parent_gui.hutch == 'c':
            self.RE(self.service_plan_funcs['get_offsets'](hutch_c = True))

        self.push_get_offsets.setEnabled(True)