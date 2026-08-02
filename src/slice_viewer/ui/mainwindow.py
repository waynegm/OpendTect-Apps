#
# Copyright (C) 2026 Wayne Mogg All rights reserved.
# This file may be used under the terms of the GNU GENERAL PUBLIC LICENSE Version 3 License
#

from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from shared.uiseisview import uiSeisView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpendTect PySide6 Slice Viewer")
        self.resize(1000, 700)
        self._layout = QVBoxLayout()

        self.seisview = uiSeisView()
        self._layout.addWidget(self.seisview)
        self.central_widget = QWidget()
        self.central_widget.setLayout(self._layout)
        self.setCentralWidget(self.central_widget)

        self.seisview.update_base_layer()
