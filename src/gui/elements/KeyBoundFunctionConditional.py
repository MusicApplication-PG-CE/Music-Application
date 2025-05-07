from ..core import *
from .KeyBoundFunction import KeyBoundFunction

class KeyBoundFunctionConditional(KeyBoundFunction):
  __slots__ = 'condition',
  def __init__(self,condition:types.EventHook, func:types.EventHook,keybinds:list[tuple[int,int]],consume = True):
    super().__init__(func,keybinds,consume)
    self.condition = condition
  
  def update(self, input):
    if self.condition():
      super().update(input)
