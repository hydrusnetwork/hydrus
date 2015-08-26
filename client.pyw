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
    
    import os
    import sys
    import time
    
    from include import ClientController
    import threading
    from twisted.internet import reactor
    from include import HydrusGlobals
    
    initial_sys_stdout = sys.stdout
    initial_sys_stderr = sys.stderr
    
    with open( HC.LOGS_DIR + os.path.sep + 'client.log', 'a' ) as f:
        
        sys.stdout = f
        sys.stderr = f
        
        try:
            
            print( 'hydrus client started at ' + time.ctime() )
            
            threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
            
            app = ClientController.Controller()
            
            app.MainLoop()
            
        except:
            
            print( 'hydrus client failed at ' + time.ctime() )
            
            import traceback
            print( traceback.format_exc() )
            
        finally:
            
            HydrusGlobals.view_shutdown = True
            HydrusGlobals.model_shutdown = True
            
            app.pubimmediate( 'shutdown' )
            
            reactor.callFromThread( reactor.stop )
            
            print( 'hydrus client shut down at ' + time.ctime() )
            
        
    
    sys.stdout = initial_sys_stdout
    sys.stderr = initial_sys_stderr
    
except:
    
    import traceback
    
    print( 'Critical error occured! Details written to crash.log!' )
    
    with open( 'crash.log', 'wb' ) as f: f.write( traceback.format_exc() )
    