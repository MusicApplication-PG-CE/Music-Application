from ..core import *
from .Slider import Slider

class AutoSlider(Slider):
  def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_layout: ColorLayout):
    super().__init__(pos, size, color_layout, lambda x: None)
    self.bar_width = self.rect.height
  def update(self,input:Input): pass

  def draw(self,surf:Surface):
      draw.rect(surf,self.color.background,(self.rect.left,self.rect.top+(self.rect.height-self.bar_width)//2,self.rect.width,self.bar_width),0,2)
      draw.rect(surf,self.color.foreground,self.passed_rect,0,2)
