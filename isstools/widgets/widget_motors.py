import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject

# from isstools.dialogs import UpdateUserDialog

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_widget_motors.ui')

class UIMotorWidget(*uic.loadUiType(ui_path)):
    def __init__(self,
                 this_motor_dict=None,
                 parent_gui=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.parent_gui = parent_gui
        self.this_motor_dict = this_motor_dict

