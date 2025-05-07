from pygame import Surface
from .gui.ui import *
from .UIFramework import *
from .Utils.SearchYT import VideoSearch,PlaylistSearch
from .Utils.SearchItunes import ITunesSearch
from .Settings import settings
from .AppFramework import keybinds
import _thread as thread

class DownloaderLayer(Layer):
    def __init__(self, size: tuple[int, int]):
        super().__init__(size)
        backend_cs = ColorScheme(50,50,50)
        adjust_cs = ColorScheme(70,70,70,2)

        self.query = ObjectValue('')
        self._openBackendAdjustments = False
        self.backend_attributes_by_service = {
            'Youtube': {
                'Search For ':['Videos','Playlists']
            },
            'ITunes': {
                'Search By ':['None','Genre', 'Artist', 'Composer', 'Album', 'Song']
            }
        }
        self.backend_service = 'Youtube'
        self.backend_selected_attrs_by_service = {
            'Youtube': {
                'Search For ':'Videos',
            },
            'ITunes':{
                'Search By ':'None',
            }
        }

        header = self.space.cutTopSpace(40)
        header.addObjects(
            BackgroundColor((80,80,80)),
            Resizer(input_box:=InputBoxOneLine((0,0),(1,1),inputbox_cl,self.query.set,getFont(FONT_NAME.ARIAL,20)).setPlaceholder('Search...').setText(self.query.get()),
                    '5','5','100%-130','~+30'),
            Aligner(
                Dropdown((-35,5),(90,30),base_layer,62,backend_cs,list(self.backend_attributes_by_service.keys()),self.setBackendService,getFont(FONT_NAME.ARIAL,17)).setWord(self.backend_service), #type: ignore
                1,0,1,0
            ),
            Aligner(
                AddImage(
                    Button((-5,7),(26,26),adjust_cs,self.openBackendAdjustments),
                    adjust_img,offset_y=1
                ),
                1,0,1,0
            ),
            KeyBoundFunction(self.search,[(const.K_RETURN,0)]),
        )
        
        self.results_by_backend = {
            'Youtube:Videos':{
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,YTVideoUI),
                'backend':VideoSearch(removeLivestreams=True),
                'continuing':False
            },
            'Youtube:Playlists': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,YTPlaylistUI),
                'backend':PlaylistSearch(),
                'continuing':False
            },
            'ITunes:None': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,ItunesResultUI),
                'backend':ITunesSearch(),
                'continuing':False
            },
            'ITunes:Genre': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,ItunesResultUI),
                'backend':ITunesSearch(settings.iso_country_code,'genreIndex'),
                'continuing':False
            },
            'ITunes:Artist': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,ItunesResultUI),
                'backend':ITunesSearch(settings.iso_country_code,'artistTerm'),
                'continuing':False
            },
            'ITunes:Composer': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,ItunesResultUI),
                'backend':ITunesSearch(settings.iso_country_code,'composerTerm'),
                'continuing':False
            },
           'ITunes:Album': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,ItunesResultUI),
                'backend':ITunesSearch(settings.iso_country_code,'albumTerm'),
                'continuing':False
            },
           'ITunes:Song': {
                'results':ObjectValue([]),
                'selection':Selection((0,0),(0,120),1,selection_cs,None,ItunesResultUI),
                'backend':ITunesSearch(settings.iso_country_code,'songTerm'),
                'continuing':False
            }
        }
        #Initialize The dictionary above
        for backend in self.results_by_backend.values():
            sel:Selection = backend['selection']
            res:ObjectValue[list] = backend['results']
            sel.dataGetter = res.get
            res.obj_change_event.register(lambda _,sel=sel:sel.recalculateSelection())

        class Continuer:
            def __init__(self2,fullBackend:str,s:Scrollbar): #type: ignore
                self2.backend = self.results_by_backend[fullBackend]
                self2.scrollbar = s

            @property
            def b_backend(self) -> ITunesSearch|VideoSearch|PlaylistSearch:
                return self.backend['backend']

            def update(self,input:Input):#type: ignore
                if self.backend['continuing']: 
                    #here we need to basically just check if the results got back
                    if self.b_backend.canRead():
                        out:ObjectValue[list] = self.backend['results']
                        self.backend['continuing'] = False
                        try:    
                            out.get().extend(self.b_backend.getParsed())
                        except ConnectionError:
                            #retry
                            self.backend['continuing'] = False
                        else:
                            out.notify()
                elif self.b_backend.canContinue():
                    sel:Selection = self.backend['selection']
                    if (sel.fullHeight - sel.max_y - sel.y_scroll_target < 350) and self.scrollbar.getValue() > 0.9 : #if 100 px from end
                        thread.start_new_thread(asyncContinueStart,(self.b_backend,))
                        self.backend['continuing'] = True
                
        container:dict[str,list] = {}
        for key,backend in self.results_by_backend.items():
            container[key] = [
                Resizer(backend['selection'],'0','0','100%-10','100%'),
                s:=Scrollbar((0,0),(10,10),1,primary_layout).linkToDropdown(backend['selection']),
                Continuer(key,s)
            ]
        self.space.makeContainer(
            container | {
                "OfflineScreen": [
                    Aligner(
                        Text((0,0),'You\'re offline',text_color,getFont(FONT_NAME.YOUTUBE_EXTRA_BOLD,17)),
                            0.5,0.5
                    ),
                ]
            },
            self.getFullBackend(),
            [
                BackgroundColor(),
                KeyBoundFunctionConditional(lambda : not input_box.getActive(),input_box.setActive,keybinds.getActionKeybinds('Start Search'))
            ]
        )

    def getFullBackend(self):
        backend_attrs = self.backend_selected_attrs_by_service[self.backend_service]
        uri = '-'.join(backend_attrs.values())
        if uri:
            return self.backend_service + ':' + uri
        else:
            return self.backend_service

    def search(self):
        query = self.query.get()
        if not query: return 
        full_backend = self.getFullBackend()
        backend = self.results_by_backend[full_backend]
        self.space.setActive(full_backend)     
        def onGood():
            self.space.setActive(full_backend)
            backend['selection'].setYScroll(0)       
        def onError(exc:Exception):
            print(type(exc),'inside on error')
            return
            if type(exc) is ConnectionRefusedError:
                print('setting to offline')
                self.setOffline()
            else:
                asyncSearch(query,backend['results'],backend['backend'],then=onGood)
        thread.start_new_thread(asyncSearch,(query,backend['results'],backend['backend']),{'then':onGood,'onError':onError})
        
    def setBackendService(self,backend:Literal['Youtube','ITunes']):
        self.backend_service = backend
        
    def openBackendAdjustments(self):
        self._openBackendAdjustments = True

    def draw(self, surf: Surface):
        if self._openBackendAdjustments:
            self._openBackendAdjustments = False
            offset = surf.get_abs_offset()
            size = (150,100)
            if size[0] >= self.rect.width:
                size = self.rect.width,size[1]
            dropdown_font = getFont(FONT_NAME.OPEN_SANS,16)
            attributes = self.backend_attributes_by_service[self.backend_service]
            default = self.backend_selected_attrs_by_service[self.backend_service]
            max_width = max(map(lambda s: (dropdown_font.size(s)[0]),[state for attrname in attributes for state in attributes[attrname]]))
            r = Rect(0,40,max(size[0],max_width+max(map(lambda s: dropdown_font.size(s)[0],attributes.keys()))),size[1])
            r.right = self.rect.right

            new_layer = base_layer.addLayer()

            ui =  BackendAdjustmentsUI(new_layer,r.move(offset))
            y = 35
            for attrname in attributes:
                states = attributes[attrname]
                selected = default[attrname]

                a = ui.addObject(
                    Text((5,y),attrname,text_color,getFont(FONT_NAME.YOUTUBE_REGULAR,15))
                )
                ui.addObject(
                    Dropdown((a.rect.right,y),(max_width,20),base_layer,200,selection_cs,states,lambda type,attrname=attrname: self.backend_selected_attrs_by_service[self.backend_service].update({attrname:type})).setDropdownSpacing(1).setWord(selected)
                )
                y += 35

            new_layer.space.addObject(ui)
        return super().draw(surf)

    def setOffline(self):
        self.space.setActive('OfflineScreen')
def asyncSearch(query:str,out:ObjectValue[list],backend:VideoSearch|ITunesSearch|PlaylistSearch,then:Callable|None=None,onError:Callable[[Exception],typing.Any]|None=None):
    try:
        backend.beginQuery(query)
        out.set(backend.getParsed())
    except Exception as err:
        print(err,type(err))
        if onError: onError(err)
    else:
        if then: then()

def asyncContinueStart(backend:VideoSearch|ITunesSearch|PlaylistSearch):
    for i in range(3):
        try:
            backend.continueQuery()
        except ConnectionError:
            pass
        else:
            break
    else:
        raise ConnectionError
    
class BackendAdjustmentsUI(ForceFocusOptionsBase):
    pref_size:tuple = (100,100)
    def __init__(self,layer:Layer,rect:Rect):
        super().__init__(layer,rect)
        self.addObjects(
            BackgroundColor((100,100,100)),
            Aligner(
                Text((0,0),'Settings',text_color,getFont(FONT_NAME.YOUTUBE_REGULAR,20)),
                0.5,0,0.5,0
            ),
            Aligner(
                AddImage(
                    Button((-5,5),(20,20),exit_button_cs,None,self.removeLayer),
                    Exit
                ),
                1,0,1,0
            ),
            # KeyBoundFunction(self.removeLayer,const.K_ESCAPE,consume=False)
        )

    def checkToExit(self, input: Input) -> bool:
        return input.consumeKey(const.K_ESCAPE) or ((input.mb1d or input.mb3d) and not self.rect.collidepoint(input.mpos))
