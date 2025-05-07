import time
from ..core import *
from pygame import font
from pygame import scrap
from ..utils import utils
from ..utils import unicode_constants as u_const

class InputBoxOneLine(DrawBase):
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_layout:ColorLayout,callback:types.Callable[[str],None]|None,font:font.Font):
    self.rect = Rect(pos,size)
    self.color_layout = color_layout
    self.callback = callback
    self.max_chars = 999
    self.font = font
    self.surf = Surface(self.rect.size,const.SRCALPHA)
    self.surf.fill(self.color_layout.background)
    self.placeholder = ''
    self.text = ''
    self.text_surf = Surface((0,0))
    self.cursor_position = 0
    self.cursor_height = self.font.get_height()
    self.cursor_visible_x = 0
    self.text_surf_left_shift = 0
    self.valid_keys = u_const.REGULAR
    self.text_y_alignment = 0.5
    self.active = False
    self.cursor_time = 0.0

  def onResize(self,newSize:tuple[int,int]):
    self.surf = Surface(self.rect.size,const.SRCALPHA)
    self.redrawSurf()

  def setPlaceholder(self,placeholder:str):
    self.placeholder = placeholder
    return self

  def setRestrictInput(self,validKeys:set[str]|None):
    self.valid_keys = validKeys

  def setRestrictInputChain(self,validKeys:set[str]|None):
    self.valid_keys = validKeys
    return self
  
  def setMaxChars(self,max:int):
    self.max_chars = max
    return self
  
  def setText(self,text:str):
    self.text = text
    if self.callback:
      self.callback(text)
    self.redrawSurf()
    return self
  
  def getXPosOfCursorPosition(self,c_position:int):
    return self.font.size(self.text[:c_position])[0] - self.text_surf_left_shift
  
  def resize(self,newSize:tuple[int,int]):
    self.rect.size = newSize
    self.onResize((0,0))

  def setActive(self,active=True):
    self.active = active
    if active:
      self.cursor_time = time.monotonic()
      self.cursor_position = len(self.text)
      self.cursor_visible_x = self.font.size(self.text[:self.cursor_position])[0]

  def setInactive(self):
    self.setActive(active=False)

  def getActive(self):
    return self.active

  def update(self,input:Input):
    mhover = self.rect.collidepoint(input.mpos)
    if input.mb1d:
      self.active = mhover
      if mhover:
        self.cursor_time = time.monotonic()
        self.cursor_position = utils.binaryApproximate(self.getXPosOfCursorPosition,input.mousex-self.rect.left,0,len(self.text))
        self.cursor_visible_x = self.font.size(self.text[:self.cursor_position])[0]
    if self.active:
      to_process = input.KDQueue
      input.KDQueue = []
      t = self.text
      for i,key in enumerate(to_process):
        if key.key == const.K_ESCAPE:
          self.active = False
          input.KDQueue.extend(to_process[i+1:])
          break
        elif key.key==const.K_v and key.mod&const.KMOD_CTRL:
          text = scrap.get_text()
          for char in text:
            self.typeKey(char,input.lctrl,False)
        elif key.key == const.K_LEFT:
          self.cursor_position = max(0,self.cursor_position-1)
          self.redrawSurf()
          self.cursor_time = time.monotonic() - 0.5
        elif key.key == const.K_RIGHT:
          self.cursor_position = min(len(self.text),self.cursor_position+1)
          self.redrawSurf()
          self.cursor_time = time.monotonic() - 0.5
        else:
          if not self.typeKey(key.unicode,input.lctrl,False):
            input.KDQueue.append(key)
      
      # input.KDQueue = list(filter(lambda c: not self.typeKey(c,input.lctrl,False),input.KDQueue))
      if t is not self.text:
        self.cursor_time = time.monotonic() - 0.5
        self.redrawSurf()
        if self.callback:
          self.callback(self.text)

  def backspace(self):
    if not self.text[:self.cursor_position]: return
    self.text = self.text[:self.cursor_position-1] + self.text[self.cursor_position:]
    self.cursor_position -= 1
    if self.cursor_position < 0: self.cursor_position = 0
  
  def currChar(self):
    if not self.cursor_position or self.cursor_position > len(self.text): return ''
    return self.text[self.cursor_position-1]

  def typeKey(self,key:str,lctrl:bool = False,use_callback:bool = True):
    '''Returns whether key has been consumed or not'''
    if not key: return True
    if key == u_const.BACK:
      if lctrl:
        if self.currChar() == ' ': 
          while self.currChar()==' ':self.backspace()
        while self.currChar() not in {'',' '}:
          self.backspace()
      else:
        self.backspace()
      return True
    elif key == u_const.DELETE:
      if lctrl:
        if self.cursor_position+1 < len(self.text) and self.text[self.cursor_position] == ' ':
          pos = self.cursor_position + 1
          while pos < len(self.text) and self.text[pos] == ' ': 
            pos += 1
          pos_to_delete_to = pos
        else:
          pos_to_delete_to = self.text.find(' ',self.cursor_position)
        self.text = self.text[:self.cursor_position] + (self.text[pos_to_delete_to:] if pos_to_delete_to != -1 else '')
      else:
        self.text = self.text[:self.cursor_position] + self.text[self.cursor_position+1:]
          
    if self.valid_keys is not None and key not in self.valid_keys: return False
    if len(self.text) < self.max_chars:
      if key == u_const.ENTER:
        key = '\n'
      self.text = self.text[:self.cursor_position] + key + self.text[self.cursor_position:] 
      self.cursor_position += 1
    if self.callback and use_callback:
      self.callback(self.text)
    return True

  def redrawSurf(self):
    self.surf.fill(self.color_layout.background)
    if self.text:
      self.text_surf = self.font.render(self.text,True,self.color_layout.foreground)
    else:
      self.text_surf = self.font.render(self.placeholder,True,self.color_layout.tertiary)
    if self.font.size(self.text)[0] < self.rect.width:
      self.text_surf_left_shift = 0
    self.cursor_visible_x = self.font.size(self.text[:self.cursor_position])[0]
    cursor_x_pos = self.cursor_visible_x - self.text_surf_left_shift
    if cursor_x_pos > self.rect.width-3:
      self.text_surf_left_shift += cursor_x_pos - self.rect.width + 3
    elif cursor_x_pos < 0:
      self.text_surf_left_shift += cursor_x_pos  
    self.surf.blit(self.text_surf,(-self.text_surf_left_shift,(self.rect.height - self.font.get_height())*self.text_y_alignment))

  def draw(self,surf:Surface):
    surf.blit(self.surf,self.rect)
    if not self.active: return
    t = int(time.monotonic() - self.cursor_time)
    if not t%2:
      draw.rect(surf,self.color_layout.foreground,(self.cursor_visible_x - self.text_surf_left_shift+self.rect.left,self.rect.top +(self.rect.height - self.font.get_height())*self.text_y_alignment,2,self.font.get_height()))

