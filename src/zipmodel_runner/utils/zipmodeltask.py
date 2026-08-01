import numpy as np
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
    batch_size: int
    chunk_size: tuple[int,int,int]
    overlap: tuple[int,int,int]
    merge_mode: int
    property_names: str
    formats: list[str]

class ZipModelTask(JobTask):
    def __init__(self, row: int, pars: ZipModelTaskPars):
        super().__init__(row, pars)

    @Slot()
    def run(self):
        from odbind.survey import Survey
        from odbind.seismic3d import Seismic3D, MergeMode

        try:
            if not isinstance(self.pars, ZipModelTaskPars ):
                return
            zipmodel = load_modelimpl(self.pars.model_path)
            survey = Survey(self.pars.survey_name)
            Seismic3D.use_xarray = False
            inputvols = [Seismic3D(survey, volume_name) for volume_name in self.pars.input_volume_names]
            zistime = inputvols[0].zistime
            chunksets = []
            for inputvol in inputvols:
                chunk = inputvol.chunk
                chunk.set_chunkpars(
                    volume=(self.pars.inline_range, self.pars.crossline_range, self.pars.z_range),
                    chunkshape=self.pars.chunk_size,
                    overlap=self.pars.overlap,
                    mergemode=MergeMode(self.pars.merge_mode)
                )
                chunksets.append(chunk[:])
            numchunks = len(inputvols[0].chunk)
            outputvols = [Seismic3D.create(
                                            survey,
                                            volume_name,
                                            self.pars.inline_range,
                                            self.pars.crossline_range,
                                            self.pars.z_range,
                                            components=[property_name],
                                            fmt=format,
                                            zistime=zistime,
                                            overwrite=True
            ) for volume_name, property_name, format in zip(self.pars.output_volume_names, self.pars.property_names, self.pars.formats)]
            batchsz = self.pars.batch_size
            numin = len(self.pars.input_volume_names)
            for idx in range(0, numchunks, batchsz):
                numbatch = min(batchsz,numchunks-idx)
                input = np.empty((numbatch, numin, *self.pars.chunk_size), dtype=np.float32)
                nanarray = np.empty_like(input, dtype=np.bool)
                infos = []
                for bidx in range(numbatch):
                    for cidx in range(numin):
                        data, info = next(chunksets[cidx])
                        infos.append(info)
                        nanarray[bidx, cidx, :, :, :] = np.isnan(data[0])
                        input[bidx,cidx,:,:,:] = np.nan_to_num(data[0])
                if self.do_stop:
                    break
                prediction = zipmodel.predict(input)
                for bidx in range(numbatch):
                    newinfo = infos[bidx]
                    for cidx, outputvol in enumerate(outputvols):
                        newinfo['comp'] = self.pars.property_names[cidx]
                        prediction[bidx, cidx, nanarray[bidx, cidx]] = np.nan
                        outputvol.chunk[:] = ([prediction[bidx,cidx]], newinfo)
                self.signals.progress.emit(self.row, round((idx+numbatch)/numchunks*100), "Running")
            self.signals.progress.emit(self.row, 0, "Saving")
            for idx, outputvol in enumerate(outputvols):
                outputvol.close()
                self.signals.progress.emit(self.row, round((idx+1)/len(outputvols)*100), "Saving")
            result = f"Completed at {time.strftime('%X')}"
        except Exception as e:
            result = f"Error: {e}"
        finally:
            self.signals.finished.emit(self.row, result)
