from .. import types

class ColorLayout:
  __slots__ = 'foreground','background','tertiary'
  def __init__(self,foreground:types.ColorType,background:types.ColorType,tertiary:types.ColorType|None = None):
    self.foreground = foreground
    self.background = background
    self.tertiary = tertiary or background
