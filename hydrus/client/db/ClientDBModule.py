import os
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusGlobals as HG

def BlockingSafeShowMessage( message ):
    
    from qtpy import QtWidgets as QW
    
    HG.client_controller.CallBlockingToQt( HG.client_controller.app, QW.QMessageBox.warning, None, 'Warning', message )
    
class ClientDBModule( HydrusDBModule.HydrusDBModule ):
    
    def _DisplayCatastrophicError( self, text: str ):
        
        message = 'The db encountered a serious error! This is going to be written to the log as well, but here it is for a screenshot:'
        message += os.linesep * 2
        message += text
        
        HydrusData.DebugPrint( message )
        
        HG.client_controller.SafeShowCriticalMessage( 'hydrus db failed', message )
        
    
    def _PresentMissingIndicesWarningToUser( self, index_names: typing.Collection[ str ] ):
        
        index_names = sorted( index_names )
        
        HydrusData.DebugPrint( 'The "{}" database module is missing the following indices:'.format( self.name ) )
        HydrusData.DebugPrint( os.linesep.join( index_names ) )
        
        message = 'Your "{}" database module was missing {} indices. More information has been written to the log. This may or may not be a big deal, and on its own it is completely recoverable. If you do not have further problems, hydev does not need to know about it. The indices will be regenerated once you proceed--it may take some time.'.format( self.name, len( index_names ) )
        
        BlockingSafeShowMessage( message )
        
        HG.client_controller.frame_splash_status.SetText( 'recreating indices' )
        
    
    def _PresentMissingTablesWarningToUser( self, table_names: typing.Collection[ str ] ):
        
        table_names = sorted( table_names )
        
        HydrusData.DebugPrint( 'The "{}" database module is missing the following tables:'.format( self.name ) )
        HydrusData.DebugPrint( os.linesep.join( table_names ) )
        
        message = 'Your "{}" database module was missing {} tables. More information has been written to the log. This is a serious problem.'.format( self.name, len( table_names ) )
        message += os.linesep * 2
        message += 'If this is happening on the first boot after an update, it is likely a fault in the update code. If you updated many versions in one go, kill the hydrus process now and update in a smaller version increment.'
        message += os.linesep * 2
        message += 'If this is just a normal boot, you most likely encountered hard drive damage. You should check "install_dir/db/help my db is broke.txt" for background reading. Whatever happens next, you need to check that your hard drive is healthy.'
        message += os.linesep * 2
        
        if self.CAN_REPOPULATE_ALL_MISSING_DATA:
            
            recovery_info = 'This module stores copies of core data and believes it can recover everything that was lost by recomputing its cache. It may do that immediately after this dialog, or it may be delayed to a later stage of boot. Either way, the regeneration job may take some time. There may also still be miscounts or other missing/incorrect data when you boot. Please let Hydev know how you get on.'
            
        else:
            
            recovery_info = 'Unfortunately, this module manages core data and may not be able to regenerate what was lost. The missing tables can be remade, but they will likely be empty. If you have a good functional backup, you should probably kill the hydrus process now, check your drive, and ultimately rollback to that backup. If you have no backup and must continue, you will likely encounter more problems with systems related to this module. With luck it will be something small, like a suddenly empty file maintenance queue, or it could be severe, such as not being able to load any file. If you are severely damaged with no backup, Hydev will be able to help figure out what to do next. If your backup is very old and you would rather not rollback to it, Hydev may be able to figure out a way to recover some of the mising data from that and still save most of your current database.'
            
        
        message += 'If you proceed, the missing tables will be recreated. {}'.format( recovery_info )
        
        BlockingSafeShowMessage( message )
        
        HG.client_controller.frame_splash_status.SetText( 'recreating tables' )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        raise NotImplementedError()
        
    
