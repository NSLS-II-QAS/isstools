import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject
from functools import partial

from isstools.widgets.widget_motors import UIWidgetMotors

# from isstools.dialogs import UpdateUserDialog

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_user_motors.ui')

class UIUserMotors(*uic.loadUiType(ui_path)):
    def __init__(self,
                 motors_dict=None,
                 apb=None,
                 wps = None,
                 parent_gui=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.parent_gui = parent_gui
        self.motors_dict = motors_dict
        self.wps = wps
        self.apb = apb

        self._sample_stage_motors = ['sample_stage1_rotary',
                                     'sample_stage1_x',
                                     'sample_stage1_y',
                                     'sample_stage1_z',
                                     'sample_stage1_theta',
                                     'sample_stage1_chi']

        for motor in self._sample_stage_motors:
            self.verticalLayout_sample_motors.addWidget(UIWidgetMotors(self.motors_dict[motor]))


        self._gains = [f"1E{f:.0f} V/A" for f in range(3,11)]

        for i in range(1,5):
            self.add_gain_subscriptions(i)
        #     # getattr()
            getattr(self, 'comboBox_ch' + str(i) + '_gain').currentIndexChanged.connect(self.update_gain)

        self._ion_chambers = ['i0', 'it', 'ir']
        for i, ic in enumerate(self._ion_chambers):
            self.add_ion_chambers_plate_subscriptions(i+1, ic)

        for i, ic in enumerate(self._ion_chambers):
            self.add_ion_chambers_grid_subscriptions(i+1, ic)

        # for

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
            getattr(self, 'comboBox_ch' + str(ch) + '_gain').setCurrentIndex(value)
        getattr(self.apb, 'amp_ch' + str(ch)).gain.subscribe(update_gain_value)


    def add_ion_chambers_plate_subscriptions(self, ch, ic):
        def update_wps_grid_readback(value, **kwargs):
            if value < 1490:
                getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setStyleSheet("border : 2px solid red;")
            else:
                getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setStyleSheet("border : 2px solid green;")
            getattr(self, 'lineEdit_ch' + str(ch) + "_gridV").setText(f"{value:4.2f} V")

        getattr(self.wps, ic + '_grid_rb').subscribe(update_wps_grid_readback)

    def add_ion_chambers_grid_subscriptions(self, ch, ic):
        def update_wps_plate_readback(value, **kwargs):
            if value < 1650:
                getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setStyleSheet("border : 2px solid red;")
            else:
                getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setStyleSheet("border : 2px solid green;")
            getattr(self, 'lineEdit_ch' + str(ch) + "_plateV").setText(f"{value:4.2f} V")

        getattr(self.wps, ic + '_plate_rb').subscribe(update_wps_plate_readback)