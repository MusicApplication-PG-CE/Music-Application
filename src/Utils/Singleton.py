
class Singleton:
    def __new__(cls,*args,**kwargs):
        if not hasattr(cls,'_instance'):
            cls._instance = object.__new__(cls,*args,**kwargs)
        return cls._instance
