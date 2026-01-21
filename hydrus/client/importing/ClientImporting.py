import random

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.parsing import ClientParsingResults

CHECKER_STATUS_OK = 0
CHECKER_STATUS_DEAD = 1
CHECKER_STATUS_404 = 2

DOWNLOADER_SIMPLE_STATUS_DONE = 0
DOWNLOADER_SIMPLE_STATUS_WORKING = 1
DOWNLOADER_SIMPLE_STATUS_PENDING = 2
DOWNLOADER_SIMPLE_STATUS_PAUSED = 3
DOWNLOADER_SIMPLE_STATUS_DEFERRED = 4
DOWNLOADER_SIMPLE_STATUS_PAUSING = 5

downloader_enum_sort_lookup = {
    DOWNLOADER_SIMPLE_STATUS_DONE : 0,
    DOWNLOADER_SIMPLE_STATUS_WORKING : 1,
    DOWNLOADER_SIMPLE_STATUS_PENDING : 2,
    DOWNLOADER_SIMPLE_STATUS_DEFERRED : 3,
    DOWNLOADER_SIMPLE_STATUS_PAUSING : 5,
    DOWNLOADER_SIMPLE_STATUS_PAUSED : 6
}

DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME = 0.1

REPEATING_JOB_TYPICAL_PERIOD = 30.0

def ConvertParsedPostsToFileSeeds( parsed_posts: list[ ClientParsingResults.ParsedPost ], source_url: str, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
    
    file_seeds = []
    
    seen_urls = set()
    
    for parsed_post in parsed_posts:
        
        parsed_urls = parsed_post.GetURLs( ( HC.URL_TYPE_DESIRED, ), only_get_top_priority = True )
        
        parsed_urls = [ url for url in parsed_urls if url not in seen_urls ]
        
        seen_urls.update( parsed_urls )
        
        for url in parsed_urls:
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.SetReferralURL( source_url )
            
            file_seed.AddParsedPost( parsed_post, file_import_options )
            
            file_seeds.append( file_seed )
            
        
    
    return file_seeds
    

def GenerateMultiplePopupNetworkJobPresentationContextFactory( job_status ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def enter_call():
            
            job_status.SetNetworkJob( network_job )
            
        
        def exit_call():
            
            job_status.DeleteNetworkJob()
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
def GenerateSinglePopupNetworkJobPresentationContextFactory( job_status ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def enter_call():
            
            job_status.SetNetworkJob( network_job )
            
        
        def exit_call():
            
            job_status.DeleteNetworkJob()
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
def GetRepeatingJobInitialDelay():
    
    return 0.5 + ( random.random() * 0.5 )
    

def PublishPresentationHashes( publishing_label: str, hashes: list[ bytes ], publish_to_popup_button: bool, publish_files_to_page: bool ):
    
    if publish_to_popup_button:
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetVariable( 'attached_files_mergable', True )
        job_status.SetFiles( list( hashes ), publishing_label )
        
        job_status.Finish() # important to later make it auto-dismiss on all files disappearing
        
        CG.client_controller.pub( 'message', job_status )
        
    
    if publish_files_to_page:
        
        CG.client_controller.pub( 'imported_files_to_page', list( hashes ), publishing_label )
        
    

def THREADDownloadURL( job_status, url, url_string ):
    
    job_status.SetStatusTitle( url_string )
    job_status.SetStatusText( 'initialising' )
    
    #
    
    file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
    file_import_options.SetIsDefault( True )
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJob( *args, **kwargs )
        
        network_job.OverrideBandwidth( 30 )
        
        return network_job
        
    
    def status_hook( text ):
        
        job_status.SetStatusText( HydrusText.GetFirstLine( text ) )
        
    
    network_job_presentation_context_factory = GenerateSinglePopupNetworkJobPresentationContextFactory( job_status )
    
    file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
    
    #
    
    try:
        
        file_seed.DownloadAndImportRawFile( url, file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD, network_job_factory, network_job_presentation_context_factory, status_hook )
        
        status = file_seed.status
        
        if status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                
                job_status.SetStatusText( 'successful!' )
                
            elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                
                job_status.SetStatusText( 'was already in the database!' )
                
            
            if file_seed.HasHash():
                
                hash = file_seed.GetHash()
                
                job_status.SetFiles( [ hash ], 'download' )
                
            
        elif status == CC.STATUS_DELETED:
            
            job_status.SetStatusText( 'had already been deleted!' )
            
        
    finally:
        
        job_status.Finish()
        
    
def THREADDownloadURLs( job_status: ClientThreading.JobStatus, urls, title ):
    
    job_status.SetStatusTitle( title )
    job_status.SetStatusText( 'initialising' )
    
    num_successful = 0
    num_redundant = 0
    num_deleted = 0
    num_failed = 0
    
    presentation_hashes = []
    presentation_hashes_fast = set()
    
    file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
    file_import_options.SetIsDefault( True )
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJob( *args, **kwargs )
        
        network_job.OverrideBandwidth()
        
        return network_job
        
    
    def status_hook( text ):
        
        job_status.SetStatusText( HydrusText.GetFirstLine( text ), 2 )
        
    
    network_job_presentation_context_factory = GenerateMultiplePopupNetworkJobPresentationContextFactory( job_status )
    
    for ( i, url ) in enumerate( urls ):
        
        ( i_paused, should_quit ) = job_status.WaitIfNeeded()
        
        if should_quit:
            
            break
            
        
        job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( i, len( urls ) ) )
        job_status.SetGauge( i, len( urls ) )
        
        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
        
        try:
            
            file_seed.DownloadAndImportRawFile( url, file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD, network_job_factory, network_job_presentation_context_factory, status_hook )
            
            status = file_seed.status
            
            if status in CC.SUCCESSFUL_IMPORT_STATES:
                
                if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                    
                    num_successful += 1
                    
                elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                    
                    num_redundant += 1
                    
                
                if file_seed.HasHash():
                    
                    hash = file_seed.GetHash()
                    
                    if hash not in presentation_hashes_fast:
                        
                        presentation_hashes.append( hash )
                        
                    
                    presentation_hashes_fast.add( hash )
                    
                
                if len( presentation_hashes ) > 0:
                    
                    job_status.SetFiles( presentation_hashes, 'downloads' )
                    
                
            elif status == CC.STATUS_DELETED:
                
                num_deleted += 1
                
            
        except Exception as e:
            
            num_failed += 1
            
            HydrusData.Print( url + ' failed to import!' )
            HydrusData.PrintException( e )
            
        finally:
            
            job_status.DeleteStatusText( level = 2 )
            
        
    
    job_status.DeleteNetworkJob()
    
    text_components = []
    
    if num_successful > 0:
        
        text_components.append( HydrusNumbers.ToHumanInt( num_successful ) + ' successful' )
        
    
    if num_redundant > 0:
        
        text_components.append( HydrusNumbers.ToHumanInt( num_redundant ) + ' already in db' )
        
    
    if num_deleted > 0:
        
        text_components.append( HydrusNumbers.ToHumanInt( num_deleted ) + ' deleted' )
        
    
    if num_failed > 0:
        
        text_components.append( HydrusNumbers.ToHumanInt( num_failed ) + ' failed (errors written to log)' )
        
    
    job_status.SetStatusText( ', '.join( text_components ) )
    
    if len( presentation_hashes ) > 0:
        
        job_status.SetFiles( presentation_hashes, 'downloads' )
        
    
    job_status.DeleteGauge()
    
    job_status.Finish()
    
def UpdateFileSeedCacheWithFileSeeds( file_seed_cache, file_seeds, max_new_urls_allowed = None ):
    
    new_file_seeds = []
    
    num_urls_added = 0
    num_urls_already_in_file_seed_cache = 0
    can_search_for_more_files = True
    stop_reason = ''
    
    for file_seed in file_seeds:
        
        if max_new_urls_allowed is not None and num_urls_added >= max_new_urls_allowed:
            
            can_search_for_more_files = False
            
            stop_reason = 'hit file limit'
            
            break
            
        
        if file_seed_cache.HasFileSeed( file_seed ):
            
            num_urls_already_in_file_seed_cache += 1
            
        else:
            
            num_urls_added += 1
            
            new_file_seeds.append( file_seed )
            
        
    
    file_seed_cache.AddFileSeeds( new_file_seeds )
    
    return ( num_urls_added, num_urls_already_in_file_seed_cache, can_search_for_more_files, stop_reason )
    
def WakeRepeatingJob( job ):
    
    if job is not None:
        
        job.Wake()
        
    

class NetworkJobPresentationContext( object ):
    
    def __init__( self, enter_call, exit_call ):
        
        self._enter_call = enter_call
        self._exit_call = exit_call
        
    
    def __enter__( self ):
        
        self._enter_call()
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._exit_call()
        
    
