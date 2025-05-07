from typing import Callable
from time import perf_counter
try:from . import logger
except: import logger #type: ignore
import typing
C = typing.TypeVar('C',bound=Callable)

if __debug__:
  def profileFunc(func:Callable):
    def wrapper(*args,**kwargs):
      start = perf_counter()
      x = func(*args,**kwargs)
      end = perf_counter()

      logger.log(func.__name__,':',end-start)
      return x
    wrapper.__name__ = func.__name__
    return wrapper
else: 
  def profileFunc(func:Callable): return func

def profile(func:Callable):
  def wrapper(*args,**kwargs):
    start = perf_counter()
    x = func(*args,**kwargs)
    end = perf_counter()
    print(func.__name__,':',end-start)
    return x
  wrapper.__name__ = func.__name__
  return wrapper

if __debug__:
    def profileGen(func:Callable[...,typing.Generator[typing.Any,typing.Any,typing.Any]]):
        def wrapper(*args,**kwargs):
            start = perf_counter()
            try:
                return (yield from func(*args,**kwargs))
            finally:
                end = perf_counter()
                print(func.__name__,':',end-start)
        wrapper.__name__ = func.__name__
        return wrapper
else:
    def profileGen(func:Callable[...,typing.Generator[typing.Any,typing.Any,typing.Any]]):
        return func
def profileAbove(a:float):
  def profile(func:Callable):
    def wrapper(*args,**kwargs):
      start = perf_counter()
      x = func(*args,**kwargs)
      end = perf_counter()
      if (end-start) > a:
        print(func.__name__,':',end-start)
      return x
    wrapper.__name__ = func.__name__
    return wrapper
  return profile

def assertNeverThrows(func:Callable):
  def _wrapper_(*args,**kwargs):
    try:
      return func(*args,**kwargs)
    except BaseException as err:
      logger.log(f"Assertion Failed! {func.__name__} raised Exception: {err}")
      raise err
  return _wrapper_


from collections import deque
class Tracer:
    class MutableString: 
        def __init__(self):
            self.s= ''
        def __iadd__(self,other:str):
            self.s += other
            return self
        def get(self): return self.s
    singleton = None
    @classmethod
    def new(cls):
        return super(cls).__new__(cls)
            
    def __new__(cls):
        if Tracer.singleton is None:
            Tracer.singleton = object.__new__(cls)
            Tracer.singleton.calls = deque()
            Tracer.singleton.running = True
        return Tracer.singleton
        
    def __init__(self):
        self.calls:deque[tuple[int,float,str]] 
        self.running:bool
        
    def clear(self):
       self.calls.clear()

    if __debug__:
        def addDebug(self,info:str):
            self.calls.append((2,perf_counter(),str(info)))
    else:
        def addDebug(self,info:str): ...
    
    if __debug__:
        def traceas(self,name:str): #type: ignore
            def trace(func:Callable):
                def wrapper(*args,**kwargs):
                    if self.running:
                        self.calls.append((0,perf_counter(),name))
                        try:
                            val = func(*args,**kwargs)
                        finally:
                            self.calls.append((1,perf_counter(),name))
                        return val
                    return func(*args,**kwargs)
                return wrapper
            return trace
    else:
        def traceas(self,name:str) -> Callable[[C],C]:
            return lambda x: x
    
    if __debug__:
        def trace(self,func:Callable):
            prefix = (func.__class__.__name__+'.') if hasattr(func,'__class__') else ''
            def wrapper(*args,**kwargs):
                if self.running:
                    self.calls.append((0,perf_counter(),prefix+func.__name__))
                    try:
                        val = func(*args,**kwargs)
                    finally:
                        self.calls.append((1,perf_counter(),prefix+func.__name__))
                    return val
                return func(*args,**kwargs)
            return wrapper
    else:
        def trace(self,func:Callable):
            return func
    def show(self):
        import pygame
        if not __debug__: return
        if not self.calls:
            return
        pygame.quit()
        pygame.init()
        screen = pygame.display.set_mode((800,400))
        font = pygame.font.SysFont('Arial',10)
        start_time = self.calls[0][1]
        left_time = self.calls[0][1]
        right_time = min(self.calls[-1][1],left_time+10)
        no_more_time = self.calls[-1][1]
        calls= list(self.calls)
        surf = pygame.Surface((800,400))
        from .fast import cache
        def lerp(a,b,t):
            return a * (1-t) + b * t
        def inverse_lerp(a,b,c):
            return (c - a)/(b-a)
        def map2(a,b,c,x,y):
            t= inverse_lerp(a,b,c)
            return lerp(x,y,t)

        @cache
        def get_color(s:str):
            h = hash(s)
            hue =  (h>>8)%360
            sat = (h&0xFF)%50+50
            val = h%50+50
            return pygame.Color.from_hsva(
               hue,sat,val
            )
            return hash(s) & 0xFF_FF_FF
        @cache
        def render_string(s:str,color:tuple[int,int,int]|str='black'):
            return font.render(s,True,color)
            
        def draw(start_index:int):
            screen.fill('white')
            while calls[start_index][0] != 0:
               start_index += 1
            assert calls[start_index][0] == 0

            stack:list[tuple[float,str,Tracer.MutableString]] = [calls[start_index][1:] + (Tracer.MutableString(),)]
            i = start_index + 1
            while i < len(calls):
                cur = calls[i]
                
                if cur[0] == 0: 
                    stack.append(cur[1:] + (Tracer.MutableString(),))
                elif cur[0] == 2:
                    print(cur[2])
                    stack[-1][2].__iadd__(cur[2])
                elif not stack:
                    print('not that bad')
                elif stack[-1][1] == cur[2]:
                    #Draw Code Here
                    height = 30
                    y = len(stack)*height
                    start_time = stack[-1][0]
                    end_time = cur[1]
                    start_x = map2(left_time,right_time,start_time,0,surf.get_width())
                    end_x = map2(left_time,right_time,end_time,0,surf.get_width())
                    d_time= (end_time-start_time)
                    t_suf = 'secs'
                    if d_time < 1:
                        d_time *= 1000
                        t_suf = 'ms'
                    if d_time < 1:
                        d_time *= 1000
                        t_suf =  'µs'
              
                    pygame.draw.rect(screen,get_color(cur[2]),(start_x,y,max(1,end_x-start_x),height))
                    if end_x-start_x > 5:
                        screen.blit(render_string(cur[2]), (start_x,y))
                        screen.blit(render_string(str(round(d_time,2))+t_suf), (start_x,y+10))
                    current_info = stack[-1][2].get()
                    if current_info:
                        if end_x-start_x > font.size(current_info)[0]:
                            screen.blit(render_string(current_info),(start_x,y+20))
                    # End Draw Code
                    stack.pop()
                    
                else:
                    print('BAD',end='\r')
                i+=1
        draw(0)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    to_move = (right_time - left_time)  * 0.05
                    if event.key == pygame.K_LEFT:
                        dt = right_time - left_time
                        left_time -= to_move
                        if left_time < start_time:
                            left_time = start_time
                        right_time = left_time + dt
                        draw(0)
                    elif event.key == pygame.K_RIGHT:
                        dt = right_time - left_time
                        right_time += to_move
                        if right_time > no_more_time:
                            right_time = no_more_time
                        left_time = right_time - dt
                        draw(0)
                    elif event.key == pygame.K_UP:
                        left_time -= to_move/2
                        if left_time < start_time:
                            left_time = start_time
                        right_time += to_move/2
                        if right_time > no_more_time:
                            right_time = no_more_time
                        draw(0)
                    elif event.key == pygame.K_DOWN:
                        left_time += to_move/2
                        right_time -= to_move/2
                        if left_time >= right_time:
                            avg = (left_time + right_time)/2
                            left_time = avg - 0.01
                            right_time = avg + 0.01
                        draw(0) 
            pygame.time.wait(30)
            pygame.display.flip()



class Stats:
  percentiles = [1,10,50,90,99]
  def __init__(self,a:list[float]) -> None:
    self.a = a
    self.srtd = sorted(a)
    self.s = sum(a)
    self.maximum = max(a)
    self.minimum = min(a)
    self.avg = self.s/len(a)
    self.median = self.srtd[len(a)//2]
    self.variance = (sum((x-self.avg)**2 for x in a)/len(a))
    self.std_dev = self.variance**0.5

  def percentile(self,percent:float):
    return self.srtd[int(len(self.a)*(percent/100))]
  
  def show(self,tabs:int=0):
    p = list(map(self.percentile,self.percentiles))
    longest = max(map(len,map(str,p)))
    print('\t'*tabs+'Max:',f'{self.maximum*1000:.2f} ms')
    print('\t'*tabs+'Min:',f'{self.minimum*1000:.2f} ms')
    print('\t'*tabs+'Avg:',f'{self.avg*1000:.2f} ms')
    print('\t'*tabs+'Median:',f'{self.median*1000:.2f} ms')
    print('\t'*tabs+'Std Dev:',f'{self.std_dev*1000:.2f} ms')
    print('\t'*tabs+'Percentiles',end = '')
    for per in self.percentiles:
      print(f'{per}%'.center(longest + 2),end = '')
    print()
    print(('\t'*tabs).ljust(tabs+len('Percentiles')),end = '')
    for per in p:
      print(f'{per}'.center(longest + 2),end = '')
    print()

  def compare(self,b:"Stats",tabs:int=0):
    p = list(map(self.percentile,self.percentiles))
    longest = max(map(len,map(str,p)))
    print('\t'*tabs+'Max:',f'{self.maximum*1000:.2f} ms', f'({(self.maximum-b.maximum)*100/b.maximum:+.1f}%)')
    print('\t'*tabs+'Min:',f'{self.minimum*1000:.2f} ms', f'({(self.minimum-b.minimum)*100/b.minimum:+.1f}%)')
    print('\t'*tabs+'Avg:',f'{self.avg*1000:.2f} ms', f'({(self.avg-b.avg)*100/b.avg:+.1f}%)')
    print('\t'*tabs+'Median:',f'{self.median*1000:.2f} ms', f'({(self.median-b.median)*100/b.median:+.1f}%)')
    print('\t'*tabs+'Std Dev:',f'{self.std_dev*1000:.2f} ms', f'({(self.std_dev-b.std_dev)*100/b.std_dev:+.1f}%)')
    print('\t'*tabs+'Percentiles',end = '')
    for per in self.percentiles:
      print(f'{per}%'.center(longest + 2),end = '')
    print()
    print(('\t'*tabs).ljust(tabs+len('Percentiles')),end = '')
    for per in p:
      print(f'{per}'.center(longest + 2),end = '')
    print()




