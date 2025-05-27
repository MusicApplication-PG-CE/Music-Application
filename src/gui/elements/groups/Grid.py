from ...core import *
from ... import settings
from ...utils import utils
from ..positioners import Resizer

class Grid(DrawBase):
    def __init__(self,rectlike:Rect|tuple,cells:tuple[int,int],cell_size:tuple[str|list[str],str|list[str]],cell_margin:tuple[str,str],contents:types.Optional[list[list[types.SupportsAll]]]=None) -> None:
        self.cells = list(cells)
        self.contents:list[list[types.SupportsAll]] = contents if contents else []
        self.rect = Rect(rectlike)
        self.scroll_x = 0
        self.scroll_y = 0 
        self.cell_margin = cell_margin
        self.cell_size = cell_size
        if type(self.cell_size[0]) is str:
            self.cell_size = [self.cell_size[0]],self.cell_size[1]
        if type(self.cell_size[1]) is str:
            self.cell_size = self.cell_size[0],[self.cell_size[1]]
        self.added = False
  
    def onResize(self,size:tuple[int,int]):
        cache:dict[tuple[str,int],int] = {}
        self.margin_x = int(Resizer.toPixels(self.cell_margin[0],self.rect.width))
        self.margin_y = int(Resizer.toPixels(self.cell_margin[1],self.rect.height))
        yshift = 0
        for y, row in enumerate(self.contents):
            xshift = 0
            h_args = self.cell_size[1][y%len(self.cell_size[1])].replace('~',str(100/(self.cells[1]))+'%').replace('`',str(2*self.margin_y)),self.rect.height
            cell_height = int(utils.useCache(Resizer.toPixels,h_args,cache))
            for x, element in enumerate(row):
                w_args = self.cell_size[0][x%len(self.cell_size[0])].replace('~',str(100/self.cells[0])+'%').replace('`',str(2*self.margin_x)),self.rect.width
                element.rect.width = int(utils.useCache(Resizer.toPixels,w_args,cache))
                element.rect.height = cell_height
                element.rect.left = xshift + self.margin_x
                element.rect.top = yshift + self.margin_y
                xshift += element.rect.width +  2*self.margin_x

                if hasattr(element,'onResize'):
                    element.onResize(self.rect.size) #type: ignore
            yshift += cell_height + 2*self.margin_y
  
    def clear(self):
        self.contents = []

    def addRow(self,row:types.Sequence[types.SupportsAll]):
        assert len(row) == self.cells[0]
        self.cells[1] += 1
        self.contents.append(list(row))
        if self.added:
            self.onResize((1,1)) #Recalculate Grid

    def popRow(self,i:int=-1):
        val = self.contents.pop(i)
        if self.added:
            self.onResize((1,1)) #Recalculate Grid
        return val
    
    @property
    def full_size(self):
        if not self.contents:
            return 0,0
        last = self.contents[-1][-1].rect
        return last.right + self.margin_x, last.bottom + self.margin_y

   

    def update(self,input:Input):
        l,t = self.rect.topleft
        sx = int(self.scroll_x)
        sy = int(self.scroll_y)
        input.mousex += sx - l
        input.mousey += sy - t
        for row in self.contents:
            for element in row:
                if element is not None:
                    element.update(input)
        input.mousex -= sx - l
        input.mousey -= sy - t
        wheel = input.wheel or input.touch_wheel
        input.wheel = 0
        input.touch_wheel = 0
        size = self.full_size
        max_scroll = max(size[0]-self.rect.width,0),max(size[1]-self.rect.height,0),
        if wheel and self.rect.collidepoint(input.mpos):
            if (size[0]> self.rect.width and size[1] <self.rect.height) or input.lctrl:
                #scroll horizonally
                self.scroll_x += wheel * settings.wheel_sensitivity
                if self.scroll_x < 0: self.scroll_x = 0
                elif self.scroll_x > max_scroll[0]: self.scroll_x = max_scroll[0]
            else:
                self.scroll_y += wheel * settings.wheel_sensitivity
                if self.scroll_y < 0: self.scroll_y = 0
                elif self.scroll_y > max_scroll[1]: self.scroll_y = max_scroll[1]
                #scroll vertically (normal)


    def draw(self,surf:Surface):
        surf = surf.subsurface(self.rect)
        sx = self.scroll_x
        sy = self.scroll_y
        for row in self.contents:
            for element in row:
                if element is not None:
                # if crect.colliderect(element.rect):
                    element.rect.left -= sx
                    element.rect.top -= sy
                    element.draw(surf)
                    element.rect.left += sx
                    element.rect.top += sy