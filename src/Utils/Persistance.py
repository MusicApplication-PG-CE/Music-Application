from typing import Any,Final,final
try: from .Singleton import Singleton
except: from Singleton import Singleton

ValidType = list|tuple|set|dict|int|str|bytes|bool

class PersistantObject(Singleton):
    VALID_TYPES:Final = list,tuple,set,dict,int,str,bytes,bool
    
    def __init_subclass__(cls) -> None:
        if not hasattr(cls,'_file'):
            raise SyntaxError("All Subclasses of <PersistantObject> must have a class attribute called, ")
        if hasattr(cls,'_lock'):
            raise SyntaxError("<Persistant Object> uses class attribute: _lock. Subclasses cannot define this value")
        cls._lock = True#type: ignore

    def __new__(cls, *args, **kwargs):
        new = not hasattr(cls,'_instance')
        inst = super().__new__(cls,*args, **kwargs)
        if new and not inst.__loadstate__():
            inst.init(*args,**kwargs) 
        return inst
    
    def init(self,*args,**kwargs): '''Init is called when __loadstate__ is unsuccessful, meaning that its the first time that the object was instantiated'''

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name,value)
        if self.__class__._lock:
            self.__savestate__()

    @classmethod
    def unlock(cls):
        cls._lock = False
    
    @classmethod
    def lock(cls):
        cls._lock = True
        cls._instance.__savestate__()
        
    @final
    def hasslots(self):
        return hasattr(self.__class__,'__slots__')

    def __setstate__(self,state:dict[str,ValidType]):  
        for k,v in state.items():
            super().__setattr__(k,v)

    
    def __checkobj__(self,obj:Any):
        if type(obj) not in PersistantObject.VALID_TYPES:
            if type(obj) in (list,tuple,set):
                for s in obj:
                    if not self.__checkobj__(s):
                        return False
            elif type(obj) == dict:
                for k,v in obj.items():
                    if type(k) != str:
                        return False
                    if not self.__checkobj__(v):
                        return False
        return True

    def __getstate__(self):
        if not self.hasslots():
            keys = tuple(self.__dict__.keys())
        else:
            keys = self.__class__.__slots__ #type: ignore
        mapping:dict[str,ValidType] = {}
        for k in keys:
            v = super().__getattribute__(k) 
            if not self.__checkobj__(v):
                raise ValueError(f"Found object type<{type(v)}> which cannot be saved")
            mapping[k] = v
        return mapping
    

    def __savestate__(self):
        state = self.__getstate__()
        import json
        with open('./'+self.__class__._file,'w+') as file: #type: ignore
            json.dump(state,file,indent = 2)
        

    def __loadstate__(self) -> bool:
        try:
            import json
            with open('./'+self.__class__._file,'r') as file: #type: ignore
                state = json.load(file)
            self.__setstate__(state)
        except:
            return False
        return True