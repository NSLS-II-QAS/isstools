from bluesky.callbacks import CallbackBase
from xas.process import process_interpolate_bin


class ProcessingCallback(CallbackBase):
    def __init__(self,db,draw_func_interp, draw_func_binned):
        self.db = db
        self.draw_func_interp = draw_func_interp
        self.draw_func_binned = draw_func_binned
        super().__init__()

    def stop(self,doc):
        print('>>>>>> stopped')
        process_interpolate_bin(doc, self.db, self.draw_func_interp, self.draw_func_binned)



class PilatusCallback(CallbackBase):
    def __init__(self, db):
        self.db = db
        super().__init__()

    def stop(self, doc):
        print(">>>>>>>>>> Pilatus stopped")
        path = '/nsls2/data/qas-new/legacy/processed/{year}/{cycle}/{PROPOSAL}XRD'.format(**doc)
        file_prefix = '{start[sample_name]}-{start[exposure_time]:.1f}s-{start[scan_id]}-'.format(**doc)
        



