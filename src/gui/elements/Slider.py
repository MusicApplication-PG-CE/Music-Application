from ..core import *


class Slider(DrawBase):
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_layout:ColorLayout,save_function:types.Callable[[float],None]):
    self.pos = pos
    self.size = size
    self.rect = Rect(pos,size)
    self.save_function = save_function
    self.color = color_layout
    self.sliderx = 0
    self.value = 0.0
    self.bar_width = 9
    self.active = False
    self.pactive = False
    self.mouse_active = False
 
  def onActivate(self): ...
  def onDeactivate(self): ...

  @property
  def passed_rect(self):
    return Rect(self.rect.left,self.rect.top+(self.rect.height-self.bar_width)//2,self.sliderx,self.bar_width)

  def setValue(self,x:float):
    '''Set a percentage in the range [0,1]'''
    if x < 0: x = 0
    elif x > 1: x = 1
    self.sliderx = self.rect.width*x
    self.value = x
    self.save_function(self.value)

  def update(self,input:Input):
    mpos,mb1down,mb1up = input.mpos,input.mb1d,input.mb1u
    if self.rect.collidepoint(mpos):
      self.mouse_active = True
      if mb1down:
        self.active = True
        self.onActivate()
        input.mb1d = False
    else:
      self.mouse_active = False
    if self.active and mb1up:
      self.active = False
      self.onDeactivate()
      input.mb1u = False

    if self.active:
      self.sliderx = min(max(mpos[0] - self.rect.left,0),self.rect.width)
      newVal = self.sliderx / self.rect.width
      if self.value != newVal:
        self.value = newVal
        self.save_function(self.value)

    self.pactive = self.active

  def draw(self,surf:Surface):
      draw.rect(surf,self.color.background,(self.rect.left,self.rect.top+(self.rect.height-self.bar_width)//2,self.rect.width,self.bar_width),0,2)
      # draw.rect(surf,self.passed_color,self.passed_rect,0,2)
      draw.circle(surf,self.color.foreground,(self.sliderx+self.rect.left,self.rect.midleft[1]),7)
