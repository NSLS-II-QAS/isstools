import os
import uuid
import pandas as pd
import numpy as np
from isstools.trajectory.trajectory import trajectory, trajectory_manager
from isstools.conversions import xray
from subprocess import call


class XASExperiment:
    def __init__(self, definition=None, trajectory_num=None):
        self.definition = definition
        self.trajectory_num = trajectory_num


class XASBatchExperiment:
    def __init__(self, excel_file='/nsls2/xf08id/Sandbox/ISS-Sample-Spreadsheet.xlsx', skiprows=1, hhm=None):
        self.excel_file = excel_file
        self._skiprows = skiprows
        self.hhm = hhm
        self.trajectory_manager = trajectory_manager(self.hhm)

        self.experiments = []
        self.trajectory_folder = '/nsls2/xf08id/trajectory'
        # Loaded pandas dataframe:
        self.experiment_table = None

        # List of all found trajectories from the file:
        self.trajectories = []

        # Unique trajectories derived from trajectories:
        self.unique_trajectories = []

        self.trajectory_filenames = []

    def read_excel(self):
        self.experiment_table = pd.read_excel(self.excel_file, skiprows=self._skiprows)

    def batch_create_trajectories(self):
        for i in range(len(self.experiment_table)):
            d = self.experiment_table.iloc[i]
            traj = trajectory(self.hhm)
            kwargs = dict(
                edge_energy=d['Position'],
                offsets=([d['pre-edge start'], d['pre-edge stop'],
                          d['post_edge stop'], xray.k2e(d['k-range'], d['Position']) - d['Position']]),
                trajectory_type='Double Sine',
                dsine_preedge_duration=d['time 1'],
                dsine_postedge_duration=d['time 2'],
            )
            traj.define(**kwargs)

            # Add some more parameters manually:
            traj.elem = d['Element']
            traj.edge = d['Edge']
            traj.e0 = d['Position']

            traj.interpolate()
            traj.revert()
            self.trajectories.append(traj)
            self.experiments.append(XASExperiment(definition=d))

    def create_unique_trajectories(self):
        self.unique_trajectories.append(self.trajectories[0])
        for i in range(len(self.trajectories)):
            unique_flag = True
            for j in range(len(self.unique_trajectories)):
                if np.allclose(self.trajectories[i].energy_grid, self.unique_trajectories[j].energy_grid):
                    unique_flag = False
            if unique_flag:
                self.unique_trajectories.append(self.trajectories[i])

    def assign_trajectory_number(self):
        for i in range(len(self.trajectories)):
            for j in range(len(self.unique_trajectories)):
                if np.allclose(self.trajectories[i].energy_grid, self.unique_trajectories[j].energy_grid):
                    self.experiments[i].trajectory_num = j
                    continue


    def save_trajectories(self):
        for ut in self.unique_trajectories:
            filename = os.path.join(self.trajectory_folder, 'trajectory_{}.txt'.format(str(uuid.uuid4())[:8]))
            self.trajectory_filenames.append(filename)
            print(f'Saving {filename}...')
            np.savetxt(filename, ut.energy_grid, fmt='%.6f',
                       header=f'element: {ut.elem}, edge: {ut.edge}, E0: {ut.e0}')
            call(['chmod', '666', filename])

    def load_trajectories(self):
        offset = self.hhm.angle_offset.value
        print(offset)
        for i, traj_file in enumerate(self.trajectory_filenames):
            self.trajectory_manager.load(os.path.basename(traj_file),i+1,is_energy=True, offset=offset )




if __name__ == "__main__":
    import matplotlib.pyplot as plt
    plt.ion()
    xas = XASBatchExperiment(hhm=hhm)
    xas.read_excel()
    xas.batch_create_trajectories()
    xas.create_unique_trajectories()
    xas.assign_trajectory_number()
    xas.save_trajectories()
    xas.load_trajectories()
    #for i, t in enumerate(xas.unique_trajectories):
    #    plt.plot(t.energy, label = str(i))
    #plt.legend()
