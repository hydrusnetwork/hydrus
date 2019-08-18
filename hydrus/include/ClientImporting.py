from . import ClientConstants as CC
from . import ClientData
from . import ClientDefaults
from . import ClientDownloading
from . import ClientFiles
from . import ClientImportOptions
from . import ClientImportFileSeeds
from . import ClientImportGallerySeeds
from . import ClientNetworkingContexts
from . import ClientNetworkingJobs
from . import ClientParsing
from . import ClientPaths
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
import os
import random
import threading
import time
import traceback
import wx

CHECKER_STATUS_OK = 0
CHECKER_STATUS_DEAD = 1
CHECKER_STATUS_404 = 2

DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME = 0.1

REPEATING_JOB_TYPICAL_PERIOD = 30.0

def ConvertAllParseResultsToFileSeeds( all_parse_results, source_url, file_import_options ):
    
    file_seeds = []
    
    seen_urls = set()
    
    for parse_results in all_parse_results:
        
        parsed_urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_DESIRED, ), only_get_top_priority = True )
        
        parsed_urls = HydrusData.DedupeList( parsed_urls )
        
        parsed_urls = [ url for url in parsed_urls if url not in seen_urls ]
        
        seen_urls.update( parsed_urls )
        
        # note we do this recursively due to parse_results being appropriate only for these urls--don't move this out again, or tags will be messed up
        
        for url in parsed_urls:
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.SetReferralURL( source_url )
            
            file_seed.AddParseResults( parse_results, file_import_options )
            
            file_seeds.append( file_seed )
            
        
    
    return file_seeds
    
def GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def enter_call():
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
        
        def exit_call():
            
            job_key.SetVariable( 'popup_network_job', None )
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
def GenerateSinglePopupNetworkJobPresentationContextFactory( job_key ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def enter_call():
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
        
        def exit_call():
            
            job_key.DeleteVariable( 'popup_network_job' )
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
def GetRepeatingJobInitialDelay():
    
    return 0.5 + ( random.random() * 0.5 )
    
def PageImporterShouldStopWorking( page_key ):
    
    return HG.view_shutdown or not HG.client_controller.PageAlive( page_key )
    
def PublishPresentationHashes( publishing_label, hashes, publish_to_popup_button, publish_files_to_page ):
    
    if publish_to_popup_button:
        
        files_job_key = ClientThreading.JobKey()
        
        files_job_key.SetVariable( 'popup_files_mergable', True )
        files_job_key.SetVariable( 'popup_files', ( list( hashes ), publishing_label ) )
        
        HG.client_controller.pub( 'message', files_job_key )
        
    
    if publish_files_to_page:
        
        HG.client_controller.pub( 'imported_files_to_page', list( hashes ), publishing_label )
        
    
def THREADDownloadURL( job_key, url, url_string ):
    
    job_key.SetVariable( 'popup_title', url_string )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    #
    
    file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJob( *args, **kwargs )
        
        network_job.OverrideBandwidth( 30 )
        
        return network_job
        
    
    def status_hook( text ):
        
        job_key.SetVariable( 'popup_text_1', text )
        
    
    network_job_presentation_context_factory = GenerateSinglePopupNetworkJobPresentationContextFactory( job_key )
    
    file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
    
    #
    
    try:
        
        file_seed.DownloadAndImportRawFile( url, file_import_options, network_job_factory, network_job_presentation_context_factory, status_hook )
        
        status = file_seed.status
        
        if status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                
                job_key.SetVariable( 'popup_text_1', 'successful!' )
                
            elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                
                job_key.SetVariable( 'popup_text_1', 'was already in the database!' )
                
            
            if file_seed.HasHash():
                
                hash = file_seed.GetHash()
                
                job_key.SetVariable( 'popup_files', ( [ hash ], 'download' ) )
                
            
        elif status == CC.STATUS_DELETED:
            
            job_key.SetVariable( 'popup_text_1', 'had already been deleted!' )
            
        
    finally:
        
        job_key.Finish()
        
    
def THREADDownloadURLs( job_key, urls, title ):
    
    job_key.SetVariable( 'popup_title', title )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    num_successful = 0
    num_redundant = 0
    num_deleted = 0
    num_failed = 0
    
    presentation_hashes = []
    presentation_hashes_fast = set()
    
    file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJob( *args, **kwargs )
        
        network_job.OverrideBandwidth()
        
        return network_job
        
    
    def status_hook( text ):
        
        job_key.SetVariable( 'popup_text_2', text )
        
    
    network_job_presentation_context_factory = GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key )
    
    for ( i, url ) in enumerate( urls ):
        
        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
        
        if should_quit:
            
            break
            
        
        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, len( urls ) ) )
        job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( urls ) ) )
        
        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
        
        try:
            
            file_seed.DownloadAndImportRawFile( url, file_import_options, network_job_factory, network_job_presentation_context_factory, status_hook )
            
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
                    
                
            elif status == CC.STATUS_DELETED:
                
                num_deleted += 1
                
            
        except Exception as e:
            
            num_failed += 1
            
            HydrusData.Print( url + ' failed to import!' )
            HydrusData.PrintException( e )
            
        finally:
            
            job_key.DeleteVariable( 'popup_text_2' )
            
        
    
    job_key.DeleteVariable( 'popup_network_job' )
    
    text_components = []
    
    if num_successful > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_successful ) + ' successful' )
        
    
    if num_redundant > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_redundant ) + ' already in db' )
        
    
    if num_deleted > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_deleted ) + ' deleted' )
        
    
    if num_failed > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_failed ) + ' failed (errors written to log)' )
        
    
    job_key.SetVariable( 'popup_text_1', ', '.join( text_components ) )
    
    if len( presentation_hashes ) > 0:
        
        job_key.SetVariable( 'popup_files', ( presentation_hashes, 'downloads' ) )
        
    
    job_key.DeleteVariable( 'popup_gauge_1' )
    
    job_key.Finish()
    
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
        
    
