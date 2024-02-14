import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusThreading

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
            
        
    
def DAEMONCheckImportFolders():
    
    controller = CG.client_controller
    
    if not controller.new_options.GetBoolean( 'pause_import_folders_sync' ):
        
        HG.import_folders_running = True
        
        try:
            
            import_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            for name in import_folder_names:
                
                import_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
                
                if controller.new_options.GetBoolean( 'pause_import_folders_sync' ) or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                import_folder.DoWork()
                
            
        finally:
            
            HG.import_folders_running = False
            
        
    
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
                
            
            for group_of_hashes in HydrusData.SplitIteratorIntoChunks( hashes, 8 ):
                
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
            
            for group_of_hashes in HydrusData.SplitIteratorIntoChunks( hashes, 8 ):
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, group_of_hashes )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
                controller.WriteSynchronous( 'content_updates', content_update_package )
                
                time.sleep( 0.01 )
                
            
            hashes = controller.Read( 'trash_hashes', limit = 256, minimum_age = max_age )
            
            time.sleep( 2 )
            
        
    
