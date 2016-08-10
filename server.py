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
    
    from include import HydrusExceptions
    from include import HydrusConstants as HC
    from include import HydrusData
    
    import os
    import sys
    import time
    
    from include import ServerController
    import threading
    from twisted.internet import reactor
    from include import HydrusGlobals
    from include import HydrusLogger
    import traceback
    
    action = ServerController.GetStartingAction()
    
    if action == 'help':
    
        HydrusData.Print( 'This is the hydrus server. It accepts these commands:' )
        HydrusData.Print( '' )
        HydrusData.Print( 'server start - runs the server' )
        HydrusData.Print( 'server stop - stops an existing instance of this server' )
        HydrusData.Print( 'server restart - stops an existing instance of this server, then runs itself' )
        HydrusData.Print( '' )
        HydrusData.Print( 'You can also run \'server\' without arguments. Depending on what is going on, it will try to start or it will ask you if you want to stop or restart.' )
        HydrusData.Print( 'You can also stop the running server just by hitting Ctrl+C.')
        
    else:
        
        log_path = os.path.join( HC.DB_DIR, 'server.log' )
        
        with HydrusLogger.HydrusLogger( log_path ) as logger:
            
            try:
                
                if action in ( 'stop', 'restart' ):
                    
                    ServerController.ShutdownSiblingInstance()
                    
                
                if action in ( 'start', 'restart' ):
                    
                    HydrusData.Print( 'Initialising controller...' )
                    
                    threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
                    
                    controller = ServerController.Controller()
                    
                    controller.Run()
                    
                
            except HydrusExceptions.PermissionException as e:
                
                error = str( e )
                
                HydrusData.Print( error )
                
            except:
                
                error = traceback.format_exc()
                
                HydrusData.Print( 'Hydrus server failed' )
                
                HydrusData.Print( traceback.format_exc() )
                
            finally:
                
                HydrusGlobals.view_shutdown = True
                HydrusGlobals.model_shutdown = True
                
                try: controller.pubimmediate( 'wake_daemons' )
                except: pass
                
                reactor.callFromThread( reactor.stop )
                
            
        
    
except HydrusExceptions.PermissionException as e:
    
    HydrusData.Print( e )
    
except:
    
    import traceback
    import os
    
    try:
        
        dest_path = os.path.join( HC.DB_DIR, 'crash.log' )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( traceback.format_exc() )
            
        
        print( 'Critical error occured! Details written to crash.log!' )
        
    except NameError, IOError:
        
        print( 'Critical error occured!' )
        
        traceback.print_exc()
        