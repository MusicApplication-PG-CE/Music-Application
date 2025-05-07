from . import types
from . import utils

def parseContinuationToken(b:bytes,start:int=0,version:int=2):
    if version==2:
        c = b.find(b'continuationCommand":',start)
        if c == -1: return None
        c = utils.indexEnd(b,b'token":',c)
        token,_ = utils.readWholeQuote(b,c)
        return token.decode()
    elif version==1:
        return utils.readWholeQuote(b,start)[0].decode()
    raise RuntimeError

def parseVidRenderer(a:bytes,version:int):
    
    #videoId
    c = utils.indexEnd(a,b'videoId":')
    videoId,c = utils.readWholeQuote(a,c)

    #thumbnails
    c = utils.indexEnd(a,b'thumbnails":',c)#a.split(b'thumbnails": [',1)[1]
    start = c
    c = a.index(b']',c) #a.split(b']',1)
    thumbnails = a[start:c]

    #video title
    c = a.index(b'title":',c) # a = a.split(b'title": {',1)[1]
    c = utils.indexEnd(a,b'text":',c) # a = a.split(b'text": "',1)[1]
    title,c = utils.readWholeQuote(a,c)

    #channel type stuff
    c = utils.indexEnd(a,b'longBylineText',c) # a = a.split(b'longBylineText',1)[1]
    c = utils.indexEnd(a,b'"text":',c) # a = a.split(b'"text": "',1)[1]
    channel_name,c = utils.readWholeQuote(a,c) # channel_name,a = a.split(b'\n',1) # channel_name,*_ = channel_name.rsplit(b'"',1)
    # c = utils.indexEnd(a,b'webPageType":',c) # a = a.split(b'webPageType": "',1)[1]
    # channel_type,c = utils.readWholeQuote(a,c) # channel_type,a = a.split(b'\n',1)# channel_type,*_ = channel_type.rsplit(b'"',1)

    c = utils.indexEnd(a,b'browseEndpoint":',c)  # a = a.split(b'browseEndpoint": ',1)[1]
    c = utils.indexEnd(a,b'"browseId":',c)  # a = a.split(b'"browseId": "',1)[1]

    channel_id,c = utils.readWholeQuote(a,c) # channel_id,a = a.split(b'"',1)
    c = utils.indexEnd(a,b'canonicalBaseUrl":',c) # a = a.split(b'canonicalBaseUrl": "',1)[1]
    channel_canonical_url,c = utils.readWholeQuote(a,c) # channel_canonical_url,a = a.split(b'\n',1) # channel_canonical_url,*_ = channel_canonical_url.rsplit(b'"',1)

    #video length
    x = a.find(b'lengthText":',c)
    if x == -1:
        vid_len = -1
    else:
        c = utils.indexEnd(a,b'simpleText":',x)
        l,c = utils.readWholeQuote(a,c)
        vid_len = utils.parseDuration(l)

    #view count

    c = utils.indexEnd(a,b'viewCountText":',c)    # a = a.split(b'viewCountText": ',1)[1]
    
    c2 = a.find(b'simpleText":',c)
    if c2 == -1:
        c2 = utils.indexEnd(a,b'text":',c)
    else:
        c2 += 12 #len(b'simpleText": "')
    view_count,c2 = utils.readWholeQuote(a,c2)
    view_count = view_count.removesuffix(b's').removesuffix(b' view')

    #channel thumbnail
    e = utils.indexEnd(a,b'channelThumbnailSupportedRenderers":' if version==2 else b'channelThumbnail',c)
    #IS verified artist
    verified_artist = a.find(b'BADGE_STYLE_TYPE_VERIFIED_ARTIST' if version==2 else b"verifiedBadge",c,e) != -1
    c = e
    c = utils.indexEnd(a,b'"thumbnails":',c)# *_,a = a.split(b'"thumbnails": ',1)
    channel_thumbnail = a[c:a.index(b']',c)]# channel_thumbnail,*_ = a.split(b']',1)


    c = types.Channel()
    c.canonical_url = channel_canonical_url.decode()
    c.id = channel_id.decode()
    c.name = channel_name.decode()
    c.is_verified_artist= verified_artist
    c.thumbnails = types.Image.fromstringlist(channel_thumbnail)

    v = types.YTVideo()
    v.title = title.decode()
    v.id = videoId.decode()
    if view_count == b'No' or view_count == b'Shorts':
        v.views = -1
    else:
        v.views = int(view_count.replace(b',',b''))

    v.duration = vid_len
    v.channel = c
    v.thumbnails = types.Image.fromstringlist(thumbnails)
    return v



def parse(b:bytes) -> tuple[list[types.YTVideo],str|None]:
    # c = utils.indexEnd(b,b'primaryContents')
    # c = utils.indexEnd(b,b'contents":[',c)
    # c = b.index(b'contents":',c)
    # end = b.rindex(b'"header":{',c)
    results_start = utils.findEnd(b,b'videoRenderer":')
    if results_start == -1: 
        return [],None
    results_end = b.rfind(b'continuationItemRenderer":',results_start)
    if results_end == -1:
        results_end = b.rindex(b'continuation":',results_start)
        version = 1
    else:
        version = 2

    results = b[results_start:results_end].split(b'videoRenderer":')

    # results,*continuation_data = b[c:end].rsplit(b'"continuationItemRenderer": ',1)
    # pre,*results = results.split(b'videoRenderer": ')
    token = parseContinuationToken(b,results_end,version)
    out = []

    for x in results:
        out.append(parseVidRenderer(x,version))
    # corrected_query = parsePre(pre)
    return out,token #{