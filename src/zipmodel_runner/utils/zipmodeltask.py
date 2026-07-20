from dataclasses import dataclass
from shlex import join
import time

from dgbpy.zipmodelbase import load_modelimpl

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

@dataclass(slots=True)
class ZipModelTaskPars:
    job_id: int
    model_path: str
    survey_name: str
    input_volume_name: str
    output_volume_name: str
    inline_range: tuple[int,int]
    crossline_range: tuple[int,int]
    z_range: tuple[float,float]
    chunk_size: tuple[int,int,int]
    overlap: tuple[int,int,int]
    merge_mode: int
    propery_name: str
    format_name: str


class ZipModelTaskSignals(QObject):
    finished = Signal(str, str) # Job ID, Result
    progress = Signal(str, int) # Job ID, Progress %

# 2. Define the Worker that executes a single job
class ZipModelTask(QRunnable):
    def __init__(self, pars: ZipModelTaskPars):
        super().__init__()
        self.pars = pars
        self.signals = ZipModelTaskSignals()

    @Slot()
    def run(self):
        from odbind.survey import Survey
        from odbind.seismic3d import Seismic3D

        zipmodel = load_modelimpl(self.pars.model_path)
        survey = Survey(self.pars.survey_name)
        Seismic3D.use_xarray = False
        inputvol = Seismic3D(survey, self.pars.input_volume_name)
        inchunks = inputvol.chunk
        inchunks.set_chunkpars(
            volume=(self.pars.inline_range, self.pars.crossline_range, self.pars.z_range),
            chunk_shape=self.pars.chunk_size,
            overlap=self.pars.overlap,
            merge_mode=self.pars.merge_mode
        )

        with Seismic3D.create(
            survey,
            self.pars.output_volume_name,
            self.pars.inline_range,
            self.pars.crossline_range,
            self.pars.z_range,
            [self.pars.propery_name],
            self.pars.format_name,
            True,
            True
        ) as outputvol:
            for idx, chunk in enumerate(inchunks):
                data, info = chunk
                prediction = zipmodel.predict(data)
                outputvol[:] = (prediction, info)
                self.signals.progress.emit(self.pars.job_id, int(round((idx+1)/len(inchunks)))*100)

        result = f"Completed at {time.strftime('%X')}"
        self.signals.finished.emit(self.pars.job_id, result)
