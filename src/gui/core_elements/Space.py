from ..core import *
class Space(DrawBase):
    __slots__ = 'rect','surface','to_update','to_draw','sub_spaces','splits','is_container','container_copies','active_container'
    def __init__(self,rect:Rect):
        self.rect = rect
        self.to_update:list[types.SupportsUpdate] = []
        self.to_draw:list[types.SupportsDraw] = []
        self.sub_spaces:list[Space] = []
        self.splits:list[tuple[int,int]] = []
        self.is_container = False
        self.container_copies:dict[str,tuple[list[types.SupportsUpdate],list[types.SupportsDraw]]] = {}
        self.active_container:str = ''

    def makeContainer(self,ui_elements:dict[str,list[types.SupportsDraw|types.SupportsUpdate|None]],active:str,shared_elements:list[types.SupportsDraw|types.SupportsUpdate] = []):
        if self.to_draw or self.to_update: raise RuntimeError("Cannot Make Space that already contains elements into Container")
        assert active in ui_elements, '<active> must be a key in the dict <container_copies>'
        self.is_container = True
        for key,l in ui_elements.items():
            self.to_update,self.to_draw = [],[]
            self.addObjects(*l)
            self.addObjects(*shared_elements)
            self.container_copies[key] = (self.to_update,self.to_draw)
        self.setActive(active)
        return self

    def copyEmptyShallow(self):
        '''Returns a new Space with the same size with no sub_spaces or UIElements and not as a container'''
        return Space(self.rect.copy())

    def addObject(self,obj:types.T) -> types.T:
        '''Will add a UI element to the Space, if this Space is a Container, it adds the element to the currently loaded element list
        Returns UI element'''
        if hasattr(obj,'update'):
            self.to_update.append(obj)#type: ignore
        if hasattr(obj,'draw'):
            self.to_draw.append(obj) #type: ignore
            self.to_draw.sort(key=lambda d:d.order_in_layer)
            if hasattr(obj,'onResize'):
                obj.onResize(self.rect.size) #type: ignore
        return obj

    def removeObject(self,obj:types.SupportsUpdate|types.SupportsDraw):
        if self.is_container:
            for u,d in self.container_copies.values():
                if obj in u:
                    u.remove(obj)#type: ignore
                if obj in d:
                    d.remove(obj)
        else:
            if hasattr(obj,'update'):
                self.to_update.remove(obj)#type: ignore
            if hasattr(obj,'draw'):
                self.to_draw.remove(obj) #type: ignore

    def wipe(self,quick:bool=False):
        '''Destroy All References to Every Object Registered, Drawables, Updatables, Sub-Spaces, etc...'''
        if quick:
            self.to_update = []
            self.to_draw = []
            self.sub_spaces = []
            return
        self.container_copies.clear()
        self.is_container = False
        self.splits.clear()
        self.to_update.clear()
        self.to_draw.clear()
        for sub in self.sub_spaces:
            sub.wipe()
        self.sub_spaces.clear()

    def addObjects(self,*objs:types.SupportsUpdate|types.SupportsDraw|None):
        '''Add UIElements in bulk, for more info read addObject docstring'''
        for obj in objs:
            if obj is not None:
                self.addObject(obj)

    def setActive(self,key:str):
        if not self.is_container: raise RuntimeError("Active Key only applies for Container's")
        self.to_update, self.to_draw = self.container_copies[key]
        self.active_container = key

    def getActive(self) -> str:
        if not self.is_container: raise RuntimeError("Active Key only applies for Container's")
        return self.active_container

    def resized(self,space:"Space"):
        '''
        This function is a little confusing, but its main purpose is to take in a blank <Space> object and partition it
        exactly how itself is, however the blank <Space> object may be of different size than this object
        '''
        for (direction,amount),sub in zip(self.splits,self.sub_spaces):
            f = [space.cutTopSpace,space.cutBottomSpace,space.cutLeftSpace,space.cutRightSpace][direction]
            sub.resized(f(amount))
        if self.is_container:
            space.container_copies = self.container_copies
            space.is_container = True
            space.to_update = self.to_update
            space.to_draw = self.to_draw
            space.active_container = self.active_container
            for _u,draw in self.container_copies.values():
                for d in draw: #type: ignore
                    if hasattr(d,'onResize'):
                        d:types.SupportsResize
                        d.onResize(space.rect.size)
        else:
            space.to_update = self.to_update
            space.to_draw = self.to_draw
            for d in self.to_draw: #type: ignore
                if hasattr(d,'onResize'):
                    d:types.SupportsResize
                    d.onResize(space.rect.size) 

    def update(self,input:Input):
        l,t = self.rect.topleft #store topleft just in case it changes from updates
        input.mousex -= l
        input.mousey -= t
        for u in self.to_update:
            u.update(input)
        input.mousex += l
        input.mousey += t

        for s in self.sub_spaces:
            s.update(input)

    def draw(self,surf:Surface):
        surface = surf.subsurface(self.rect)
        for d in self.to_draw:
            d.draw(surface)
        for s in self.sub_spaces:
            s.draw(surf)

    def _resize_ui(self):
        for element in self.to_draw:
            if hasattr(element,'onResize'):
                element.onResize(self.rect.size) #type: ignore
        



    def cutTopSpace(self,amount:int) -> "Space":
        new = Space(Rect(self.rect.left,self.rect.top,self.rect.width,amount))
        self.rect.height -= amount
        self.rect.top += amount
        self.splits.append((0,amount)) 
        self.sub_spaces.append(new)
        self._resize_ui()
        return new

    def cutBottomSpace(self,amount:int) -> "Space":
        new = Space(Rect(self.rect.left,self.rect.bottom-amount,self.rect.width,amount))
        self.rect.height -= amount
        self.splits.append((1,amount)) 
        self.sub_spaces.append(new)
        self._resize_ui()
        return new

    def cutLeftSpace(self,amount:int) -> "Space":
        new = Space(Rect(self.rect.left,self.rect.top,amount,self.rect.height))
        self.rect.left += amount
        self.rect.width -= amount
        self.splits.append((2,amount)) 
        self.sub_spaces.append(new)
        self._resize_ui()
        return new

    def cutRightSpace(self,amount:int) -> "Space":
        self.rect.width -= amount
        new = Space(Rect(self.rect.right,self.rect.top,amount,self.rect.height))
        self.splits.append((3,amount)) 
        self.sub_spaces.append(new)
        self._resize_ui()
        return new
