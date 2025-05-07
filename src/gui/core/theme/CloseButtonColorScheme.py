from ...core import types
from ...core.theme.ColorScheme import ColorScheme
from ...utils import color
class CloseButtonColorScheme(ColorScheme):
  def __init__(self,exit_color:types.ColorType,background_color:types.ColorType) -> None:
    super().__init__(*exit_color)
    self.bg_color = background_color
    
  def getActive(self):
    return color.darken(self.r,self.g,self.b,100)

  def getInactive(self):
    return self.bg_color
  
  def withBGColor(self,bg_color:types.ColorType):
    return CloseButtonColorScheme(self.color,bg_color)
