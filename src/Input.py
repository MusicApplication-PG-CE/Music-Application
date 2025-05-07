from pygame import event
from pygame import constants as const
from pygame import mouse
from .gui import Input
from typing import Callable

__all__ = [
    'Input',
    'getInput'
]

event_dispatch:dict[int,Callable[[Input,event.Event],None]] = {}


def onEvent(e):
    def decorator(func:Callable[[Input,event.Event],None]):
        event_dispatch[e] = func
    return decorator

@onEvent(const.KEYDOWN)    
def onKEYDOWN(input:Input,e:event.Event):
    input.KDQueue.append(e)
    if e.key == const.K_LCTRL:
        Input.lctrl = True
    elif e.key == const.K_LALT:
        Input.lalt = True

@onEvent(const.KEYUP)
def onKEYUP(input:Input,event:event.Event):
    input.KUQueue.append(event)
    if event.key == const.K_LCTRL:
        Input.lctrl = False
    elif event.key == const.K_LALT:
        Input.lalt = False

onEvent(const.QUIT)(lambda i,e: setattr(i,'quitEvent',True))
onEvent(const.WINDOWCLOSE)(lambda i,e: i.windowClose.append(e))
onEvent(const.WINDOWLEAVE)(lambda i,e: i.windowLeave.append(e))
onEvent(const.WINDOWENTER)(lambda i,e: i.windowEnter.append(e))

@onEvent(const.MOUSEBUTTONDOWN)
def onMOUSEBUTTONDOWN(i:Input,e:event.Event):
    if e.button == 1:
        i.mb1d = True
    elif e.button == 2:
        i.mb2d = True
    elif e.button == 3:
        i.mb3d = True

@onEvent(const.MOUSEWHEEL)
def onMOUSEWHEEL(i:Input,e:event.Event):
    i.wheel += -e.precise_y

@onEvent(const.FINGERMOTION)
def onFINGERMOTION(i:Input,e:event.Event):
    i.touch_wheel += -e.dy
@onEvent(const.MOUSEBUTTONUP)
def onMOUSEBUTTONUP(i:Input,e:event.Event):
    if e.button ==1:
        i.mb1u = True
    elif e.button == 2:
        i.mb2u = True
    elif e.button == 3:
        i.mb3u = True


def getInput() -> Input:
    input = Input()
    input.mousex,input.mousey = mouse.get_pos()
    input.mb1,input.mb2,input.mb3 = mouse.get_pressed()
    for e in event.get():
        input.Events.add(e.type)
        if f:=event_dispatch.get(e.type):
            f(input,e)
    return input


