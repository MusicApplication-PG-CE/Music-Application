from ..core import *

class Image(DrawBase): 
  def __init__(self,pos:tuple[int,int],image:Surface):
    self.rect = Rect(pos,image.get_size())
    self.image = image

  def draw(self,surf:Surface):
    surf.blit(self.image,self.rect)  

