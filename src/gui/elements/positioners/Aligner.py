from ...core import *

class Aligner:
  def __init__(self,obj:types.HasFullRect|types.HasRect,anchor_x:float,anchor_y:float,alignment_x:float|None = None,alignment_y:float|None = None):
    self.obj = obj
    self.order_in_layer = obj.order_in_layer
    self.anchor = anchor_x,anchor_y
    self.alignment = anchor_x if alignment_x is None else alignment_x,anchor_y if alignment_y is None else alignment_y
    self.offset = self.obj.rect.topleft
    self.last_size:types.Optional[tuple[int,int]] = None
    self.is_resizing = False
    if hasattr(obj,'update'):
      self.update = obj.update #type: ignore
    if hasattr(obj,'on_rect_change_event'):
      obj.on_rect_change_event.register( #type: ignore
        lambda : self.onResize(self.last_size) if (self.last_size is not None) and (not self.is_resizing) else None
      )

  @property
  def rect(self):
    return self.obj.rect
  
  @rect.setter
  def rect(self,rect:Rect):
    self.obj.rect = rect #type: ignore

  def onResize(self,size:tuple[int,int]):
    self.is_resizing = True
    self.last_size = size
    r = self.obj.rect
    r.left = size[0] * self.anchor[0] - r.width * self.alignment[0] + self.offset[0]
    r.top = size[1] * self.anchor[1] - r.height * self.alignment[1] + self.offset[1]
    p_r_size = r.size
    if hasattr(self.obj,'onResize'): self.obj.onResize(size) #type: ignore
    if r.size != p_r_size:
      self.onResize(size) 
    self.is_resizing = False

  def draw(self,surf:Surface):
    self.obj.draw(surf)