from ..core import *

class ColorArea(DrawBase):
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],color:types.ColorType = (0,0,0)):
    self.rect = Rect(pos,size)
    self.color = color

  def draw(self,surf:Surface):
    surf.fill(self.color,self.rect)
