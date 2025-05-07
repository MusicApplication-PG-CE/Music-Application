import typing
T = typing.TypeVar('T')

class Headers:
    '''For the most part HTTP headers can be stored as dictionary key,value pairs. However there are some 
    headers for which there can be multiple within one packet, for that reason alone this class exists. 
    '''
    __slots__ = 'headers',

    def __init__(self,pairs:list[tuple[str,str]]|typing.ItemsView = []):
        self.headers:dict[str,list[str]] = {}
        for k,v in pairs:
            self.addHeader(k,v)

    def addHeader(self,name:str,value:str):
        v = self.headers.get(name)
        if v is None:
            self.headers[name] = [value]
        else:
            v.append(value)

    def get(self,name:str,default:T = None) -> str|T:
        values = self.headers.get(name)
        if values is None: return default
        return values[0]
    
    def getAll(self,name:str) -> list[str]|None:
        values = self.headers.get(name)
        if values is None: return None
        return values
        
    def __getitem__(self,key:str)->str|list[str]:
        values = self.headers[key]
        if len(values) == 1:
            return values[0]
        return values
         
    def __contains__(self,key:str):
        return self.headers.__contains__(key)
    
    def __setitem__(self,key:str,value:str):
        return self.addHeader(key,value)
    
    def copy(self):
        h = Headers()
        h.headers = self.headers.copy()
        return h
    
    def __repr__(self) -> str:
        out =  'Headers:\n'
        for header,values in self.headers.items():
            for value in values:
                out += f'\t{header}: {value}\n'
        return out

    def toString(self):
        out = ''
        for header,values in self.headers.items():
            for value in values:
                out += f'{header}: {value}\n'
        return out