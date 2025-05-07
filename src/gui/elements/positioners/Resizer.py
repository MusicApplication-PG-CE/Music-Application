from ...core import *
from ...core_elements import *
class ToPixelsError(Exception): ...

class Resizer:
  @classmethod
  def fill(cls,obj:types.HasRect|types.HasFullRect):
    return cls(obj,'0','0','100%','100%')
  
  @staticmethod
  def toPixels(s:str,l:int) -> float:
    try:
      if not s: return 0
      f_open = s.find('(')
      f_close = s.find(')')
      if f_open < f_close:
        counter = 1
        open = f_open
        i = f_open+1
        while counter:
          f_open = s.find('(',i)
          f_close = s.find(')',i)
          if f_close == -1: raise SyntaxError('All Parenthesis must have valid pairs')
          if f_open < f_close and f_open != -1:
            counter += 1
            i = f_open+1
          else:
            counter -= 1
            i = f_close+1
            if counter == 0:
              break
        prev = s[:open]
        expresion = s[open+1:f_close]
        after = s[f_close+1:]
        return Resizer.toPixels(prev+str(Resizer.toPixels(expresion,l))+after,l)
      
      if 'max' in s:
        toMin = s.split('max')
        return max(Resizer.toPixels(s,l) for s in toMin)
      if 'min' in s:
        toMin = s.split('min')
        return min(Resizer.toPixels(s,l) for s in toMin)
      if '+' in s:
        toSum = s.split('+')
        return sum(Resizer.toPixels(s,l) for s in toSum)
      if '-' in s:
        s1,s2 = s.rsplit('-',1) 
        return (Resizer.toPixels(s1,l) - Resizer.toPixels(s2,l)) % l
      if '*' in s:
        s1,s2 = s.split('*',1)
        return min(max(0,Resizer.toPixels(s1,l) * Resizer.toPixels(s2,l)),l)
      if s.isdigit():
        # if l == 0:
        #   raise ToPixelsError(f'toPixels Error: {repr(s)} {repr(l)}')
        return int(s)
      elif s[-1] == '%':
        return int(float(s[:-1])* 0.01 * l)
      try:
        return float(s)
      except:

        raise ToPixelsError(f"Incorrect Format: {s}")
    except ToPixelsError:
      raise ToPixelsError(f'toPixels Error: {repr(s)} {repr(l)}')

  def __init__(self,obj:types.HasRect|types.HasFullRect,left:str,top:str,right:str,bottom:str):
    self.obj = obj
    self.left = left
    self.top = top
    self.right = right
    self.bottom = bottom
    self.order_in_layer = obj.order_in_layer
    if hasattr(obj,'update'):
      self.update = obj.update#type: ignore


  @property
  def rect(self):
    return self.obj.rect
  @rect.setter
  def rect(self,rect):
    self.obj.rect = rect #type: ignore

  def onResize(self,size:tuple[int,int]):    
    obj = self.obj
    l = self.toPixels(self.left.replace('h',str(size[1])).replace('w',str(size[0])),size[0])
    t = self.toPixels(self.top.replace('h',str(size[1])).replace('w',str(size[0])),size[1])
    w = max(self.toPixels(self.right.replace('~',str(l)).replace('h',str(size[1])).replace('w',str(size[0])),size[0]) - l,0) 
    h = max(self.toPixels(self.bottom.replace('~',str(t)).replace('h',str(size[1])).replace('w',str(size[0])),size[1]) - t,0)
    if isinstance(self.obj,Space):
      newSpace = Space(Rect(l,t,w,h))
      self.update = newSpace.update #the update method that is cached must be redirected to point to the new object
      self.obj.resized(newSpace)
      self.obj = newSpace
      return 
    obj.rect.left = l
    obj.rect.top = t
    obj.rect.width = w
    obj.rect.height = h
    if hasattr(obj,'onResize'): obj.onResize(size) #type: ignore

  def draw(self,surf:Surface):
    self.obj.draw(surf)
