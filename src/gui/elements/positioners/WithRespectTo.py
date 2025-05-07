from ...core import *

class WithRespectTo:
  def __init__(self,obj:types.HasRect,anchor:types.HasRect,anchor_x:float,anchor_y:float,alignment_x:float = 0.5,alignment_y:float = 0.5):
    self.order_in_layer = obj.order_in_layer
    self.obj = obj
    self.anchor_rect = anchor.rect
    self.anchor = anchor_x,anchor_y
    self.alignment = alignment_x,alignment_y
    self.offset = obj.rect.topleft
    if hasattr(obj,'update'):
      self.update = self.obj.update #type: ignore

  def onResize(self,newSize:tuple[int,int]):
      if hasattr(self.obj,'onResize'): self.obj.onResize(newSize) #type: ignore
      r = self.obj.rect
      anchor = self.anchor_rect
      ax,ay = self.anchor
      r.left = anchor.left * (1-ax) + anchor.right * ax - r.width * self.alignment[0] + self.offset[0]
      r.top =  anchor.top * (1-ay) + anchor.bottom * ay - r.height * self.alignment[1] + self.offset[1]


  def draw(self,surf:Surface):
    self.obj.draw(surf)
