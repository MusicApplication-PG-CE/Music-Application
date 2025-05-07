from typing import *
import os
import math
import time
import typing
import pygame
from collections import deque

from . import gui
from . import exporter
from . import Installer
from .Utils import Async
from .Utils import logger 
from .Utils import Stopwatch
from .Utils import advanced_color as colorUtils 
from .Utils.YoutubeParsers import types as yttypes
from .Utils.SearchItunes import ItunesResult
from .gui.ui import *
from .gui.core import *
from .gui.core.types import *
from .gui.utils import FontRule
from .Utils.debug import Tracer

from .Settings import settings #type: ignore

from .DownloadingStatus import DownloadingStatus
from .downloadImageAsync import queueDownload,clear_cache
from .AppFramework import MusicPlayer,database,Song,Playlist,keybinds
from .Youtube_Accesor import downloadURLAsync,yt_dlp_days_since_update,AsyncInOutBatchDownloader
from .utils2 import cache, isInsideCircle, formatArtists, getCharWidth, trimText, foreverIter, formatTimeSpecial,formatTime2,reprKey,lerp
from .metadata import getYTVideoMetadata, getYTPlaylistSongs, clear_prefetch,prefetchIfNeededAsync,getMetaDataForYTBatchAsync,DownloadingSong,getYTSongsFromITunes
from .AppFramework import MUSIC_PATH
S = TypeVar('S',bound=str)
T = TypeVar('T')


try:
    from .assets import * #type: ignore
except Exception:
    logger.log('Error Loading Assets. Possible Solution: Redownload Application')
    raise
DownloadingStatus.font_default = font_default
DownloadingStatus.text_color = text_color
DOUBLE_CLICK_THRESHOLD = 0.5
base_layer = Layer((200,200))

miniplayer_base = Layer((200,200))

def wipe(o:Any):
    if type(o) is list:
        i = 0
        while i < len(o):
            wipe(o[i])
    elif type(o) is dict:
        o.clear()
    elif hasattr(o,'__dict__'):
        for attr in dict(o.__dict__):
            wipe(getattr(o,attr))
            delattr(o,attr)

def getLengthOfHighestBelow(xs:Sequence[int],below:int):
    s = 0
    for i,x in enumerate(xs):
        s += x
        if s > below:
            return i
    return len(xs)

def toNone(*args):
    return None

def tNF(*args:Callable[[],Any]):
    def _inner():
        for a in args:
            a()
    return _inner

class CanBeCheckboxed(Protocol):
    @property
    def rect(self) -> Rect: ...
    def draw(self,surf:Surface): ...
    def onResize(self,size:tuple[int,int]): ...
    color_scheme:ColorScheme

K = TypeVar("K",bound=Hashable)
@cache
def getCheckMark(width:int,height:int,color:tuple[int,int,int]):
    s = Surface((width,height))
    s.fill((0,0,1))
    s.set_colorkey((0,0,1))
    draw.lines(s,color,False,[(width//4,height//4),(width//2,height//2+2),(width,0)])
    return s

class Null(DrawBase):
    __slots__ = 'rect'
    def __init__(self) -> None:
        self.rect = Rect(0,0,1,1)
    def onResize(self,size:tuple[int,int]):...
    def update(self,input:Input): ...
    def draw(self,surf:Surface): ...

class CheckBoxLone(Button):
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_layout: ColorLayout, callback:Callable[[bool],Any],starting_value:bool = False):
        cs = ColorScheme(*color_layout.background)
        self.color_layout = color_layout
        self.on = ObjectValue(starting_value)
        self.on.obj_change_event.register(callback)
        super().__init__(pos, size, cs, None, lambda : self.on.set(not self.on.get()))

    
        
    
    def draw(self, surf: pygame.Surface):
        # super().draw(surf)
        r = self.rect
        draw.rect(surf,self.color_layout.background,self.rect,0,4)

        if self.on.get():
            draw.rect(surf,self.color_layout.foreground,self.rect,0,4)
            draw.lines(surf,self.color_layout.tertiary,False,
                         [r.move(-4,-4).center,r.move(0,2).center,r.move(10,-10).center],3)
        else:
            draw.rect(surf,self.color_layout.foreground,self.rect,2,4)

        
class CheckBox(SelectionBase):
    def __init__(self,pos:tuple[int,int],size:tuple[int,int],cs:ColorScheme,i:K,t:typing.MutableMapping[K,bool],d:T,typ:Callable[[tuple[int,int],tuple[int,int],ColorScheme,T],CanBeCheckboxed]):
        def toggle():
            t[i]=not t[i]
        super().__init__(pos,size,cs,toggle)
        self.obj = typ((30,pos[1]),(size[0]-30,size[1]),cs,d)
        self.i = i
        self.t = t
    @Tracer().traceas('CheckBox')
    def onResize(self,size:tuple[int,int]):
        r = self.obj.rect
        r.width = self.rect.width - 30
        r.height = self.rect.height
        r.left = self.rect.left + 30
        r.top = self.rect.top
        self.obj.onResize(size) #type: ignore

    def toggle(self):
        self.t[self.i] = not self.t[self.i]
    
    @property
    def is_checked(self):
        return self.t[self.i]
    
    @is_checked.setter
    def is_checked(self,val:bool):
        self.t[self.i] = val

    def draw(self, surf: Surface):
        super().draw(surf)
        self.obj.rect.top = self.rect.top
        self.obj.draw(surf)
        r = Rect(4,0,22,22)
        r.centery = self.rect.centery
        draw.rect(surf,self.obj.color_scheme.color,r,0 if self.is_checked else 3,2)
        if self.is_checked:
            #draw arrow
            #m = getCheckMark(*r.size,(255,255,255))
            #surf.blit(m,)
            draw.lines(surf,self.obj.color_scheme.getLight(170),False,
                         [r.move(-4,-4).center,r.move(0,2).center,r.move(10,-10).center],3)

    def destroy(self):
        self.__dict__.clear()


class PickManySongs(Selection):
    def __init__(self, pos: tuple[int, int], selectionSize: tuple[int, int], max_y: int, color_scheme: ColorScheme, spacing: float = 1,checked:dict[Song,bool] = {}):
        self.checked = checked
        super().__init__(pos, selectionSize, max_y, color_scheme,lambda :database.songs.copy(),SongBox, spacing)
    def recalculateSelection(self):
        self.songs_displayed = list(self.dataGetter()) #type: ignore
        if not self.songs_displayed: self.songs_displayed = database.songs.copy()
        for key in self.songs_displayed:
            if key not in self.checked:
                self.checked[key] = False #type: ignore
        self.setYScroll(0)
        self.selection =  [CheckBox((0,(self.selectionSize[1]*i*self.spacing).__trunc__()),self.selectionSize,self.color_scheme,song,self.checked,song,SongBox) for i,song in enumerate(self.songs_displayed)]#type: ignore
        self.size_change_event.fire()
        
        if self.fullHeight < self.max_y:
            self.setYScroll(0)
        elif self.fullHeight + self.y_scroll_real < self.max_y:
            self.setYScroll(self.fullHeight-self.max_y)
        else:
            for s in self.selection:
                s.setYOffset(self.y_scroll_real)
    
    def selectAllShowing(self):
        for b in self.selection:
            assert isinstance(b,CheckBox)
            b.is_checked = True

    def deselectAllShowing(self):
        for b in self.selection:
            assert isinstance(b,CheckBox)
            b.is_checked = False

    def toggleAllShowing(self):
        for b in self.selection:
            assert isinstance(b,CheckBox)
            b.toggle()

    def refineResults(self,songs:list[Song]):
        self.songs_displayed = songs
        self.recalculateSelection()

class PauseButton(ButtonSwitch):
    def __init__(self,pos:tuple[int,int]):
        size = 19
        super().__init__((pos[0] ,pos[1]),(size*2,size*2),[UnPaused,Paused],1)  
        self.state:int

    def update(self,input:Input):
        if not MusicPlayer.songLoaded: return
        if MusicPlayer.paused != self.state:
            self.state = MusicPlayer.paused
        mpos,mb1,KDQueue= input.mpos,input.mb1d,input.KDQueue
        if input.consumeKeys(*keybinds.getActionKeybinds('Pause')) or (self.rect.collidepoint(mpos) and mb1 and isInsideCircle(mpos[0],mpos[1],self.rect.centerx,self.rect.centery,20)):
            next_state = (self.state + 1) % len(self.states)
            if next_state == 0:
                MusicPlayer.unpause()
            else:
                MusicPlayer.pause()

    def draw(self,surf:Surface):
        png = self.states[self.state]

        draw.circle(surf,(255,255,255),self.rect.center,self.rect.width/2)
        # gfxdraw.filled_circle(surf,self.rect.centerx,self.rect.centery,self.rect.width//2,(255,255,255))
        # gfxdraw.aacircle(surf,self.rect.centerx,self.rect.centery,self.rect.width//2,(255,255,255))
        surf.blit(png,(self.rect.centerx - png.get_width()//2, self.rect.centery - png.get_height()//2))

class WithAlpha:
    __slots__ = 'obj','order_in_layer','update','surf'
    def __init__(self,obj:HasRect,/,alpha:int=255) -> None:
        self.obj= obj
        
        self.order_in_layer = obj.order_in_layer
        self.surf = Surface(self.obj.rect.size,const.SRCALPHA)
        self.surf.set_alpha(alpha)
        if hasattr(obj,'update'):
            self.update = obj.update #type: ignore

    def setAlpha(self,alpha:int):
        self.surf.set_alpha(alpha)

    @property
    def rect(self):
        return self.obj.rect

    def draw(self,surf:Surface):
        r = self.rect
        x,y = r.topleft
        r.top = 0
        r.left = 0
        self.surf.fill((0,0,0,0))
        self.obj.draw(self.surf)
        r.left = x
        r.top = y
        surf.blit(self.surf,r)

class PlaylistBoxSimple(SelectionBase):
    def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,data:tuple[Playlist,Callable[[Playlist],None]]):
        self.playlist = data[0]
        self.callback = data[1]
        super().__init__(pos,size,color_scheme,None,lambda : self.callback(self.playlist))
        self.txt_surf = getFont(FONT_NAME.ARIAL,14).render(self.playlist.name,True,text_color)

    def draw(self,surf:Surface):
        super().draw(surf)
        surf.blit(self.txt_surf,(self.rect.left+6,self.rect.midleft[1]-self.txt_surf.get_height()//2))

class PlaylistBoxComplicated(SelectionBase):
    def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,data:tuple[Playlist,Callable[[Playlist],None]]):
        self.playlist = data[0]
        self.callback = data[1]
        super().__init__(pos,size,color_scheme,None,lambda : data[1](data[0]))
        self.txt_surf = getFont(FONT_NAME.ARIAL,14).render(self.playlist.name,True,text_color)
    def update(self,input:Input):
        super().update(input)
        if self.state == 1 and input.mb3u:
                l = base_layer.addLayer()
                l.space.addObject(
                    PlaylistOptions(l,self.playlist)
                ) 
    def draw(self,surf:Surface):
        super().draw(surf)
        surf.blit(self.txt_surf,(self.rect.left+6,self.rect.midleft[1]-self.txt_surf.get_height()//2))

class OptionsBase(Space,DrawBase):
    layer:Layer
    child:Optional['OptionsBase']

    __slots__ = 'layer','child'
    def __init__(self,l:Layer,r:Rect):
        super().__init__(r)
        self.layer = l
        self.child = None

    def addChild(self,child:'OptionsBase'):
        '''This method has different nuances than normally creating a <options> this will AUTOMATICALLY add the the child to the parents layer'''
        # if self.child is not None:
        #     self.child.layer.space.removeObject(self.child)
        self.child = child
        # self.layer.space.addObject(child)
  
    def isHovering(self,input:Input) -> bool: 
        if self.rect.collidepoint(input.mpos): return True
        if self.child:
            return self.child.isHovering(input)
        return False

    def removeLayer(self):
        base_layer.removeLayer(self.layer)

    def checkToExit(self,input:Input):
        if input.consumeKey(const.K_ESCAPE):
            return True
        if self.isHovering(input): return False
        if input.mb3d:
            input.mb3d = False
            return True
        if input.mb1d:
            input.mb1d = False
            return True
        if input.wheel:
            return True
        return False

    def update(self,input:Input):
        super().update(input)
        if self.child is not None:
            self.child.update(input)
        if self.checkToExit(input):
            self.removeLayer()
    
    def draw(self,surf:Surface):
        super().draw(surf)
        if self.child is not None: self.child.draw(surf)

class RightClickOptions(OptionsBase):
    def __init__(self,buttons:list[tuple[str,Callable[[],Any]]],color_scheme:ColorScheme,mouse_anchor:tuple[int,int]=(0,0)):
        l = base_layer.addLayer()
        l.space.addObject(self)
        self.font = getFont(FONT_NAME.ARIAL,16)
        margin = 2
        xpadding = 3
        ypadding = 3
        max_width = max(self.font.size(s)[0] for s,c in buttons)
        height = max(self.font.size(s)[1] for s,c in buttons)
        r = Rect(0,0,max_width+margin*2+xpadding*2,len(buttons)*(height+2*(margin+ypadding)))
        mouse = pygame.mouse.get_pos()
        r.left = lerp(mouse[0],mouse[0]-r.width,mouse_anchor[0])
        r.top = lerp(mouse[1],mouse[1]-r.height,mouse_anchor[1])
        DownloadingScreenOptions.makeInBounds(r)
        super().__init__(l,r)
        y = 0
        for button_name,button_callback in buttons:
            self.addObject(
                AddText(
                    Button((margin,y+margin),(max_width+2*xpadding,height+2*ypadding),color_scheme,None,tNF(button_callback,self.removeLayer)),
                    button_name,text_color,self.font
                ),
            )
            y += height+2*margin+2*ypadding

    def update(self,input:Input):
        super().update(input)
        self.mouse_hover = self.rect.collidepoint(input.mpos)
        if self.mouse_hover:
            input.clearALL()

    def draw(self, surf: pygame.Surface):
        draw.rect(surf,bg_color,self.rect,0,2)
        super().draw(surf)

class ForceFocusOptionsBase(OptionsBase):
    __slots__ = 'removed',
    def __init__(self, l, r):
        super().__init__(l, r)
        self.removed = False

    def removeLayer(self):
        self.removed = True
        return super().removeLayer()
    def checkToExit(self, input: Input) -> bool:
        return False

    def update(self,input:Input):
        super().update(input)
        if not self.removed:
            input.clearALL()

class ForceFocusOptionsBaseCanEscape(ForceFocusOptionsBase):
    def checkToExit(self, input: Input) -> bool:
        return input.consumeKey(const.K_ESCAPE)

class ExportTrackerPopup(ForceFocusOptionsBase):
    def __init__(self,l:Layer,songs:dict[Song,bool],path:str,format:exporter.FormatTypes):
        r = Rect(0,0,500,300)
        r.center = l.rect.center
        super().__init__(l,r)
        self.addObject(BackgroundColor())
        self.tracker = self.addObject(AutoSlider((0,0),(r.width,3),ColorLayout((50,150,50),(60,60,60))))
        self.dbgmessage = Text((0,0),'',(255,255,255),getFont(FONT_NAME.ARIAL,13))
        self.addObject(
            Aligner(self.dbgmessage,0.5,0.5)
        )
        self.generator = exporter.exportAsync({song for song,v in songs.items() if v},format,path)


    def update(self, input: Input):
        try:
            dbgmsg = next(self.generator)
            if isinstance(dbgmsg,float):
                self.tracker.setValue(dbgmsg)
            elif isinstance(dbgmsg,str):
                self.dbgmessage.setTextIfNeeded(dbgmsg)
        except StopIteration as err:
            val:bool = err.value
            if val is not None: 
                t = 'Export Success' if val else 'Some Items Failed to Export'
                light_red = (230,100,100)
                white = 255,255,255
                self.addObject(Aligner(Text((0,0),t,white if val else light_red,getFont(FONT_NAME.ARIAL)),0.5,0.3,alignment_y=0.3))
                self.addObject(Aligner(AddText(Button((0,0),(50,50),ColorScheme(80,80,80),None,self.removeLayer),'Done',(255,255,255),getFont(FONT_NAME.ARIAL,16)),0.5,0.8))

        return super().update(input)
     
class SelectionPopup(OptionsBase):
  class Box(SelectionBase):
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme,info:tuple[str,Callable,font.Font]) -> None:
      super().__init__(pos, size, color_scheme, None,lambda : info[1](info[0]))
      font= info[2]
      self.word = font.render(info[0],True,colorUtils.getTextColorFromBackground(self.color_scheme.r,self.color_scheme.g,self.color_scheme.b))
      self.word_rect = self.word.get_rect()
      

    def draw(self, surf: Surface):
      super().draw(surf)
      self.word_rect.center = self.rect.center
      surf.blit(self.word,self.word_rect)
    
  def __init__(self, l: Layer, r: Rect,box_height:int,color_scheme:ColorScheme,options:list[str],callback:Callable[[str],Any],font_:font.Font|None=None,spacing:float = 1.06):
    spx = (box_height*(spacing-1)).__trunc__()
    fullheight = len(options)*(box_height+spx)
    if r.height > fullheight:
        r.height = fullheight
    super().__init__(l, r)
    self.font = font_ or font.SysFont('Arial',int(r.height*0.8))
    self.ret_func = callback
    self.addObjects(
      BackgroundColor(),
      Resizer(
        Selection((0,0),(self.rect.width,box_height),self.rect.height,color_scheme,lambda : [(option,self.returnWithOption,self.font) for option in options],SelectionPopup.Box,spacing),
        '0','0','100%','100%'
      )
    )
  def update(self,input:Input):
    super().update(input)
    if self.isHovering(input):  
        input.clearMouse()


  def checkToExit(self,input:Input):
    return ((input.mb3d or input.mb2d or input.mb1d) and not self.isHovering(input)) or input.consumeKey(const.K_ESCAPE)


  def returnWithOption(self,option:str):
    self.ret_func(option)
    self.removeLayer()

class Dropdown(Button):
  def __init__(self, pos:tuple[int,int],size:tuple[int,int],l:'Layer',max_height:int,color_scheme:ColorScheme,options:list[S],onSelect:Callable[[S],Any]|None = None,font_:font.Font|None=None):
    self.font = font_ or font.SysFont('Arial',int(size[1]*0.8))
    super().__init__(pos, size, color_scheme,self.openSelection)
    onSelect = onSelect or (lambda x:None)
    self.options = options
    self.selected:ObjectValue[str|None] = ObjectValue(None)
    self.max_height = max_height
    self.selected.obj_change_event.register(lambda x: None if x is None else onSelect(x)) #type: ignore
    self.selected.obj_change_event.register(lambda x: None if x is None else toNone(self.setWord(x)))
    self.layer = l
    self._open_selection = False
    self.word_surf = Surface((0,0))
    self.word_rect = Rect(0,0,0,0)
    self.dropdown_spacing = 1.06

  def setWord(self,word:str):
    self.word_surf = self.font.render(word,True,colorUtils.getTextColorFromBackground(*self.color_scheme.color))
    self.word_rect = self.word_surf.get_rect()
    return self
  
  def setDropdownSpacing(self,spacing:float):
      self.dropdown_spacing = spacing
      return self
  
  def setOptions(self,options:list):
    self.options = options
    return self

  def removeOptions(self,options:list,ok_fail:bool=True):
    for option in options:
      try:
        self.options.remove(option)
      except ValueError as err:
        if not ok_fail:
          raise err
    return self
  
  def addOptions(self,options:list,add_duplicates:bool=True):
    if add_duplicates:
      self.options.extend(options)
    else:
      for option in options:
         if options not in self.options:
          self.options.append(option)
    return self

  def openSelection(self):
    self._open_selection = True
    
  def update(self, input: Input):
    return super().update(input)

  def draw(self,surf:Surface):
    if self._open_selection:
      next = self.layer.addLayer()
      r = Rect(surf.get_abs_offset(),(self.rect.width,self.max_height))
      r.move_ip(self.rect.left,3+self.rect.bottom)
      next.space.addObject(
            SelectionPopup(next,r,self.rect.height,self.color_scheme,self.options,self.selected.set,self.font,self.dropdown_spacing), #type: ignore
      )
      self._open_selection = False
    super().draw(surf)
    self.word_rect.center = self.rect.center
    surf.blit(self.word_surf,self.word_rect)

class LoadingScreenWindow(OptionsBase):
    def __init__(self, l: Layer, r: Rect,force_focus:bool,promise:Async.Promise[str]):
        super().__init__(l, r)
        if force_focus:
            self.checkToExit = lambda input: False
        self.force_focus = force_focus
        self.promise = promise
        loading_area_rect = Rect(10,35,r.width-20,20)
        
        self.addObjects(
            BackgroundColor((70,70,70)),
            ColorArea(loading_area_rect.topleft,loading_area_rect.size,dark_primary_color),
            Aligner(Text((0,0),"Loading",text_color,title_font),0.5,0,0.5,0)
        )
        
        loading_area = self.addObject(ColorArea(loading_area_rect.topleft,(1,20),primary_color))
        loading_text = self.addObject(Text((10,65),'',text_color,getFont(FONT_NAME.ARIAL,10)))

        def update(percent:float):
            loading_area.rect.width= (percent*loading_area_rect.width).__ceil__()
        self.promise.percent_done.obj_change_event.register(update)
        self.promise.obj.obj_change_event.register(lambda s: loading_text.setText(s or ''))

    def update(self,input:Input):
        super().update(input)
        if self.promise.percent_done.get() == 1:
            self.removeLayer()
            return
        if self.force_focus:
            input.clearMouse()
            input.clearKeys()

def showLoadingScreenWindow(size:tuple[int,int],force_focus:bool,promise:Async.Promise):
    l = base_layer.addLayer()
    r = Rect((0,0),size)
    r.center = base_layer.rect.center
    l.space.addObject(
        Aligner(
        LoadingScreenWindow(l,r,force_focus,promise),0.5,0.5
        )
    )

class AddPlaylistToPlaylistAskDuplicates(ForceFocusOptionsBase):
    def __init__(self,src:Playlist,dst:Playlist):
        r = Rect(0,0,400,150)
        l = base_layer.addLayer()
        r.center = l.rect.center
        super().__init__(l,r)
        self.layer.space.addObject(self)
        self.addObjects(
            BackgroundColor((20,20,25)),
            Aligner(
                Text((0,3),'Some of these songs are already in the',text_color,font_default),
                0.5,0,0.5,0
            ),
            Aligner(
                Text((0,30),'playlist: '+trimText(dst.name,120,font_default)+'',text_color,font_default),
                0.5,0,0.5,0
            ),
            Aligner(
                AddText(
                    Button(
                        (-2,0),(90,35),light_selection_cs,None,lambda : toNone(database.addPlaylistToPlaylist(src,dst,False),self.removeLayer())
                    ),
                    'Only New',text_color,font_default
                ),
                0.5,0.6,1
            ),
            Aligner(
                AddText(
                    Button(
                        (2,0),(90,35),light_selection_cs,None,lambda : toNone(database.addPlaylistToPlaylist(src,dst,True),self.removeLayer())
                    ),
                    'All Songs',text_color,font_default
                ),
                0.5,0.6,0
            )
        )
    def checkToExit(self, input: Input):
        return ((input.mb1d or input.mb3d) and not self.isHovering(input)) or (const.K_ESCAPE in [e.key for e in input.KDQueue])
    
def addPlaylistToPlaylist(source:Playlist,dest:Playlist):
    if source == dest: return#bruh what
    if set(source.songs).intersection(dest.songs):
        AddPlaylistToPlaylistAskDuplicates(source,dest)
    else:
        database.addPlaylistToPlaylist(source,dest,addDuplicates=True) #there are not duplicates so the reason behind addDuplicates=True is because its simply more efficient than having to check for duplicates when we know there arent any

class PlaylistOptions(OptionsBase):
    def __init__(self,l:Layer,playlist:Playlist) -> None:
        self.playlist = playlist
        r = Rect(pygame.mouse.get_pos(),(120,145))
        size = l.rect.size
        if r.right > size[0]:
            r.right = size[0]
        if r.bottom > size[1]:
            r.bottom = size[1]
        super().__init__(l,r)
        self.addObjects(
            Resizer(
                AddText(
                    Button((5,5),(1,1),light_selection_cs,None,lambda : toNone(self.addChild(PickPlaylistOptions(l,lambda dest: toNone(addPlaylistToPlaylist(playlist,dest),self.removeLayer()),DownloadingScreenOptions.makeInBounds(Rect(self.rect.right,self.rect.top-min(200,len(database.playlists)*30+10),120,min(200,len(database.playlists)*30+10))),primary_layout,(0,0,0))))),
                    'Add To Playlist',text_color,option_font
                ),
               '5','5','-5','35'
            ),
            Resizer(
                AddText(
                    Button((5,5),(1,1),light_selection_cs),
                    'Add To Queue',text_color,option_font
                ),
               '5','40','-5','70'
            ),
            Resizer(
                AddText(
                    Button((5,5),(1,1),light_selection_cs,None, tNF(makePlaylistProtocol,self.removeLayer)),
                    'New Playlist',text_color,option_font
                ),
               '5','75','-5','105'
            ),
            Resizer(
                AddText(
                    Button((5,5),(1,1),light_selection_cs,None, tNF(lambda : deletePlaylistProtocol(self.playlist),self.removeLayer)),
                    'Delete Playlist',warning_color,option_font
                ),
               '5','110','-5','140'
            )
        )

    def update(self,input:Input):
        super().update(input)
        if self.isHovering(input):
            input.mousex = -999
            input.mousey = -999

    def draw(self,surf:Surface):
        draw.rect(surf,(14,14,14),self.rect,0,3)
        super().draw(surf)

class GeneralPlaylistOptions(OptionsBase):
    def __init__(self, l: Layer):
        r = Rect(pygame.mouse.get_pos(),(120,40))
        size = l.rect.size
        if r.right > size[0]:
            r.right = size[0]
        if r.bottom > size[1]:
            r.bottom = size[1]
        super().__init__(l,r)
        self.addObjects(
            Resizer(
                AddText(
                    Button((5,5),(1,1),light_selection_cs,None, tNF(makePlaylistProtocol,self.removeLayer)),
                    'New Playlist',text_color,option_font
                ),
               '5','5','-5','35'
            )
        )
    def update(self, input: Input):
        super().update(input)
        if self.rect.collidepoint(input.mpos):
            input.mousex = -999
            input.mousey = -999

    def draw(self,surf:Surface):
        draw.rect(surf,(14,14,14),self.rect,0,3)
        super().draw(surf)

class PickPlaylistOptions(OptionsBase):
    def __init__(self,l:Layer,callback:Callable[[Playlist],None],rect:Rect,color_layout:ColorLayout,bg_color:ColorType):
        super().__init__(l,rect)
        self.cb = callback
        self.playlist_selection = Selection((5,5),(rect.width-7,30),rect.height-10,selection_cs,lambda : zip(database.playlists,foreverIter(callback)),PlaylistBoxSimple)
        if self.playlist_selection.getScrollPercent() != 1: 
            self.playlist_selection.resize((5,5),(rect.width-25,30),rect.height-10)
        self.scrollbar = Scrollbar((0,0),(7,rect.height-7),1,color_layout).linkToDropdown(self.playlist_selection)
        self.addObjects(
            self.scrollbar,
            self.playlist_selection
        )
        
        self.bg_color = bg_color
    def update(self,input:Input): 
        super().update(input)
        mouse_hover = self.rect.collidepoint(input.mpos)

     
        if mouse_hover:
            input.mousex = -999
            input.mousey = -999
            input.mb1 = False
            input.mb1d = False
            input.mb1u = False
            input.mb2 = False
            input.mb2d = False
            input.mb2u = False
            input.mb3 = False
            input.mb3d = False
            input.mb3u = False

    def draw(self,surf:Surface):
        draw.rect(surf,self.bg_color,self.rect,0,3)
        super().draw(surf)

class ArtistBox(SelectionBase):
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme,data:tuple[ObjectValue[str],font.Font]) -> None:
        super().__init__(pos, size, color_scheme)
        self.newArtistName = data[0]
        self.textBox = InputBoxOneLine((0,0),size,dark_inputbox_cl,self.newArtistName.set,data[1]).setText(self.newArtistName.get())
        self.surf = Surface(self.rect.size)

    def onResize(self,newSize:tuple[int,int]):
        self.surf = Surface(self.rect.size)
        self.textBox.rect.size = self.rect.size
        self.textBox.onResize(newSize)

    def update(self,input:Input):
        # self.mhover = self.rect.collidepoint(input.mpos)
        # if not self.mhover and not self.state:
        #     pass
        # elif self.mhover and self.state == 0 :
        #     self.state = 1
        # elif self.state == 1 and not self.mhover:
        #     self.state = 0
        # elif input.mb1d and self.state == 1:
        #     self.state = 2
        #     self.textBox.active = True
        # elif self.state == 2 and not self.mhover and input.mb1d:
        #     self.state = 0

        input.mousex -= self.rect.left
        input.mousey -= self.rect.top
        self.textBox.update(input)
        input.mousex += self.rect.left
        input.mousey += self.rect.top
       
    def draw(self,surf:Surface):
        super().draw(surf)
        self.textBox.draw(self.surf)
        surf.blit(self.surf,self.rect)

class EditSongOptions(ForceFocusOptionsBase):
    def __init__(self,layer:Layer,song:Song):
        r = Rect(0,0,550,350)
        self.song = song
        super().__init__(layer,r)
        self.newName = ObjectValue(song.name)
        self.newAlbumName = ObjectValue(song.album)
        self.newArtists = [ObjectValue(artist) for artist in song.artists]
        self.newLanguage = ObjectValue(song.language)
        self.newRating = ObjectValue(song.rating)
        
        self.addObjects(
            BackgroundColor(),
            #Top Bar
            Resizer(
                ColorArea((0,0),(0,30),dark_primary_color),
                '0','0','100%','30'
            ),
            Resizer(
                ColorArea((0,30),(0,0),bg_color),
                '0','30','100%','~+30'
            ),
            # Aligner(ColorArea((0,0),(0,2)),0,1,0,1),
            # Aligner(ColorArea((0,0),(2,0)),1,0,1,0),

            Text((5,3),'Edit Song',text_color,font_default),
            Aligner(AddImage(Button((-2,2),(50,28),exit_button_cs.withBGColor(dark_primary_color),None,self.removeLayer),Exit),1,0,1,0),

            #Song Specific UI
            Aligner(Text((10,40),'Name:',text_color,settings_button_font),0,.2,0,0),
            Aligner(Text((10,40),'Album:',text_color,settings_button_font),0,.35,0,0),
            Aligner(Text((10,40),'Languange:',text_color,settings_button_font),0,.5,0,0),
            Aligner(Text((10,40),'Rating:',text_color,settings_button_font),0,.65,0,0),
        )
        title = Text((0,33),song.name,text_color,title_font)
        album_title = Text((0,33+title_font.get_height()),song.album,dim_text_color,subtitle_font)
        artists_title = Text((0,33+title_font.get_height()+subtitle_font.get_height()-4),', '.join(song.artists),dim_text_color,subtitle_font)
        self.newName.obj_change_event.register(title.setTextIfNeeded)
        self.newAlbumName.obj_change_event.register(album_title.setTextIfNeeded)
        self.addObjects(
            Aligner(title,0.5,0,0.5,0),
            Aligner(album_title,0.5,0,0.5,0),
            Aligner(artists_title,0.5,0,0.5,0)
        )
        self.addObjects(
            Resizer(InputBoxOneLine((63,50),(130,25),dark_inputbox_cl,self.newName.set,settings_button_font).setMaxChars(100).setText(self.newName.get()),'63','40+20%','50%-5','~+25'),
            Resizer(InputBoxOneLine((67,50),(130,25),dark_inputbox_cl,self.newAlbumName.set,settings_button_font).setMaxChars(100).setText(self.newAlbumName.get()),'67','40+35%','50%-5','~+25'),
            Resizer(InputBoxOneLine((100,50),(130,25),dark_inputbox_cl,self.newLanguage.set,settings_button_font).setMaxChars(50).setText(self.newLanguage.get()),'100','39+50%','50%-5','~+25'),
            Resizer(InputBoxOneLine((66,50),(140,25),dark_inputbox_cl,self.newRating.set,settings_button_font).setMaxChars(100).setText(self.newRating.get()),'66','40+65%','50%-5','~+25')
        )
    

        artist_list = Selection((0,0),(1,20),1,selection_cs,lambda : zip(self.newArtists,foreverIter(settings_button_font)),ArtistBox,1.1)
        add_artist = Button((0,0),(0,0),settings_button_cs,None,lambda : toNone(self.newArtists.append(ObjectValue('')),artist_list.recalculateSelection()))
        remove_artist = Button((0,0),(0,0),settings_button_cs,None,lambda : toNone([self.newArtists.pop(a) for a in range(len(self.newArtists)) if artist_list.selection[a].textBox.active] or (self.newArtists.pop() if self.newArtists else None),artist_list.recalculateSelection())) #type: ignore
        self.addObjects(
            Resizer(ColorArea((0,0),(1,1),selection_cs.getIdle()),'5+50%','40+20%','100%-10','40+65%'),
            Resizer(artist_list,'5+50%','40+20%','100%-10','40+65%'),
            AddText(Resizer(add_artist,'5+50%','40+65%','75%','~+25'),'Add Artist',text_color,subtitle_font),
            AddText(Resizer(remove_artist,'75%','40+65%','100%-10','~+25'),'Remove Artist',text_color,subtitle_font)
        )
        
        self.addObjects(
            Aligner(AddText(Button((-2,-35),(60,24),ColorScheme(100,200,100),None,self.onDone),'Done',text_color,option_font),.5,1,1,0.5),
            Aligner(AddText(Button((2,-35),(60,24),ColorScheme(200,100,100),None,self.removeLayer),'Cancel',text_color,option_font),.5,1,0,0.5)
        )

    def onDone(self):
        database.replaceSong(self.song,self.makeSong())
        self.removeLayer()
             
    def makeSong(self):
        s = Song()
        s.name = self.newName.get()
        s.album = self.newAlbumName.get()
        s.rating = self.newRating.get()
        s.language = self.newLanguage.get()
        s.artists = [a.get() for a in self.newArtists]
        s.length_seconds = self.song.length_seconds
        s.size_bytes = self.song.size_bytes
        s.file_extension = self.song.file_extension
        s.bit_rate_kbps = self.song.bit_rate_kbps
        s.release_date = self.song.release_date
        s.genre = self.song.genre
        s.explicit = self.song.explicit
        s.track_number = self.song.track_number
        s._fileName = self.song._fileName
        return s

    def onResize(self,newSize:tuple[int,int]):
        self.rect.center = newSize[0]//2,newSize[1]//2

class SongCreditsOptions(OptionsBase):
    @classmethod
    def ofSong(cls,song:Song):
        i  = 70
        r = Rect(0,0,3*i,3*i)
        new_layer = base_layer.addLayer()
        return new_layer.space.addObject(Aligner(cls(new_layer,r,song),0.5,0.5))

    def __init__(self,l:Layer,r:Rect,song:Song):
        super().__init__(l,r)
        self.song = song
        self.addObjects(
            BackgroundColor(),
            Aligner(a:=Text((0,10),song.name,(255,255,255),title_font),0.5,0,0.5,0),
            Aligner(b:=Text((0,title_font.get_height()+10),song.album,(160,160,160),subtitle_font),0.5,0,0.5,0),
            Aligner(c:=Text((0,title_font.get_height()+15+subtitle_font.get_height()),'Length: '+formatTime2(song.length_seconds),(255,255,255),subtitle_font),0.5,0,0.5,0),
            Aligner(d:=Text((0,5),'Artists',(230,230,230),subtitle_font),0.5,0.5),
            Aligner(e:=Text((0,subtitle_font.get_height()+5),formatArtists(tuple(song.artists)),(220,220,220),getFont(FONT_NAME.OPEN_SANS,15)),0.5,0.5)
        )
        max_width = max(a.rect.width,b.rect.width,c.rect.width,d.rect.width,e.rect.width)+16
        self.on_rect_change_event = Event()
        if max_width > self.rect.width:
            self.rect.width = max_width
            self.on_rect_change_event.fire()

            for obj in self.to_draw:
                if hasattr(obj,'onResize'):
                    obj.onResize(self.rect.size) #type: ignore

    def update(self,input:Input):
        super().update(input)
        input.clearALL()

    def draw(self,surf:Surface):
        super().draw(surf)
        draw.rect(surf,(130,130,130),self.rect,3,3)

class PickPlaylist(Selection):
    def __init__(self,pos:tuple[int,int],size:tuple[int,int],callback:Callable[[Playlist],None],bg_color:ColorType):
        self.cb = callback
        self.rect = Rect(pos,size)
        self.bg_color = bg_color
        super().__init__((5,5),(self.rect.width-10,30),self.rect.height-10,selection_cs,lambda : zip(database.playlists,foreverIter(callback)),PlaylistBoxComplicated)
        database.playlists_changed_event.register(self.recalculateSelection)

    def update(self,input:Input):
        super().update(input)
        if input.mb3d and not self.selection and self.mhover:
            l = base_layer.addLayer()
            l.space.addObject(
                # Aligner(
                    GeneralPlaylistOptions(l)
                    # ,0.5,0.5
                # )
            )
        
    def elementResizeHook(self, element: SelectionProtocol):
        element.rect.top += 2
        element.rect.centerx = self.rect.centerx


    def recalculateSelection(self):
        super().recalculateSelection()
        for s in self.selection: # center all the buttons
            self.elementResizeHook(s)

    def draw(self,surf:Surface):
        draw.rect(surf,self.bg_color,self.rect,0,3)
        super().draw(surf)

class SongOptions(OptionsBase):
    @staticmethod
    def inBounds(rect:Rect,layer:Layer):
        w,h = layer.rect.size
        return 0<=rect.top and rect.bottom < h and 0<=rect.left and rect.right < w

    def __init__(self,current_layer:Layer,song:Song) -> None:
        #buttons to draw, add to playlist
        #add to queue
        #view song credits
        self.song = song
        r = Rect(pygame.mouse.get_pos(),(150,215))
        size = current_layer.rect.size
        if r.right > size[0]:
            r.right = size[0]
        if r.bottom > size[1]:
            r.bottom = size[1]
        super().__init__(current_layer,r)
        self.addObjects(
            AddText(
                Button((5,5),(self.rect.width-10,30),light_selection_cs,None,self.addToPlaylist),
                'Add To Playlist',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,40),(self.rect.width-10,30),light_selection_cs,lambda : MusicPlayer.songQueue.queued.append(self.song),self.removeLayer),
                'Add To Queue',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,75),(self.rect.width-10,30),light_selection_cs,self.viewSongCredits),
                'View Credits',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,110),(self.rect.width-10,30),light_selection_cs,None,tNF(self.removeLayer,lambda : (l:=base_layer.addLayer()).space.addObject(Aligner(EditSongOptions(l,self.song),0.5,0.5)))),
                'Edit Song',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
              AddText(
                Button((5,145),(self.rect.width-10,30),light_selection_cs,None,(lambda : toNone(self.export(),self.removeLayer()))),
                'Export Song',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,180),(self.rect.width-10,30),light_selection_cs,None,lambda : toNone((database.removeSong(self.song) if MusicPlayer.songQueue.current is not self.song else (MusicPlayer.clearCurrentSong(),database.removeSong(self.song)) ),self.removeLayer())),
                'Delete Song',warning_color,getFont(FONT_NAME.ARIAL,14)
            )
        )
        self.surf = Surface(self.rect.size)
        self.surf.set_colorkey((0,0,1))
        self.surf.fill((0,0,1))
        draw.rect(self.surf,(0,0,0),((0,0),self.rect.size),0,3)

    def addToPlaylist(self):
        rect = Rect(self.rect.topright,(120,min(200,len(database.playlists)*30+10)))
        rect.bottom = self.rect.top
        if rect.right > self.layer.rect.size[0]:
            rect.right = self.rect.left
        if rect.top < 0:
            rect.top = 0
            
        self.child = PickPlaylistOptions(self.layer,lambda p : toNone(database.addSongToPlaylist(p,self.song),base_layer.removeLayer(self.layer)),rect,primary_layout,(0,0,0))
        # self.layer.space.addObject(self.child)

    def viewSongCredits(self):
        base_layer.removeLayer(self.layer)
        SongCreditsOptions.ofSong(self.song)

    def export(self):
        if self.song not in database.songs:
            logger.log('Attempt to export a song which does not exist in database! Song:',self.song)
            return 
        export_checked.clear()
        export_checked[self.song] = True
        export_dropdown.recalculateSelection()
        y = database.songs.index(self.song)


        export_dropdown.setYScroll(export_dropdown.selectionSize[1]*y)
        base_layer.space.setActive('export')

    def update(self,input:Input):
        super().update(input)
        self.mouse_hover = self.rect.collidepoint(input.mpos)
        if input.mb1d and self.mouse_hover:
            input.mb1d = False
        if self.mouse_hover:
            input.clearMouse()

    def draw(self,surf:Surface):
        draw.rect(surf,(0,0,0),self.rect,0,2)
        super().draw(surf)

class PlaylistSongOptions(OptionsBase):
    def __init__(self, l: Layer, song: Song, song_index: int, playlist:Playlist):
        r = Rect(pygame.mouse.get_pos(),(150,215))
        DownloadingScreenOptions.makeInBounds(r)
        super().__init__(l, r)
        self.song = song
        self.song_index = song_index
        self.playlist = playlist

        self.addObjects(
            AddText(
                Button((5,5),(self.rect.width-10,30),light_selection_cs,None,self.addToPlaylist),
                'Add To Playlist',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,40),(self.rect.width-10,30),light_selection_cs,lambda : MusicPlayer.songQueue.queued.append(self.song),self.removeLayer),
                'Add To Queue',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,75),(self.rect.width-10,30),light_selection_cs,self.viewSongCredits),
                'View Credits',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,110),(self.rect.width-10,30),light_selection_cs,None,tNF(self.removeLayer,lambda : (l:=base_layer.addLayer()).space.addObject(EditSongOptions(l,self.song)))),
                'Edit Song',text_color,getFont(FONT_NAME.ARIAL,14)
            ),
            AddText(
                Button((5,145),(self.rect.width-10,30),light_selection_cs,None,lambda : toNone(database.removeIndexSongFromPlaylist(self.playlist,song_index),self.removeLayer())),
                'Remove From Playlist',warning_color,getFont(FONT_NAME.ARIAL,13)
            ),
            AddText(
                Button((5,180),(self.rect.width-10,30),light_selection_cs,None,lambda : toNone((database.removeSong(self.song) if MusicPlayer.songQueue.current is not self.song else (MusicPlayer.clearCurrentSong(),database.removeSong(self.song)) ),self.removeLayer())),
                'Delete Song',warning_color,getFont(FONT_NAME.ARIAL,14)
            )
        )

        
    def draw(self,surf:Surface):
        draw.rect(surf,(0,0,0),self.rect,0,2)
        super().draw(surf)

    def addToPlaylist(self):
        rect = Rect(self.rect.topright,(120,min(200,len(database.playlists)*30+10)))
        rect.bottom = self.rect.top
        if rect.right > self.layer.rect.size[0]:
            rect.right = self.rect.left
        if rect.top < 0:
            rect.top = 0
            
        self.child = PickPlaylistOptions(self.layer,lambda p : toNone(database.addSongToPlaylist(p,self.song),base_layer.removeLayer(self.layer)),rect,primary_layout,(0,0,0))
        # self.layer.space.addObject(self.child)

    def viewSongCredits(self):
        base_layer.removeLayer(self.layer)
        SongCreditsOptions.ofSong(self.song)

class VolumeIcon(Button):
    def __init__(self,pos:tuple[int,int]):
        super().__init__(pos,(30,30),selection_cs)
        
    def draw(self,surf:Surface):
        v = MusicPlayer.get_volume()
        if v == 0:
            surf.blit(AudioMute,self.rect)
        elif v < .30:
            surf.blit(AudioLowVolume,self.rect)
        elif v < .60:
            surf.blit(AudioMediumVolume,self.rect)
        else:
            surf.blit(AudioHighVolume,self.rect)

class SongBox(SelectionBase):
    song_name_font = getFont(FONT_NAME.OPEN_SANS,15)
    artists_name_font = getFont(FONT_NAME.OPEN_SANS,13)
    album_name_font = getFont(FONT_NAME.OPEN_SANS,13)
    more_options_font = getFont(FONT_NAME.YOUTUBE_EXTRA_BOLD,15)
    @Tracer().traceas('SongBox')
    def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,song:Song) -> None:
        super().__init__(pos,size,color_scheme)
        MIN_WIDTH_TO_DISPLAY_ALBUM = 500
       
        self.song = song
        self.pad_left = 50
        self.pad_right = 10
        self.more_options_width = getCharWidth('. . .',self.more_options_font) + 10 
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            max_length = self.rect.width/2 - self.pad_left - 10 # of song_name and artists_name
        else:
            max_length = self.rect.width - self.pad_left - 10 - self.more_options_width
        
        self.middle_max_length = self.rect.width//2 - self.more_options_width if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM else 0

        song_name = trimText(self.song.name,max_length,self.song_name_font)
        self.song_name_surf = self.song_name_font.render(song_name,True,'white')
        
        artist_name = trimText(', '.join(song.artists),max_length,self.artists_name_font)
        self.artists_name_surf = self.artists_name_font.render(artist_name,True,(200,200,200))
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            song_album = trimText(song.album,self.middle_max_length,self.album_name_font)
            self.album_name_surf = self.album_name_font.render(song_album,True,(200,200,200))
        else:
            self.album_name_surf = None
        self.more_options_surf = self.more_options_font.render('. . .',True,(255,255,255))        
        self.mouse_hover = False

        self.selected = False
        self.last_lc_time = 0.0

    @Tracer().traceas('SongBox.onResize')
    def onResize(self,size:tuple[int,int]):
        MIN_WIDTH_TO_DISPLAY_ALBUM = 500
        self.setYOffset(self.yoffset)
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            max_length = self.rect.width/2 - self.pad_left - 10 # of song_name and artists_name
        else:
            max_length = self.rect.width - self.pad_left - 10 - self.more_options_width
        
        self.middle_max_length = self.rect.width//2 - self.more_options_width if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM else 0

        song_name = trimText(self.song.name,max_length,self.song_name_font)
        self.song_name_surf = self.song_name_font.render(song_name,True,text_color)
        
        artist_name = trimText(', '.join(self.song.artists),max_length,self.artists_name_font)
        self.artists_name_surf = self.artists_name_font.render(artist_name,True,(200,200,200))
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            song_album = trimText(self.song.album,self.middle_max_length,self.album_name_font)
            self.album_name_surf = self.album_name_font.render(song_album,True,(200,200,200))
        else:
            self.album_name_surf = None
        self.more_options_surf = self.more_options_font.render('. . .',True,text_color)        
        self.mouse_hover = False

        self.selected = False
        self.last_lc_time = 0.0

    def setToUp(self):
        self.mouse_hover = False
        return super().setToUp()

    def update(self, input: Input):
        mb1d = input.mb1d
        mb1u = input.mb1u
        super().update(input)
        input.mb1d = mb1d
        input.mb1u = mb1u
        if self.rect.collidepoint(input.mpos):
            self.mouse_hover = True
            if mb1u:
                self.selected = True
            if mb1d:
                if input.mousex - self.rect.left < 50:
                    #we hit the play button
                    if MusicPlayer.songQueue.current is self.song:
                        #Pause/Unpause song
                        MusicPlayer.setPaused(not MusicPlayer.getPaused())
                    else:
                        MusicPlayer.playSongAbsolute(self.song)
                elif self.rect.right - input.mousex < 50:
                    #we hit the more options
                    self.selected = True
                    l = base_layer.addLayer()
                    l.space.addObject(
                        SongOptions(l,self.song)
                    )
                else:
                    if pygame.time.get_ticks()/1000 - self.last_lc_time <= DOUBLE_CLICK_THRESHOLD:
                        MusicPlayer.playSongAbsolute(self.song)
                    self.last_lc_time = pygame.time.get_ticks()/1000            
            if input.mb3u:
                self.selected = True
                l = base_layer.addLayer()
                l.space.addObject(
                    SongOptions(l,self.song)
                )
                input.mb3u = False
        else:
            self.mouse_hover = False
            if input.mb1u:
                self.selected = False
            if input.mb3d:
                self.selected = False
      
    def draw(self,surf:Surface):
        cs = self.color_scheme
        color = [cs.getInactive,cs.getIdle,cs.getActive][max(self.mouse_hover,self.selected*2)]() #TODO find out if its worth it to cache the results instead of calling them everytime
        r = self.rect
        draw.rect(surf,color,r)

        surf.blit(self.song_name_surf,(r.left+self.pad_left,r.centery-self.song_name_surf.get_height()+1))
        surf.blit(self.artists_name_surf,(r.left+self.pad_left,r.centery-1))
        if self.state == 1 or self.state == 2 or self.selected:
            surf.blit(self.more_options_surf,(r.right-self.more_options_width,r.centery-self.more_options_surf.get_height()//2-6))
            if MusicPlayer.songQueue.current is self.song:
                surf.blit(UnPaused,(r.left + 20,r.centery - UnPaused.get_height()//2))
            else:
                surf.blit(Paused,(r.left + 20,r.centery - Paused.get_height()//2))
        if self.album_name_surf:
            surf.blit(self.album_name_surf,(r.centerx,r.centery-self.album_name_surf.get_height()//2))

class PlaylistBox(SelectionBase):
    song_name_font = getFont(FONT_NAME.OPEN_SANS,15)
    artists_name_font = getFont(FONT_NAME.OPEN_SANS,13)
    album_name_font = getFont(FONT_NAME.OPEN_SANS,13)
    more_options_font = getFont(FONT_NAME.YOUTUBE_EXTRA_BOLD,15)

    def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,data:tuple[tuple[Song,T],Callable[[Song,T],Any],Optional[Callable[[Song,T],Any]]]) -> None:
        super().__init__(pos,size,color_scheme)
        MIN_WIDTH_TO_DISPLAY_ALBUM = 500
        song = data[0][0]
        self.data = data
        self.func = data[1]
        self.rfunc = data[2] or (lambda _,_2: None)
        self.song = song
        self.pad_left = 50
        self.pad_right = 10
        self.more_options_width = getCharWidth('. . .',self.more_options_font) + 10 
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            max_length = self.rect.width/2 - self.pad_left - 10 # of song_name and artists_name
        else:
            max_length = self.rect.width - self.pad_left - 10 - self.more_options_width
        self.middle_max_length = self.rect.width//2 - self.more_options_width if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM else 0

        song_name = trimText(song.name,max_length,self.song_name_font)
        self.song_name_surf = self.song_name_font.render(song_name,True,'white')
        
        artist_name = trimText(', '.join(song.artists),max_length,self.artists_name_font)
        self.artists_name_surf = self.artists_name_font.render(artist_name,True,(200,200,200))
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            song_album = trimText(song.album,self.middle_max_length,self.album_name_font)
            self.album_name_surf = self.album_name_font.render(song_album,True,(200,200,200))
        else:
            self.album_name_surf = None
        self.more_options_surf = self.more_options_font.render('. . .',True,(255,255,255))        
        self.mouse_hover = False

        self.selected = False
        self.last_lc_time = 0.0

    def onResize(self,size:tuple[int,int]):
        MIN_WIDTH_TO_DISPLAY_ALBUM = 500
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            max_length = self.rect.width/2 - self.pad_left - 10 # of song_name and artists_name
        else:
            max_length = self.rect.width - self.pad_left - 10 - self.more_options_width
        self.middle_max_length = self.rect.width//2 - self.more_options_width if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM else 0

        song_name = trimText(self.song.name,max_length,self.song_name_font)
        self.song_name_surf = self.song_name_font.render(song_name,True,'white')
        
        artist_name = trimText(', '.join(self.song.artists),max_length,self.artists_name_font)
        self.artists_name_surf = self.artists_name_font.render(artist_name,True,(200,200,200))
        if self.rect.width > MIN_WIDTH_TO_DISPLAY_ALBUM:
            song_album = trimText(self.song.album,self.middle_max_length,self.album_name_font)
            self.album_name_surf = self.album_name_font.render(song_album,True,(200,200,200))
        else:
            self.album_name_surf = None
        self.mouse_hover = False

        self.selected = False
        self.last_lc_time = 0.0

    def setToUp(self):
        self.mouse_hover = False
        return super().setToUp()

    def update(self, input: Input):
        mb1d,mb1u = input.mb1d,input.mb1u
        super().update(input)
        if self.rect.collidepoint(input.mpos):
            self.mouse_hover = True
            if mb1u:
                self.selected = True
            if  mb1d:
                if input.mousex - self.rect.left < 50:
                    #we hit the play button
                    self.func(*self.data[0]) 
                elif self.rect.right - input.mousex < 50:
                    #we hit the more options
                    self.selected = True
                    self.rfunc(*self.data[0])
                else:
                    if pygame.time.get_ticks()/1000 - self.last_lc_time <= DOUBLE_CLICK_THRESHOLD:
                        self.func(*self.data[0]) 
                    self.last_lc_time = pygame.time.get_ticks()            
            if input.mb3u:
                self.selected = True
                self.rfunc(*self.data[0])
                input.mb3u = False
        else:
            self.mouse_hover = False
            if mb1u:
                self.selected = False
            if input.mb3d:
                self.selected = False
      
    def draw(self,surf:Surface):
        cs = self.color_scheme
        color = [cs.getInactive,cs.getIdle,cs.getActive][max(self.mouse_hover,self.selected*2)]() #TODO find out if its worth it to cache the results instead of calling them everytime
        draw.rect(surf,color,self.rect)

        surf.blit(self.song_name_surf,   (self.rect.left+self.pad_left,self.rect.midleft[1]-self.song_name_surf.get_height()+1))
        surf.blit(self.artists_name_surf,(self.rect.left+self.pad_left,self.rect.midleft[1]-1))
        if self.state == 1 or self.state == 2 or self.selected:
            surf.blit(self.more_options_surf,(self.rect.right-self.more_options_width,self.rect.midleft[1]-self.more_options_surf.get_height()//2-6))
            if MusicPlayer.songQueue.current is self.song:
                surf.blit(UnPaused,(self.rect.left + 20,self.rect.midleft[1] - UnPaused.get_height()//2))
            else:
                surf.blit(Paused,(self.rect.left + 20,self.rect.midleft[1] - Paused.get_height()//2))
        if self.album_name_surf:
            surf.blit(self.album_name_surf,  (self.rect.midbottom[0],self.rect.midleft[1]-self.album_name_surf.get_height()/2))

class AllSongsList(Selection):
    sorting:Literal['none','name','artist','album']
    songs:list[Song]
    def __init__(self, top,horizontal_pad:int,selection_height:int,func:Callable[[Song],Any]):
        self.top = top
        self.horizontal_pad = horizontal_pad
        self.selection_height = selection_height
        self.sorting = 'none'
        self.songs = database.songs.copy()
        self.func = func
        self.tempfunc:Optional[Callable] = None
        database.songs_changed_event.register(self.recalculateAllSongs)

        super().__init__((0,0), (0,0),1,selection_cs,lambda : self.songs,SongBox,1)
        self.recalculateAllSongs()

    @Tracer().traceas('AllSongsList')
    def onResize(self,size:tuple[int,int]):
        selection_size = (size[0]-2*self.horizontal_pad,self.selection_height)
        max_y = size[1] - self.top
        pos = self.horizontal_pad,self.top
        self.resize(pos,selection_size,max_y)

    @Tracer().traceas('AllSongsList.update')
    def update(self, input: Input):
        return super().update(input)
        
    @Tracer().traceas('AllSongsList.draw')
    def draw(self, surf: Surface):
        return super().draw(surf)
    def playSortedSong(self,index:int):
        if self.tempfunc:
            self.tempfunc(self.songs[index])
            self.tempfunc = None
        else:
            self.func(self.songs[index])

    def recalculateAllSongs(self):
        self.songs = database.songs.copy() #update catalog of songs
        if self.sorting == 'none': pass
        elif self.sorting == 'name':
            self.songs.sort(key=lambda x:x.name)
        elif self.sorting == 'artist':
            self.songs.sort(key=lambda x:x.artists[0] if x.artists else '')
        elif self.sorting == 'album':
            self.songs.sort(key=lambda x:x.album)
        self.recalculateSelection()

    def setSorting(self,sortBy:Literal['none','name','artist','album']):
        self.sorting = sortBy

def ease(x):
    if x > 1: return 1
    elif x < 0: return 0
    return x*x*(3-2*x)

class ResizingImage:
    def __init__(self,obj:HasRect,image:Surface|Callable[[int,int],Surface]):
        self.obj = obj
        if callable(image):
            self.func = image
            image = image(obj.rect.width,obj.rect.height)
        else:
            self.func = None
        self.image = image
        self.surf = image
        self.order_in_layer = obj.order_in_layer
        if hasattr(obj,'update'):
            self.update = obj.update#type: ignore
    @property
    def rect(self):
        return self.obj.rect    
    
    def draw(self,surf:Surface):
        self.obj.draw(surf)
        size = self.obj.rect.size
        if self.surf.get_size() != size:
            if self.func is None:
                self.surf = pygame.transform.smoothscale(self.image,size) 
            else:
                self.surf = self.func(size[0],size[1])
        surf.blit(self.surf,self.obj.rect.topleft)

class LocalSongsMenu(Layer):
    class Title(DrawBase):
        def __init__(self,font:font.Font):
            self.text_color = primary_color
            self.surf_cache:dict[int,Surface] = {}
            self.font = font
            self.rect = Rect()
            self.on_rect_change_event:Event[[]] = Event()
            self.active = True
            self.setText('Local Songs')
        
        def setText(self,newText:str):
            self.text = newText
            self.surf_cache.clear()
            new_surf = self.font.render(self.text,True,self.text_color)
            self.surf_cache[self.font.point_size] = new_surf
            self.surf = new_surf
            self.rect.width = self.surf.get_width()
            self.rect.height = self.surf.get_height()
            self.on_rect_change_event.fire()
        
        def setFontHeight(self,height:int):
            self.font.set_point_size(height)
            if height not in self.surf_cache:
                self.surf_cache[height] = self.font.render(self.text,True,self.text_color)
            self.surf = self.surf_cache[height]
            self.rect.width = self.surf.get_width()
            self.rect.height = self.surf.get_height()

        def onResize(self,newSize:tuple[int,int]):
            #new size is the new size of the container we are in
            new_width,new_height = newSize
            font_size = int(new_height*0.7)
            self.setFontHeight(font_size)
        def draw(self,surf:Surface):
            if self.active:
                surf.blit(self.surf,self.rect)
    class SearchBar(InputBoxOneLine):
        def __init__(self,pos:tuple[int,int],size:tuple[int,int],songlist:AllSongsList):
            def save(query):
                if query:
                    songlist.songs = database.search(query)
                else:
                    songlist.songs = database.songs.copy()
                songlist.recalculateSelection()

            super().__init__(pos,size,primary_layout,save,getNewFont(FONT_NAME.YOUTUBE_REGULAR,20))
            self.roll_speed = 1.0 #seconds to fully expand
            self.roll_ = 0 #[0,1]
            self.roll_color = (80,80,80)
            self.roll_target = 0


        def roll(self):
            self.roll_target = 1

        def unroll(self):
            self.roll_target = 0

        def update(self,input:Input):
            if self.roll_target != self.roll_:
                if (self.roll_ - self.roll_target).__abs__() <= .01:
                    self.roll_ = self.roll_target
                else:
                    self.roll_ += (self.roll_target - self.roll_) * min(1/5,1)
            if self.roll_ == 0:
                return

            super().update(input)
        
        def redrawSurf(self):
            self.surf.fill((0,0,0,0))
            self.text_surf = self.font.render(self.text,True,self.color_layout.foreground)
            if self.font.size(self.text)[0] < self.rect.width:
                self.text_surf_left_shift = 0
            self.cursor_visible_x = self.font.size(self.text[:self.cursor_position])[0]
            cursor_x_pos = self.cursor_visible_x - self.text_surf_left_shift
            if cursor_x_pos > self.rect.width-3:
                self.text_surf_left_shift += cursor_x_pos - self.rect.width + 3
            elif cursor_x_pos < 0:
                self.text_surf_left_shift += cursor_x_pos  
            self.surf.blit(self.text_surf,(-self.text_surf_left_shift,(self.rect.height - self.font.get_height())*self.text_y_alignment))
        def draw(self,surf:Surface):
            if self.roll_:
                draw.rect(surf,self.roll_color,(self.rect.left-2,self.rect.top,self.rect.width*self.roll_*1.12,self.rect.height),0,1)
                surf.blit(self.surf,self.rect)
                if not self.active: return
                t = int(time.monotonic() - self.cursor_time)
                if not t%2:
                    draw.rect(surf,self.color_layout.foreground,(self.cursor_visible_x - self.text_surf_left_shift+self.rect.left,self.rect.top +(self.rect.height - self.font.get_height())*self.text_y_alignment,2,self.font.get_height()))
    class ExitSearch(Button):
        def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme, onDownFunction: Callable[[], None] | None = None, onUpFunction: Callable[[], None] | None = None):
            super().__init__(pos,size,color_scheme,onDownFunction,onUpFunction)
            self.active = False
        def draw(self,surf:Surface):
            if not self.active: return
            if self.state == 0:
                color = self.color_scheme.getInactive()
            elif self.state == 1:
                color = self.color_scheme.getIdle()
            else:
                color = self.color_scheme.getActive()
            draw.aaline(surf,color,self.rect.topleft,self.rect.bottomright,max(1,self.rect.height//10))
            draw.aaline(surf,color,self.rect.bottomleft,self.rect.topright,max(1,self.rect.height//10))
    def __init__(self,size:tuple[int,int]):
        super().__init__(size)
        self.songlist = AllSongsList(5,5,50,MusicPlayer.playSongAbsolute)
        self.last_yscroll=self.songlist.y_scroll_real
        self.yscroll = 0
        self.yscroll_target = 0
        self.header_size = 70
        self.songlist_scroll = 0
        self.is_searching = False

        self.menu_header_title = Aligner(
            LocalSongsMenu.Title(getNewFont(FONT_NAME.YOUTUBE_REGULAR,20)), 0.5,0.5
        )

        self.menu_header_search = WithRespectTo(
            Resizer(
                ResizingImage(
                    Button((-3,2),(50,50),selection_cs,self.onSearchPress),
                    Search
                ),
                '0','0','h*0.7','70%',
            ),
            self.menu_header_title.obj,-0.1,0.5,1,0.5
        )
        self.roller=LocalSongsMenu.SearchBar((7,0),(1,1),self.songlist)
        self.menu_header_searchbox = WithRespectTo(
            Resizer(
                self.roller,
                '0','0','h*4','50%',
            ),            
            self.menu_header_search.obj,1,0.5,0,0.5
        )
        self.exit_searching_button = WithRespectTo(
            Resizer(
                a:=LocalSongsMenu.ExitSearch((2,0),(1,1),primary_cs,None,self.stopSearching),
                '0','0','h*0.3','30%'
            ),
            self.roller,1,0.5,0,0.5
        )

        self.extra_options_button = Resizer(
            ResizingImage(
                Button((0,0),(10,10),selection_cs,lambda : RightClickOptions([
                            ('Export',lambda : base_layer.space.setActive('export')),
                            ('Import',lambda : base_layer.space.setActive('import'))
                        ],light_selection_cs,
                        mouse_anchor=(1,0),
                    ),
                ),
                self.threeDot,
            ),
            '100%-h*0.6-5','15%','100%-5','85%+5'
        )
        self.exit_searching_button_obj = a
        self.header_bg = BackgroundColor()
        self.main_bg = BackgroundColor()
        self.open_search_keybind = KeyBoundFunctionConditional(lambda : not self.is_searching,lambda : self.setSearching(True),keybinds.getActionKeybinds('Start Search'))
        self.close_search_keybind = KeyBoundFunctionConditional(lambda : self.is_searching,self.stopSearching,[(const.K_ESCAPE,0)])
        self.recut(self.header_size)
        self.pwheel = 0


    @cache
    def threeDot(self,width:int,height:int):
        surf = Surface((width,height),const.SRCALPHA)
        r = min((height*0.07),3.5)
        spacing = r*4
        center_y = height//2
        center_x = width//2
        pygame.draw.aacircle(surf,text_color,(center_x,center_y),r)
        pygame.draw.aacircle(surf,text_color,(center_x,center_y-spacing),r)
        pygame.draw.aacircle(surf,text_color,(center_x,center_y+spacing),r)
        return surf

    def stopSearching(self):
        self.setSearching(False)

    def setSearching(self,searching:bool):
        self.is_searching = searching
        self.menu_header_title.obj.active = not searching #type: ignore
        self.yscroll_target = 0
        if searching:
            self.roller.roll()
            self.exit_searching_button_obj.active = True
            self.roller.active = True
        else:
            self.roller.setText('')
            self.roller.unroll()
            self.exit_searching_button_obj.active = False

    @Tracer().traceas('Local Songs Menu')
    def onResize(self, size: tuple[int, int]):
        return super().onResize(size)         
    def onSearchPress(self):
        self.setSearching(True)

    def recut(self,headersize:int):
        new = Space(self.rect.copy())
        header = new.cutTopSpace(headersize)
        header.addObjects(
            # self.header_bg,
            self.menu_header_title,
            self.menu_header_search,
            self.menu_header_searchbox,
            self.exit_searching_button,
            self.open_search_keybind,
            self.close_search_keybind,
            self.extra_options_button
            )
        new.addObjects(
            # self.main_bg,
            self.songlist)
        self.space.wipe()
        self.space = new

        # self.pwheel = 0
        
    def update(self, input: Input):
        mhover = self.rect.collidepoint(input.mpos)
        if mhover:
            yscroll_target = self.yscroll_target + ((input.wheel+self.pwheel) * gui.settings.wheel_sensitivity).__trunc__()
            sfh = self.songlist.fullHeight
            
            full_height = max(0,sfh - self.songlist.max_y + 120)  if sfh > self.songlist.max_y else 0
            if yscroll_target < 0: yscroll_target = 0
            elif yscroll_target > full_height: yscroll_target = full_height
            self.yscroll_target = yscroll_target
            if input.wheel:
                input.wheel = 0
        self.pwheel = (self.pwheel + input.wheel * 0.4) if input.wheel else 0

        if int(self.yscroll_target) != self.yscroll:
            if (self.yscroll - self.yscroll_target).__abs__() <= 2:
                self.yscroll = int(self.yscroll_target)
            else:
                self.yscroll = gui.utils.utils.expDecay(self.yscroll,self.yscroll_target,1/gui.settings.scroll_smoothing,input.dt)
        if self.is_searching:
            header_size = int((1-ease(self.yscroll/90))*20+50)
        else:
            header_size = int((1-ease(self.yscroll/90))*30+40)

        if header_size != self.header_size:
            self.header_size = header_size
            self.recut(self.header_size)
          
        songlist_scroll = min(max(0,self.yscroll - 110),self.songlist.fullHeight)
        if songlist_scroll != self.songlist_scroll:
            self.songlist_scroll = songlist_scroll
            songlist = self.songlist
            songlist.y_scroll_target = songlist.y_scroll_real = songlist_scroll
            for sel in songlist.selection:
                sel.setYOffset(songlist_scroll)
        return super().update(input)

class SongList2(Selection):
    def __init__(self,pos,size,maxy,color_scheme:ColorScheme,func:Callable[[Song,int],Any],captions:Callable[[],Iterable[tuple[Song,int]]],rightClickOptions:Optional[Callable[[Layer,Song,int],Any]] = None):
        def openOptions(s:Song,i:int):
            if rightClickOptions is None: return
            l = base_layer.addLayer()
            l.space.addObject(rightClickOptions(l,s,i))
        captions2 = lambda : list((x,func,openOptions) for x in captions())
        super().__init__(pos,size,maxy,color_scheme,captions2,PlaylistBox)

class DownloadingScreenOptions(ForceFocusOptionsBase):
    @staticmethod
    def center(r:Rect):
        r.center = base_layer.rect.center
        return r
    @staticmethod
    def makeInBounds(r:Rect):
        br = base_layer.rect
        if r.left < br.left:
            r.left = br.left
        elif r.right > br.right:
            r.right = br.right
        if r.top < br.top:
            r.top = br.top
        elif r.bottom > br.bottom:
            r.bottom = br.bottom
        return r
    def __init__(self, l: Layer, r: Rect,song:Song):
        title_width = title_font.size(song.name)[0]
        if title_width > r.width:
            r.inflate_ip(title_width-r.width,0)
        super().__init__(l,self.makeInBounds(r))
        self.song = song
        self.addObject(BackgroundColor())
        self.addObject(Aligner(Text((0,0),'Downloading Song',text_color,title_font),0.5,0,0.5,0))
        sa = AutoSlider((0,-10),(r.width,3),ColorLayout((50,150,50),(60,60,60)))
        self.addObject(Aligner(sa,0.5,1,0.5,1))
        self.addObject(Aligner(Text((0,title_font.get_height()),song.name,text_color,title_font),0.5,0,0.5,0))
        self.percent_done = ObjectValue(0.0)
        p = Text((0,0),'0%',text_color,settings_button_font)
        self.percent_done.obj_change_event.register(lambda x: p.setTextIfNeeded(f'{round(x*100)}%'))
        self.percent_done.obj_change_event.register(sa.setValue)

        self.speed:ObjectValue[tuple[float,str]] = ObjectValue((0.0,'bps'))
        s = Text((0,0),'0.0 Mbps',text_color,settings_button_font)
        self.speed.obj_change_event.register(lambda x: s.setTextIfNeeded(str(x[0])+' '+x[1]))
        self.size = ObjectValue('')
        si = Text((0,0),'0 B',text_color,settings_button_font)
        self.size.obj_change_event.register(si.setTextIfNeeded)
        self.addObjects(
            Aligner(p,0.2,0.5),Aligner(s,0.5,0.5),Aligner(si,0.8,0.5)
        )
        def onUpdate(percent:float,size:str,speed:tuple[float,str]):
            self.percent_done.set(percent)
            self.size.set(size)
            self.speed.set(speed)

        
        def onDone(path:Optional[str],error:Optional[Exception]):
            if not path and error is not None:
                days = yt_dlp_days_since_update()
                l = base_layer.addLayer()
                l.space.addObject(SAligner(options:=ForceFocusOptionsBase(l,Rect(0,0,500,200)),0.5,0.5))
                header = options.cutTopSpace(25)
                header.addObjects(
                    BackgroundColor(grey_color),
                    Aligner(
                        Text((0,0),"An Error Has Occured",warning_color,font_default),
                        0.5,0,0.5,0
                    ),
                    Aligner(
                        AddText(
                            Button((0,0),(40,30),exit_button_cs,None,tNF(self.removeLayer,options.removeLayer)),
                            'Exit',(0,0,0),settings_button_font,offset_y=-3
                        ),
                        1,0,1,0
                    )
                )
                options.addObjects(
                    BackgroundColor(dark_primary_color),
                    Text((5,5),"Updating Dependency: YT-DLP may resolve the issue.",text_color,settings_button_font),
                    AddText(Button((5,34),(70,25),light_selection_cs,None,lambda: toNone(self.removeLayer(),options.removeLayer(),updateYTDLP(base_layer))),'Update',text_color,settings_button_font),
                )
                if days <= 2:
                    options.addObjects(
                        Text((5,70),'Please contact the developers!',text_color,settings_button_font),
                        Text((5,91),'Yt-dlp was recently updated, updating it will likely not',text_color,settings_button_font),
                        Text((5,91-70+91),' fix the issue, however you are free to try!',text_color,settings_button_font),
                    )
                return
            elif not path:
                return logger.log("[Unreachable code path detected] function <onDone> in \"UIFramwork.py\"")
            newFilename = '['+path.split('[')[-1]
            from . import importer
            file_meta = Async.run(importer.getAudioMetaFromFileAsync(path))
            os.replace(path,MUSIC_PATH+newFilename)
            s = Song()
            s.name = self.song.name
            s.album = self.song.album or ''
            s.artists = self.song.artists or []
            s._fileName =  newFilename
            s.file_extension = '.ogg'
            s.size_bytes = os.stat(MUSIC_PATH+newFilename).st_size
            s.rating = self.song.rating
            s.bit_rate_kbps = file_meta['_bitrate']
            s.length_seconds = self.song.length_seconds
            s.language = self.song.language
            s.release_date = file_meta.get('date',self.song.release_date)
            s.explicit = self.song.explicit
            s.track_number = self.song.track_number
            s.genre = self.song.genre
            database.addSong(s)
            database.saveAllSongs()
            self.removeLayer()

        downloadURLAsync(song._fileName,onDone,onUpdate)

class SongTitle(Text):
    def __init__(self, pos:tuple[int,int], font:font.Font):
        super().__init__(pos, "No Song",primary_color,font)
        self.right_mask = Surface((20,self.font.get_height()+1),const.SRCALPHA)
        for x in range(self.right_mask.get_width()):
            column = self.right_mask.subsurface((x,0,1,self.right_mask.get_height()))
            color = 255,255,255,(255-255*x//self.right_mask.get_width())
            column.fill(color)
        self.sot = pygame.time.get_ticks()
        self.msurf = Surface((0,0))

        
    def offset(self,d:float):
        LENGTH = 5
        vel = d/LENGTH
        ttime= LENGTH
        time = (pygame.time.get_ticks() - self.sot) / 1000 % (4*ttime)
        if time < ttime:
            return vel*time
        time -= ttime
        if time < ttime:
            return d
        time -= ttime
        if time < ttime:
            return d-vel*time
        return 0

    def setText(self, newText: str) -> None:
        self._Text__text = newText
        self.surf = self.font.render(self._Text__text,True,self.color)
        self.sot = pygame.time.get_ticks()-2000
        self.is_long = self.rect.width < self.surf.get_width()


    def update(self,_:Input):
        name = MusicPlayer.songQueue.current.name if MusicPlayer.songQueue.current is not None else "No Song"
        self.setTextIfNeeded(name)



    def draw(self, surf: Surface):
        is_long = self.rect.width < self.surf.get_width()
        if not is_long:
            surf.blit(self.surf,self.rect.topleft)

            pass
        elif self.showing:
            if self.msurf.get_width()!= self.rect.width+4:
                self.msurf = Surface((self.rect.width+4,self.rect.height),const.SRCALPHA)

            self.msurf.fill((0,0,0,0))
            self.msurf.blit(self.surf,(-self.offset(self.surf.get_width()-self.rect.width),0))
            self.msurf.blit(self.right_mask,(self.msurf.get_width()-self.right_mask.get_width(),0),special_flags=const.BLEND_RGBA_MIN)
            surf.blit(self.msurf,self.rect.topleft)

            

            # surf.blit(self.surf,self.rect.topleft)
class VolumeSlider(Slider):
    def __init__(self, pos:tuple[int,int], size:tuple[int,int]):
        super().__init__(pos,size,primary_layout,self.saveFunction)
        self.bar_width = 5
        self.setValue(MusicPlayer.get_volume())
        self.pwheel = 0
  
    def update(self,input:Input):
        super().update(input)
        wheel = input.wheel
        self.pwheel = self.pwheel + wheel * 0.3 if wheel else 0
        if self.mouse_active and wheel:
            self.setValue(self.value-(wheel+self.pwheel)* 12/300)
        elif self.value != MusicPlayer.get_volume():
            self.setValue(MusicPlayer.get_volume())

    def saveFunction(self,num:float):
        MusicPlayer.set_volume(num)
    
    def draw(self,surf:Surface):
        draw.rect(surf,self.color.background,(self.rect.left,self.rect.top+(self.rect.height-self.bar_width)//2,self.rect.width,self.bar_width),0,2)
        # draw.rect(surf,self.passed_color,self.passed_rect,0,2)        
        draw.rect(surf,self.color.tertiary,self.passed_rect,0,2)
        if self.active: #show ball when mouse hovering or dragging
            draw.circle(surf,self.color.foreground,(self.sliderx+self.rect.left,self.rect.midleft[1]),6)

class TrackingSlider(Slider):
    def __init__(self,pos:tuple[int,int],size:tuple[int,int]):
        super().__init__(pos,size,primary_layout,lambda x:None)
        self.bar_width=5

   
    def onDeactivate(self): 
        if MusicPlayer.songQueue.current:
            MusicPlayer.setPosition(self.value * MusicPlayer.songQueue.current.length_seconds)

    def update(self,input:Input):
        super().update(input)    
        if not self.active:
            if MusicPlayer.songQueue.current is not None:
                self.setValue(MusicPlayer.getPosition() / MusicPlayer.songQueue.current.length_seconds) 
            else:
                self.setValue(0)

    def draw(self,surf:Surface):
        draw.rect(surf,self.color.background,(self.rect.left,self.rect.top+(self.rect.height-self.bar_width)//2,self.rect.width,self.bar_width),0,2)
        # draw.rect(surf,self.passed_color,self.passed_rect,0,2)        
        draw.rect(surf,self.color.tertiary,self.passed_rect,0,2)
        if self.mouse_active or self.active: #show ball when mouse hovering or dragging
            draw.circle(surf,self.color.foreground,(self.sliderx+self.rect.left,self.rect.midleft[1]),5)

class RepeatButton(ButtonSwitch):
    def __init__(self, pos: tuple[int, int], size: tuple[int, int]):
        super().__init__(pos, size, [Repeat0,Repeat1,Repeat2],settings.repeat_level,self.onDown)

    def onDown(self,state:int):
        logger.log(f'Repeat Button turning state to: {state*2}')
        MusicPlayer.songQueue.repeat_level = state

class SongLengthPassed(Text):
    def __init__(self, pos:tuple[int,int], font:font.Font, text:str, words_color:ColorType):
        self.current_time = 0
        super().__init__(pos, text, words_color, font )

    def update(self,_):
        if MusicPlayer.songLoaded:
            self.setTextIfNeeded(formatTimeSpecial(MusicPlayer.timer.timeElapsed().__trunc__()))
        else:

            self.setTextIfNeeded(formatTimeSpecial(0))

class SongLength(Text):
    def __init__(self, pos:tuple[int,int], font:font.Font, text:str, words_color:ColorType):
        self.current_time = 0
        super().__init__(pos,text, words_color, font )

    def update(self,_):
        if MusicPlayer.songQueue.current is not None:
            self.setTextIfNeeded(formatTimeSpecial(MusicPlayer.songQueue.current.length_seconds))
        else:
            self.setTextIfNeeded(formatTimeSpecial(0))

class SongArtists(Text):
    def __init__(self, pos, font, text, words_color):
        super().__init__(pos, text, words_color, font)
        self.right_mask = Surface((20,self.font.get_height()+1),const.SRCALPHA)
        for x in range(self.right_mask.get_width()):
            column = self.right_mask.subsurface((x,0,1,self.right_mask.get_height()))
            color = 255,255,255,(255-255*x//self.right_mask.get_width())
            column.fill(color)
        self.t = pygame.time.get_ticks()
        self.msurf = Surface((0,0))

    def setTextIfNeeded(self,newText:str):
        if self._Text__text==newText:return
        self._Text__text = newText
        self.surf = self.font.render(self._Text__text,True,self.color)
        self.sot = pygame.time.get_ticks()
        self.is_long = self.rect.width < self.surf.get_width()

    def update(self,_:Input):
        if MusicPlayer.songQueue.current is not None:
            self.setTextIfNeeded(formatArtists(tuple(MusicPlayer.songQueue.current.artists))) 
    def offset(self,d:float):
        LENGTH = 5
        vel = d/LENGTH
        ttime= LENGTH
        time = (pygame.time.get_ticks() - self.sot) / 1000 % (4*ttime)
        if time < ttime:
            return vel*time
        time -= ttime
        if time < ttime:
            return d
        time -= ttime
        if time < ttime:
            return d-vel*time
        return 0
    def draw(self, surf: Surface): 
        is_long = self.rect.width < self.surf.get_width()
        if not is_long:
            surf.blit(self.surf,self.rect.topleft)

            pass
        elif self.showing:
            if self.msurf.get_width()!= self.rect.width+4:
                self.msurf = Surface((self.rect.width+4,self.rect.height),const.SRCALPHA)
            self.msurf.fill((0,0,0,0))
            self.msurf.blit(self.surf,(-self.offset(self.surf.get_width()-self.rect.width),0))
            self.msurf.blit(self.right_mask,(self.msurf.get_width()-self.right_mask.get_width(),0),special_flags=const.BLEND_RGBA_MIN)
            surf.blit(self.msurf,self.rect.topleft)
        
class SongSearchResults(Selection):
    def __init__(self,top:int,horizontal_pad:int,box_height:int):
        self.top = top
        self.horizontal_pad = horizontal_pad
        self.box_height = box_height
        super().__init__((0,0),(1,1),1,selection_cs,lambda : [],SongBox)

    def onResize(self,size:tuple[int,int]):
        self.resize((self.horizontal_pad,self.top),(size[0]-2*self.horizontal_pad,self.box_height),size[1]-self.top)

class SongSearchBox(InputBoxOneLine):
    def __init__(self, y:int, horizontal_pad:int,height:int, searchResultsDropdown:Selection):
        self.dropdown = searchResultsDropdown
        self.y = y
        self.h_pad = horizontal_pad
        self.height = height
        def _inner(query):
            songs = database.search(query)
            searchResultsDropdown.dataGetter = lambda : songs#type: ignore
            searchResultsDropdown.recalculateSelection()
        
        super().__init__((horizontal_pad,y), (100,30),primary_layout,_inner,getFont(FONT_NAME.OPEN_SANS,20))
        @database.songs_changed_event.register
        def _():
            self.setText(self.text) # retrigger a new search of the database to only include current songs
        
    
    def onResize(self,newSize:tuple[int,int]):
        self.rect.size = (newSize[0]-2*self.h_pad,self.height)
        super().onResize(newSize)

class PlaylistDisplay(DrawBase):
    def __init__(self,size:tuple[int,int]):
        self.playlist = None
        def songOptions(l:Layer,s:Song,si:int):
            if self.playlist is not None:
                return PlaylistSongOptions(l,s,si,self.playlist)
        self.songlist = SongList2((20,100),(size[0]-40,40),size[1]-100,ColorScheme(20,20,20),self.onSongClick,lambda : list((s,i) for i,s in enumerate(self.getPlaylistSongs())),songOptions)
        database.playlists_changed_event.register(self.songlist.recalculateSelection)
        self.titleBox = ColorArea((0,0),(0,100),secondary_color)    
        self.title = Text((10,0),'',(255,255,255),getFont(FONT_NAME.ARIAL,50))
        self.playButton = AddImage(
            Button((20,60),(35,35),ColorScheme(50,255,60),lambda : MusicPlayer.playPlaylist(self.playlist) if self.playlist else None),
            Paused
        )
        self.renameTitle = AddText(
            Button((size[0]-100,10),(80,25),ColorScheme(100,100,100),self.toggleRenaming),
            'Rename',(255,255,255),getFont(FONT_NAME.ARIAL))
        # self.playSongs = RoundButton((30,70),20,self.playPlaylist,theme_light_yellow,theme_yellow,theme_yellow,PlaylistPlayButton,-10,-10)
        self.renaming = False
        self.current_rename = ''
        self.renamingInputBox = InputBoxOneLine((10,3),(size[0]-150,50),primary_layout,None,getFont(FONT_NAME.ARIAL,50))

        # self.addToPlaylist = AddText(
        # Button((size[0]-110,45),(95,25),ColorScheme(255,0,0),self.toggleAdding),'Add Song',(255,255,255),font_default)

    def onSongClick(self,s:Song,i:int):
        assert self.playlist
        MusicPlayer.songQueue.loadPlaylist(self.playlist,i)
        MusicPlayer.playNext()

    def onResize(self,size:tuple[int,int]):
        self.songlist.resize((20,100),(size[0]-40,40),size[1]-100)
        # self.titleBox.onResize(size)
        self.renamingInputBox.resize((size[0]-150,50))
        self.renameTitle.obj.rect.right = size[0] - 20
        # self.addToPlaylist.obj.rect.right = size[0]-20

    def getPlaylistSongs(self):
        if not self.playlist: return ()
        else: return self.playlist.songs

    def playSongFromPlaylist(self,i:int):
        if not self.playlist: raise RuntimeError("No PlayList Loaded")
        MusicPlayer.playSongAbsolute(self.playlist.songs[i])

    def playPlaylist(self):
        if not self.playlist: raise RuntimeError("No PlayList Loaded")
        MusicPlayer.playPlaylist(self.playlist)

    def toggleRenaming(self):
        assert self.playlist
        self.renaming = not self.renaming
        self.renameTitle.setText('Done' if self.renaming else 'Rename')
        if not self.renaming:
            self.playlist.name = self.renamingInputBox.text
            database.savePlaylists()
            self.setPlaylist(self.playlist)
            database.playlists_changed_event.fire()
        else:
            self.renamingInputBox.setText(self.playlist.name)
        
    def setPlaylist(self,playlist:Playlist):
        self.playlist = playlist
        self.title.setText(playlist.name)
        self.songlist.recalculateSelection()
        
    def update(self,input:Input):
        if self.renaming:
            self.renamingInputBox.update(input)
            self.renameTitle.update(input)
        else:
            self.songlist.update(input)
            self.renameTitle.update(input)
            self.playButton.update(input)
            # self.playSongs.update(input)

    def draw(self,surf:Surface):
        self.titleBox.draw(surf)
        if self.renaming:
            self.renamingInputBox.draw(surf)
            self.renameTitle.draw(surf)
        else:
            self.songlist.draw(surf)
            self.renameTitle.draw(surf)
            self.title.draw(surf)
            self.playButton.draw(surf)
            # self.playSongs.draw()

class AsyncImage:
    def __init__(self,url:str|None,size:tuple[int,int]):
        self.surface = Surface(size)
        queueDownload(url,self.setSurf)

    def setSurf(self,surface:Surface|None):
        if surface is not None:
            if surface.get_size() != self.surface.get_size():
                surface = pygame.transform.smoothscale(surface,self.surface.get_size())
            self.surface = surface

class AsyncCircleImage(AsyncImage):
    @cache
    @staticmethod
    def makeMask(length:int):
        circle_middle = (length/2,length/2)
        mask = Surface((length,length))
        mask.fill((3,2,1))
        pygame.draw.circle(mask,(1,2,3),circle_middle,length/2)
        mask.set_colorkey((1,2,3))
        return mask
    
    @staticmethod
    def maskImage(surface:Surface):
        surface.blit(AsyncCircleImage.makeMask(surface.get_height()),(0,0))
        surface.set_colorkey((3,2,1))

    def __init__(self, url: str | None, size: tuple[int, int]):
        super().__init__(url, size)

    def setSurf(self, surface: Surface | None):
        super().setSurf(surface)
        self.maskImage(self.surface)
    
class Finalize(EditSongOptions):
    def onDone(s): #type: ignore
        new_layer = s.layer.addLayer()
        r = Rect(0,0,400,200)
        new_layer.space.addObject(
            Aligner(DownloadingScreenOptions(new_layer,r,s.makeSong()),0.5,0.5))
        s.removeLayer()

class UpdateFunction:
    __slots__ = 'func','typ','__dict__'
    def __init__(self,f:Callable[['UpdateFunction',Input],typing.Any] |
                      Callable[[Input],typing.Any] |
                      Callable[[],typing.Any],**initial_state,
                 ):
        self.func = f
        self.typ = f.__code__.co_posonlyargcount or   f.__code__.co_argcount
        if initial_state:
            self.__dict__.update(initial_state)
    def update(self,input:Input):
        if self.typ == 0:
            self.func() #type: ignore
        elif self.typ == 1:
            self.func(input) #type: ignore
        elif self.typ == 2: 
            self.func(self,input) #type: ignore
        else:
            raise ValueError

class YTVideoUI(SelectionBase):
    channel_font = getFont(FONT_NAME.OPEN_SANS,12)
    title_font = getFont(FONT_NAME.OPEN_SANS)
    length_font = getFont(FONT_NAME.OPEN_SANS,13)
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme,ytVideo:yttypes.YTVideo) -> None:
        def noRefAddToDownloadQueueAsync():
            #Show Loading Thingy
            logger.log(f"Completing MetaData for Youtube Video: {ytVideo.title}")
            new_layer = base_layer.addLayer()
            new_layer.space.addObjects(
                Aligner(
                    Layer((100,100)).inline(
                        BackgroundColor(),
                        Aligner(
                            LoadingIndicator((0,0),60,(255,255,255)),
                            0.5,0.5
                        )
                    ),
                    0.5,0.5
                ),
                UpdateFunction(Input.clearALL),
            )
            #Start get Metadata
            #Wait for metadata end
            song = yield from (getYTVideoMetadata(ytVideo))
            #Stop Loading Thingy
            base_layer.removeLayer(new_layer)
            #Show EditSongOptions [Finalize]
            l = base_layer.addLayer()
            s = Song()
            s.name = song.title
            s.album = song.album or ''
            s.artists = song.artists or []
            s.explicit = song.explicit or False
            s.genre = song.genre or ''
            s.language = 'eng'
            s.file_extension = '.ogg'
            s.size_bytes = -1
            s._fileName =  ytVideo.url
            s.rating = 'Unrated'
            s.bit_rate_kbps = 1536
            s.length_seconds = ytVideo.duration
            s.track_number = song.track_number or 0
            s.release_date = song.release_date or 'Unknown'
            l.space.addObject(Aligner(Finalize(l,s),0.5,0.5))        

        super().__init__(pos, size, color_scheme, lambda : Async.addCoroutine(noRefAddToDownloadQueueAsync()), None)
        self.data = ytVideo
        self.onResize((0,0))
        self.do_prefetch = settings.youtube_prefetch

    def onResize(self,size:tuple[int,int]):
        size = self.rect.size
        self.thumbnail_height = (size[1]-10)
        self.thumbnail_width = int(self.thumbnail_height * 9 / 5)
        if self.thumbnail_width > .35*size[0]:
            self.thumbnail_width = int(.35*size[0])
            self.thumbnail_height = int(self.thumbnail_width * 5 / 9)
        self.space_for_title = size[0] - 10 - self.thumbnail_width-10
        self.title_surf = self.title_font.render(
            trimText(self.data.title,self.space_for_title,self.title_font),
            True,
            text_color
        )
        
        self.channel_name_surf = self.channel_font.render(
            trimText(self.data.channel.name,self.space_for_title,self.channel_font),
            True,
            text_color
        )
        self.view_surf = self.length_font.render(
            f'{self.data.views:,} views' if self.data.views else 'No Views',
            True,
            text_color
        )
        
        self.duration_surf = self.length_font.render(
            formatTime2(self.data.duration),
            True,
            (255,255,255)
        )
        self.duration_surf_rect = self.duration_surf.get_rect()
        self.duration_surf_rect.right = self.rect.left+ self.thumbnail_width+5-2
        self.duration_surf_rect.bottom = self.thumbnail_height+5-2
        self.dsr_bg = self.duration_surf_rect.inflate(2,2)
        if self.data.thumbnails:
            url = self.data.thumbnails[0].url
            self.thumbnail = AsyncImage(url,(self.thumbnail_width,self.thumbnail_height))
        else:
            self.thumbnail = None
        if self.data.channel.thumbnails:
            channel_thumnbail = self.data.channel.thumbnails[0]
            self.channel_thumbnail = AsyncCircleImage(channel_thumnbail.url,(40,40))
        else:
            self.channel_thumbnail = None


    def draw(self,surf:Surface):
        if self.do_prefetch:prefetchIfNeededAsync(self.data.url) 
        self.duration_surf_rect.bottom = self.rect.top+ self.thumbnail_height+5-2
        self.dsr_bg.center = self.duration_surf_rect.center
        super().draw(surf)
        if self.thumbnail:
            surf.blit(self.thumbnail.surface,(self.rect.left+5,self.rect.top+5))
        draw.rect(surf,(0,0,0),self.dsr_bg,0,2)
        surf.blit(self.duration_surf,self.duration_surf_rect)
        surf.blit(self.title_surf,(self.rect.left+self.thumbnail_width+10,self.rect.top))
        surf.blit(self.view_surf,(self.rect.left+self.thumbnail_width+10,self.rect.top+self.title_font.get_height()))
        if self.channel_thumbnail:surf.blit(self.channel_thumbnail.surface,(self.rect.left+self.thumbnail_width+10,self.rect.top+self.title_font.get_height()+self.view_surf.get_height()+10))
        if self.channel_name_surf:
            surf.blit(self.channel_name_surf,(self.rect.left+self.thumbnail_width+10+50,self.rect.top+self.title_font.get_height()+self.view_surf.get_height()+10))

class YTPlaylistUI(SelectionBase):
    channel_font = getFont(FONT_NAME.OPEN_SANS,12)
    title_font = getFont(FONT_NAME.OPEN_SANS)
    length_font = getFont(FONT_NAME.OPEN_SANS,13)
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme,ytPlaylist:yttypes.YTPlaylist) -> None:
        def showPlaylistInfoAsync():
            logger.log(f"Completing MetaData for Youtube Playlist: {ytPlaylist.title}")
            #Show Loading Indicator
            new_layer = base_layer.addLayer()
            new_layer.space.addObjects(
                Aligner(
                    Layer((100,100)).inline(
                        BackgroundColor(),
                        Aligner(
                            LoadingIndicator((0,0),60,(255,255,255)),
                            0.5,0.5
                        ),
                        Resizer(
                            loading_bar:=AutoSlider((0,0),(1,1),primary_layout),
                            '0','100%-5','100%','100%'
                        )
                    ),
                    0.5,0.5
                ),
                UpdateFunction(Input.clearALL),
            )
            songs:list[yttypes.YTVideo] = []
            #Get Playlist Songs
            for s in getYTPlaylistSongs(ytPlaylist):
                if s is not None:
                    songs.append(s)
                    loading_bar.setValue(len(songs)/ytPlaylist.songs)
                yield
            loading_bar.setValue(1)
            ytPlaylist.songs = len(songs)
            #Remove Loading Indicator
            base_layer.removeLayer(new_layer)
            #Show Playlist Information
            new_layer = base_layer.addLayer()
            
            new_layer.space.addObject(
                Resizer(
                    PlaylistInfoScreen(new_layer,(350,500),ytPlaylist,songs),
                    '50%-(30%min300)','50%-(40%min300)','50%+(30%min300)','50%+(40%min300)',
                )
            )

        super().__init__(pos, size, color_scheme, None, lambda : Async.addCoroutine(showPlaylistInfoAsync()))
        self.data = ytPlaylist
        self.thumbnail_height = (size[1]-10)
        self.thumbnail_width = int(self.thumbnail_height * 9 / 5)
        if self.thumbnail_width > .35*size[0]:
            self.thumbnail_width = int(.35*size[0])
            self.thumbnail_height = int(self.thumbnail_width * 5 / 9)
        self.space_for_title = size[0] - 10 - self.thumbnail_width-10
        self.title_surf = self.title_font.render(
            trimText(ytPlaylist.title,self.space_for_title,self.title_font),
            True,
            text_color
        )
        self.channel_name_surf = self.channel_font.render(
            trimText(ytPlaylist.channel.name,self.space_for_title,self.channel_font),
            True,
            text_color
        )
        self.duration_surf = self.length_font.render(
            f'{ytPlaylist.songs:,} videos',
            True,
            (255,255,255)
        )
        self.duration_surf_rect = self.duration_surf.get_rect()
        self.duration_surf_rect.right = self.rect.left+ self.thumbnail_width+5-2
        self.duration_surf_rect.bottom = self.thumbnail_height+5-2
        self.dsr_bg = self.duration_surf_rect.inflate(2,2)
        url = ytPlaylist.thumbnails[0].url
        self.thumbnail = AsyncImage(url,(self.thumbnail_width,self.thumbnail_height))

    def draw(self,surf:Surface):
        self.duration_surf_rect.bottom = self.rect.top+ self.thumbnail_height+5-2
        self.dsr_bg.center = self.duration_surf_rect.center
        super().draw(surf)

        surf.blit(self.thumbnail.surface,(self.rect.left+5,self.rect.top+5))
        draw.rect(surf,(0,0,0),self.dsr_bg,0,2)
        surf.blit(self.duration_surf,self.duration_surf_rect)
        surf.blit(self.title_surf,(self.rect.left+self.thumbnail_width+10,self.rect.top))
        # surf.blit(self.view_surf,(self.rect.left+self.thumbnail_width+10,self.rect.top+self.title_font.get_height()))
        # if self.channel_thumbnail:surf.blit(self.channel_thumbnail.surface,(self.rect.left+self.thumbnail_width+10,self.rect.top+self.title_font.get_height()+self.view_surf.get_height()+10))
        surf.blit(self.channel_name_surf,(self.rect.left+self.thumbnail_width+10,self.rect.top+self.title_font.get_height()+10))

class YTVideoUIForPlaylist(YTVideoUI):
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme, ytData: tuple[yttypes.YTVideo,list,list]) -> None:
        super().__init__(pos, size, color_scheme, ytData[0])
        self.onDown = None
        self.rightClick = lambda : (nl:=base_layer.addLayer()).space.addObjects(DownloadingPlaylistOptions(nl,ytData[1].index(ytData[0]),ytData[1],ytData[2]))
        self.do_prefetch = False
        self.channel_name_surf = None
        
    def update(self,input:Input):
        super().update(input)
        if input.mb3d and self.rect.collidepoint(input.mpos):
            self.rightClick()

class DownloadingPlaylistOptions(OptionsBase):
    def __init__(self,current_layer:Layer,i:int,l:list,h:list) -> None:
        #buttons to draw, add to playlist
        #add to queue
        #view song credits
        self.i = i
        r = Rect(pygame.mouse.get_pos(),(140,40))
        
        def remove():
            h.append((i,l.pop(i)))
            self.removeLayer()
            del self.to_draw
            del self.to_update
        super().__init__(current_layer,r)
        self.addObjects(

            AddText(
                Button((5,5),(self.rect.width-10,30),light_selection_cs,None,remove),
                'Remove',text_color,getFont(FONT_NAME.ARIAL,14)
            )
        )
        self.surf = Surface(self.rect.size)
        self.surf.set_colorkey((0,0,1))
        self.surf.fill((0,0,1))
        draw.rect(self.surf,(0,0,0),((0,0),self.rect.size),0,3) 
    def update(self,input:Input):
        super().update(input)
        if self.rect.collidepoint(input.mpos):
            input.clearMouse()
    def draw(self, surf: Surface):
        draw.rect(surf,(0,0,0),self.rect,0,2)
        return super().draw(surf)
    
class ItunesResultUI(SelectionBase):
    artist_font = getFont(FONT_NAME.ARIAL,12)
    title_font = getFont(FONT_NAME.OPEN_SANS,20)
    length_font = getFont(FONT_NAME.OPEN_SANS,13)
    album_font = getFont(FONT_NAME.OPEN_SANS,17)
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme,itunesData:ItunesResult) -> None:
        def addToDownloadQueue():
            new_layer = base_layer.addLayer()
            new_layer.space.addObjects(
                Aligner(
                    Layer((100,100)).inline(
                        BackgroundColor(),
                        Aligner(
                            LoadingIndicator((0,0),60,(255,255,255)),
                            0.5,0.5
                        )
                    ),
                    0.5,0.5
                ),
                UpdateFunction(Input.clearALL),
            )
            songs:list[yttypes.YTVideo] = []
            #Get Possible Songs
            songs,match = yield from getYTSongsFromITunes(itunesData)
            #Remove Loading Indicator
            base_layer.removeLayer(new_layer)
            if not songs:
                #no songs could be produced 
                #add some sort of failure window
                logger.log("No possible yt songs found")
                return
            new_layer = base_layer.addLayer()
            r = Rect(0,-50,500,230)
            new_layer.space.addObject(
                SAligner(
                    MatchItunesToYTUI(new_layer,r,songs,match),
                    0.5,0.5
                )
            )
            yield

        super().__init__(pos, size, color_scheme, lambda : Async.addCoroutine(addToDownloadQueue()), None)
        self.data = itunesData
        self.thumbnail_height = (size[1]-10)
        self.thumbnail_width = self.thumbnail_height
        self.space_for_title = size[0] - 10 - self.thumbnail_width-10
        self.show_album = self.space_for_title > 350
        if self.show_album:
            self.space_for_title //= 2 
        self.title_surf = self.title_font.render(
            trimText(itunesData.title,self.space_for_title,self.title_font),
            True,
            text_color
            )
        
        self.channel_name_surf = self.artist_font.render(
            trimText(itunesData.artist,self.space_for_title,self.artist_font),
            True,
            dim_text_color
            )
       
        self.duration_surf = self.length_font.render(
            f'{formatTimeSpecial(itunesData.duration)}',
            True,
            text_color
            )

        self.album_surf = self.album_font.render(
            trimText(itunesData.album,self.space_for_title,self.album_font),
            True,
            dim_text_color    
            )
        
        self.duration_surf_rect = self.duration_surf.get_rect()
        self.duration_surf_rect.right = self.rect.left+ self.thumbnail_width+5-2
        self.duration_surf_rect.bottom = self.thumbnail_height+5-2
        self.dsr_bg = self.duration_surf_rect.inflate(4,1)

        url = itunesData.thumbnail.url
        # else:
        #     url = itunesData.thumbnail(self.thumbnail_width)
        self.thumbnail = AsyncImage(url,(self.thumbnail_width,self.thumbnail_height))
    
    def draw(self,surf:Surface):
        self.duration_surf_rect.bottom = self.rect.top+ self.thumbnail_height+5-2
        self.dsr_bg.center = self.duration_surf_rect.center
        super().draw(surf)
        surf.blit(self.thumbnail.surface,(self.rect.left+5,self.rect.top+5))
        draw.rect(surf,(0,0,0),self.dsr_bg,0,2)
        surf.blit(self.duration_surf,self.duration_surf_rect)

        surf.blit(self.title_surf,(self.rect.left+self.thumbnail_width+10,self.rect.centery-self.title_font.get_height()//2))
        if self.show_album:
            surf.blit(self.album_surf,(self.rect.left+self.thumbnail_width+10+self.space_for_title+5,self.rect.centery-self.album_font.get_height()//2))
        surf.blit(self.channel_name_surf,(self.rect.left+self.thumbnail_width+10,self.rect.centery+self.title_font.get_height()//2))        

class MatchItunesToYTUI(ForceFocusOptionsBase):

    def __init__(self,l:Layer,r:Rect,possible_matches:list[yttypes.YTVideo],match:yttypes.YTVideo|None):
        super().__init__(l,r)
        self.possible_matches = possible_matches
        self.match = match
        header = self.cutTopSpace(30)
        header.addObjects(
            BackgroundColor((20,20,20)),
            Aligner(
                Text((0,0),'Matching to Youtube',text_color,title_font),
                0.5,0.5
            )
        )
        light_green_cs = ColorScheme(100,200,100)
        light_red_cs = ColorScheme(200,100,100)
        footer = self.cutBottomSpace(50)
        footer.addObjects(
            BackgroundColor(),
            Aligner(
                AddText(
                    Button((2,0),(100,30),light_red_cs,None,self.removeLayer),
                    'Cancel',text_color,option_font
                ),
                0.5,0.5
            ),
        )
        self.selected_match = match
        self.selected_match_ui = YTVideoUI((0,0),(100,100),selection_cs,match or yttypes.YTVideo.unknown())
        self.addObjects(
            BackgroundColor(),
            Resizer(
                self.selected_match_ui,
                '5','20','100%-5','100%-20'
            )
        )

def fetchYTPlaylistAsync(playlistID:str,pipe:ObjectValue[None|str|list[yttypes.YTVideo]]):
    pipe.set('fetching')
        
    # Thread(target=lambda : pipe.set(SongSearch.getYoutubePlaylist(playlistID)),daemon=True).start()

def registerFetchPipeCallback(
        pipe:ObjectValue[None|str|list[yttypes.YTVideo]],
        onStart:EventHookAny,
        onDone:EventHookAny
    ):
    pipe.obj_change_event.register(
        lambda _: onStart() if isinstance(_,str) else onDone()
    )

class LoadingIndicator(DrawBase):
    def __init__(self,pos:tuple[int,int],size:int,color:tuple[int,int,int]) -> None:
        self.rect = Rect(*pos,size,size)
        self.s = Surface((size,size),pygame.SRCALPHA)
        self.dots = 12
        self.time_of_next_dot = time.monotonic()
        self.dot_rad = max(3,int(size*0.07))
        self.rad = size//2-self.dot_rad
        self.i = 0
        self.dot_deltatime = 1/12
        self.color = color
        self.s2 = Surface(self.s.size,const.SRCALPHA)
        self.s2.fill((20,20,20,20))

    def draw(self,surf:Surface):
        cur_time = time.monotonic()
        while cur_time > self.time_of_next_dot:
            theta = 2*math.pi*self.i/self.dots
            x = (self.rad-1) * math.cos(theta) + self.rad + self.dot_rad
            y = (self.rad-1) * math.sin(theta) + self.rad + self.dot_rad
            self.s.blit(self.s2,special_flags=const.BLEND_RGBA_SUB)
            draw.aacircle(self.s,self.color,(x,y),self.dot_rad)
            self.i += 1
            self.time_of_next_dot += self.dot_deltatime
        surf.blit(self.s,self.rect)

class BatchDownloadSongs(ForceFocusOptionsBase):
    class SimpleBox(SelectionBase):
        def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme,t:tuple[DownloadingSong,ObjectValue[float]]) -> None:
            super().__init__(pos, size, color_scheme)
            self.scroller = AutoSlider((0,0),(self.rect.width,2),ColorLayout((80,180,100),(50,50,50)))
            t2,self.o = t
            self.txt = Text((0,0),f"{t2.title} • {(t2.album or '')[:40]}",(255,255,255),subtitle_font)
        def update(self,input:Input):
            self.scroller.setValue(self.o.get())
        def onResize(self,newSize:tuple[int,int]):
            self.scroller.rect.width = self.rect.width
            self.scroller.setValue(self.scroller.value)
        def draw(self,surf:Surface):
            self.scroller.rect.top = self.rect.top
            self.txt.rect.centery = self.rect.centery
            super().draw(surf)
            self.scroller.draw(surf)
            self.txt.draw(surf)
    class Selection(Selection):
        def update(self, input):
            mpos,wheel = input.mpos,input.wheel
            touch_wheel = input.touch_wheel
            input.mousex -= self.rect.left
            input.mousey -= self.rect.top
            for i,button in enumerate(self.selection):
                button.update(input)
            input.mousex += self.rect.left
            input.mousey += self.rect.top

            if self.rect.collidepoint(mpos):  
                self.mhover = True 
                input.wheel = 0
                input.touch_wheel = 0     
                if wheel and self.fullHeight > self.max_y:
                    w = (wheel + self.pwheel.__trunc__()) * gui.settings.wheel_sensitivity
                    self.y_scroll_target += w
                    if self.y_scroll_target > self.fullHeight - self.max_y:
                        self.y_scroll_target = self.fullHeight - self.max_y
                    elif self.y_scroll_target < 0: self.y_scroll_target = 0
                    self.aligned_y = False
                elif touch_wheel and self.fullHeight > self.max_y:
                    dpy = touch_wheel * base_layer.rect.height
                    self.y_scroll_target += dpy
                    self.setYScroll(self.y_scroll_target)

            else:
                if self.mhover:
                    for s in self.selection:
                        s.setToUp()
                    self.mhover = False
                if input.mb1d or input.mb1u or input.mb3u or input.mb3d:
                    for button in self.selection:
                        button.update(input)
                
            if not self.aligned_y:
                self.y_scroll_real = int(gui.utils.utils.expDecay(self.y_scroll_real,self.y_scroll_target,1/gui.settings.scroll_smoothing,input.dt))
                if (self.y_scroll_real - self.y_scroll_target).__abs__() <= 2:
                    self.y_scroll_real = int(self.y_scroll_target)
                    self.aligned_y = True
                for s in self.selection:
                    s.setYOffset(self.y_scroll_real)
            self.pwheel = self.pwheel + wheel * 0.4 if wheel else 0

    def __init__(self, l: Layer, r: Rect):
        super().__init__(l,r)
        self.songs:list[tuple[DownloadingSong,ObjectValue[float]]] = []
        self.autoscroller=  AutoSlider((0,0),(r.width,10),dark_inputbox_cl)
        self.draw_selection = BatchDownloadSongs.Selection((0,0),(20,30),10,ColorScheme(14,14,14),lambda : self.songs,BatchDownloadSongs.SimpleBox,1.07)
        self.pipe:deque[tuple[str,Callable,Callable]] = deque()
        self.batch_installer = AsyncInOutBatchDownloader(self.pipe)
        self.text = Text((0,15),'0/0 Songs Done',(255,255,255),subtitle_font)
        self.done = 0
        self.dirty = False
        self.addObjects(
            BackgroundColor((70,70,70)),
            Resizer(
                self.autoscroller,'0','2','100%','12'
            ),
            Aligner(
                self.text,0.5,0,0.5,0
            ),
            Resizer(
                self.draw_selection,
                '5','40','100%-5','100%-5'
            )
        )
        self.time_to_leave = 0
        self.started_countdown = False

    def __del__(self):
        return self.batch_installer.close()

    def update(self,input:Input):
        super().update(input)

        escape = pygame.key.get_just_pressed()[const.K_ESCAPE]
        ctrl = pygame.key.get_mods()&const.KMOD_CTRL
        if escape:
            if len(self.songs):#we still have songs
                if ctrl:
                    self.removeLayer()
            else:
                self.removeLayer()
        if self.done != 0 and len(self.songs) == 0: 
            if not self.started_countdown:
                self.started_countdown = True
                self.time_to_leave = time.monotonic()+2
            else:
                if time.monotonic() > self.time_to_leave:
                    self.removeLayer()
        elif self.started_countdown:
            self.started_countdown = False #

    def draw(self,surf:Surface):
        if self.dirty:
            self.draw_selection.recalculateSelection()
            self.autoscroller.setValue(self.done / (len(self.songs)+self.done))
            self.text.setText(f'{self.done} / {len(self.songs)+self.done} Songs Done')
            self.dirty = False
        super().draw(surf)

    def addSong(self,song:DownloadingSong):
        o = ObjectValue(0.0)
        self.songs.append((song,o))
        self.dirty = True
        def onUpdate(percent:float,size:str,speed:tuple[float,str]):
            o.set(percent)
        def onDone(path:str,err:Exception):
            self.songs.remove((song,o))
            self.done +=1
            self.dirty = True
            if err:
                logger.log(f'{song.title} | {song.url} was not able to be downloaded')
                return
            _,name= path.rsplit('/',1)
            s = Song()
            s.name = song.title
            s.album = song.album or ''
            s.artists = song.artists or []
            s._fileName =  name
            s.file_extension = '.ogg'
            s.size_bytes = os.stat(path).st_size
            s.rating = 'Unrated'
            s.bit_rate_kbps = 1536
            s.length_seconds = song.length_seconds
            s.language = 'en'
            try:
                database.addSong(s)
            except ValueError: #this song is already in database
                pass
            database.saveAllSongs()
            
        self.pipe.append((song.url,onUpdate,onDone))

def downloadBatch(songs:list[yttypes.YTVideo]):
    songs = list(filter(lambda x: f'[{x.id}].ogg' not in database.songsByFileName,songs))
    if not songs:
        logger.log("All Songs Were already downloaded")
        return
    nl = base_layer.addLayer()

    r = Rect(0,0,400,350)
    nl.space.addObject(Aligner(popup:=BatchDownloadSongs(nl,r),0.5,0.5))
    #some songs might already be downloaded so we should remove them
    Async.addCoroutine(getMetaDataForYTBatchAsync(songs,popup.addSong))

class PlaylistInfoScreen(Region):
    def __init__(self,l:Layer,size:tuple[int,int],ytplaylist:yttypes.YTPlaylist,videos:list[yttypes.YTVideo]):
        self.layer = l
        super().__init__(Rect((0,0),size))
        self.songs:list[yttypes.YTVideo] = videos
        self.delete_history:list[tuple[int,yttypes.YTVideo]] = []
        self.vid_name = 'Song' if ytplaylist.channel.is_verified_artist else 'Video'
        self.header = ObjectValue(f'{ytplaylist.songs}  {self.vid_name}{"s" if ytplaylist.songs!=1 else ""}')
        header = Region(Rect(0,0,self.rect.width,30))
        body = Region(Rect(0,30,self.rect.width,self.rect.height-60))
        footer = Region(Rect(0,self.rect.height-30,self.rect.width,30))

        self.addObjects(
            Resizer(
                header,
                '0','0','100%','30'
            ),
            Resizer(
                body,
                '0','30','100%','100%-30'
            ),
            Resizer(
                footer,
                '0','100%-30','100%','100%'
            ),
        )
        header.addObjects(
            BackgroundColor((30,30,30)),
            Aligner(a:=Text((0,0),self.header.get(),(255,255,255),title_font),0.5,0.5)
        )
        self.header.obj_change_event.register(a.setTextIfNeeded)
        
        footer.addObjects(
            BackgroundColor((10,10,10)),
            Aligner(
                AddText(
                    Button((-2,0),(90,24),ColorScheme(80,140,80),None,lambda :toNone(self.removeLayer(),downloadBatch(self.songs))), #type: ignore
                    'Download',(255,255,255),subtitle_font,

                ),0.5,0.5,1
            ),
            Aligner(
                AddText(
                    Button((2,0),(90,24),ColorScheme(80,140,80),None,lambda: base_layer.removeLayer(self.layer)),
                    'Cancel',(255,255,255),subtitle_font,
                ),0.5,0.5,0
            )
        )
        body.addObject(
            KeyBoundFunction(lambda : self.songs.insert(*self.delete_history.pop()) if self.delete_history else None,keybinds.getActionKeybinds('Undo')),
        )
        self.selection = Selection((0,0),(50,50),2,selection_cs,
            lambda : zip(self.songs,(self.songs,)*len(self.songs),(self.delete_history,)*len(self.songs)),YTVideoUIForPlaylist
        ) 
        body.addObjects(
            a:=Resizer(
                self.selection,
                '0','0','100%','100%'
            ),
            ScrollbarConsuming((0,0),(10,1),10,primary_layout).linkToDropdown(self.selection),
            BackgroundColor((30,30,30))
        )
        if self.selection.fullHeight > self.selection.max_y:
            a.right = '100%-10'
            a.onResize(self.rect.size)
        self.p_songlen = len(self.songs)
    
    def update(self, input: Input):
        songlen = len(self.songs)
        if songlen != self.p_songlen:
            self.selection.recalculateSelection()
            self.p_songlen = songlen
            self.header.set(f'{songlen}  {self.vid_name}{"s" if songlen!=1 else ""}')
        super().update(input)
        input.clearALL()
    


class PlaylistInfoOptions(ForceFocusOptionsBase):
    @classmethod
    def onLayerCenter(cls,l:Layer,size:tuple[int,int],playlistID:str):
        nl = l.addLayer()
        r = Rect(0,0,*size)
        v = cls(nl,r,playlistID)
        nl.space.addObject(SAligner(v,0.5,0.5))
        return v
    
    def __init__(self,l:Layer,r:Rect,playlistID:str):
        super().__init__(l,r)
        self.playlistID = playlistID
        self.addObject(BackgroundColor((30,30,30)))
        self.delete_history:list[tuple[int,YTVideoUI]] = []
        self.songs:list[YTVideoUI] = []
        self.last_len = 0
        self.fetched = False
        self.startedFetch = False
        self.pipe:ObjectValue[None|str|list[yttypes.YTVideo]] = ObjectValue(None)
        registerFetchPipeCallback(self.pipe,lambda:setattr(self,'startedFetch',True),lambda:setattr(self,'fetched',True))
        if self.pipe.get() is None:
            fetchYTPlaylistAsync(playlistID,self.pipe)
        elif self.pipe.get() == 'fetching':
            self.startFetching()
        else:
            self.onFetched()  


    def startFetching(self):
        self.addObject(Aligner(LoadingIndicator((0,0),50,(255,255,255)),0.5,0.5))

    def update(self, input: Input):
        if hasattr(self,'selection'):
            if self.last_len != len(self.songs):
                self.selection.recalculateSelection()
                self.last_len = len(self.songs)
        if self.fetched:
            self.fetched = False
            self.onFetched()
        if self.startedFetch:
            self.startedFetch = False
            self.startFetching()
        return super().update(input)

    def onFetched(self):
        self.to_draw.clear()
        self.to_update.clear()
        playlistInfo = self.pipe.get()
        assert isinstance(playlistInfo,list)
        self.songs = playlistInfo #type: ignore
        header = self.cutTopSpace(30)
        self.addObject(
            KeyBoundFunctionConditional(lambda : self.delete_history,lambda : self.songs.insert(*self.delete_history.pop()),keybinds.getActionKeybinds('Undo'))
        )
        # self.addObject(KeyBoundFunction(lambda : self.songs.insert(*self.delete_history.pop()) if self.delete_history and pygame.key.get_mods()&const.KMOD_CTRL else None,const.K_z))
        header.addObjects(BackgroundColor((30,30,30)),Aligner(Text((0,0),f'{len(playlistInfo)} Song{"s" if len(playlistInfo)!=1 else ""}',(255,255,255),title_font),0.5,0.5))
        self.selection = Selection((0,0),(50,50),2,selection_cs,lambda : zip(self.songs,(self.songs,)*len(self.songs),(self.delete_history,)*len(self.songs)),YTVideoUI) #type: ignore
        bottom = self.cutBottomSpace(30)

        bottom.addObjects(
            BackgroundColor((10,10,10)),
            Aligner(
                AddText(
                    Button((-2,0),(90,24),ColorScheme(80,140,80),None,lambda :toNone(self.removeLayer(),downloadBatch(self.songs))), #type: ignore
                    'Download',(255,255,255),subtitle_font,

                ),0.5,0.5,1
            ),
            Aligner(
                AddText(
                    Button((2,0),(90,24),ColorScheme(80,140,80),None,self.removeLayer),
                    'Cancel',(255,255,255),subtitle_font,
                ),0.5,0.5,0
            )
        )

        self.addObjects(
            Resizer(
                self.selection,
                '0','0','100%-10','100%'
            ),
            ScrollbarConsuming((0,0),(10,1),10,primary_layout).linkToDropdown(self.selection)
        )

class DetectedPlaylist(ForceFocusOptionsBase):
    @classmethod
    def onLayerCenter(cls,l:Layer,size:tuple[int,int],url:str):
        nl = l.addLayer()
        r = Rect(0,0,*size)
        v = cls(nl,r,url)
        nl.space.addObject(Aligner(v,0.5,0.5))
        return v
    
    def __init__(self, l: Layer, r: Rect,url:str):    
        super().__init__(l, r)
        self.url = url
        self.addObjects(
            BackgroundColor((30,30,30)),
            Aligner(
                Text((0,5),'Detected Playlist',(255,255,255),title_font),
                0.5,0.0,0.5,0
            )
        )

        def download():
            self.removeLayer()
            PlaylistInfoOptions.onLayerCenter(base_layer,(400,300),url)


        self.addObjects(
            BackgroundColor((30,30,30)),
            Text((5,10+30),'It seems as though you have input a playlist url!',(255,255,255),subtitle_font),
            Text((5,30+30),'Would you like to download this playlist?',(255,255,255),subtitle_font),
            Aligner(
                AddText(
                    Button((-3,-10),(70,20),ColorScheme(100,255,100),None,download),
                    'Yes',(0,0,0),getFont(FONT_NAME.OPEN_SANS,15)
                ),
                0.5,1,1,1
            ),
            Aligner(
                AddText(
                    Button((3,-10),(70,20),ColorScheme(110,110,110),None,self.removeLayer),
                    'No',(0,0,0),getFont(FONT_NAME.OPEN_SANS,15)
                ),
                0.5,1,0,1
            )

        )
    def removeLayer(self):
        super().removeLayer()
        del self.to_draw #relinquish references to all objects
        del self.to_update #relinquish references to all objects

    def update(self,input:Input):
        super().update(input)

    def draw(self,surf:Surface):
        super().draw(surf)
class Plus(DrawBase):
    __slots__ = 'color','rect','width'
    def __init__(self,color:ColorType,rect:Rect|None = None,width:int = 1) -> None:
        self.color = color
        self.rect = rect or Rect(1,1,1,1) 
        self.width = width
    def update(self,input:Input): ...
    def draw(self,surf:Surface):
        draw.line(surf,self.color,self.rect.midtop,self.rect.midbottom,self.width)
        draw.line(surf,self.color,self.rect.midleft,self.rect.midright,self.width)
class Minus(DrawBase):
    __slots__ = 'color','rect','width'
    def __init__(self,color:ColorType,rect:Rect|None = None,width:int = 1) -> None:
        self.color = color
        self.rect = rect or Rect(1,1,1,1) 
        self.width = width
    def update(self,input:Input): ...
    def draw(self,surf:Surface):
        draw.line(surf,self.color,self.rect.midleft,self.rect.midright,self.width)
        

class ActionModifierUI(Layer):
    def __init__(self, size: tuple[int, int],action:str):
        assert keybinds.hasAction(action), 'Action ({}) does not exist!'.format(action)
        super().__init__(size)
        keybinds.getActionKeybinds(action)
        self.action = action
        self.cs = cs = selection_cs.copy()
        cs.variance = 6
        
        self.binds = binds = keybinds.getActionKeybinds(action)
        self.binduis = Grid(Rect(1,1,1,1),(2,0),(['100%-35-`','35-`'],'35-`'),('2','2'))
        self.addbindui = Button((0,0),(1,1),cs,None,
            lambda : KeyListenerUI.addOnLayer(base_layer,lambda key,mod,action=action: toNone(keybinds.addKeybind(action,(key,mod)),self.queueRebuild()),
          )
        )
        self.should_rebuild_binduis = False
        height = 300
        self.space.addObjects(
            Resizer(
                a:=Region(Rect(1,1,1,1)).addObjects(
                    BackgroundColor(colorUtils.lighten(*bg_color,20)),
                    Aligner(
                        BoxText((0,0),(200,30),action,text_color,title_font,alignment_y=0),
                        0.5,0
                    ),
                    Resizer(
                        Region(Rect(1,1,1,1)).addObjects(
                            Resizer.fill(
                                self.binduis,
                            ),
                            BackgroundColor(colorUtils.lighten(*bg_color,23))
      
                        ),
                        '10','30','100%-10','100%-10'
                    )

                ),
                '20%',f'50%-{height//2}','80%',f'50%+{height//2}'
            )
        )
        self.rebuild_bindui()
        self.inner_space =a
    def onResize(self,size:tuple[int,int]):
        super().onResize(size)
    def queueRebuild(self):
        self.should_rebuild_binduis = True
    def rebuild_bindui(self):
            self.binduis.added = False
            self.binduis.clear()
            def modify_ip(x:int,key,mods,binds=self.binds):
                binds[x] = (key,mod)
   
            for i,(key,mod) in enumerate(self.binds):
                a = lambda key,mod,i=i: toNone(modify_ip(i,key,mod),self.queueRebuild())
                self.binduis.addRow(
                    [   
                        ZStack(
                            Button((0,0),(1,1),self.cs,
                                lambda a=a: KeyListenerUI.addOnLayer(base_layer,a)),
                            BoxText((0,0),(1,1),reprKey(key,mod),text_color,font_default),
                        ),
                        ZStack(
                            Button((0,0),(1,1),self.cs,lambda binds=self.binds,i=i: toNone(binds.pop(i),self.queueRebuild())),
                            Region(Rect(1,1,1,1)).addObjects(
                                Resizer(
                                    Minus(text_color,width=2),
                                    '25%','0','75%','-1'
                                )
                            )
                        ),
                    ] 
                )
            self.binduis.addRow(
                    [
                    AddText(
                        self.addbindui,
                        'New Keybind',text_color,getFont(FONT_NAME.YOUTUBE_REGULAR,16)
                    )
                    ,Null()
                ]
            )
            self.binduis.added = True

            self.binduis.onResize((1,1))

    def update(self, input: Input):
        if self.should_rebuild_binduis:
            self.rebuild_bindui()
            self.should_rebuild_binduis = False
        super().update(input)
        if input.mb1d and not self.inner_space.rect.collidepoint(input.mousex,input.mousey):
            base_layer.removeLayer(self)
        input.clearALL()
    
    def draw(self, surf: pygame.Surface):
        super().draw(surf)

class KeyListenerUI(Layer):
    @classmethod
    def addOnLayer(cls,layer:Layer,callback:Callable[[int,int],Any]):
        layer.addLayer(cls(layer.rect.size,callback))

    def __init__(self, size: tuple[int, int],callback:Callable[[int,int],Any]):
        super().__init__(size)
        height = '((20%max100)min150)'
        self.key = None
        self.callback = callback
        self.keyui = BoxText((0,0),(1,1),'-',text_color,font_default)
        fontRule = FontRule()
        self.space.addObjects(
            Resizer(
                ZStack(
                    ColorArea((0,0),(1,1),colorUtils.lighten(*bg_color,10)),
                    Region(Rect(1,1,1,1)).addObjects(
                        Resizer(
                            BoxText((0,0),(20,20),'Listening For Key',text_color,getNewFont(FONT_NAME.OPEN_SANS),alignment_y=0).setFontRule(fontRule),
                            '0','0','-1','50min30%'
                        ),
                        Resizer(
                            self.keyui,
                            '0','50min30%','-1','85%'
                        ),
                        Resizer(
                            BoxText((0,0),(20,12),'Press Any Key to Bind to Action',text_color,getNewFont(FONT_NAME.OPEN_SANS),alignment_y=1).setFontRule(fontRule),
                            '0','85%','-1','-1'
                        ),
                    ),
                ),
                '20%',f'50%-{height}*0.5','80%',f'~+{height}'
            ),
        )
    def update(self, input: Input):
        if input.KDQueue:
            self.key = input.KDQueue.pop()
            self.keyui.setText(reprKey(self.key.key,self.key.mod))
        if self.key is not None and input.KUQueue:
            base_layer.removeLayer(self)
            self.callback(self.key.key,self.key.mod)
        

        super().update(input)

        input.clearALL()

class KeyBindMenu(Layer):
    @classmethod
    def showOnLayer(cls,l:Layer):
        new_layer = l.addLayer()
        inst = cls(l.rect.size,new_layer)
        new_layer.space.addObject(
            Resizer(
                inst,
                '10%','10%','90%','90%'
            )
        )

    def __init__(self, size: tuple[int, int],l:Layer):
        self.layer = l
        super().__init__(size)
        bg = BackgroundColor(bg_color)
        header = self.space.cutTopSpace(40)
        header.addObjects(
            Resizer(
                BoxText((0,0),(1,1),'Keybinds Menu',text_color,title_font),
                '0','0','-1','-1'
            ),
            bg,
            Aligner(
                a:=AddImage(
                    Button(
                        (0,0),(40,30),exit_button_cs,None,lambda : toNone(base_layer.removeLayer(self.layer),keybinds.save())
                    ),
                    Exit
                ),
                1,0
            ),
            WithRespectTo(
                AddText(
                    Button((-15,3),(70,30),selection_cs.mix(ColorScheme(255,255,255),0.1),keybinds.reset),
                    'Reset', text_color,getFont(FONT_NAME.OPEN_SANS,20)
                ),
                a,0,0,1,0
            )
        )
        grid = Grid(Rect(1,1,1,1),(2,0),(['30%-`','70%-`'],'~-`'),('5','5min1%'))
        fontRule = FontRule()
        for action in keybinds.getAllActions():
            binds = keybinds.getActionKeybinds(action)
            lighten = ColorScheme(255,255,255)
            cs = selection_cs.mix(lighten,0.1)
            cs.variance = 10
            def update(state,binds,text:BoxText):
                hash = sum(map(id,binds))
                if state.prevhash != hash :
                    text.setText(', '.join([reprKey(key,mod) for key,mod in binds]) or '<No Key Bound>') 
                    state.prevhash = hash
            grid.addRow([
                BoxText((0,0),(1,1),action,(255,255,255),getNewFont(FONT_NAME.YOUTUBE_REGULAR),1).setFontRule(fontRule),
                ZStack(
                    Button((1,1),(1,1),cs,None,lambda action=action:toNone(self.layer.addLayer(ActionModifierUI(self.layer.rect.size,action)))),
                    a:=BoxText((0,0),(1,1),', '.join([reprKey(key,mod) for key,mod in binds]) or '<No Key Bound>',text_color,getNewFont(FONT_NAME.YOUTUBE_REGULAR)).setFontRule(fontRule),
                    UpdateFunction(lambda state,input,/,a=a,binds=binds:update(state,binds,a),prevhash=sum(map(id,binds)))
                ),
            ])

        self.space.addObjects(
            bg,
            Resizer(
                grid,
                '0','0','100%-50','100%-10'
            ),
        )

    @Tracer().traceas('KeybindMenu')
    def onResize(self, size: tuple[int, int]):
        return super().onResize(size)
        
    def update(self, input: Input):
        super().update(input)
        input.clearALL()
class Direction:
    L = 0
    T = 1
    R = 2
    B = 3
class CustomBorder:

    def __init__(self,window:pygame.Window) -> None:
        self.window = window
        self.rect = Rect((0,0),window.size)
        self.resizing = False
        self.dir:list[bool]
        self.rad = rad = 5
        self.border_rects = [
            self.rect.copy(),
            self.rect.copy(),
            self.rect.copy(),
            self.rect.copy()
        ]
        self._m_start_pos:tuple[int,int]
        self.border_colliding = [False]*len(self.border_rects)
        self.border_rects[Direction.L].width = rad
        self.border_rects[Direction.T].height = rad
        self.border_rects[Direction.B].height = rad
        self.border_rects[Direction.B].bottom = self.rect.bottom
        self.border_rects[Direction.R].width = rad
        self.border_rects[Direction.R].right = self.rect.right
        self._p_colliding = False
        self.active = True

    def resize(self,size:tuple[int,int]):
        self.rect.size = size
        for r in self.border_rects:
            r.topleft = self.rect.topleft
            r.size = self.rect.size
        self.border_rects[Direction.L].width = self.rad
        self.border_rects[Direction.T].height = self.rad
        self.border_rects[Direction.B].height = self.rad
        self.border_rects[Direction.B].bottom = self.rect.bottom
        self.border_rects[Direction.R].width = self.rad
        self.border_rects[Direction.R].right = self.rect.right

    def update(self,input:Input):
        if not self.active: return
        if self.rect.size!=self.window.size and not self.resizing:
            self.resize(self.window.size)
        for i,r in enumerate(self.border_rects):
            self.border_colliding[i] = r.collidepoint(input.mpos)
        if not self.resizing:
            if any(self.border_colliding):
                if input.mb1d:
                    input.mb1d = False
                    self.resizing = True
                    self.dir = self.border_colliding.copy()
                    self._m_start_pos = pygame.mouse.get_pos(True)
                    self._w_start_pos = self.window.position
                    self._w_start_size = self.window.size
                c = self.border_colliding
                if c[Direction.L] and c[Direction.T]:
                    pygame.mouse.set_cursor(const.SYSTEM_CURSOR_SIZENWSE)
                elif c[Direction.L] and c[Direction.B]:
                    pygame.mouse.set_cursor(const.SYSTEM_CURSOR_SIZENESW)
                elif c[Direction.R] and c[Direction.T]:
                    pygame.mouse.set_cursor(const.SYSTEM_CURSOR_SIZENESW)
                elif c[Direction.R] and c[Direction.B]:
                    pygame.mouse.set_cursor(const.SYSTEM_CURSOR_SIZENWSE)
                elif c[Direction.L] or c[Direction.R]:
                    pygame.mouse.set_cursor(const.SYSTEM_CURSOR_SIZEWE)
                elif c[Direction.T] or c[Direction.B]:
                    pygame.mouse.set_cursor(const.SYSTEM_CURSOR_SIZENS)
            elif self._p_colliding:
                pygame.mouse.set_cursor(const.SYSTEM_CURSOR_ARROW)
            self._p_colliding = any(self.border_colliding)
                
        elif self.resizing:
            if input.mb1u:
                self.resizing = False
                input.mb1u = False
            else:
                g_mpos = pygame.mouse.get_pos(True)
                dif_x = g_mpos[0] - self._m_start_pos[0]
                dif_y = g_mpos[1] - self._m_start_pos[1]
                new_pos = list(self.window.position)
                new_size = list(self.window.size)
                if self.dir[Direction.L]:
                    new_size[0] = max(self._w_start_size[0]-dif_x,self.window.minimum_size[0])
                    new_pos[0] = self._w_start_pos[0]+self._w_start_size[0] - new_size[0]
                if self.dir[Direction.R]:
                    new_size[0] = max(self._w_start_size[0]+dif_x,self.window.minimum_size[0])
                if self.dir[Direction.T]:
                    new_size[1] = max(self._w_start_size[1]-dif_y,self.window.minimum_size[1])
                    new_pos[1] = self._w_start_pos[1]+self._w_start_size[1] - new_size[1]
                if self.dir[Direction.B]:
                    new_size[1] = max(self._w_start_size[1]+dif_y,self.window.minimum_size[1])

                self.window.position = tuple(new_pos)
                self.window.size = tuple(new_size)
                
class WindowDrag(DrawBase):
    def __init__(self,rect:Rect,window:pygame.Window) -> None:
        self.window = window
        self.dragging = False
        self.rect = rect


    def update(self,input:Input):

        if not self.dragging:
            if input.mb1d and self.rect.collidepoint(input.mpos):
                self.dragging = True
                self._w_start_pos = self.window.position
                self._m_start_pos = pygame.mouse.get_pos(True)
        else:
            if input.mb1u:
                self.dragging = False
            g_mpos = pygame.mouse.get_pos(True)
            rel_x = g_mpos[0]-self._m_start_pos[0]
            rel_y = g_mpos[1]-self._m_start_pos[1]
            new_w_pos = (self._w_start_pos[0] + rel_x,
                            self._w_start_pos[1] + rel_y)
            self.window.position = new_w_pos

class MiniplayerSettings(Layer):
    @classmethod
    def showOnLayer(cls,l:Layer):
        new_layer = l.addLayer()
        inst = cls(l.rect.size,l,new_layer)
        new_layer.space.addObject(
            Resizer(
                inst,
                '50%-(40%min100)','10%','50%+(40%min100)','90%min(~+200.0)'
            )
        )
    def __init__(self,size:tuple[int,int],l:Layer,l2:Layer):
        super().__init__(size)
        self.layer = l
        self.other_layer = l2
        grid = Grid(Rect(0,0,200,200),(2,0),(['20','100%-20-`*2'],'20'),('2','2'))
        settings_ = {
            'miniplayer_borderless':'Borderless',
            'miniplayer_always_on_top':'Always On Top'
        }
        layoout = ColorLayout(
            (40,40,40),
            (4,4,4),
            (200,200,200)
        )
        for setting,display_name in settings_.items():
            ssv = settings.makeSharedSettingsValue(setting)
            grid.addRow(
                [
                    CheckBoxLone((0,0),(1,1),layoout,ssv.set,ssv.get()),
                    BoxText((0,0),(1,1),display_name,text_color,getNewFont(FONT_NAME.YOUTUBE_REGULAR)).setFontRule(FontRule())
                ]
            )
        self.space.addObjects(
            BackgroundColor(bg_color),
            Resizer.fill(
               grid
            )
        )

    def onResize(self, size: tuple[int, int]):
        super().onResize(size)

    def update(self, input: Input):
        super().update(input)
        if input.consumeKey(const.K_ESCAPE) or (input.mb1d and not self.rect.collidepoint(input.mpos)):
            input.mb1d = False
            self.layer.removeLayer(self.other_layer)
        input.clearALL()

def updateYTDLP(l:Layer):
    pipe = Async.Pipe()
    done = ObjectValue(False)
    r = Rect(0,0,400,70)
    new_layer = base_layer.addLayer()
    new_layer.space.addObjects(BackgroundColor(),Aligner(DownloadingStatus(r,pipe),0.5,0.5))
    done.obj_change_event.register(lambda x: [None,l.removeLayer(new_layer,True)][x])
    Installer.update_ytdlp_async(done,pipe)

searching = False
is_online = ObjectValue(False)


def makePlaylistProtocol():
    p = database.makePlaylist(f'New Playlist #{len(database.playlists)+1}','')
    showPlaylist(p)

def deletePlaylistProtocol(p:Playlist):
    database.removePlaylist(p)
    if playlistDisplay.playlist is p:
        base_layer.space.setActive('home')

def showPlaylist(playlist:Playlist):
  playlistDisplay.setPlaylist(playlist)
  base_layer.space.setActive('playlist')

playlistDisplay = PlaylistDisplay((500,500))
export_checked:dict[Song,bool] = {}

export_dropdown=PickManySongs((0,0),(25,50),100,selection_cs,checked=export_checked)