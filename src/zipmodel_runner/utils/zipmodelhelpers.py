#
# Copyright (C) 2026 Wayne Mogg All rights reserved.
# This file may be used under the terms of the GNU GENERAL PUBLIC LICENSE Version 3 License
#

import json
import logging
import zipfile
from dataclasses import asdict
from types import ModuleType

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


def is_seisimg2img(modelinfo):
    return modelinfo["learn_type"] == "Seismic Image Transformation"

def extract_model_info(zipmodel_path):
    """Returns the modelinfo data from a zipmodel file."""
    try:
        modelinfo_json = 'modelinfo.json'
        with zipfile.ZipFile(zipmodel_path, 'r') as z:
            if modelinfo_json in z.namelist():
                with z.open(modelinfo_json) as f:
                    return json.load(f)
            src = z.read('zipmodel.py').decode('utf-8')
        compiled = compile(src, filename='zipmodel.py', mode='exec')
        sandbox = ModuleType('sandbox_module')
        sandbox.__dict__.update({
            '__file__': 'zipmodel.py'
        })
        exec(compiled, sandbox.__dict__)
        ZipModelClass = sandbox.__dict__.get('ZipModel')
        if ZipModelClass and hasattr(ZipModelClass, 'modelinfo'):
            return asdict(ZipModelClass.modelinfo)
        raise AttributeError('ZipModel class or modelinfo attribute is missing.')
    except Exception as e:
        print(f'Failed to extract modelinfo from {zipmodel_path}: {e}')
#        logger.error(f'Failed to extract modelinfo from {zipmodel_path}: {e}')
        raise

class ZipModelInfoReader(QThread):
    info_loaded = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, zipmodel_path):
        super().__init__()
        self.zipmodel_path = zipmodel_path

    def run(self):
        try:
            info = extract_model_info(self.zipmodel_path)
            if info:
                self.info_loaded.emit(info)
            else:
                self.error_occurred.emit('No modelinfo found in zipmodel.')
        except Exception as e:
            self.error_occurred.emit(str(e))
