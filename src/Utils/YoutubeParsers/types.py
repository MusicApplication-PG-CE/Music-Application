from . import utils
class Image:
    url:str
    width:int
    height:int
    __slots__ = 'url','width','height'
    @classmethod
    def fromstringlist(cls,string:bytes) -> list["Image"]:
        a = string
        l = []
        c = 0
        while True:
            c = a.find(b'{',c)
            if c == -1: break
            c = utils.indexEnd(a,b'url":',c)
            c = utils.indexEnd(a,b'"',c)
            url,c = utils.readFast(a,b'"',c)
            c = utils.indexEnd(a,b'width":',c)
            width,c = utils.readFast(a,b',',c)
            c = utils.indexEnd(a,b'height":',c)
            height,c = utils.readInt(a,c)
            img = Image()
            img.url = url.decode('ISO-8859-1')
            img.width = int(width)
            img.height = int(height)
            

            # try:
            #     a = a.split(b'{',1)[1]
            # except IndexError: #splitting will never error out, but the list indexing could and that means that we have run out of things to parse
            #     break
            # img = Image()
            # url,a = readString(a,b'url": "',b'"')
            # width,a = readString(a,b'width": ',b',')
            # height,a = readString(a,b'height": ',b'\n')
            # img.url = url.decode()
            # img.width = int(width)
            # img.height = int(height)
            l.append(img)
        return l
        
    @classmethod
    def new(cls,url:str,width:int,height:int):
        out = Image()
        out.url = url
        out.width = width
        out.height = height
        return out

    def __repr__(self):
        return f'YoutubeImage[url={self.url}, size=[{self.width},{self.height}]]'

class Channel:
    name:str
    id:str
    canonical_url:str
    is_verified_artist:bool
    thumbnails:list[Image]
    __slots__ = 'name','id','canonical_url','is_verified_artist','thumbnails'
    
    def __repr__(self) -> str:
        return f'Channel[{self.name}{' (Verified Artist)' if self.is_verified_artist else ''}]'
    #     return f'''YoutubeChannel[
    # name={self.name},
    # id={self.id},
    # canonical_url={self.canonical_url},
    # thumbnails={self.thumbnails}
    # ]'''

    @classmethod
    def unknown(cls):
        out = cls()
        out.name = 'UNKNOWN CHANNEL'
        out.id = 'UCBR8-60-B28hp2BmDPdntcQ' #Official Youtube Channel ID
        out.is_verified_artist = False
        out.thumbnails = []
        return out

class YTVideo:
    title:str
    id:str
    duration:int
    views:int
    thumbnails:list[Image]
    channel:Channel
    __slots__ = 'title','id','duration','views','thumbnails','channel'
    def __repr__(self) -> str:
        return f'''VideoResult[{self.title} [{self.id}],
duration={self.duration},
views={self.views},
thumbnails={len(self.thumbnails)},
channel={self.channel}
]'''
    
    def __hash__(self) -> int:
        return hash(self.id+'VIDEO')

    @property
    def url(self):
        return f'www.youtube.com/watch?v={self.id}'
    
    @classmethod
    def unknown(cls):
        out = YTVideo()
        out.title = "UNKNOWN"
        out.id = 'dQw4w9WgXcQ'
        out.duration = 0
        out.views = 0
        out.thumbnails = []
        out.channel = Channel.unknown()
        return out

class YTPlaylist:
    title:str
    id:str
    songs:int
    thumbnails:list[Image]
    channel:Channel
    __slots__ = 'title','id','songs','thumbnails','channel'
    def __repr__(self) -> str:
        return f'''PlaylistResult[
title={self.title},
id={self.id},
songs={self.songs},
thumbnails={self.thumbnails}
]'''
    def __hash__(self) -> int:
        return hash(self.id+'PLAYLIST')
