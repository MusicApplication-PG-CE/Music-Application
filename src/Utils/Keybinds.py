import src.Utils.logger as logger


class Keybinds:
    def __init__(self,path:str):
        open(path,'a').close() #Ensure file exists
        self.path = path
        self.actions:dict[str,list[tuple[int,int]]] = {}
        self.defaults:dict[str,tuple[tuple[int,int],...]] = {}
        self.load()

    def registerAction(self,action:str):
        if action in self.actions: raise RuntimeError(f'Already Registered Action: {repr(action)}')
        self.actions[action] = []
        
    def addKeybind(self,action:str,trigger:tuple[int,int]):
        if action not in self.actions: raise RuntimeError(f'Unknown Action: {repr(action)}')
        self.actions[action].append(trigger)

    def addKeybinds(self,action:str,*triggers:tuple[int,int]):
        if action not in self.actions: raise RuntimeError(f'Unknown Action: {repr(action)}')
        self.actions[action].extend(triggers)

    def getActionKeybinds(self,action:str) -> list[tuple[int,int]]:
        assert action in self.actions, f'Unknown Action: {repr(action)}'
        return self.actions[action]
    
    def getAllActions(self) -> list[str]:
        return list(self.actions.keys())
    
    def hasAction(self,action:str):
        return action in self.actions
    
    def setDefaultAction(self,action:str,*triggers:tuple[int,int]):
        self.defaults[action] = triggers
        if self.hasAction(action): return
        self.registerAction(action)
        self.addKeybinds(action,*triggers)

    def reset(self):
        for action,binds in self.actions.items():
            binds.clear()
            binds.extend(self.defaults[action])


    def _setstate(self,serialized:str):
        self.actions.clear()
        action = None
        for line in serialized.split('\n'):
            if not line: continue
            if line.startswith('\t'):
                if action is None:
                    raise BufferError('Invalid Keybind File Syntax')
                line = line.removeprefix('\t')
                key,mods = line.split(' ')
                self.addKeybind(action,(int(key),int(mods)))
            elif line.startswith(' '):
                raise SyntaxError('Invalid Syntax')
            else:
                action = line
                self.registerAction(action)

    def _getstate(self) -> str:
        lines:list[str] = []
        for action,keybinds in self.actions.items():
            lines.append(action)
            for key,mods in keybinds:
                lines.append(f'\t{key} {mods}')
        return '\n'.join(lines)

    def load(self):
        try:
            with open(self.path,'r') as file:
                self._setstate(file.read())
        except Exception:
            with open(self.path,'w') as file: pass 
            logger.log('Corrupted Keybinds Found, Overwriting...')
            self.load()

    def save(self):
        with open(self.path,'w') as file:
            file.write(self._getstate())


