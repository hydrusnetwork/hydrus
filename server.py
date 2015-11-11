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
    
    from include import ServerController
    import threading
    from twisted.internet import reactor
    from include import HydrusExceptions
    from include import HydrusGlobals
    from include import HydrusLogger
    import traceback
    
    HydrusGlobals.instance = HC.HYDRUS_SERVER
    
    action = ServerController.GetStartingAction()
    
    if action == 'help':
    
        print( 'This is the hydrus server. It accepts these commands:' )
        print( '' )
        print( 'server start - runs the server' )
        print( 'server stop - stops an existing instance of this server' )
        print( 'server restart - stops an existing instance of this server, then runs itself' )
        print( '' )
        print( 'You can also run \'server\' without arguments. Depending on what is going on, it will try to start or it will ask you if you want to stop or restart.' )
        print( 'You can also stop the running server just by hitting Ctrl+C.')
        
    else:
        
        with HydrusLogger.HydrusLogger( 'server.log' ):
            
            error_occured = False
            
            try:
                
                if action in ( 'stop', 'restart' ):
                    
                    ServerController.ShutdownSiblingInstance()
                    
                
                if action in ( 'start', 'restart' ):
                    
                    print( 'Initialising controller...' )
                    
                    threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
                    
                    controller = ServerController.Controller()
                    
                    controller.Run()
                    
                
            except HydrusExceptions.PermissionException as e:
                
                error_occured = True
                error = str( e )
                
                print( error )
                
            except:
                
                error_occured = True
                error = traceback.format_exc()
                
                print( 'Hydrus server failed' )
                
                print( traceback.format_exc() )
                
            finally:
                
                HydrusGlobals.view_shutdown = True
                HydrusGlobals.model_shutdown = True
                
                try: controller.pubimmediate( 'wake_daemons' )
                except: pass
                
                reactor.callFromThread( reactor.stop )
                
            
        
    
except HydrusExceptions.PermissionException as e:
    
    print( e )
    
except:
    
    import traceback
    
    print( 'Critical error occured! Details written to crash.log!' )
    
    with open( 'crash.log', 'wb' ) as f: f.write( traceback.format_exc() )
    