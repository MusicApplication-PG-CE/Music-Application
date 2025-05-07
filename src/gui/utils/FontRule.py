from pygame import font,Rect
from .utils import binaryApproximate

class FontRule:
  def __init__(self,min:int=5,max:int=30):
    self.min = min
    self.max = max

  def __call__(self,f:font.Font,text:str,r:Rect):
    f.set_point_size(min(self.max,max(self.min,r.height-4)))
    s = f.size(text)
    if s[0] > r.width:
      def search(i:int):
        f.set_point_size(i)
        return f.size(text)[0]
      binaryApproximate(search,r.width,self.min,f.get_point_size())
