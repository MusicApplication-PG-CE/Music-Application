from ..core import *
from .Space import Space

class Layer(DrawBase):
  __slots__ = 'rect','next_layer','space'
  def __init__(self,size:tuple[int,int]):
    self.rect = Rect(0,0,size[0],size[1])
    self.next_layer: Layer|None = None
    self.space = Space(self.rect.copy())

  def inline(self,*objects:types.SupportsDraw|types.SupportsUpdate|None):
    self.space.addObjects(*objects)
    return self
  

  def onResize(self,size:tuple[int,int]):
    new = Space(self.rect.copy())
    self.space.resized(new)
    self.space = new
    if self.next_layer:
      self.next_layer.resize(size)

  def removeCut(self,dir:types.Literal['left','top','bottom','right'],i:int=-1):
    direction = {
      'top':0,
      'bottom':1,
      'left':2,
      'right':3
    }[dir]
    if i != -1:
      x = 0
      for i_,(split_dir,size) in enumerate(self.space.splits):
        if split_dir == direction:
          if i == x:
            i = i_
            break
          x+=1
    else:
      for i_ in range(len(self.space.splits)-1,-1,-1):
        if self.space.splits[i][0] == direction:
          i = i_
          break
    if i < 0:
      raise ValueError(f"Invalid Index: {i}")
    self.space.splits.pop(i)
    self.space.sub_spaces.pop(i)
    self.onResize(self.rect.size)
    return 
    
  def insertCut(self,i:int,dir:types.Literal['left','top','bottom','right'],size:int):
    direction = {
      'top':0,
      'bottom':1,
      'left':2,
      'right':3
    }[dir]
    if i < 0:
      raise ValueError(f"Invalid Cut Index: {i}")
    new = Space(self.rect.copy())
    self.space.splits.insert(i,(direction,size))
    self.space.sub_spaces.insert(i,new)
    self.onResize(self.rect.size)
    return new


  def resize(self,newSize:tuple[int,int]):
    self.rect.size = newSize
    new = Space(self.rect.copy())
    self.space.resized(new)
    self.space = new
    if self.next_layer:
      self.next_layer.resize(newSize)

  def resetEverything(self,newSize:tuple[int,int]|None=None):
    if newSize is not None:
      self.rect.size = newSize
    if self.next_layer:
      self.removeLayer(self.next_layer,True)
    self.space = Space(self.rect.copy())

  def update(self,input:Input):
    if self.next_layer:
      self.next_layer.update(input)
    self.space.update(input)

  def draw(self,surf:Surface):
    self.space.draw(surf)
    if self.next_layer:
      self.next_layer.draw(surf)

  def addLayer(self,layer:types.Optional["Layer"] = None) -> "Layer":
    if self.next_layer:
      return self.next_layer.addLayer(layer)
    self.next_layer = layer or Layer(self.rect.size)
    return self.next_layer
  
  def removeLayer(self,layer:"Layer",and_all_after:bool = False) -> bool:
    if self.next_layer is not layer:
      if self.next_layer:
        return self.next_layer.removeLayer(layer,and_all_after)
      else:
        return False
    else:
      if and_all_after:
        self.next_layer = None
      else:
        self.next_layer = layer.next_layer
      return True

  def withTemp(self,object):
    class Temp:
      def __enter__(self2):
        self.space.addObject(object)
        return self
      def __exit__(self2,exc_type, exc_val, exc_tb):
        self.space.removeObject(object)
    return Temp()