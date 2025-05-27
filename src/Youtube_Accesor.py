import os
import time 
import typing
import threading
import subprocess
from .Utils import Async

from src.utils2 import fileExists
from src.Utils import logger #type: ignore
from collections import deque
from subprocess import PIPE,DEVNULL,STDOUT


class AsyncInOutBatchDownloader:
    '''Asynchronous Youtube Downloader capable of accepting input over time and producing output over time.'''
    def __init__(self,pipe:deque[tuple[str,typing.Callable[[float,str,tuple[float,str]],typing.Any],typing.Callable[[str|None,Exception|None],typing.Any]]]):
        MAX_BATCH_SIZE = 4
        self.running = True
        def thread():
            state = 'inactive'
            while self.running:
                if state != 'inactive':
                    try:
                        url,onUpdate,onDone = state
                    except Exception:
                        state = 'inactive'
                    else:
                        _download(url,onDone,onUpdate)
                        #now that we are done with this url#
                        try:
                            state = pipe.popleft()
                        except Exception:
                            state = 'inactive'
                        #thread successfully got a url to work with 
                elif state == 'inactive':
                    time.sleep(0.5)
                    try:
                        state = pipe.popleft()
                    except Exception:
                        pass
        for i in range(MAX_BATCH_SIZE):
            threading.Thread(target=thread,daemon=True).start()
    def close(self):
        self.running = False


def downloadURLAsync(url:str,onDone:typing.Callable[[str|None,Exception|None],typing.Any],
                            onUpdate:typing.Callable[[float,str,tuple[float,str]],typing.Any]|None = None):
    threading.Thread(target = __download,args = (url,onDone,onUpdate)).start()

def __download(url:str,onDone:typing.Callable,onUpdate:typing.Callable|None):
    if not url.startswith('https://'):
        url = 'https://'+url
    try:
        cmd = subprocess.Popen(['dep/yt-dlp.exe','-x','--audio-format','vorbis',url,'--print','after_move:filepath','--progress','--embed-metadata'],stdout=PIPE,creationflags=subprocess.CREATE_NO_WINDOW,text=True)
        logger.log("created Popen for url:",url)
        output = []
        last = ''
        while (return_code :=cmd.poll()) is None:
            if cmd.stdout:  
                l = cmd.stdout.readline()
                if not l: continue
                output.append(l)
                if onUpdate:
                    if l.startswith('[download]'):
                        try:
                            l = l.removeprefix('[download]').replace('of','').replace('at','')
                            percent,size,speed = l.split()[:3]
                            percent = float(percent.split('%')[0]) / 100
                            size = str(size)
                            speed = (float(speed[:-5]),str(speed[-5:]))
                            onUpdate(percent,size,speed)
                        except:
                            pass
                last = l
            time.sleep(0.01)
        logger.log("[yt-dlp.exe return code {}]".format(url), return_code)
        if return_code != 0:
            logger.log('YT-DLP FULL OUTPUT:',*map(str.strip,output),sep='\n\t')
            return onDone(None,RuntimeError("yt-dlp unsuccessful"))
        path = last.strip()
        name = path.split('\\')[-1]
        if not fileExists(name):
            logger.log('YT-DLP file output not found, searching directory',name,end = '  -> ')
            name = list(filter(lambda x: x.endswith('.ogg'),os.listdir('.')))
            if name:
                try:
                    _,vid_id = url.rsplit('v=',1)
                except: # the url is shortened
                    _,vid_id = url.rsplit('/',1)
                for filename in name:
                    if vid_id in filename:
                        name = filename
                        break
                else:
                    name = name[0]
            else:
                name = ''
            logger.log(name)
        os.replace('./'+name,'./Database/__Music/'+name)
    except BaseException as err:
        logger.log('Exception in "Youtube_Accessor.py, <__download> :',err)
        onDone(None,err)
    else:
        onDone('./Database/__Music/'+name,None)

_download = __download #function export

def yt_dlp_version():
    version =  subprocess.run(['yt-dlp','--version'],text=True,stdout=PIPE,creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
    return tuple(map(int,version.split('.')))

def yt_dlp_upgrade():
    return subprocess.run(['yt-dlp.exe','--update-to', 'nightly','-v'],text=True,stdout=PIPE,creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()

def yt_dlp_upgrade_async():
    promise:Async.Promise[str] = Async.Promise()
    def __inner():
        popen = subprocess.Popen(['yt-dlp.exe','--update-to', 'nightly','-v'],text=True,stdout=PIPE,stderr = STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    
        while (return_code := popen.poll()) is None:
            if popen.stdout:
                line =popen.stdout.readline()
                #if popen.stdout.readable():
                #    line = popen.stdout.readline()
                if line:
                    if line.startswith('[debug] Fetching release info'): promise.percent_done.set(0.1)
                    elif line.startswith('[debug] Downloading _update_spec'): promise.percent_done.set(0.2)
                    elif line.startswith('[debug] Downloading SHA2'): promise.percent_done.set(0.3)
                    elif line.startswith('Latest version:'):promise.percent_done.set(0.4)
                    elif line.startswith('Updating to'): promise.percent_done.set(0.6)
                    elif line.startswith('[debug] Downloading yt-dlp.exe'): promise.percent_done.set(0.7)
                    elif line.startswith('Updated yt-dlp to') or line.startswith('yt-dlp is up to date'): promise.percent_done.set(1.0)
                    promise.obj.set(line.strip())
        promise.obj.set(None)
        promise.percent_done.set(1.0)
    threading.Thread(target=__inner).start()
    return promise
                
    

# def yt_dlp_date() -> tuple[int,int,int]|None:
#     try:
#         version = yt_dlp_version()
#     except:
#         return None
#     if len(version) < 3: return None
#     return version[0],version[1],version[2]


# def year_is_leap(year:int):
#     return year % 400==0 or (year % 4==0 and not year % 100==0)


# def date_to_yday(date:tuple[int,int,int]):
#     DAYS_IN_MONTH = [31, 28+year_is_leap(date[0]), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
#     days = 0
#     for i in range(date[1]-1):
#         days += DAYS_IN_MONTH[i]
#     return days + date[2]
def yt_dlp_days_since_update():
    last_modification = os.stat('./yt-dlp.exe').st_mtime
    seconds_since_update = time.time() - last_modification
    return seconds_since_update/(60*60*24)

    # yt_day = date_to_yday(yt_dlp_date() or (0,1,0))
    # day= time.localtime().tm_yday
    # return day - yt_day
    


    
    
