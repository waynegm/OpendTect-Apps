import logging
import zipfile
import builtins as _builtins_module
from types import ModuleType

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

_builtins_obj = __builtins__ if isinstance(__builtins__, dict) else __builtins__
_real_import = _builtins_module.__import__

_BLOCKED_IMPORTS = frozenset({
    'os', 'sys', 'subprocess', 'shutil', 'signal', 'socket',
    'http', 'urllib', 'ftplib', 'smtplib', 'xmlrpc', 'telnetlib',
    'ctypes', 'multiprocessing', 'threading', 'pickle', 'shelve',
    'dbm', 'sqlite3', 'code', 'codeop', 'pdb', 'profile', 'trace',
    'gc', 'inspect', 'dis', 'pkgutil', 'zipimport',
    'runpy', 'compileall',
})

def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    top_level = name.split('.')[0]
    if top_level in _BLOCKED_IMPORTS:
        raise ImportError(f'Import of {name!r} is not allowed in zipmodel sandbox')
    return _real_import(name, globals, locals, fromlist, level)

def _make_safe_builtins():
    builtins = {
        name: getattr(_builtins_obj, name)
        for name in (
            'abs', 'bool', 'dict', 'dir', 'enumerate', 'filter', 'float',
            'frozenset', 'getattr', 'hasattr', 'hash', 'int', 'isinstance',
            'issubclass', 'iter', 'len', 'list', 'map', 'max', 'min',
            'next', 'print', 'property', 'range', 'repr', 'reversed',
            'round', 'set', 'setattr', 'slice', 'sorted', 'str', 'sum',
            'super', 'tuple', 'type', 'zip',
        )
        if hasattr(_builtins_obj, name)
    }
    builtins['__import__'] = _restricted_import
    return builtins

_SAFE_BUILTINS = _make_safe_builtins()

def is_seisimg2img(modelinfo):
    from dgbpy.zipmodelbase import LearnType
    return modelinfo.learn_type == LearnType.SeisImg2Img

def extract_model_info(zipmodel_path):
    """Returns the modelinfo data from a zipmodel file."""
    try:
        with zipfile.ZipFile(zipmodel_path, 'r') as z:
            src = z.read('zipmodel.py').decode('utf-8')
        compiled = compile(src, filename='zipmodel.py', mode='exec')
        sandbox = ModuleType('sandbox_module')
        sandbox.__dict__.update({
            '__file__': 'zipmodel.py',
            '__builtins__': _SAFE_BUILTINS,
        })
        exec(compiled, sandbox.__dict__)
        ZipModelClass = sandbox.__dict__.get('ZipModel')
        if ZipModelClass and hasattr(ZipModelClass, 'modelinfo'):
            return ZipModelClass.modelinfo
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
