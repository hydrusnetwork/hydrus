#!/usr/bin/env python3

# Hydrus is released under WTFPL
# You just DO WHAT THE FUCK YOU WANT TO.
# https://github.com/sirkris/WTFPL/blob/master/WTFPL.md

try:
    
    import locale
    
    try: locale.setlocale( locale.LC_ALL, '' )
    except: pass
    
    import os
    import sys
    import time
    import traceback
    import threading
    
    from hydrus.core import HydrusBoot
    
    HydrusBoot.AddBaseDirToEnvPath()
    
    from hydrus.core import HydrusExceptions
    from hydrus.core import HydrusConstants as HC
    from hydrus.core import HydrusData
    from hydrus.core import HydrusPaths
    
    from hydrus.server import ServerController
    from twisted.internet import reactor
    from hydrus.core import HydrusGlobals as HG
    from hydrus.core import HydrusLogger
    
    #
    
    import argparse
    
    argparser = argparse.ArgumentParser( description = 'hydrus network server' )
    
    argparser.add_argument( 'action', default = 'start', nargs = '?', choices = [ 'start', 'stop', 'restart' ], help = 'either start this server (default), or stop an existing server, or both' )
    argparser.add_argument( '-d', '--db_dir', help = 'set an external db location' )
    argparser.add_argument( '--temp_dir', help = 'override the program\'s temporary directory' )
    argparser.add_argument( '--no_daemons', action='store_true', help = 'run without background daemons' )
    argparser.add_argument( '--no_wal', action='store_true', help = 'run without WAL db journaling' )
    argparser.add_argument( '--db_memory_journaling', action='store_true', help = 'run db journaling entirely in memory (DANGEROUS)' )
    argparser.add_argument( '--db_synchronous_override', help = 'override SQLite Synchronous PRAGMA (range 0-3, default=2)' )
    argparser.add_argument( '--no_db_temp_files', action='store_true', help = 'run db temp operations entirely in memory' )
    
    result = argparser.parse_args()
    
    action = result.action
    
    if result.db_dir is None:
        
        db_dir = HC.DEFAULT_DB_DIR
        
        if not HydrusPaths.DirectoryIsWritable( db_dir ) or HC.RUNNING_FROM_MACOS_APP:
            
            db_dir = HC.USERPATH_DB_DIR
            
        
    else:
        
        db_dir = result.db_dir
        
    
    db_dir = HydrusPaths.ConvertPortablePathToAbsPath( db_dir, HC.BASE_DIR )
    
    try:
        
        HydrusPaths.MakeSureDirectoryExists( db_dir )
        
    except:
        
        raise Exception( 'Could not ensure db path "{}" exists! Check the location is correct and that you have permission to write to it!'.format( db_dir ) )
        
    
    if not os.path.isdir( db_dir ):
        
        raise Exception( 'The given db path "{}" is not a directory!'.format( db_dir ) )
        
    
    if not HydrusPaths.DirectoryIsWritable( db_dir ):
        
        raise Exception( 'The given db path "{}" is not a writable-to!'.format( db_dir ) )
        
    
    HG.no_daemons = result.no_daemons
    HG.no_wal = result.no_wal
    HG.db_memory_journaling = result.db_memory_journaling
    
    if result.db_synchronous_override is not None:
        
        try:
            
            db_synchronous_override = int( result.db_synchronous_override )
            
        except ValueError:
            
            raise Exception( 'db_synchronous_override must be an integer in the range 0-3' )
            
        
        if db_synchronous_override not in range( 4 ):
            
            raise Exception( 'db_synchronous_override must be in the range 0-3' )
            
        
    
    HG.no_db_temp_files = result.no_db_temp_files
    
    if result.temp_dir is not None:
        
        HydrusPaths.SetEnvTempDir( result.temp_dir )
        
    
    #
    
    try:
        
        action = ServerController.ProcessStartingAction( db_dir, action )
        
    except HydrusExceptions.ShutdownException as e:
        
        HydrusData.Print( e )
        
        action = 'exit'
        
    
    if action == 'exit':
        
        sys.exit( 0 )
        
    
except Exception as e:
    
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
    
    import sys
    
    sys.exit( 1 )
    
controller = None

with HydrusLogger.HydrusLogger( db_dir, 'server' ) as logger:
    
    try:
        
        if action in ( 'stop', 'restart' ):
            
            ServerController.ShutdownSiblingInstance( db_dir )
            
        
        if action in ( 'start', 'restart' ):
            
            HydrusData.Print( 'Initialising controller\u2026' )
            
            threading.Thread( target = reactor.run, name = 'twisted', kwargs = { 'installSignalHandlers' : 0 } ).start()
            
            controller = ServerController.Controller( db_dir )
            
            controller.Run()
            
        
    except ( HydrusExceptions.DBCredentialsException, HydrusExceptions.ShutdownException ) as e:
        
        error = str( e )
        
        HydrusData.Print( error )
        
    except:
        
        error = traceback.format_exc()
        
        HydrusData.Print( 'Hydrus server failed' )
        
        HydrusData.Print( traceback.format_exc() )
        
    finally:
        
        HG.view_shutdown = True
        HG.model_shutdown = True
        
        if controller is not None:
            
            controller.pubimmediate( 'wake_daemons' )
            
        
        reactor.callFromThread( reactor.stop )
        
        HydrusData.Print( 'hydrus server shut down' )
        
    
