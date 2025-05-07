from ...core import *
from . import Aligner

class SAligner(Aligner):
  def __init__(self, obj: 'Space', anchor_x: float, anchor_y: float, alignment_x: float = 0.5, alignment_y: float = 0.5):
    super().__init__(obj, anchor_x, anchor_y, alignment_x, alignment_y)
    self.offset = (0,0)

  def onResize(self, size: tuple[int, int]):
    self.last_size = size
    self.obj:Space
    s = self.obj
    nr = self.obj.rect.copy()
    nr.left = size[0] * self.anchor[0] - nr.width * self.alignment[0] + self.offset[0]
    nr.top = size[1] * self.anchor[1] - nr.height * self.alignment[1] + self.offset[1]
    rel = nr.left - s.rect.left,nr.top - s.rect.top
    s.rect.left = nr.left
    s.rect.top = nr.top
    def move_all_subs(s:Space):
      for sub_s in s.sub_spaces:
        sub_s.rect.move_ip(rel)
        s.surface = None
        move_all_subs(sub_s)
    s.surface = None
    move_all_subs(s)
    if hasattr(self.obj,'onResize'): self.obj.onResize(size) #type: ignore
