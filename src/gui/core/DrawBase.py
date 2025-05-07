import pygame

class DrawBase:
  order_in_layer = 0
  __slots__ = ()
  def draw(self,surf:pygame.Surface): ...
