#!/usr/bin/env python3

try:
    
    # For Russian and Polish and some other 24-hour-only systems, it is highly important this happens before Qt and mpv get their teeth into things
    # it establishes some timezone cache that requires the locale to be clean
    # I don't know if it needs to be before locale.setlocale, but I know that it works if it does
    import dateparser
    
except:
    
    pass
    

import locale

try: locale.setlocale( locale.LC_ALL, '' )
except: pass

from hydrus.client.gui import QtInit
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.core import HydrusStaticDir

HydrusStaticDir.USE_USER_STATIC_DIR = False

from hydrus.test import TestController

import sys
import threading
import traceback

from twisted.internet import reactor

def boot():
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        only_run = args[0]
        
    else:
        
        only_run = None
        
    
    try:
        
        # noinspection PyUnresolvedReferences
        target = reactor.run
        
        threading.Thread( target = target, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        QtInit.MonkeyPatchMissingMethods()
        app = QW.QApplication( sys.argv )
        
        from hydrus.client.gui import ClientGUICallAfter
        
        try:
            
            # we run the tests on the Qt thread atm
            # keep a window alive the whole time so the app doesn't finish its mainloop
            
            win = QW.QWidget( None )
            win.setWindowTitle( 'Running tests...' )
            
            controller = TestController.Controller( win, only_run )
            
            def do_it():
                
                controller.Run( win )
                
            
            controller.CallAfterQtSafe( win, do_it )
            
            app.exec_()
            
        except:
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
        finally:
            
            HG.started_shutdown = True
            
            HG.view_shutdown = True
            
            try:
                
                controller.pubimmediate( 'wake_daemons' )
                
            except:
                
                pass
                
            
            HG.model_shutdown = True
            
            try:
                
                controller.pubimmediate( 'wake_daemons' )
                
                controller.TidyUp()
                
            except:
                
                pass
                
            
        
    except:
        
        HydrusData.DebugPrint( traceback.format_exc() )
        
    finally:
        
        # noinspection PyUnresolvedReferences
        target = reactor.stop
        
        # noinspection PyUnresolvedReferences
        reactor.callFromThread( target )
        
        print( 'This was version ' + str( HC.SOFTWARE_VERSION ) )
        
        if sys.stdin.isatty():
            
            input( 'Press any key to exit.' )
            
        
        try:
            
            if controller.was_successful:
                
                sys.exit( 0 )
                
            
        except:
            
            pass
            
        
        sys.exit( 1 )
        
    
