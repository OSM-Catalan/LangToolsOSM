from . import LangToolsOSM
from .LangToolsOSM import *
from pkg_resources import require  # part of setuptools
__version__ = require("LangToolsOSM")[0].version  # defined in setup.py
