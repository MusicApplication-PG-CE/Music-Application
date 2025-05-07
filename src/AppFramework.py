import pygame
import pygame.locals as const
from collections import deque
from src.Utils import logger
from src.Database.MusicDatabase import Database, Playlist, Song
from src.utils2 import MUSIC_PATH
from src.Utils.Stopwatch import Stopwatch
from src.utils2 import shuffle
from src.Utils.Keybinds import Keybinds
database = Database()
database.loadFromFiles()
database.loadPlaylists()

def _internal_music_load(file:str):
    try:
        pygame.mixer_music.load(file)
    except pygame.error:
        return False
    else:
        return True

class MusicQueue:
    played:deque[Song]
    current:Song|None = None
    queued:deque[Song]
    unshuffled:deque[Song]

    repeat_level = 0
    shuffle = False
    loadedPlaylist:Playlist|None
    """Level of repeat\n
    0 =  No repeat\n
    1 = Repeat playlist when done\n
    2 = Repeat song when song done
    """
    
    def __init__(self):
        self.played = deque()
        self.current = None
        self.queued = deque()
        self.unshuffled = deque()
        database.song_removed_event.register(self.deleteSong)

    def nextSong(self) -> Song|None:
        '''Returns the next song to play, it could be the same one currently playing. if return
        None then no song should be played'''
        if self.current is None:
            logger.log('no song currently playing!')
            return None
        if self.repeat_level == 0:
            if self.queued:
                self.played.append(self.current)
                self.current = self.queued.popleft()
            else:
                return None 
        elif self.repeat_level == 1:
            if self.queued:
                self.played.append(self.current)
                self.current = self.queued.popleft()
            else:
                if self.loadedPlaylist is not None:
                    self.loadPlaylist(self.loadedPlaylist)
                else:
                    self.played.append(self.current)
                    self.queued.extend(self.played)
                    self.played.clear()
                    self.current = self.queued.popleft()
        elif self.repeat_level == 2:
            pass
        return self.current
    
    def setShuffle(self,b:int):
        
        self.shuffle = bool(b)
        if b:
            self.unshuffled = self.queued.copy()
            shuffle(self.queued)
        else:
            self.queued = self.unshuffled

    def deleteSong(self,song:Song):
        self.played = deque(filter(lambda s:s!=song,self.played))
        self.queued = deque(filter(lambda s:s!=song,self.queued))
        self.unshuffled = deque(filter(lambda s:s!=song,self.unshuffled))


    def goBackOneSong(self) -> None:
        if self.current is None: raise ValueError("Must Have a loaded song to go back!")
        if self.played:
            self.queued.appendleft(self.current)
            self.current = self.played.pop()
        else:
            pass

    def loadPlaylist(self,playlist:Playlist,starting_index:int = -1):
        self.loadedPlaylist = playlist
        self.queued.clear()
        songs = playlist.songs[starting_index+1:]
        if self.shuffle:
            shuffle(songs)
        self.queued.extend(songs)
        if starting_index == -1:
            self.current = self.queued.popleft()
        else:
            self.current = playlist.songs[starting_index]       


    def standalonePlaySong(self,song:Song):
        self.loadedPlaylist = None
        self.queued.clear()
        self.current = song
        self.played.clear()


class MusicPlayer:
    songLoaded:bool = False
    donePlaying:bool = False
    volume:float = pygame.mixer_music.get_volume()
    volume_multiplier:float = 1
    target_pause = False
    paused:bool = False
    songQueue = MusicQueue()
    timer = Stopwatch()
    pause_time:float = 0

    
    @classmethod
    def getPaused(cls) -> bool:
        return cls.target_pause
    
    @classmethod
    def setPaused(cls,newVal:bool):
        cls.target_pause = newVal
        if not newVal:
            cls._setPaused(False)
    
    @classmethod
    def _setPaused(cls,pause:bool):
        cls.paused = pause
        if pause:
            cls.timer.pause()
            pygame.mixer_music.pause()
        else:
            cls.timer.unpause()
            pygame.mixer_music.unpause()

    @classmethod
    def pause(cls):
        cls.setPaused(True)

    @classmethod
    def unpause(cls):
        if cls.paused: 
            cls.setPaused(False)

    @classmethod
    def set_volume_multiplier(cls,multiplier:float):
        cls.volume_multiplier= multiplier
        pygame.mixer_music.set_volume(cls.volume * multiplier)

    @classmethod
    def set_volume(cls,volume:float):
        pygame.mixer_music.set_volume(volume * cls.volume_multiplier)
        cls.volume = volume

    @classmethod
    def incVolume(cls,amnt:float = 0.1):
        v = cls.get_volume() + amnt
        if v > 1: v = 1
        elif v < 0: v = 0
        cls.set_volume(v)

    @classmethod
    def decVolume(cls,amnt:float = -0.1):
        v = cls.get_volume() + amnt
        if v > 1: v = 1
        elif v < 0: v = 0
        cls.set_volume(v)

    @classmethod
    def get_volume_real(cls) -> float:
        return pygame.mixer_music.get_volume()
    
    @classmethod
    def get_volume(cls) -> float:
        return cls.volume
    
    @classmethod
    def playSongAbsolute(cls,song:Song):
        cls.playAbsolute(song._fileName)

    @classmethod
    def playAbsolute(cls,songFileName:str):
        song = database.songsByFileName[songFileName]
        if not _internal_music_load(MUSIC_PATH+song._fileName):
            cls.timer.pause()
            cls.timer.reset()
            cls.songLoaded = False
            logger.log(f'Error Loading {song}')
        else:
            cls.songQueue.standalonePlaySong(song)
            cls.timer.reset()
            cls.songLoaded = True
            cls.unpause()
            cls.set_volume_multiplier(1) #Fixed No-Sound On Play Bug.
            assert cls.songQueue.current is not None
            logger.log(f'Playing {cls.songQueue.current}')
            pygame.mixer_music.play()

    @classmethod
    def setPosition(cls,seconds:float):
        if cls.songQueue.current:
            logger.log(seconds, ':',cls.songQueue.current.length_seconds)
            cls.timer.setTime(seconds)
            try:
                pygame.mixer_music.set_pos(seconds) 
                # for some reason when you set the postion of a song close enough to the end of it (approximately .5 secs) 
                # it complains with "Position not implemented for music type"... so this try block is needed to catch that 
                # and just assume that the song must've ended
            except pygame.error:
                cls.finishSong()
        
    @classmethod
    def playPlaylist(cls,playlist:Playlist):
        if not playlist.songs: return
        cls.songQueue.loadPlaylist(playlist)
        assert cls.songQueue.current is not None
        if not _internal_music_load(MUSIC_PATH+cls.songQueue.current._fileName):
            cls.timer.pause()
            cls.timer.reset()
            cls.songLoaded = False
            cls.songQueue.current = None
        else:
            cls.timer.reset()
            cls.songLoaded = True
            cls.unpause()
            logger.log("Playing Playlist: "+playlist.name)
            logger.log("Songs:",playlist.songs)
            logger.log(f'Playing {cls.songQueue.current}')
            pygame.mixer_music.play() 
            cls.set_volume_multiplier(1) #Fixed No-Sound On Play Bug.
            # pygame.mixer_music.unpause() 

    @classmethod
    def getPosition(cls) -> float:
        return cls.timer.timeElapsed()
    
    @classmethod
    def update(cls,dt:float):
        target = float(not cls.target_pause)
        if cls.volume_multiplier != target:
            if cls.pause_time == 0: 
                v_mult = target
            else:
                slope = 1/cls.pause_time * dt
                if cls.target_pause: 
                    slope = -slope
                v_mult = cls.volume_multiplier + slope
                if v_mult > 1: v_mult = 1
                elif v_mult <= 0: 
                    v_mult = 0
                    cls._setPaused(True)
            cls.set_volume_multiplier(v_mult)
            


        if cls.songQueue.current and not cls.paused:
            if cls.timer.timeElapsed() > cls.songQueue.current.length_seconds:
                logger.log("Update Method detected song end",cls.songQueue.current.name,'Time:',cls.timer.timeElapsed(),'/', cls.songQueue.current.length_seconds)
                cls.finishSong()
        

    @classmethod
    def playNext(cls):
        assert cls.songQueue.current is not None
        if not _internal_music_load(MUSIC_PATH+cls.songQueue.current._fileName):
            cls.timer.pause()
            cls.timer.reset()
            cls.songLoaded = False
            cls.songQueue.current = None
        else:
            cls.timer.reset()
            cls.songLoaded = True
            cls.unpause()
            logger.log(f'Playing {cls.songQueue.current}')
            pygame.mixer_music.play() 

    @classmethod
    def backButton(cls):
        if cls.songQueue.current is None: return
        if cls.timer.timeElapsed() < 3:
            cls.songQueue.goBackOneSong()
            if not _internal_music_load(MUSIC_PATH+cls.songQueue.current._fileName):
                cls.songLoaded = False
                cls.timer.pause()
                cls.timer.reset()
            else:
                logger.log(f'Playing {cls.songQueue.current}')
                pygame.mixer_music.play()
        else:
            cls.setPosition(0)

    @classmethod
    def finishSong(cls):
        if cls.songQueue.current:
            prevSong = cls.songQueue.current
            nextSong = cls.songQueue.nextSong()
            if nextSong is None:
                cls.playAbsolute(prevSong._fileName)
                cls.pause()  
            else:
                cls.playNext()

    @classmethod
    def clearCurrentSong(cls):
        cls.pause()
        cls.songQueue.current = None
        pygame.mixer_music.unload()
        cls.timer.reset()
        cls.timer.stop()

        
keybinds = Keybinds('./config/keybinds.config')
keybinds.setDefaultAction('Pause',(const.K_SPACE,0))
keybinds.setDefaultAction('Home',(const.K_h,0))
keybinds.setDefaultAction('Settings',(const.K_s,0))
keybinds.setDefaultAction('Library',(const.K_m,0))
keybinds.setDefaultAction('Download',(const.K_d,0))
keybinds.setDefaultAction('Volume Up',(const.K_UP,0))
keybinds.setDefaultAction('Volume Down',(const.K_DOWN,0))
keybinds.setDefaultAction('Skip Back',(const.K_LEFT,0))
keybinds.setDefaultAction('Skip Forward',(const.K_RIGHT,0))
keybinds.setDefaultAction('Start Search',(const.K_SLASH,0))
keybinds.setDefaultAction('Undo',(const.K_z,const.KMOD_CTRL))
keybinds.setDefaultAction('Miniplayer',(const.K_p,0))