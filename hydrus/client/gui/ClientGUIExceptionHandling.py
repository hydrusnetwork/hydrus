from qtpy import QtWidgets as QW

from hydrus.core import HydrusData

HAVE_SHOWN_PAINT_EVENT_EXCEPTION = False

def HandlePaintEventException( win: QW.QWidget, e: Exception ):
    
    global HAVE_SHOWN_PAINT_EVENT_EXCEPTION
    
    if not HAVE_SHOWN_PAINT_EVENT_EXCEPTION:
        
        HAVE_SHOWN_PAINT_EVENT_EXCEPTION = True
        
        message = 'Hey, one of your windows raised an exception during a paint event. This is never ever supposed to happen, and this last-ditch failsafe is now handling it to forestall a crash.'
        message += '\n\n'
        message += f'The name of the window is "{win}", and the exception trace will follow. Please send it to hydev! You will not see any more of these error popups this program boot, but it is probably still happening. Stuff is probably drawing bad somewhere.'
        
        HydrusData.ShowText( message )
        HydrusData.ShowException( e, do_wait = False )
        
    
