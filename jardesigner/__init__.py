# -*- coding: utf-8 -*-
"""
JARDesigner - Web-based GUI for MOOSE neuroscience simulator
"""

__version__ = '0.1.0'

# Import from private module
from ._jardesigner import JarDesigner

# Re-export for backward compatibility
from . import _jardesigner as jardesigner

__all__ = ['JarDesigner', 'jardesigner']
