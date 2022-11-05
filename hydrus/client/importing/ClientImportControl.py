import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing.options import FileImportOptions

def CheckImporterCanDoFileWorkBecausePaused( paused: bool, file_seed_cache: ClientImportFileSeeds.FileSeedCache, page_key: bytes ):
    
    if paused:
        
        raise HydrusExceptions.VetoException( 'paused' )
        
    
    if HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' ):
        
        raise HydrusExceptions.VetoException( 'all file import queues are paused!' )
        
    
    work_pending = file_seed_cache.WorkToDo()
    
    if not work_pending:
        
        raise HydrusExceptions.VetoException()
        
    
    if HG.client_controller.PageClosedButNotDestroyed( page_key ):
        
        raise HydrusExceptions.VetoException( 'page is closed' )
        
    

def CheckImporterCanDoFileWorkBecausePausifyingProblem( file_import_options: FileImportOptions ):
    
    try:
        
        file_import_options.CheckReadyToImport()
        
    except Exception as e:
        
        raise HydrusExceptions.VetoException( str( e ) )
        
    

def CheckImporterCanDoGalleryWorkBecausePaused( paused: bool, gallery_seed_log: typing.Optional[ ClientImportGallerySeeds.GallerySeedLog ] ):
    
    if paused:
        
        raise HydrusExceptions.VetoException( 'paused' )
        
    
    if HG.client_controller.new_options.GetBoolean( 'pause_all_gallery_searches' ):
        
        raise HydrusExceptions.VetoException( 'all gallery searches are paused!' )
        
    
    if gallery_seed_log is not None:
        
        work_pending = gallery_seed_log.WorkToDo()
        
        if not work_pending:
            
            raise HydrusExceptions.VetoException()
            
        
    

def CheckCanDoNetworkWork( no_work_until: int, no_work_until_reason: str ):
    
    if not HydrusData.TimeHasPassed( no_work_until ):
        
        no_work_text = '{}: {}'.format( HydrusData.ConvertTimestampToPrettyExpires( no_work_until ), no_work_until_reason )
        
        raise HydrusExceptions.VetoException( no_work_text )
        
    
    if HG.client_controller.network_engine.IsBusy():
        
        raise HydrusExceptions.VetoException( 'network engine is too busy!' )
        
    

def CheckImporterCanDoWorkBecauseStopped( page_key: bytes ):
    
    if PageImporterShouldStopWorking( page_key ):
        
        raise HydrusExceptions.VetoException( 'page should stop working' )
        
    

def GenerateLiveStatusText( text: str, paused: bool, no_work_until: int, no_work_until_reason: str ) -> str:
    
    if not HydrusData.TimeHasPassed( no_work_until ):
        
        return '{}: {}'.format( HydrusData.ConvertTimestampToPrettyExpires( no_work_until ), no_work_until_reason )
        
    
    if paused and text != 'paused':
        
        if text == '':
            
            text = 'pausing'
            
        else:
            
            text = 'pausing - {}'.format( text )
            
        
    
    return text
    

def NeatenStatusText( text: str ) -> str:
    
    if len( text ) > 0:
        
        text = text.splitlines()[0]
        
    
    return text
    

def PageImporterShouldStopWorking( page_key: bytes ):
    
    return HG.started_shutdown or not HG.client_controller.PageAlive( page_key )
    
