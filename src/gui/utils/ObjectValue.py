import typing


from .Event import Event

class ObjectValue[T]:
  __slots__ = 'obj','obj_change_event'
  def __init__(self,obj:T) -> None:
    self.obj = obj
    self.obj_change_event:Event[[T]] = Event()

  def set(self,obj:T): 
    self.obj = obj
    self.obj_change_event.fire(obj)

  def get(self): 
    return self.obj
  
  def notify(self,*args:typing.Any):
    self.obj_change_event.fire(self.obj)

