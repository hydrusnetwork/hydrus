import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusThreading

from hydrus.client import ClientConstants as CC

def DAEMONCheckExportFolders():
    
    controller = HG.client_controller
    
    if not controller.options[ 'pause_export_folders_sync' ]:
        
        HG.export_folders_running = True
        
        try:
            
            export_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            for name in export_folder_names:
                
                export_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, name )
                
                if controller.options[ 'pause_export_folders_sync' ] or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                export_folder.DoWork()
                
            
        finally:
            
            HG.export_folders_running = False
            
        
    
def DAEMONCheckImportFolders():
    
    controller = HG.client_controller
    
    if not controller.options[ 'pause_import_folders_sync' ]:
        
        HG.import_folders_running = True
        
        try:
            
            import_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            for name in import_folder_names:
                
                import_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
                
                if controller.options[ 'pause_import_folders_sync' ] or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                import_folder.DoWork()
                
            
        finally:
            
            HG.import_folders_running = False
            
        
    
def DAEMONMaintainTrash():
    
    controller = HG.client_controller
    
    if HC.options[ 'trash_max_size' ] is not None:
        
        max_size = HC.options[ 'trash_max_size' ] * 1048576
        
        service_info = controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
        
        while service_info[ HC.SERVICE_INFO_TOTAL_SIZE ] > max_size:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            hashes = controller.Read( 'trash_hashes', limit = 10 )
            
            if len( hashes ) == 0:
                
                return
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
            
            controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            service_info = controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
            
            time.sleep( 2 )
            
        
    
    if HC.options[ 'trash_max_age' ] is not None:
        
        max_age = HC.options[ 'trash_max_age' ] * 3600
        
        hashes = controller.Read( 'trash_hashes', limit = 10, minimum_age = max_age )
        
        while len( hashes ) > 0:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
            
            controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            hashes = controller.Read( 'trash_hashes', limit = 10, minimum_age = max_age )
            
            time.sleep( 2 )
            
        
    
