from pygame import event


class Input:
    '''
    A way to dump all the input gathered by getAllInput() so that it can be directly put into
    update methods so that they can pick what they need to update things.
    '''
    mousex:int
    mousey:int
    mb1:bool
    mb2:bool
    mb3:bool
    lctrl:bool = False
    lalt:bool = False
    

    __slots__ = 'Events','KDQueue','KUQueue','dt','wheel','touch_wheel','quitEvent','windowClose','mb1d','mb2d','mb3d','mb1','mb2','mb3','mb1u','mb2u','mb3u','mousex','mousey','windowLeave','windowEnter'
    def __init__(self):
        self.mousex = self.mousey = -99999
        self.Events  = set()
        self.KDQueue:list[event.Event] = []
        self.KUQueue:list[event.Event] = []
        self.dt:float = 0
        self.wheel:float = 0
        self.touch_wheel = 0.0
        self.quitEvent = False
        self.windowClose = []
        self.windowLeave:list[event.Event] = []
        self.windowEnter:list[event.Event] = []
        self.mb1d:bool = False
        self.mb2d:bool = False
        self.mb3d:bool = False
        self.mb1u:bool = False
        self.mb2u:bool = False
        self.mb3u:bool = False

    @property
    def mpos(self): return self.mousex,self.mousey

    def consumeKey(self,key,mods:int=0):
        if not self.KDQueue: return False
        for event in self.KDQueue:
            if event.key==key and (event.mod&mods or mods==0): break
        else:
            return False
        self.KDQueue.remove(event)
        return True

    def consumeKeys(self,*keys:tuple[int,int]):
        if not self.KDQueue: return False
        for event in self.KDQueue:
            b = False
            for key,mods in keys:
                if event.key==key and (event.mod&mods or mods==0): 
                    b = True
                    break
            if b: break
        else:
            return False
        self.KDQueue.remove(event)
        return True

    def checkKeys(self,*keys:tuple[int,int]):
        if not self.KDQueue: return False
        for event in self.KDQueue:
            for key,mods in keys:
                if event.key==key and (event.mod&mods or mods==0): 
                    return True
        return False

    def clearALL(self):
        self.__init__()

    def clearMouse(self):
        self.mb1d = self.mb2d = self.mb3d = self.mb1u = self.mb2u = self.mb3u = self.mb1 = self.mb2 = self.mb3 = False
        self.mousex = self.mousey = -99999

    def clearKeys(self):
        self.KUQueue.clear()
        self.KDQueue.clear()
