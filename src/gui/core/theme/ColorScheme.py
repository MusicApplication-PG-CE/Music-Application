from .. import types
from ...utils import color

class ColorScheme:
  __slots__ = 'r','g','b','variance'
  def __init__(self,r:int,g:int,b:int,variance:int=20):
    self.r = r
    self.g = g
    self.b = b
    self.variance = variance
    
  def getActive(self): return self.getDark(self.variance)
  def getIdle(self): return self.getLight(self.variance)
  def getInactive(self): return self.color

  @property
  def color(self) -> types.ColorType:
    return self.r,self.g,self.b
  
  def copy(self):
    return ColorScheme(self.r,self.g,self.b,self.variance)

  def mix(self,other:"ColorScheme",weight:float = 0.5):
    return ColorScheme(int(self.r*(1-weight)+other.r * weight),
                       int(self.g*(1-weight)+other.g * weight),
                       int(self.b*(1-weight)+other.b * weight))
  def getDark(self,amount:int):
    return color.darken(self.r,self.g,self.b,amount)
  def getLight(self,amount:int):
    return color.lighten(self.r,self.g,self.b,amount)
  def getComplementary(self):
    return color.getComplementary(self.r,self.g,self.b)
