import inspect
import re
import pkg_resources
from PyQt5 import uic, QtWidgets, QtCore

from PyQt5 import uic, QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QThread
from PyQt5.Qt import QSplashScreen, QObject
import numpy as np
import collections
import time as ttime
import os

from isstools.elements import elements
from isstools.trajectory.trajectory import trajectory_manager
from isstools.batch.batch import BatchManager


ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_batch_manual.ui')

path_icon_experiment = pkg_resources.resource_filename('isstools', 'icons/experiment.png')
icon_experiment = QtGui.QIcon()
icon_experiment.addPixmap(QtGui.QPixmap(path_icon_experiment), QtGui.QIcon.Normal, QtGui.QIcon.Off)

path_icon_sample = pkg_resources.resource_filename('isstools', 'icons/sample.png')
icon_sample = QtGui.QIcon()
icon_sample.addPixmap(QtGui.QPixmap(path_icon_sample), QtGui.QIcon.Normal, QtGui.QIcon.Off)

path_icon_scan = pkg_resources.resource_filename('isstools', 'icons/scan.png')
icon_scan = QtGui.QIcon()
icon_scan.addPixmap(QtGui.QPixmap(path_icon_scan), QtGui.QIcon.Normal, QtGui.QIcon.Off)

class ItemSample(QtGui.QStandardItem):
    name = ''
    x = 0
    y = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class UIBatchManual(*uic.loadUiType(ui_path)):
    def __init__(self,
                 plan_funcs,
                 service_plan_funcs,
                 hhm,
                 motors_dict,
                 sample_stage = None, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        #self.addCanvas()

        self.plan_funcs = plan_funcs
        self.service_plan_funcs = service_plan_funcs
        self.plan_funcs_names = [plan.__name__ for plan in plan_funcs]
        self.service_plan_funcs_names = [plan.__name__ for plan in service_plan_funcs]
        self.sample_stage = sample_stage
        self.motors_dict = motors_dict
        self.mot_list = self.motors_dict.keys()
        self.mot_sorted_list = list(self.mot_list)
        self.mot_sorted_list.sort()

        self.batch_mode_uids = []
        self.traj_manager = trajectory_manager(hhm)

        self.treeView_batch = elements.TreeView(self, 'all')

        self.gridLayout_batch_definition.addWidget(self.treeView_batch, 0, 0)

        # sample functions
        self.push_create_batch_experiment.clicked.connect(self.create_batch_experiment)

        self.model_batch = QtGui.QStandardItemModel(self)
        self.treeView_batch.header().hide()
        self.treeView_batch.setModel(self.model_batch)


        self.model_samples = QtGui.QStandardItemModel(self)
        self.push_create_sample.clicked.connect(self.create_new_sample)
        self.push_delete_sample.clicked.connect(self.delete_sample)
        self.push_get_sample.clicked.connect(self.get_sample_pos)

        self.model_scans = QtGui.QStandardItemModel(self)
        self.push_create_scan.clicked.connect(self.create_new_scan)
        self.push_delete_scan.clicked.connect(self.delete_scan)


        self.push_batch_delete.clicked.connect(self.delete_current_batch)
        self.push_create_measurement.clicked.connect(self.create_measurement)

        self.comboBox_scans.addItems(self.plan_funcs_names)
        self.comboBox_services.addItems(self.service_plan_funcs_names)

        self.comboBox_services.currentIndexChanged.connect(self.populate_service_parameters)
        self.push_update_traj_list.clicked.connect(self.update_batch_traj)

        try:
            self.update_batch_traj()
        except OSError as err:
             print('Error loading:', err)



        self.comboBox_sample_loop_motor.addItems(self.mot_sorted_list)
        self.comboBox_sample_loop_motor.currentTextChanged.connect(self.update_loop_values)

        spinBox_connects = [self.restore_add_loop,
                            self.comboBox_sample_loop_motor.setDisabled,
                            self.spinBox_motor_range_start.setDisabled,
                            self.spinBox_motor_range_stop.setDisabled,
                            self.spinBox_motor_range_step.setDisabled,
                            self.radioButton_sample_rel.setDisabled,
                            self.radioButton_sample_abs.setDisabled,
                            ]
        for changer in spinBox_connects:
            self.spinBox_sample_loop_rep.valueChanged.connect(changer)

        self.radioButton_sample_rel.toggled.connect(self.set_loop_values)
        self.last_lut = 0



    '''
    Dealing with batch experiemnts
    '''

    def create_batch_experiment(self):
        parent = self.model_batch.invisibleRootItem()
        batch_experiment = 'Batch experiment "{}" repeat {} times'.format(self.lineEdit_batch_experiment_name.text(),
                                                                        self.spinBox_sample_loop_rep.value())
        new_item = QtGui.QStandardItem(batch_experiment)
        new_item.setEditable(False)
        new_item.item_type = 'experiment'
        new_item.repeat=self.spinBox_sample_loop_rep.value()
        new_item.setIcon(icon_experiment)
        parent.appendRow(new_item)


    '''
    Dealing with samples
    '''
    def create_new_sample(self):
        x = self.spinBox_sample_x.value()
        y = self.spinBox_sample_y.value()
        name = self.lineEdit_sample_name.text()
        comment = self.lineEdit_sample_comment.text()
        item = QtGui.QStandardItem('Sample {} at X {} Y {}'.format(name, x, y))
        item.setDropEnabled(False)
        item.item_type = 'sample'
        item.setCheckable(True)
        item.setEditable(False)
        item.x = x
        item.y = y
        item.name = name
        item.comment = comment
        item.setIcon(icon_sample)

        parent = self.model_samples.invisibleRootItem()
        parent.appendRow(item)
        self.listView_samples.setModel(self.model_samples)

    def get_sample_pos(self):

        x_value = self.sample_stage.x.position
        y_value = self.sample_stage.y.position
        self.spinBox_sample_x.setValue(x_value)
        self.spinBox_sample_y.setValue(y_value)

    def delete_sample(self):
        view = self.listView_samples
        index = view.currentIndex()
        if index.row() < view.model().rowCount():
            view.model().removeRows(index.row(), 1)


    '''
    Dealing with scans
    '''

    def delete_scan(self):
        view = self.listView_scans
        index = view.currentIndex()
        if index.row() < view.model().rowCount():
            view.model().removeRows(index.row(), 1)

    def create_new_scan(self):
        scan_type= self.comboBox_scans.currentText()
        traj = self.comboBox_lut.currentText()
        repeat =  self.spinBox_scan_repeat.value()
        delay = self.spinBox_scan_delay.value()
        item = QtGui.QStandardItem('Scan {} with trajectory {}, repeat {} times with {} s delay'.format(scan_type,
                                                                             traj, repeat, delay))

        item.setDropEnabled(False)
        item.item_type = 'scan'
        item.scan_type = scan_type
        item.trajectory = self.comboBox_lut.currentIndex()
        item.repeat = repeat
        item.delay = delay
        item.setCheckable(True)
        item.setEditable(False)
        item.setIcon(icon_scan)

        parent = self.model_scans.invisibleRootItem()
        parent.appendRow(item)
        self.listView_scans.setModel(self.model_scans)

    def delete_current_batch(self):
        view = self.treeView_batch
        index = view.currentIndex()
        if index.row() < view.model().rowCount():
            view.model().removeRows(index.row(), 1)

    '''
    Dealing with measurements
    '''

    def create_measurement(self):
        if self.treeView_batch.model().rowCount():
            if self.treeView_batch.selectedIndexes():
                selected_index = self.treeView_batch.selectedIndexes()[0]
                parent = self.model_batch.itemFromIndex(selected_index)
                if parent.item_type == 'experiment':
                    if self.radioButton_priority_sample.isChecked():
                        if self.listView_samples.model() is not None:
                            for index in range(self.listView_samples.model().rowCount()):
                                item_sample = self.listView_samples.model().item(index)
                                if item_sample.checkState():
                                    new_item_sample = self.clone_sample_item(item_sample)
                                    if self.listView_scans.model() is not None:
                                        for index in range(self.listView_scans.model().rowCount()):
                                            item_scan = self.listView_scans.model().item(index)
                                            if item_scan.checkState():
                                                new_item_scan = self.clone_scan_item(item_scan)
                                                new_item_sample.appendRow(new_item_scan)
                                                new_item_scan.setCheckable(False)
                                                new_item_scan.setEditable(False)
                                                new_item_scan.setIcon(icon_scan)
                                parent.appendRow(new_item_sample)
                                new_item_sample.setCheckable(False)
                                new_item_sample.setEditable(False)
                    else:
                        if self.listView_scans.model() is not None:
                            for index in range(self.listView_scans.model().rowCount()):
                                item_scan = self.listView_scans.model().item(index)

                                if item_scan.checkState():
                                    new_item_scan = self.clone_scan_item(item_scan)

                                    if self.listView_samples.model() is not None:
                                        for index in range(self.listView_samples.model().rowCount()):
                                            item_sample = self.listView_samples.model().item(index)
                                            if item_scan.checkState():
                                                new_item_sample = self.clone_sample_item(item_sample)
                                                new_item_scan.appendRow(new_item_sample)
                                                new_item_scan.setCheckable(False)
                                                new_item_scan.setEditable(False)
                                                new_item_scan.setIcon(icon_scan)
                                parent.appendRow(new_item_scan)
                                new_item_scan.setCheckable(False)
                                new_item_scan.setEditable(False)

                    self.treeView_batch.expand(self.model_batch.indexFromItem(parent))

                    for index in range(parent.rowCount()):
                        self.treeView_batch.expand(self.model_batch.indexFromItem(parent.child(index)))
                    self.treeView_batch.setModel(self.model_batch)



    def clone_sample_item(self, item_sample):
        new_item_sample = QtGui.QStandardItem(item_sample.text())
        new_item_sample.item_type = 'sample'
        new_item_sample.x = item_sample.x
        new_item_sample.y = item_sample.y
        new_item_sample.name = item_sample.name
        new_item_sample.setIcon(icon_sample)
        return new_item_sample

    def clone_scan_item(self, item_scan):
        new_item_scan = QtGui.QStandardItem(item_scan.text())
        new_item_scan.item_type = 'scan'
        new_item_scan.trajectory = item_scan.trajectory
        new_item_scan.scan_type = item_scan.scan_type
        new_item_scan.repeat = item_scan.repeat
        new_item_scan.delay = item_scan.delay
        return new_item_scan


    def update_loop_values(self, text):
        for motor in self.motors_dict:
            if self.comboBox_sample_loop_motor.currentText() == self.motors_dict[motor]['name']:
                curr_mot = self.motors_dict[motor]['object']
                break
        if self.radioButton_sample_rel.isChecked():
            if curr_mot.connected == True:
                self.push_add_sample_loop.setEnabled(True)
                self.spinBox_motor_range_start.setValue(-0.5)
                self.spinBox_motor_range_stop.setValue(0.5)
                self.spinBox_motor_range_step.setValue(0.25)
                self.push_add_sample_loop.setEnabled(True)
            else:
                self.push_add_sample_loop.setEnabled(False)
                self.spinBox_motor_range_start.setValue(0)
                self.spinBox_motor_range_stop.setValue(0)
                self.spinBox_motor_range_step.setValue(0.025)
        else:
            if curr_mot.connected == True:
                self.push_add_sample_loop.setEnabled(True)
                curr_pos = curr_mot.read()[curr_mot.name]['value']
                self.spinBox_motor_range_start.setValue(curr_pos - 0.1)
                self.spinBox_motor_range_stop.setValue(curr_pos + 0.1)
                self.spinBox_motor_range_step.setValue(0.025)
            else:
                self.push_add_sample_loop.setEnabled(False)
                self.spinBox_motor_range_start.setValue(0)
                self.spinBox_motor_range_stop.setValue(0)
                self.spinBox_motor_range_step.setValue(0.025)

    def restore_add_loop(self, value):
        if value:
            self.push_add_sample_loop.setEnabled(True)

    def set_loop_values(self, checked):
        if checked:
            self.spinBox_motor_range_start.setValue(-0.5)
            self.spinBox_motor_range_stop.setValue(0.5)
            self.spinBox_motor_range_step.setValue(0.25)
            self.push_add_sample_loop.setEnabled(True)
        else:
            motor_text = self.comboBox_sample_loop_motor.currentText()
            self.update_loop_values(motor_text)

    def add_new_sample_loop(self, samples, scans):
        parent = self.model_batch.invisibleRootItem()
        new_item = QtGui.QStandardItem('Sample Loop')
        new_item.setEditable(False)

        if self.spinBox_sample_loop_rep.value():
            repetitions_item = QtGui.QStandardItem('Repetitions:{}'.format(self.spinBox_sample_loop_rep.value()))
        else:
            repetitions_item = QtGui.QStandardItem(
                'Motor:{} Start:{} Stop:{} Step:{}'.format(self.comboBox_sample_loop_motor.currentText(),
                                                           self.spinBox_motor_range_start.value(),
                                                           self.spinBox_motor_range_stop.value(),
                                                           self.spinBox_motor_range_step.value()))
        new_item.appendRow(repetitions_item)

        if self.radioButton_sample_loop.isChecked():
            primary = 'Samples'
        else:
            primary = 'Scans'
        primary_item = QtGui.QStandardItem('Primary:{}'.format(primary))
        new_item.appendRow(primary_item)

        samples_item = QtGui.QStandardItem('Samples')
        samples_item.setDropEnabled(False)
        for index in range(len(samples)):
            subitem = QtGui.QStandardItem(samples[index])
            subitem.setDropEnabled(False)
            samples_item.appendRow(subitem)
        new_item.appendRow(samples_item)

        scans_item = QtGui.QStandardItem('Scans')
        scans_item.setDropEnabled(False)
        for index in range(len(scans)):
            subitem = QtGui.QStandardItem(scans[index])
            subitem.setDropEnabled(False)
            scans_item.appendRow(subitem)
        new_item.appendRow(scans_item)

        parent.appendRow(new_item)
        self.treeView_batch.expand(self.model_batch.indexFromItem(new_item))
        for index in range(new_item.rowCount()):
            self.treeView_batch.expand(new_item.child(index).index())


    def populate_service_parameters(self, index):
        # DEPRECATED
        # if self.comboBox_scans.currentText()[: 5] != 'tscan':
        #     self.comboBox_lut.setEnabled(False)
        # else:
        #     self.comboBox_lut.setEnabled(True)

        for i in range(len(self.widget_scan_param1)):
            self.gridLayout_scans.removeWidget(self.widget_service_param1[i])
            self.gridLayout_scans.removeWidget(self.widget_service_param2[i])
            self.gridLayout_scans.removeWidget(self.widget_service_param3[i])
            self.widget_service_param1[i].deleteLater()
            self.widget_service_param2[i].deleteLater()
            self.widget_service_param3[i].deleteLater()
        self.widget_service_param1 = []
        self.widget_service_param2 = []
        self.widget_service_param3 = []
        self.param_types_batch = []
        plan_func = self.service_plan_funcs[index]
        signature = inspect.signature(plan_func)
        for i in range(0, len(signature.parameters)):
            default = re.sub(r':.*?=', '=', str(signature.parameters[list(signature.parameters)[i]]))
            if default == str(signature.parameters[list(signature.parameters)[i]]):
                default = re.sub(r':.*', '', str(signature.parameters[list(signature.parameters)[i]]))
            self.add_parameters(list(signature.parameters)[i], default,
                                signature.parameters[list(signature.parameters)[i]].annotation,
                                grid=self.gridLayout_services,
                                params=[self.widget_service_param1, self.widget_service_param2, self.widget_service_param3])
            self.param_types_batch.append(signature.parameters[list(signature.parameters)[i]].annotation)

    def add_parameters(self, name, default, annotation, grid, params):
        rows = int((grid.count()) / 3)
        param1 = QtWidgets.QLabel(str(rows + 1))

        param2 = None
        def_val = ''
        if default.find('=') != -1:
            def_val = re.sub(r'.*=', '', default)
        if annotation == int:
            param2 = QtWidgets.QSpinBox()
            param2.setMaximum(100000)
            param2.setMinimum(-100000)
            def_val = int(def_val)
            param2.setValue(def_val)
        elif annotation == float:
            param2 = QtWidgets.QDoubleSpinBox()
            param2.setMaximum(100000)
            param2.setMinimum(-100000)
            def_val = float(def_val)
            param2.setValue(def_val)
        elif annotation == bool:
            param2 = QtWidgets.QCheckBox()
            if def_val == 'True':
                def_val = True
            else:
                def_val = False
            param2.setCheckState(def_val)
            param2.setTristate(False)
        elif annotation == str:
            param2 = QtWidgets.QLineEdit()
            def_val = str(def_val)
            param2.setText(def_val)

        if param2 is not None:
            param3 = QtWidgets.QLabel(default)
            grid.addWidget(param1, rows, 0, QtCore.Qt.AlignTop)
            grid.addWidget(param2, rows, 1, QtCore.Qt.AlignTop)
            grid.addWidget(param3, rows, 2, QtCore.Qt.AlignTop)
            params[0].append(param1)
            params[1].append(param2)
            params[2].append(param3)

    def update_batch_traj(self):
        self.trajectories = self.traj_manager.read_info(silent=True)
        self.comboBox_lut.clear()
        self.comboBox_lut.addItems(
            ['{}-{}'.format(lut, self.trajectories[lut]['name']) for lut in self.trajectories if lut != '9'])

    def load_csv(self):
        user_filepath = '/GPFS/xf08id/User Data/{}.{}.{}/'.format(self.RE.md['year'],
                                                                  self.RE.md['cycle'],
                                                                  self.RE.md['PROPOSAL'])
        filename = QtWidgets.QFileDialog.getOpenFileName(caption='Select file to load',
                                                         directory=user_filepath,
                                                         filter='*.csv',
                                                         parent=self)[0]
        if filename:
            batman = BatchManager(self)
            batman.load_csv(filename)

    def save_csv(self):
        user_filepath = '/GPFS/xf08id/User Data/{}.{}.{}/'.format(self.RE.md['year'],
                                                                  self.RE.md['cycle'],
                                                                  self.RE.md['PROPOSAL'])
        filename = QtWidgets.QFileDialog.getSaveFileName(caption='Select file to save',
                                                         directory=user_filepath,
                                                         filter='*.csv',
                                                         parent=self)[0]
        if filename:
            if filename[-4:] != '.csv':
                filename += '.csv'
            batman = BatchManager(self)
            batman.save_csv(filename)

    def check_pause_abort_batch(self):
        if self.batch_abort:
            print('**** Aborting Batch! ****')
            raise Exception('Abort button pressed by user')
        elif self.batch_pause:
            self.label_batch_step.setText('[Paused] {}'.format(self.label_batch_step.text()))
            while self.batch_pause:
                QtCore.QCoreApplication.processEvents()




