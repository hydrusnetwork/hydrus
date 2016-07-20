#!/usr/bin/env python2

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.

try:
    
    import locale
    
    try: locale.setlocale( locale.LC_ALL, '' )
    except: pass
    
    from include import HydrusConstants as HC
    from include import HydrusData
    
    import os
    import sys
    import time
    
    from include import ClientController
    import threading
    from twisted.internet import reactor
    from include import HydrusGlobals
    from include import HydrusLogger
    import traceback
    
    log_path = os.path.join( HC.DB_DIR, 'client.log' )
    
    with HydrusLogger.HydrusLogger( log_path ) as logger:
        
        try:
            
            HydrusData.Print( 'hydrus client started' )
            
            threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
            
            controller = ClientController.Controller()
            
            controller.Run()
            
        except:
            
            HydrusData.Print( 'hydrus client failed' )
            
            HydrusData.Print( traceback.format_exc() )
            
        finally:
            
            HydrusGlobals.view_shutdown = True
            HydrusGlobals.model_shutdown = True
            
            try:
                
                controller.pubimmediate( 'wake_daemons' )
                
            except:
                
                HydrusData.Print( traceback.format_exc() )
                
            
            reactor.callFromThread( reactor.stop )
            
            HydrusData.Print( 'hydrus client shut down' )
            
        
    
    HydrusGlobals.shutdown_complete = True
    
    if HydrusGlobals.restart:
        
        HydrusData.RestartProcess()
        
    
except:
    
    import traceback
    
    try:
        
        dest_path = os.path.join( HC.DB_DIR, 'crash.log' )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( traceback.format_exc() )
            
        
        print( 'Critical error occured! Details written to crash.log!' )
        
    except NameError, IOError:
        
        print( 'Critical error occured!' )
        
        traceback.print_exc()
        