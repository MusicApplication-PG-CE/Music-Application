from array import array

def parseDuration(b:bytes):
  '''Input format should be int : int : int  or int : int
    Output: total seconds'''
  if b'.' in b:
    # print(b[b.index(b'.')+1:])
    frac,c = readInt(b,b.index(b'.')+1)
    frac = 0 if int(frac) < 0.05 else 1
    b = b[:b.index(b'.')]
  else:
    frac = 0
  nums = map(int,b.split(b":"))
  out = 0
  for num in nums:      
    out *= 60
    out += num
  return out + frac
        
def indexEnd(b:bytes,sub:bytes,start:int=0):
  return b.index(sub,start)+len(sub)

def findEnd(b:bytes,sub:bytes,start:int|None=None,end:int|None=None):
  i = b.find(sub,start,end)
  if i == -1: return -1
  return i + len(sub)

def readString(s:bytes,value:bytes,end:bytes) -> tuple[bytes,bytes]:
    # start = s.index(value)
    # end_ = s.index(end,start)
    s = s.split(value,1)[1]
    out,a = s.split(end,1)
    return out,a

def readFast(b:bytes,end:bytes,start:int=0):
  c = b.index(end,start)
  return b[start:c],c+len(end)
def readInt(b:bytes,start:int=0,_ints= set(b'0123456789')):
  c = start
  while c < len(b) and b[c] in _ints:
    c+=1
  return b[start:c],c


def parseBytes(b:bytes,start:int=0):
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
        i+=b[i]==92
        i+=1
      i+=1
    elif cur in opening:
      stack += 1
    elif cur in closing:
      stack -=1
      if stack <= 0:
        break
  return i

def bytesUntilQuote(b:bytes,start:int=0):
  assert 0<= start < len(b)
  out = array('B')
  i = start
  lb = len(b) 
  while i < lb and b[i] != 34: 
    i+=b[i]==92
    out.append(b[i])
    i+=1
  return out.tobytes(),b[i+1:]
def findEndOfQuote(b:bytes,start:int=0):
  assert 0<= start < len(b)
  out = array('B')
  i = start
  lb = len(b) 
  while i < lb and b[i] != 34: 
    i+=b[i]==92
    out.append(b[i])
    i+=1
  return out.tobytes(),i+1

def readWholeQuote(b:bytes,start:int=0):
  assert 0<= start < len(b)
  out = array('B')
  i = start
  lb = len(b) 
  while i < lb and b[i] != 34:
    i+=1
  i+=1
  while i < lb and b[i] != 34: 
    i+=b[i]==92
    out.append(b[i])
    i+=1
  return out.tobytes(),i+1
