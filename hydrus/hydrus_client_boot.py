#!/usr/bin/env python3

# Hydrus is released under WTFPL
# You just DO WHAT THE FUCK YOU WANT TO.
# https://github.com/sirkris/WTFPL/blob/master/WTFPL.md

try:
    
    # For Russian and Polish and some other 24-hour-only systems, it is highly important this happens before Qt and mpv get their teeth into things
    # it establishes some timezone cache that requires the locale to be clean
    # I don't know if it needs to be before locale.setlocale, but I know that it works if it does
    import dateparser
    
except Exception as e:
    
    pass
    

import locale

try:
    
    locale.setlocale( locale.LC_ALL, '' )
    
except Exception as e:
    
    pass
    

import sys

try:
    
    import os
    import argparse
    
    from hydrus.core import HydrusBoot
    
    HydrusBoot.AddBaseDirToEnvPath()
    
    HydrusBoot.DoPreImportEnvWork()
    
    # initialise Qt here, important it is done early
    from hydrus.client.gui import QtInit
    
    from hydrus.core import HydrusConstants as HC
    
    HC.RUNNING_CLIENT = True
    
    from hydrus.core import HydrusData
    from hydrus.core import HydrusGlobals as HG
    from hydrus.core import HydrusLogger
    from hydrus.core import HydrusPaths
    from hydrus.core import HydrusTemp
    from hydrus.core import HydrusTime
    
    argparser = argparse.ArgumentParser( description = 'hydrus network client' )
    
    argparser.add_argument( '-d', '--db_dir', help = 'set an external db location' )
    argparser.add_argument( '--temp_dir', help = 'override the program\'s temporary directory' )
    argparser.add_argument( '--db_journal_mode', default = 'WAL', choices = [ 'WAL', 'TRUNCATE', 'PERSIST', 'MEMORY' ], help = 'change db journal mode (default=WAL)' )
    argparser.add_argument( '--db_cache_size', type = int, help = 'override SQLite cache_size per db file, in MB (default=256)' )
    argparser.add_argument( '--db_transaction_commit_period', type = int, help = 'override how often (in seconds) database changes are saved to disk (default=30,min=10)' )
    argparser.add_argument( '--db_synchronous_override', type = int, choices = range(4), help = 'override SQLite Synchronous PRAGMA (default=2)' )
    argparser.add_argument( '--no_db_temp_files', action='store_true', help = 'run db temp operations entirely in memory' )
    argparser.add_argument( '--boot_debug', action='store_true', help = 'print additional bootup information to the log' )
    argparser.add_argument( '--no_user_static_dir', action='store_true', help = 'do not allow a static dir in the db dir to override the install static dir contents' )
    argparser.add_argument( '--profile_mode', action='store_true', help = 'start the program with profile mode (db) on, capturing boot performance' )
    argparser.add_argument( '--pause_network_traffic', action='store_true', help = 'start the program with all new network traffic paused' )
    argparser.add_argument( '--win_qt_darkmode_test', action='store_true', help = 'Windows only: Try Qt\'s automatic darkmode recognition.' )
    argparser.add_argument( '--no_wal', action='store_true', help = 'OBSOLETE: run using TRUNCATE db journaling' )
    argparser.add_argument( '--db_memory_journaling', action='store_true', help = 'OBSOLETE: run using MEMORY db journaling (DANGEROUS)' )
    
    result = argparser.parse_args()
    
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
        
    
    HG.boot_with_network_traffic_paused_command_line = result.pause_network_traffic
    
    if HC.PLATFORM_WINDOWS and result.win_qt_darkmode_test:
        
        QtInit.DoWinDarkMode()
        
    
    QtInit.SetupLogging()
    
    try:
        
        from twisted.internet import reactor
        
    except Exception as e:
        
        import traceback
        
        HG.twisted_is_broke_exception = traceback.format_exc()
        HG.twisted_is_broke = True
        
    
    if result.temp_dir is not None:
        
        HydrusTemp.SetEnvTempDir( result.temp_dir )
        
    
except Exception as e:
    
    title = 'Critical boot error occurred! Details written to crash.log in either your db dir, userdir, or desktop!'
    
    import traceback
    
    error_trace = str( e ) + '\n\nFull error follows:\n\n' + traceback.format_exc()
    
    try:
        
        HydrusData.DebugPrint( title )
        HydrusData.PrintException( e )
        
    except Exception as e:
        
        print( title )
        print( 'Note for hydev: HydrusData did not import; probably a very early import (Qt?) issue!' )
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
        
        f.write( title )
        
        f.write( '\n\n' )
        
        f.write( error_trace )
        
    
    try:
        
        from qtpy import QtWidgets
        
        app = QtWidgets.QApplication( sys.argv )
        
        from hydrus.client.gui import ClientGUIDialogsMessage
        
        ClientGUIDialogsMessage.ShowCritical( None, title, str( e ) )
        ClientGUIDialogsMessage.ShowCritical( None, title, 'Here is the full error:\n\n' + traceback.format_exc() )
        
    except Exception as e:
        
        message = 'Could not start up Qt to show the error visually!'
        
        try:
            
            HydrusData.Print( message )
            
        except Exception as e:
            
            print( message )
            
        
    
    sys.exit( 1 )
    

def boot():
    
    controller = None
    
    with HydrusLogger.HydrusLogger( db_dir, 'client' ) as logger:
        
        try:
            
            HydrusData.Print( 'hydrus client started' )
            
            if not HG.twisted_is_broke:
                
                import threading
                
                # noinspection PyUnresolvedReferences
                target = reactor.run
                
                threading.Thread( target = target, name = 'twisted', kwargs = { 'installSignalHandlers' : 0 } ).start()
                
            
            from hydrus.client import ClientController
            
            controller = ClientController.Controller( db_dir, logger )
            
            controller.Run()
            
        except Exception as e:
            
            HydrusData.Print( 'hydrus client failed' )
            
            import traceback
            
            HydrusData.Print( traceback.format_exc() )
            
        finally:
            
            HG.started_shutdown = True
            HG.view_shutdown = True
            HG.model_shutdown = True
            
            if controller is not None:
                
                controller.pubimmediate( 'wake_daemons' )
                
            
            if not HG.twisted_is_broke:
                
                # noinspection PyUnresolvedReferences
                target = reactor.stop
                
                # noinspection PyUnresolvedReferences
                reactor.callFromThread( target )
                
            
            HydrusData.Print( 'hydrus client shut down' )
            
        
    
    HG.shutdown_complete = True
    
    if HG.restart:
        
        from hydrus.core.processes import HydrusProcess
        
        HydrusProcess.RestartProcess()
        
    
