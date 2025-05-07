try:from . import db_utils
except: import db_utils
from . import events
from collections import defaultdict
from typing import Any,Optional,Sequence
import os

os.makedirs('./Database/__Music',exist_ok=True) #ensure that Database and __Music exist
if not os.path.exists('./Database/key.json'):
    with open('./Database/key.json','w+') as file: file.write('[]')
if not os.path.exists('./Database/playlists.json'):
    with open('./Database/playlists.json','w+') as file: file.write('[]')


class Song:
    name:str
    size_bytes:int 
    rating:str
    length_seconds: int
    bit_rate_kbps: int
    file_extension:str
    release_date:str
    artists:list[str]
    album:str
    language: str
    genre:str
    track_number:int
    explicit:bool
    _fileName:str

    __slots__ = 'name','size_bytes','rating','length_seconds','bit_rate_kbps','file_extension','artists','album','language','_fileName','genre','track_number','explicit','release_date'
    def __repr__(self):
        return f'Song[{self.name}: ' + ' | '.join(self.artists) + ']'
    
    def __eq__(self,other:"Song"):
        return self._fileName == other._fileName
    
    def __setattr__(self, name: str, value: Any) -> None: #makes set values immutable
        if hasattr(self,name): raise SyntaxError("Cannot override a set value of a song")
        super().__setattr__(name,value)
    
    def __hash__(self):
        return self._fileName.__hash__()
    
    @property
    @db_utils.cache
    @classmethod
    def null(cls): #TODO class properties deprecated, make this a method
        s = Song()
        s.name = 'No Song'
        s.album = ''
        s.artists = ['None']
        s.bit_rate_kbps = -1
        s.size_bytes = -1
        s.length_seconds = 1
        s.language = 'N/A'
        s.file_extension = 'N/A'
        s.rating = 'N/A'
        s.genre = 'Unknown'
        s.track_number = -1
        s._fileName = 'None'
        return s

class Playlist:
    name:str
    description:str
    songs:list[Song]

class Album:
    name:str
    album_artist:str
    song_fileNames:list[str]

class SongSearch:
    def __init__(self):
        self.__names:defaultdict[str,set[Song]] = defaultdict(set)
        self.__misc:defaultdict[str,set[Song]] = defaultdict(set)
        self.__vowels:defaultdict[str,set[Song]] = defaultdict(set)
        self.__consonants:defaultdict[str,set[Song]] = defaultdict(set)
        self.__artists:defaultdict[str,set[Song]] = defaultdict(set)
        self.__albums:defaultdict[str,set[Song]] = defaultdict(set)
        self.__name_score = 100
        self.__artist_score = 5
        self.__album_score = 5
        self.__word_score = 6
        self.__vowel_score = 3
        self.__consonant_score = 2
        self.__letter_score = 0
        
    def addSong(self,song:Song):
        n = db_utils.sanitizeName(song.name)
        v = db_utils.onlyVowels(n)
        c = db_utils.onlyConsonants(n)
        
        self.__names[n].add(song)
        if v:
            self.__vowels[v].add(song)
        if c:
            self.__consonants[c].add(song)
        for artist in song.artists:
            a = db_utils.sanitizeName(artist)
            a1 = db_utils.onlyVowels(a)
            a2 = db_utils.onlyConsonants(a)
            for w in a.split():
                self.__artists[w].add(song)
            self.__artists[a1].add(song)
            self.__artists[a2].add(song)
        if song.album:
            a_n = db_utils.sanitizeName(song.album)
            for a_n in a_n.split():
                a_v = db_utils.onlyVowels(a_n)
                a_c = db_utils.onlyConsonants(a_n)

                self.__albums[a_n].add(song)
                self.__albums[a_v].add(song)
                self.__albums[a_c].add(song)
        for c in ''.join(n.split()):
            self.__misc[c].add(song)
        if n:
            for word in n.split():
                self.__misc[word].add(song)
    
    def removeSong(self,song:Song):
        n = db_utils.sanitizeName(song.name)
        v = db_utils.onlyVowels(n)
        c = db_utils.onlyConsonants(n)
        
        self.__names[n].discard(song)
        if v:
            self.__vowels[v].discard(song)
        if c:
            self.__consonants[c].discard(song)
        for artist in song.artists:
            a = db_utils.sanitizeName(artist)
            a1 = db_utils.onlyVowels(a)
            a2 = db_utils.onlyConsonants(a)
            for w in a.split():
                self.__artists[w].discard(song)
            self.__artists[a1].discard(song)
            self.__artists[a2].discard(song)
        if song.album:
            a_n = db_utils.sanitizeName(song.album)
            for a_n in a_n.split():
                a_v = db_utils.onlyVowels(a_n)
                a_c = db_utils.onlyConsonants(a_n)

                self.__albums[a_n].discard(song)
                self.__albums[a_v].discard(song)
                self.__albums[a_c].discard(song)
        for c in ''.join(n.split()):
            self.__misc[c].discard(song)
        if n:
            for word in n.split():
                self.__misc[word].discard(song)

    def rawSearch(self,query:str):
        query = db_utils.sanitizeName(query)
        words = query.split()

        results:defaultdict[Song,int] = defaultdict(int)
        for r in self.__names[query]:
            results[r] += self.__name_score
        for word in words:
            self.searchWord(word,results)

        return {k:results[k] for k in results if results[k]}
    
    def searchWord(self,query:str,results:Optional[defaultdict[Song,int]] = None):
        if results is None:
            results = defaultdict(int)

        v = db_utils.onlyVowels(query)
        c = db_utils.onlyConsonants(query)  
        for r in self.__misc[query]:
            results[r] += self.__word_score
        for r in self.__artists[query]:
            results[r] += self.__artist_score    
        for r in self.__vowels[v]:
            results[r] += self.__vowel_score
        for r in self.__consonants[c]:
            results[r] += self.__consonant_score
        for r in self.__albums[query]:
            results[r] += self.__album_score
        for char in query:
            for r in self.__misc[char]:
                results[r] += self.__letter_score
        return results
        
    def search(self,query:str) -> list[Song]:
        results = self.rawSearch(query)
        return sorted(results.keys(),key=lambda x: results[x],reverse=True)

class Database:
    songs:list[Song]
    songsByFileName:dict[str,Song]  
    albums:list[Album]
    playlists:list[Playlist]
    searchDB:SongSearch

    def __init__(self) -> None:
        self.playlists = []
        self.songs = []
        self.songsByFileName = {}
        self.albums = []
        self.searchDB = SongSearch()
        self.songs_changed_event:events.Event[[]] = events.Event()
        self.song_removed_event:events.Event[[Song]] = events.Event()
        self.playlists_changed_event:events.Event[[]] = events.Event()


    def addSong(self,song:Song):
        '''Triggers a song_change event'''
        if song._fileName in self.songsByFileName: raise ValueError("This song is already in the database")
        self._addSongNoEventFire(song)
        self.songs_changed_event.fire()

    def addSongs(self,songs:Sequence[Song]):
        for song in songs:
            if song._fileName in self.songsByFileName: raise ValueError(f"Song: {song} is already in the database")
            self._addSongNoEventFire(song)

    def replaceSong(self,old:Song,new:Song):
        changed = False
        for p in self.playlists:
            for i in range(len(p.songs)):
                if p.songs[i] is old:
                    p.songs[i] = new
                    changed = True
        if changed:
            self.playlists_changed_event.fire()

        self.songs[self.songs.index(old)]=new
        self.songsByFileName[old._fileName] = new
        self.searchDB.removeSong(old)
        self.searchDB.addSong(new)
        self.saveAllSongs()
        self.songs_changed_event.fire()
            
    def _addSongNoEventFire(self,song:Song):
        self.songsByFileName[song._fileName] = song
        self.songs.append(song)
        self.searchDB.addSong(song)

    def loadFromFiles(self): 
        '''Triggers a song_change event'''
        for songData in db_utils.getAllSongs():
            s = Song()
            s.album = songData['Album Name']    
            s.artists = songData['Artists']
            s.bit_rate_kbps = songData['Bit rate']
            s.file_extension = songData['File extension']
            s.language = songData['Language']
            s.length_seconds = songData['Length']
            s.name = songData['Name']
            s.rating = songData['Rating']
            s.size_bytes = songData['Size']
            s.release_date = songData.get('Release Date','Unknown')
            s.genre = songData.get('Genre','')
            s.track_number = int(songData.get('Track Number',0))
            s.explicit = bool(songData.get('Explicit',False))
            s._fileName = songData['File Name']
            self._addSongNoEventFire(s)
        self.songs_changed_event.fire()
        
    def loadPlaylists(self):
        for songData in db_utils.getAllPlaylists():
            p = Playlist()
            p.name = songData['Name']
            p.description = songData['Description']
            p.songs = [self.songsByFileName[fileName] for fileName in songData['Song File Names'] if fileName in self.songsByFileName]
            self.playlists.append(p)
        self.playlists_changed_event.fire()

    def makePlaylist(self,name:str,description:str):
        p = Playlist()
        p.name = name
        p.description = description
        p.songs = []
        self.playlists.append(p)
        self.playlists_changed_event.fire()
        self.savePlaylists()
        return p
    
    def removePlaylist(self,p:Playlist):
        try:
            self.playlists.remove(p)
        except ValueError:
            return False
        self.playlists_changed_event.fire()
        self.savePlaylists()
        return True

    def savePlaylists(self):
        playlists = []
        for p in self.playlists:
            songData = {}
            songData['Name'] = p.name
            songData['Description'] = p.description
            songData['Song File Names'] = [s._fileName for s in p.songs]
            playlists.append(songData)
        db_utils.saveAllPlaylists(playlists)

    def saveAllSongs(self):
        songDatas = []
        for s in self.songs:
            songData = {}
            songData['Album Name'] = s.album
            songData['Artists'] = s.artists
            songData['Bit rate'] = s.bit_rate_kbps
            songData['File extension'] = s.file_extension
            songData['Language'] = s.language
            songData['Length'] = s.length_seconds
            songData['Name'] = s.name
            songData['Rating'] = s.rating
            songData['Size'] = s.size_bytes
            songData['File Name'] = s._fileName
            songData['Release Date'] = s.release_date
            songData['Genre'] = s.genre
            songData['Track Number'] = s.track_number
            songData['Explicit'] = s.explicit
            songDatas.append(songData)
        db_utils.saveAllSongs(songDatas)
   
    def getAllSongNames(self): 
        for song in self.songs:
            yield song.name

    def search(self,query:str) -> list[Song]: 
        return self.searchDB.search(query)

    def removeSong(self,song:Song):
        '''Triggers a song_change event.
        Conditionaly triggers a playlist_change event'''
        self.songs.remove(song)

        del self.songsByFileName[song._fileName]
        self.searchDB.removeSong(song)
        db_utils.deleteSongAudio(song._fileName)
        self.saveAllSongs()
        self.songs_changed_event.fire()
        self.song_removed_event.fire(song)

        for playlist in self.playlists:
            if song in playlist.songs:
                self.stripSongFromPlaylist(playlist,song)
        self.savePlaylists()
        

    def stripSongFromPlaylist(self,playlist:Playlist,song:Song):
        '''
        Removes ALL instances of <song> from <playlist>.

        Triggers a playlist_change event'''
        assert song in playlist.songs, 'Song must be present in playlist'
        for i in range(len(playlist.songs)-1,-1,-1):
            if playlist.songs[i] is song:
                playlist.songs.pop(i)
        self.playlists_changed_event.fire()

    def removeIndexSongFromPlaylist(self,playlist:Playlist,index:int):
        '''
        Returns the song removed.
        
        Triggers a playlist_change event 
        '''
        assert 0 <= index < len(playlist.songs), 'index out of bounds'
        s = playlist.songs.pop(index)
        self.savePlaylists()

        self.playlists_changed_event.fire()
        return s
    def addSongToPlaylist(self,playlist:Playlist,song:Song):
        playlist.songs.append(song)
        self.savePlaylists()
        self.playlists_changed_event.fire()

    def addPlaylistToPlaylist(self,source:Playlist,destination:Playlist,addDuplicates:bool):
        if addDuplicates:
            destination.songs.extend(source.songs)
        else:
            song_set = set(destination.songs)
            for song in source.songs:
                if song not in song_set:
                    song_set.add(song) #this line has the effect of only adding one of the song of the source to the destination, if this proves unacceptable, removeing this will make sure that duplicate songs from <source> will all be copied over, but duplicated originating from <destination> will not.
                    destination.songs.append(song)

        self.savePlaylists()
        self.playlists_changed_event.fire()
