import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject
from functools import partial

from isstools.dialogs.BasicDialogs import message_box
from isstools.widgets.widget_motors import UIWidgetMotors

# from isstools.dialogs import UpdateUserDialog

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_user_motors.ui')

class UIUserMotors(*uic.loadUiType(ui_path)):
    def __init__(self,
                 motors_dict=None,
                 apb=None,
                 wps = None,
                 mfc = None,
                 parent_gui=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.parent_gui = parent_gui
        self.motors_dict = motors_dict
        self.wps = wps
        self.mfc = mfc
        self.apb = apb

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

        self._mfc_channels = ['ch1_he', 'ch2_n2', 'ch3_ar', 'ch4_n2', 'ch5_ar']

        for i in range(1,5):
            self.add_gain_subscriptions(i)
        #     # getattr()
            getattr(self, 'comboBox_ch' + str(i) + '_gain').currentIndexChanged.connect(self.update_gain)
            getattr(self, 'pushButton_amp_ch' + str(i)).clicked.connect(self.set_current_suppr)

        self._ion_chambers = ['i0', 'it', 'ir']
        for i, ic in enumerate(self._ion_chambers):
            self.add_ion_chambers_plate_subscriptions(i+1, ic)

        for i, ic in enumerate(self._ion_chambers):
            self.add_ion_chambers_grid_subscriptions(i+1, ic)

        for channel in self._mfc_channels:
            self.add_mfc_subscriptions(channel)
            getattr(self, 'lineEdit_' + channel).returnPressed.connect(self.set_flow_in_mfc)


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
        getattr(self.apb, 'amp_ch' + channel_index).gain.set(sender_obj_value).wait()
    #
    def add_gain_subscriptions(self, ch):
        getattr(self, 'comboBox_ch' + str(ch) + '_gain').addItems(self._gains)
        def update_gain_value(value, **kwargs):
            try:
                getattr(self, 'comboBox_ch' + str(ch) + '_gain').setCurrentIndex(value)
            except:
                pass
        getattr(self.apb, 'amp_ch' + str(ch)).gain.subscribe(update_gain_value)


    def add_ion_chambers_plate_subscriptions(self, ch, ic):
        def update_wps_grid_readback(value, **kwargs):
            try:
                if value < 1490:
                    getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setStyleSheet("border : 2px solid red;")
                else:
                    getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setStyleSheet("border : 2px solid green;")
                getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setText(f"{value:4.2f} V")
            except:
                pass
        getattr(self.wps, ic + '_grid_rb').subscribe(update_wps_grid_readback)

    def add_ion_chambers_grid_subscriptions(self, ch, ic):
        def update_wps_plate_readback(value, **kwargs):
            try:
                if value < 1650:
                    getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setStyleSheet("border : 2px solid red;")
                else:
                    getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setStyleSheet("border : 2px solid green;")
                getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setText(f"{value:4.2f} V")
            except:
                pass

        getattr(self.wps, ic + '_plate_rb').subscribe(update_wps_plate_readback)


    def add_mfc_subscriptions(self, channel):
        def update_mfc_readback(value, **kwargs):
            try:
                getattr(self, 'label_' + channel).setText(f"{value:.2f} sccm")
            except:
                pass

        getattr(self.mfc, channel + '_rb').subscribe(update_mfc_readback)