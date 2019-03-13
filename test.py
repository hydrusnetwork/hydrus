#!/usr/bin/env python3

import locale

try: locale.setlocale( locale.LC_ALL, '' )
except: pass

from include import HydrusConstants as HC
from include import HydrusData
from include import HydrusGlobals as HG
from include import TestController
import sys
import threading
import traceback
import wx
from twisted.internet import reactor

if __name__ == '__main__':
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        only_run = args[0]
        
    else:
        
        only_run = None
        
    
    try:
        
        threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        app = wx.App()
        
        try:
            
            # we run the tests on the wx thread atm
            # keep a window alive the whole time so the app doesn't finish its mainloop
            
            win = wx.Frame( None, title = 'Running tests...' )
            
            controller = TestController.Controller( win, only_run )
            
            def do_it():
                
                controller.Run( win )
                
            
            wx.CallAfter( do_it )
            
            app.MainLoop()
            
        except:
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
        finally:
            
            HG.view_shutdown = True
            
            controller.pubimmediate( 'wake_daemons' )
            
            HG.model_shutdown = True
            
            controller.pubimmediate( 'wake_daemons' )
            
            controller.TidyUp()
            
        
    except:
        
        HydrusData.DebugPrint( traceback.format_exc() )
        
    finally:
        
        reactor.callFromThread( reactor.stop )
        
        print( 'This was version ' + str( HC.SOFTWARE_VERSION ) )
        
        input()
        
