from typing import Literal
DEFAULT_HTTP_VERSION = 'HTTP/1.1'
METHODTYPE = Literal['GET','POST','PUT','HEAD','CONNECT','PATCH','DELETE','OPTIONS','TRACE']

scheme_to_port = {'https':443,'http':80}