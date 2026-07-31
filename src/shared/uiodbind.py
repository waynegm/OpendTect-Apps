import os
import sys
from collections import namedtuple
from importlib.util import find_spec
from shared.uitools import (
    uiLabelledComboBox,
    uiLabelledLineEdit,
    uiSpinBoxRowWidget
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)

Shape = namedtuple('Shape', ['ninl', 'ncrl', 'nz'])
Sampling = namedtuple('Sampling', ['inlrg', 'crlrg', 'zrg'])

class SurveySel(uiLabelledComboBox):
    def __init__(self, label:str="Survey", above:bool=True, parent=None):
        from odbind.survey import Survey
        super().__init__(label=label, above=above, parent=parent)
        self.addItems(Survey.names())

class Seismic3DSel(uiLabelledComboBox):
    def __init__(self, label:str="Input Volume", above:bool=True, parent=None):
        super().__init__(label=label, above=above, parent=parent)

    def setSurvey(self, text:str):
        from odbind.survey import Survey
        from odbind.seismic3d import Seismic3D
        self.clear()
        self.addItems(Seismic3D.names(Survey(text)))

class MultiSeismic3DInputSelGrp(QGroupBox):
    def __init__(self, surveysel: SurveySel, title:str="Input Volumes", parent=None):
        super().__init__(title, parent=parent)
        self._surveysel = surveysel
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self._layout)
        self.update_inputs()

    def update_inputs(self, names: list[str] | None = None):
        names = names or ['Input']
        while self._layout.count() > len(names):
            layout_item = self._layout.takeAt(self._layout.count()-1)
            widget = layout_item.widget()
            if widget:
                if isinstance(widget, Seismic3DSel):
                    try:
                        self._surveysel.currentTextChanged.disconnect(widget.setSurvey)
                    except RuntimeError:
                        pass
                widget.deleteLater()

        while self._layout.count()<len(names):
            entry = Seismic3DSel()
            self._surveysel.currentTextChanged.connect(entry.setSurvey)
            entry.setSurvey(self._surveysel.currentText())
            self._layout.addWidget(entry)

        for idx, name in enumerate(names):
            layout_item = self._layout.itemAt(idx)
            widget = layout_item.widget()
            if isinstance(widget, Seismic3DSel):
                widget.label.setText(name)
                widget.label.adjustSize()

    def get_inputs(self) -> list[str]:
        inputs = []
        for idx in range(self._layout.count()):
            layout_item = self._layout.itemAt(idx)
            widget = layout_item.widget()
            if isinstance(widget, Seismic3DSel):
                inputs.append(widget.currentText())
        return inputs

    def get_common_range(self) -> Sampling:
        from odbind.survey import Survey
        from odbind.seismic3d import Seismic3D
        survey = Survey(self._surveysel.currentText())
        ranges = [survey.inlrange,survey.crlrange,survey.zrange]
        for input in self.get_inputs():
            seis = Seismic3D(survey, input)
            sampling = seis.ranges
            for seisrng, rng in zip(sampling,ranges):
                rng[0] = max(rng[0], seisrng[0])
                rng[1] = min(rng[1], seisrng[1])
        return Sampling(*ranges)

class MultiSeismic3DOutputSelGrp(QGroupBox):
    def __init__(self, surveysel: SurveySel, title:str="Output Volumes", parent=None):
        super().__init__(title, parent)
        self._surveysel = surveysel
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self._layout)
        self.update_outputs()

    def update_outputs(self, names: list[str] | None = None):
        names = names or ['Output']
        while self._layout.count() > len(names):
            layout_item = self._layout.takeAt(self._layout.count()-1)
            widget = layout_item.widget()
            if widget:
                if isinstance(widget, Seismic3DSel):
                    try:
                        self._surveysel.currentTextChanged.disconnect(widget.setSurvey)
                    except RuntimeError:
                        pass
                widget.deleteLater()

        while self._layout.count()<len(names):
            entry = ODObjectSel(translatorgrp="Seismic Data")
            self._surveysel.currentTextChanged.connect(entry.setSurvey)
            entry.setSurvey(self._surveysel.currentText())
            self._layout.addWidget(entry)

        for idx, name in enumerate(names):
            layout_item = self._layout.itemAt(idx)
            widget = layout_item.widget()
            if isinstance(widget, ODObjectSel):
                widget.label.setText(name)
                widget.label.adjustSize()

    def get_outputs(self) -> list[str]:
        outputs = []
        for idx in range(self._layout.count()):
            layout_item = self._layout.itemAt(idx)
            widget = layout_item.widget()
            if isinstance(widget, ODObjectSel):
                outputs.append(widget.text())
        return outputs

class Range3DSelGrp(QGroupBox):
    rangeChanged = Signal(Sampling)

    def __init__(self, surveysel: SurveySel, title: str="Process Range", withstep: bool=False,
                 stepsnap:bool=False, parent=None):
        super().__init__(title, parent=parent)
        self._surveysel = surveysel
        self._ranges = []
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._withstep = withstep
        self._stepsnap = stepsnap
        self.make_ui()
        self._surveysel.currentTextChanged.connect(self._on_survey_changed)
        self._on_survey_changed(surveysel.currentText())

    def _on_survey_changed(self, surveynm: str):
        from odbind.survey import Survey
        survey = Survey(surveynm)
        sampling = Sampling(survey.inlrange,survey.crlrange,survey.zrange)
        self.set_world_range(sampling)
        self.set_ranges(sampling)

    def _on_range_change(self):
        for range in self._ranges:
            values = range.get_values()
            if values[1] < values[0]:
                range.blockSignals(True)
                range.set_values((values[0], values[0]))
                range.blockSignals(False)
        self.rangeChanged.emit(self.get_ranges())

    def set_world_range(self, ranges: Sampling):
        for idx, rng in enumerate(self._ranges):
            for ridx in range(3 if self._withstep else 2):
                rng.set_range(ridx, *ranges[idx])

    def make_ui(self):
        for idx, name in enumerate(("Inlines", "Crosslines", "Z")):
            if self._withstep:
                range = uiSpinBoxRowWidget(label=name, above=False, withsym=False, prefix=("start", "stop", "step"))
            else:
                range = uiSpinBoxRowWidget(label=name, above=False, withsym=False, prefix=["start", "stop"])
            range.valuesChanged.connect(self._on_range_change)
            self._ranges.append(range)
            self._layout.addWidget(range)

    def set_ranges(self, ranges: Sampling):
        for range, newrng in zip(self._ranges, ranges):
            if self._withstep:
                range.set_values(newrng)
            else:
                range.set_values(newrng[:2])

    def get_ranges(self) -> Sampling:
        return Sampling(self._ranges[0].get_values(), self._ranges[1].get_values(), self._ranges[2].get_values())

class ChunkMergeMode(uiLabelledComboBox):
    def __init__(self, label:str="Merge Mode", above:bool=True, parent=None):
        super().__init__(label=label, above=above, parent=parent)

    def initui(self):
        from odbind.seismic3d import MergeMode
        self.clear()
        modes = [mode.name for mode in MergeMode]
        self.addItems(modes)
        self.setCurrentIndex(MergeMode.Blend)

class ODObjectSel(QWidget):
    def __init__(self,
            translatorgrp: str="Seismic Data",
            label:str="Object",
            above:bool=True,
            parent=None):
        super().__init__(parent)
        self.translatorgrp = translatorgrp
        self.above = above
        self.input = QComboBox()
        self.input.setEditable(True)
        self.input.setDuplicatesEnabled(False)
        self.input.setInsertPolicy(QComboBox.InsertPolicy.InsertAtCurrent)
        self.input.setPlaceholderText("Type or select...")
        self.input.setMaxVisibleItems(10)
        self.input.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.input.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.button = QPushButton("Select")
        self.button.clicked.connect(self.show_dialog)
        self.label = QLabel(label)
        self.label.setBuddy(self.input)
        if above:
            labelled_layout = QVBoxLayout(self)
            layout = QHBoxLayout()
        else:
            labelled_layout = QHBoxLayout(self)
            layout = labelled_layout
        labelled_layout.setContentsMargins(0, 0, 0, 0)
        labelled_layout.addWidget(self.label)
        if above:
            labelled_layout.addLayout(layout)
        else:
            layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.button)

        self.buttonClicked = self.button.clicked
        self.textChanged = self.input.currentTextChanged

    def setSurvey(self, survey_name: str):
        self.survey = survey_name
        self.input.clear()

    def show_dialog(self):
        from odbind.survey import Survey

        caption = "Select output " + self.translatorgrp
        dlg = ODObjectSelDlg(self.survey, caption=caption, parent=self)
        dlg.clear()
        dlg.addItems(Survey(self.survey).get_object_names(self.translatorgrp))
        dlg.exec()
        if dlg.result()==QDialog.DialogCode.Accepted:
            if self.input.findText(dlg.text())==-1:
                self.input.addItem(dlg.text())
            self.input.setCurrentText(dlg.text())
            self.translator = dlg.chosen_translator()

    def text(self) -> str:
        return self.input.currentText()

    def chosen_translator(self) -> str:
        return self.translator

class ODObjectSelDlg(QDialog):
    def __init__(self,
        survey: str,
        label:str="Object",
        above:bool=True,
        caption: str="Select an Object",
        parent=None):
        super().__init__(parent)
        self.setWindowTitle(caption)
        self.object_list = QListWidget()
        sp = self.object_list.sizePolicy()
        sp.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        self.object_list.setSizePolicy(sp)
        self.translator = uiLabelledComboBox(label="Write to", above=False)
        self.object_name = uiLabelledLineEdit(label="Name", above=False)
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.addRow("", self.object_list)
        form_layout.addRow(self.translator.label, self.translator.input)
        form_layout.addRow(self.object_name.label, self.object_name.input)
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        main_layout.addWidget(self.translator)
        main_layout.addWidget(self.object_name)
        self.object_list.currentTextChanged.connect(self.object_name.setText)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.setLayout(main_layout)
        self.textChanged = self.object_name.textChanged

    def clear(self):
        self.object_list.clear()

    def addItems(self, items: list[str]):
        self.object_list.addItems(items)

    def text(self) -> str:
        return self.object_name.text()

    def chosen_translator(self) -> str:
        return self.translator.currentText()

def odbind_found() -> bool:
    if find_spec("odbind") is None or find_spec("dgbpy") is None:
        seldir = QFileDialog.getExistingDirectory(
            None,
            caption="Select the OpendTect Pro installation root",
            dir="",
            options=QFileDialog.Option.ShowDirsOnly
        )
        if seldir:
            odpython_path = os.path.join(seldir, "bin", "python")
            if os.path.exists(odpython_path) and odpython_path not in sys.path:
                sys.path.insert(0, odpython_path)
    return find_spec("odbind") is not None and find_spec("dgbpy") is not None
