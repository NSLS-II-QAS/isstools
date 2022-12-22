import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject

from isstools.dialogs import UpdateUserDialog


ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_beamline_status.ui')

def get_state(shutter):
    """Get the state of the shutters in a uniform way.
    
    This assumes that:
        - shutter.read() returns exactly 1 reading
        - that reading is the state of the shutter


    We need this function because the shutters at QAS have significant
    non-uniformity in their implementation / nameing conventions.

    Parameters
    ----------
    shutter : Device
        An ophyd device that you claim is a shutter.

    Returns
    -------
    str
        The state of the shutter as a string.
    """
    return list(shutter.read().values())[0]['value']



class UIBeamlineStatus(*uic.loadUiType(ui_path)):
    shutters_sig = QtCore.pyqtSignal()
    def __init__(self,
                 shutters={},
                 apb=None,
                 apb_c = None,
                 mono=None,
                 parent_gui=None,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # Initialize Ophyd elements
        self.shutters_sig.connect(self.change_shutter_color)
        self.apb = apb
        self.apb_c = apb_c
        self.mono = mono
        self.parent_gui=parent_gui


        daq_rate_b = self.apb.acq_rate.get()
        self.spinBox_daq_rate_b.setValue(daq_rate_b)


        daq_rate_c = self.apb_c.acq_rate.get()
        self.spinBox_daq_rate_c.setValue(daq_rate_c)

        self.spinBox_daq_rate_b.valueChanged.connect(self.update_daq_rate)
        self.spinBox_daq_rate_c.valueChanged.connect(self.update_daq_rate)


        self.radioButton_hutch_b.toggled.connect(self.select_hutch)

        enc_rate_in_points = mono.enc.filter_dt.get()
        enc_rate = 1 / (enc_rate_in_points * 10 * 1e-9) / 1e3
        #TODO Something is fishy here
        self.spinBox_enc_rate.setValue(enc_rate)
        self.spinBox_enc_rate.valueChanged.connect(self.update_enc_rate)

        self.shutters = shutters
        self.color_map = {'Open': 'lime', 'Close': 'red', 'Not Open': 'red'}
        self.shutters_buttons = []
        for key, item in self.shutters.items():
            self.shutter_layout = QtWidgets.QVBoxLayout()

            label = QtWidgets.QLabel(key)
            label.setAlignment(QtCore.Qt.AlignCenter)
            self.shutter_layout.addWidget(label)
            label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

            button = QtWidgets.QPushButton('')
            button.setFixedSize(self.height() * 0.5, self.height() * 0.5)
            self.shutter_layout.addWidget(button)
            # button.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)

            self.horizontalLayout_shutters.addLayout(self.shutter_layout)

            self.shutters_buttons.append(button)
            button.setFixedWidth(button.height() * 1.2)
            QtCore.QCoreApplication.processEvents()

            if hasattr(item, 'status') and hasattr(item.status, 'subscribe'):
                item.button = button
                item.status.subscribe(self.update_shutter)
               

                def toggle_shutter_call(shutter):
                    
                    def toggle_shutter():
                        state = get_state(shutter)
                        toggle_map = {'Open': "Close",
                            "Close": "Open",
                            "Not Open": "Open"}
                        shutter.set(toggle_map[state]).wait(timeout=1)
                        
                    return toggle_shutter

                button.clicked.connect(toggle_shutter_call(item))
                state = get_state(item)
          
                button.setStyleSheet(f"background-color: {self.color_map[state]}")
          
        if self.horizontalLayout_shutters.count() <= 1:
            self.groupBox_shutters.setVisible(False)

    def update_shutter(self, pvname=None, value=None, char_value=None, **kwargs):
        if 'obj' in kwargs.keys():
            if hasattr(kwargs['obj'].parent, 'button'):
                self.current_button = kwargs['obj'].parent.button
                state = get_state(kwargs['obj'])
                self.current_button_color = self.color_map[state]
                
                self.shutters_sig.emit()

    def change_shutter_color(self):
        self.current_button.setStyleSheet("background-color: " + self.current_button_color)


    def update_daq_rate(self):
        sender_object = QObject().sender()
        daq_rate = sender_object.value()
        # 374.94 is the nominal RF frequency
        divider = int(374.94 / daq_rate)
        if self.parent_gui.hutch == 'b':
             self.apb.divide.set(divider)
        elif self.parent_gui.hutch == 'c':
            self.apb_c.divide.set(divider)

    def update_enc_rate(self):
        enc_rate = self.spinBox_enc_rate.value()
        rate_in_points = (1 / (enc_rate * 1e3)) * 1e9 / 10

        rate_in_points_rounded = int(np.ceil(rate_in_points / 100.0) * 100)
        #elf.mono.enc.filter_dt, rate_in_points_rounded, wait=True))

        # self.RE(bps.abs_set(self.mono.enc.filter_dt, rate_in_points, wait=True))

    def select_hutch(self):
        if self.radioButton_hutch_c.isChecked():
            self.parent_gui.hutch = 'c'
            self.parent_gui.widget_batch_mode.widget_batch_manual.checkBox_hutch_c.setChecked(True)
        elif self.radioButton_hutch_b.isChecked():
            self.parent_gui.hutch = 'b'
            self.parent_gui.widget_batch_mode.widget_batch_manual.checkBox_hutch_c.setChecked(False)

