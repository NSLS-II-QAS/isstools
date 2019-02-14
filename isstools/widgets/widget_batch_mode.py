import sys

import pkg_resources
from PyQt5 import uic
from bluesky.plan_stubs import mv
from xas.trajectory import trajectory_manager
from isstools.widgets import widget_batch_manual

ui_path = pkg_resources.resource_filename('isstools', 'ui/ui_batch_mode.ui')


class UIBatchMode(*uic.loadUiType(ui_path)):
    def __init__(self,
                 plan_funcs,
                 service_plan_funcs,
                 hhm,
                 RE,
                 sample_stage,
                 parent_gui,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.plan_funcs = plan_funcs
        self.service_plan_funcs = service_plan_funcs
        self.RE = RE
        self.hhm = hhm
        self.sample_stage = sample_stage
        self.parent_gui = parent_gui

        self.widget_batch_manual = widget_batch_manual.UIBatchManual(plan_funcs,
                                                                     service_plan_funcs,
                                                                     hhm,
                                                                     sample_stage=sample_stage
                                                                     )

        self.layout_batch_manual.addWidget(self.widget_batch_manual)
        self.push_run_batch_manual.clicked.connect(self.run_batch_manual)

    def run_batch_manual(self):
        print('[Batch scan] Starting...')
        batch = self.widget_batch_manual.treeView_batch.model()
        self.RE(self.batch_parse_and_run(self.hhm, self.sample_stage, batch, self.plan_funcs))

    def batch_parse_and_run(self, hhm, sample_stage, batch, plans_dict):
        sys.stdout = self.parent_gui.emitstream_out
        tm = trajectory_manager(hhm)
        for ii in range(batch.rowCount()):
            experiment = batch.item(ii)
            repeat = experiment.repeat
            for indx in range(repeat):
                if repeat > 1:
                    exper_index = f'{(indx+1):04d}'
                else:
                    exper_index = ''
                for jj in range(experiment.rowCount()):
                    print(experiment.rowCount())
                    step = experiment.child(jj)
                    if step.item_type == 'sample':
                        sample = step
                        yield from mv(sample_stage.x, sample.x, sample_stage.y, sample.y)
                        for kk in range(sample.rowCount()):
                            child_item = sample.child(kk)
                            if child_item.item_type == 'scan':
                                scan=child_item
                                traj_index = scan.trajectory
                                plan = plans_dict[scan.scan_type]
                                sample_name = '{} {} {}'.format(sample.name, scan.name, exper_index)
                                self.label_batch_step.setText(sample_name)
                                kwargs = {'name': sample_name,
                                          'comment': '',
                                          'delay': 0,
                                          'n_cycles': scan.repeat,
                                          'stdout': self.parent_gui.emitstream_out}
                                tm.init(traj_index+1)
                                yield from plan(**kwargs)
                            elif child_item.item_type == 'service':
                                service = child_item
                                kwargs = {'stdout': self.parent_gui.emitstream_out}

                                yield from service.service_plan(**step.service_params, **kwargs)

                    elif step.item_type == 'scan':
                        scan = step
                        traj_index = scan.trajectory
                        tm.init(traj_index + 1)
                        for kk in range(step.rowCount()):
                            child_item = scan.child(kk)
                            if child_item.item_type == 'sample':
                                sample=child_item
                                yield from mv(sample_stage.x, sample.x, sample_stage.y, sample.y)
                                plan = plans_dict[scan.scan_type]

                                sample_name = '{} {} {}'.format(sample.name, scan.name, exper_index)
                                self.label_batch_step.setText(sample_name)
                                kwargs = {'name': sample_name,
                                          'comment': '',
                                          'delay': 0,
                                          'n_cycles': scan.repeat,
                                          'stdout': self.parent_gui.emitstream_out}
                                yield from plan(**kwargs)
                            elif child_item == 'service':
                                service = child_item
                                kwargs = {'stdout': self.parent_gui.emitstream_out}
                                yield from service.service_plan(**step.service_params,**kwargs)
                    elif step.item_type == 'service':
                        print(step.service_params)
                        kwargs = {'stdout': self.parent_gui.emitstream_out}
                        yield from step.service_plan(**step.service_params,**kwargs)
        self.label_batch_step.setText('idle')