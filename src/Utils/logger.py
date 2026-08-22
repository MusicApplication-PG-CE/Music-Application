'''
This module exports a single function called "log"
this function serves to log anything to a file
stored in \<LOG_FILE\>. This function guarantee's 
to never throw an error.
'''
LOGGING = True
TIMESTAMP = True
LOG_FILE:str = './log.txt'

def _toString(obj:object) -> str:
    try:
        return str(obj)
    except UnicodeError:
        try:
            return bytes.decode(obj,'utf-8','ignore')
        except:
            return '<CAN_NOT_DECODE>'
    except: 
        return f'<ERROR>'
__all__ = [
    'log'
]



if LOGGING and not TIMESTAMP:
    def log(*x:object,sep:str = ' ',end:str = '\n'):
        s = str(sep).join([str(a) for a in x]) + str(end)
        with open(LOG_FILE,'a+') as file:
            try:
                file.write(s)
            except:
                file.write("Exception Occured in writing to log file!\n")
                import traceback
                import sys
                traceback.print_stack(sys._getframe(),file=file)

elif LOGGING and TIMESTAMP:
    def log(*x:object,sep:str = ' ',end:str = '\n'):
        try:
            import time
            s = f'[{time.asctime()}]'+_toString(sep).join(list(map(_toString,x))) + _toString(end)
            with open(LOG_FILE,'a+') as file:
                try:
                    file.write(s)
                except Exception as err:
                    try:
                        file.write(f"Exception Occured in writing to log file!{[repr(arg) for arg in err.args]}\n")
                        import traceback
                        import sys
                        traceback.print_stack(sys._getframe(),file=file)
                    except:
                        file.write(f"Unknown Exception Occured in logging to file.\n")
        except BaseException as err:
            print('Exception in Writing to log file.',err)
            raise err
else:
    log = print

def dump(filepath:str,content:bytes):
    try:
        with open(filepath,'wb+') as file:
            file.write(content)
        return True
    except:
        log(f'Unable to content (len={len(content)}) to file {filepath}')
    return False


