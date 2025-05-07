'''
This File is mainly for elements so that they can easily import all commonly used classes.
'''

from pygame import Surface
from pygame import Rect
from pygame import draw
from pygame import constants as const
from . import theme
from . import types
from .Input import Input

from .DrawBase import DrawBase
from ..utils.Event import Event
from ..utils.ObjectValue import ObjectValue

from .theme.ColorScheme import ColorScheme
from .theme.ColorLayout import ColorLayout

__all__ = [
    'Surface',
    'Rect',
    'draw',
    'const',
    'theme',
    'types',
    'Input',
    'DrawBase',
    'Event',
    'ObjectValue',
    'ColorScheme',
    'ColorLayout'
]