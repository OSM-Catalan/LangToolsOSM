from . import osm_utils
from .osm_utils import *
from . import wikimedia
from .wikimedia import *
from pkg_resources import require  # part of setuptools
__version__ = require('LangToolsOSM')[0].version  # defined in setup.py
