import stat
import _thread
from . import metadata
import subprocess as sp
from .gui import Input
from .Utils import Async
from .Utils.YoutubeParsers.utils import parseDuration
from .UIFramework import * #type: ignore
from .explorer import FileExplorer
from .Utils.Path import Path
from .AppFramework import MUSIC_PATH

BATCH_SIZE = max((os.cpu_count() or 1)//2,1)

def _importSongThread(queue:list[tuple[str,str,'ImportingSong']],count:ObjectValue[int]):
    while True:
        add_song = False
        try:
            src,dst,song = queue.pop()
        except IndexError:
            break
        if 'libvorbis' in song.meta.get('encoder','').lower():
            command = [
                'ffmpeg','-hide_banner','-i',src,
                '-map_metadata','0','-map_metadata','0:s:0', #map all metadata
                '-map','0:a', #select audio
                '-c','copy', #copy. do not transcode
                '-n', #exit immediately if would overwrite a file
                dst
            ]
        else:
            command = [
                'ffmpeg','-hide_banner','-i',src,
                '-map_metadata','0','-map_metadata','0:s:0',
                '-map','0:a',
                '-q','9', #highest quality 
                '-n', 
                dst
            ]
        completed_process = sp.run(command,stdout=sp.DEVNULL,stderr=sp.DEVNULL,creationflags=sp.CREATE_NO_WINDOW)
        if completed_process.returncode != 0:
            count.set(count.get()+1)    
        else:
            add_song = True
        if add_song:
            s = Song()
            s.name = song.name
            s.size_bytes = os.stat(dst).st_size
            s.rating = song.rating
            s.length_seconds = song.length_seconds
            s.bit_rate_kbps = song.bit_rate_kbps
            s.file_extension = song.file_extension
            s.release_date = song.release_date
            s.artists = song.artists.copy()
            s.album = song.album
            s.language = song.language
            s.genre = song.genre
            s.track_number = song.track_number
            s.explicit = song.explicit
            s._fileName = os.path.basename(dst)
            database.addSong(s)
            database.saveAllSongs()
    del queue,count
    try:
        del song,src,dst #type: ignore
    except: 
        pass

def path_is_audio(path:str):
    '''Not an exhaustive result, TODO: Find a better way'''
    return  path.endswith('.ogg') or \
            path.endswith('.mp3') or \
            path.endswith('.flac') or \
            path.endswith('.aac') or \
            path.endswith('.m4a') or \
            path.endswith('.aiff') or \
            path.endswith('.alac')

def getAudioMetaFromFileAsync(path:str):
    if ':' in path:
        path = path.split(':',1)[-1]
    command = ['ffmpeg', '-hide_banner', '-i', f'{path}']
    
    process = sp.Popen(command,stdout=sp.DEVNULL,stderr=sp.PIPE)
    p_out = b''
    while process.poll() is None:
        yield
        if stderr:=process.stderr:
            p_out += stderr.read()
    out:dict[str,bytes] = {}
    key = None
    lines = p_out.split(b'\n')
    if  b'misdetection' in lines[1] or \
        b'misdetection' in lines[0] or \
        b'Invalid' in lines[1] or \
        b'Error' in lines[1]: return None
    got_header = False
    getting_metadata = False
    metadata_tab_spaces = -1
    try:
        for line in lines:
            if line.lstrip().startswith(b'Stream #'):
                pass
            elif not got_header and line.lstrip().startswith(b'Duration: '):
                duration,start,bitrate = line.strip().split(b', ',2)
                _,duration = duration.split(b': ',1)
                _,bitrate = bitrate.split(b': ',1)
                out['_duration'] = str(parseDuration(duration)).encode()    
                out['_bitrate'] = bitrate
                got_header = True
            elif line.strip().startswith(b'Metadata:'):
                if getting_metadata:
                    break
                metadata_tab_spaces = 0
                while line[metadata_tab_spaces] == b' '[0]:
                    metadata_tab_spaces += 1
                getting_metadata = True
            elif line.startswith(b' '*metadata_tab_spaces) and getting_metadata:
                line = line[metadata_tab_spaces:]
                new_key,value = line.split(b': ',1)
                new_key = new_key.strip().decode().lower()
                if new_key:
                    key = new_key
                    out[key] = b''
                if not isinstance(key,str): 
                    continue
                out[key] += value.replace(b'\r',b'\n')
        if not got_header:
            raise RuntimeError("FFmpeg unexpected output! [FF_AUDIO_INFO_HEADER_EXPECTED]")
        o:dict[str,str] = {}
        for key,value in out.items():
            try:
                o[key] = value.strip().decode()
            except UnicodeDecodeError:
                o[key] = value.strip().decode('latin-1')
        return o
    except ValueError:
        return None

def removeExtension(filename:str):
    if '.' in filename:
        return filename.rsplit('.',1)[0]
    else:
        return filename


class ImportingSong(Song):
    path:Path
    meta:dict
    __slots__ = 'path','meta'


class ImporterMenu(Layer):
    def __init__(self, size: tuple[int, int]):
        super().__init__(size)
        self.path = ObjectValue(os.path.abspath(os.path.expanduser('~')))
        self.path_text = AddText(
            Button((0,0),(20,20),ColorScheme(80,80,80),None,lambda:toNone((nl:=base_layer.addLayer()).space.addObject(  
                    Resizer(FileExplorer(nl,self.path.get(),self.path),'15%','20%','85%','80%')
                ))
            ),
            self.path.get(),text_color,getFont(FONT_NAME.ARIAL,16),0,alignment_x=0
        ).setClip(True)
        color_layout = ColorLayout(text_color,grey_color,colorUtils.darken(*primary_color,50))
        self.playlist = ObjectValue('')
        self.playlist_ui = InputBoxOneLine((0,0),(1,1),color_layout,self.playlist.set,getFont(FONT_NAME.OPEN_SANS,17)).setPlaceholder('[None]')
        self.path.obj_change_event.register(self.path_text.setText)
        
        self.space.addObjects(
            Aligner(
                Text((0,10),'Import Menu',text_color,title_font),
                0.5,0
            ),
            Resizer(
                g:=Grid(Rect(0,0,100,100),(2,1),(['100','100%-100-`*2'],'30-`'),('2','2'),[
                    [
                        BoxText((0,0),(1,1),'Path:',text_color,subtitle_font,1),
                        self.path_text
                    ],
                    [
                        BoxText((0,0),(1,1),'Playlist:',text_color,subtitle_font,1),
                        self.playlist_ui
                    ],
                ]),
                '10%','50','90%','~+100'
            ),
            WithRespectTo(
                AddText(
                    Button((0,0),(70,30),dark_primary_cs,None,
                           lambda : toNone(
                               (nl:=base_layer.addLayer()).space.addObject(
                                   Resizer(
                                        ImporterLoading(
                                            nl,(300,300),self.path.get(),self.path.get() if os.path.isdir(self.path.get()) else os.path.dirname(self.path.get()),self.playlist.get()
                                        ),
                                    '20%','20%','80%','80%'
                                    )
                                )
                           )
                    ),
                    'Import',text_color,font_default
                ),
                g,0.5,1,0.5,1
            )
        )

class SongUI(SongBox):
    def __init__(self,pos:tuple[int,int],size:tuple[int,int],color_scheme:ColorScheme,song:Song) -> None:
        super().__init__(pos,size,color_scheme,song)
        self.pad_left = 5
        self.pad_right = 5

    def update(self, input: Input): pass #Do Nothing
      
    def draw(self,surf:Surface):
        r = self.rect
        cs = self.color_scheme
        color = [cs.getInactive,cs.getIdle,cs.getActive][max(self.mouse_hover,self.selected*2)]() #TODO find out if its worth it to cache the results instead of calling them everytime
        draw.rect(surf,color,r)
        surf.blit(self.song_name_surf,(r.left+self.pad_left,r.centery-self.song_name_surf.get_height()+1))
        surf.blit(self.artists_name_surf,(r.left+self.pad_left,r.centery-1))
        if self.state == 1 or self.state == 2 or self.selected:
            surf.blit(self.more_options_surf,(r.right-self.more_options_width,r.centery-self.more_options_surf.get_height()//2-6))
        if self.album_name_surf:
            surf.blit(self.album_name_surf,(r.centerx,r.centery-self.album_name_surf.get_height()//2))

class ImporterLoading(Layer):
    def __init__(self,layer:Layer, size: tuple[int, int],path:str,directory:str,playlist:str,include_subdirs:bool = True):
        super().__init__(size)
        self.layer = layer
        self.playlist = playlist
        self.songs:list[ImportingSong] = []
        self.space.addObject(BackgroundColor(colorUtils.darken(*bg_color,5)))
        Async.addCoroutine(self.initAsync(path,directory,include_subdirs))
    
    def initAsync(self,path,dir,include_subdirs):
        yield from self.findSongsAsync(path,include_subdirs)
        yield from self.loadSongsAsync(self.paths,dir)
        self.showSongs()

    def findSongsAsync(self,path:str,include_subdirs:bool):
        slider = AutoSlider((0,0),(20,5),primary_layout)
        with self.withTemp(
            Resizer.fill(Region(Rect(1,1,1,1)).addObjects(
                Resizer(slider,'0+20','70%','100%-20','~+5'),
                Aligner(LoadingIndicator((0,0),50,text_color),0.5,0.5),
                Resizer.fill(
                    BoxText((0,0),(10,10),'Collecting Songs',text_color,title_font,alignment_y=0,offset=(0,10))

                )
            ))):
            if os.path.isfile(path):
                self.paths:list[Path] = [Path.fromFile(path)]
            elif os.path.isdir(path):
                dir = path
                if not include_subdirs:
                    try:
                        self.paths = [Path(dir,path) for path in os.listdir(path) if os.path.isfile(fp:=os.path.join(dir,path))]
                    except PermissionError:
                        self.paths:list[Path] = []
                else:
                    #Two Stages
                    # 1st Find all directories, count all non_directories
                    dirs_found:set[str] = set()
                    dirs_looked = 0
                    new_dirs:deque[str] = deque([path])
                    self.paths:list[Path] = []
                    time_alloc = 0.5/settings.fps
                    t_start = time.perf_counter()
                    while new_dirs:
                        dir = new_dirs.popleft()
                        dirs_looked += 1
                        try:
                            ls = os.listdir(dir)
                        except PermissionError:
                            continue
                        for end in ls:
                            fullpath = os.path.join(dir,end)
                            try:
                                st = os.stat(fullpath)
                            except (OSError, ValueError): continue
                            if stat.S_ISDIR(st.st_mode):
                                if fullpath not in dirs_found:
                                    dirs_found.add(fullpath)
                                    new_dirs.append(fullpath)
                            elif stat.S_ISREG(st.st_mode) and path_is_audio(end):
                                self.paths.append(Path(dir,end))
                        t_cur = time.perf_counter()
                        if t_cur >= time_alloc + t_start:
                            slider.setValue(len(new_dirs)/(len(new_dirs)+dirs_looked))
                            yield 
                            t_start = time.perf_counter()
        
    def loadSongsAsync(self,song_paths:list[Path],g_meta_directory:str):
        loading_indicator = Aligner(LoadingIndicator((0,0),50,text_color),0.5,0.5)
        info = BoxText((0,47),(200,20),'',text_color,getFont(FONT_NAME.ARIAL,16))
        slider = AutoSlider((0,0),(20,5),primary_layout)

        self.space.addObject(loading_indicator)
        self.space.addObject(a:=Aligner(info,0.5,0.5))
        self.space.addObject(b:=Resizer(slider,'0+20','70%','100%-20','~+5'))
        self.space.addObject(c:=Resizer.fill(BoxText((0,0),(1,1),'Extracting Metadata',text_color,title_font,alignment_y=0,offset=(0,10))))
        ctx = Async.TimingContext(0.4 / settings.fps)
        false_positives = 0
        for i,song_path in enumerate(song_paths):
            file_metadata = yield from ctx.updateCoro(getAudioMetaFromFileAsync(song_path.fullpath))
            if file_metadata is None:
                false_positives += 1
                continue
            
            if '.' in song_path.filename:
                file_name_no_ext = song_path.filename.rsplit('.',1)[0]
            else:
                file_name_no_ext = song_path.filename
            if 'title' in file_metadata and 'artist' in file_metadata and file_metadata['artist'].lower() in file_metadata['title'].lower(): #assume from youtube
                yt = metadata.yttypes.YTVideo.unknown()
                yt.channel.is_verified_artist = False
                yt.channel.name = file_metadata['artist']
                yt.title = file_metadata['title']
                meta = metadata._shallowExtractDataFromYTVideo(yt)
            else:
                meta = metadata.DownloadingSong.unknown()
            s = ImportingSong()
            s.path = song_path
            s.meta = file_metadata
            s.name = meta.title or file_metadata.get('name') or file_name_no_ext
            s.size_bytes = 0
            s.rating = file_metadata.get('rating') or "Unrated"
            s.length_seconds = int(file_metadata['_duration'])
            s.bit_rate_kbps = int(file_metadata['_bitrate'].split(' ')[0])
            s.file_extension = '.ogg'
            s.release_date = file_metadata.get('date','Unknown')
            s.artists = meta.artists or [file_metadata.get('artist') or 'Unknown']
            s.album = file_metadata.get('album') or ''
            s.language = file_metadata.get('language')  or 'eng'
            s.genre = file_metadata.get('genre')  or 'eng'
            s.track_number = -1
            s.explicit = 'explicit' in file_metadata
            s._fileName = ''
            info.setText(f'{s.name}: {s.artists}')
            slider.setValue(i/(len(song_paths)))
            self.songs.append(s)
        self.space.removeObject(loading_indicator)
        self.space.removeObject(a)
        self.space.removeObject(b)
        self.space.removeObject(c)

    def showSongs(self):
        '''Called from self.loadSongsAsync after songs have been loaded'''
        if len(self.songs) == 1:
            txt = 'Loading 1 Song'
        else:
            txt = f'Loading {len(self.songs)} Songs'
        cs_green = ColorScheme(100,200,100)
        title = Resizer(BoxText((0,0),(1,1),txt,text_color,title_font),'0','0','100%','50')
        self.space.addObject(title)
        self.space.addObjects(
            Resizer(
                Selection((0,0),(100,50),100,selection_cs,lambda : self.songs,SongUI),
                '10%','60','90%','100%-50'
            ),
            Resizer(
                Grid((0,0,1,1),(2,1),('~-`','~-`'),('2','10'),
                    [[
                        AddText(
                            Button((0,-10),(80,30),cs_green,self.importAllSongs),
                            'Download',text_color,settings_button_font
                        ),
                        AddText(
                            Button((0,-10),(80,30),exit_button_cs,lambda : base_layer.removeLayer(self.layer)),
                            'Cancel',text_color,settings_button_font
                        ),
                    ]]
                ),
                '50%-100','100%-50','50%+100','100%'
            )
        )
        
    def update(self, input: Input):
        super().update(input)
        input.clearALL()

    def importAllSongs(self):
        self.resetEverything()
        self.space.addObject(BackgroundColor(colorUtils.darken(*bg_color,5)))
        taken = set(os.listdir(MUSIC_PATH))

        queue:list[tuple[str,str,ImportingSong]] = []
        errors = ObjectValue(0)
        i = 0
        for song in self.songs:
            new_name = removeExtension(song.path.filename)
            new_name = findName(new_name,'ogg',taken)
            assert '/' not in new_name and '\\' not in new_name
            taken.add(new_name)
            queue.append((song.path.fullpath,os.path.join(MUSIC_PATH,new_name),song))
            i += 1
        
        if __debug__:
            print('Importing',len(self.songs),'songs')
            print('First 10 in Queue:',queue[:10])
        Async.addCoroutine(self.manageImportingAsync(queue,len(queue),errors))
        for i in range(min(BATCH_SIZE,len(queue))):
            _thread.start_new_thread(_importSongThread,(queue,errors))

    def manageImportingAsync(self,queue:list[tuple[str,str,ImportingSong]],start_len:int,errors:ObjectValue[int]):
        last_len = start_len
        time_ = 2
        with self.withTemp(
            Resizer.fill(
                Region(Rect(1,1,1,1)).addObjects(
                    Resizer.fill(
                        BoxText((0,0),(1,1),'Importing',text_color,title_font,0.5,0,(0,10))
                    ),
                    Aligner(
                        LoadingIndicator((0,0),50,text_color),
                        0.5,0.5
                    ),
                    Resizer(
                        slider:=AutoSlider((0,0),(10,5),primary_layout),
                        '5','50%','100%-5','~+5'
                    )
                )
            )
        ):
            while (l:=len(queue)):
                if last_len != l:
                    slider.setValue(1-l/start_len)
                yield
            slider.setValue(1)
            yield
            while time_ > 0:
                time_ -= 1/settings.fps
                yield
        base_layer.removeLayer(self.layer)

def findName(base:str,ext:str,taken:set[str]):
    if base+'.'+ext not in taken:
        return base+'.'+ext
    i = 1
    while True:
        new = f'{base} ({i}).{ext}'
        if new not in taken:
            return new
        i+=1