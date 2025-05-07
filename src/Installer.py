'''
The Purpose of this module is to make sure that the proper dependancies are installed
FFMPEG and YT-DLP
'''
import os
import sys
import zlib
import time
import src.Utils.Async as Async
import src.Utils.logger as logger
import src.Utils.NetLight as NetLight

from src.gui.utils.utils import lerp
from src.gui.utils.ObjectValue import ObjectValue

FFMPEG_URL = 'https://lgarciasanchez5450.github.io/static/assets/ffmpeg.lzip'
# country_codes = ['AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AW', 'AX', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ', 'BR', 'BS', 'BT', 'BV', 'BW', 'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN', 'CO', 'CR', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EE', 'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF', 'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW', 'GY', 'HK', 'HM', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN', 'IO', 'IQ', 'IR', 'IS', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG', 'MH', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC', 'NE', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST', 'SV', 'SX', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'ZA', 'ZM', 'ZW']
# TIMEZONE_URL = 'https://wttr.in/?format=%Z' # unused maybe theres some use for it but not right now

ytdlp_url_by_platform = {
    'darwin':'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos',
    'win32':'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
    'linux':'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux'
}

YT_DLP_URL = ytdlp_url_by_platform[sys.platform]

class Generator:
    __slots__ = 'gen','value'
    def __init__(self,gen):
        self.gen= gen
    
    def __iter__(self):
        self.value = yield from self.gen
        return self.value

def fetchURL(pipe:Async.Pipe,url:str,title:str = '') -> bytes:
    request = NetLight.Request.GET({
        'User-Agent':'Music-ApplicationV5',
        'Accept-Encoding':'identity',
        'Connection':'close'
    })
    pipe.title.set(title if title else 'Fetching URL')
    pipe.percent.set(0)
    pipe.description.set(url)

    url_ = NetLight.URL(url)
    sock = NetLight.makeSocket(url_)
    NetLight.sendRequest(sock,url_,request)

    gen = Generator(NetLight.waitResponseGen(sock))
    for percent in gen:
        pipe.percent.set(percent)
    response:NetLight.Response = gen.value
    assert isinstance(response,NetLight.Response)
    pipe.percent.set(1.0)
    if response.status_code in (301,302): #redirect request
        pipe.description.set('Redirecting')
        time.sleep(0.05)
        new_url = response.headers.get('Location')
        if new_url is None:
            pipe.title.set('FetchURL Error')
            pipe.description.set('Redirect URL not found')
            logger.log('Expected Location Header Not Found')
            logger.log('Headers:',response.headers)
            raise RuntimeError
        else:
            return fetchURL(pipe,new_url) #recursively try the new url redirected to
    elif response.status_code == 200:
        if response.chunked:
            pipe.description.set('Recieving Chunks')
            while d:=NetLight.waitChunkResponse(sock):
                pipe.percent.set(lerp(pipe.percent.get(),1,(1-600/(len(d)+600))**3))
                response.body += d
            pipe.percent.set(1.0)
        else:
            pipe.description.set('Recieved Payload')
        return response.body
    elif response.status_code//100 == 4: #status code is in the 400s
        pipe.title.set('Error: Status Code '+str(response.status_code))
        pipe.description.set(response.reason_phrase)
        raise RuntimeError
    else:
        raise NotImplementedError

def update_ytdlp_async(done:ObjectValue,pipe:Async.Pipe):
    '''Updates to yt-dlp to latest nightly build'''
    # calls github api with url
    # https://api.github.com/repos/yt-dlp/yt-dlp/releases/tag
    # Headers:
    #   'Accept': 'application/vnd.github+json'
    #   'User-Agent': 'yt-dlp'
    #   'X-GitHub-Api-Version': '2022-11-28'

    # Gets value of "tag_name" key in return json
    # This value if the latest version to update to

    # Make the Variable binary_name to match the file downloaded across platforms
    # MacOS -> yt-dlp_macos
    # Windows -> yt-dlp.exe
    # Linux -> yt-dlp_linux

    # Build the final URL, Should look like this:
    # https://github.com/yt-dlp/yt-dlp/releases/download/YYYY.MM.DD/{binary_name}
    *_, file_name = YT_DLP_URL.rsplit('/',1)
    def inner():
        #get latest nightly build
        pipe.percent.set(0)
        response = fetchURL(pipe,'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest','Fetching Latest Build Info')
        pipe.title.set('Got Build Info')
        _,latest_build = response.split(b'tag_name":',1)
        latest_build = latest_build[latest_build.index(b'"')+1:]
        latest_build,_ = latest_build.split(b'"',1)
        content = fetchURL(pipe,f'https://github.com/yt-dlp/yt-dlp/releases/download/{latest_build.decode()}/{file_name}','Downloading Content')
        time.sleep(0.1)
        pipe.title.set('Writing to Disk')
        with open('./dep/yt-dlp.exe','wb+') as file: #if we already are here we *NEED* to overwrite the whole file or else bad stuff happens
            while content:
                content = content[file.write(content):]
        done.set(True)
    import threading
    thread = threading.Thread(target=inner,daemon=True)
    thread.start()
    return pipe


class Dependency:
    def __init__(self,name:str):
        self.name = name

    def hasDependency(self) -> bool: ...

    def installDependency(self,pipe:Async.Pipe):
        '''
        This Function is run in a thread and should let any normal exceptions raise to the caller.
        '''

    def __repr__(self):
        return f'Dependency[{self.name}]'

class FileDependency(Dependency):
    def __init__(self,name:str,path:str):
        super().__init__(name)
        self.path = path

    def hasDependency(self) -> bool:
        path = os.path.abspath(self.path)
        print(f'Looking for {self.name} at: {(path)}')
        assert os.path.isfile(path)==os.path.isfile(self.path)
        return os.path.isfile(self.path)
    
    def replaceAtomic(self,contents:bytes):
        tmp_path = self.path+'.new'
        try:
            with open(tmp_path,'wb+') as file:
                file.write(contents)
            os.replace(tmp_path,self.path)
        except: 
            os.remove(tmp_path)
            raise

class FFMPEGDependency(FileDependency):
    def __init__(self):
        super().__init__('FFmpeg','./dep/ffmpeg.exe')

    def installDependency(self, pipe: Async.Pipe):
        compressed = fetchURL(pipe,FFMPEG_URL,'Fetching FFMPEG dependency')
        pipe.title.set('Decompressing')
        decompressed = zlib.decompress(compressed)
        pipe.description.set('')
        pipe.title.set('Installing')
        self.replaceAtomic(decompressed)

class OnlineFileDependency(FileDependency):
    def __init__(self,name:str,path:str,url:str):
        super().__init__(name,path)
        self.url = url

    def installDependency(self, pipe: Async.Pipe):
        contents = fetchURL(pipe,self.url,f'Fetching {self.name} dependency')
        self.replaceAtomic(contents)

dependencies:list[Dependency] = [
    FFMPEGDependency(),
    OnlineFileDependency('YT-DLP','./dep/yt-dlp.exe',YT_DLP_URL),
    OnlineFileDependency('Noto Sans Extended','Assets/fonts/all.ttf','https://lgarciasanchez5450.github.io/static/assets/all.ttf')
]