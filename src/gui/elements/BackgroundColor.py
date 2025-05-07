from ..core import *

class BackgroundColor:
  order_in_layer = -1
  __slots__ = 'color'
  def __init__(self,color:types.ColorType|int = 0):
    self.color = color

  def draw(self,surf:Surface):
    surf.fill(self.color)

