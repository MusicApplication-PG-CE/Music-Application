
def resolve_scheme(url:str) -> str|None:
    if '://' in url:
        scheme,*_ = url.split('://',1)
        return scheme
    if url.startswith('www.'):
        return 'https'

def remove_scheme(url:str) -> str:
    if '://' in url:
        scheme,*rest = url.split('://',1)
        return rest[0] if rest else ''
    else:
        return url
    
def resolve_host(url:str):
    url = remove_scheme(url)
    host,*_ = url.split('/',1)
    return host

def resolve_inner_url(url:str):
    url = remove_scheme(url)
    index = url.find('/')
    if index == -1:
        return '/'
    return url[index:]