import sys
import stat
from .gui import Input
from pygame import Rect, Surface, transform
from .UIFramework import *

class DirectoryContent(SelectionBase):
    def __init__(self, pos: tuple[int, int], size: tuple[int, int], color_scheme: ColorScheme, info:tuple[str,Callable[[str,str],Any],str,Callable[[str,str],Any]]):
        super().__init__(pos, size, color_scheme,self.click)

        fsize = max(min(int((size[1]-8)*0.7),20),7)
        isize = min(32,(size[1]-8))
        self.oneclick = info[1]
        self.doubleclick = info[3]
        self.path = path = info[0]
        self.name = name = info[2]
        if os.path.isdir(path):
            self.image = transform.smoothscale(folder_img,(isize,isize))
        elif os.path.isfile(path):
            self.image = transform.smoothscale(file_img,(isize,isize))
        else:
            self.image = Surface((isize,isize))
            self.image.blit(getFont(FONT_NAME.ARIAL,fsize).render("?",True,'white'))
        self.last_click_time = -float('inf')
        self.ntext = Text((size[1],0),name,(255,255,255),getFont(FONT_NAME.ARIAL,fsize))
        self.ntext.rect.centery = self.rect.centery
        self.i = Image((4,(self.rect.height-32)//2+ self.yoffset) ,self.image)

    def click(self):
        t = time.monotonic()
        time_since_last_click = t- self.last_click_time
        if time_since_last_click < 0.5:
            #double click
            self.doubleclick(self.path,self.name)
        else:
            #single click
            self.oneclick(self.path,self.name)

        self.last_click_time = t

    def update(self, input: Input):
        return super().update(input)

    def draw(self, surf: Surface):
        super().draw(surf)
        self.i.rect.top = (self.rect.height-32)//2 + self.rect.top
        self.i.draw(surf)
        self.ntext.rect.centery = self.rect.centery
        self.ntext.draw(surf)


if sys.platform == 'win32':
    def isHidden(path:str,name:str): #type: ignore
        if name.startswith('.'): return True
        try:
            return os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN
        except FileNotFoundError:
            return True

else:
    def isHidden(path:str,name:str):
        return name.startswith('.')

          
class NewFolderNamePopup(OptionsBase):
    def __init__(self, l: Layer, r:Rect,cl:ColorLayout,out:Callable[[str|None],Any],font:font.Font):
        super().__init__(l, r)
        self.out = out
        self.obj = ObjectValue(None)
        self.inputbox =  self.addObject(InputBoxOneLine((0,0),r.size,cl,self.obj.set,font)) #type: ignore
        self.inputbox.active = True

    def setText(self,text:str):
        self.inputbox.cursor_position = len(text)
        self.inputbox.setText(text)

    def setRestrictChars(self,chars:set[str]|None):
        self.inputbox.setRestrictInput(chars)
        
    def setMaxChars(self,max:int):
        self.inputbox.setMaxChars(max)

    def update(self,input:Input):
        super().update(input)
        input.clearALL()
        input.clearMouse()
    def removeLayer(self):
        self.out(self.obj.get())
        return super().removeLayer()



class FileExplorer(Layer):
    @staticmethod
    def constrainRect(r:Rect,boundary:Rect):
        assert r.width <= boundary.width
        assert r.height <= boundary.height
        if r.left < boundary.left:
            r.left = boundary.left
        elif r.right > boundary.right:
            r.right = boundary.right
        if r.top < boundary.top:
            r.top = boundary.top
        elif r.bottom > boundary.bottom:
            r.bottom = boundary.bottom
        return r

    def __init__(self, l: Layer,startpath:str,path:ObjectValue[str]):
        r = Rect(0,0,500,400)
        r.center = l.rect.center
        self.layer = l
        super().__init__(r.size)

        self.path = path
        startpath = os.path.abspath(os.path.expanduser(startpath))
        self.raw_startpath = startpath
        if not os.path.isdir(startpath):
            startpath = os.path.dirname(startpath)
        self.startpath = startpath

        self.current_path = ObjectValue(startpath)
        self.view_filter:Callable[[str],bool|Any] = lambda _: True
        self.select_filter:Callable[[str],bool|Any] = lambda _:True
        self.current_out = ObjectValue('')

        self.history:list[str] = [self.startpath]
        self.future:list[str] = []
        label = Text((0,0),self.current_path.get(),(255,255,255),getFont(FONT_NAME.ARIAL,15))
        self.current_path.obj_change_event.register(label.setTextIfNeeded)
        self.view_hidden = ObjectValue(False)
        self.view_hidden.obj_change_event.register(
            lambda x: self.directory_contents.recalculateSelection()
        )

        self.directory_contents = Selection((0,0),(1,30),1,selection_cs,self.getCurDirCont,DirectoryContent)
        self.selected = Text((0,0),'',(255,255,255),getFont(FONT_NAME.ARIAL,15))
        header = self.space.cutTopSpace(25)

        header.addObjects(
            BackgroundColor(),
            Aligner(
                label,
                0,0.5,0,0.5
            ),
            Resizer(
                AddImage(
                    Button((0,0),(1,1),exit_button_cs,None,self.exitBad),
                    Exit
                ),
                '100%-50','0','100%','100%'
            )
        )
        header2 = self.space.cutTopSpace(23)
        header2.addObjects(
            BackgroundColor(),
            Aligner(
                AddImage(Button((0,0),(33,header2.rect.height-4),settings_button_cs,self.historyBack),left_arrow_img)
                ,0,0.5,0
            ),
            Aligner(
                AddImage(Button((35,0),(33,header2.rect.height-4),settings_button_cs,self.historyRedo),right_arrow_img)
                ,0,0.5,0
            ),
            Aligner(
                AddImage(Button((35+35,0),(27,header2.rect.height-4),settings_button_cs,self.gotoParentDir),transform.smoothscale(up_arrow_img,(32,21)))
                ,0,0.5,0
            ),
            Aligner(
                AddText(Switch((35+35+30,0),(header2.rect.height-4,header2.rect.height-4),
                               settings_button_cs,self.view_hidden.set),
                        "View Hidden",(255,255,255),getFont(FONT_NAME.ARIAL,header2.rect.height-6),1,0.5,0,0.5,3)
                ,0,0.5,0
            ),
            Aligner(
                AddText(Button((-10,0),(90,header2.rect.height-4),settings_button_cs,None,self.createFolder),'New Folder',(255,255,255),
                        getFont(FONT_NAME.ARIAL,header2.rect.height-6)),1,0.5,1
            )
            
        )
        bottom = self.space.cutBottomSpace(40)
        bottom.addObjects(
            BackgroundColor(),
            Resizer(self.selected,
                '5','5','100%-50-5','100%-5'
            ),
            Resizer(
                AddText(
                    Button((0,0),(50,50),ColorScheme(100,255,100),self.tryToExit),
                    'OK',(0,0,0),getFont(FONT_NAME.ARIAL,20)
                ),
                '100%-50','5','100%-5','100%-5'
            )
        )

        self.space.addObjects(
            BackgroundColor(),
            Resizer(self.directory_contents,'10','5','100%-10','100%-5'),
            KeyBoundFunction(self.exitBad,[(const.K_ESCAPE,0)])
        )

    def renameFolder(self,path:str,name:str):
        nl = self.layer.addLayer()
        if not self.hasFolderPermission(path): return False
        self.directory_contents.recalculateSelection()
        for o in self.directory_contents.selection:
            assert isinstance(o,DirectoryContent)
            if o.name == name:
                self.directory_contents.setYScroll(o.pos[1])
                r = o.ntext.rect.inflate(4,4)
                r.centery = o.rect.centery
                r.move_ip(self.directory_contents.rect.topleft)
                r.move_ip(self.rect.topleft)
                font = o.ntext.font
                r.width += 100
                break

        else:
            # raise RuntimeError("BAD BAD BAD")
            if name in os.listdir(os.path.dirname(path)):
                r = Rect(0,0,200,50)
                r.center = self.layer.rect.center
                font = getFont(FONT_NAME.ARIAL,20)
            else:
                raise ValueError("Could not find Folder")
        r.clamp_ip(nl.rect)
        new_name:ObjectValue[str|None] = ObjectValue(None)
        @new_name.obj_change_event.register
        def try_rename(new:str|None):
            if new is None: return
            try:
                os.rename(path,os.path.join(os.path.dirname(path),new))
            except PermissionError:
                pass
            else:
                self.directory_contents.recalculateSelection()
                for o in self.directory_contents.selection:
                    assert isinstance(o,DirectoryContent)
                    if o.name == new:
                        self.directory_contents.setYScroll(o.pos[1])
                        break
        nl.space.addObject(NewFolderNamePopup(nl,r,primary_layout,new_name.set,font)).setText(name)

    def createFolder(self):
        i = 0
        existing_files = set(os.listdir(self.current_path.get()))
        while i < 999:
            name = f'New Folder' 
            if i:
                name += f' ({i})'
            path = os.path.join(self.current_path.get(),name)
            if name not in existing_files:
                try:
                    os.mkdir(path)
                except PermissionError:
                    return None#False
                else:
                    break
            i+=1
        else:
            return None#False
        self.renameFolder(path,name)
        return None#True

    def tryToExit(self):
        path = self.current_out.get()
        if not path:
            print('Cannot exit with nothing selected!')
            return 
        if self.select_filter(path):
            #we *can* exit with this path
            self.exit()
        else:
            print("Cannot exit with selected option")

    def historyBack(self):
        if len(self.history) <= 1: return
        self.future.append(self.history.pop())
        self.current_path.set(self.history[-1])
        self.directory_contents.recalculateSelection()
        
    def historyRedo(self):
        if not self.future: return
        self.history.append(self.future.pop())
        self.current_path.set(self.history[-1])
        self.directory_contents.recalculateSelection()

    def historyAdd(self,path:str):
        self.history.append(path)
        if self.future:
            self.future.clear()    

    def singleClick(self,path:str,name:str):
        if not self.current_path.get(): return
        self.current_out.set(path)
        self.selected.setText(name)

    def gotoParentDir(self):
        path= os.path.dirname(self.current_path.get())
        if path == self.current_path.get():#we are at the root
            self.current_path.set('')

        else:
            if not self.hasFolderPermission(path): return
            self.current_path.set(path)
        self.historyAdd(self.current_path.get())
        self.directory_contents.recalculateSelection()
        self.directory_contents.setYScroll(0)
    
    def hasFolderPermission(self,path:str):
        try:
            os.listdir(path)
        except:
            return False
        else:
            return True
    
    def doubleClick(self,path:str,name:str):
        if not self.hasFolderPermission(path): return 
        if os.path.isdir(path): #then open the directory

            self.current_path.set(path)
            self.historyAdd(self.current_path.get())
            self.directory_contents.recalculateSelection()
            self.directory_contents.setYScroll(0)
        else:
            #try to exit with path
            self.current_out.set(path)
            if self.select_filter(path):
                #we *can* exit with this path
                self.exit()
            else:
                print("Cannot exit with selected option")
            
        pass
    def getCurDirCont(self):
        can_see_hidden = self.view_hidden.get()
        cur_path = self.current_path.get()
           
        try:
            l = os.listdir(cur_path)
        except PermissionError:
            l = []
        except FileNotFoundError:
            if not cur_path:
                for name in  os.listdrives():
                    yield(name,self.singleClick,name,self.doubleClick)
                return
            else:
                l = []
        for name in l:
            path = os.path.join(cur_path,name)
            if self.view_filter(path) and (can_see_hidden or not isHidden(path,name)):
                yield (path,self.singleClick,name,self.doubleClick)

    def onResize(self,size:tuple[int,int]):
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.width > size[0]:
            self.rect.width = size[0]
        if self.rect.height > size[1]:
            self.rect.height = size[1]
        super().onResize(size)

    def setOnlyDir(self):
        self.view_filter = os.path.isdir
        self.select_filter = os.path.isdir
        return self

    def setOnlyFiles(self):
        self.select_filter = os.path.isfile
        self.view_filter = lambda _: True
        return self

    def update(self, input: Input):
        super().update(input)
        input.clearMouse()
    
    def exit(self):
        self.path.set(self.current_out.get())
        base_layer.removeLayer(self.layer)

    def exitBad(self):
        self.path.set(self.raw_startpath)
        base_layer.removeLayer(self.layer)