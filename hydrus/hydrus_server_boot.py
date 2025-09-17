#!/usr/bin/env python3

# Hydrus is released under WTFPL
# You just DO WHAT THE FUCK YOU WANT TO.
# https://github.com/sirkris/WTFPL/blob/master/WTFPL.md

action = 'start'

import sys

try:
    
    import locale
    
    try: locale.setlocale( locale.LC_ALL, '' )
    except: pass
    
    import os
    import threading
    
    from hydrus.core import HydrusBoot
    
    HydrusBoot.AddBaseDirToEnvPath()
    
    HydrusBoot.DoPreImportEnvWork()
    
    from hydrus.core import HydrusConstants as HC
    
    HC.RUNNING_SERVER = True
    
    from hydrus.core import HydrusExceptions
    from hydrus.core import HydrusData
    from hydrus.core import HydrusGlobals as HG
    from hydrus.core import HydrusLogger
    from hydrus.core import HydrusPaths
    from hydrus.core import HydrusTemp
    from hydrus.core import HydrusTime
    
    from hydrus.server import ServerController
    
    from twisted.internet import reactor
    
    #
    
    import argparse
    
    argparser = argparse.ArgumentParser( description = 'hydrus network server' )
    
    argparser.add_argument( 'action', default = 'start', nargs = '?', choices = [ 'start', 'stop', 'restart' ], help = 'either start this server (default), or stop an existing server, or both' )
    argparser.add_argument( '-d', '--db_dir', help = 'set an external db location' )
    argparser.add_argument( '--temp_dir', help = 'override the program\'s temporary directory' )
    argparser.add_argument( '--db_journal_mode', default = 'WAL', choices = [ 'WAL', 'TRUNCATE', 'PERSIST', 'MEMORY' ], help = 'change db journal mode (default=WAL)' )
    argparser.add_argument( '--db_cache_size', type = int, help = 'override SQLite cache_size per db file, in MB (default=256)' )
    argparser.add_argument( '--db_transaction_commit_period', type = int, help = 'override how often (in seconds) database changes are saved to disk (default=120,min=10)' )
    argparser.add_argument( '--db_synchronous_override', type = int, choices = range(4), help = 'override SQLite Synchronous PRAGMA (default=2)' )
    argparser.add_argument( '--no_db_temp_files', action='store_true', help = 'run db temp operations entirely in memory' )
    argparser.add_argument( '--boot_debug', action='store_true', help = 'print additional bootup information to the log' )
    argparser.add_argument( '--no_user_static_dir', action='store_true', help = 'do not allow a static dir in the db dir to override the install static dir contents' )
    argparser.add_argument( '--profile_mode', action='store_true', help = 'start the server with profile mode on' )
    argparser.add_argument( '--no_wal', action='store_true', help = 'OBSOLETE: run using TRUNCATE db journaling' )
    argparser.add_argument( '--db_memory_journaling', action='store_true', help = 'OBSOLETE: run using MEMORY db journaling (DANGEROUS)' )
    
    result = argparser.parse_args()
    
    HG.server_action = result.action
    
    db_dir = HydrusPaths.FigureOutDBDir( result.db_dir )
    
    HG.db_journal_mode = result.db_journal_mode
    
    if result.no_wal:
        
        HG.db_journal_mode = 'TRUNCATE'
        
    
    if result.db_memory_journaling:
        
        HG.db_journal_mode = 'MEMORY'
        
    
    if result.db_cache_size is not None:
        
        HG.db_cache_size = result.db_cache_size
        
    else:
        
        HG.db_cache_size = 256
        
    
    if result.db_transaction_commit_period is not None:
        
        HG.db_transaction_commit_period = max( 10, result.db_transaction_commit_period )
        
    else:
        
        HG.db_transaction_commit_period = 30
        
    
    if result.db_synchronous_override is not None:
        
        HG.db_synchronous = int( result.db_synchronous_override )
        
    else:
        
        if HG.db_journal_mode == 'WAL':
            
            HG.db_synchronous = 1
            
        else:
            
            HG.db_synchronous = 2
            
        
    
    HG.no_db_temp_files = result.no_db_temp_files
    
    HG.boot_debug = result.boot_debug
    
    from hydrus.core import HydrusStaticDir
    
    HydrusStaticDir.USE_USER_STATIC_DIR = not result.no_user_static_dir
    
    if result.profile_mode:
        
        from hydrus.core import HydrusProfiling
        
        HydrusProfiling.StartProfileMode( 'db' )
        
    
    if result.temp_dir is not None:
        
        HydrusTemp.SetEnvTempDir( result.temp_dir )
        
    
except Exception as e:
    
    import traceback
    
    error_trace = traceback.format_exc()
    
    print( error_trace )
    
    if 'db_dir' in locals() and os.path.exists( db_dir ):
        
        emergency_dir = db_dir
        
    else:
        
        emergency_dir = os.path.expanduser( '~' )
        
        possible_desktop = os.path.join( emergency_dir, 'Desktop' )
        
        if os.path.exists( possible_desktop ) and os.path.isdir( possible_desktop ):
            
            emergency_dir = possible_desktop
            
        
    
    dest_path = os.path.join( emergency_dir, 'hydrus_crash.log' )
    
    with open( dest_path, 'w', encoding = 'utf-8' ) as f:
        
        f.write( error_trace )
        
    
    print( 'Critical boot error occurred! Details written to hydrus_crash.log in either db dir or user dir!' )
    
    sys.exit( 1 )
    
def boot():
    
    try:
        
        HG.server_action = ServerController.ProcessStartingAction( db_dir, HG.server_action )
        
    except HydrusExceptions.ShutdownException as e:
        
        HydrusData.Print( e )
        
        HG.server_action = 'exit'
        
    
    if HG.server_action == 'exit':
        
        sys.exit( 0 )
        
    
    controller = None
    
    with HydrusLogger.HydrusLogger( db_dir, 'server' ) as logger:
        
        try:
            
            if HG.server_action in ( 'stop', 'restart' ):
                
                ServerController.ShutdownSiblingInstance( db_dir )
                
            
            if HG.server_action in ( 'start', 'restart' ):
                
                HydrusData.Print( 'Initialising controller' + HC.UNICODE_ELLIPSIS )
                
                # noinspection PyUnresolvedReferences
                target = reactor.run
                
                threading.Thread( target = target, name = 'twisted', kwargs = { 'installSignalHandlers' : 0 } ).start()
                
                controller = ServerController.Controller( db_dir )
                
                controller.Run()
                
            
        except ( HydrusExceptions.DBCredentialsException, HydrusExceptions.ShutdownException ) as e:
            
            error = str( e )
            
            HydrusData.Print( error )
            
        except:
            
            import traceback
            
            error = traceback.format_exc()
            
            HydrusData.Print( 'Hydrus server failed' )
            
            HydrusData.Print( error )
            
        finally:
            
            HG.started_shutdown = True
            HG.view_shutdown = True
            HG.model_shutdown = True
            
            if controller is not None:
                
                controller.pubimmediate( 'wake_daemons' )
                
            
            # noinspection PyUnresolvedReferences
            target = reactor.stop
            
            # noinspection PyUnresolvedReferences
            reactor.callFromThread( target )
            
            HydrusData.Print( 'hydrus server shut down' )
            
        
    
