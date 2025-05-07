import time
import json
import typing
import threading
from .Utils import Async
from .Utils import logger
from .Utils import NetLight
from .Utils.debug import profileFunc,profile,profileGen
from .Utils.YoutubeParsers import types as yttypes
from .Utils.SearchYT import VideoInfo,VideoInfo2,PlaylistInfo,VideoSearch
from .Utils.SearchItunes import ITunesSearch,ItunesResult
from difflib import SequenceMatcher
from .Settings import settings
from .utils2 import  cleanYTTitle,getFeats,getRelevantFilters,formatTitle,tillNextDoubleQuote,removeRedundancies
from .utils2 import formatDict,parseBytes2,cacheNoRememberFalses,separateArtists,removeBrackets

guess_song_meta = True
guess_song_meta_cutoff = 0.5 #if we do want to guess the song, what should be the cutoff?

prefetched_urls:dict[str,NetLight.Response] = {}
fetching:dict[str,threading.Thread] = {}
def prefetch_url(url:str):
    prefetched_urls[url] = NetLight.fetch(url) #requests.get(url,stream=True)

def prefetch_url_async(url:str) -> None:
    if url in fetching: return
    def _inner(url:str):
        prefetch_url(url)
        if url in fetching:
            del fetching[url] 
        #previosly there was a branch so if the url was not in <fetching> then it would delete the fetch afterwords. i dont know why it was there
        #it was there because when the cache is cleared each thread will realize this and subsequently delete what it would have cached. 
        # this is removed because it does not affect the performance ( there is always < 30 caches), and for code simplicity
    t = threading.Thread(target = _inner,args = [url])
    fetching[url]=t
    t.start()

def prefetchIfNeededAsync(url:str):
    if  url not in prefetched_urls:
        prefetch_url_async(url)

def get_url(url:str):
    '''Blocking function which will return a requests.Response of the url'''
    if url not in prefetched_urls:
        if url in fetching:
            start_time = time.perf_counter()
            logger.log('get_url called. However the url already being fetched. Starting Wait:')
            while url not in prefetched_urls:
                time.sleep(0.01)
            end_time = time.perf_counter()
            logger.log('Time Spent in Wait:',end_time - start_time,'seconds')
        else:
            prefetch_url(url)
    return prefetched_urls[url]

def clear_prefetch():
    prefetched_urls.clear()
    fetching.clear()

class DownloadingSong:
    title:str
    album:str|None = None
    artists:list[str]|None = None
    release_date:str|None = None
    explicit:bool|None = None
    genre:str|None = None
    track_number:int|None = None
    url:str
    length_seconds:int
    album_artwork:str|None=None

    @classmethod
    def unknown(cls):
        v = cls()
        v.title = ''
        return v
    def __repr__(self):
        return "MetaData: "+formatDict(self.__dict__)
        return f'title: {self.title } album: {self.album}, artists: {self.artists} release_date: {self.release_date} explicit: {self.explicit} genre: {self.genre} track_number: {self.track_number}'

def getMetaDataForYTBatchAsync(yts:list[yttypes.YTVideo],cb:typing.Callable[[DownloadingSong],typing.Any]):
    MAX_BATCH_SIZE = 2
    # batch_size = min(MAX_BATCH_SIZE,len(yts))
    async_manager = Async.AsyncContext()
    free_searchers = [VideoSearch() for _ in range(MAX_BATCH_SIZE)]
    bound_searchers:dict[Async.Coroutine,VideoSearch] = {}

    yts = yts[::-1]#we are gonna pop off the top
    while yts or async_manager.getNumCoros():
        if free_searchers and yts:
            ytvid = yts.pop()
            searcher = free_searchers.pop()
            coro = getYTVideoMetadata(ytvid)
            bound_searchers[coro] = searcher
            async_manager.addCoroutine(coro)
        if (done:=async_manager.update()) is not None:
            coro,metadata_song = done
            free_searchers.append(bound_searchers[coro])
            #On Metadata Finish
            cb(metadata_song)
        yield 


@profileGen
def getYTVideoMetadata(yt:yttypes.YTVideo,ytGetter:VideoInfo2|None=None,itunesGetter:ITunesSearch|None=None)-> typing.Generator[None,None,DownloadingSong]:
    ytGetter = ytGetter or VideoInfo2()
    itunesGetter = itunesGetter or ITunesSearch()
    out = DownloadingSong()
    out.length_seconds = yt.duration
    out.url = yt.url
    out.album_artwork = yt.thumbnails[-1].url if yt.thumbnails else None
    if not settings.tryFindSong:
        out.title = yt.title
        out.artists = [yt.channel.name]
        out.album = ''
        out.track_number = -1
        return out
    if yt.channel.is_verified_artist:
        title = removeBrackets(yt.title)
        artist = yt.channel.name.removesuffix('VEVO').rstrip(' ')
        artists = [artist]
        if ' - ' in title:
            before,after = title.split(' - ',1)
            if artist in before:
                title = after
            elif artist in after:
                title = before
            else:
                title = after
            #get feats
            feats = getFeats(title)
            artists.extend(feats)

        out.artists = artists
        out.title = title
    else:
        title = yt.title
        if ' - ' in title: #all titles with this string are likely songs
            before,after = title.split(' - ',1)
            title = after
            artists = [before]
            #get feats
            feats = getFeats(title)
            artists.extend(feats)
        else:
            artists = []
        out.artists = artists
        out.title = title

    try:
        youtube = yield from getYTSong(yt,ytGetter)
    except Exception:
        logger.log('getYTSong raised exception in metadata.py')
        raise 
    # itg = getItunesSong(out.title,itunesGetter,10)
    # youtube,*_= mainloop(ytg)
    # assert (isinstance(youtube,DownloadingSong) or youtube is None) #and isinstance(itunes,list)
    # print(youtube)
    # print(itunes)
    if youtube:
        if youtube.album:
            out.album = youtube.album
        if youtube.album_artwork:
            out.album_artwork = youtube.album_artwork
        if youtube.title:
            out.title = youtube.title
        if youtube.artists:
            out.artists = youtube.artists
    out.length_seconds # to
    out.album
    return out


    vid_title = yt.title
    if vid_title.find('"',None,-1) != -1:
        name = tillNextDoubleQuote(vid_title[vid_title.index('"')+1:])
        artists = cleanYTTitle(vid_title.replace(f'"{name}"',''))
        if artists.count(', ') == 0:
            if artists.count(' ') > 6:
                artists = yt.channel.name
            else:
                artists = yt.channel.name + ', ' + artists
    else:
        name,artists,*_= vid_title.split(' - ',1)[::-1] + ['']
    out.title  = cleanYTTitle(name)
    out.artists = (artists.split(', ') if artists else []) + getFeats(name)
    out.album = ''

    # itunes_meta =gen.value
    # if itunes_meta:
    #     if confident or (guess_song_meta and itunes_meta['matchScore'] >= guess_song_meta_cutoff):
    #         if out.album: # if album is similar to title (which happens on yt) that means that its probably not correct and we should ask itunes to fill it in for us
    #             if out.album.lower() == out.title.lower() or SequenceMatcher(None,out.album,out.title).ratio() > 0.8:
    #                 out.album = None
    #         #only use itunes to fill in other metadata
    #         out.album = itunes_meta['collectionName']
    #         out.artists = itunes_meta['artistName']
    #         out.release_date = itunes_meta['releaseDate']
    #         out.explicit = itunes_meta['trackExplicitness'] != 'notExplicit'
    #         out.genre = itunes_meta['primaryGenreName']
    #         out.track_number = itunes_meta['trackNumber']
    # return out


def getYTPlaylistSongs(yt:yttypes.YTPlaylist,ytGetter:PlaylistInfo|None=None,itunesGetter:ITunesSearch|None=None)-> typing.Generator[None|yttypes.YTVideo,None,None]:
    '''Most Readable Function Right Here'''
    ytGetter = ytGetter or PlaylistInfo()
    yield from ytGetter.beginQueryAsync(yt.id)
    yield from (yield from ytGetter.getParsedAsync())
    while ytGetter.canContinue():
        yield from ytGetter.continueQueryAsync()
        yield from (yield from ytGetter.getParsedAsync())


def getInitialData(yt:yttypes.YTVideo,v:VideoInfo2) -> typing.Generator[None,None,bytes|None]:
    yield from v.beginQueryAsync(yt.id)
    response = yield from v.getResponseAsync()
    if response.status_code != 200:
        return None
    return response.body 

@cacheNoRememberFalses
def getYTSong(yt:yttypes.YTVideo,v:VideoInfo2) -> typing.Generator[None,None,DownloadingSong|None]:
    from .Utils.YoutubeParsers import utils
    out = DownloadingSong()
    initial_data_b = (yield from getInitialData(yt,v))
    if initial_data_b is None:
        return None
    try:
        b = initial_data_b
        c = b.find(b'"horizontalCardListRenderer"')
        if c == -1:
            return None
        c = utils.indexEnd(b,b'image"',c)
        c = utils.indexEnd(b,b'url":',c)
        album_cover,c = utils.readWholeQuote(b,c)
        c = utils.indexEnd(b,b'title":',c)
        title,c = utils.readWholeQuote(b,c)
        end = utils.indexEnd(b,b'overflowMenuOnTap":',c)
        artists_i = utils.findEnd(b,b'subtitle":',c,end)
        album_i = utils.findEnd(b,b'content":',c,end)
        if artists_i != -1:
            artists,_ = utils.readWholeQuote(b,artists_i)
            out.artists = artists.decode().split(', ')
        if album_i != -1:
            album,_ = utils.readWholeQuote(b,album_i)
            out.album = album.decode().replace('\\u0026','\u0026')
        out.title = title.decode()
        out.album_artwork = album_cover.decode()
    except Exception:
        import random
        filename = f'ytdump({random.randint(0,99999999)})'
        if logger.dump(filename,initial_data_b):
            logger.log(f'Unable to parse Youtube Initial Data, Dump can be found in {filename}')
        else:
            logger.log('Unable to parse Youtube Initial Data ')
        raise
    return out
    # initial_data_b = initial_data_b.split(b'"horizontalCardListRenderer"',1)
    # if len(initial_data_b) == 1:
    #     return None
    # initial_data_b = initial_data_b[1].split(b'"videoAttributeViewModel"',1)[1]
    # initial_data_b
    # initial_data_b = initial_data_b.split(b'"orientation"',1)[0]
    # out.album_artwork = initial_data_b.split(b'"url":"',1)[1].split(b'"')[0].decode()

    # out.title = tillNextDoubleQuote(initial_data_b.split(b'"title":"')[1].decode())
    # out.artists =  tillNextDoubleQuote(initial_data_b.split(b'"subtitle":"')[1].decode()).split(', ')
    # out.album =  tillNextDoubleQuote(initial_data_b.split(b'"content":"')[1].decode()).replace('\\u0026','\u0026')
    # return out

@profile
def searchItunesSongOfArtist(artist:str,song_name_to_match:str,itunesGetter:ITunesSearch):
    '''Returns: Name, Artist, Album,AlbumArtworkURL '''
    url = f'https://itunes.apple.com/search?term={artist}&entity=allArtist&limit=1&explicit=Yes'
    # logger.log('[Itunes] Searching For Artist:',artist)
    start = time.perf_counter()
    try:
        artist_id = NetLight.fetch(url).content.split(b'artistId":',1)[1].split(b',',1)[0].decode()
    except IndexError:
        return None
    except UnicodeDecodeError:
        artist_id = NetLight.fetch(url).content.split(b'artistId":',1)[1].split(b',',1)[0].decode('latin-1')
    finally:
        end = time.perf_counter()
        logger.log("Initial Artist Search Took:",end-start)
    url = f'https://itunes.apple.com/lookup?id={artist_id}&entity=song'
    r = NetLight.fetch(url)

    try:
        songs = json.loads(r.content)['results']
    except:
        return None
    sm = SequenceMatcher(None,'',song_name_to_match)
    # print(songs)
    for song in songs:
        if song['wrapperType'] != 'track': continue
        # print('Checking Song:', song['trackName'])
        song['artistName'] = separateArtists(song['artistName'])
        sm.set_seq1(song['trackName'])
        if sm.real_quick_ratio() >= .85 and \
        sm.quick_ratio() >= .85 and \
        (r:=sm.ratio()) >= .85:
            song['matchScore'] = r
            return song

@profileGen
def getItunesSong(title:str,itunesGetter:ITunesSearch,limit:int = 10) -> typing.Generator[None,None,list[ItunesResult]]:
    if settings.useItunes is False: return []
    # logger.log(f"Searching Itunes for Title:{title}, Artist:{main_artist}, Album:{album} Response Limit:{limit}")
    if limit > 200: limit = 200
    # print("FIX THE ITUNES THINGY THAT SEARCHING FOR WORD 'no' JUST BREAKS EVERYTHING AND RETURNS INVALID RESPONSE")
    start = time.perf_counter()
    # prev = itunesGetter.setSearchBy('songTerm')
    itunesGetter.sendQuery(title,20)
    if False:
        yield
        results = itunesGetter.getParsed()
    else:
        results = yield from itunesGetter.getParsedAsync()
    # itunesGetter.setSearchBy(prev)
    end = time.perf_counter()
    # print('Inner Itunes Fetch:',end-start)
    # print(f'GetItunes: {(end-start)*1000:.2f} millis')
    # base_url = 'https://itunes.apple.com/search?term={}&entity=song&limit='+str(limit)
    # response = NetLight.fetch(base_url.format(sanitizeQueryItunes(title)))
    logger.log(f'Got Itunes Response in {(end-start)*1000:.2f} millis')
    # results = json.loads(response.content)['results'] if response.status_code == 200 else []
    return results
    if not results: 
        return None
        # if main_artist is not None:
        #     return (yield from searchItunesSongOfArtist(main_artist,title))
    
    cutoff = 0.3
    matches:dict[ItunesResult,float] = {}
    titleMatcher = Ranker(title.casefold())
    albumMatcher = Ranker(removeBrackets(album or '').strip().casefold())
    artistMatcher = Ranker((main_artist or '').strip().casefold())
    for result in results:
        ratio = titleMatcher.ratioIfGreaterThan(result.title.casefold(),cutoff) or 0
        if album:
            ratio += albumMatcher.ratioIfGreaterThan(result.album.casefold(),cutoff) or 0
        if main_artist:
            artistMatcher.set_seq1(result.artist)
            ratio += artistMatcher.ratio() /  artistMatcher.real_quick_ratio()
        matches[result] = ratio
    return max(matches.keys(),key=matches.__getitem__)

    # # titleMatcher = Ranker(title)
    # if album:
    # for result in results:
    #     title_ratio = titleMatcher.ratioIfGreaterThan(result.title,cutoff)
    #     if title_ratio is None: continue
        

    #     if album:
    #         albumMatcher.set_seq1(removeBrackets(result.album))
    #         if albumMatcher.real_quick_ratio() < cutoff or albumMatcher.quick_ratio() < cutoff: continue
    #     if main_artist:
    #         p_artists = separateArtists(result.artist)
    #         for p_artist in p_artists:
    #             artistMatcher.set_seq1(p_artist)
    #             if artistMatcher.real_quick_ratio() >= 0.5 and artistMatcher.quick_ratio() >= 0.5 and artistMatcher.ratio() >= 0.5:
    #                 break
    #         else:
    #             continue #no matching artists
    #     ratio = titleMatcher.ratio()
    #     if ratio < cutoff: continue
    #     if album:
    #         albumScore = albumMatcher.ratio()
    #         if albumScore < cutoff: continue
    #         ratio *= albumScore
    #         ratio **= 0.5 #square root it
    #     result['artistName'] = p_artists
    #     possible_matches.append(result)
    
    # if len(possible_matches) == 0:
    #     return None

    # return max(possible_matches,key=lambda x: x['matchScore'])

def getYTSongsFromITunes(song:ItunesResult) -> typing.Generator[None,None,tuple[list[yttypes.YTVideo],yttypes.YTVideo|None]]:
    '''Async Function which returns a list of possible Videos and the one it thinks is most likely correct'''
    v = VideoSearch(removeLivestreams=True)
    yt_query = f'{song.title} {song.artist}' #This is the super scientific way of generating the optimal youtube query
    if song.explicit: #Youtube mostly tries to serve non-explicit results which is why we should specify explicitness when needed
        yt_query += ' Explicit'
    # print('Song:')
    # print('  Title:',song.title)
    # print('  Duration:',song.duration)
    # print('  Artist:',song.artist)
    # print('Query:',yt_query)
    yield from v.beginQueryAsync(yt_query)
    results = yield from v.getParsedAsync()
    if not results: return [],None
    #now we have a list of possible results
    title_ranker = Ranker(song.title)
    artist_ranker = Ranker(song.artist)

    
    def score(ytresult:yttypes.YTVideo) -> float: 
        score = 0.0
        ytsong = _shallowExtractDataFromYTVideo(ytresult)
        title_score = (title_ranker.ratioIfGreaterThan(ytsong.title,0.4) or 0.0) * 100 #matching title

        artist_score = (artist_ranker.ratioIfGreaterThan(', '.join(ytsong.artists or []),0.4) or 0.0) * 100 #matching artists

        verified_score = ytresult.channel.is_verified_artist * 10 #is channel verified?
        time_score = -abs(ytresult.duration - song.duration) #matching song length
        score = title_score + artist_score + verified_score + time_score
        # print(ytresult.url,'->',score)
        # print('  Title:',ytsong.title)
        # print('  Artist:',ytsong.artists)
        # print('  Duration:',ytresult.duration)
        # print('  Score Breakdown:',title_score,artist_score,verified_score,time_score)
        return score
    scores = {}
    for r in results:
        scores[r] = score(r)
        yield
    sorted_results = sorted(scores.keys(),key=scores.__getitem__,reverse=True)
    if scores[sorted_results[0]] < 0: #if highest score is negative (ie totaly not the song we're looking for)
        return results,None #assume the song is not easily matchable and leave it as a task for someone else
    return sorted_results,sorted_results[0]
        

        
def _shallowExtractDataFromYTVideo(vid:yttypes.YTVideo) -> DownloadingSong:
    out = DownloadingSong()
    if vid.channel.is_verified_artist:
        title = removeBrackets(vid.title)
        artist = vid.channel.name.removesuffix('VEVO')
        artists = [artist]
        if ' - ' in title:
            before,after = title.split(' - ',1)
            if artist in before:
                title = after
            elif artist in after:
                title = before
            else:
                title = after
            #get feats
            feats = getFeats(title)
            # print('feats:',feats)
            artists.extend(feats)

        out.artists = artists
        out.title = title
    else:
        title = vid.title
        if ' - ' in title: #all titles with this string are likely songs
            before,after = title.split(' - ',1)
            title = after
            artists = [before]
            #get feats
            feats = getFeats(title)
            artists.extend(feats)
        else:
            artists = []
        out.artists = artists
        out.title = title
    return out

class Ranker(SequenceMatcher):
    def __init__(self,match_against:str):
        super().__init__(None,'',match_against,False)

    def ratioIfGreaterThan(self,toMatch:str,cutoff:float):
        self.set_seq1(toMatch)
        if self.real_quick_ratio() <= cutoff or self.quick_ratio() <= cutoff: return None
        ratio = self.ratio()
        if ratio <= cutoff: return None
        return ratio
