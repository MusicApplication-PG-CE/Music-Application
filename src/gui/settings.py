wheel_sensitivity = 10
scroll_smoothing = 0.5

def setter(var:str):
    g = globals()
    assert var in g,'Variable must exist'
    return lambda x:g.__setitem__(var,x)