#
# Copyright (C) 2026 Wayne Mogg All rights reserved.
# This file may be used under the terms of the GNU GENERAL PUBLIC LICENSE Version 3 License
#
import numpy as np
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
from shared.uitools import uiLabelledComboBox, uiSpinBoxRowWidget


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
        self.slicetype = uiLabelledComboBox(label="", above=False)
        self.slicetype.addItems(["Inline", "Crossline", "Z"])
        self.slicesel = uiSpinBoxRowWidget(prefix=[""], label="Slice", above=False, withsym=False)
        self.slicesel.set_range(-1, 1, 8, 1)
        self.controls_layout.addWidget(self.surveysel)
        self.controls_layout.addWidget(self.baseseis)
        self.controls_layout.addWidget(self.overseis)
        self.controls_layout.addWidget(self.slicetype)
        self.controls_layout.addWidget(self.slicesel)

        self.seismic_layout = pg.GraphicsLayoutWidget()
        self.seis_view = self.seismic_layout.addPlot()
        self.seis_view.hideAxis('bottom')
        self.seis_view.showAxis('top')
        self.seis_view.getViewBox().scene().views()[0].setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )
        self.baseseis_item = pg.ImageItem()
        self.overseis_item = pg.ImageItem()
#        self.overseis_item.setOpacity(0.25)
        self.seis_view.addItem(self.baseseis_item)
        self.seis_view.addItem(self.overseis_item)
#        self.seis_view.addColorBar(self.baseseis_item,colorMap='CET-L2')
        self.baseseis_cmap = pg.ColorBarItem(colorMap='CET-L2')
        self.baseseis_cmap.setImageItem(self.baseseis_item)
        over_lut = np.zeros((256, 4), dtype=np.uint8)
        over_lut[:, 0] = np.arange(256)
        over_lut[:, 1] = 0
        over_lut[:, 2] = 0
        over_lut[0, 3] = 0
        over_lut[1:, 3] = 200
        self.overseis_item.setLookupTable(over_lut)
        self.overseis_item.setLevels([0.5,1.0])
#        self.overseis_cmap = pg.ColorBarItem(colorMap='CET-L18')
#        self.overseis_cmap.setImageItem(self.overseis_item)
        self.seismic_layout.addItem(self.baseseis_cmap)
#        self.seismic_layout.addItem(self.overseis_cmap)
        #self.overseis_item = pg.ImageItem()

        self._layout.addLayout(self.controls_layout)
        self._layout.addWidget(self.seismic_layout)
        self.setLayout(self._layout)
        #self.seis_view.addItem(self.overseis_item)
        self._on_survey_change()
        self.surveysel.currentTextChanged.connect(self._on_survey_change)
        self.baseseis.currentTextChanged.connect(self._on_data_change)
        self.overseis.currentTextChanged.connect(self._on_data_change)
        self.slicetype.currentTextChanged.connect(self._on_slicetype_change)
        self.slicetype.currentTextChanged.connect(self.update_view)
        self.slicesel.valuesChanged.connect(self.update_view)
        # Enable Alpha Blending for Overlay
        #self.overseis_item.setOpacity(0.5)

    def _on_survey_change(self):
        surveynm = self.surveysel.currentText()
        self._survey = Survey(surveynm)
        self.baseseis.setSurvey(surveynm)
        self.overseis.setSurvey(surveynm)
        self._on_data_change()

    def _on_data_change(self):
        self._baseseismic = Seismic3D(self._survey, self.baseseis.currentText())
        self._overseismic = Seismic3D(self._survey, self.overseis.currentText())
        self._on_slicetype_change()

    def _on_slicetype_change(self):
        ranges = self._baseseismic.ranges
        slicetype = self.slicetype.currentIndex()
        self.slicesel.set_range(-1, ranges[slicetype][0], ranges[slicetype][1], ranges[slicetype][2])
        self.slicesel.set_values([(ranges[slicetype][0]+ranges[slicetype][1])//2])
        self.update_view()

    def update_view(self):
        ranges = self._baseseismic.ranges
        slice = self.slicesel.get_values()[0]
        slicetype = self.slicetype.currentIndex()
        if slicetype==0:
            base = self._baseseismic.iline[slice]
            over = self._overseismic.iline[slice]
            x0 = base.xline.values[0]
            y0 = base.twt.values[0]
            dx = ranges.crlrg[2]
            dy = ranges.zrg[2]
            self.seis_view.setAspectLocked(False)
            self.seis_view.invertY(True)
        elif slicetype==1:
            base = self._baseseismic.xline[slice]
            over = self._overseismic.xline[slice]
            x0 = base.iline.values[0]
            y0 = base.twt.values[0]
            dx = ranges.inlrg[2]
            dy = ranges.zrg[2]
            self.seis_view.setAspectLocked(False)
            self.seis_view.invertY(True)
        else:
            base = self._baseseismic.zslice[self._baseseismic.z_index(slice)]
            over = self._overseismic.zslice[self._overseismic.z_index(slice)]
            x0 = base.iline.values[0]
            y0 = base.xline.values[0]
            dx = ranges.inlrg[2]
            dy = ranges.crlrg[2]
            self.seis_view.setAspectLocked(True)
            self.seis_view.invertY(False)
        base_first = next(iter(base.data_vars))
        over_first = next(iter(over.data_vars))
        transform = QTransform()
        transform.translate(x0 - (dx / 2.0), y0 - (dy / 2.0))
        transform.scale(dx, dy)
        self.baseseis_item.setTransform(transform)
        data = base[base_first].values
        data[np.isnan(data)] = 0.0
        minval = data.min()
        maxval = data.max()
        self.baseseis_item.setImage(data)
        self.baseseis_item.setLevels([minval,maxval])
        self.baseseis_cmap.setLevels(values=(minval,maxval))
        self.overseis_item.setTransform(transform)
        data = over[over_first].values
        data[np.isnan(data)] = 0.0
        minval = data.min()
        maxval = data.max()
        self.overseis_item.setImage(data)
        self.overseis_item.setLevels([minval,maxval])
#        self.overseis_cmap.setLevels(values=(minval,maxval))
