import os

class Path:
    __slots__ = 'dirpath','filename'
    def __init__(self,dirpath:str,filename:str):
        self.dirpath = dirpath
        self.filename = filename

    @property
    def fullpath(self):
        return os.path.join(self.dirpath,self.filename).replace('\\','/')
    
    @classmethod
    def fromFile(cls,path:str):
        return Path(os.path.dirname(path),os.path.basename(path))