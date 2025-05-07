import typing
from . import status_codes as sc
from .headers import Headers
from .const import DEFAULT_HTTP_VERSION
StrLike = typing.TypeVar('StrLike',bound=str,covariant=True)

class Response:
    '''Meant to mimic the <Response> Objects of other modules like requests and urllib. This allows for simpler migration of code.

    To use, simply wrap the output of <waitResponse> with Reponse like 
     >>> response = Response(waitResponse(socket))
    '''
    @classmethod
    def build(cls,status_code:int,headers:dict[StrLike,str]|Headers,body:bytes):
        out = Response()
        out.http_version = DEFAULT_HTTP_VERSION
        out.status_code = status_code
        out.reason_phrase = sc._CODE_TO_NAME.get(status_code,'Unknown') #type:ignore
        out.headers = headers if isinstance(headers,Headers) else Headers(headers.items())
        out.body = body
        return out

    @classmethod
    def Forbidden(cls,headers:dict[StrLike,str]|Headers):
        return cls.build(sc.FORBIDDEN,headers,b'')
    
    @classmethod
    def BadRequest(cls,headers:dict[StrLike,str]|Headers):
        return cls.build(sc.BAD_REQUEST,headers,b'')
    
    @classmethod
    def NotFound(cls,headers:dict[StrLike,str]|Headers):
        return cls.build(sc.NOT_FOUND,headers,b'')
    
    @classmethod
    def InternalServerError(cls,headers:dict[StrLike,str]|Headers):
        return cls.build(sc.INTERNAL_SERVER_ERROR,headers,b'')
    
    @classmethod
    def NotImplemented(cls,headers:dict[StrLike,str]|Headers):
        return cls.build(sc.NOT_IMPLEMENTED,headers,b'')
    

    http_version:str
    status_code:int
    reason_phrase:str
    headers:Headers
    body:bytes

    __slots__ = 'http_version','status_code','reason_phrase','body','headers'

    @property
    def content(self):
        return self.body
    
    @property
    def text(self):
        return self.body.decode('ISO-8859-1')
 
    @property
    def content_encoding(self):
        '''Content Encoding of HTTP Body. "identity" means no encoding. <None> means encoding not found.'''
        return self.headers.get('Content-Encoding')

    @property
    def chunked(self):
        return self.headers.get('Transfer-Encoding','').lower() == 'chunked'

    def isInvalid(self):
        return self.http_version == ''

    def __repr__(self):
        try:
            return f'Response({self.http_version} {self.status_code} \
    {self.reason_phrase}, Body[{len(self.content)}]{" [Chunked]"if self.chunked else""})'
        except:
            return 'Response[Error]'
        
    def toString(self):
        return f'''Response[
{self.http_version} {self.status_code} {self.reason_phrase}
{self.headers.toString()}
{self.body.decode('utf-8','ignore')}
]'''