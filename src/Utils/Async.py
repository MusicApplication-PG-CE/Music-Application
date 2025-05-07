import typing
from collections import deque

from src.gui.utils.ObjectValue import ObjectValue
type Coroutine[T] = typing.Generator[typing.Any,typing.Any,T]
T = typing.TypeVar('T')

class Promise(typing.Generic[T]):
    obj:ObjectValue[T|None]
    percent_done:ObjectValue[float]
    def __init__(self) -> None:
        self.percent_done = ObjectValue(0.0)
        self.obj =  ObjectValue(None)

class Pipe:
    title:ObjectValue[str]
    description:ObjectValue[str]
    percent:ObjectValue[float]
    __slots__ = 'title','description','percent'
    def __init__(self) -> None:
        self.title = ObjectValue('')
        self.description = ObjectValue('')
        self.percent = ObjectValue(0.0)
    
    def destroy(self):
        del self.title 
        del self.description
        del self.percent

def run(coro:Coroutine[T]) -> T:
    try:
        while True:
            next(coro)
    except StopIteration as e:
        return e.value

def batch(*gens:*tuple[Coroutine[T],...]) -> tuple[T,...]:
    done = 0
    total = len(gens)
    currents:list[None|Coroutine] = list(gens) #type: ignore
    out = [None]*total
    while done < total:
        for i,gen in enumerate(currents):
            if gen is None: continue
            try:
                next(gen)
            except StopIteration as e:
                currents[i] = None
                out[i] = e.value
                done += 1
    return out #type: ignore
 
coroutines:deque[Coroutine] = deque()
def addCoroutine(coro:Coroutine):
    coroutines.append(coro)



def manageCoroutines():
    global coroutines
    if not coroutines: return
    coro = coroutines.popleft()
    try:
        next(coro)
    except StopIteration:
        pass
    else:
        coroutines.append(coro)


class AsyncContext:
    def __init__(self) -> None:
        self.coros:deque[Coroutine] = deque()

    def update(self) -> tuple[Coroutine,typing.Any]|None:
        if not self.coros: return
        coro = self.coros.popleft()
        try:
            next(coro)
        except StopIteration as e:
            return coro,e.value
        else:
            self.coros.append(coro)

    def addCoroutine(self,coro:Coroutine):
        self.coros.append(coro)

    def getNumCoros(self):
        return len(self.coros)
    
Context = AsyncContext

from time import perf_counter as _perf_counter
class TimingContext(AsyncContext):
    def __init__(self,time:float) -> None:
        super().__init__()
        self.time = time

    def updateCoro(self,coro:T) -> T:
        t_start = _perf_counter()
        while True:
            try:
                next(coro)
            except StopIteration as e:
                return e.value
            t_cur = _perf_counter()
            if t_cur >= t_start + self.time:
                yield
        