import time
import typing
from . import gui
from .Utils import Async
from pygame import font
from pygame import Rect


class DownloadingStatus(gui.Space):
    text_color = (255,255,255)
    font_default = font.SysFont(None,20)
    def __init__(self,rect:Rect,pipe:Async.Pipe,no_response_timeout:float = float('inf')):
        super().__init__(rect)
        self.pipe = pipe
        self.title_text = gui.ui.Text((0,0),self.pipe.title.get(),self.text_color,font.SysFont('Arial',16))
        self.percent_bar = gui.ui.AutoSlider((0,0),(1,5),gui.ColorLayout((50,150,50),(60,60,60)))
        self.desc_text = gui.ui.Text((0,5+20+4),pipe.description.get(),self.text_color,font.SysFont("Arial",14))
        self.pipe.title.obj_change_event.register(self.title_text.setText)
        self.pipe.description.obj_change_event.register(self.desc_text.setText)
        self.pipe.percent.obj_change_event.register(self.percent_bar.setValue)
        self.last_response = time.monotonic()
        self.nrt= no_response_timeout
        @self.pipe.percent.obj_change_event.register
        def reset_time(*args):
            self.last_response = time.monotonic()

        self.retry_callback = lambda : None

        
        self.addObjects(
            gui.ui.BackgroundColor(),
            gui.ui.positioners.Aligner(
                self.title_text,
                0.5,0,0.5,0
            ),
            gui.ui.positioners.Resizer(
                self.percent_bar,
                '10','22','100%-10','~+5'
            ),
            gui.ui.positioners.Aligner(
                self.desc_text,
                0.5,0.0,0.5,0.0
            )
        )
    def setRetryCallback(self,callback:typing.Callable[[],typing.Any]):
        self.retry_callback = callback
        return self

    def update(self, input: gui.Input):
        if time.monotonic()-self.last_response > self.nrt and self.nrt != -1:
            self.nrt = -1
            print('hello')
            self.addObjects(
                gui.ui.positioners.Aligner(
                    gui.ui.AddText(
                        gui.ui.Button(
                            (0,-5),(70,50),gui.ColorScheme(200,90,90),None,self.retry_callback,
                        ),
                        'Retry',(255,255,255),self.font_default,
                    ),
                    0.5,1,0.5,1
                )
            )
        return super().update(input)
