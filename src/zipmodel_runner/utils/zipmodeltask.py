from dataclasses import dataclass
from shlex import join
import time

from shared.uijobqueue import (
    JobPars,
    JobTask
)

from dgbpy.zipmodelbase import load_modelimpl

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

@dataclass(slots=True)
class ZipModelTaskPars(JobPars):
    model_path: str
    survey_name: str
    input_volume_names: list[str]
    output_volume_names: list[str]
    inline_range: tuple[int,int]
    crossline_range: tuple[int,int]
    z_range: tuple[float,float]
    chunk_size: tuple[int,int,int]
    overlap: tuple[int,int,int]
    merge_mode: int
    propery_names: str
    format_name: str

class ZipModelTask(JobTask):
    def __init__(self, row: int, pars: ZipModelTaskPars):
        super().__init__(row, pars)

    @Slot()
    def run(self):
        from odbind.survey import Survey
        from odbind.seismic3d import Seismic3D

        try:
            if not isinstance(self.pars, ZipModelTaskPars ):
                return
            zipmodel = load_modelimpl(self.pars.model_path)
            survey = Survey(self.pars.survey_name)
            Seismic3D.use_xarray = False
            inputvol = Seismic3D(survey, self.pars.input_volume_names[0])
            inchunks = inputvol.chunk
            inchunks.set_chunkpars(
                volume=(self.pars.inline_range, self.pars.crossline_range, self.pars.z_range),
                chunk_shape=self.pars.chunk_size,
                overlap=self.pars.overlap,
                merge_mode=self.pars.merge_mode
            )

            with Seismic3D.create(
                survey,
                self.pars.output_volume_names[0],
                self.pars.inline_range,
                self.pars.crossline_range,
                self.pars.z_range,
                [self.pars.propery_names[0]],
                zistime=inputvol.zistime,
                overwrite=True
            ) as outputvol:
                for idx, chunk in enumerate(inchunks):
                    if self.do_stop:
                        break
                    data, info = chunk
                    prediction = zipmodel.predict(data)
                    outputvol[:] = (prediction, info)
                    self.signals.progress.emit(self.row, round((idx+1)/len(inchunks))*100, "running")
        finally:
            result = f"Completed at {time.strftime('%X')}"
            self.signals.finished.emit(self.row, result)
