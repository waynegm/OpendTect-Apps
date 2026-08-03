#
# Copyright (C) 2026 Wayne Mogg All rights reserved.
# This file may be used under the terms of the GNU GENERAL PUBLIC LICENSE Version 3 License
#

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class uiLabelledLineEdit(QWidget):
    """A labelled textbox"""

    def __init__(self,
            label: str="LineEdit",
            above: bool=True,
            parent=None):
        super().__init__(parent)
        if above:
            layout = QVBoxLayout(self)
        else:
            layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.input = QLineEdit()
        self.label = QLabel(label)
        self.label.setBuddy(self.input)
        layout.addWidget(self.label)
        layout.addWidget(self.input, 1)

        self.textChanged = self.input.textChanged

    def text(self) -> str:
        return self.input.text()

    def setText(self, text: str):
        self.input.setText(text)

    def clear(self):
        self.input.clear()

    def blockSignals(self, block: bool) -> bool:
        self.input.blockSignals(block)
        return super().blockSignals(block)


class uiLabelledComboBox(QWidget):
    """A labelled combobox"""

    def __init__(self,
            label: str="ComboBox",
            above: bool=True,
            parent=None):
        super().__init__(parent)
        if above:
            layout = QVBoxLayout(self)
        else:
            layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.input = QComboBox()
        self.input.setMaxVisibleItems(10)
        self.input.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.input.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.label = QLabel(label)
        self.label.setBuddy(self.input)
        layout.addWidget(self.label)
        layout.addWidget(self.input, 1)

        self.currentIndexChanged = self.input.currentIndexChanged
        self.currentTextChanged = self.input.currentTextChanged

    def addItem(self, text, userData=None):
        self.input.addItem(text, userData)

    def addItems(self, texts):
        self.input.addItems(texts)

    def clear(self):
        self.input.clear()

    def currentText(self) -> str:
        return self.input.currentText()

    def currentIndex(self) -> int:
        return self.input.currentIndex()

    def setCurrentIndex(self, index: int):
        self.input.setCurrentIndex(index)

    def blockSignals(self, block: bool) -> bool:
        self.input.blockSignals(block)
        return super().blockSignals(block)

class uiFileSel(QWidget):
    """A file selection widget"""

    def __init__(self,
            label: str="FileSel",
            above: bool=True,
            start:str=".",
            filter:str="All files (*)",
            caption:str="",
            mode:QFileDialog.FileMode=QFileDialog.FileMode.AnyFile,
            parent=None):
        super().__init__(parent)
        self.mode = mode
        self.start = start
        self.filter = filter
        if not caption:
            if self.mode==QFileDialog.FileMode.Directory:
                self.defcaption = "Select a Folder..."
            else:
                self.defcaption = "Select a File..."
        else:
            self.defcaption = caption
        self.caption = self.defcaption

        self.input = QLineEdit()
        self.input.setPlaceholderText(self.caption)
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
        self.textChanged = self.input.textChanged


    def show_dialog(self):
        if self.mode==QFileDialog.FileMode.Directory:
            thepath = QFileDialog.getExistingDirectory(
                self,
                caption = self.caption,
                dir = self.start,
                options = QFileDialog.Option.ShowDirsOnly
            )
        elif self.mode==QFileDialog.FileMode.ExistingFile:
            thepath, _ = QFileDialog.getOpenFileName(
                self,
                caption = self.caption,
                dir = self.start,
                filter = self.filter
            )
        elif self.mode==QFileDialog.FileMode.AnyFile:
            thepath, _ = QFileDialog.getSaveFileName(
                self,
                caption = self.caption,
                dir = self.start,
                filter = self.filter
            )
        else:
            QMessageBox.critical(
                self,
                "Error: ⚠️ Unsupported FileMode",
                "This widget can only be used to select a single folder or file"
            )
            return
        if thepath:
            self.input.setText(thepath)

    def path(self) -> str:
        thepath = self.input.text()
        if thepath==self.defcaption:
            return ""
        else:
            return thepath

class uiPrefixSpinBox(QSpinBox):
    """Custom spin box that enforces a read-only text prefix."""
    def __init__(self, prefix_text, parent=None):
        super().__init__(parent)
        if prefix_text:
            self.setPrefix(f"{prefix_text}: ")

class uiSpinBoxRowWidget(QWidget):
    """A row of spinboxes with labels inside the input box."""

    valuesChanged = Signal(tuple)

    def __init__(self,
        prefix=("inl","crl","z"),
            label: str="SpinBoxes",
            above: bool=True,
            withsym: bool=True,
            parent=None):
        super().__init__(parent)
        self._is_syncing = False
        self.withsym = withsym

        self.label = QLabel(label)
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

        layout.setSpacing(15)
        self.spinners = []
        for idx, nm in enumerate(prefix):
            spinbox = uiPrefixSpinBox(nm)
            self.spinners.append(spinbox)
            layout.addWidget(spinbox)
            spinbox.valueChanged.connect(lambda val, theidx=idx: self.value_changedcb(theidx,val))
        self.label.setBuddy(self.spinners[0])

        if self.withsym:
            self.symmetric = QCheckBox("Symmetric")
            self.symmetric.toggled.connect(self.symmetry_cb)
            layout.addWidget(self.symmetric)

    def numbox(self):
        return len(self.spinners)

    def set_range(self, index, min_val, max_val, step_val):
        """Helper to modify ranges and step increments of spin boxes."""
        if index<0:
            for sb in self.spinners:
                sb.setRange(min_val, max_val)
                sb.setSingleStep(step_val)
        elif 0 <= index < len(self.spinners):
            sb = self.spinners[index]
            sb.setRange(min_val, max_val)
            sb.setSingleStep(step_val)

    def set_values(self, values):
        for sb, val in zip(self.spinners, values) :
            sb.blockSignals(True)
            if self.withsym and self.symmetric.isChecked():
                sb.setValue(values[0])
            else:
                sb.setValue(val)
            sb.blockSignals(False)
        self.valuesChanged.emit(self.get_values())

    def get_values(self):
        return tuple([sb.value() for sb in self.spinners])

    def value_changedcb(self, idx, val):
        if self._is_syncing:
            return
        if self.withsym and self.symmetric.isChecked():
            self._is_syncing = True
            for i, sb in enumerate(self.spinners):
                if i != idx:
                    sb.setValue(val)
            self._is_syncing = False
        self.valuesChanged.emit(self.get_values())

    def symmetry_cb(self, checked):
        if checked:
            val = self.spinners[0].value()
            self.set_values(tuple([val for _ in self.spinners]))
