import time
from ..core import *
from pygame import font


class InputBox(DrawBase):
  def __init__(self,pos,size,color_layout:ColorLayout,caption = '',save_function:types.Callable|None =None,restrict_input = None):
    self.pos = pos
    self.font = font.SysFont('Courier New', 21)
    self.active = False
    self.caption = caption
    self.box_color = color_layout.background
    self.text_color = color_layout.foreground
    self.max_chars = 500
    self.text = ''
    self.textsurface = self.font.render(self.text, True, (0, 0, 0))
    self.rect = Rect(self.pos, size)
    self.max_chars_per_line = size[0]//12
    self.save_function = save_function if save_function else lambda x : x
    self.restrict_input = restrict_input
    self.timeactive = 0.0
    self.cursor_rect = Rect(0,0,2,18)
    self.surf = Surface(size,const.SRCALPHA)

  def resize(self,newSize:tuple[int,int]):
    self.rect.size = newSize
    self.max_chars_per_line = newSize[0]//12
    self.surf = Surface(newSize,const.SRCALPHA)
    self.redrawSurf()

  def setMaxChars(self,max:int):
    self.max_chars = max
    if len(self.text) > max: self.text = self.text[:max]
    return self

  def setText(self,new_text):
    self.text = new_text
    self.redrawSurf()

  def _checkKey(self,key:str,input:Input,save:bool = False):
    if self.restrict_input and key not in self.restrict_input and key != u_const.BACK: return False
    if key == u_const.BACK:
      if len(self.text):    
        if input.lctrl:
          self.text = '' if ' ' not in self.text else ' '.join(self.text.split()[:-1])
        else:
          self.text = self.text[:-1]
      else:
        return False
    elif len(self.text) < self.max_chars:
      if key == '\r':
        key = '\n'
      self.text +=key
    if self.save_function and save:
      self.save_function(self.text)
    return True

  def update(self,input:Input):
    'mpos,mb1down,keys'
    mpos = input.mpos
    mb1down = input.mb1d
    if self.rect.collidepoint(mpos) and mb1down:
      self.active = True
      self.cursor_rect.topleft = (self.rect.left + (len(self.text)%self.max_chars_per_line)*12+2,self.rect.top+(len(self.text)//self.max_chars_per_line)*self.font.get_height()+2)
      self.timeactive = time.monotonic()
    elif mb1down:
      self.active = False
    t = self.text
    if self.active:
      to_process = input.KDQueue
      input.KDQueue = []
      for key in to_process:
        if key.key == const.K_LEFT: #type: ignore
          self.cursor_position = max(0,self.cursor_position-1)
          self.redrawSurf()
          self.cursor_time = time.monotonic() - 0.5
        elif key.key == const.K_RIGHT:
          self.cursor_position = min(len(self.text),self.cursor_position+1)
          self.redrawSurf()
          self.cursor_time = time.monotonic() - 0.5
        else:
          if not self._checkKey(key.unicode,input): #type: ignore
            input.KDQueue.append(key)
    if t != self.text: #if text has been updated
      self.timeactive = time.monotonic()-.5
      self.cursor_rect.topleft = (self.rect.left + (len(self.text)%self.max_chars_per_line)*12+2,self.rect.top+(len(self.text)//self.max_chars_per_line)*self.font.get_height()+2)
      self.redrawSurf()

  def redrawSurf(self):
    self.surf.fill((0,0,0,0))
    letters = [letter for letter in self.text]
    for char_num, letter in enumerate(letters):
      txt = self.font.render(letter, True, self.text_color)
      letterx = (char_num%self.max_chars_per_line)*12
      self.surf.blit(txt,(letterx,(char_num//self.max_chars_per_line)*self.font.get_height()))

  def draw(self,surf:Surface): 
    if self.box_color:
      draw.rect(surf,self.box_color,self.rect)
    if not self.text:
      self.textsurface = self.font.render(self.caption, True, self.text_color)
      surf.blit(self.textsurface,self.pos)
    else:
      surf.blit(self.surf,self.rect)
    if self.active and not int(time.monotonic()-self.timeactive) % 2:
      draw.rect(surf,(0,0,0),self.cursor_rect)
