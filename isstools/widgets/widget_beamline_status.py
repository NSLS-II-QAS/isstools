import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources
from PyQt5.Qt import QObject, QTimer
from xraydb import ionchamber_fluxes as ionfl
import numpy as np

from time import sleep as slp

from isstools.dialogs import UpdateUserDialog
from functools import partial

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
                 apb_c=None,
                 mono=None,
                 mfc=None,
                 parent_gui=None,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # Initialize Ophyd elements
        self.shutters_sig.connect(self.change_shutter_color)
        self.apb = apb
        self.apb_c = apb_c
        self.mono = mono
        self.parent_gui = parent_gui
        self.mfc = mfc

        self._old_value = [0]
        self._value = [0]

        wfm_length = self.apb.wf_len.get()
        self.lineEdit_wfm_length.setText(f"{wfm_length}")
        self.lineEdit_wfm_length.returnPressed.connect(self.update_wfm_length)

        fa_sample = self.apb.sample_len.get()
        self.lineEdit_fa_sample.setText(f"{fa_sample}")

        daq_rate_b = self.apb.acq_rate.get()
        self.spinBox_daq_rate_b.setValue(daq_rate_b)

        daq_rate_c = self.apb_c.acq_rate.get()
        self.spinBox_daq_rate_c.setValue(daq_rate_c)

        self.spinBox_daq_rate_b.valueChanged.connect(self.update_daq_rate)
        self.pushButton_update_wfm.clicked.connect(self.update_wfm_parameters)
        self.spinBox_daq_rate_c.valueChanged.connect(self.update_daq_rate)

        self.radioButton_hutch_b.toggled.connect(self.select_hutch)

        self.voltage_channels = ['vi0', 'vit', 'vir', 'vip']

        # for channel in self.voltage_channels:
        #     getattr(self, 'lineEdit_' + channel).setStyleSheet("background-color : blue; color: white;")
        #     self.add_voltage_subscriptions(channel)

        self.timer_update_ic_voltages = QTimer(self)
        self.timer_update_ic_voltages.setInterval(100)
        self.timer_update_ic_voltages.timeout.connect(self.update_ic_voltages)
        self.timer_update_ic_voltages.start()

        self.timer_update_flux = QTimer(self)
        self.timer_update_flux.setInterval(1000)
        self.timer_update_flux.timeout.connect(self.update_flux)
        self.timer_update_flux.start()

        enc_rate_in_points = mono.enc.filter_dt.get()
        enc_rate = 1 / (enc_rate_in_points * 10 * 1e-9) / 1e3
        # TODO Something is fishy here
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
            button.setFixedSize(int(self.height() * 0.5), int(self.height() * 0.5))
            self.shutter_layout.addWidget(button)
            # button.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)

            self.horizontalLayout_shutters.addLayout(self.shutter_layout)

            self.shutters_buttons.append(button)
            button.setFixedWidth(int(button.height() * 1.2))
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
                        shutter.set(toggle_map[state]).wait(timeout=5)

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

    def get_gas_composition_dict(self, key='vi0'):
        gases = {}
        total_flow = 0
        if key == 'vi0':
            keys = ['Helium', 'Nitrogen', 'Argon']
            index = np.arange(1, 4, 1)
            for i, _gas, _key in zip(index, ['he', 'n2', 'ar'], keys):
                _current_flow = getattr(self.mfc, 'ch' + str(i) + '_' + _gas + '_rb').get()
                total_flow += _current_flow
                gases[_key] = _current_flow

            for _key in keys:
                gases[_key] = gases[_key] / total_flow

        elif key == 'vit' or key == 'vir':
            keys = ['Nitrogen', 'Argon']
            index = np.arange(4, 6, 1)
            for i, _gas, _key in zip(index, ['n2', 'ar'], keys):
                _current_flow = getattr(self.mfc, 'ch' + str(i) + '_' + _gas + '_rb').get()
                total_flow += _current_flow
                gases[_key] = _current_flow

            for _key in keys:
                gases[_key] = gases[_key] / total_flow
        else:
            gases['nitrogen'] = 100
        return gases

    def compute_ionization_chamber_flux(self, ionchamber='vi0', channel='ch1'):
        gases = self.get_gas_composition_dict(key=ionchamber)
        energy = self.mono.energy.user_readback.get()
        voltage = getattr(self.apb, ionchamber).get()
        gain = getattr(self.apb, 'amp_' + channel).gain.get() + 3
        flux = ionfl(gas=gases, volts=voltage, length=14.5, energy=energy, sensitivity=pow(10, -gain))
        return flux

    # def add_voltage_subscriptions(self, channel):
    #     def update_voltage(value, old_value, **kwargs):
    #         self._value = [0]
    #         self._old_value = [0]
    #         self._value.append(value)
    #         self._old_value.append(old_value)
    #         # self.update_text(value, old_value, channel)
    #         # pass
    #         # if abs(value-old_value) > 0.1:
    #         #     getattr(self, 'lineEdit_'+ channel).setText(f"{value:1.2f}")
    #         #     if value >= 8:
    #         #         getattr(self, 'lineEdit_' + channel).setStyleSheet("background-color : red; color: white;")
    #         #     else:
    #         #         getattr(self, 'lineEdit_' + channel).setStyleSheet("background-color : blue; color: white;")
    #     getattr(self.apb, channel).subscribe(update_voltage)

    def update_flux(self):
        for volt_ch, ch in zip(self.voltage_channels, ['ch1', 'ch2', 'ch3', 'ch4']):
            flux = self.compute_ionization_chamber_flux(ionchamber=volt_ch, channel=ch)
            if flux.transmitted < 1E6:
                getattr(self, 'lineEdit_' + volt_ch + '_phs').setText(f"{0}")
            else:
                getattr(self, 'lineEdit_' + volt_ch + '_phs').setText(f"{flux.transmitted:1.2g}")
            getattr(self, 'lineEdit_' + volt_ch + '_phs').setStyleSheet("background-color: green; color: white; font: 16px;")


    def update_ic_voltages(self):
        for channel, ch in zip(self.voltage_channels, ['ch1', 'ch2', 'ch3', 'ch4']):
            channel_voltage = getattr(self.apb, channel).get()
            getattr(self, 'lineEdit_' + channel).setText(f"{channel_voltage:1.2f}")
            if channel_voltage >= 8:
                getattr(self, 'lineEdit_' + channel).setStyleSheet("background-color : red; color: white;")
            else:
                getattr(self, 'lineEdit_' + channel).setStyleSheet("background-color : blue; color: white;")


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
        # elf.mono.enc.filter_dt, rate_in_points_rounded, wait=True))

        # self.RE(bps.abs_set(self.mono.enc.filter_dt, rate_in_points, wait=True))

    def select_hutch(self):
        if self.radioButton_hutch_c.isChecked():
            self.parent_gui.hutch = 'c'
            self.parent_gui.widget_batch_mode.widget_batch_manual.checkBox_hutch_c.setChecked(True)
        elif self.radioButton_hutch_b.isChecked():
            self.parent_gui.hutch = 'b'
            self.parent_gui.widget_batch_mode.widget_batch_manual.checkBox_hutch_c.setChecked(False)

    def update_wfm_length(self):
        _input = self.lineEdit_wfm_length.text()
        _wf_length = float(_input.split()[0])
        self.apb.wf_len.set(_wf_length).wait()

    def update_wfm_parameters(self):
        _wf_length = self.apb.wf_len.get()
        self.lineEdit_wfm_length.setText(f"{_wf_length:.1f}")

        _fa_sample = self.apb.sample_len.get()
        self.lineEdit_fa_sample.setText(f"{_fa_sample:.1f}")
