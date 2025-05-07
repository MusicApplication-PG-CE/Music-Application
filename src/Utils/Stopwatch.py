from typing import Callable
import time
class Stopwatch:
  def __init__(self,function:Callable[[],float] = time.time):
    self.startTime = None
    self.extraTime = 0.0
    self.paused = False
    self.measurement = function

  def running(self):
    return self.startTime
    
  def start(self):
    self.startTime = self.measurement()

  def stop(self):
    time = self.timeElapsed()
    self.paused = 0.0
    self.startTime = None
    self.extraTime = 0.0
    return time

  def timeElapsed(self):
    if not self.startTime: return 0.0
    if not self.paused:
      return self.measurement() - self.startTime + self.extraTime
    else: 
      return self.extraTime
    
  def setTime(self,newVal:float):
    if not self.paused:
      self.startTime = self.measurement() - newVal
      self.extraTime = 0.0
    elif self.paused:
      self.extraTime = newVal

  def pause(self):
    if not self.startTime: return
    if not self.paused:
      self.extraTime += self.measurement() - self.startTime
      self.paused = True

  def unpause(self):
    if self.paused:
      self.startTime = self.measurement()
      self.paused = False
  
  def reset(self):
    self.startTime, self.extraTime = self.measurement(), 0.0
