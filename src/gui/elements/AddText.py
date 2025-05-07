from ..core import *
from pygame import font

class AddText(DrawBase):
  __slots__ = 'color','f','obj','anchor_x','anchor_y','alignment_x','alignment_y','offset_x','offset_y','update','_s','onResize','rect','txt','clip'
  def __init__(self,obj:types.HasRect,text:str,color:types.ColorType,f:font.Font,anchor_x:float = 0.5,anchor_y:float = 0.5,
                                                                     alignment_x:float = 0.5,alignment_y:float = 0.5,
                                                                     offset_x:int = 0,offset_y:int = 0):
    self.color = color
    self.f = f
    self.obj = obj
    self.anchor_x = anchor_x
    self.anchor_y = anchor_y
    self.alignment_x = alignment_x
    self.alignment_y = alignment_y
    self.offset_x = offset_x
    self.offset_y = offset_y
    self.rect = obj.rect
    self.setText(text)
    self.txt = ''
    self.clip = False

    if hasattr(obj,'update'):
      self.update = obj.update #type: ignore
    if hasattr(obj,'onResize'):
      self.onResize = obj.onResize#type: ignore

  def setText(self,text:str):
    self.txt = text
    self._s = self.f.render(text,True,self.color)
  
  def setClip(self,clip:bool):
    self.clip = True
    return self

  def draw(self,surf:Surface):
    self.obj.draw(surf)
    if self.clip:
      p_clip = surf.get_clip()
      surf.set_clip(self.rect)
    surf.blit(self._s,
      (self.rect.left+self.rect.width*self.anchor_x-self._s.get_width()*self.alignment_x + self.offset_x,
       self.rect.top+self.rect.height*self.anchor_y-self._s.get_height()*self.alignment_y + self.offset_y)
    )
    if self.clip:
      surf.set_clip(p_clip)
