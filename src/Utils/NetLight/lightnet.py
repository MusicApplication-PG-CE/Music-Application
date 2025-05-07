import socket
try:from .utils import https_context
except:from utils2 import https_context #type: ignore
try:from .URL import URL 
except:from URL import URL #type: ignore
try:from .headers import Headers
except:from headers import Headers #type: ignore
import ssl
import _thread


class OpenedSocket:
    def __init__(self,sock:socket.socket):
        self.socket = sock
        self.file = sock.makefile('rb')

    def close(self):
        self.socket.close()
        self.file.close()

scheme_to_port = {'https':443,'http':80}
def makeSocket(url:'URL'):
    try:
        sock = socket.create_connection((url.host,scheme_to_port.get(url.scheme,0) if url.scheme else 0)) #make this faster
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if url.scheme == 'https':
            sock = https_context().wrap_socket(sock,server_hostname=url.host) #type: ignore
        return OpenedSocket(sock)
    except: #catch all exceptions
        raise ConnectionRefusedError('Check Internet Connection')
    
def makeSocketAsync(url:'URL'):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    ip_addr = socket.gethostbyname(url.host)
    port = scheme_to_port.get(url.scheme or '',0)
    done = False
    err = False
    def connect(ip_addr,port):
        nonlocal done,err,sock
        try:
            sock.connect((ip_addr,port))
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if url.scheme == 'https':
                sock = https_context().wrap_socket(sock,server_hostname=url.host) #type: ignore
        except BaseException as e:
            err = True
        done = True
    _thread.start_new_thread(connect,(ip_addr,port))
    while not done:
        yield
    if err:
        raise RuntimeError
    return OpenedSocket(sock) 
    
def makeServerSocket(ipv4:str,port:int):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ipv4,port))
    return sock


def readHeadersAndBody(s:OpenedSocket,headers:Headers):
    '''FOR INTERNAL USE ONLY: Assumes that the status/first line has already been read'''
    file_descriptor = s.file
    while (line:= file_descriptor.readline(2**16+1).strip()):
        name,value = line.decode('ISO-8859-1').split(':',1)
        headers.addHeader(name,value.removeprefix(' '))
    content_len = int(headers.get('Content-Length',-1))
    if content_len > 0:
        return file_descriptor.read(content_len)
    else: 
        return  b''
    
def readHeadersAndBodyAsync(s:OpenedSocket,headers:Headers):
    '''FOR INTERNAL USE ONLY: Assumes that the status/first line has already been read'''
    while (line:= (yield from readlineAsync(s)).strip()):
        name,value = line.decode('ISO-8859-1').split(':',1)
        headers.addHeader(name,value.removeprefix(' '))
    content_len = int(headers.get('Content-Length',-1))
    if content_len > 0:
        return (yield from readAsync(s,content_len))
    else: 
        return  b''

def readHeadersAndBodyGen(s:OpenedSocket,headers:Headers): # Generator Version that yields values corresponding to percent done
    '''FOR INTERNAL USE ONLY: Assumes that the status/first line has already been read'''
    file_descriptor = s.file
    while (line:= file_descriptor.readline(2**16+1).strip()):
        name,value = line.decode('ISO-8859-1').split(':',1)
        headers.addHeader(name,value.removeprefix(' '))
    content_len = int(headers.get('Content-Length',-1))
    content_left = content_len
    body = b''
    while content_left > 0:
        c = file_descriptor.read1(content_left)
        content_left -= len(c)
        body += c
        yield len(body)/content_len
    return body

def readAsync(s:OpenedSocket,l:int):
    '''Assumes that the socket is non-blocking and is SSLSocket'''
    b = []
    left = l
    while l!=len(b):
        try:
            portion = s.file.read1(left)
            left -= len(portion)
        except ssl.SSLWantReadError:
            yield
        else:
            b.append(portion)
    return b''.join(b)

def readlineAsync(s:OpenedSocket):
    '''Assumes that the socket is non-blocking and is SSLSocket'''
    while True:
        try:
            line = s.file.readline(2**16+1)
        except ssl.SSLWantReadError:
            yield
        else:
            return line

def isOnline(timeout:float|None = None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(('8.8.8.8',53))
    except (TimeoutError, OSError):
        return False
    else:
        return True
    finally:
        s.close()
