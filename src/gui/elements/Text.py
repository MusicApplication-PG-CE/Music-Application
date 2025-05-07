from ..core import *
from pygame import font

class Text(DrawBase):
  def __init__(self,pos:tuple[int,int],text:str,color:types.ColorType,font:font.Font):
    self.rect = Rect(pos,(0,0))
    self.font = font
    self.color = color
    self.on_rect_change_event:Event[[]] = Event()
    self.setText(text)
    self.showing = True

  def setFont(self,font:font.Font):
    self.font = font
    self.setText(self.__text)

  def getText(self):
    return self.__text

  def setTextIfNeeded(self,newText:str):
    if self.__text != newText:
      self.setText(newText)

  def setText(self,newText:str) -> None:
    self.__text = newText
    self.surf = self.font.render(self.__text,True,self.color)
    self.rect.width = self.surf.get_width()
    self.rect.height = self.surf.get_height()
    self.on_rect_change_event.fire()

  def clear(self): self.setText('')

  def show(self): 
    self.showing = True
    return self
  
  def setShowing(self,showing:bool):
    self.showing = showing
    
  
  def hide(self): 
    self.showing = False
    return self

  def draw(self,surf:Surface):
    if self.showing:
      surf.blit(self.surf,self.rect.topleft)
