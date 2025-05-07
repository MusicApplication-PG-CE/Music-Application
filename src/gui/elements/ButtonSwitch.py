from ..core import *

class ButtonSwitch(DrawBase):
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],states:list[Surface],state:int = 0,onDown:types.EventHookInt|None = None):
    self.rect = Rect(pos,size)
    self.states = states
    self.state = state
    self.onDown = onDown
    self.rect_color:types.Optional[types.ColorType] = None

  def update(self,input:Input):
    if input.mb1d and self.rect.collidepoint(input.mpos):
      self.state = (self.state + 1) % len(self.states)
      if self.onDown:
        self.onDown(self.state)

  def draw(self,surf:Surface):
    s = self.states[self.state]
    r = s.get_rect()
    if self.rect_color is not None:
      draw.rect(surf,self.rect_color,self.rect)
    r.center = self.rect.center
    surf.blit(s,r)
