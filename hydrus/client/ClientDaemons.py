import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime

from hydrus.client.metadata import ClientContentUpdates

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG

def DAEMONCheckExportFolders():
    
    controller = CG.client_controller
    
    if not controller.new_options.GetBoolean( 'pause_export_folders_sync' ):
        
        HG.export_folders_running = True
        
        try:
            
            export_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            for name in export_folder_names:
                
                export_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, name )
                
                if controller.new_options.GetBoolean( 'pause_export_folders_sync' ) or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                export_folder.DoWork()
                
            
        finally:
            
            HG.export_folders_running = False
            
        
    

def DAEMONMaintainTrash():
    
    # TODO: Looking at it, this whole thing is whack
    # rewrite it to be a database command that returns 'more work to do' and then just spam it until done
    
    controller = CG.client_controller
    
    if HC.options[ 'trash_max_size' ] is not None:
        
        max_size = HC.options[ 'trash_max_size' ] * 1048576
        
        service_info = controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
        
        while service_info[ HC.SERVICE_INFO_TOTAL_SIZE ] > max_size:
            
            hashes = controller.Read( 'trash_hashes', limit = 256 )
            
            if len( hashes ) == 0:
                
                return
                
            
            for group_of_hashes in HydrusLists.SplitIteratorIntoChunks( hashes, 8 ):
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, group_of_hashes )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
                controller.WriteSynchronous( 'content_updates', content_update_package )
                
                time.sleep( 0.01 )
                
                service_info = controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
                
                if service_info[ HC.SERVICE_INFO_TOTAL_SIZE ] <= max_size:
                    
                    break
                    
                
            
            time.sleep( 2 )
            
        
    
    if HC.options[ 'trash_max_age' ] is not None:
        
        max_age = HC.options[ 'trash_max_age' ] * 3600
        
        hashes = controller.Read( 'trash_hashes', limit = 256, minimum_age = max_age )
        
        while len( hashes ) > 0:
            
            for group_of_hashes in HydrusLists.SplitIteratorIntoChunks( hashes, 8 ):
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, group_of_hashes )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
                controller.WriteSynchronous( 'content_updates', content_update_package )
                
                time.sleep( 0.01 )
                
            
            hashes = controller.Read( 'trash_hashes', limit = 256, minimum_age = max_age )
            
            time.sleep( 2 )
            
        
    

class ManagerWithMainLoop( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller", pre_loop_wait_time: int ):
        
        self._controller = controller
        
        self._pre_loop_wait_time = pre_loop_wait_time
        
        self._lock = threading.Lock()
        
        self._wake_event = threading.Event()
        self._shutdown = False
        self._mainloop_is_finished = False
        self._serious_error_encountered = False
        
        self._controller.sub( self, 'Shutdown', 'shutdown' )
        self._controller.sub( self, 'Wake', 'wake_daemons' )
        
    
    def __str__( self ):
        
        return f'MainLoop: {self.GetName()}'
        
    
    def _CheckShutdown( self ):
        
        if HydrusThreading.IsThreadShuttingDown() or self._shutdown or self._serious_error_encountered:
            
            raise HydrusExceptions.ShutdownException()
            
        
    
    def _DoMainLoop( self ):
        
        # temporary method for while I harmonise the different mainloops into this class
        
        raise NotImplementedError()
        
    
    def DoPreMainLoopWait( self ):
        
        with self._lock:
            
            time_to_start = HydrusTime.GetNowFloat() + self._pre_loop_wait_time
            
        
        while not HydrusTime.TimeHasPassedFloat( time_to_start ):
            
            with self._lock:
                
                self._CheckShutdown()
                
            
            self._wake_event.wait( 1 )
            
            if self._wake_event.is_set():
                
                break
                
            
        
    
    def GetName( self ) -> str:
        
        raise NotImplementedError()
        
    
    def MainLoop( self ):
        
        try:
            
            self.DoPreMainLoopWait()
            
            self._DoMainLoop()
            
            # we want to push towards:
            # have work to do?
            # can work?
            # still work to do = do work()
            # if shutting down, dump out
            # get a wait period( still work to do )
            # do a wait
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        finally:
            
            self._mainloop_is_finished = True
            
        
    
    def IsShutdown( self ):
        
        return self._mainloop_is_finished
        
    
    def Shutdown( self ):
        
        with self._lock:
            
            self._shutdown = True
            
        
        self.Wake()
        
    
    def Start( self ):
        
        self._controller.CallToThreadLongRunning( self.MainLoop )
        
    
    def Wake( self ):
        
        self._wake_event.set()
        
    
