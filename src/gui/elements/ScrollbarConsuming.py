from ..core import *
from .Scrollbar import Scrollbar

class ScrollbarConsuming(Scrollbar):
  def update(self,input:Input):
    super().update(input)
    if self.state == 'Hover Scroll' or self.state == 'Dragging':
      input.mousex = -999
      input.mousey = -999
