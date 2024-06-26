import time
from PyQt5 import uic, QtCore, QtWidgets
from PyQt5.QtWidgets import QLabel, QPushButton, QLineEdit
import pkg_resources
from PyQt5.Qt import QObject
from isstools.dialogs.UpdateMotorLimit import UIUpdateMotorLimit

# from isstools.dialogs import UpdateUserDialog

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_widget_motor.ui')

class MyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(MyLineEdit, self).__init__(parent)
    def mousePressEvent(self, e):
        try:
            self.selectAll()
        except Exception as e:
            print(f'Error: {e}')

class UIWidgetMotors(*uic.loadUiType(ui_path)):
    def __init__(self,
                 this_motor_dictionary=None, # "this" is to emphasize that the dict is for a specific motor!
                 parent=None,
                 *args, **kwargs
                 ):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.parent = parent
        self.width = 800

        self.motor_dict = this_motor_dictionary
        self._motor_object = self.motor_dict['object']

        self.label_motor_description = QLabel("")

        self.layout_motor_widget = self.horizontalLayout_motor
        self.label_motor_description.setText(self.motor_dict['keyword'])
        self.label_motor_description.setFixedWidth(160)
        self.layout_motor_widget.addWidget(self.label_motor_description)

        self.label_mov_status = QLabel("      ")
        self.label_mov_status.setStyleSheet('background-color: rgb(55,130,60)')
        self.label_mov_status.setFixedHeight(20)
        self.layout_motor_widget.addWidget(self.label_mov_status)

        # self.lineEdit_setpoint = QLineEdit("")
        self.lineEdit_setpoint = MyLineEdit("")
        _user_setpoint = f"{self._motor_object.user_setpoint.get():3.3f} { self._motor_object.egu}"
        self.lineEdit_setpoint.setText(_user_setpoint)
        self.lineEdit_setpoint.setFixedWidth(100)
        self.layout_motor_widget.addWidget(self.lineEdit_setpoint)
        self.lineEdit_setpoint.returnPressed.connect(self.update_set_point)
        self._motor_object.user_setpoint.subscribe(self.update_set_point_value)

        self.label_low_limit = QLabel("      ")
        self.label_low_limit.setStyleSheet('background-color: rgb(94,20,20)')
        self.label_low_limit.setFixedHeight(20)
        self._motor_object.low_limit_switch.subscribe(self.update_motor_llim_status)
        self.layout_motor_widget.addWidget(self.label_low_limit)

        self.label_motor_readback = QLabel("")
        self.label_motor_readback.setFixedWidth(80)
        self._motor_object.user_readback.subscribe(self.update_readback)
        self._motor_object.motor_is_moving.subscribe(self.update_moving_label)
        self.layout_motor_widget.addWidget(self.label_motor_readback)

        self.label_high_limit = QLabel("      ")
        self.label_high_limit.setStyleSheet('background-color: rgb(94,20,20)')
        self.label_high_limit.setFixedHeight(20)
        self._motor_object.high_limit_switch.subscribe(self.update_motor_hlim_status)
        self.layout_motor_widget.addWidget(self.label_high_limit)

        self.button_move_decrement = QPushButton("<")
        self.button_move_decrement.setFixedWidth(30)
        self.layout_motor_widget.addWidget(self.button_move_decrement)
        self.button_move_decrement.clicked.connect(self.update_decrement)

        # self.lineEdit_step = QLineEdit("")
        self.lineEdit_step = MyLineEdit("")
        self.lineEdit_step.setFixedWidth(100)
        self._motor_object.twv.subscribe(self.update_step_value)
        self.layout_motor_widget.addWidget(self.lineEdit_step)
        self.lineEdit_step.returnPressed.connect(self.update_step)

        self.button_move_increment = QPushButton(">")
        self.button_move_increment.setFixedWidth(30)
        self.layout_motor_widget.addWidget(self.button_move_increment)
        self.button_move_increment.clicked.connect(self.update_increment)

        self.button_stop_motor = QPushButton("Stop")
        self.layout_motor_widget.addWidget(self.button_stop_motor)
        self.button_stop_motor.clicked.connect(self.stop_the_motor)

        # self.button_change_limts = QPushButton("Change limit")
        # self.layout_motor_widget.addWidget(self.button_change_limts)
        # self.button_change_limts.clicked.connect(self.update_lo_hi_limit)


    def update_step_value(self, value, **kwargs):
        self.lineEdit_step.setText(f'{value:.3f} {self._motor_object.egu}')

    def update_moving_label(self, value, **kwargs):
        if value == 1:
            self.label_mov_status.setStyleSheet('background-color: rgb(95,249,95)')
        else:
            self.label_mov_status.setStyleSheet('background-color: rgb(55,130,60)')

    def update_set_point(self):
        _read_desired_setpoint = self.lineEdit_setpoint.text()
        _desired_setpoint = float(_read_desired_setpoint.split()[0])
        _set_obj = self._motor_object.set(_desired_setpoint)

    def update_set_point_value(self, value, **kwargs):
        self.lineEdit_setpoint.setText(f"{value:3.3f} {self._motor_object.egu}")

    def update_readback(self, value, **kwargs):
        self.label_motor_readback.setText(f"{value:3.3f} {self._motor_object.egu}")

    def update_motor_hlim_status(self, value, **kwargs):
        if value == 1:
            self.label_high_limit.setStyleSheet('background-color: rgb(255,0,0)')
        else:
            self.label_high_limit.setStyleSheet('background-color: rgb(94,20,20)')

    def update_motor_llim_status(self, value, **kwargs):
        if value == 1:
            self.label_low_limit.setStyleSheet('background-color: rgb(255,0,0)')
        else:
            self.label_low_limit.setStyleSheet('background-color: rgb(94,20,20)')

    def update_decrement(self):
        self._motor_object.twr.put(1)


    def update_step(self):
        _user_step_reading = self.lineEdit_step.text()
        _step_convert = float(_user_step_reading.split()[0])
        _step_text = f"{_step_convert:3.3f} {self._motor_object.egu}"
        self.lineEdit_step.setText(_step_text)
        self._motor_object.twv.set(_step_convert)

    def update_increment(self):
        self._motor_object.twf.put(1)

    def stop_the_motor(self):
        self._motor_object.stop()

    # def update_lo_hi_limit(self):
    #     dlg = UIUpdateMotorLimit("", self._motor_object, parent=self)
    #     if dlg.exec_():
    #         pass