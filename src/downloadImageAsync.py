from typing import Callable, Optional
import io
import pygame
from .Utils import NetLight
import sys
__all__ = [
    'queueDownload'
]
conn_pool = NetLight.ConnectionPool(2)
def queueDownload(url:Optional[str],callback:Callable[[pygame.Surface|None],None]):
    if url is not None:
        if url in cache:
            callback(cache[url])
        else:
            conn_pool.queueUrl(url,lambda data: add_to_cache(url,callback,data))

cache:dict[str,pygame.Surface] = {}
def add_to_cache(url,callback,data):
    a = cache[url] = pygame.image.load(io.BytesIO(data),'webp').convert()
    callback(a)

def clear_cache(use_refcount:bool = True):
    if use_refcount:
        for url in list(cache.keys()):
            if sys.getrefcount(cache[url]) <= 2: #the cache keeps one reference and getrefcount also makes a temp reference so the lowest number should be 2
                del cache[url]
    else:
        cache.clear()
