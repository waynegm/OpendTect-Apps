from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from utils.zipmodelhelpers import ZipModelInfoReader, is_seisimg2img

from shared.uijobqueue import uiJobQueue
from shared.uiodbind import (
    ChunkMergeMode,
    MultiSeismic3DInputSelGrp,
    MultiSeismic3DOutputSelGrp,
    Range3DSelGrp,
    SurveySel,
)
from shared.uitools import uiFileSel, uiSpinBoxRowWidget
from zipmodel_runner.utils.zipmodeltask import ZipModelTask, ZipModelTaskPars


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Zipmodel Runner")

        self.filesel = uiFileSel(
            label="ZipModel",
            filter="Zipmodels (*.zip)",
            caption="Select a ZipModel...",
            mode=QFileDialog.FileMode.ExistingFile
        )
        self.filesel.textChanged.connect(self.on_zipmodel_select)

        self.surveysel = SurveySel()
        self.inputgrp = MultiSeismic3DInputSelGrp(self.surveysel)
        self.outputgrp = MultiSeismic3DOutputSelGrp(self.surveysel)
        self.rangegrp = Range3DSelGrp(self.surveysel, title="Process Range")

        self.paramgrp = QGroupBox("Parameters")
        self.param_layout = QVBoxLayout()
        self.paramgrp.setLayout(self.param_layout)
        self.make_params()

        layout = QVBoxLayout()
        layout.addWidget(self.filesel)
        layout.addWidget(self.surveysel)
        layout.addWidget(self.inputgrp)
        layout.addWidget(self.outputgrp)
        layout.addWidget(self.rangegrp)
        layout.addWidget(self.paramgrp)


        buttongrp = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self.on_add_button_clicked)
        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.on_start_button_clicked)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_stop_button_clicked)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.on_delete_button_clicked)
        buttongrp.addWidget(self.add_button)
        buttongrp.addWidget(self.start_button)
        buttongrp.addWidget(self.stop_button)
        buttongrp.addWidget(self.delete_button)
        layout.addLayout(buttongrp)

        self.jobqueue = uiJobQueue(1)
        layout.addWidget(self.jobqueue)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def on_delete_button_clicked(self):
        self.jobqueue.delete_selected()
        if self.jobqueue.size()==0:
            self.delete_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def on_add_button_clicked(self):
        self.fillpars()
        job = ZipModelTask(self.jobqueue.rowCount(),self.pars)
        self.jobqueue.add_job(job)
        if self.jobqueue.size()==1:
            self.delete_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        else:
            self.delete_button.setEnabled(True)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)


    def on_start_button_clicked(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_stop_button_clicked(self):
        pass

    def on_zipmodel_select(self):
        try:
            if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
                self.worker = None
        except RuntimeError:
            self.worker = None

        self.filesel.button.setEnabled(False)
        zipmodel_path = self.filesel.path()
        self.worker = ZipModelInfoReader(zipmodel_path)
        self.worker.info_loaded.connect(self.on_modelinfo_loaded)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.filesel.button.setEnabled(True))
        self.worker.start()

    def on_error(self, errormsg):
        QMessageBox.critical(self, "Error", errormsg)

    def on_modelinfo_loaded(self, modelinfo):
        if not is_seisimg2img(modelinfo):
            QMessageBox.critical(self, "Error", f"Unsupported learning type: {modelinfo.learn_type}")
            return

        self.modelinfo = modelinfo
        self.inputgrp.update_inputs(modelinfo["input_names"])
        self.outputgrp.update_outputs(modelinfo["output_names"])
        self.update_params(modelinfo)
        self.add_button.setEnabled(True)

    def get_final_range(self):
        selrange = self.rangegrp.get_ranges()
        datarange = self.inputgrp.get_common_range()
        ranges = []
        for selrng, datarng in zip(selrange, datarange):
            rng = list(datarng)
            rng[0] = max(rng[0], selrng[0])
            rng[1] = min(rng[1], selrng[1])
            ranges.append(rng)
        return ranges

    def fillpars(self):
        inputs = self.inputgrp.get_inputs()
        if not inputs:
            QMessageBox.warning(self, "Missing Inputs", "All inputs must be assigned before adding a run.")
            return
        outputs = self.outputgrp.get_outputs()
        if not outputs:
            QMessageBox.warning(self, "Missing Outputs", "All outputs must be assigned before adding a run.")
            return
        inlrg, crlrg, zrg = self.get_final_range()
        self.pars = ZipModelTaskPars(
            name=self.modelinfo["model_name"],
            model_path=self.filesel.path(),
            survey_name=self.surveysel.currentText(),
            input_volume_names=inputs,
            output_volume_names=outputs,
            inline_range=inlrg,
            crossline_range=crlrg,
            z_range=zrg,
            batch_size=self.batchsz.get_values()[0],
            chunk_size=self.chunksz.get_values(),
            overlap=self.overlap.get_values(),
            merge_mode=self.mergemode.currentIndex(),
            property_names=self.modelinfo["output_names"],
            formats=self.outputgrp.get_translators()
        )

    def make_params(self):
        self.param_layout.setContentsMargins(5, 5, 5, 5)
        self.batchsz = uiSpinBoxRowWidget(prefix=[""], label="Batch Size", withsym=False)
        self.batchsz.set_range(-1, 1, 8, 1)
        self.param_layout.addWidget(self.batchsz)
        self.chunksz = uiSpinBoxRowWidget(label="Chunk Size")
        self.chunksz.set_range(-1, 16, 512, 16)
        self.param_layout.addWidget(self.chunksz)
        self.overlap = uiSpinBoxRowWidget(label="Overlap %")
        self.overlap.set_range(-1, 0, 60, 1)
        self.overlap.set_values((10,10,10,))
        self.param_layout.addWidget(self.overlap)
        self.mergemode = ChunkMergeMode()
        self.param_layout.addWidget(self.mergemode)

    def update_params(self, modelinfo):
        self.mergemode.initui()
        input_shape = modelinfo["input_shape"]
        chunksz = []
        for sz in input_shape[2:]:
            if sz==0:
                chunksz.append(64)
            else:
                chunksz.append(sz)
        self.chunksz.set_values(tuple(chunksz))
