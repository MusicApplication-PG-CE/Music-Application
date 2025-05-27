import gzip
import brotli
import typing

from .YoutubeParsers import utils
from .YoutubeParsers.types import Image
from . import NetLight

class ItunesResult:
  title:str
  album:str
  artist:str
  thumbnail:Image
  duration:int
  release_date:str
  explicit:bool
  genre:str
  __slots__ = 'title','album','artist','thumbnail','duration','release_date','explicit','genre'
  def __repr__(self) -> str:
      return f'ItunesSong[{self.title}, {self.artist}, {self.album}]'


def percentDecode(s:str):
    map = {'%'+hex(i)[2:].upper():chr(i) for i in range(0x10,0xff+1)}
    map['%%'] = '%'
    for key,value in list(map.items())[::-1]:
        s = s.replace(key,value)
    return s



type JSONType = dict[str,"str|JSONType"]
type MusicAttributes = typing.Literal['mixTerm', 'genreIndex', 'artistTerm', 'composerTerm', 'albumTerm', 'ratingIndex', 'songTerm']
# from .debug import profile
# @profile
def parseSection(b:bytes) -> ItunesResult:
    c = utils.indexEnd(b,b'artistName":')
    artistName,c = utils.readWholeQuote(b,c)
    c = utils.indexEnd(b,b'collectionName":',c)
    albumName,c = utils.readWholeQuote(b,c)
    c = utils.indexEnd(b,b'trackName":',c)
    trackName,c = utils.readWholeQuote(b,c)
    # c = utils.indexEnd(b,b'artworkUrl30":',c)
    # artworkUrl30,c = utils.readWholeQuote(b,c)
    # c = utils.indexEnd(b,b'artworkUrl60":',c)
    # artworkUrl60,c = utils.readWholeQuote(b,c)
    c = utils.indexEnd(b,b'artworkUrl100":',c)
    artworkUrl100,c = utils.readWholeQuote(b,c)
    c = utils.indexEnd(b,b'releaseDate":',c)
    releaseDate,c = utils.readWholeQuote(b,c)
    c = utils.indexEnd(b,b'trackExplicitness":',c)
    explicitness,c = utils.readWholeQuote(b,c)
    c = utils.indexEnd(b,b'trackTimeMillis":',c)
    trackTimeMillis,c = utils.readInt(b,c)
    c = utils.indexEnd(b,b'primaryGenreName":',c)
    primaryGenreName,c = utils.readWholeQuote(b,c)

    out = ItunesResult()
    out.artist = artistName.decode()
    out.album = albumName.decode()
    out.title = trackName.decode()
    out.thumbnail = Image.new(artworkUrl100.decode(),100,100)
    out.release_date = releaseDate.decode()
    out.explicit = explicitness.decode().lower()=='explicit'
    out.duration = (int(trackTimeMillis)/1000).__ceil__()
    out.genre = primaryGenreName.decode()
    return out

def parse(b:bytes) -> list[ItunesResult]:
    _,*sections = b.split(b'wrapperType":')
    return [parseSection(s) for s in sections]

def fastBuildJSON(x:JSONType|str):
    if isinstance(x,str):
        return f'"{x}"'
    elif isinstance(x,list):
        return ','.join([fastBuildJSON(c) for c in x]).join(['[',']'])
    values = [f'"{key}":{fastBuildJSON(value)}' for key,value in x.items()]
    return f"{{{','.join(values)}}}"

def percentEncode(x:str): #only tested to work with youtube query characters!
    the_specials = {'$', '&', '#', '%', '[', '\\', ',', '?', '{', '}', '+', ';', ':', '|', '@', "'", '/', '=', '^', ']','(',')','-'}
    mappings = {char:f'%{hex(ord(char))[2:]}'.upper() for char in the_specials}
    trans_table = str.maketrans(mappings|{' ':'+'})
    return x.translate(trans_table)

class ITunesSearch:
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    apiKey = 'AIzaSyCtkvNIR1HCEwzsqK6JuE6KqpyjusIRI30'
    baseUrl = 'https://itunes.apple.com/search?'

    __slots__ = 'country','sock','url','headers','parameters'

    def __init__(self,country:str='US',searchBy:MusicAttributes|None=None) -> None:
        self.country= country
        self.sock = None
        self.url = None
        self.headers = {
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'User-Agent': self.userAgent,
            'Accept-Encoding': 'br, gzip, identity',
        }
        self.parameters = {
            'media':'music', #media type is song
            'entity':'song' #subtype of media
        }
        if searchBy is not None:
            self.parameters['attribute'] = searchBy

    def setSearchBy(self,searchBy:MusicAttributes|None) -> MusicAttributes|None:
        if searchBy is None:
            return self.parameters.pop('attributes',None)
        ret = self.parameters.get('attributes')
        self.parameters['attributes'] = searchBy
        return ret


    def sendQuery(self,query:str,limit:int|None=None,__i:int=0):
        '''This is the function that will begin the query to Itunes API'''
        if self.url is not None: #there is a request in progress
            raise RuntimeError 
        query = percentEncode(query)
        params:dict[str,str] = {'term':query} | self.parameters
        if limit:
            params['limit'] = str(limit)
        url_query = '&'.join(['='.join(item) for item in params.items()])
        self.url = NetLight.URL(self.baseUrl+url_query)
        if self.sock is None:
            self.sock = NetLight.makeSocket(self.url)
        try:
            NetLight.POST(self.sock,self.url,self.headers,b'')
        except ConnectionError:
            if __i < 3:
                self.sock.close()
                self.sock = None
                self.url = None
                self.sendQuery(query,limit,__i+1)    
            else:
                raise
    def getResponse(self):
        assert self.sock is not None
        response = NetLight.waitResponse(self.sock)
        self.url = None
        if response.isInvalid():
            self.sock.close()
            self.sock = None #close the socket
            raise ConnectionError
        if response.chunked:
            parts = [response.body]
            while (d:= NetLight.waitChunkResponse(self.sock)):
                parts.append(d)
            _ = self.sock.file.read1() #Finalizer Packet 
            response.body = b''.join(parts)
        encoding = response.content_encoding
        if encoding == 'br':
            response.body = brotli.decompress(response.body)
        elif encoding == 'gzip':
            response.body = gzip.decompress(response.body)
        return response
    

    def getResponseAsync(self):
        response = yield from NetLight.waitResponseAsync(self.sock)
        print('got response')
        self.url = None
        if response.isInvalid():
            self.sock.close()
            self.sock = None #close the socket
            raise ConnectionError
        print('response:',response)
        if response.chunked:
            parts = [response.body]
            while (d:= NetLight.waitChunkResponse(self.sock)):
                parts.append(d)
            _ = self.sock.file.read1() #Finalizer Packet 
            response.body = b''.join(parts)
        encoding = response.content_encoding

        if encoding == 'br':
            response.body = brotli.decompress(response.body)
        elif encoding == 'gzip':
            response.body = gzip.decompress(response.body)
        return response

    def canContinue(self):
        return False

    def canRead(self):
        return True

    def getParsed(self):
        response = self.getResponse()
        return parse(response.body)
    
    def getParsedAsync(self):
        response = yield from self.getResponseAsync()
        return parse(response.body)

    def beginQuery(self,query:str,limit:int|None=None):
        self.sendQuery(query,limit)

    def continueQuery(self):
        raise RuntimeError('Itunes Query Cannot be continued')

    def setContinuationToken(self,token:str|None):
        raise RuntimeError

class ITunesSongByName(ITunesSearch):
    def __init__(self,country:str='US') -> None:
        super().__init__(country,'songTerm')