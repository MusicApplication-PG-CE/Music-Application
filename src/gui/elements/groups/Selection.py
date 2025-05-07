from ...core import *
from ...utils import utils
from ... import settings

class Selection(DrawBase):
    __slots__ = 'rect','selectionSize','max_y','buttonFactory','dataGetter','selection','y_scroll_real','y_scroll_target','aligned_y','mhover','color_scheme','spacing','size_change_event','surf2','pwheel','last_surf'
    def __init__(self,pos:tuple[int,int],selectionSize:tuple[int,int],max_y:int,color_scheme:ColorScheme,dataGetter:types.Callable[[],types.Iterable[types.T]]|None,buttonFactory:types.Callable[[tuple[int,int],tuple[int,int],ColorScheme,types.T],types.SelectionProtocol]=None,spacing:float = 1):
        self.rect = Rect(pos,(selectionSize[0],max_y))
        self.selectionSize = selectionSize
        self.max_y = max_y
        self.buttonFactory = buttonFactory
        self.dataGetter = dataGetter or (lambda :[])
        self.selection:list[types.SelectionProtocol] = []
        self.y_scroll_real:int = 0
        self.y_scroll_target:float = 0 
        self.aligned_y = True
        self.mhover = False
        self.color_scheme = color_scheme
        self.spacing = spacing
        self.size_change_event:Event[[]] = Event()
        self.surf2 = None
        self.pwheel = 0
        self.recalculateSelection()
        self.last_surf = None
        
    def refitSelection(self):
        return
        pixel_spacing = int(self.selectionSize[1]*(self.spacing-1))
        for i,s in enumerate(self.selection):
            pos= (0,((self.selectionSize[1]+pixel_spacing)*i).__trunc__())
            s.pos = pos
            s.rect.size = self.selectionSize
            if hasattr(s,'onResize'):
                s.onResize(self.rect.size) #type: ignore

    def recalculateSelection(self):
        pixel_spacing = int(self.selectionSize[1]*(self.spacing-1))
        self.selection = [self.buttonFactory((0,((self.selectionSize[1]+pixel_spacing)*i).__trunc__()),self.selectionSize,self.color_scheme,d) for i,d in enumerate(self.dataGetter())]
        self.size_change_event.fire()
        if self.fullHeight < self.max_y:
            self.setYScroll(0)
        elif self.fullHeight + self.y_scroll_real < self.max_y:
            self.setYScroll(self.fullHeight-self.max_y)
        else:
            for s in self.selection:
                s.setYOffset(self.y_scroll_real)
    def resize(self,newPos:tuple[int,int],newSelectionSize:tuple[int,int],new_max_y:int):
        self.rect.topleft = newPos
        self.rect.width = newSelectionSize[0]
        self.rect.height = new_max_y
        pssize = self.selectionSize
        self.selectionSize = newSelectionSize
        self.max_y = new_max_y
        if pssize != newSelectionSize:
            self.refitSelection()

        self.size_change_event.fire()
        self.setYScroll(self.y_scroll_real)

    def onResize(self,size:tuple[int,int]):
        self.max_y = self.rect.height
        self.selectionSize = (self.rect.width,self.selectionSize[1])
        self.refitSelection()
        if self.fullHeight < self.max_y:
            self.y_scroll_real = 0
        elif self.y_scroll_real > self.fullHeight - self.max_y:
            self.y_scroll_real = self.fullHeight - self.max_y  
            self.setYScroll(self.y_scroll_real)
        if self.surf2 and self.rect.size != self.surf2.get_size():
            self.surf2 = None

    @property
    def fullHeight(self):
        ps = (self.selectionSize[1]*(self.spacing-1)).__trunc__()
        return len(self.selection) * (self.selectionSize[1]+ps)

    def getScrollPercent(self):
        fullHeight = self.fullHeight
        usableHieght = self.max_y
        if usableHieght >= fullHeight:
            return 1.0
        return self.y_scroll_real / (fullHeight - usableHieght)

    def setScrollPercent(self,percent:float):
        fullHeight = self.fullHeight
        usableHieght = self.max_y
        if usableHieght <= fullHeight:
            self.setYScroll((percent *(fullHeight - usableHieght)).__round__())

    def setYScroll(self,y:int|float):
        if self.fullHeight <= self.max_y: 
            y =0
        elif y > self.fullHeight - self.max_y:
            y = self.fullHeight - self.max_y
        elif y < 0: 
            y = 0
        self.aligned_y = False
        self.y_scroll_real = int(y) 
        self.y_scroll_target = y
        for s in self.selection:
            s.setYOffset(self.y_scroll_real)

    def update(self,input:Input):
        mpos,wheel = input.mpos,input.wheel
        touch_wheel = input.touch_wheel
        if self.rect.collidepoint(mpos):  
            self.mhover = True 
            input.wheel = 0
            input.touch_wheel = 0     
            if wheel and self.fullHeight > self.max_y:
                w = (wheel + self.pwheel.__trunc__()) * settings.wheel_sensitivity
                self.y_scroll_target += w
                if self.y_scroll_target > self.fullHeight - self.max_y:
                    self.y_scroll_target = self.fullHeight - self.max_y
                elif self.y_scroll_target < 0: 
                    self.y_scroll_target = 0
                self.aligned_y = False
            elif touch_wheel and self.fullHeight > self.max_y:
                dpy = touch_wheel
                self.y_scroll_target += dpy
                self.setYScroll(self.y_scroll_target)

            input.mousex -= self.rect.left
            input.mousey -= self.rect.top
            for i,button in enumerate(self.selection):
                top = (i*self.selectionSize[1]*self.spacing).__trunc__() - self.y_scroll_real
                bottom = top + self.selectionSize[1]
                if bottom < 0 or top > self.max_y: continue
                button.update(input)
            input.mousex += self.rect.left
            input.mousey += self.rect.top
        else:
            if self.mhover:
                for s in self.selection:
                    s.setToUp()
                self.mhover = False
            if input.mb1d or input.mb1u or input.mb3u or input.mb3d:
                mx,my = input.mpos
                input.mousex = -999
                input.mousey = -999
                for button in self.selection:
                    button.update(input)
                input.mousey = my
                input.mousex = mx
        
        if not self.aligned_y:
            self.y_scroll_real = int(utils.expDecay(self.y_scroll_real,self.y_scroll_target,1/settings.scroll_smoothing,input.dt))
            if (self.y_scroll_real - self.y_scroll_target).__abs__() <= 2:
                self.y_scroll_real = int(self.y_scroll_target)
                self.aligned_y = True
            for s in self.selection:
                s.setYOffset(self.y_scroll_real)
        self.pwheel = self.pwheel + wheel * 0.4 if wheel else 0

    def elementResizeHook(self,element:types.SelectionProtocol): ...

    def draw(self,surf:Surface):
        if self.last_surf is not surf:
            self.surf2 = surf.subsurface(self.rect)
            self.last_surf = surf
        pixel_spacing = int(self.selectionSize[1]*(self.spacing-1))
        srf = surf.subsurface(self.rect)
        i = int(self.y_scroll_real/(self.selectionSize[1]*self.spacing))
        while i < len(self.selection) and (s:=self.selection[i]).rect.top <=self.max_y:
            if s.rect.size != self.selectionSize:
                s.pos= (0,((self.selectionSize[1]+pixel_spacing)*i).__trunc__())
                s.rect.size = self.selectionSize
                if hasattr(s,'onResize'):
                    s.onResize(self.rect.size) #type: ignore
                self.elementResizeHook(s)
            s.draw(srf)
            i+=1
