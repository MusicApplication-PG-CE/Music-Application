from ..core import *
from pygame import font

class BoxText(DrawBase):
  __slots__ = 'rect','color','f','alignment_x','alignment_y','text','surf','font_rule','offset_x','offset_y'
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],text:str,color:types.ColorType,f:font.Font,alignment_x:float = 0.5,alignment_y:float = 0.5,offset:tuple[int,int]=(0,0)):
    self.rect = Rect(pos,size)
    self.color = color
    self.f = f
    self.alignment_x = alignment_x
    self.alignment_y = alignment_y
    self.offset_x,self.offset_y = offset
    self.text = text 
    self.surf = self.f.render(text,True,color)    
    self.font_rule:types.Callable[[font.Font,str,Rect],None]|None = None
    

  def setFontRule(self,rule:types.Callable[[font.Font,str,Rect],None]):
    self.font_rule = rule
    self.onResize((0,0))
    return self

  def onResize(self,size:tuple[int,int]):
    if self.font_rule is not None:
      self.setText(self.text,True)
    
  def setText(self,text,force:bool = False):
    if self.text == text and not force: return
    self.text = text
    if self.font_rule is not None:
      self.font_rule(self.f,text,self.rect)
    self.surf = self.f.render(text,True,self.color)

  def update(self,input:Input): ...

  def draw(self,surf:Surface):
    left = (self.rect.width - self.surf.get_width()) * self.alignment_x + self.rect.left + self.offset_x
    top = (self.rect.height - self.surf.get_height()) * self.alignment_y  + self.rect.top + self.offset_y
    surf.blit(self.surf,(left,top))
