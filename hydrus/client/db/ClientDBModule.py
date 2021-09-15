import os
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

def BlockingSafeShowMessage( message ):
    
    from qtpy import QtWidgets as QW
    
    HG.client_controller.CallBlockingToQt( HG.client_controller.app, QW.QMessageBox.warning, None, 'Warning', message )
    
class ClientDBModule( HydrusDBModule.HydrusDBModule ):
    
    def _PresentMissingIndicesWarningToUser( self, index_names ):
        
        index_names = sorted( index_names )
        
        HydrusData.DebugPrint( 'The "{}" database module is missing the following indices:'.format( self.name ) )
        HydrusData.DebugPrint( os.linesep.join( index_names ) )
        
        message = 'Your "{}" database module was missing {} indices. More information has been written to the log. This may or may not be a big deal, and on its own is completely recoverable. If you do not have further problems, hydev does not need to know about it. The indices will be regenerated once you proceed--it may take some time.'.format( self.name, len( index_names ) )
        
        BlockingSafeShowMessage( message )
        
        HG.client_controller.frame_splash_status.SetText( 'recreating indices' )
        
    
    def _PresentMissingTablesWarningToUser( self, table_names ):
        
        table_names = sorted( table_names )
        
        HydrusData.DebugPrint( 'The "{}" database module is missing the following tables:'.format( self.name ) )
        HydrusData.DebugPrint( os.linesep.join( table_names ) )
        
        message = 'Your "{}" database module was missing {} tables. More information has been written to the log. This is a serious problem and possibly due to hard drive damage. You should check "install_dir/db/help my db is broke.txt" for background reading. If you have a functional backup, kill the hydrus process now and rollback to that backup.'.format( self.name, len( table_names ) )
        message += os.linesep * 2
        message += 'Otherwise, proceed and the missing tables will be recreated. Your client should be able to boot, but full automatic recovery may not be possible and you may encounter further errors. A database maintenance task or repository processing reset may be able to fix you up once the client boots. Hydev will be able to help if you run into trouble.'
        
        BlockingSafeShowMessage( message )
        
        HG.client_controller.frame_splash_status.SetText( 'recreating tables' )
        
    
