from ..core import *

class AddImage(DrawBase):
  def __init__(self,obj:types.HasRect,img:Surface,anchor_x:float = 0.5,anchor_y:float = 0.5,offset_x:int = 0,offset_y:int = 0):
    self.obj = obj
    self.img = img
    self.anchor_x = anchor_x
    self.anchor_y = anchor_y
    self.offset_x = offset_x
    self.offset_y = offset_y
    if hasattr(obj,'update'):
      self.update = obj.update#type: ignore
    if hasattr(obj,'onResize'):
      self.onResize = obj.onResize#type: ignore

  @property
  def rect(self):
    return self.obj.rect
  
  @rect.setter
  def rect(self,rect):
    self.obj.rect = rect #type: ignore
  def draw(self,surf:Surface):
    self.obj.draw(surf)
    surf.blit(self.img,
              (self.obj.rect.left+self.obj.rect.width*self.anchor_x-self.img.get_width()*self.anchor_x+self.offset_x,
               self.obj.rect.top+self.obj.rect.height*self.anchor_y-self.img.get_height()*self.anchor_y+self.offset_y)
              )
