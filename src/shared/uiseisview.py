#
# Copyright (C) 2026 Wayne Mogg All rights reserved.
# This file may be used under the terms of the GNU GENERAL PUBLIC LICENSE Version 3 License
#
import numpy as np
import pyqtgraph as pg
from odbind.seismic3d import Seismic3D
from odbind.survey import Survey
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from shared.uiodbind import (
    Seismic3DSel,
    SurveySel,
)
from shared.uitools import uiLabelledComboBox, uiSpinBoxRowWidget


def cmap_fault_red():
    return pg.ColorMap(
        [0.0,0.5,1.0],
        [(255,255,255,0),(255,125,125,255),(255,0,0,255)]
    )

def cmap_dgb_fault():
    return pg.ColorMap(
        [0.0,0.4,0.49,0.58,0.85,1.0],
        [(255,255,255,0),(197,180,153,125),(216,173,1,255),(73,145,9,255),(0,85,0,255),(0,111,166,255)]
    )

CMAPS = {
    "CET-L2": "CET-L2",
    "Fault-Red": cmap_fault_red(),
    "DGB_Fault": cmap_dgb_fault(),
}

class uiColorBarWidget(QWidget):
    colorMapChanged = Signal(str)
    clipChanged = Signal()

    def __init__(self, cmapdefault="Fault-Red", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.cmaps = uiLabelledComboBox(label="", above=False)
        self.cmaps.addItems(list(CMAPS.keys()))
        self.cmaps.setCurrentText(cmapdefault)
        self.clipmode = uiLabelledComboBox(label="", above=False)
        self.clipmode.addItems(["PercClip", "StdClip", "RangeClip"])
        self.lo_spin = QDoubleSpinBox()
        self.hi_spin = QDoubleSpinBox()
        for sb in (self.lo_spin, self.hi_spin):
            sb.setMaximumWidth(80)
            sb.setRange(0.0, 100.0)
            sb.setSingleStep(1.0)
            sb.setDecimals(1)
        self.lo_spin.setValue(2.0)
        self.hi_spin.setValue(98.0)
        layout.addWidget(self.cmaps)
        layout.addWidget(self.clipmode)
        layout.addWidget(self.lo_spin)
        layout.addWidget(self.hi_spin)

        self.colorMapChanged = self.cmaps.currentTextChanged
        self.clipmode.currentTextChanged.connect(self._on_clipmode_change)
        self.lo_spin.valueChanged.connect(self._emit_clipchanged)
        self.hi_spin.valueChanged.connect(self._emit_clipchanged)

    def colorMap(self):
        return self.cmaps.currentText()

    def compute_levels(self, data):
        lo = self.lo_spin.value()
        hi = self.hi_spin.value()
        if self.clipmode.currentText() == "PercClip":
            return np.percentile(data, lo), np.percentile(data, hi)
        if self.clipmode.currentText() == "RangeClip":
            return lo, hi
        mean = data.mean()
        std = data.std()
        return mean - lo * std, mean + hi * std

    def _emit_clipchanged(self, *_):
        self.clipChanged.emit()

    def _on_clipmode_change(self, mode):
        self.lo_spin.blockSignals(True)
        self.hi_spin.blockSignals(True)
        if mode == "PercClip":
            for sb in (self.lo_spin, self.hi_spin):
                sb.setRange(0.0, 100.0)
                sb.setSingleStep(1.0)
            self.lo_spin.setValue(2.0)
            self.hi_spin.setValue(98.0)
        elif mode == "RangeClip":
            for sb in (self.lo_spin, self.hi_spin):
                sb.setRange(-10000.0, 10000.0)
                sb.setSingleStep(10.0)
            self.lo_spin.setValue(0.0)
            self.hi_spin.setValue(100.0)
        else:
            for sb in (self.lo_spin, self.hi_spin):
                sb.setRange(0.0, 10.0)
                sb.setSingleStep(0.1)
            self.lo_spin.setValue(2.0)
            self.hi_spin.setValue(2.0)
        self.lo_spin.blockSignals(False)
        self.hi_spin.blockSignals(False)
        self.clipChanged.emit()

class uiSeisView(QWidget):

    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout()
        self.controls_layout = QGridLayout()
        self.surveysel = SurveySel(above=False)
        self.baseseis = Seismic3DSel("Background", above=False)
        self.overseis = Seismic3DSel("Overlay", above=False)
        self.baseseis.setSurvey(self.surveysel.currentText())
        self.overseis.setSurvey(self.surveysel.currentText())
        self.baseseis_cbar = uiColorBarWidget(cmapdefault="CET-L2")
        self.overseis_cbar = uiColorBarWidget(cmapdefault="Fault-Red")
        labelw = max(self.baseseis.label.sizeHint().width(),
                     self.overseis.label.sizeHint().width())
        self.baseseis.setLabelWidth(labelw)
        self.overseis.setLabelWidth(labelw)
        self.slicetype = uiLabelledComboBox(label="", above=False)
        self.slicetype.addItems(["Inline", "Crossline", "Z"])
        self.slicesel = uiSpinBoxRowWidget(prefix=[""], label="Slice", above=False, withsym=False)
        self.slicesel.set_range(-1, 1, 8, 1)
        self.controls_layout.addWidget(self.surveysel, 0, 0)
        self.controls_layout.addWidget(self.baseseis, 0, 1)
        self.controls_layout.addWidget(self.baseseis_cbar, 0, 2)
        self.controls_layout.addWidget(self.overseis, 1, 1)
        self.controls_layout.addWidget(self.overseis_cbar, 1, 2)
        self.controls_layout.addWidget(self.slicetype, 1, 3)
        self.controls_layout.addWidget(self.slicesel, 1, 4)

        self.seismic_layout = pg.GraphicsLayoutWidget()
        self.seis_view = self.seismic_layout.addPlot()
        self.seis_view.hideAxis('bottom')
        self.seis_view.showAxis('top')
        self.seis_view.getViewBox().scene().views()[0].setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )
        self.baseseis_item = pg.ImageItem()
        self.overseis_item = pg.ImageItem()
        self.seis_view.addItem(self.baseseis_item)
        self.seis_view.addItem(self.overseis_item)
        self.baseseis_cmap = pg.ColorBarItem(colorMap='CET-L2')
        self.baseseis_cmap.setImageItem(self.baseseis_item)
        self.seismic_layout.addItem(self.baseseis_cmap)
        self.overseis_cmap = pg.ColorBarItem(colorMap=CMAPS['Fault-Red'])
        self.overseis_cmap.setImageItem(self.overseis_item)
        self.seismic_layout.addItem(self.overseis_cmap)

        self._layout.addLayout(self.controls_layout)
        self._layout.addWidget(self.seismic_layout)
        self.setLayout(self._layout)
        self.baseseis_cbar.colorMapChanged.connect(self._on_baseseis_cbar_change)
        self.overseis_cbar.colorMapChanged.connect(self._on_overseis_cbar_change)
        self.baseseis_cbar.clipChanged.connect(self.update_view)
        self.overseis_cbar.clipChanged.connect(self.update_view)
        self._on_survey_change()
        self.surveysel.currentTextChanged.connect(self._on_survey_change)
        self.baseseis.currentTextChanged.connect(self._on_data_change)
        self.overseis.currentTextChanged.connect(self._on_data_change)
        self.slicetype.currentTextChanged.connect(self._on_slicetype_change)
        self.slicetype.currentTextChanged.connect(self.update_view)
        self.slicesel.valuesChanged.connect(self.update_view)

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

    def _on_baseseis_cbar_change(self):
        self.baseseis_cmap.setColorMap(CMAPS[self.baseseis_cbar.colorMap()])

    def _on_overseis_cbar_change(self):
        self.overseis_cmap.setColorMap(CMAPS[self.overseis_cbar.colorMap()])

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
        minval, maxval = self.baseseis_cbar.compute_levels(data)
        self.baseseis_item.setImage(data)
        self.baseseis_item.setLevels([minval,maxval])
        self.baseseis_cmap.setLevels(values=(minval,maxval))
        self.overseis_item.setTransform(transform)
        data = over[over_first].values
        data[np.isnan(data)] = 0.0
        minval, maxval = self.overseis_cbar.compute_levels(data)
        self.overseis_item.setImage(data)
        self.overseis_item.setLevels([minval,maxval])
        self.overseis_cmap.setLevels(values=(minval,maxval))
