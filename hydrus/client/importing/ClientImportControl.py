from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing.options import LocationImportOptions

def CheckImporterCanDoFileWorkBecausePaused( paused: bool, file_seed_cache: ClientImportFileSeeds.FileSeedCache, page_key: bytes ):
    
    if paused:
        
        raise HydrusExceptions.VetoException( 'paused' )
        
    
    if CG.client_controller.new_options.GetBoolean( 'pause_all_paged_importers' ):
        
        raise HydrusExceptions.VetoException( 'all paged importers are paused! hit network->pause to resume!' )
        
    
    if CG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' ):
        
        raise HydrusExceptions.VetoException( 'all file import queues are paused! hit network->pause to resume!' )
        
    
    work_pending = file_seed_cache.WorkToDo()
    
    if not work_pending:
        
        raise HydrusExceptions.VetoException()
        
    
    if CG.client_controller.PageClosedButNotDestroyed( page_key ):
        
        raise HydrusExceptions.VetoException( 'page is closed' )
        
    

def CheckImporterCanDoFileWorkBecausePausifyingProblem( location_import_options: LocationImportOptions.LocationImportOptions ):
    
    try:
        
        location_import_options.CheckReadyToImport()
        
    except Exception as e:
        
        raise HydrusExceptions.VetoException( str( e ) )
        
    

def CheckImporterCanDoGalleryWorkBecausePaused( paused: bool, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog | None ):
    
    if paused:
        
        raise HydrusExceptions.VetoException( 'paused' )
        
    
    if CG.client_controller.new_options.GetBoolean( 'pause_all_paged_importers' ):
        
        raise HydrusExceptions.VetoException( 'all paged importers are paused! hit network->pause to resume!' )
        
    
    if CG.client_controller.new_options.GetBoolean( 'pause_all_gallery_searches' ):
        
        raise HydrusExceptions.VetoException( 'all gallery searches are paused! hit network->pause to resume!' )
        
    
    if gallery_seed_log is not None:
        
        work_pending = gallery_seed_log.WorkToDo()
        
        if not work_pending:
            
            raise HydrusExceptions.VetoException()
            
        
    

def CheckCanDoNetworkWork( no_work_until: int, no_work_until_reason: str ):
    
    if not HydrusTime.TimeHasPassed( no_work_until ):
        
        no_work_text = '{}: {}'.format( HydrusTime.TimestampToPrettyExpires( no_work_until ), no_work_until_reason )
        
        raise HydrusExceptions.VetoException( no_work_text )
        
    
    if CG.client_controller.network_engine.IsBusy():
        
        raise HydrusExceptions.VetoException( 'network engine is too busy!' )
        
    

def CheckImporterCanDoWorkBecauseStopped( page_key: bytes ):
    
    if PageImporterShouldStopWorking( page_key ):
        
        raise HydrusExceptions.VetoException( 'page should stop working' )
        
    

def GenerateLiveStatusText( text: str, paused: bool, currently_working: bool, no_work_until: int, no_work_until_reason: str ) -> str:
    
    if not HydrusTime.TimeHasPassed( no_work_until ):
        
        return '{}: {}'.format( HydrusTime.TimestampToPrettyExpires( no_work_until ), no_work_until_reason )
        
    
    if paused and text != 'paused':
        
        if currently_working:
            
            pause_text = 'pausing'
            
        else:
            
            pause_text = 'paused'
            
        
        text = f'{pause_text} - {text}'
        
    
    return text
    

def PageImporterShouldStopWorking( page_key: bytes ):
    
    return HG.started_shutdown or not CG.client_controller.PageAlive( page_key )
    
