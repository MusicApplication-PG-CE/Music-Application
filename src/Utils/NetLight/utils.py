import typing
try:from .const import DEFAULT_HTTP_VERSION
except:from const import DEFAULT_HTTP_VERSION #type: ignore
import ssl
def coerce_to_bytes(x:typing.Any):
    if isinstance(x,bytes):
        return x
    elif isinstance(x,str):
        return x.encode()
    else:
        raise TypeError(f'Cannot convert type {type(x).__name__} to type bytes!')
        

def https_context():
    context = ssl._create_default_https_context() #type: ignore
    # send ALPN extension to indicate HTTP/1.1 protocol
    # if DEFAULT_HTTP_VERSION == 11:  #type: ignore
    # context.set_alpn_protocols(['http/1.1'])
    # enable PHA for TLS 1.3 connections if available
    if context.post_handshake_auth is not None: #type: ignore
        context.post_handshake_auth = True
    return context


def reorder_headers(headers:typing.Collection[str]):   
    order = ['Host','User-Agent','Accept','Accept-Encoding','Connection','Content-Length','Content-Type']                                                                                                                                                        
    headers = list(headers)
    headers.sort(key = lambda x: order.index(x) if x in order else float('inf'))
    return headers
