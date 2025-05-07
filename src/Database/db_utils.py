import json
from typing import Any,Literal
import os
MetadataKey = Literal["File Name","Name","Size","Item type","Date modified","Date created","Date accessed","Rating","Length","Bit rate","File extension","Language","Album Name","Artists"]
PlaylistKey = Literal["Name","Description","Song File Names"]
null_metadata:dict[MetadataKey,Any] = {
    "File Name": "",
    "Name": "No Song",
    "Size": 0,
    "Item type": "N/A",
    "Date modified": 0,
    "Date created": 0,
    "Date accessed": 0,
    "Rating": "N/A",
    "Length": 1,
    "Bit rate": 0,
    "File extension": "N/A",
    "Language": "N/A",
    "Album Name": "N/A",
    "Artists": ["None"]
  }
def cache(func):
    class Wrapper:
        def __init__(self) -> None:
            self.cache = {}
            self.func = func
        def clearCache(self):
            self.cache.clear()
        def __call__(self,*args):
            if args not in self.cache:
                self.cache[args] = func(*args)
            return self.cache[args]    
        def noCache(self,*args):
            return func(*args)
    return Wrapper()

@cache
def getSongMetadata(fileName:str) -> dict[MetadataKey,Any]:
    with open('key.json','r') as file:
        for data in json.load(file):
            if data['File Name'] == fileName:
                return data#type: ignore
        return null_metadata

def getAllSongs(path='./Database/key.json') -> list[dict[MetadataKey,Any]]:
    with open(path,'r') as file:
        return json.load(file)

def getAllPlaylists(path='./Database/playlists.json') -> list[dict[PlaylistKey,Any]]:
    with open(path,'r') as file:
        return json.load(file)
    
def saveAllSongs(songs:list[dict[MetadataKey,Any]],path='./Database/key.json'):
    with open(path,'w') as file:
        return json.dump(songs,file,indent=2)
    
def saveAllPlaylists(playlists:list,path='./Database/playlists.json'):
    with open(path,'w') as file:
        json.dump(playlists,file,indent=2)

def onlyConsonants(string:str):
    return ''.join((c for c in string if c not in {'a','e','i','o','u'}))

def onlyVowels(string:str):
    return ''.join((c for c in string if c in {'a','e','i','o','u'}))

def getWords(string:str):
    return (word for word in string.split() if word.isalnum())

def deleteSongAudio(songFileName:str):
    os.remove("./Database/__Music/"+songFileName)


_translation_table = str.maketrans('-_','  ','(),./`~=+[]{}<>\'";:|')
def sanitizeName(string:str) -> str:
    return string.strip().translate(_translation_table).casefold().replace('&','and')

