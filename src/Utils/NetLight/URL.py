from typing import Optional
from . import URLParser

class URL:
    __slots__ = '_url','scheme','host','inner_url'
    def __init__(self,url:str):
        self._url = url
        self.scheme = URLParser.resolve_scheme(url)
        self.host:str= URLParser.resolve_host(url)
        self.inner_url:str = URLParser.resolve_inner_url(url)
    
    def sameConn(self,other:"URL"):
        if other is None: return False
        return self.scheme and other.scheme and (other.scheme == self.scheme and other.host == self.host)
    
    def __repr__(self):
        return self._url