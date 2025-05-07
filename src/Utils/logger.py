'''
This module exports a single function called "log"
this function serves to log anything to a file
stored in \<LOG_FILE\>. This function guarantee's 
to never throw an error.
'''
LOGGING = True
TIMESTAMP = True
LOG_FILE:str = './log.txt'

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
        import time
        s = f'[{time.asctime()}] '+str(sep).join([str(a) for a in x]) + str(end)
        with open(LOG_FILE,'a+') as file:
            try:
                file.write(s)
            except Exception as err:
                file.write("Exception Occured in writing to log file!{}\n".format(map(repr,err.args)))
                import traceback
                import sys
                sys.exception
                traceback.print_stack(sys._getframe(),file=file)
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
