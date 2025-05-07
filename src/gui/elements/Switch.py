from ..core import *

class Switch(DrawBase):
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,callback:types.Callable[[bool],None]):
    self.rect = Rect(pos,size)
    self.callback = callback
    self.color_scheme = color_scheme
    self.state = False
    self.mhover = False
    self.clicking = False

  def setState(self,newState:bool):
    self.state = newState
    return self

  def update(self,input:Input):
    self.mhover = self.rect.collidepoint(input.mpos)
    if input.mb1d and self.mhover:
      self.clicking = True
      self.state = not self.state
      self.callback(self.state)
    elif input.mb1u and self.clicking:
      self.clicking = False

  def draw(self,surf:Surface):
    width = 0 if self.state else 2
    if self.clicking:
      color = self.color_scheme.getActive()
    elif self.mhover:
      color = self.color_scheme.getIdle()
    else:
      color = self.color_scheme.getInactive()
    draw.rect(surf,color,self.rect,width,4)
