import os
import sys

from importlib.util import find_spec
from unittest.main import main

from shared.uitools import (
    uiLabelledComboBox,
    uiLabelledLineEdit,
)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)

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
        return

    def text(self) -> str:
        return self.input.currentText()

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
            if os.path.exists(odpython_path):
                if odpython_path not in sys.path:
                    sys.path.insert(0, odpython_path)
    return find_spec("odbind") is not None and find_spec("dgbpy") is not None
