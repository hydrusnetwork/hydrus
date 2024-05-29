# noinspection PyUnresolvedReferences
from win32com.shell import shell, shellcon

def OpenFileProperties( path: str ):
    
    shell.ShellExecuteEx( fMask = shellcon.SEE_MASK_INVOKEIDLIST, lpFile = path, lpVerb = 'properties' )
    

def OpenFileWith( path: str ):
    
    shell.ShellExecuteEx( fMask = shellcon.SEE_MASK_INVOKEIDLIST, lpFile = path, lpVerb = 'openas' )
    
