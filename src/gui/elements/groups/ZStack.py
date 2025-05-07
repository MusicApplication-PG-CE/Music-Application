from ...core import *

class ZStack(DrawBase):
  def __init__(self,*contents:types.HasFullRect|types.SupportsUpdate):
    self.contents = contents
    self.to_update:list[types.SupportsUpdate] = list(filter(lambda x: hasattr(x,'update'),contents)) #type: ignore
    self.to_resize:list[types.SupportsResize] = list(filter(lambda x: hasattr(x,'onResize'),contents)) #type: ignore
    self.to_draw:list[types.SupportsDraw] = list(filter(lambda x: hasattr(x,'draw'),contents)) #type: ignore
    self.rect = self.to_draw[0].rect #type: ignore
    
  def onResize(self,size:tuple[int,int]):
    for c in self.to_resize:
      c.onResize(size)

  @property
  def rect(self):
    return self._rect
  
  @rect.setter
  def rect(self,rect:Rect):
    self._rect = rect
    for c in self.contents:
      c.rect = rect #type: ignore

  def update(self,input:Input):
    for u in self.to_update:
      u.update(input)

  def draw(self,surf:Surface):
    for c in self.to_draw:
      c.draw(surf)