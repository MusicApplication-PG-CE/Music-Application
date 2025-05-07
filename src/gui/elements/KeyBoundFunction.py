from ..core import *

class KeyBoundFunction:
  __slots__ = 'func','keybinds','consume'
  def __init__(self,func:types.EventHook,keybinds:list[tuple[int,int]],consume=True):
    self.func = func
    self.keybinds = keybinds
    self.consume = consume

  def update(self,input:Input) -> None:
    if self.consume:
      if input.consumeKeys(*self.keybinds):
        self.func()
    else:
      if input.checkKeys(*self.keybinds):
        self.func()