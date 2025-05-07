#D2LMTY
import sys
import time
import pygame
import _thread
pygame.init()
from src import Installer
from src import gui
from src.Utils import Async
from src.Utils import logger
from src.DownloadingStatus import DownloadingStatus
from pygame import font
from pygame import Rect
from pygame import Surface
from pygame import Clock
from pygame import transform
from pygame import scrap

if sys.platform == 'win32':
  import ctypes
  try:
    ctypes.windll.user32.SetProcessDPIAware()
  except: 
    pass
  del ctypes
   
from src.Input import getInput

##############################################
# Before Main App Startup Check Dependencies #
##############################################
if to_install := [dep for dep in Installer.dependencies if not dep.hasDependency()]:
  base = gui.Layer((100,100))
  logger.log("Dependencies missing: ",to_install)
  w = pygame.Window('Missing Dependencies', (530,300))
  text_color = (255,255,255) #white
  font_default = font.SysFont(None,25)
  download_ = gui.utils.ObjectValue(False)
  def download():
    pipe = Async.Pipe()
    r = Rect(0,0,400,140)
    r.center = base.rect.center
    (nl:=base.addLayer()).space.addObjects(
      gui.ui.BackgroundColor(),DownloadingStatus(r,pipe,5).setRetryCallback(lambda l=nl: (base.removeLayer(l),download_.set(True))))
    def _download():
      #this runs in another thread 
      for dep in to_install:
        try:
          dep.installDependency(pipe)
        except ConnectionError:
          pipe.title.set('Connection Error')
          pipe.description.set('Ensure you have a stable Internet Connection')
          return

      running.set(False)
    _thread.start_new_thread(_download,())
    
  base.space.addObjects(
    gui.ui.BackgroundColor(),
    gui.ui.positioners.Aligner(
      gui.ui.Text((0,0),'There are missing dependencies this application relies on.',text_color,font_default),
      0.5,0.2
    ),
    gui.ui.positioners.Aligner(
      gui.ui.Text((0,font_default.get_height()),'Missing:',text_color,font_default),
      0.5,0.2
    ),
    *[gui.ui.positioners.Aligner(
      gui.ui.Text((0,(font_default.get_height()+2)*(i+1)),'- '+dep.name,text_color,font_default),
      0.5,0.2
    ) for i,dep in enumerate(to_install,start=1)],
    gui.ui.positioners.Aligner(
      gui.ui.AddText(
        gui.ui.Button((0,0),(100,40),gui.ColorScheme(50,150,50),None,download),
        'Download',text_color,font_default
      ),
      0.5,0.7
    ),
  )
  clock = Clock()
  running = gui.ObjectValue(True)
  base.resize(w.size)
  while running.get():
    myInput = getInput()
    if myInput.quitEvent:
      sys.exit()
    if download_.get():
      download()
      download_.set(False)
    base.update(myInput)
    base.draw(w.get_surface())
    w.flip()
    clock.tick(30)
  base.resetEverything()
  w.destroy()

del Installer
del to_install

####################
# Main App Startup #
####################
t_start_main_app_startup = time.perf_counter()
logger.log("Main App Startup")
from src.Settings import settings,UP_TO_DATE
# from src.framework import * #type: ignore
from src.AppFramework import MusicPlayer,keybinds
pygame.init()
window = pygame.Window(settings.windowName,size=(900,600),resizable=True,borderless=settings.borderless)
window.get_surface()
from src.assets import * #type: ignore
import src.Utils.Async as Async
from src.UIFramework import * #type: ignore
from src.UIFramework import  showPlaylist,toNone,updateYTDLP
base = base_layer
title_bar_height = 30
title_bar = Layer((window.size[0],30))
title_bar.space.addObjects(
  gui.ui.BackgroundColor(exit_button_cs.getInactive()),
  gui.ui.Resizer(
    a:=gui.ui.BoxText((0,0),(100,100),settings.windowName,text_color,getNewFont(FONT_NAME.OPEN_SANS),0,offset=(3,0)).setFontRule(FontRule(max=20)),
    '0','0','100%-40-40','100%'
  ),
  toNone(settings.makeSharedSettingsValue('windowName').on_set.register(a.setText)),
  gui.ui.Resizer(
    gui.ui.AddImage(
      ex:=gui.ui.Button((0,0),(1,1),exit_button_cs,None,lambda : pygame.event.post(pygame.Event(const.QUIT))),
      Exit,
    ),
    '100%-40','0','100%','100%'
  ),
  gui.ui.positioners.Resizer(
    gui.ui.AddImage(
      mi:=gui.ui.Button((0,0),(1,1),exit_button_cs,None,window.minimize),
      MinimizeWindow,
    ),
    '100%-40-40','0','~+40','100%'
  ),
  gui.ui.positioners.Resizer.fill(
    WindowDrag(Rect(0,0,1,1),window)
  ),
)
window.minimum_size = (650,400)

if settings.scroll_smoothing == 5: #migration from version 14 - 20 (yup i skipped lots of versions)
  settings.scroll_smoothing = 0.1
gui.settings.wheel_sensitivity = 40
gui.settings.scroll_smoothing = settings.scroll_smoothing

window.set_icon(Logo)

MusicPlayer.pause_time = settings.pause_fade_time_ms / 1000

r_delay = settings.makeSharedSettingsValue('key_repeat_delay')
r_interval = settings.makeSharedSettingsValue('key_repeat_interval')

pygame.key.set_repeat(r_delay.get(),r_interval.get())
r_delay.on_set.register(lambda x: pygame.key.set_repeat(x,r_interval.get()))
r_interval.on_set.register(lambda x: pygame.key.set_repeat(r_delay.get(),x))

settings.makeSharedSettingsValue('windowName').on_set.register(lambda x: setattr(window,'title',x))  
settings.makeSharedSettingsValue('scroll_smoothing').on_set.register(gui.settings.setter('scroll_smoothing'))
settings.makeSharedSettingsValue('pause_fade_time_ms').on_set.register(lambda pftms:setattr(MusicPlayer,'pause_time',pftms/1000))

base.resize(window.size)
bottom_border = base.space.cutBottomSpace(70)
left_border = base.space.cutLeftSpace(120)

  
if database.playlists:
  playlistDisplay.setPlaylist(database.playlists[0])
fps_text = gui.ui.Text((30,128),f'FPS: {settings.fps}',text_color,settings_button_font)
fade_time_text = gui.ui.Text((30,190),f'Fade Duration: {settings.pause_fade_time_ms}',text_color,settings_button_font)
settings.makeSharedSettingsValue('pause_fade_time_ms').on_set.register(lambda x: fade_time_text.setText(f"Fade Duration: {x:0>3}ms"))
settings.makeSharedSettingsValue('fps').on_set.register(lambda x: fps_text.setText(f"FPS:{x:>4}"))
d_search = gui.ObjectValue('')
from src.DownloadUI import DownloaderLayer
downloader_layer = DownloaderLayer(base.rect.size)

from src.explorer import FileExplorer
from src.exporter import FormatTypes,formats
export_dest = None
format:gui.ObjectValue[FormatTypes] = gui.ObjectValue('ogg')
export_on_path = gui.ObjectValue(os.path.abspath(os.path.expanduser('~')))
from src.UIFramework import LocalSongsMenu
from src.importer import ImporterMenu

class Switcher:
  def update(self,input:gui.Input):
    if input.consumeKeys(*keybinds.getActionKeybinds('Home')):
      base.space.setActive('home')
    elif input.consumeKeys(*keybinds.getActionKeybinds('Settings')):
      base.space.setActive('settings')
    elif input.consumeKeys(*keybinds.getActionKeybinds('Library')):
      base.space.setActive('all songs')
    elif input.consumeKeys(*keybinds.getActionKeybinds('Download')):
      base.space.setActive('download')
      
def queueBorderless(borderless:bool):
  global next_borderless
  next_borderless = borderless

def setBorderless(borderless:bool):
  if app_state == STATE_MAINAPP:
    p_size = window.size
    n_size = window.size[0],window.size[1] + (30 if borderless else -30)
    new_pos = (pygame.Vector2(window.position) + pygame.Vector2(p_size) - pygame.Vector2(n_size))
    

    window.position = new_pos.x,new_pos.y
    window.size = n_size
    window.borderless = borderless
    window.resizable = True

  if borderless:
    header = base.insertCut(0,'top',30)
  else:
    base.removeCut('top',0)

settings.makeSharedSettingsValue('borderless').on_set.register(queueBorderless)

base.space.makeContainer(
  {
    'home': [
      gui.ui.BackgroundColor(),
      gui.ui.Text((30,30),'Welcome To Fake Spotify 5.5.2!',(255,255,255),font_default),
      gui.ui.Text((30,60),'Author | Developer: Leo',(255,255,255),font_default),
      gui.ui.Text((30,95),'Improvements: Improved Download Screen',(255,255,255),font_default),
      gui.ui.Text((30,130),'Downgrades: None',(255,255,255),font_default),
      gui.ui.Text((30,155),'Any and All feedback is desired.',(255,255,255),font_default),
      gui.ui.Text((30,180),'Contact: <Redacted> (checked infrequently)',(255,255,255),font_default)
    ],
    'settings': [
      gui.ui.Text((30,10),'Settings',(255,255,255),title_font),
      gui.ui.AddText(
        gui.ui.Switch((30,50),(30,30),settings_button_cs,settings.setTryFindSong).setState(settings.tryFindSong),
        'Try Find Song',(255,255,255),settings_button_font,1,alignment_x=0,offset_x=5
      ),
      gui.ui.AddText(
        gui.ui.Switch((30,90),(30,30),settings_button_cs,settings.makeSharedSettingsValue('borderless').set).setState(settings.borderless),
        'Custom Titlebar', (255,255,255),settings_button_font,1,alignment_x=0,offset_x=5
      ),
      fps_text,
      gui.ui.positioners.WithRespectTo(
        gui.ui.SquareSlider((2,0),(100,20),primary_layout,range(10,101,5),settings.makeSharedSettingsValue('fps').set,settings.fps),
        fps_text,1,0.5,0
      ),
      a:=gui.ui.Text((30,160),'Window Name:',text_color,settings_button_font),
      gui.ui.InputBoxOneLine((a.rect.right+5,160),(200,25),primary_layout,settings.makeSharedSettingsValue('windowName').set,settings_button_font).setText(settings.windowName).setMaxChars(25),
      fade_time_text,
      gui.ui.SquareSlider((208,190),(100,20),primary_layout,range(0,501,10),settings.makeSharedSettingsValue('pause_fade_time_ms').set,int(settings.pause_fade_time_ms)),
      a:=gui.ui.Text((30,220),'Key Repeating',(255,255,255),settings_button_font),
      a:=gui.ui.Text((50,245),f'Delay {r_delay.get():>4} ms',(255,255,255),settings_button_font),
      toNone(r_delay.on_set.register(lambda x,a=a: a.setText(f"Delay: {(x or '----'):>4} ms"))),
      toNone(r_delay.on_set.register(lambda x:r_interval.set(r_interval.get()))),
      gui.ui.SquareSlider((a.rect.right+13,245),(150,20),primary_layout,range(0,1001,10),r_delay.set,r_delay.get(),strict_iv=False),
      # InputBoxOneLine((a.rect.right+3,250),(30,settings_button_font.get_height()+4),primary_layout,lambda x:r_delay.set(int(x or '0')),settings_button_font).setMaxChars(4).setRestrictInputChain(u_const.DIGITS),
      a:=gui.ui.Text((50,270),f'Interval {(r_interval.get() or r_delay.get()):>3} ms:',(255,255,255),settings_button_font),
      toNone(r_interval.on_set.register(lambda x,a=a: a.setText(f"Interval: {(x or r_delay.get()):>3} ms"))),
      gui.ui.SquareSlider((a.rect.right+13,270),(150,20),primary_layout,range(0,501,5),r_interval.set,r_interval.get(),strict_iv=False),
      a:=gui.ui.Text((30,300),f'Scroll Smoothing: {settings.scroll_smoothing:.3f}',text_color,settings_button_font),
      toNone(settings.makeSharedSettingsValue('scroll_smoothing').on_set.register(lambda x,a=a: a.setText(f'Scroll Smoothing: {x:.3f}'))),
      SquareSlider((a.rect.right+10,a.rect.centery-10),(80,20),primary_layout,[x/1000 for x in range(5,205,5)],settings.makeSharedSettingsValue('scroll_smoothing').set,settings.scroll_smoothing), #type: ignore
      gui.ui.AddText(gui.ui.Button((30,330),(180,30),light_selection_cs,None,lambda :KeyBindMenu.showOnLayer(base)),'Configure Keybinds',text_color,settings_button_font),
      gui.ui.AddText(gui.ui.Button((30,370),(150,30),light_selection_cs,None,lambda : updateYTDLP(base)),'Update YT-DLP',text_color,settings_button_font),
      
      #Export Songs Button
      gui.ui.positioners.Aligner(
        gui.ui.AddImage(
          gui.ui.Button((-5,5),(40,40),settings_button_cs,None,lambda :base.space.setActive('export')),
          export_img
        ),
        1,0,1,0
      )
    ],
    'all songs' : [
      gui.ui.positioners.Resizer.fill(
        LocalSongsMenu((100,100))
      )
    ], 
    'export': [
      gui.ui.positioners.Resizer(export_dropdown,
        '10','80','100%-20','100%-60'     
      ),
      gui.ui.positioners.Resizer(gui.ui.ScrollbarConsuming((0,0),(10,20),1,primary_layout).linkToDropdown(export_dropdown),
              '100%-30','80','100%-20','100%-60'
      ),
      SongSearchBox(10,10,28,export_dropdown),
      #QOL Buttons
      gui.ui.AddText(
        gui.ui.Button((10,45),(80,25),settings_button_cs,None,export_dropdown.selectAllShowing),
        'Select All',(255,255,255),getFont(FONT_NAME.OPEN_SANS,16)
      ),
      gui.ui.AddText(
        gui.ui.Button((95,45),(100,25),settings_button_cs,None,export_dropdown.deselectAllShowing),
        'Select None',(255,255,255),getFont(FONT_NAME.OPEN_SANS,16)
      ),
      gui.ui.AddText(
        gui.ui.Button((200,45),(70,25),settings_button_cs,None,export_dropdown.toggleAllShowing),
        'Invert',(255,255,255),getFont(FONT_NAME.OPEN_SANS,16)
      ),
      gui.ui.positioners.Resizer(
        path_text :=gui.ui.AddText(
        gui.ui.Button((90,-20),(500,25),gui.ColorScheme(80,80,80),None,
               lambda:toNone((nl:=base.addLayer()).space.addObject(FileExplorer(nl,'~',export_on_path).setOnlyDir()))),export_on_path.get(),(255,255,255),getFont(FONT_NAME.ARIAL,16),0,alignment_x=0
        ),
        '90','100%-45','100%-100','100%-20'
      ),
      gui.ui.positioners.Aligner(
        Dropdown((20,-20),(60,25),base,50,gui.ColorScheme(80,200,80),list(formats),format.set #type: ignore
                 ,getFont(FONT_NAME.OPEN_SANS,16)).setWord('ogg')
        ,0,1,0,1
      ),
      gui.ui.positioners.Aligner(
        gui.ui.AddText(
          gui.ui.Button((-20,-20),(70,25),gui.ColorScheme(80,200,80),None,
                lambda : toNone((nl:=base.addLayer()).space.addObject(ExportTrackerPopup(nl,export_checked,export_on_path.get(),format.get())) if any(export_checked.values()) else None)) ,#type: ignore
              'Export',(255,255,255),getFont(FONT_NAME.ARIAL,18)
          ),
        1,1,1,1
      ),
    ],
    'playlist': [
      playlistDisplay
    ],
    'download' : [
      gui.ui.positioners.Resizer(downloader_layer,'0','0','100%','100%'),
    ],
    'import' : [
      gui.ui.positioners.Resizer.fill(
        ImporterMenu((100,100))
      )
    ]
  },
  'home',
  [
    gui.ui.BackgroundColor(),
    Switcher()
  ]
)
export_on_path.obj_change_event.register(
  path_text.setText
)



cs = ColorScheme(50,50,50)
txt_color = (255,255,255)
left_border.addObjects(
  gui.ui.BackgroundColor(primary_color),
  gui.ui.AddImage(gui.ui.Button((0,0),(left_border.rect.width,50),cs,lambda : base.space.setActive('home')),Home),
  gui.ui.AddImage(gui.ui.Button((0,53),(left_border.rect.width,50),cs,lambda : base.space.setActive('settings')),Settings_img),
  gui.ui.AddImage(gui.ui.Button((0,106),(left_border.rect.width,50),cs,lambda : base.space.setActive('all songs')),Notes),
  gui.ui.AddImage(gui.ui.Button((0,159),(left_border.rect.width,50),cs,lambda : base.space.setActive('download')),Download),
  gui.ui.positioners.Resizer(
    PickPlaylist((0,0),(left_border.rect.width,left_border.rect.height-210),showPlaylist,(50,50,50)),
    '0','210','100%','100%'
  )
)
MusicPlayer.set_volume(settings.volume)
MusicPlayer.songQueue.shuffle = settings.shuffle
MusicPlayer.songQueue.repeat_level = settings.repeat_level

bottom_border.addObjects(
  gui.ui.BackgroundColor(),
  gui.ui.positioners.Aligner(
    VolumeSlider((-20,-3),(100,20)),
    1,.5,1,0.5
  ),
  gui.ui.positioners.Aligner(
    VolumeIcon((-122,-1-3)),
    1,.5,1,.5
  ),
  gui.ui.positioners.Aligner(
    gui.ui.AddImage(
      gui.ui.Button((-155,0-3),(30,30),selection_cs,lambda :queueAppState(STATE_MINIPLAYER)),
      MiniPlayer
    ),
    1,0.5
  ),
  KeyBoundFunction(lambda :queueAppState(STATE_MINIPLAYER),keybinds.getActionKeybinds('Miniplayer')), #Support For Keybind
  gui.ui.positioners.Aligner(
    PauseButton((0,0)),
    0.5,0.4
  ),
  gui.ui.positioners.Resizer(
    TrackingSlider((0,0),(10,20)),
    '30%','100%-20-2','70%','100%-2'
  ),
  gui.ui.positioners.Aligner(
    SongLength((6,-4),getFont(FONT_NAME.ARIAL,15),'0:00',primary_color),
    0.7,1,0,1
  ),
  gui.ui.positioners.Aligner(
    SongLengthPassed((-6,-4),getFont(FONT_NAME.ARIAL,15),'0:00',primary_color),
    0.3,1,1,1
  ),
  gui.ui.positioners.Aligner(
    gui.ui.AddImage(
      gui.ui.Button((50,0),(30,30),selection_cs,None,MusicPlayer.finishSong),
      NextSong
    ),
    0.5,0.4
  ),
  gui.ui.positioners.Aligner(
    gui.ui.AddImage(
      gui.ui.Button((-50,0),(30,30),selection_cs,None,MusicPlayer.backButton),
      PrevSong
    ),
    0.5,0.4
  ),
  gui.ui.positioners.Aligner(
    RepeatButton((90,1),(30,30)),
    0.5,0.4
  ),
  gui.ui.positioners.Aligner(
    gui.ui.ButtonSwitch((-90,3),(30,30),[ShuffleOff,ShuffleOn],settings.shuffle,MusicPlayer.songQueue.setShuffle),
    0.5,0.4
  ),
  gui.ui.positioners.Resizer(
    SongTitle((5,15),getFont(FONT_NAME.OPEN_SANS,15)),
    '5','15','30%','~+20'
  ),
  gui.ui.positioners.Resizer(
    SongArtists((5,35),getFont(FONT_NAME.OPEN_SANS,13),'',(160,160,160)),
    '5','35','30%-40','~+20'
  ),
  KeyBoundFunction(MusicPlayer.backButton,keybinds.getActionKeybinds('Skip Back')),
  KeyBoundFunction(MusicPlayer.finishSong,keybinds.getActionKeybinds('Skip Forward')),
  KeyBoundFunction(MusicPlayer.incVolume,keybinds.getActionKeybinds('Volume Up')),
  KeyBoundFunction(MusicPlayer.decVolume,keybinds.getActionKeybinds('Volume Down'))
)

if not UP_TO_DATE:
  logger.log("New Update Detected")
  l = base.addLayer()
  r = Rect(0,0,350,200)
  options = ForceFocusOptionsBaseCanEscape(l,r)
  l.space.addObject(
    Aligner(options,0.5,0.5))
  options.addObjects(
    BackgroundColor(bg_color),
    ColorArea((0,0),(0,25),(50,50,50)),
    Aligner(
      AddImage(
        Button((0,0),(30,25),exit_button_cs,None,options.removeLayer),
        Exit
      ),
      1,0,1,0
    ),
    Text((3,0),'Notification',text_color,getFont(FONT_NAME.ARIAL)),
    Text((5,40),'A New Update Is Available!',text_color,getFont(FONT_NAME.ARIAL,16)),
    Text((5,65),'You can access this new update via downloader.',text_color,getFont(FONT_NAME.ARIAL,16)),
    a:=Text((5,90),'Copy the link to the downloader',text_color,getFont(FONT_NAME.ARIAL,16)),
    AddText(
      Button((a.rect.right+3,90),(36,20),selection_cs,lambda : scrap.put_text('https://lgarciasanchez5450.github.io/static/assets/mysetup_music.exe')),
      'here',text_color,getFont(FONT_NAME.ARIAL,16,italic = True)
    ),
    Aligner(
      AddText(
        Button((0,-20),(40,26),settings_button_cs,options.removeLayer),
        'Ok',text_color,subtitle_font
      ),.5,1,.5,1
    )
  ) 


if settings.borderless:
  header = base.insertCut(0,'top',30)
  base.resize(base.rect.size)

miniplayer_base.space.addObjects(
  BackgroundColor(),
  Aligner(
    Image((0,0),Notes),0.5,0.5
  ),
  Resizer(
    TrackingSlider((0,0),(10,20)),
    '0%','100%-10','100%','100%-5'
  ),
  
  Resizer.fill(
    reg:=Region(Rect(0,0,1,1)).addObjects(
      Aligner(
        AddText(
          Button((5,5),(30,30),selection_cs,None,lambda : queueAppState(STATE_MAINAPP)),
          '‹',text_color,getFont(FONT_NAME.OPEN_SANS,30),offset_y=-4
        ),
        0,0
      ),
      Aligner(
        AddImage(
          Button((-5,5),(30,30),selection_cs,None,lambda : MiniplayerSettings.showOnLayer(miniplayer_base)),
          transform.smoothscale(Settings_img,(32,32))
        ),
        1,0
      ),
      Aligner(
        WithAlpha(
          PauseButton((0,-30)),
          alpha=200
        ),
        0.5,1
      ),
      Aligner(
        WithAlpha(
          AddImage(
            Button((40,-33),(30,30),selection_cs,None,MusicPlayer.finishSong),
          NextSong
          ),
          alpha=200
        ),
        0.5,1
      ),
      Aligner(
        WithAlpha(
          AddImage(
            Button((-40,-33),(30,30),selection_cs,None,MusicPlayer.backButton),
            PrevSong
          ),
          alpha=200
        ),
        0.5,1
      ),
      Resizer(
        SongTitle((0,0),getFont(FONT_NAME.OPEN_SANS,15)),
        '5','100%-33','100%-5','100%-10'
      )
    ),
  ),
  Resizer.fill(
    WindowDrag(Rect(0,0,1,1),window)
  ),
  KeyBoundFunction(MusicPlayer.backButton,keybinds.getActionKeybinds('Skip Back')),
  KeyBoundFunction(MusicPlayer.finishSong,keybinds.getActionKeybinds('Skip Forward')),
  KeyBoundFunction(MusicPlayer.incVolume,keybinds.getActionKeybinds('Volume Up')),
  KeyBoundFunction(MusicPlayer.decVolume,keybinds.getActionKeybinds('Volume Down'))
)
def queueAppState(state:int):
  global next_app_state
  next_app_state = state
def setAppState(state:int):
  p_size = window.size
  global app_state,base
  if state == STATE_MINIPLAYER:
    window.minimum_size = (150,150)
    if settings.miniplayer_pos is None:
      new_pos = (pygame.Vector2(window.position) + pygame.Vector2(p_size) - pygame.Vector2(window.size))
      settings.miniplayer_pos = int(new_pos.x),int(new_pos.y)
    else:
      new_pos = pygame.Vector2(settings.miniplayer_pos)
    window.size = tuple(settings.miniplayer_size)
    window.resizable = True
    window.borderless = settings.miniplayer_borderless
    window.always_on_top = settings.miniplayer_always_on_top
    base = miniplayer_base
  elif state == STATE_MAINAPP:
    if app_state == STATE_MINIPLAYER: #if we were previously in miniplayer
      settings.miniplayer_pos = window.position
      settings.miniplayer_size = list(window.size)
    window.minimum_size = (650,400)
    window.size=(900,600)
    new_pos = (pygame.Vector2(window.position) + pygame.Vector2(p_size) - pygame.Vector2(window.size))
    window.resizable = True
    window.borderless = settings.borderless
    window.always_on_top = False
    base = base_layer
  else: raise ValueError
  window.position = max(0,new_pos.x),max(30,new_pos.y)
  app_state = state
settings_value_mp_borderless = settings.makeSharedSettingsValue('miniplayer_borderless')
settings_value_mp_always_on_top = settings.makeSharedSettingsValue('miniplayer_always_on_top')
settings_value_mp_borderless.on_set.register(
  lambda x: (setattr(window,'borderless',x) if app_state is STATE_MINIPLAYER else None)
)
settings_value_mp_always_on_top.on_set.register(
  lambda x: (setattr(window,'always_on_top',x) if app_state is STATE_MINIPLAYER else None)
)
clock = Clock()
dt = 0.01
STATE_MAINAPP = 1
STATE_MINIPLAYER = 2
next_app_state:None|int = None
next_borderless:None|bool = None
app_state = STATE_MAINAPP
screen = window.get_surface()
c_border = CustomBorder(window)
t_end_main_app_startup = time.perf_counter()
logger.log(f'Main App Startup: {(t_end_main_app_startup-t_start_main_app_startup)*1000:.2f} ms')
try:
  while True:
    if __debug__:
      t_start = time.perf_counter()
    myInput = getInput()
    g_mpos = pygame.mouse.get_pos(True)
    myInput.mousex = g_mpos[0] - window.position[0]
    myInput.mousey = g_mpos[1] - window.position[1]
    if __debug__:
      t_a = time.perf_counter()

    if app_state == STATE_MINIPLAYER:
      if myInput.windowLeave: 
        reg.setActive(False)
      if myInput.windowEnter:
        reg.setActive(True)
    if next_borderless is not None:
      setBorderless(next_borderless)
      next_borderless = None
    if next_app_state is not None:
      setAppState(next_app_state)
      next_app_state = None
    if myInput.quitEvent:
      break
    if window.borderless:
      c_border.update(myInput)
    if window.size != base.rect.size:
      base.resize(window.size)
      title_bar.resize((window.size[0],30))
    if window.borderless:
      title_bar.update(myInput)

      title_bar.draw(screen)
    if __debug__:
      end = False
      if myInput.consumeKey(const.K_F12,const.KMOD_CTRL):
        end = True
        Tracer().clear()
      elif myInput.consumeKey(const.K_F12):
        Tracer().clear()
    myInput.dt = dt
    base.update(myInput)
    Async.manageCoroutines()
    MusicPlayer.update(dt)
    base.draw(screen) #Render Screen Function
    if __debug__:
      t_end = time.perf_counter()
      print('\r',round(1000*(t_end-t_start),3),'ms',round(1000*(t_end-t_a),3),'ms',end='') #type: ignore
      if end: #type: ignore
        break
    window.flip()
    dt = clock.tick(settings.fps) / 1_000
except SystemExit:
  pass
except KeyboardInterrupt:
  pass
except BaseException as base_err:
  import traceback
  import time
  try:
    with open(f"./ExceptionDump {time.ctime().replace(':',' ')}.dmp",'w+') as file:
      traceback.print_exception(base_err,file=file)
  except:
    logger.log("Exception Writing ExceptionDump")
  raise base_err
finally:
  #on quit
  settings.unlock()
  settings.volume = MusicPlayer.volume
  settings.shuffle = MusicPlayer.songQueue.shuffle
  settings.repeat_level = MusicPlayer.songQueue.repeat_level
  settings.lock() 
  keybinds.save()

Tracer().show()