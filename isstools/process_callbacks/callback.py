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



