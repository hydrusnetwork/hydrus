import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates

def DoMoveOrDuplicateLocalFiles( dest_service_key: bytes, action: int, media_results: collections.abc.Collection[ ClientMediaResult.MediaResult ], source_service_key: bytes | None = None ):
    
    if action in ( HC.CONTENT_UPDATE_MOVE, HC.CONTENT_UPDATE_MOVE_MERGE ) and source_service_key is None:
        
        raise Exception( 'A file move migration was called without a source file service key!' )
        
    
    for media_result in media_results:
        
        if not CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY in media_result.GetLocationsManager().GetCurrent():
            
            raise Exception( f'The file "{media_result.GetHash().hex()} is not in any local file domains, so I cannot copy!' )
            
        
    
    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_MOVE ):
        
        media_results = [ m for m in media_results if dest_service_key not in m.GetLocationsManager().GetCurrent() ]
        
    
    if len( media_results ) == 0:
        
        return
        
    
    dest_service_name = CG.client_controller.services_manager.GetName( dest_service_key )
    
    job_status = ClientThreading.JobStatus( cancellable = True )
    
    title = 'moving files' if action == HC.CONTENT_UPDATE_MOVE else 'adding files'
    
    job_status.SetStatusTitle( title )
    
    BLOCK_SIZE = 16
    
    pauser = HydrusThreading.BigJobPauser()
    
    num_to_do = len( media_results )
    
    if num_to_do > BLOCK_SIZE:
        
        CG.client_controller.pub( 'message', job_status )
        
    
    now_ms = HydrusTime.GetNowMS()
    
    for ( num_done, num_to_do, block_of_media_results ) in HydrusLists.SplitListIntoChunksRich( media_results, BLOCK_SIZE ):
        
        if job_status.IsCancelled():
            
            break
            
        
        job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) )
        job_status.SetGauge( num_done, num_to_do )
        
        content_updates = []
        undelete_hashes = set()
        
        for m in block_of_media_results:
            
            if dest_service_key in m.GetLocationsManager().GetDeleted():
                
                undelete_hashes.add( m.GetHash() )
                
            elif dest_service_key not in m.GetLocationsManager().GetCurrent():
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( m.GetFileInfoManager(), now_ms ) ) )
                
            
        
        if len( undelete_hashes ) > 0:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undelete_hashes ) )
            
        
        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( dest_service_key, content_updates ) )
        
        if action in ( HC.CONTENT_UPDATE_MOVE, HC.CONTENT_UPDATE_MOVE_MERGE ):
            
            block_of_hashes = [ m.GetHash() for m in block_of_media_results if source_service_key in m.GetLocationsManager().GetCurrent() ]
            
            content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE, block_of_hashes, reason = 'Moved to {}'.format( dest_service_name ) ) ]
            
            CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( source_service_key, content_updates ) )
            
        
        pauser.Pause()
        
    
    job_status.FinishAndDismiss()
    
