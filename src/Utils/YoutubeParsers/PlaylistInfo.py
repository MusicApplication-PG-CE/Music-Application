from . import types
from . import utils

def parseVideoRenderer2(b:bytes):
    c = utils.indexEnd(b,b'videoId":"')
    videoId,c = utils.findEndOfQuote(b,c)

    c = utils.indexEnd(b,b'thumbnails":',c)
    thumbnails,c = utils.readFast(b,b']',c)
    c = utils.indexEnd(b,b'text":"')
    title,c = utils.findEndOfQuote(b,c)

    # title,a = readString(a,b'text": "',b'\n')

    # title = title.strip()[:-1]
    try:
        c = utils.indexEnd(b,b'label":"',c)
        
        views,c = utils.findEndOfQuote(b,c)
        views_stop = views.rindex(b' view')
        views_start = views.rindex(b' ',None,views_stop)+1
        views = views[views_start:views_stop].replace(b',',b'')
    except:
        print(views)
        views = -1


    # try:int(views)
    # except:views='0'
    c = utils.indexEnd(b,b'text":"',c)
    channel_name,c, = utils.findEndOfQuote(b,c)


    # channel_name,a = readString(a,b'text": "',b'\n')
    # channel_name = channel_name.strip()[:-2]
    c = utils.indexEnd(b,b'browseId":"',c)
    channel_id,c = utils.findEndOfQuote(b,c)
    c = utils.indexEnd(b,b'canonicalBaseUrl":"',c)
    channel_url,c = utils.findEndOfQuote(b,c)
    # channel_url,a = readString(a,b' "',b'"')
    c = utils.indexEnd(b,b'lengthSeconds":"',c)
    length,c = utils.findEndOfQuote(b,c)
    # len_secs,a = readString(a,b'lengthSeconds": "',b'"')    
    if views == -1:
        c = utils.indexEnd(b,b'videoInfo":',c)    
        c = utils.indexEnd(b,b'text":"',c)
        b_views,c = utils.findEndOfQuote(b,c)
        if b'view' in b_views:
            b_views,_ = b_views.split(b' view',1)
            suffix = b_views[-1:]
            if suffix.isdigit():
                views = int(suffix)
            else:
                mult = {'k'.casefold():1_000,'m'.casefold():1_000_000,'b'.casefold():1_000_000_000}[suffix.decode().casefold()]
                views = float(b_views[:-1].decode()) * mult


    channel = types.Channel()
    channel.name = channel_name.decode('ISO-8859-1')
    channel.canonical_url = channel_url.decode()
    channel.id = channel_id.decode()
    channel.thumbnails = []
    channel.is_verified_artist = False#'WEB_PAGE_TYPE_WATCH'

    out = types.YTVideo()
    out.views = int(views)
    out.title = title.decode('ISO-8859-1')
    out.id = videoId.decode()
    out.thumbnails = types.Image.fromstringlist(thumbnails)
    out.duration = int(length) 
    out.channel = channel
    return out

def parse(b:bytes):
    # c = utils.indexEnd(b,b'contents":')
    # c = utils.indexEnd(b,b'contents":',c)
    c = b.find(b'playlistVideoListRenderer')
    if c==-1:
        c = utils.indexEnd(b,b'continuationItems')
        #doesnt have the canReorder
        stop = -1
    else:
        stop = b.index(b'canReorder"')

    # c = utils.indexEnd(b,b'contents":',c)
    stop = b.find(b'continuationItemRenderer"',c,stop)
    
    _,*vids = b[c:stop].split(b'playlistVideoRenderer')

    if stop != -1:
        c = utils.indexEnd(b,b'token":',stop)
        cont,c = utils.readWholeQuote(b,c)
        cont = cont.decode()
    else:
        cont = None
    out = []
    for v in vids:
        try:
            out.append(parseVideoRenderer2(v))
        except ValueError:
            import logger
            logger.log('[Error] in parseVideoRenderer2. This is likely due to Youtube changing the json served on a whim *sigh*')

    return out,cont
    # return [parseVideoRenderer2(v) for v in vids],cont
