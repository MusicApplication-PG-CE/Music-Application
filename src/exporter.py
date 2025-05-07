import typing
import os
from src.Database.MusicDatabase import Song
import subprocess
from subprocess import STDOUT,PIPE,DEVNULL, CREATE_NO_WINDOW
import random
from src.Utils import logger #type: ignore
FormatTypes = typing.Literal['ogg','mp3','wav','aac']
formats:tuple[FormatTypes,...] = ('ogg','mp3','wav','aac')
BATCH_SIZE = 20 
def exportAsync(s:set[Song],format:FormatTypes,folder:str):
    '''Export All Songs in set <s> to directory <folder> in format <format>
    Returns: True -> Success
     False -> Some/All Songs could not be exported'''
    songs_num = len(s)
    if not(os.path.exists(folder) and os.path.isdir(folder)):
        raise ValueError("Incorrect Path")
    running:list[tuple[subprocess.Popen[str],Song]] = []
    added_namespace:list[str] = []
    s = s.copy()
    failed:list[Song] = []
    yield 'Initialized'
    count = 0

    while s or running:
        while len(running) < BATCH_SIZE and s:
            song = s.pop()
            cnames = set(map(lambda x: x.removesuffix('.'+format),os.listdir())).union(added_namespace)
            i = 0

            while True:
                name = song.name 
                if i: name += f' {i}'
                i+=1
                if name not in cnames: break
            cnames.add(name)
            # print('Exporting:',song.name,'as ->',name)
            command = ['ffmpeg', '-i', f'Database/__Music/{song._fileName}']
            command.extend(('-map_metadata','0'))
            command.extend(('-map_metadata','0:s:0'))
            command.extend(('-af','silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-50dB'))
            command.append('-vn')
            command.append(f'{os.path.join(folder,name)}.{format}')
            added_namespace.append(name)
            process = subprocess.Popen(command,
                                       stdout=DEVNULL,
                                       creationflags=CREATE_NO_WINDOW,text=True)
            running.append((process,song))
            yield f"Exporting for Song: {song.name}"
        # in here the invariants are: len(running) <= 5
        for _t in running.copy():
            process,song=_t
            if (ret_code := process.poll()) is not None:                   
                if ret_code != 0:
                    failed.append(song)
                    yield f"Song {song.name} Failed to Export"
                else:
                    yield f'Song {song.name} Successfully Exported'
                running.remove(_t)
                count += 1
        yield count / songs_num
    if not failed:
        logger.log("Exporting Songs Success")
    else:
        names = map(lambda x: (x.name,x._fileName),failed)
        logger.log(f"Exporting Songs Failure: {len(failed)} Failed Exports out of {songs_num} Total")
        logger.log("Failed Songs:")
        for n in names:
            logger.log(f'\t{n[0]}: {n[1]}')
    return bool(not failed)

def export(s:set[Song],format:FormatTypes,folder:str,dbg:bool=__debug__):   
    gen = exportAsync(s,format,folder)
    while True:
        try:
            d = next(gen)
            if dbg and d:
                print(d)
        except StopIteration as err:
            ret = err.value
            break
    return ret
