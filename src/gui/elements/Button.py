from ..core import *

class Button(DrawBase):
  rect:Rect
  __slots__ = 'rect','color_scheme','onDown','onUp','state','colors'
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,onDownFunction:types.EventHook|None=None,onUpFunction:types.EventHook|None=None):
    self.rect = Rect(pos,size)
    self.color_scheme = color_scheme
    self.onDown = onDownFunction
    self.onUp = onUpFunction
    self.state = 0 #0 -> up, 1 -> hover, 2 -> down
    self.colors = self.color_scheme.getInactive(),self.color_scheme.getIdle(),self.color_scheme.getActive()

  def setToUp(self):
    if self.state == 2 and self.onUp is not None:
      self.onUp()
    self.state = 0

  def update(self,input:Input):
    c = self.rect.collidepoint(input.mpos)
    if c:
      if self.state == 0:
        self.state = 1
      if input.mb1d:
        self.state = 2
        if self.onDown is not None:
          self.onDown()
        input.mb1d = False
    else:
      if self.state == 1:
        self.state = 0
  
    if self.state == 2:
      if input.mb1u:
        self.state = 1 if c else 0
        if self.onUp is not None:
          self.onUp() 
        input.mb1u = False

  #@Tracer().traceas('Button.draw')
  def draw(self,surf:Surface):
    draw.rect(surf,self.colors[self.state],self.rect)
