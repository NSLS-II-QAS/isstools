
from PyQt5 import uic, QtGui, QtCore
import pkg_resources
import requests
import urllib.request

import itertools

from isstools.dialogs import UpdateUserDialog
from timeit import default_timer as timer

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_general_info.ui')


class UIGeneralInfo(*uic.loadUiType(ui_path)):
    @QtCore.pyqtSlot()
    def __init__(self,
                 accelerator=None,
                 RE = None,
                 db = None,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        # Start QTimer to display current day and time
        self.timer_update_time = QtCore.QTimer(self)
        self.timer_update_time.setInterval(1000)
        self.timer_update_time.timeout.connect(self.update_time)
        self.timer_update_time.start()

        self.timer_update_weather = QtCore.QTimer(self)
        self.timer_update_weather.singleShot(0, self.update_weather)
        self.timer_update_weather.setInterval(1000*60*5)
        self.timer_update_weather.timeout.connect(self.update_weather)
        self.timer_update_weather.start()
        self.counter = itertools.count()

        self.RE = RE
        self.db = db
        if self.RE is not None:
            self.RE.is_aborted = False
            self.timer_update_user_info = QtCore.QTimer()
            self.timer_update_user_info.timeout.connect(self.update_user_info)
            self.timer_update_user_info.start(60*1000)
            self.timer_update_user_info.singleShot(0, self.update_user_info)
            self.push_set_user_info.clicked.connect(self.set_user_info)
        else:
            self.push_update_user.setEnabled(False)


        # Initialize general settings
        self.accelerator = accelerator
        self.accelerator.beam_current.subscribe(self.update_beam_current)
        self.accelerator.status.subscribe(self.update_accelerator_status)

    def update_weather(self):
        # try:
        #     current_weather = requests.get(
        #         'http://api.openweathermap.org/data/2.5/weather?zip=11973&APPID=a3be6bc4eaf889b154327fadfd9d6532').json()
        #     string_current_weather  = current_weather['weather'][0]['main'] + ' in Upton, NY,  it is {0:.0f} °F outside,\
        #         humidity is {1:.0f}%'\
        #         .format(((current_weather['main']['temp']-273)*1.8+32), current_weather['main']['humidity'])
        #     icon_url = 'http://openweathermap.org/img/w/' + current_weather['weather'][0]['icon'] + '.png'
        #     image = QtGui.QImage()
        #     image.loadFromData(urllib.request.urlopen(icon_url).read())
        #     self.label_current_weather_icon.setPixmap(QtGui.QPixmap(image))
        # except:
        string_current_weather = 'Weather information not available'
        self.label_current_weather.setText(string_current_weather)

    def update_time(self):
        self.label_current_time.setText(
            'Today is {0}'.format(QtCore.QDateTime.currentDateTime().toString('MMMM d, yyyy, h:mm:ss ap')))

    @QtCore.pyqtSlot(QtGui.QColor)
    def update_beam_current(self, **kwargs):
        # print(f"{kwargs = }")
        rgb_list = [255, 255, 255]
        current = float(kwargs['value'])
        rgb = int(min(255, abs(current - 400) * 100))
        pos = next(self.counter) % 3
        rgb_list[pos] = rgb
        rgb_str = ",".join([str(x) for x in rgb_list])
        print(f"RGB string: {rgb_str}")
        self.label_beam_current.setText(f'Beam current is {current:.1f} mA')
        self.label_accelerator_status.setText(f'Beam has dumped {pos}')
        self.label_accelerator_status.setStyleSheet(f'color: rgb({rgb_str})')
        # self.label_accelerator_status_indicator.setStyleSheet(f'background-color: rgb({rgb_str})')

    def update_accelerator_status(self, **kwargs):
        if kwargs['value'] == 0:
            self.label_accelerator_status.setText('Beam available')
            self.label_accelerator_status.setStyleSheet('color: rgb(19,139,67)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(95,249,95)')
        elif kwargs['value'] == 1:
            self.label_accelerator_status.setText('Setup')
            self.label_accelerator_status.setStyleSheet('color: rgb(209,116,42)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(246,229,148)')
        elif kwargs['value'] == 2:
            self.label_accelerator_status.setText('Accelerator studies')
            self.label_accelerator_status.setStyleSheet('color: rgb(209,116,42)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(209,116,42)')
        elif kwargs['value'] == 3:
            self.label_accelerator_status.setText('Beam has dumped')
            self.label_accelerator_status.setStyleSheet('color: rgb(237,30,30)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(237,30,30)')
        elif kwargs['value'] == 4:
            self.label_accelerator_status.setText('Maintenance')
            self.label_accelerator_status.setStyleSheet('color: rgb(209,116,42)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(200,149,251)')
        elif kwargs['value'] == 5:
            self.label_accelerator_status.setText('Shutdown')
            self.label_accelerator_status.setStyleSheet('color: rgb(190,190,190)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(190,190,190)')
        elif kwargs['value'] == 6:
            self.label_accelerator_status.setText('Unscheduled ops')
            self.label_accelerator_status.setStyleSheet('color: rgb(19,139,67)')
            self.label_accelerator_status_indicator.setStyleSheet('background-color: rgb(0,177,0)')

    def update_user_info(self):
        self.label_user_info.setText('{} is running  under Proposal {}/SAF {} '.
                                     format(self.RE.md['PI'], self.RE.md['PROPOSAL'], self.RE.md['SAF']))
        self.cycle = ['', 'Spring', 'Summer', 'Fall']
        self.label_current_cycle.setText(
            'It is {} {} NSLS Cycle'.format(self.RE.md['year'], self.cycle[int(self.RE.md['cycle'])]))

    def set_user_info(self):
        dlg = UpdateUserDialog.UpdateUserDialog(self.RE.md['year'], self.RE.md['cycle'], self.RE.md['PROPOSAL'],
                                                self.RE.md['SAF'], self.RE.md['PI'], parent=self)
        if dlg.exec_():
            start = timer()
            self.RE.md['year'], self.RE.md['cycle'], self.RE.md['PROPOSAL'], self.RE.md['SAF'], self.RE.md[
                'PI'] = dlg.getValues()
            print('2')
            stop1 = timer()
            self.update_user_info()
            print('3')
            stop2 = timer()
            print(stop1 - start)
            print(stop2 - start)
