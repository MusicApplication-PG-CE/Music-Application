import gzip
import brotli
import typing
import select

from . import NetLight

from .YoutubeParsers import Video,Playlist

type JSONType = dict[str,"str|JSONType"]
type SearchModeType = typing.Literal['EgIQAQ%3D%3D','EgIQAg%3D%3D','EgIQAw%3D%3D','EgJAAQ%3D%3D']

__all__ = [
    'YoutubeSearch',
    'VideoSearch',
    'PlaylistSearch',
    'PlaylistInfo',
    'VideoInfo'
]

# YouTube on TV client secrets
# _client_id = '861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com'
# _client_secret = 'SboVhoG9s0rNafixCSGGKXAT'

# Extracted API keys -- unclear what these are linked to.
# _api_keys = [
#     'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8', #currently in use
#     'AIzaSyCtkvNIR1HCEwzsqK6JuE6KqpyjusIRI30',
#     'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
#     'AIzaSyC8UYZpvA2eknNex0Pjid0_eTLJoDu6los',
#     'AIzaSyCjc_pVEDi4qsv5MtC2dMXzpIaDoRFLsxw',
#     'AIzaSyDHQ9ipnphqTzDqZsbtd8_Ru4_kiKVQe2k'
# ]

class SearchMode:
    videos = 'EgIQAQ%3D%3D'
    channels = 'EgIQAg%3D%3D' #unused
    playlists = 'EgIQAw%3D%3D'
    livestreams = 'EgJAAQ%3D%3D' #unused
    
def fastBuildJSON(x:JSONType|str):
    t = type(x)
    if  t is int:
        return str(x)
    elif t is str:
        return f'"{x}"'
    elif t is list:
        return '[' + ','.join([fastBuildJSON(c) for c in x]) + ']'
    assert isinstance(x,dict)
    values = [f'"{key}":{fastBuildJSON(value)}' for key,value in x.items()]
    return f"{{{','.join(values)}}}"

def percentEncode(x:str): #only tested to work with youtube query characters!
    the_specials = {'$', '&', '#', '%', '[', '\\', ',', '?', '{', '}', '+', ';', ':', '|', '@', "'", '/', '=', '^', ']'}
    mappings = {char:f'%{hex(ord(char))[2:]}'.upper() for char in the_specials}
    trans_table = str.maketrans(mappings|{' ':'+'})
    return x.translate(trans_table)


class YoutubeSearch:
    # userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    apiKey = 'AIzaSyCtkvNIR1HCEwzsqK6JuE6KqpyjusIRI30'
    baseUrl = 'https://www.youtube.com/youtubei/v1/search?' 

    __slots__ = 'language','region','sock','url','query','continuation_token','headers','version'

    def __init__(self,language:str='en', region:str='US') -> None:
        self.language = language
        self.region = region
        self.sock = None
        self.url = NetLight.URL(self.baseUrl+'key='+self.apiKey+'&prettyPrint=false')
        self.query = None
        self.continuation_token = None
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'br, gzip, identity',
            'Connection': 'keep-alive',
            'User-Agent': self.userAgent,
            'Content-Type': 'application/json'
        }
        self.version:typing.Literal['MOBILE','DESKTOP'] = 'DESKTOP'

    ### PURE FUNCTIONS ###  
    def buildRequestBody(self,query:str,continuation_token:str|None=None) -> JSONType:
        a:dict[str,dict|str] = {
            "context": {
                "client": {
                    "deviceMake":"","deviceModel":"","visitorData":"",

                    "clientName":"WEB",
                    "clientVersion":"{}.20250312.04.00".format({'MOBILE':'1','DESKTOP':'2'}[self.version]),
                    "platform":"DESKTOP","clientFormFactor":"UNKNOWN_FORM_FACTOR",
                    "browserName":"Chrome","browserVersion":"133.0.0.0",

                    # "newVisitorCookie":'true',
                    "hl":self.language,
                    "gl":self.region,
                },
                "user": {
                    "lockedSafetyMode":'false',
                }
            }
        }
        if continuation_token is not None:
            a["continuation"]=continuation_token
        return a
    
    def sendQueryAsync(self,query:str,continuation_token:str|None=None,_i:int=0):
        # query = percentEncode(query)
        body = fastBuildJSON(self.buildRequestBody(query,continuation_token)).encode('ISO-8859-1')
        if self.sock is None:
            self.sock = yield from NetLight.makeSocketAsync(self.url)
        try:
            NetLight.POST(self.sock,self.url,self.headers,body)
        except ConnectionError:
            if _i < 3:
                self.sock.close()
                self.sock = None
                self.sendQuery(query,continuation_token,_i+1)
            else:
                raise 

    def sendQuery(self,query:str,continuation_token:str|None=None,_i:int=0):
        '''This is the function that will begin the query to Youtube's Inner API'''
        # query = percentEncode(query)
        body = fastBuildJSON(self.buildRequestBody(query,continuation_token)).encode('ISO-8859-1')
        if self.sock is None:
            self.sock = NetLight.makeSocket(self.url)
        try:
            NetLight.POST(self.sock,self.url,self.headers,body)
        except ConnectionError:
            if _i < 3:
                self.sock.close()
                self.sock = None
                self.sendQuery(query,continuation_token,_i+1)
            else:
                raise 

    def getResponse(self):
        assert self.sock is not None
        import time
        start = time.perf_counter()
        response = NetLight.waitResponse(self.sock)
        end = time.perf_counter()
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
        assert self.sock is not None
        response = yield from NetLight.waitResponseAsync(self.sock)
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

    def canRead(self) -> bool:
        if self.sock is None: return False
        # assert self.sock is not None
        return select.select([self.sock.socket],[],[],0.001)[0] #type: ignore

    def canContinue(self):
        return self.continuation_token is not None

    ### MUTATING FUNCTIONS ###
    def beginQuery(self,query:str):
        self.query = query
        self.sendQuery(query,None)

    def beginQueryAsync(self,query:str):
        self.query = query
        yield from self.sendQueryAsync(query,None)

    def resetSock(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def continueQuery(self):
        if self.query is None:
            raise RuntimeError('No existing query to continue')
        if self.continuation_token is None:
            raise RuntimeError('Existing query cannot be continued')
        self.sendQuery(self.query,self.continuation_token)

    def continueQueryAsync(self):
        if self.query is None:
            raise RuntimeError('No existing query to continue')
        if self.continuation_token is None:
            raise RuntimeError('Existing query cannot be continued')
        yield from self.sendQueryAsync(self.query,self.continuation_token)

    def setContinuationToken(self,token:str|None):
        self.continuation_token = token


class VideoSearch(YoutubeSearch):
    def __init__(self, language = 'en', region = 'US',removeLivestreams:bool=False):
        super().__init__(language, region)
        self.remove_livestreams = removeLivestreams

    ### PURE FUNCTIONS ###
    def buildRequestBody(self,query:str,continuation_token:str|None=None):
        a = super().buildRequestBody(query,continuation_token)
        a['params'] = SearchMode.videos
        a['query'] = query
        return a
           
    ### MUTATING FUNCTIONS ###
    def getParsed(self):
        r = self.getResponse()
        results,cont_token =  Video.parse(r.body)
        self.setContinuationToken(cont_token)
        return [result for result in results if result.views != -1] if self.remove_livestreams else results
    
    def getParsedAsync(self):
        r = yield from self.getResponseAsync()
        results,cont_token = Video.parse(r.body)
        self.setContinuationToken(cont_token)
        return [result for result in results if result.views != -1] if self.remove_livestreams else results
    
class PlaylistSearch(YoutubeSearch):

    ### PURE FUNCTIONS ###
    def buildRequestBody(self,query:str,continuation_token:str|None=None):
        a = super().buildRequestBody(query,continuation_token)
        a['query'] = query
        a['params'] = SearchMode.playlists
        return a
        
    ### MUTATING FUNCTIONS ###
    def getParsed(self):
        r = self.getResponse()
        results,cont_token =  Playlist.parse(r.body)
        self.setContinuationToken(cont_token)
        return results


class PlaylistInfo(YoutubeSearch):
    baseUrl = 'https://www.youtube.com/youtubei/v1/browse?' 

    ### PURE FUNCTIONS ###
    def buildRequestBody(self,query:str,continuation_token:str|None=None):
        a = super().buildRequestBody(query,continuation_token)
        a['browseId'] = f'VL{query}'
        a['query'] = query
        return a
    
    ### MUTATING FUNCTIONS ###
    def getParsedAsync(self):
        r = yield from self.getResponseAsync()
        results,cont_token = Playlist.parseInfo(r.body)
        self.setContinuationToken(cont_token)
        return results
    
    
    def getParsed(self):
        r = self.getResponse()
        results,cont_token =  Playlist.parseInfo(r.body)
        self.setContinuationToken(cont_token)
        return results

    def gatherAllParsed(self):
        yield self.getParsed()
        while self.continuation_token is not None:
            self.continueQuery()
            yield self.getParsed()
            
class VideoInfo(YoutubeSearch):
    baseUrl = 'https://www.youtube.com/youtubei/v1/player?'

    def buildRequestBody(self,query:str,continuation_token:str|None=None) -> JSONType:
        body= {"context":{
                    "client":{
                        "hl":self.language,"gl":self.region,
                        "deviceMake":"","deviceModel":"","visitorData":"",
                        "clientName":"WEB",
                        "clientVersion":"2.20250304.01.00",
                        "originalUrl":f"https://www.youtube.com/watch?v={query}",
                        "platform":"DESKTOP","clientFormFactor":"UNKNOWN_FORM_FACTOR",
                        "browserName":"Chrome","browserVersion":"133.0.0.0",
                        "acceptHeader":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    },
                    "user":{"lockedSafetyMode":'false'},
                },
                "videoId":query,
                "racyCheckOk":'true', #dont really know what this does
                "contentCheckOk":'true', #^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        }
        return body

    
    def get(self,videoId:str):
        self.sendQuery(videoId,None) 
        return self.getResponse()    

class VideoInfo2(VideoInfo):
    baseUrl = 'https://www.youtube.com/youtubei/v1/next?'
    def buildRequestBody(self, query: str, continuation_token: str | None = None) -> dict[str, str | JSONType]:
        a = super().buildRequestBody(query,continuation_token)
        a['params'] = "8gMFDT6N5D0%3D"
        # a['autonavState'] = "STATE_OFF"

        # a["captionsRequested"]='true'

        return a

