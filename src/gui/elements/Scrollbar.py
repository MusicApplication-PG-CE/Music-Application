from ..core import *


class Scrollbar(DrawBase):
  def __init__(self,pos:tuple[int,int],size:tuple[int,int],scrollbar_size:int,color_layout:ColorLayout) -> None:
    self.pos = pos
    self.scroll_size = scrollbar_size
    self.usable_size = size[1]-scrollbar_size
    self.rect = Rect(pos,size)
    self.color_layout = color_layout

    self.mouse_down_offset = 0
    self.x = 0
    self._drag_rect = Rect(self.pos[0],self.pos[1],size[0],scrollbar_size)

    self.state:types.Literal["Dragging",'Hover Scroll','Hover','Off'] = 'Off'
    self.linked_dropdown:types.Optional[types.SelectionLike] = None
    self.hiding = False


  def onResize(self,size:tuple[int,int]):
    if self.linked_dropdown:
      self.adjustSize()

  def linkToDropdown(self,dropdown:types.SelectionLike, auto_adjust = True):
    self.linked_dropdown = dropdown
    if auto_adjust:
      dropdown.size_change_event.register(self.adjustSize)
      self.adjustSize()
    return self
  
  def adjustSize(self):
    assert self.linked_dropdown
    try:
     x = self.linked_dropdown.max_y/self.linked_dropdown.fullHeight 
    except ZeroDivisionError:
      x = float('inf')

    if x >=1:
      self.hiding = True
    else:
      self.hiding = False

      self.rect.left = self.linked_dropdown.rect.right
      self.rect.height = self.linked_dropdown.max_y
      self.scroll_size =(x * self.rect.height).__trunc__()
      self.usable_size = self.rect.height-self.scroll_size
      self._drag_rect.left = self.rect.left
      self._drag_rect.height = self.scroll_size 

  def update(self,input:Input):
    if self.hiding: return
    mpos,mb1d,mb1u = input.mpos,input.mb1d,input.mb1u
    if self.rect.collidepoint(mpos) and self.state != 'Dragging':
      self.state = 'Hover Scroll' if self._drag_rect.collidepoint(mpos) else 'Hover'
      if mb1d and self.state =='Hover Scroll':
        self.mouse_down_offset = mpos[1] - self._drag_rect.top
        self.state = 'Dragging'
    if mb1u and self.state == 'Dragging':
      self.state = 'Off'

    if self.state == 'Dragging':
      self._drag_rect.top = mpos[1] - self.mouse_down_offset
      if self._drag_rect.top < self.rect.top: self._drag_rect.top = self.rect.top
      if self._drag_rect.bottom > self.rect.bottom: self._drag_rect.bottom = self.rect.bottom
      self.x = self._drag_rect.top - self.rect.top 
      if self.linked_dropdown:
        self.linked_dropdown.setScrollPercent(self.getValue())
    else:
      if not self.rect.collidepoint(mpos):
        self.state = 'Off'
      if self.linked_dropdown:
        self.setValue(self.linked_dropdown.getScrollPercent())

  def getValue(self):
    return min(self.x / self.usable_size,1)

  def setValue(self,value:float):
    self.x = value * self.usable_size
    self._drag_rect.top = self.rect.top + self.x
        
  def draw(self,surf:Surface):
    if self.hiding: return
    draw.rect(surf,self.color_layout.background,self.rect)
    draw.rect(surf,self.color_layout.foreground,self._drag_rect)

