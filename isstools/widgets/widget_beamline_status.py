import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources


from isstools.dialogs import UpdateUserDialog


ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_beamline_status.ui')


class UIBeamlineStatus(*uic.loadUiType(ui_path)):
    shutters_sig = QtCore.pyqtSignal()
    def __init__(self,
                 shutters={},
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # Initialize Ophyd elements
        self.shutters_sig.connect(self.change_shutter_color)
        self.shutters = shutters

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

            if hasattr(item.status, 'subscribe'):
                item.button = button
                item.status.subscribe(self.update_shutter)

                def toggle_shutter_call(shutter):
                    def toggle_shutter():
                        if shutter.status.value == 'Open':
                            st = shutter.set('Close')
                        else:
                            st = shutter.set('Open')
                        while True:
                            if not st.done:
                                time.sleep(0.01)
                            else:
                                break
                    return toggle_shutter

                button.clicked.connect(toggle_shutter_call(item))

                if item.status.value == 'Open':
                    button.setStyleSheet("background-color: lime")
                else:
                    button.setStyleSheet("background-color: red")

        if self.horizontalLayout_shutters.count() <= 1:
            self.groupBox_shutters.setVisible(False)

    def update_shutter(self, pvname=None, value=None, char_value=None, **kwargs):
        if 'obj' in kwargs.keys():
            if hasattr(kwargs['obj'].parent, 'button'):
                self.current_button = kwargs['obj'].parent.button
                if kwargs['obj'].value == 'Open':
                    self.current_button_color = 'lime'
                else:
                    self.current_button_color = 'red'

                self.shutters_sig.emit()

    def change_shutter_color(self):
        self.current_button.setStyleSheet("background-color: " + self.current_button_color)
