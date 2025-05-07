from typing import Callable,ParamSpec,TypeVar
P = ParamSpec("P")
K = TypeVar("K")
def cache(func:Callable[P,K]) -> Callable[P,K]:
    cache:dict[tuple,K] = {}
    def wrapper(*args,**kwargs):
        i = tuple(args) + tuple(kwargs)
        if i not in cache:
            cache[i] = func(*args,**kwargs)
        return cache[i]
    wrapper.__name__ = func.__name__
    return wrapper #type: ignore
        
def fancyCache(func:Callable[P,K]) -> Callable[P,K]:
  class Wrapper:
    def __init__(self) -> None:
      self.cache = {}
      self.func = func
    def clearCache(self):
      self.cache.clear()
    def __call__(self,*args:P.args,**kwargs:P.kwargs):
      if args not in self.cache:
        self.cache[args] = func(*args,**kwargs)
      return self.cache[args]    
  return Wrapper()