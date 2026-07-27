from shared.uiodbind import (
    SurveySel,
    Seismic3DSel,
    ODObjectSel,
    ChunkMergeMode
)
from shared.uitools import (
    uiFileSel,
    uiSpinBoxRowWidget
)
from shared.uijobqueue import (
    uiJobQueue,
    JobTask,
    JobPars,
    JobSignals
)

from src.zipmodel_runner.utils.zipmodeltask import ZipModelTask, ZipModelTaskPars
from utils.zipmodelhelpers import ZipModelInfoReader, is_seisimg2img

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

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

        self.inputgrp = QGroupBox("Input Volumes")
        self.input_layout = QVBoxLayout()
        self.inputgrp.setLayout(self.input_layout)
        self.update_inputs()

        self.outputgrp = QGroupBox("Output Volumes")
        self.output_layout = QVBoxLayout()
        self.outputgrp.setLayout(self.output_layout)
        self.update_outputs()

        self.paramgrp = QGroupBox("Parameters")
        self.param_layout = QVBoxLayout()
        self.paramgrp.setLayout(self.param_layout)
        self.make_params()

        layout = QVBoxLayout()
        layout.addWidget(self.filesel)
        layout.addWidget(self.surveysel)
        layout.addWidget(self.inputgrp)
        layout.addWidget(self.outputgrp)
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

        self.fillpars(modelinfo)
        self.update_inputs(modelinfo["input_names"])
        self.update_outputs(modelinfo["output_names"])
        self.update_params(modelinfo)
        self.add_button.setEnabled(True)

    def fillpars(self, modelinfo):
        self.pars = ZipModelTaskPars(
            name=modelinfo["model_name"],
            model_path=self.filesel.path(),
            survey_name=self.surveysel.currentText(),
            input_volume_names=[""],
            output_volume_names=[""],
            inline_range=(0, 0),
            crossline_range=(0, 0),
            z_range=(0.0, 0.0),
            chunk_size=self.chunksz.get_values(),
            overlap=self.overlap.get_values(),
            merge_mode=self.mergemode.currentIndex(),
            propery_names=modelinfo["output_names"],
            format_name="CBVS"
        )

    def update_inputs(self, names: list[str] | None = None):
        names = names or ['Input']
        while self.input_layout.count() > len(names):
            layout_item = self.input_layout.takeAt(self.input_layout.count()-1)
            widget = layout_item.widget()
            if widget:
                if isinstance(widget, Seismic3DSel):
                    try:
                        self.surveysel.currentTextChanged.disconnect(widget.setSurvey)
                    except RuntimeError:
                        pass
                widget.deleteLater()

        while self.input_layout.count()<len(names):
            entry = Seismic3DSel()
            self.surveysel.currentTextChanged.connect(entry.setSurvey)
            entry.setSurvey(self.surveysel.currentText())
            self.input_layout.addWidget(entry)

        for idx, name in enumerate(names):
            layout_item = self.input_layout.itemAt(idx)
            widget = layout_item.widget()
            if isinstance(widget, Seismic3DSel):
                widget.label.setText(name)
                widget.label.adjustSize()

    def update_outputs(self, names: list[str] | None = None):
        names = names or ['Output']
        while self.output_layout.count() > len(names):
            layout_item = self.output_layout.takeAt(self.output_layout.count()-1)
            widget = layout_item.widget()
            if widget:
                if isinstance(widget, Seismic3DSel):
                    try:
                        self.surveysel.currentTextChanged.disconnect(widget.setSurvey)
                    except RuntimeError:
                        pass
                widget.deleteLater()

        while self.output_layout.count()<len(names):
            entry = ODObjectSel(translatorgrp="Seismic Data")
            self.surveysel.currentTextChanged.connect(entry.setSurvey)
            entry.setSurvey(self.surveysel.currentText())
            self.output_layout.addWidget(entry)

        for idx, name in enumerate(names):
            layout_item = self.output_layout.itemAt(idx)
            widget = layout_item.widget()
            if isinstance(widget, ODObjectSel):
                widget.label.setText(name)
                widget.label.adjustSize()

    def make_params(self):
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
