import time
from PyQt5 import uic, QtCore, QtWidgets
import pkg_resources


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
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # Initialize Ophyd elements
        self.shutters_sig.connect(self.change_shutter_color)
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
