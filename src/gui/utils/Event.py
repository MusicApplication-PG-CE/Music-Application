import typing

P = typing.ParamSpec("P")

class Event(typing.Generic[P]):
    __slots__ = 'listeners'
    def __init__(self):
        self.listeners:list[typing.Callable[P,None]] = []

    def register(self,function:typing.Callable[P,None]):
        self.listeners.append(function)
        return function
    
    def clearListeners(self):
        self.listeners.clear()

    def fire(self,*args:P.args,**kwargs:P.kwargs):
        self(*args,**kwargs)

    def __call__(self,*args:P.args,**kwargs:P.kwargs):
        for listener in self.listeners:
            listener(*args,**kwargs)





