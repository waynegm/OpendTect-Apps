#
# Copyright (C) 2026 Wayne Mogg All rights reserved.
# This file may be used under the terms of the GNU GENERAL PUBLIC LICENSE Version 3 License
#

import pyqtgraph as pg
from odbind.seismic3d import Seismic3D
from odbind.survey import Survey
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from shared.uiodbind import (
    Seismic3DSel,
    SurveySel,
)
from shared.uitools import uiSpinBoxRowWidget


class uiSeisView(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout()
        self.controls_layout = QHBoxLayout()
        self.surveysel = SurveySel(above=False)
        self.baseseis = Seismic3DSel("Background", above=False)
        self.overseis = Seismic3DSel("Overlay", above=False)
        self.baseseis.setSurvey(self.surveysel.currentText())
        self.overseis.setSurvey(self.surveysel.currentText())
        self.slicesel = uiSpinBoxRowWidget(prefix=[""], label="Slice", above=False, withsym=False)
        self.slicesel.set_range(-1, 1, 8, 1)
        self.surveysel.currentTextChanged.connect(self.baseseis.setSurvey)
        self.surveysel.currentTextChanged.connect(self.overseis.setSurvey)
        self.baseseis.currentTextChanged.connect(self.data_change)
        self.baseseis.currentTextChanged.connect(self.update_base_layer)
        self.slicesel.valuesChanged.connect(self.update_base_layer)
        self.controls_layout.addWidget(self.surveysel)
        self.controls_layout.addWidget(self.baseseis)
        self.controls_layout.addWidget(self.overseis)
        self.controls_layout.addWidget(self.slicesel)
        self._layout.addLayout(self.controls_layout)

        self.inline = 425

        self.seismic_layout = pg.GraphicsLayoutWidget()
        self._layout.addWidget(self.seismic_layout)

        self.seis_view = self.seismic_layout.addPlot()
        self.seis_view.hideAxis('bottom')
        self.seis_view.showAxis('top')
        self.seis_view.invertY(True)
        self.seis_view.getViewBox().scene().views()[0].setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )
        self.baseseis_item = pg.ImageItem()
        #self.overseis_item = pg.ImageItem()

        self.seis_view.addItem(self.baseseis_item)
        self.setLayout(self._layout)
        #self.seis_view.addItem(self.overseis_item)
        self.data_change()
        # Enable Alpha Blending for Overlay
        #self.overseis_item.setOpacity(0.5)

#        self.update_base_layer()
    def data_change(self):
        survey = Survey(self.surveysel.currentText())
        seismic = Seismic3D(survey, self.baseseis.currentText())
        ranges = seismic.ranges
        self.slicesel.set_range(-1, ranges.inlrg[0], ranges.inlrg[1], ranges.inlrg[2])
        self.slicesel.set_values([(ranges.inlrg[0]+ranges.inlrg[1])//2])

    def update_base_layer(self):
        survey = Survey(self.surveysel.currentText())
        seismic = Seismic3D(survey, self.baseseis.currentText())
        ranges = seismic.ranges
        inline = self.slicesel.get_values()[0]
        data = seismic.iline[inline]
        first = next(iter(data.data_vars))
        dx = ranges.inlrg[2]
        dy = ranges.zrg[2]
        transform = QTransform()
        x0 = data.xline.values[0]
        y0 = data.twt.values[0]
        transform.translate(x0 - (dx / 2.0), y0 - (dy / 2.0))
        transform.scale(dx, dy)
        self.baseseis_item.setTransform(transform)
        self.baseseis_item.setImage(data[first].values)
