import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject
from PyQt5.Qt import QObject, QTimer
from functools import partial
# import sys
from xas.energy_calibration import get_possible_edges, get_atomic_symbol, find_correct_foil
import sys
import json
# import RE

from isstools.dialogs.BasicDialogs import message_box
from isstools.widgets.widget_motors import UIWidgetMotors

path_ionchamber_gases_dict = '/nsls2/data/qas-new/shared/config/repos/xas/xas/ionchamber_gas_dict.json'

try:
    with open(path_ionchamber_gases_dict) as fp:
        atomic_dict_for_ionchamber_gases = json.load(fp)
except FileNotFoundError:
    atomic_dict_for_ionchamber_gases = {}


# from isstools.dialogs import UpdateUserDialog

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_user_motors.ui')



class UIUserMotors(*uic.loadUiType(ui_path)):
    def __init__(self,
                 RE,
                 motors_dict=None,
                 apb=None,
                 wps = None,
                 mfc = None,
                 service_plan_funcs = None,
                 parent_gui=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.parent_gui = parent_gui
        self.motors_dict = motors_dict
        self.wps = wps
        self.mfc = mfc
        self.apb = apb
        self.service_plan_funcs = service_plan_funcs
        self.RE = RE

        self._gc = ""

        self._sample_stage_motors = ['sample_stage1_rotary',
                                     'sample_stage1_x',
                                     'sample_stage1_y',
                                     'sample_stage1_z',
                                     'sample_stage1_theta',
                                     'sample_stage1_chi']

        for motor in self._sample_stage_motors:
            self.verticalLayout_sample_motors.addWidget(UIWidgetMotors(self.motors_dict[motor], parent=self.parent_gui))


        self._gains = [f"1E{f:.0f} V/A" for f in range(3,11)]

        self.pushButton_getoffsets.clicked.connect(self.get_offsets)


        self._mfc_channels = ['ch1_he', 'ch2_n2', 'ch3_ar', 'ch4_n2', 'ch5_ar']

        for i in range(1,5):
            self.add_gain_subscriptions(i)
        #     # getattr()
            getattr(self, 'comboBox_ch' + str(i) + '_gain').currentIndexChanged.connect(self.update_gain)
            getattr(self, 'pushButton_amp_ch' + str(i)).clicked.connect(self.set_current_suppr)

        self._ion_chambers = ['i0', 'it', 'ir']
        # for i, ic in enumerate(self._ion_chambers):
        #     self.add_ion_chambers_plate_subscriptions(i+1, ic)
        #
        # for i, ic in enumerate(self._ion_chambers):
        #     self.add_ion_chambers_grid_subscriptions(i+1, ic)

        for channel in self._mfc_channels:
            self.add_mfc_subscriptions(channel)
            getattr(self, 'lineEdit_' + channel).returnPressed.connect(self.set_flow_in_mfc)

        self.update_voltage_values = QtCore.QTimer(self)
        self.update_voltage_values.setInterval(1000)
        self.update_voltage_values.timeout.connect(self.update_voltage_reading)
        self.pushButton_forced_release.clicked.connect(self.release_getoffset)
        self.comboBox_element.addItems(get_atomic_symbol())
        self.pushButton_set_reference_foil.clicked.connect(self.set_auto_reference_foil)
        self.comboBox_element.currentIndexChanged.connect(self.populate_possible_edges)
        self.pushButton_set_ionchamber_gases.clicked.connect(self.set_ionchamber_gases)
        self.lineEdit_timer.setText(f"DONE")
        self.lineEdit_timer.setStyleSheet("background-color: green; color: white; font: 16px")
        self.comboBox_edge.currentIndexChanged.connect(self.update_edge_label)
        self.comboBox_edge.addItems(['K'])
        self.label_edge.setText(f"{4966:.0f} eV")

        self.update_voltage_values.start()
        self.flag = False

        self.timer_ionchamber = QTimer(self)
        self.timer_ionchamber.setInterval(1000)
        self.timer_ionchamber.timeout.connect(self.update_ionchamber_timer)
        self.timer_ionchamber.start()
        self.count = 600

    def set_i0_and_it_gases(self, gases_i0=None, gases_it=None):
        if 'helium' not in gases_i0.keys():
            getattr(self.mfc, 'ch1_he_sp').set(0)
        else:
            getattr(self.mfc, 'ch1_he_sp').set(gases_i0['helium'])

        getattr(self.mfc, 'ch2_n2_sp').set(gases_i0['nitrogen'])

        if 'argon' not in gases_i0.keys():
            getattr(self.mfc, 'ch3_ar_sp').set(0)
        else:
            getattr(self.mfc, 'ch3_ar_sp').set(gases_i0['argon'])

        getattr(self.mfc, 'ch4_n2_sp').set(gases_it['nitrogen'])
        getattr(self.mfc, 'ch5_ar_sp').set(gases_it['argon'])


    def update_ionchamber_timer(self):
        if self.flag:
            self.lineEdit_timer.setText(f"{self.count}")
            self.lineEdit_timer.setStyleSheet("background-color: red; color: white; font: 16px")
            self.count -= 1
        if self.count <= 0:
            self.flag = False
            self.count = 600

            _current_element = self.comboBox_element.currentText()
            _current_edge = self.comboBox_edge.currentText()
            gases_i0 = atomic_dict_for_ionchamber_gases[_current_element][_current_edge]['i0']['gases_final']
            gases_it = atomic_dict_for_ionchamber_gases[_current_element][_current_edge]['it']['gases_final']
            self.set_i0_and_it_gases(gases_i0=gases_i0, gases_it=gases_it)

            self.lineEdit_timer.setText(f"DONE")
            self.lineEdit_timer.setStyleSheet("background-color: green; color: white; font: 16px")





    def set_ionchamber_gases(self):
        _current_element = self.comboBox_element.currentText()
        _current_edge = self.comboBox_edge.currentText()

        gases_i0 = atomic_dict_for_ionchamber_gases[_current_element][_current_edge]['i0']['gases_initial']
        gases_it = atomic_dict_for_ionchamber_gases[_current_element][_current_edge]['it']['gases_initial']

        self.set_i0_and_it_gases(gases_i0=gases_i0, gases_it=gases_it)
        self.flag = True

    def set_auto_reference_foil(self):
        _current_element = self.comboBox_element.currentText()
        _current_edge = self.comboBox_edge.currentText()

        _element, _edge, _energy = find_correct_foil(element=_current_element, edge=_current_edge)
        if _element is not None:
            self.label_reference_foil.setText(f"{_element} {_edge} {_energy} eV")
        else:
            self.label_reference_foil.setText(f"None")
        if _element is not None:
            print(f'Setting Reference foil >>> Element:{_element} Edge:{_edge} Energy:{_energy} eV')
        else:
            print(f"No Reference foil found setting to None")
        uid = self.RE(self.service_plan_funcs['set Reference foil'](element=_element))


    def populate_possible_edges(self):
        self.comboBox_edge.blockSignals(True)

        current_element = self.comboBox_element.currentText()
        self.comboBox_edge.clear()
        possible_edges = get_possible_edges(element=current_element)
        self.comboBox_edge.addItems(possible_edges.keys())
        _first_element = list(possible_edges.values())[0]
        self.label_edge.setText(f"{_first_element:.0f} eV")
        self.comboBox_edge.blockSignals(False)


    def update_edge_label(self):
        possible_edges = get_possible_edges(element=self.comboBox_element.currentText())
        current_edge = self.comboBox_edge.currentText()
        try:
            self.label_edge.setText(f"{possible_edges[current_edge]:.0f}eV")
        except KeyError:
            print('Key Error try again')

    def release_getoffset(self):
        if self.pushButton_getoffsets.isEnabled():
            pass
        else:
            # self.RE.abort()
            self.pushButton_getoffsets.setEnabled(True)



    def set_current_suppr(self):
        sender_obj = QObject().sender()
        sender_obj_name = sender_obj.objectName()
        channel_index = sender_obj_name[11:]
        getattr(self.apb, channel_index).supr_mode.set(2).wait()


    def set_flow_in_mfc(self):
        sender_obj = QObject().sender()
        sender_obj_name = sender_obj.objectName()
        sender_obj_value = sender_obj.text()
        _gas_flow = float(sender_obj_value.split()[0])

        if sender_obj_name == 'lineEdit_ch1_he':
            _total = _gas_flow + self.mfc.ch2_n2_rb.get() + self.mfc.ch3_ar_rb.get()

            if self.mfc.ch2_n2_rb.get() < (_total * 0.1):
                message_box('Warning', 'Nitrogen flow rate must be 10% or more of total flow in all the ion chambers. Increase the N2 flow or contact beamline staff')
            else:
                mfc_index = sender_obj_name[9:]
                getattr(self.mfc, mfc_index + '_sp').set(_gas_flow).wait()

        if sender_obj_name == 'lineEdit_ch2_n2':
            _total = self.mfc.ch1_he_rb.get() + _gas_flow + self.mfc.ch3_ar_rb.get()

            if _gas_flow < (_total * 0.1):
                message_box('Warning', 'Nitrogen flow rate must be 10% or more of total flow in all the ion chambers. Increase the N2 flow or contact beamline staff')
            else:
                mfc_index = sender_obj_name[9:]
                getattr(self.mfc, mfc_index + '_sp').set(_gas_flow).wait()

        if sender_obj_name == 'lineEdit_ch3_ar':
            _total = self.mfc.ch1_he_rb.get() + self.mfc.ch2_n2_rb.get() + _gas_flow

            if self.mfc.ch2_n2_rb.get() < (_total * 0.1):
                message_box('Warning', 'Nitrogen flow rate must be 10% or more of total flow in all the ion chambers. Increase the N2 flow or contact beamline staff')
            else:
                mfc_index = sender_obj_name[9:]
                getattr(self.mfc, mfc_index + '_sp').set(_gas_flow).wait()

        if sender_obj_name == 'lineEdit_ch4_n2':
            _total = _gas_flow + self.mfc.ch5_ar_rb.get()

            if _gas_flow < (_total * 0.1):
                message_box('Warning', 'Nitrogen flow rate must be 10% or more of total flow in all the ion chambers. Increase the N2 flow or contact beamline staff')
            else:
                mfc_index = sender_obj_name[9:]
                getattr(self.mfc, mfc_index + '_sp').set(_gas_flow).wait()

        if sender_obj_name == 'lineEdit_ch5_ar':
            _total = self.mfc.ch4_n2_rb.get() + _gas_flow

            if self.mfc.ch4_n2_rb.get() < (_total * 0.1):
                message_box('Warning', 'Nitrogen flow rate must be 10% or more of total flow in all the ion chambers. Increase the N2 flow or contact beamline staff')
            else:
                mfc_index = sender_obj_name[9:]
                getattr(self.mfc, mfc_index + '_sp').set(_gas_flow).wait()




    def update_gain(self):
        sender_obj = QObject().sender()
        sender_obj_value = sender_obj.currentIndex()
        sender_obj_name = sender_obj.objectName()
        channel_index = sender_obj_name[11:12]
        # getattr(self.apb, 'amp_ch' + channel_index).gain.set(sender_obj_value).wait()
        getattr(self.apb, 'amp_ch' + channel_index).gain.put(sender_obj_value)
    #
    def add_gain_subscriptions(self, ch):
        getattr(self, 'comboBox_ch' + str(ch) + '_gain').addItems(self._gains)
        def update_gain_value(value, **kwargs):
            try:
                getattr(self, 'comboBox_ch' + str(ch) + '_gain').setCurrentIndex(value)
            except:
                pass
        getattr(self.apb, 'amp_ch' + str(ch)).gain.subscribe(update_gain_value)

    def update_voltage_reading(self):
        for channel in self._ion_chambers:
            _plate = getattr(self.wps, channel + '_plate_rb').get()
            _grid = getattr(self.wps, channel + '_grid_rb').get()
            if _plate > -1650:
                getattr(self, 'lineEdit_' + channel + "_plateV").setStyleSheet("border : 2px solid red;")
            else:
                getattr(self, 'lineEdit_' + channel + "_plateV").setStyleSheet("border : 2px solid green;")
            getattr(self, 'lineEdit_' + channel + "_plateV").setText(f"{_plate:4.2f} V")

            if _grid > -1490:
                getattr(self, 'lineEdit_' + channel + "_gridV").setStyleSheet("border : 2px solid red;")
            else:
                getattr(self, 'lineEdit_' + channel + "_gridV").setStyleSheet("border : 2px solid green;")
            getattr(self, 'lineEdit_' + channel + "_gridV").setText(f"{_grid:4.2f} V")

    def get_offsets(self):
        self.pushButton_getoffsets.setEnabled(False)
        sys.stdout = self.parent_gui.emitstream_out
        if self.parent_gui.hutch == 'b':
            self.RE(self.service_plan_funcs['get_offsets'](hutch_c = False))
        if self.parent_gui.hutch == 'c':
            self.RE(self.service_plan_funcs['get_offsets'](hutch_c = True))

        self.pushButton_getoffsets.setEnabled(True)







    # def add_ion_chambers_plate_subscriptions(self, ch, ic):
    #     def update_wps_grid_readback(value, **kwargs):
    #         try:
    #             if value > -1490:
    #                 getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setStyleSheet("border : 2px solid red;")
    #             else:
    #                 getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setStyleSheet("border : 2px solid green;")
    #             getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setText(f"{value:4.2f} V")
    #         except:
    #             pass
    #     getattr(self.wps, ic + '_grid_rb').subscribe(update_wps_grid_readback)
    #
    # def add_ion_chambers_grid_subscriptions(self, ch, ic):
    #     def update_wps_plate_readback(value, **kwargs):
    #         try:
    #             if value > -1650:
    #                 getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setStyleSheet("border : 2px solid red;")
    #             else:
    #                 getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setStyleSheet("border : 2px solid green;")
    #             getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setText(f"{value:4.2f} V")
    #         except:
    #             pass
    #
    #     getattr(self.wps, ic + '_plate_rb').subscribe(update_wps_plate_readback)


    def add_mfc_subscriptions(self, channel):
        def update_mfc_readback(value, **kwargs):
            try:
                getattr(self, 'label_' + channel).setText(f"{value:.2f} sccm")
            except:
                pass

        getattr(self.mfc, channel + '_rb').subscribe(update_mfc_readback)