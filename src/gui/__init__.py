'''
Framework for building Graphical User Interfaces for applications with Pygame-CE\n

Author: Hithere32123

This has been used to make:\n
Pixel Art Program\n
Gravity Sim\n
Music Player (similar to Spotify)\n
Notes Application (trashy)
'''

from .core import *
from . import elements
from . import ui
from .core_elements.Layer import Layer
from .core_elements.Space import Space
from . import utils
from . import settings


__all__ = [
    'elements',
    'ui',
    'Layer',
    'Space',
    'utils',
    'settings'
] 

from . import core
__all__ += core.__all__
del core
