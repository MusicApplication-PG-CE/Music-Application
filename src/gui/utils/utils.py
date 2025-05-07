import math
from typing import Callable
from typing import TypeVar
T = TypeVar('T')



def expDecay(a:T,b:T,decay:float,dt:float) -> T:
  '''
  This function is useful for lerp smooth following with framerate independance
  '''
  return 	b+(a-b)*math.exp(-decay*dt) #type: ignore

def useCache(func:Callable,args:tuple,cache:dict,sentinel:object = object()):
  if (res := cache.get(args,sentinel)) is not sentinel:
    return res
  a = cache[args] = func(*args)
  return a




def useCache(func:Callable,args:tuple,cache:dict,sentinel:object = object()):
  if (res := cache.get(args,sentinel)) is not sentinel:
    return res
  a = cache[args] = func(*args)
  return a

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


def lerp(a:float,b:float,t:float):
  return a + (b-a) * t



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


def formatTime(seconds:int):
  if seconds < 0: return '-'+formatTime(-seconds)
  s = seconds % 60
  mins = seconds//60
  hours = mins//60
  mins %= 60
  if not hours:
    return f'{mins}:{s:0>2}'       
  else:
    return f'{hours}:{mins:0>2}:{s:0>2}'



# fs = [formatTime]

# tests = [-1,0,1,59,60,61,120,60*10,60*60-1,60*60,60*60+1,60*60*24]
# results:list[list[str]] = []
# pad = 0
# for test in tests:
#     r:list[str] = []
#     for f in fs:
#         r.append(f(test))
#     pad = max(pad,*map(len,r))
#     results.append(r)

# rows:list[list[str]] = [['Case',*map(lambda x:x.__name__,fs)]]
# pad = max(pad,*map(len,rows[0]))
# pad += 2
# for test,r in zip(tests,results):
#   rows.append([str(test),*r])

# for row in rows:
#   lne = ''.join([s.rjust(pad) for s in row])
#   print(lne)

