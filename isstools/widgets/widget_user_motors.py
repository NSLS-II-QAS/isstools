import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject

from isstools.widgets.widget_motors import UIWidgetMotors

# from isstools.dialogs import UpdateUserDialog

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_user_motors.ui')

class UIUserMotors(*uic.loadUiType(ui_path)):
    def __init__(self,
                 motors_dict=None,
                 parent_gui=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.parent_gui = parent_gui
        self.motors_dict = motors_dict

        self._sample_stage_motors = ['sample_stage1_rotary',
                                     'sample_stage1_x',
                                     'sample_stage1_y',
                                     'sample_stage1_z',
                                     'sample_stage1_theta',
                                     'sample_stage1_chi']

        for motor in self._sample_stage_motors:
            self.verticalLayout_sample_motors.addWidget(UIWidgetMotors(self.motors_dict[motor]))