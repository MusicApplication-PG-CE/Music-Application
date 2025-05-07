from ...core import *
from ...core.types import SupportsUpdate,SupportsDraw,SupportsResize

class Region(DrawBase):
  def __init__(self,rect:Rect):
    self.rect = rect
    self.active = True
    self.to_update:list[SupportsUpdate] = []
    self.to_draw:list[SupportsDraw] = []
    self.to_resize:list[SupportsResize] = []

  def setActive(self,active:bool=True):
    self.active = active
  def setInactive(self):
    self.setActive(False)

  def addObject(self,element:SupportsDraw|SupportsUpdate):
    if hasattr(element,'update'):
      self.to_update.append(element) #type: ignore
    if hasattr(element,'draw'):
      self.to_draw.append(element) #type: ignore
      self.to_draw.sort(key=lambda x:x.order_in_layer)
    if hasattr(element,'onResize'):
      self.to_resize.append(element) #type: ignore
  
  def addObjects(self,*elements:SupportsDraw|SupportsUpdate) -> "Region":
    for element in elements:
      self.addObject(element)
    return self
  
  def update(self,input:Input):
    if not self.active: return
    x = self.rect.left
    y = self.rect.top
    input.mousex -= x
    input.mousey -= y    
    for u in self.to_update:
      u.update(input)
    input.mousex += x
    input.mousey += y
    
  def onResize(self,size:tuple[int,int]):
    for ui in self.to_resize:
        ui.onResize(self.rect.size)

  def draw(self,surf:Surface):
    if not self.active: return
    srect = surf.get_rect()
    if srect.colliderect(self.rect):
      sub = surf.subsurface(self.rect.clip(srect))
      for ui in self.to_draw:
        ui.draw(sub)
