from src import gui
from pygame import transform,Surface,constants as const,draw
from pygame import font
from pygame import image
from src.utils2 import cache
ShuffleOn = image.load('./Assets/Images/shuffle0.png').convert_alpha()
ShuffleOff = image.load('./Assets/Images/shuffle1.png').convert_alpha()
Repeat0 = image.load('./Assets/Images/repeat0.png').convert_alpha()
Repeat1 = image.load('./Assets/Images/repeat1.png').convert_alpha()
Repeat2 = image.load('./Assets/Images/repeat2.png').convert_alpha()
PrevSong = transform.smoothscale(image.load('./Assets/Images/PrevSongButton.png').convert_alpha(),(22,22))
NextSong = transform.smoothscale(transform.flip(image.load('./Assets/Images/PrevSongButton.png').convert_alpha(),True,False),(22,22))
Paused = transform.smoothscale(image.load('./Assets/Images/NewPaused.png').convert_alpha(),(15,15))
UnPaused = transform.smoothscale(image.load('./Assets/Images/NewPlaying.png').convert_alpha(),(15,15))
Logo = transform.smoothscale(image.load('./Assets/Images/Logo_simple.png').convert_alpha(),(64,64))
Exit = image.load('./Assets/Images/exit.png').convert_alpha()
Settings_img = image.load('./Assets/Images/settings.png').convert_alpha()
Home = image.load('./Assets/Images/home.png').convert_alpha()
Search = image.load('./Assets/Images/search.png').convert_alpha()
Notes = image.load('./Assets/Images/notes.png').convert_alpha()
Download = image.load('./Assets/Images/download.png').convert_alpha()
AudioMute = image.load('./Assets/Images/0.png').convert_alpha()
AudioLowVolume = image.load('./Assets/Images/1.png').convert_alpha()
AudioMediumVolume = image.load('./Assets/Images/2.png').convert_alpha()
AudioHighVolume = image.load('./Assets/Images/3.png').convert_alpha()
MiniPlayer = image.load('./Assets/Images/MiniPlayer.png').convert()
MiniPlayer.set_colorkey((0,0,0))
YT_Logo = transform.smoothscale(image.load('./Assets/Images/YouTube-logo.png').convert(),(30,30))
YT_Logo.set_colorkey((0,0,0))
Itunes_Logo = transform.smoothscale(image.load('./Assets/Images/Itunes-logo.png').convert(),(30,30))
Itunes_Logo.set_colorkey((0,0,0))
folder_img = image.load('./Assets/Images/folder.png').convert()
folder_img.set_colorkey((0,0,0))
file_img = image.load('./Assets/Images/file.png').convert()
folder_img.set_colorkey((0,0,0))
export_img = image.load('./Assets/Images/export.png').convert()
export_img.set_colorkey((0,0,0))
left_arrow_img = image.load('./Assets/Images/left.png').convert()
left_arrow_img.set_colorkey((0,0,0))
right_arrow_img = transform.flip(left_arrow_img,True,False)
right_arrow_img.set_colorkey((0,0,0))
up_arrow_img = transform.rotate(right_arrow_img,90)
up_arrow_img.set_colorkey((0,0,0))
adjust_img = image.load('./Assets/Images/adjust.png').convert_alpha()
MinimizeWindow = Surface((30,30))
r = MinimizeWindow.get_rect()
r.width = MinimizeWindow.get_width()*0.4
r.height = 1
r.center = MinimizeWindow.get_width()//2,MinimizeWindow.get_height()*0.55
draw.rect(MinimizeWindow,(200,200,200),r)

MinimizeWindow.set_colorkey((0,0,0))
MaximizeWindow = Surface((30,30))
r = MaximizeWindow.get_rect()
r.width = MaximizeWindow.get_width()*0.4
r.height = 1
r.center = MaximizeWindow.get_width()//2,MaximizeWindow.get_height()*0.55
draw.rect(MaximizeWindow,(200,200,200),r)
MaximizeWindow.set_colorkey((0,0,0))

RestoreWindow = Surface((30,30))
r = RestoreWindow.get_rect()
r.height = r.height * 0.3
r.width = r.height
r.center = RestoreWindow.get_width()//2,RestoreWindow.get_height()//2
draw.rect(RestoreWindow,(200,200,200),r.move(2,-2),2)
draw.rect(RestoreWindow,(200,200,200),r,2)
RestoreWindow.set_colorkey((0,0,0))

# FullSizeLogo = transform.smoothscale(image.load('./Assets/Images/Logo_simple.png'),framework.getWindowSize())
PlaylistPlayButton = transform.smoothscale(image.load('./Assets/Images/NewPaused.png'),(20,20))
PlaylistPlayButton.set_colorkey((253,253,253))
upArrow = image.load("./Assets/Images/uparrow.png").convert_alpha()
downArrow = image.load("./Assets/Images/downarrow.png").convert_alpha()

### FONTS = 
class FontName(str): pass
class FONT_NAME:
    YOUTUBE_REGULAR = FontName('YoutubeSansRegular.otf')
    YOUTUBE_EXTRA_BOLD = FontName('YoutubeSansExtrabold.otf')
    OPEN_SANS = FontName('all.ttf')
    ARIAL = FontName('Arial')
    ROBOTO = FontName('Roboto')


@cache
def getFont(name:FontName,size:int=20,**kwargs):
    return getNewFont(name,size,**kwargs)

def getNewFont(name:FontName,size:int=20,**kwargs):
    try:
        return font.Font("./Assets/Fonts/"+name,size)
    except:
        return font.SysFont(name,size,**kwargs)
font_default = getFont(FONT_NAME.OPEN_SANS)
title_font = getFont(FONT_NAME.OPEN_SANS,22)
subtitle_font = getFont(FONT_NAME.OPEN_SANS,18)
yt_subtitle_font = getFont(FONT_NAME.OPEN_SANS,18)
settings_button_font = getFont(FONT_NAME.OPEN_SANS,17)
option_font = getFont(FONT_NAME.ARIAL,14)
inputbox_cl = gui.ColorLayout((15,15,15),(200,200,200),(55,55,55))
dark_inputbox_cl = gui.ColorLayout((200,200,200),(50,50,50))
selection_cs = gui.ColorScheme(14,14,14)
settings_button_cs = gui.ColorScheme(50,50,50)
light_selection_cs = gui.ColorScheme(40,40,40)
primary_cs = gui.ColorScheme(200,200,200)
dark_primary_cs = gui.ColorScheme(140,140,140)
exit_button_cs = gui.theme.CloseButtonColorScheme((255,50,50),(50,50,50))
warning_color = exit_button_cs.color
text_color = (255,255,255)
dim_text_color = (150,150,150)
grey_color = (100,100,100)
primary_color = (255,255,255)
dark_primary_color = (50,50,50)
secondary_color = (100,130,75)
tertiary_color = (150,75,150)
bg_color = (14,14,14)
primary_layout = gui.ColorLayout(primary_color,grey_color,tertiary_color)
del gui, transform

