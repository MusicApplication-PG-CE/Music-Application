import os
import math
from collections import deque
from pygame import font
from pygame import key as pgkey
from pygame import constants as const
from typing import Callable, Generator, NoReturn, TypeVar, Hashable
from src.Utils.fast import cache
from src.Utils.debug import profile

T = TypeVar('T')
H = TypeVar('T',bound=Hashable)
L = TypeVar("L",list,deque)

def shuffle(a:L):
  seed = (id(a)&0xFFFF) ^ int.from_bytes(os.urandom(2))
  a_len = len(a)
  for i in range(a_len-1,0,-1):
    j = (id(a[i])^seed)%(i+1)
    a[i], a[j] = a[j], a[i]
  return a

def lerp(a,b,t):
  return a * (1-t) + b*t

def removeRedundancies(seq:list[H],*processing:Callable[[H],Hashable]) -> list[H]:
  '''Removes redundant values in sequence as long as values are hashable'''
  hashes = set()
  out = []
  for v in seq:
    hv = v 
    for p in processing:
      hv = p(hv)#type: ignore
    if hv not in hashes:
      hashes.add(hv)
      out.append(v)
  return out
    
def formatDict(d:dict,*keys,tabs=0):  
  assert isinstance(d,dict),'First argument must be a dictionary'
  keys = keys or d.keys()
  string = '\t'*tabs+'{\n'
  for key in keys:
    try:
      if not hasattr(d[key],'__str__') and not hasattr(d[key],'__repr__') and hasattr(d[key],'__dict__'):
        string +='\t'*tabs+'\t'+str(key)+': '+f'{d[key].__class__}[{formatDict(d[key].__dict__,tabs+1)}]'+'\n'  
      string +='\t'*tabs+'\t'+str(key)+': '+str(d[key])+'\n'
    except KeyError:
      string +='\t'*tabs+'\t'+str(key)+': <KeyError>\n'
  return string+'\t'*tabs+"}"

def fileExists(path:str):
  try:
    open(path).close()
    return True
  except:
    return False

def formatTime(secs:int|float):
  secs = int(secs)
  out = str(secs%60).rjust(2,'0')
  secs//=60
  while secs:
    out = f'{secs%60:0>2}' +':'+ out
    secs//=60
  if ':' not in out:
    out = '0:' + out
  return out
 
def formatTimeSpecial(timeSecs:float) -> str:
  """
  Will get an input in seconds and convert it to format "Minutes : Seconds" 
  """
  timeSecs = timeSecs.__trunc__()
  mins = timeSecs // 60
  secs = timeSecs%60
  secs = f'0{secs}' if secs < 10 else str(secs)
  return f"{mins}:{secs}"

def cacheNoRememberFalses(func):
  cached = {}
  def wrapper(*args):
    if args not in cached:
      val = func(*args)
      if not val: return val
      cached[args] = val
    return cached[args]
  wrapper.__name__ = func.__name__
  return wrapper

def foreverIter(val:T) -> Generator[T,None,NoReturn]:
  while True:
    yield val


def reprKey(key:int,mods:int = 0):
  name = pgkey.name(key,False)
  if mods == 0:
    return name
  l = []
  if mods&const.KMOD_CTRL:
    l.append('CTRL')
  if mods&const.KMOD_SHIFT:
    l.append('SHIFT')
  if mods&const.KMOD_ALT:
    l.append('ALT')
  l.append(name)
  return '+'.join(l)


  

@cache
def getCharWidth(s:str,font:font.Font):
  try:
    return  font.render(s,False,0).get_width()
  except:
    return 0

def binaryApproximate(searchFunc:Callable[[int],int],target:int,start:int,end:int):
  assert start <= end
  if start == end: return start

  mid = (end-start) //2 + start
  if mid == start:
    return min(end,start,key=lambda x: abs(target-searchFunc(x)))
  val = searchFunc(mid)
  if target > val:
    return binaryApproximate(searchFunc,target,mid,end)
  elif target < val:
    return binaryApproximate(searchFunc,target,start,mid)
  else:
    return mid

@cache
def trimText(s:str,lengthPixels:int|float,font:font.Font):
  # assert lengthPixels > 0,f'<lengthPixels> arg cannot be negative : lengthPixels={lengthPixels}'
  if lengthPixels <= 0: return ''
  string = ''
  l = 0
  for i in range(len(s)):
    c = s[i]
    if l + getCharWidth(c,font) < lengthPixels:
      l += getCharWidth(c,font)
      string += c
    else:
      while l > lengthPixels - getCharWidth('...',font) and string:
        i -= 1
        c = s[i]
        l -= getCharWidth(c,font)
        string = string[:-1]
      return string + '...'
  return s

@cache
def formatArtists(artists:tuple[str,...]) -> str:
  if not artists or artists[0] == 'None': return ''
  return ', '.join(artists)
  
def isInsideCircle(x1:int|float,y1:int|float,circlex:int|float,circley:int|float,rad:int|float) -> float:
  return (x1 - circlex)**2 + (y1 - circley)**2 < rad*rad

def separateArtists(a:str):
  artists = a.split(', ')
  if ' & ' not in artists[-1]: return artists
  artists.extend(artists.pop().split(' & ',1))
  return artists

def removeBrackets(s_:str):
  s = s_.replace('[','(').replace('{','(')
  s = s.replace(']',')').replace('}',')')  
  if s.find('(') == -1: return s_
  out = ''
  b = 0
  for c in s:
    if c == '(':
      b+=1
    elif c == ')':
      b-=1
      if b < 0: b = 0
    elif b==0: #b == 0
      out += c
  return out.strip()

def breakApartTitle(t:str,blacklist:set[str] = set()):
  parts:list[str] = []
  curr = ''
  inParen = False
  def addCurr():
    nonlocal curr
    if inParen and curr.strip():
      c = curr.strip()
      for b in blacklist:
        if b in c:
          curr = ''
          # print('stopping',c,'because of ',b)
          return

    if curr.strip():
      parts.append(curr.strip())
      curr = ''
  for c in t:
    if inParen and c in set(')]'):
      addCurr()
      inParen = False
    if inParen:
      curr += c
    else:
      if c == ' ':
        addCurr()
      else:
        curr +=c 
    if c in set('(['):
      inParen = True
      addCurr()
  addCurr()
  i = 0
  while i < len(parts):
    if len(parts[i]) == 1: pass
    elif parts[i][-1] in '([':
      # print('splitting part',part)
      parts.insert(i+1,parts[i][-1])
      parts[i] = parts[i][:-1]
      i+=1
    elif parts[i][0] in '])':
      # print('splitting part')
      start = parts[i][0]
      parts[i] = parts[i][1:]
      parts.insert(i,start)
      i+=1
    i += 1
  return parts

def removeSuperfluousAdjectivesAndFeats(s:str):
  blacklist = {
    'Official Music Video',
    'feat.',
    'feat',
    'ft.',
    'ft',
    'HD',
    'Official',
    'Music',
    'Video',
    'Audio',
    'Explicit',
    'Visualizer',
    'Official Visualizer',
    'Lyrics',
    'Lyric',
    '|'
  }

  parts = breakApartTitle(s,blacklist)
  feats = getFeats(s)
  blacklist.update(feats)
  i = 0
  # print('Cleaning YT Title:',s,'->',parts)
  while i < len(parts):
    if parts[i] in set('([') and i != len(parts)-1:
      parts[i] += parts.pop(i+1)
      i -= 1
    if parts[i] in set(')]') and i != 0:
      parts[i-1] += parts.pop(i)
      i -= 1
    i+=1
  
  return ' '.join(filter(lambda x: x not in blacklist,parts)).replace('()','').replace('[]','').strip()

def getFeats(s:str) -> list[str]:
  # i = max(s.find('feat '),s.find('feat. '),s.find('ft.'),s.find('ft '))
  l = ['feat','feat.','ft.','ft']
  acceptable_prefixes = set('( ')
  i = -1
  for sub in l:
    i2 = 0
    while (i2:=s.find(sub+' ',i2)) != -1:
      if i2 != 0: #if has a prefix
        prefix = s[i2-1]
        i2 += len(sub)+1 
        if prefix not in acceptable_prefixes: continue
      i2 += len(sub)+1 
      if i2 > i:
        i = i2
  if i == -1: return [] #no feats found
  search_buffer = s[i:].replace('\\u0026','&')
  stop_signs = set('()[]') #stop searching at any of these characters
  sep = set([',','&']) # seperate artist features by theses characters
  feats = []
  curr = ''
  for c in search_buffer:
    if c in stop_signs: break
    if c in sep:
      curr = curr.strip()
      if curr:
        feats.append(curr)
        curr = ''
    else:
      curr += c
  curr = curr.strip()
  if curr:
    feats.append(curr)
  return feats

def formatTitle(title:str,filters:list[str]):
  return f'{title} ({", ".join(map(str.capitalize,filters))})' if filters else title

def getRelevantFilters(s:str):
  filters = {
    'slow','reverb','sped'
  }
  aliases = {
    'slowed':'slow',
    'revrb':'reverb',
    'rev ': 'reverb',
    'sped up':'sped'
  }
  s = s.lower()
  for alias,value in aliases.items():
    s = s.replace(alias,value)
  parts = s.translate(str.maketrans("","","()[]")).split()
  return list(filters.intersection(parts))

def removeHashTags(s:str):
  if s.find('#') == -1 : return s
  return ' '.join(list(filter(lambda x: not x.startswith('#'),s.split())))

def cleanYTTitle(s:str) -> str:
  blacklist = {'ft.','feat.','feat','ft','HD','Music','Video','Explicit','Official','Audio','Visualizer','Lyrics','Lyric','|'}
  # test = removeSuperfluousAdjectivesAndFeats(removeHashTags(s))
  
  raw_words = s.split()
  words = [w for w in raw_words if not w.startswith('#')] #removing hashtags
  new_words:list[str] = []
  for word in words:
    if len(word) == 1: 
      new_words.append(word)
    elif word.startswith('('):
      new_words.append('(')
      new_words.append(word[1:])
    elif word.endswith(')'):
      new_words.append(word[:-1])
      new_words.append(')')
    else:
      new_words.append(word)

  new_words = [w for w in new_words if w not in blacklist]
  newest_words = []
  in_parens = False
  for word in new_words:
    if in_parens:
      if word == ')':
        in_parens = False
    else:
      if word == '(':
        in_parens = True
      else:
        newest_words.append(word)
  out = ' '.join(newest_words)
  return out

def removeUnrenderableChars(s:str):
  b = bytearray()
  it = iter(s.encode())
  while it:
    try:
      num = next(it)
    except StopIteration:
      it = None
    else:
      if num < 128: b.append(num)

  return b.decode()

def tillNextDoubleQuote(s:str):
  '''Returns a substring as s[0:e] where e is the first double quote found that is not preceeded by a backslash'''
  out = ''
  escaping = False

  for c in s:
    if escaping:
      if c == 'u':
        out += '\\'
      escaping = False
      out += c

    else:
      if c == '\\':
        escaping = True
      elif c == '"':
        return out
      else:
        out += c 
  return out.replace(r'\u0026','\u0026')#bytes(out,'utf-8').decode('unicode_escape')

def parseBytes(b:bytes):
  opening = set(b'({[')
  closing = set(b')}]')
  i = 0
  iterable = iter(b)
  stop= 0
  start = 0
  try:
    while (c:= next(iterable)):
      if c == 34:
        stop+=1
        try:
          while next(iterable) != 34: stop+=1
        except:
          break
      elif c in opening:
        i+=1
        if i == 1:
          start = stop
      elif c in closing:
        i-=1
        if i == 0: return b[start:stop+1]
      stop+=1
  except StopIteration:
    pass
  return b[start:stop]


def parseBytes2(b:bytes,start:int=0):
  assert 0<= start < len(b)
  opening = set(b'({[')
  closing = set(b')}]')  
  stack = 0
  i = start
  lb = len(b)

  while i < lb:
    cur = b[i]
    i+=1
    if cur == 34:
      while i < lb and b[i] != 34: 
        i+=b[i]==92 # 92 = '\'
        i+=1
      i+=1
    elif cur in opening:
      stack += 1
    elif cur in closing:
      stack -=1
      if stack <= 0:
        break
  return b[start:i]

def parseData(data_:str):    
  sanitizeTable = str.maketrans("{[}]",'(())')
  data = data_.translate(sanitizeTable)
  if data.find('(') == -1: return ''
  i = 0
  start = data.find('(')
  inStr = False
  len = 0
  for c in data[start:]:
    len += 1
    if c == '"':
      inStr = not inStr
    if inStr:continue
    if c == '(':
      i+=1
    elif c == ')':
      i-=1
      if i==0:
        return data_[start:start+len]
  return data_[start:]

def formatTime2(seconds:int):
  s = seconds % 60
  mins = seconds//60
  hours = mins//60
  mins %= 60
  if not hours:
    return f'{mins}:{s:0>2}'       
  else:
    return f'{hours}:{mins:0>2}:{s:0>2}'


APPLICATION_PATH = './'
MUSIC_PATH = './Database/__Music/'

