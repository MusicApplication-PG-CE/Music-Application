import time
from typing import Any
from src.Utils.Persistance import PersistantObject
from src.Utils.events import Event
from src.Utils.fast import cache
from src.Utils import logger #type: ignore
from src.Utils import NetLight #type: ignore
from pygame import constants as const

with open('./Assets/version.txt','r') as file:
    version = file.read().strip()

UP_TO_DATE = True

class Settings(PersistantObject):
    _file = './config/Settings.config'
    def __init__(self):
        self.unlock()
        if not hasattr(self,'tryFindSong'):
            self.tryFindSong = True
        if not hasattr(self,'useItunes'):
            self.useItunes = True
        if not hasattr(self,'shuffle'):
            self.shuffle = False
        if not hasattr(self,'repeat_level'):
            self.repeat_level = 0
        if not hasattr(self,'fps'):
            self.fps = 60
        if not hasattr(self,'volume'):
            self.volume = 1.0
        if not hasattr(self,'windowName'):
            self.windowName = 'Music Application'
        if not hasattr(self,'pause_fade_time_ms'):
            self.pause_fade_time_ms = 150
        if not hasattr(self,'youtube_prefetch'):
            self.youtube_prefetch = True
        if not hasattr(self,'key_repeat_interval'):
            self.key_repeat_interval = 25
        if not hasattr(self,'key_repeat_delay'):
            self.key_repeat_delay = 400
        if not hasattr(self,'scroll_smoothing'):
            self.scroll_smoothing = .1
        if not hasattr(self,'iso_country_code'):
            self.iso_country_code = 'US'
        if not hasattr(self,'miniplayer_always_on_top'):
            self.miniplayer_always_on_top = True
        if not hasattr(self,'miniplayer_borderless'):
            self.miniplayer_borderless = True
        if not hasattr(self,'borderless'):
            self.borderless = False
        if not hasattr(self,'miniplayer_size'):
            self.miniplayer_size = [300,200]
        if not hasattr(self,'miniplayer_pos'):
            self.miniplayer_pos:list[int]|tuple[int,int,]|None = None
        self.lock()

    @cache
    def makeSharedSettingsValue(self,attr:str):
        return SharedSettingValue(self,attr)

    def setTryFindSong(self,x:bool):
        self.tryFindSong = x        

    def setUseItunes(self,x:bool):
        self.useItunes = x

settings = Settings()


s = time.perf_counter()
try:
    response = NetLight.fetch('https://lgarciasanchez5450.github.io/static/assets/latest_version')
    if response.status_code == 200:
        UP_TO_DATE = response.body.decode().strip() == str(version).strip()
    logger.log("Time to check Latest Version: ",time.perf_counter()-s)
except:
    logger.log("Error in Checking Latest Version: ",time.perf_counter()-s)
del s


class SharedSettingValue:
    __slots__ = 'obj','attr','on_set'
    def __init__(self,obj,attr:str):
        self.obj = obj
        self.attr = attr
        self.on_set:Event[[Any]] = Event()

    def get(self):
        return getattr(self.obj,self.attr)
    
    def set(self,value):
        setattr(self.obj,self.attr,value)
        self.on_set.fire(value)


