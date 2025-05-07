from ..core import *
from .Slider import Slider
from ..utils.utils import binaryApproximate

class SquareSlider(Slider):
  def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_layout: ColorLayout,range:types.Iterable,save_function: types.Callable[[int], None],initial_value:int|None = None,strict_iv = True):
    self.values = list(range)
    super().__init__(pos,size,color_layout,self.save_wrapper)
    self.bar_width = size[1]
    self.save = save_function
    self.last_value = None
    self.slider_rect = Rect(0,pos[1],5,size[1])
    if initial_value is not None:
      self.setValue(initial_value,strict_iv)

  def save_wrapper(self,value:float) -> None:
    value = self.sliderx / (self.rect.width + 1)
    index = int(value * len(self.values))
    v = self.values[index]
    if v != self.last_value:
      self.last_value = v
      self.save(v)
    
  def draw(self,surf:Surface):
    self.slider_rect.centery = self.rect.centery
    draw.rect(surf,self.color.background,self.rect,0,2)
    self.slider_rect.left  = self.rect.left + (self.rect.width - self.slider_rect.width) * self.value
    draw.rect(surf,self.color.foreground,self.slider_rect,0,2)

  def setValue(self,value:int,strict:bool=True): #type: ignore
    try:
      index = self.values.index(value)
    except ValueError:
      if not strict:
        i:int = binaryApproximate(lambda x:self.values[x],value,0,len(self.values)-1)
        super().setValue( i/ (len(self.values)-1))
      else: raise ValueError("Value not found in valid values")
    else:
      super().setValue(index / (len(self.values)-1))
