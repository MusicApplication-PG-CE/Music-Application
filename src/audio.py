from pygame import mixer
from Utils import logger #type: ignore
mixer.init()

__all__ = [
    'Type',
    'loadSound',
    'playSound',
    'music'
]

class SoundType(int): 
    '''
    Types of sounds, each type of sound can get variable amounts of channels to play on
    this ensures that specific types can always play or not be interfered by with other
    types of sounds.

    For Example: Say you have a game with constant footstep sounds and a few ambient sounds
    however, it is vital the ambient sounds always play when desired, and the footsteps 
    must not interfere with that. The solution using this tool would be to create 2 new Types
    >>> FOOTSTEP = SoundType(#)
    >>> AMBIENCE = SoundType(#)
    and in the _channel_allocations you can set how many channels the ambience can take, and 
    how much the footsteps can, now when a footstep plays it will only take up a maximium of 
    the allocations have defined, and the ambient sounds will be guaranteed to have as much
    channels to play as specified by the allocations as well.

    However there is not an unlimited amount of channels that can be used, at the time of
    writing this, pygame allows a maximum of 8 channels to be used.
    '''
class Type:
    FX = SoundType(0)
    SHORT = SoundType(1)
    MISC = SoundType(2)
    RARE = SoundType(3)
    AMBIENCE = SoundType(4)
    EXPLOSION = SoundType(5)
    VOICELINE = SoundType(6)
    
_channel_allocations = {
    Type.FX     : 2,
    Type.AMBIENCE  : 2,
}

if sum(_channel_allocations.values()) < mixer.get_num_channels():
    logger.log("Channels Allocated Less than maximum. Alloc:",sum(_channel_allocations.values()),'Max:',mixer.get_num_channels())
elif sum(_channel_allocations.values()) > mixer.get_num_channels():
    msg = f"More Channels Allocated than maximum. Alloc: {sum(_channel_allocations.values())}, Max: {mixer.get_num_channels()}"
    logger.log(msg)
    raise OverflowError(msg)

a = -1
channels = {type:[mixer.Channel((a:= a+1)) for _ in range(allocs)] for type,allocs in _channel_allocations.items()}
del a

def loadSound(path:str):
    return mixer.Sound(path)

def findChannel(type:SoundType) -> mixer.Channel | None:
    for c in channels.get(type,[]):
        if not c.get_busy():
            return c

def playSound(s:mixer.Sound,type:SoundType,millis:int=0,times:int=1,fadein_ms:int=0):
    logger.log("Playing Sound")
    channel = findChannel(type)
    if channel is None: return False
    channel.play(s,times-1,millis,fadein_ms)
    return True

from pygame import mixer_music as music


