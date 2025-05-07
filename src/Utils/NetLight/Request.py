import typing
from .headers import Headers
class Request:
    '''
    To use, simply wrap the output of <waitResponse> with Request like 
     >>> client_request = Request(waitResponse(socket))
    '''
    @classmethod
    def GET(cls,headers:Headers|dict[str,str]):
        r = cls()
        r.method = 'GET'
        r.http_version = 'HTTP/1.1'
        r.body = b''
        r.headers = headers.copy() if isinstance(headers,Headers) else Headers(headers.items())
        return r


    http_version:str|typing.Literal['HTTP/1.1']
    method:typing.Literal['GET','POST','PUT','HEAD','CONNECT','PATCH','DELETE','OPTIONS','TRACE']|str
    target:str
    headers:Headers
    body:bytes

    __slots__ = 'http_version','method','target','body','headers'

    @property
    def content(self):
        return self.body
    
    @property
    def text(self):
        return self.body.decode('ISO-8859-1')

    @property
    def chunked(self):
        return self.headers.get('Transfer-Encoding','').lower() == 'chunked'

    def __repr__(self):
        if self.isInvalid():
            return f'Request(<INVALID>)'
        return f'Request({self.method} {self.target} {self.http_version}{" [Chunked]"if self.chunked else""})'
    
    def isInvalid(self):
        return self.http_version == ''