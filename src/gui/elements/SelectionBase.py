from ..core import *
from .Button import Button

class SelectionBase(Button):
  __slots__ = 'pos','yoffset'
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,onDown:types.EventHook|None = None,onUp:types.EventHook|None = None) -> None:
    self.pos = pos
    super().__init__(pos,size,color_scheme,onDown,onUp)
    self.setYOffset(0)  

  def onYOffsetChangeHook(self,offsetY:int): ...
  def getYOffSet(self) -> int: return self.yoffset

  def setYOffset(self,y:int): 
    self.yoffset = y
    self.rect.top = self.pos[1] - y
    self.onYOffsetChangeHook(y)

