from . import types
from . import utils


def parsePlaylist(b:bytes) -> types.YTPlaylist:
    c = utils.indexEnd(b,b'sources":[')
    imglist,c = utils.readFast(b,b']',c)

    # imglist,a = readString(b,b'sources": [',b']')
    # c = utils.indexEnd(b,b'PLAYLISTS',c)
    # *_,a = a.split(b'PLAYLISTS',1)
    # c = utils.indexEnd(b,b'text":"',c)
    c = utils.indexEnd(b,b'text":')

    # t = b.find(b'video',c)
    
    # try:
    songs,c = utils.readWholeQuote(b,c)
    songs,_ = utils.readInt(songs)
    # songs,c = utils.readFast(b,b' ',c)
    # songs_string,a = readString(a,b'text": "',b' video')
    # except:
        # songs_string = '0'
        # _,a = a.split(b'text": "')

    c = utils.indexEnd(b,b'title":',c) # _,a= a.split(b'title": {',1)

    c = utils.indexEnd(b,b'content":',c)
    # c = utils.indexEnd(b,b'"',c)
    title,c = utils.readWholeQuote(b,c) #title,a = readString(a,b'content": "',b'"')

    c = utils.indexEnd(b,b'content":',c)
    channel_name,c = utils.readWholeQuote(b,c)
    #some channel_infos dont have channel_name and we can check that by
    # checking if the channel name was detected to be "Playlist"
    # and if the subsequent detected whole quote is "commandRuns"
    if channel_name == b'Playlist' and utils.readWholeQuote(b,c)[0] != b'commandRuns':
        channel_name = None
        channel_id = b''
        channel_canonical_url = b''
    else:
        c = utils.indexEnd(b,b'browseId":',c)
        channel_id,c = utils.readWholeQuote(b,c)
        c = utils.indexEnd(b,b'canonicalBaseUrl":')
        channel_canonical_url,c = utils.readWholeQuote(b,c)
    
    
    # c = utils.indexEnd(b,b'url":',c)
    stop = utils.indexEnd(b,b'delimiter":',c)
    is_checked = b.find(b'CHECK_CIRCLE_FILLED',c,stop) != -1 
    c = stop
    c = utils.indexEnd(b,b'contentId":',c)
    playlist_id,c = utils.readWholeQuote(b,c)
    if channel_name is None: #channel was not provided
        chan = types.Channel.unknown()
    else:
        chan = types.Channel()
        chan.canonical_url = channel_canonical_url.decode()
        chan.id = channel_id.decode()
        chan.name = channel_name.decode()
        chan.is_verified_artist = is_checked
        chan.thumbnails = [] 
    out = types.YTPlaylist()
    out.channel = chan
    out.id = playlist_id.decode()
    out.songs=int(songs)
    out.title=title.decode()
    out.thumbnails=types.Image.fromstringlist(imglist)
    return out

def parse(b:bytes):


    # c = utils.indexEnd(b,b'itemSectionRenderer')
    # c = utils.indexEnd(b,b'contents":',c)
    c = utils.indexEnd(b,b'lockupViewModel"')
    # a = b.split(b'itemSectionRenderer',1)[1].split(b'contents": [',1)[1]
    playlist_end = utils.indexEnd(b,b'continuationItemRenderer',c)
    _,*playlists = b[c:playlist_end].split(b'lockupViewModel')
    c = playlist_end

    # try:
    #     playlists,continuation = a.split(b'continuationItemRenderer',1)
    # except:
        # playlists = []
        # continuation_token =b''
    # else:

    c = utils.indexEnd(b,b'token":')

    continuation_token,_ = utils.readWholeQuote(b,c) #readString(continuation,b'token": "',b'"')
    return [parsePlaylist(x) for x in playlists],continuation_token.decode()

from .PlaylistInfo import parse as parseInfo #export