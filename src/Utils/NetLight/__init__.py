'''NetLight is a library made to simplify the awfully complex mess of libraries surrounding internet networking.
 It operates directly on the low-level socket module

Main Dependencies:
 * Socket
 * SSL (for HTTPS connections)
 * Some Compression Libraries
'''
#These top 3 imports are only for ConnectionPool, if you dont need that then comment them out.
from typing import Callable, Any
from collections import deque
import _thread
import brotli
import gzip
import sys

from .lightnet import OpenedSocket
from .lightnet import URL
from .lightnet import isOnline
from .lightnet import makeSocketAsync
from .lightnet import makeSocket as _makeSocket
from .lightnet import readHeadersAndBody as _readHeadersAndBody
from .lightnet import readHeadersAndBodyGen as _readHeadersAndBodyGen
from .lightnet import readHeadersAndBodyAsync as _readHeadersAndBodyAsync
from .lightnet import readlineAsync as _readlineAsync
from .utils import reorder_headers
from .const import DEFAULT_HTTP_VERSION,METHODTYPE
from .Response import Response
from .Request import Request
from .headers import Headers

__all__ = [
    'fetchWithRedirects',
    'fetch',
    'makeSocket',
    'makeSocketAsync',
    'POST',
    'GET',
    'waitResponse',
    'waitRequest',
    'sendRequest',
    'sendResponse',
    'waitChunkResponse',
    'isOnline',
    'Request',
    'Response',
    'Headers',
    'OpenedSocket',
    'URL'
]

### EXTREMELY SIMPLE API ###

def fetchWithRedirects(url_:str,accept_encoding:list[str] = ['identity'],remember_redirects:bool = True) -> tuple[Response,list[Response]]:
    responses:list[Response] = []
    while True:
        response = fetch(url_,accept_encoding)
        if remember_redirects:
            responses.append(response)
        if (response.status_code == 302 or #Temporarily Moved 
            response.status_code == 301): #Permanently Moved
            url_ = response.headers['Location'] #type: ignore
        else:
            break
    return (response,responses)

def fetch(url_:str,accept_encoding:list[str] = ['identity']):
    url = URL(url_)

    headers = {
        'User-Agent':'Netlight',
        'Accept-Encoding':', '.join(accept_encoding),
        'Connection':'close'
    }
    
    s = _makeSocket(url)
    GET(s,url,headers)
    r = waitResponse(s)
    if r.chunked: 
        while d:= waitChunkResponse(s):
            r.body += d
        s.file.read1() # final chunk packet
    return r
def fetchAsync(url_:str,accept_encoding:list[str] = ['identity']):
    url = URL(url_)

    headers = {
        'User-Agent':'Netlight',
        'Accept-Encoding':', '.join(accept_encoding),
        'Connection':'close'
    }
    
    s = yield from makeSocketAsync(url)
    GET(s,url,headers)
    r = yield from waitResponseAsync(s)
    if r.chunked: 
        while d:= waitChunkResponse(s):
            r.body += d
            yield
        s.file.read1() # final chunk packet
    return r
### END EXTREMELY SIMPLE API ###

### PUBLIC API ###


def makeSocket(url:'URL'):
    return _makeSocket(url)

def POST(socket:OpenedSocket,url:URL,headers:dict[str,str]|Headers,body:bytes):
    assert 'Host' not in headers
    headers = Headers(headers.items()) if isinstance(headers,dict) else headers.copy()
    headers['Host'] = url.host
    _sendRequest(socket,'POST',url.inner_url,DEFAULT_HTTP_VERSION,headers,body)

def GET(socket:OpenedSocket,url:URL,headers:dict[str,str]|Headers):
    'Sends a GET request'
    assert 'Host' not in headers
    headers = Headers(headers.items()) if isinstance(headers,dict) else headers.copy()
    headers['Host'] = url.host #type: ignore
    _sendRequest(socket,'GET',url.inner_url,DEFAULT_HTTP_VERSION,headers,b'')

def waitResponse(socket:OpenedSocket) -> Response:
    response = Response()
    file_descriptor = socket.file
    response.headers = Headers()
    status_line = file_descriptor.readline(2**16+1).strip()
    if not status_line:
        response.http_version = ''
        return response
    response.http_version,status_code,response.reason_phrase = status_line.decode('ISO-8859-1').strip().split(' ',2)
    response.status_code = int(status_code)
    response.body = _readHeadersAndBody(socket,response.headers)
    return response

def waitResponseAsync(socket:OpenedSocket):
    response = Response()
    response.headers = Headers()
    socket.socket.setblocking(False)
    status_line = (yield from _readlineAsync(socket))
    if not status_line:
        response.http_version = ''
        return response
    response.http_version,status_code,response.reason_phrase = status_line.decode('ISO-8859-1').strip().split(' ',2)
    response.status_code = int(status_code)
    response.body = yield from _readHeadersAndBodyAsync(socket,response.headers)
    socket.socket.setblocking(True)
    return response

def waitResponseGen(socket:OpenedSocket):
    response = Response()
    file_descriptor = socket.file
    response.headers = Headers()
    status_line = file_descriptor.readline(2**16+1).strip()
    if not status_line:
        response.http_version = ''
        return response
    response.http_version,status_code,response.reason_phrase = status_line.decode('ISO-8859-1').strip().split(' ',2)
    response.status_code = int(status_code)
    
    response.body = yield from _readHeadersAndBodyGen(socket,response.headers)
    return response

def waitRequest(socket:OpenedSocket) -> Request:
    request = Request()
    file_descriptor = socket.file
    request.headers = Headers()
    status_line = file_descriptor.readline(2**16+1).strip()
    if not status_line:
        request.http_version = ''
        return request

    request.method,request.target,request.http_version = status_line.decode('ISO-8859-1').split(maxsplit=2)
    request.body = _readHeadersAndBody(socket,request.headers)
    return request

def sendRequest(socket:OpenedSocket,url:URL,request:Request):
    assert 'Host' not in request.headers
    headers = request.headers.copy()
    headers['Host'] = url.host
    _sendRequest(socket,request.method,url.inner_url, #type: ignore
                 request.http_version,headers,request.body)

def sendResponse(socket:OpenedSocket,response:Response):
    _sendResponse(socket,response.status_code,response.reason_phrase,
                  response.http_version,response.headers,response.body)

def waitChunkResponse(socket:OpenedSocket):
    '''Implements protocol for reading Transfer-Encoding: chunked packets'''
    file = socket.file
    l = file.readline(2**16+1).strip().decode('ISO-8859-1')
    length = int(l,base=16)
    if not length: return b''

    data = file.read(length)
    end = file.read(2)
    assert end == b'\r\n',f'end wrong! END: {end}'
    return data
        
### END PUBLIC API ###
class ConnectionPool:
    def __init__(self,max_workers:int):
        self.max_workers = max_workers
        self.queue:deque[tuple[URL,Callable]] = deque()
        self.queue_lock = _thread.allocate_lock()
        self.workers_alive = [0] #must be a list because we need the threads to change the number

    def queueUrl(self,url_:str,callback:Callable[[bytes],Any]):
        url = URL(url_)
        #if there is a sleeping worker 
        entry = url,callback
        if self.workers_alive[0] < self.max_workers:
            self.workers_alive[0] += 1
            _thread.start_new_thread(poolWorker,(entry,self.queue,self.queue_lock,self.workers_alive))
            return 
        else:
            self.queue.append(entry)
            
def poolWorker(current:tuple[URL,Callable],queue:deque[tuple[URL,Callable]],lock:_thread.LockType,worker_count:list[int]):
    try:
        _POOL_WORKER_HEADERS = {
            'User-Agent':'Netlight-PoolWorker',
            'Accept-Encoding':'br, gzip, identity',
            'Connection':'keep-alive'
        }
        url,callback = current
        sock = _makeSocket(url)
 
        while True:
            #send
            GET(sock,url,_POOL_WORKER_HEADERS)
            response = waitResponse(sock)
            encoding = response.content_encoding
            if encoding == 'gzip':
                response.body = gzip.decompress(response.body)
            elif encoding == 'br':
                response.body = brotli.decompress(response.body)
            if response.isInvalid():
                print('InvalidResponse')
                queue.append((url,callback))
            else:
                callback(response.body)
            #Get Next 
            '''
            This Algorithm will look ahead n entries in a deque for a target value.
            If the target is not found, the first entry is taken instead.
            The resulting queue has the same order except for the missing value.
            '''
            with lock:
                if not queue: break 
                LOOKAHEAD = 6 #heuristic: dont go go below 3
                for i in range(min(LOOKAHEAD,len(queue))):
                    if url.sameConn(queue[0][0]):
                        url,callback = queue.popleft()
                        queue.rotate(i)
                        break
                    queue.rotate(-1)
                else:
                    queue.rotate(i) #type: ignore
                    #if we get here then we need to reset the socket because we are not reusing the same connection
                    url,callback = queue.pop()
                    # sock.close() #let the os close the socket
                    sock = makeSocket(url)

                    # switches += 1  #type: ignore

        worker_count[0] -= 1
    except:
        #check if we are in interpreter shutdown 
        if not sys.is_finalizing():
            raise

### PRIVATE API ###

def _sendRequest(socket:OpenedSocket,method:METHODTYPE,url:str|None,version:str,headers:Headers,body:bytes): 
    '''Is *NOT* a part of the public facing API, arg <url> has different semantics than POST, GET and sendResquest'''
    first:bytes = f'{method} {url or "/"} {version}'.encode('ISO-8859-1',errors='ignore')
    _sendPacket(socket,first,headers,body)
    
def _sendResponse(socket:OpenedSocket,status_code:int,reason_phrase:str,version:str,headers:Headers,body:bytes): 
    '''Is *NOT* a part of the public facing API, arg <url> has different semantics than POST, GET and sendResquest'''
    first = f'{version} {status_code} {reason_phrase}'.encode('ISO-8859-1')
    _sendPacket(socket,first,headers,body)

def _sendPacket(socket:OpenedSocket,first_line:bytes,headers:Headers,body:bytes):
    if 'Content-Length' not in headers:
        headers['Content-Length'] = str(len(body))
    lines = [first_line]
    for header_name in reorder_headers(headers.headers.keys()):
        header_values = headers.headers[header_name]
        for value in header_values:
            lines.append(header_name.encode('ISO-8859-1')+ b': ' + value.encode('ISO-8859-1'))
    lines.append(b'')
    lines.append(body)
    payload = b'\r\n'.join(lines)
    socket.socket.sendall(payload)
