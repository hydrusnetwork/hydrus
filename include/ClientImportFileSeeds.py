from . import ClientConstants as CC
from . import ClientData
from . import ClientImageHandling
from . import ClientImporting
from . import ClientNetworkingDomain
from . import ClientParsing
from . import ClientPaths
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusImageHandling
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
import os
import threading
import time
import traceback
import urllib.parse

def GenerateFileSeedCacheStatus( file_seed_cache ):
    
    statuses_to_counts = file_seed_cache.GetStatusesToCounts()
    
    return GenerateStatusesToCountsStatus( statuses_to_counts )
    
def GenerateFileSeedCachesStatus( file_seed_caches ):
    
    statuses_to_counts = collections.Counter()
    
    for file_seed_cache in file_seed_caches:
        
        statuses_to_counts.update( file_seed_cache.GetStatusesToCounts() )
        
    
    return GenerateStatusesToCountsStatus( statuses_to_counts )
    
def GenerateStatusesToCountsStatus( statuses_to_counts ):
    
    num_successful_and_new = statuses_to_counts[ CC.STATUS_SUCCESSFUL_AND_NEW ]
    num_successful_but_redundant = statuses_to_counts[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ]
    num_ignored = statuses_to_counts[ CC.STATUS_VETOED ]
    num_deleted = statuses_to_counts[ CC.STATUS_DELETED ]
    num_failed = statuses_to_counts[ CC.STATUS_ERROR ]
    num_skipped = statuses_to_counts[ CC.STATUS_SKIPPED ]
    num_unknown = statuses_to_counts[ CC.STATUS_UNKNOWN ]
    
    status_strings = []
    
    num_successful = num_successful_and_new + num_successful_but_redundant
    
    if num_successful > 0:
        
        s = HydrusData.ToHumanInt( num_successful ) + ' successful'
        
        if num_successful_and_new > 0:
            
            if num_successful_but_redundant > 0:
                
                s += ' (' + HydrusData.ToHumanInt( num_successful_but_redundant ) + ' already in db)'
                
            
        else:
            
            s += ' (all already in db)'
            
        
        status_strings.append( s )
        
    
    if num_ignored > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_ignored ) + ' ignored' )
        
    
    if num_deleted > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_deleted ) + ' previously deleted' )
        
    
    if num_failed > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_failed ) + ' failed' )
        
    
    if num_skipped > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_skipped ) + ' skipped' )
        
    
    status = ', '.join( status_strings )
    
    #
    
    total = sum( statuses_to_counts.values() )
    
    total_processed = total - num_unknown
    
    #
    
    simple_status = ''
    
    if total > 0:
        
        if num_unknown > 0:
            
            simple_status += HydrusData.ConvertValueRangeToPrettyString( total_processed, total )
            
        else:
            
            simple_status += HydrusData.ToHumanInt( total_processed )
            
        
        show_new_on_file_seed_short_summary = HG.client_controller.new_options.GetBoolean( 'show_new_on_file_seed_short_summary' )
        
        if show_new_on_file_seed_short_summary and num_successful_and_new:
            
            simple_status += ' - ' + HydrusData.ToHumanInt( num_successful_and_new ) + 'N'
            
        
        simple_status_strings = []
        
        if num_ignored > 0:
            
            simple_status_strings.append( HydrusData.ToHumanInt( num_ignored ) + 'Ig' )
            
        
        show_deleted_on_file_seed_short_summary = HG.client_controller.new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' )
        
        if show_deleted_on_file_seed_short_summary and num_deleted > 0:
            
            simple_status_strings.append( HydrusData.ToHumanInt( num_deleted ) + 'D' )
            
        
        if num_failed > 0:
            
            simple_status_strings.append( HydrusData.ToHumanInt( num_failed ) + 'F' )
            
        
        if num_skipped > 0:
            
            simple_status_strings.append( HydrusData.ToHumanInt( num_skipped ) + 'S' )
            
        
        if len( simple_status_strings ) > 0:
            
            simple_status += ' - ' + ''.join( simple_status_strings )
            
        
    
    return ( status, simple_status, ( total_processed, total ) )
    
class FileImportJob( object ):
    
    def __init__( self, temp_path, file_import_options = None ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job created for path {}.'.format( temp_path ) )
            
        
        if file_import_options is None:
            
            file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
            
        
        self._temp_path = temp_path
        self._file_import_options = file_import_options
        
        self._hash = None
        self._pre_import_status = None
        
        self._file_info = None
        self._thumbnail_bytes = None
        self._phashes = None
        self._extra_hashes = None
        
    
    def CheckIsGoodToImport( self ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job testing if good to import for file import options' )
            
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        self._file_import_options.CheckFileIsValid( size, mime, width, height )
        
    
    def DoWork( self ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job starting work.' )
            
        
        ( pre_import_status, hash, note ) = self.GenerateHashAndStatus()
        
        if self.IsNewToDB():
            
            self.GenerateInfo()
            
            self.CheckIsGoodToImport()
            
            mime = self.GetMime()
            
            HG.client_controller.client_files_manager.AddFile( hash, mime, self._temp_path, thumbnail_bytes = self._thumbnail_bytes )
            
            ( import_status, note ) = HG.client_controller.WriteSynchronous( 'import_file', self )
            
        else:
            
            import_status = pre_import_status
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job is done, now publishing content updates' )
            
        
        self.PubsubContentUpdates()
        
        return ( import_status, hash, note )
        
    
    def GenerateHashAndStatus( self ):
        
        HydrusImageHandling.ConvertToPngIfBmp( self._temp_path )
        
        self._hash = HydrusFileHandling.GetHashFromPath( self._temp_path )
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job hash: {}'.format( self._hash.hex() ) )
            
        
        ( self._pre_import_status, hash, note ) = HG.client_controller.Read( 'hash_status', 'sha256', self._hash, prefix = 'file recognised' )
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job pre-import status: {}, {}'.format( CC.status_string_lookup[ self._pre_import_status ], note ) )
            
        
        return ( self._pre_import_status, self._hash, note )
        
    
    def GenerateInfo( self ):
        
        mime = HydrusFileHandling.GetMime( self._temp_path )
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job mime: {}'.format( HC.mime_string_lookup[ mime ] ) )
            
        
        new_options = HG.client_controller.new_options
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and not self._file_import_options.AllowsDecompressionBombs():
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job testing for decompression bomb' )
                
            
            if HydrusImageHandling.IsDecompressionBomb( self._temp_path ):
                
                if HG.file_import_report_mode:
                    
                    HydrusData.ShowText( 'File import job: it was a decompression bomb' )
                    
                
                raise HydrusExceptions.DecompressionBombException( 'Image seems to be a Decompression Bomb!' )
                
            
        
        self._file_info = HydrusFileHandling.GetFileInfo( self._temp_path, mime )
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job file info: {}'.format( self._file_info ) )
            
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job generating thumbnail' )
                
            
            bounding_dimensions = HG.client_controller.options[ 'thumbnail_dimensions' ]
            
            target_resolution = HydrusImageHandling.GetThumbnailResolution( ( width, height ), bounding_dimensions )
            
            percentage_in = HG.client_controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
            
            self._thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( self._temp_path, target_resolution, mime, duration, num_frames, percentage_in = percentage_in )
            
        
        if mime in HC.MIMES_WE_CAN_PHASH:
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job generating phashes' )
                
            
            self._phashes = ClientImageHandling.GenerateShapePerceptualHashes( self._temp_path, mime )
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job generated {} phashes: {}'.format( len( self._phashes ), [ phash.hex() for phash in self._phashes ] ) )
                
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job generating other hashes' )
            
        
        self._extra_hashes = HydrusFileHandling.GetExtraHashesFromPath( self._temp_path )
        
    
    def GetExtraHashes( self ):
        
        return self._extra_hashes
        
    
    def GetFileImportOptions( self ):
        
        return self._file_import_options
        
    
    def GetFileInfo( self ):
        
        return self._file_info
        
    
    def GetHash( self ):
        
        return self._hash
        
    
    def GetMime( self ):
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        return mime
        
    
    def GetPreImportStatus( self ):
        
        return self._pre_import_status
        
    
    def GetPHashes( self ):
        
        return self._phashes
        
    
    def PubsubContentUpdates( self ):
        
        if self._pre_import_status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
            
            if self._file_import_options.AutomaticallyArchives():
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, set( ( self._hash, ) ) ) ] }
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
    def IsNewToDB( self ):
        
        if self._pre_import_status == CC.STATUS_UNKNOWN:
            
            return True
            
        
        if self._pre_import_status == CC.STATUS_DELETED:
            
            if not self._file_import_options.ExcludesDeleted():
                
                return True
                
            
        
        return False
        
    
FILE_SEED_TYPE_HDD = 0
FILE_SEED_TYPE_URL = 1

class FileSeed( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED
    SERIALISABLE_NAME = 'File Import'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, file_seed_type = None, file_seed_data = None ):
        
        if file_seed_type is None:
            
            file_seed_type = FILE_SEED_TYPE_URL
            
        
        if file_seed_data is None:
            
            file_seed_data = 'https://big-guys.4u/monica_lewinsky_hott.tiff.exe.vbs'
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.file_seed_type = file_seed_type
        self.file_seed_data = file_seed_data
        
        self.created = HydrusData.GetNow()
        self.modified = self.created
        self.source_time = None
        self.status = CC.STATUS_UNKNOWN
        self.note = ''
        
        self._referral_url = None
        
        self._fixed_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        self._urls = set()
        self._tags = set()
        self._hashes = {}
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.file_seed_type, self.file_seed_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _CheckTagsBlacklist( self, tags, tag_import_options ):
        
        tag_import_options.CheckBlacklist( tags )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_fixed_service_keys_to_tags = self._fixed_service_keys_to_tags.GetSerialisableTuple()
        
        serialisable_urls = list( self._urls )
        serialisable_tags = list( self._tags )
        serialisable_hashes = [ ( hash_type, hash.hex() ) for ( hash_type, hash ) in list(self._hashes.items()) if hash is not None ]
        
        return ( self.file_seed_type, self.file_seed_data, self.created, self.modified, self.source_time, self.status, self.note, self._referral_url, serialisable_fixed_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.file_seed_type, self.file_seed_data, self.created, self.modified, self.source_time, self.status, self.note, self._referral_url, serialisable_fixed_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes ) = serialisable_info
        
        self._fixed_service_keys_to_tags = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_fixed_service_keys_to_tags )
        
        self._urls = set( serialisable_urls )
        self._tags = set( serialisable_tags )
        self._hashes = { hash_type : bytes.fromhex( encoded_hash ) for ( hash_type, encoded_hash ) in serialisable_hashes if encoded_hash is not None }
        
    
    def _NormaliseAndFilterAssociableURLs( self, urls ):
        
        normalised_urls = set()
        
        for url in urls:
            
            try:
                
                url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
                
            except HydrusExceptions.URLClassException:
                
                continue # not a url--something like "file:///C:/Users/Tall%20Man/Downloads/maxresdefault.jpg" ha ha ha
                
            
            normalised_urls.add( url )
            
        
        associable_urls = { url for url in normalised_urls if HG.client_controller.network_engine.domain_manager.ShouldAssociateURLWithFiles( url ) }
        
        return associable_urls
        
    
    def _SetupTagImportOptions( self, given_tag_import_options ):
        
        if given_tag_import_options.IsDefault():
            
            if self.IsAPostURL():
                
                tio_lookup_url = self.file_seed_data
                
            else:
                
                if self._referral_url is not None:
                    
                    tio_lookup_url = self._referral_url
                    
                else:
                    
                    tio_lookup_url = self.file_seed_data
                    
                
            
            tag_import_options = HG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( tio_lookup_url )
            
        else:
            
            tag_import_options = given_tag_import_options
            
        
        return tag_import_options
        
    
    def _UpdateModified( self ):
        
        self.modified = HydrusData.GetNow()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( file_seed_type, file_seed_data, created, modified, source_time, status, note, serialisable_urls, serialisable_tags, serialisable_hashes ) = old_serialisable_info
            
            referral_url = None
            
            new_serialisable_info = ( file_seed_type, file_seed_data, created, modified, source_time, status, note, referral_url, serialisable_urls, serialisable_tags, serialisable_hashes )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( file_seed_type, file_seed_data, created, modified, source_time, status, note, referral_url, serialisable_urls, serialisable_tags, serialisable_hashes ) = old_serialisable_info
            
            fixed_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
            serialisable_fixed_service_keys_to_tags = fixed_service_keys_to_tags.GetSerialisableTuple()
            
            new_serialisable_info = ( file_seed_type, file_seed_data, created, modified, source_time, status, note, referral_url, serialisable_fixed_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes )
            
            return ( 3, new_serialisable_info )
            
        
    
    def AddParseResults( self, parse_results, file_import_options ):
        
        for ( hash_type, hash ) in ClientParsing.GetHashesFromParseResults( parse_results ):
            
            if hash_type not in self._hashes:
                
                self._hashes[ hash_type ] = hash
                
            
        
        if file_import_options.ShouldAssociateSourceURLs():
            
            source_urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_SOURCE, ) )
            
            associable_urls = self._NormaliseAndFilterAssociableURLs( source_urls )
            
            associable_urls.discard( self.file_seed_data )
            
            self._urls.update( associable_urls )
            
        
        tags = ClientParsing.GetTagsFromParseResults( parse_results )
        
        self._tags.update( tags )
        
        source_timestamp = ClientParsing.GetTimestampFromParseResults( parse_results, HC.TIMESTAMP_TYPE_SOURCE )
        
        if source_timestamp is not None:
            
            source_timestamp = min( HydrusData.GetNow() - 30, source_timestamp )
            
            self.source_time = source_timestamp
            
        
        self._UpdateModified()
        
    
    def AddTags( self, tags ):
        
        tags = HydrusTags.CleanTags( tags )
        
        self._tags.update( tags )
        
        self._UpdateModified()
        
    
    def AddURL( self, url ):
        
        urls = ( url, )
        
        associable_urls = self._NormaliseAndFilterAssociableURLs( urls )
        
        associable_urls.discard( self.file_seed_data )
        
        self._urls.update( associable_urls )
        
    
    def CheckPreFetchMetadata( self, tag_import_options ):
        
        self._CheckTagsBlacklist( self._tags, tag_import_options )
        
    
    def DownloadAndImportRawFile( self, file_url, file_import_options, network_job_factory, network_job_presentation_context_factory, status_hook, override_bandwidth = False ):
        
        self.AddURL( file_url )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            if self.file_seed_data != file_url:
                
                referral_url = self.file_seed_data
                
            else:
                
                referral_url = self._referral_url
                
            
            status_hook( 'downloading file' )
            
            network_job = network_job_factory( 'GET', file_url, temp_path = temp_path, referral_url = referral_url )
            
            if override_bandwidth:
                
                network_job.OverrideBandwidth( 3 )
                
            
            network_job.SetFileImportOptions( file_import_options )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            with network_job_presentation_context_factory( network_job ) as njpc:
                
                network_job.WaitUntilDone()
                
            
            status_hook( 'importing file' )
            
            self.Import( temp_path, file_import_options )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    def FetchPageMetadata( self, tag_import_options ):
        
        pass
        
    
    def GetExampleNetworkJob( self, network_job_factory ):
        
        if self.IsAPostURL():
            
            post_url = self.file_seed_data
            
            ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
            
        else:
            
            url_to_check = self.file_seed_data
            
        
        network_job = network_job_factory( 'GET', url_to_check )
        
        return network_job
        
    
    def GetHash( self ):
        
        if 'sha256' in self._hashes:
            
            return self._hashes[ 'sha256' ]
            
        
        return None
        
    
    def GetPreImportStatusPredictionHash( self, file_import_options ):
        
        UNKNOWN_DEFAULT = ( CC.STATUS_UNKNOWN, None, '' )
        
        ( status, hash, note ) = UNKNOWN_DEFAULT
        
        if file_import_options.DoNotCheckHashesBeforeImporting():
            
            return ( status, hash, note )
            
        
        # hashes
        
        if status == CC.STATUS_UNKNOWN:
            
            for ( hash_type, found_hash ) in list(self._hashes.items()):
                
                ( status, hash, note ) = HG.client_controller.Read( 'hash_status', hash_type, found_hash, prefix = 'hash recognised' )
                
                if status != CC.STATUS_UNKNOWN:
                    
                    break
                    
                
            
        
        if status == CC.STATUS_DELETED:
            
            if not file_import_options.ExcludesDeleted():
                
                ( status, hash, note ) = UNKNOWN_DEFAULT
                
            
        
        return ( status, hash, note )
        
    
    def GetPreImportStatusPredictionURL( self, file_import_options, file_url = None ):
        
        UNKNOWN_DEFAULT = ( CC.STATUS_UNKNOWN, None, '' )
        
        ( status, hash, note ) = UNKNOWN_DEFAULT
        
        if file_import_options.DoNotCheckKnownURLsBeforeImporting():
            
            return ( status, hash, note )
            
        
        # urls
        
        urls = set( self._urls )
        
        if file_url is not None:
            
            urls.add( file_url )
            
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            urls.add( self.file_seed_data )
            
        
        unrecognised_url_results = set()
        
        for url in urls:
            
            if HG.client_controller.network_engine.domain_manager.URLCanReferToMultipleFiles( url ):
                
                continue
                
            
            # we now only trust url-matched single urls and the post/file urls
            # trusting unmatched source urls was too much of a hassle with too many boorus providing bad source urls like user account pages
            
            if HG.client_controller.network_engine.domain_manager.URLDefinitelyRefersToOneFile( url ) or url in ( self.file_seed_data, file_url ):
                
                results = HG.client_controller.Read( 'url_statuses', url )
                
                if len( results ) == 0: # if no match found, no useful data discovered
                    
                    continue
                    
                elif len( results ) > 1: # if more than one file claims this url, it cannot be relied on to guess the file
                    
                    continue
                    
                else: # i.e. 1 match found
                    
                    ( status, hash, note ) = results[0]
                    
                    if status != CC.STATUS_UNKNOWN:
                        
                        # a known one-file url has given a single clear result. sounds good
                        
                        we_have_a_match = True
                        
                        if self.file_seed_type == FILE_SEED_TYPE_URL:
                            
                            # to double-check, let's see if the file that claims that url has any other interesting urls
                            # if the file has another url with the same url class as ours, then this is prob an unreliable 'alternate' source url attribution, and untrustworthy
                            
                            my_url = self.file_seed_data
                            
                            if url != my_url:
                                
                                my_url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( my_url )
                                
                                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                                
                                this_files_urls = media_result.GetLocationsManager().GetURLs()
                                
                                for this_files_url in this_files_urls:
                                    
                                    if this_files_url != my_url:
                                        
                                        this_url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( this_files_url )
                                        
                                        if my_url_class == this_url_class:
                                            
                                            # oh no, the file this source url refers to has a different known url in this same domain
                                            # it is more likely that an edit on this site points to the original elsewhere
                                            
                                            ( status, hash, note ) = UNKNOWN_DEFAULT
                                            
                                            we_have_a_match = False
                                            
                                            break
                                            
                                        
                                    
                                
                            
                        
                        if we_have_a_match:
                            
                            break # if a known one-file url gives a single clear result, that result is reliable
                            
                        
                    
                
            
        
        if status == CC.STATUS_DELETED:
            
            if not file_import_options.ExcludesDeleted():
                
                ( status, hash, note ) = UNKNOWN_DEFAULT
                
            
        
        return ( status, hash, note )
        
    
    def GetSearchFileSeeds( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            search_urls = ClientNetworkingDomain.GetSearchURLs( self.file_seed_data )
            
            search_file_seeds = [ FileSeed( FILE_SEED_TYPE_URL, search_url ) for search_url in search_urls ]
            
        else:
            
            search_file_seeds = [ self ]
            
        
        return search_file_seeds
        
    
    def HasHash( self ):
        
        return self.GetHash() is not None
        
    
    def Import( self, temp_path, file_import_options ):
        
        file_import_job = FileImportJob( temp_path, file_import_options )
        
        ( status, hash, note ) = file_import_job.DoWork()
        
        self.SetStatus( status, note = note )
        self.SetHash( hash )
        
    
    def ImportPath( self, file_seed_cache, file_import_options, limited_mimes = None ):
        
        try:
            
            if self.file_seed_type != FILE_SEED_TYPE_HDD:
                
                raise HydrusExceptions.VetoException( 'Attempted to import as a path, but I do not think I am a path!' )
                
            
            path = self.file_seed_data
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.VetoException( 'Source file does not exist!' )
                
            
            if limited_mimes is not None:
                
                mime = HydrusFileHandling.GetMime( path )
                
                if mime not in limited_mimes:
                    
                    raise HydrusExceptions.VetoException( 'Not in allowed mimes!' )
                    
                
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                copied = HydrusPaths.MirrorFile( path, temp_path )
                
                if not copied:
                    
                    raise Exception( 'File failed to copy to temp path--see log for error.' )
                    
                
                self.Import( temp_path, file_import_options )
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
            self.WriteContentUpdates()
            
        except HydrusExceptions.MimeException as e:
            
            self.SetStatus( CC.STATUS_ERROR, exception = e )
            
        except HydrusExceptions.VetoException as e:
            
            self.SetStatus( CC.STATUS_VETOED, note = str( e ) )
            
        except Exception as e:
            
            self.SetStatus( CC.STATUS_ERROR, exception = e )
            
        
        file_seed_cache.NotifyFileSeedsUpdated( ( self, ) )
        
    
    def IsAPostURL( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
            
            if url_type == HC.URL_TYPE_POST:
                
                return True
                
            
        
        return False
        
    
    def IsDeleted( self ):
        
        return self.status == CC.STATUS_DELETED
        
    
    def Normalise( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            self.file_seed_data = HG.client_controller.network_engine.domain_manager.NormaliseURL( self.file_seed_data )
            
        
    
    def PredictPreImportStatus( self, file_import_options, tag_import_options, file_url = None ):
        
        ( url_status, url_hash, url_note ) = self.GetPreImportStatusPredictionURL( file_import_options, file_url = file_url )
        ( hash_status, hash_hash, hash_note ) = self.GetPreImportStatusPredictionHash( file_import_options )
        
        url_recognised_and_file_already_in_db = url_status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT
        hash_recognised_and_file_already_in_db = hash_status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT
        
        # now let's set the prediction
        
        if hash_status != CC.STATUS_UNKNOWN: # trust hashes over urls m8
            
            ( status, hash, note ) = ( hash_status, hash_hash, hash_note )
            
        else:
            
            ( status, hash, note ) = ( url_status, url_hash, url_note )
            
        
        if self.status == CC.STATUS_UNKNOWN and status != CC.STATUS_UNKNOWN:
            
            self.status = status
            
            if hash is not None:
                
                self._hashes[ 'sha256' ] = hash
                
            
            self.note = note
            
            self._UpdateModified()
            
        
        # and make some recommendations
        
        should_download_file = self.status == CC.STATUS_UNKNOWN
        
        should_download_metadata = should_download_file # if we want the file, we need the metadata to get the file_url!
        
        # but if we otherwise still want to force some tags, let's do it
        if not should_download_metadata and tag_import_options.WorthFetchingTags():
            
            url_override = url_recognised_and_file_already_in_db and tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB()
            hash_override = hash_recognised_and_file_already_in_db and tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB()
            
            if url_override or hash_override:
                
                should_download_metadata = True
                
            
        
        return ( should_download_metadata, should_download_file )
        
    
    def PresentToPage( self, page_key ):
        
        hash = self.GetHash()
        
        if hash is not None:
            
            ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
            
            HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
            
        
    
    def SetFixedServiceKeysToTags( self, service_keys_to_tags ):
        
        self._fixed_service_keys_to_tags = ClientTags.ServiceKeysToTags( service_keys_to_tags )
        
    
    def SetHash( self, hash ):
        
        if hash is not None:
            
            self._hashes[ 'sha256' ] = hash
            
        
    
    def SetReferralURL( self, referral_url ):
        
        self._referral_url = referral_url
        
    
    def SetStatus( self, status, note = '', exception = None ):
        
        if exception is not None:
            
            first_line = str( exception ).split( os.linesep )[0]
            
            note = first_line + '\u2026 (Copy note to see full error)'
            note += os.linesep
            note += traceback.format_exc()
            
            HydrusData.Print( 'Error when processing ' + self.file_seed_data + ' !' )
            HydrusData.Print( traceback.format_exc() )
            
        
        self.status = status
        self.note = note
        
        self._UpdateModified()
        
    
    def ShouldPresent( self, file_import_options, in_inbox = None ):
        
        hash = self.GetHash()
        
        if hash is not None and self.status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if in_inbox is None:
                
                if file_import_options.ShouldPresentIgnorantOfInbox( self.status ):
                    
                    return True
                    
                
                if file_import_options.ShouldNotPresentIgnorantOfInbox( self.status ):
                    
                    return False
                    
                
                in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                
            
            if file_import_options.ShouldPresent( self.status, in_inbox ):
                
                return True
                
            
        
        return False
        
    
    def WorksInNewSystem( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
            
            if url_type == HC.URL_TYPE_FILE:
                
                return True
                
            
            if url_type == HC.URL_TYPE_POST and can_parse:
                
                return True
                
            
            if url_type == HC.URL_TYPE_UNKNOWN and self._referral_url is not None: # this is likely be a multi-file child of a post url file_seed
                
                ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self._referral_url )
                
                if url_type == HC.URL_TYPE_POST: # we must have got here through parsing that m8, so let's assume this is an unrecognised file url
                    
                    return True
                    
                
            
        
        return False
        
    
    def WorkOnURL( self, file_seed_cache, status_hook, network_job_factory, network_job_presentation_context_factory, file_import_options, tag_import_options ):
        
        did_substantial_work = False
        
        try:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
            
            if url_type not in ( HC.URL_TYPE_POST, HC.URL_TYPE_FILE, HC.URL_TYPE_UNKNOWN ):
                
                raise HydrusExceptions.VetoException( 'This URL appeared to be a "{}", which is not a File or Post URL!'.format( match_name ) )
                
            
            if url_type == HC.URL_TYPE_POST and not can_parse:
                
                raise HydrusExceptions.VetoException( 'Did not have a parser for this URL!' )
                
            
            tag_import_options = self._SetupTagImportOptions( tag_import_options )
            
            status_hook( 'checking url status' )
            
            ( should_download_metadata, should_download_file ) = self.PredictPreImportStatus( file_import_options, tag_import_options )
            
            if self.IsAPostURL():
                
                if should_download_metadata:
                    
                    did_substantial_work = True
                    
                    post_url = self.file_seed_data
                    
                    ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
                    
                    status_hook( 'downloading file page' )
                    
                    if self._referral_url not in ( post_url, url_to_check ):
                        
                        referral_url = self._referral_url
                        
                    else:
                        
                        referral_url = None
                        
                    
                    network_job = network_job_factory( 'GET', url_to_check, referral_url = referral_url )
                    
                    HG.client_controller.network_engine.AddJob( network_job )
                    
                    with network_job_presentation_context_factory( network_job ) as njpc:
                        
                        network_job.WaitUntilDone()
                        
                    
                    parsing_text = network_job.GetContentText()
                    
                    parsing_context = {}
                    
                    parsing_context[ 'post_url' ] = post_url
                    parsing_context[ 'url' ] = url_to_check
                    
                    all_parse_results = parser.Parse( parsing_context, parsing_text )
                    
                    if len( all_parse_results ) == 0:
                        
                        raise HydrusExceptions.VetoException( 'The parser found nothing in the document!' )
                        
                    elif len( all_parse_results ) > 1:
                        
                        # multiple child urls generated by a subsidiary page parser
                        
                        file_seeds = ClientImporting.ConvertAllParseResultsToFileSeeds( all_parse_results, self.file_seed_data, file_import_options )
                        
                        for file_seed in file_seeds:
                            
                            file_seed._fixed_service_keys_to_tags = self._fixed_service_keys_to_tags.Duplicate()
                            
                            file_seed._urls.update( self._urls )
                            file_seed._tags.update( self._tags )
                            
                        
                        try:
                            
                            my_index = file_seed_cache.GetFileSeedIndex( self )
                            
                            insertion_index = my_index + 1
                            
                        except:
                            
                            insertion_index = len( file_seed_cache )
                            
                        
                        num_urls_added = file_seed_cache.InsertFileSeeds( insertion_index, file_seeds )
                        
                        status = CC.STATUS_SUCCESSFUL_AND_NEW
                        note = 'Found ' + HydrusData.ToHumanInt( num_urls_added ) + ' new URLs.'
                        
                        self.SetStatus( status, note = note )
                        
                    else:
                        
                        # no subsidiary page parser results, just one
                        
                        parse_results = all_parse_results[0]
                        
                        self.AddParseResults( parse_results, file_import_options )
                        
                        self.CheckPreFetchMetadata( tag_import_options )
                        
                        desired_urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_DESIRED, ), only_get_top_priority = True )
                        
                        child_urls = []
                        
                        if len( desired_urls ) == 0:
                            
                            raise HydrusExceptions.VetoException( 'Could not find a file or post URL to download!' )
                            
                        elif len( desired_urls ) == 1:
                            
                            desired_url = desired_urls[0]
                            
                            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( desired_url )
                            
                            if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_UNKNOWN ):
                                
                                file_url = desired_url
                                
                                ( should_download_metadata, should_download_file ) = self.PredictPreImportStatus( file_import_options, tag_import_options, file_url )
                                
                                if should_download_file:
                                    
                                    self.DownloadAndImportRawFile( file_url, file_import_options, network_job_factory, network_job_presentation_context_factory, status_hook, override_bandwidth = True )
                                    
                                
                            elif url_type == HC.URL_TYPE_POST and can_parse:
                                
                                # a pixiv mode=medium page has spawned a mode=manga page, so we need a new file_seed to go pursue that
                                
                                child_urls = [ desired_url ]
                                
                            else:
                                
                                raise HydrusExceptions.VetoException( 'Found a URL--' + desired_url + '--but could not understand/parse it!' )
                                
                            
                        else:
                            
                            child_urls = desired_urls
                            
                        
                        if len( child_urls ) > 0:
                            
                            child_file_seeds = []
                            
                            for child_url in child_urls:
                                
                                duplicate_file_seed = self.Duplicate() # inherits all urls and tags from here
                                
                                duplicate_file_seed.file_seed_data = child_url
                                
                                duplicate_file_seed.SetReferralURL( self.file_seed_data )
                                
                                if self._referral_url is not None:
                                    
                                    duplicate_file_seed.AddURL( self._referral_url )
                                    
                                
                                child_file_seeds.append( duplicate_file_seed )
                                
                            
                            try:
                                
                                my_index = file_seed_cache.GetFileSeedIndex( self )
                                
                                insertion_index = my_index + 1
                                
                            except:
                                
                                insertion_index = len( file_seed_cache )
                                
                            
                            num_urls_added = file_seed_cache.InsertFileSeeds( insertion_index, child_file_seeds )
                            
                            status = CC.STATUS_SUCCESSFUL_AND_NEW
                            note = 'Found ' + HydrusData.ToHumanInt( num_urls_added ) + ' new URLs.'
                            
                            self.SetStatus( status, note = note )
                            
                        
                    
                
            else:
                
                if should_download_file:
                    
                    did_substantial_work = True
                    
                    file_url = self.file_seed_data
                    
                    self.DownloadAndImportRawFile( file_url, file_import_options, network_job_factory, network_job_presentation_context_factory, status_hook )
                    
                
            
            did_substantial_work |= self.WriteContentUpdates( tag_import_options )
            
        except HydrusExceptions.ShutdownException:
            
            return False
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = str( e )
            
            self.SetStatus( status, note = note )
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                status_hook( 'cancelled!' )
                
                time.sleep( 2 )
                
            
        except HydrusExceptions.InsufficientCredentialsException:
            
            status = CC.STATUS_VETOED
            note = '403'
            
            self.SetStatus( status, note = note )
            
            status_hook( '403' )
            
            time.sleep( 2 )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_VETOED
            note = '404'
            
            self.SetStatus( status, note = note )
            
            status_hook( '404' )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            self.SetStatus( status, exception = e )
            
            status_hook( 'error!' )
            
            time.sleep( 3 )
            
        
        file_seed_cache.NotifyFileSeedsUpdated( ( self, ) )
        
        return did_substantial_work
        
    
    def WriteContentUpdates( self, tag_import_options = None ):
        
        did_work = False
        
        if self.status == CC.STATUS_ERROR:
            
            return did_work
            
        
        hash = self.GetHash()
        
        if hash is None:
            
            return did_work
            
        
        # changed this to say that urls alone are not 'did work' since all url results are doing this, and when they have no tags, they are usually superfast db hits anyway
        # better to scream through an 'already in db' import list that flicker
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        urls = set( self._urls )
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            urls.add( self.file_seed_data )
            
        
        if self._referral_url is not None:
            
            urls.add( self._referral_url )
            
        
        associable_urls = self._NormaliseAndFilterAssociableURLs( urls )
        
        if len( associable_urls ) > 0:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( associable_urls, ( hash, ) ) )
            
            service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].append( content_update )
            
        
        if tag_import_options is not None:
            
            in_inbox = HG.client_controller.Read( 'in_inbox', hash )
            
            for ( service_key, content_updates ) in tag_import_options.GetServiceKeysToContentUpdates( self.status, in_inbox, hash, set( self._tags ) ).items():
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
                did_work = True
                
            
        
        for ( service_key, content_updates ) in ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( ( hash, ), self._fixed_service_keys_to_tags ).items():
            
            service_keys_to_content_updates[ service_key ].extend( content_updates )
            
            did_work = True
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        return did_work
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED ] = FileSeed

class FileSeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE
    SERIALISABLE_NAME = 'Import File Status Cache'
    SERIALISABLE_VERSION = 8
    
    COMPACT_NUMBER = 250
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._file_seeds = HydrusSerialisable.SerialisableList()
        
        self._file_seeds_to_indices = {}
        
        self._file_seed_cache_key = HydrusData.GenerateKey()
        
        self._status_cache = None
        self._status_cache_generation_time = 0
        
        self._status_dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._file_seeds )
        
    
    def _GenerateStatus( self ):
        
        self._status_cache = GenerateStatusesToCountsStatus( self._GetStatusesToCounts() )
        self._status_cache_generation_time = HydrusData.GetNow()
        
        self._status_dirty = False
        
    
    def _GetFileSeeds( self, status = None ):
        
        if status is None:
            
            return list( self._file_seeds )
            
        else:
            
            return [ file_seed for file_seed in self._file_seeds if file_seed.status == status ]
            
        
    
    def _GetSerialisableInfo( self ):
        
        return self._file_seeds.GetSerialisableTuple()
        
    
    def _GetSourceTimestamp( self, file_seed ):
        
        source_timestamp = file_seed.source_time
        
        if source_timestamp is None:
            
            # decent fallback compromise
            # -30 since added and 'last check' timestamps are often the same, and this messes up calculations
            
            source_timestamp = file_seed.created - 30
            
        
        return source_timestamp
        
    
    def _GetStatusesToCounts( self ):
        
        statuses_to_counts = collections.Counter()
        
        for file_seed in self._file_seeds:
            
            statuses_to_counts[ file_seed.status ] += 1
            
        
        return statuses_to_counts
        
    
    def _HasFileSeed( self, file_seed ):
        
        search_file_seeds = file_seed.GetSearchFileSeeds()
        
        has_file_seed = True in ( search_file_seed in self._file_seeds_to_indices for search_file_seed in search_file_seeds )
        
        return has_file_seed
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            self._file_seeds = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
            
            self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
            
        
    
    def _SetStatusDirty( self ):
        
        self._status_dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( file_seed, file_seed_info ) in old_serialisable_info:
                
                if 'note' in file_seed_info:
                    
                    file_seed_info[ 'note' ] = str( file_seed_info[ 'note' ] )
                    
                
                new_serialisable_info.append( ( file_seed, file_seed_info ) )
                
            
            return ( 2, new_serialisable_info )
            
        
        if version in ( 2, 3 ):
            
            # gelbooru replaced their thumbnail links with this redirect spam
            # 'https://gelbooru.com/redirect.php?s=Ly9nZWxib29ydS5jb20vaW5kZXgucGhwP3BhZ2U9cG9zdCZzPXZpZXcmaWQ9MzY4ODA1OA=='
            
            # I missed some http ones here, so I've broadened the test and rescheduled it
            
            new_serialisable_info = []
            
            for ( file_seed, file_seed_info ) in old_serialisable_info:
                
                if 'gelbooru.com/redirect.php' in file_seed:
                    
                    continue
                    
                
                new_serialisable_info.append( ( file_seed, file_seed_info ) )
                
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            def ConvertRegularToRawURL( regular_url ):
                
                # convert this:
                # http://68.media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_500.jpg
                # to this:
                # http://68.media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_raw.jpg
                # the 500 part can be a bunch of stuff, including letters
                
                url_components = regular_url.split( '_' )
                
                last_component = url_components[ -1 ]
                
                ( number_gubbins, file_ext ) = last_component.split( '.' )
                
                raw_last_component = 'raw.' + file_ext
                
                url_components[ -1 ] = raw_last_component
                
                raw_url = '_'.join( url_components )
                
                return raw_url
                
            
            def Remove68Subdomain( long_url ):
                
                # sometimes the 68 subdomain gives a 404 on the raw url, so:
                
                # convert this:
                # http://68.media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_raw.jpg
                # to this:
                # http://media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_raw.jpg
                
                # I am not sure if it is always 68, but let's not assume
                
                ( scheme, rest ) = long_url.split( '://', 1 )
                
                if rest.startswith( 'media.tumblr.com' ):
                    
                    return long_url
                    
                
                ( gumpf, shorter_rest ) = rest.split( '.', 1 )
                
                shorter_url = scheme + '://' + shorter_rest
                
                return shorter_url
                
            
            new_serialisable_info = []
            
            good_file_seeds = set()
            
            for ( file_seed, file_seed_info ) in old_serialisable_info:
                
                try:
                    
                    parse = urllib.parse.urlparse( file_seed )
                    
                    if 'media.tumblr.com' in parse.netloc:
                        
                        file_seed = Remove68Subdomain( file_seed )
                        
                        file_seed = ConvertRegularToRawURL( file_seed )
                        
                        file_seed = ClientNetworkingDomain.ConvertHTTPToHTTPS( file_seed )
                        
                    
                    if 'pixiv.net' in parse.netloc:
                        
                        file_seed = ClientNetworkingDomain.ConvertHTTPToHTTPS( file_seed )
                        
                    
                    if file_seed in good_file_seeds: # we hit a dupe, so skip it
                        
                        continue
                        
                    
                except:
                    
                    pass
                    
                
                good_file_seeds.add( file_seed )
                
                new_serialisable_info.append( ( file_seed, file_seed_info ) )
                
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            new_serialisable_info = []
            
            for ( file_seed, file_seed_info ) in old_serialisable_info:
                
                file_seed_info[ 'source_timestamp' ] = None
                
                new_serialisable_info.append( ( file_seed, file_seed_info ) )
                
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            new_serialisable_info = []
            
            for ( file_seed, file_seed_info ) in old_serialisable_info:
                
                try:
                    
                    magic_phrase = '//media.tumblr.com'
                    replacement = '//data.tumblr.com'
                    
                    if magic_phrase in file_seed:
                        
                        file_seed = file_seed.replace( magic_phrase, replacement )
                        
                    
                except:
                    
                    pass
                    
                
                new_serialisable_info.append( ( file_seed, file_seed_info ) )
                
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            file_seeds = HydrusSerialisable.SerialisableList()
            
            for ( file_seed_text, file_seed_info ) in old_serialisable_info:
                
                if file_seed_text.startswith( 'http' ):
                    
                    file_seed_type = FILE_SEED_TYPE_URL
                    
                else:
                    
                    file_seed_type = FILE_SEED_TYPE_HDD
                    
                
                file_seed = FileSeed( file_seed_type, file_seed_text )
                
                file_seed.status = file_seed_info[ 'status' ]
                file_seed.created = file_seed_info[ 'added_timestamp' ]
                file_seed.modified = file_seed_info[ 'last_modified_timestamp' ]
                file_seed.source_time = file_seed_info[ 'source_timestamp' ]
                file_seed.note = file_seed_info[ 'note' ]
                
                file_seeds.append( file_seed )
                
            
            new_serialisable_info = file_seeds.GetSerialisableTuple()
            
            return ( 8, new_serialisable_info )
            
        
    
    def AddFileSeeds( self, file_seeds ):
        
        if len( file_seeds ) == 0:
            
            return 0 
            
        
        new_file_seeds = []
        
        with self._lock:
            
            for file_seed in file_seeds:
                
                if self._HasFileSeed( file_seed ):
                    
                    continue
                    
                
                file_seed.Normalise()
                
                new_file_seeds.append( file_seed )
                
                self._file_seeds.append( file_seed )
                
                self._file_seeds_to_indices[ file_seed ] = len( self._file_seeds ) - 1
                
            
            self._SetStatusDirty()
            
        
        self.NotifyFileSeedsUpdated( new_file_seeds )
        
        return len( new_file_seeds )
        
    
    def AdvanceFileSeed( self, file_seed ):
        
        with self._lock:
            
            if file_seed in self._file_seeds_to_indices:
                
                index = self._file_seeds_to_indices[ file_seed ]
                
                if index > 0:
                    
                    self._file_seeds.remove( file_seed )
                    
                    self._file_seeds.insert( index - 1, file_seed )
                    
                
                self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
                
            
        
        self.NotifyFileSeedsUpdated( ( file_seed, ) )
        
    
    def CanCompact( self, compact_before_this_source_time ):
        
        with self._lock:
            
            if len( self._file_seeds ) <= self.COMPACT_NUMBER:
                
                return False
                
            
            for file_seed in self._file_seeds[:-self.COMPACT_NUMBER]:
                
                if file_seed.status == CC.STATUS_UNKNOWN:
                    
                    continue
                    
                
                if self._GetSourceTimestamp( file_seed ) < compact_before_this_source_time:
                    
                    return True
                    
                
            
        
        return False
        
    
    def Compact( self, compact_before_this_source_time ):
        
        with self._lock:
            
            if len( self._file_seeds ) <= self.COMPACT_NUMBER:
                
                return
                
            
            new_file_seeds = HydrusSerialisable.SerialisableList()
            
            for file_seed in self._file_seeds[:-self.COMPACT_NUMBER]:
                
                still_to_do = file_seed.status == CC.STATUS_UNKNOWN
                still_relevant = self._GetSourceTimestamp( file_seed ) > compact_before_this_source_time
                
                if still_to_do or still_relevant:
                    
                    new_file_seeds.append( file_seed )
                    
                
            
            new_file_seeds.extend( self._file_seeds[-self.COMPACT_NUMBER:] )
            
            self._file_seeds = new_file_seeds
            self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
            
            self._SetStatusDirty()
            
        
    
    def DelayFileSeed( self, file_seed ):
        
        with self._lock:
            
            if file_seed in self._file_seeds_to_indices:
                
                index = self._file_seeds_to_indices[ file_seed ]
                
                if index < len( self._file_seeds ) - 1:
                    
                    self._file_seeds.remove( file_seed )
                    
                    self._file_seeds.insert( index + 1, file_seed )
                    
                
                self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
                
            
        
        self.NotifyFileSeedsUpdated( ( file_seed, ) )
        
    
    def GetEarliestSourceTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return None
                
            
            earliest_timestamp = min( ( self._GetSourceTimestamp( file_seed ) for file_seed in self._file_seeds ) )
            
        
        return earliest_timestamp
        
    
    def GetFileSeedCacheKey( self ):
        
        return self._file_seed_cache_key
        
    
    def GetFileSeedCount( self, status = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._file_seeds )
                
            else:
                
                for file_seed in self._file_seeds:
                    
                    if file_seed.status == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetFileSeeds( self, status = None ):
        
        with self._lock:
            
            return self._GetFileSeeds( status )
            
        
    
    def GetFileSeedIndex( self, file_seed ):
        
        with self._lock:
            
            return self._file_seeds_to_indices[ file_seed ]
            
        
    
    def GetHashes( self ):
        
        with self._lock:
            
            hashes = [ file_seed.GetHash() for file_seed in self._file_seeds if file_seed.HasHash() ]
            
        
        return hashes
        
    
    def GetLatestAddedTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( file_seed.created for file_seed in self._file_seeds ) )
            
        
        return latest_timestamp
        
    
    def GetLatestSourceTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetSourceTimestamp( file_seed ) for file_seed in self._file_seeds ) )
            
        
        return latest_timestamp
        
    
    def GetNextFileSeed( self, status ):
        
        with self._lock:
            
            for file_seed in self._file_seeds:
                
                if file_seed.status == status:
                    
                    return file_seed
                    
                
            
        
        return None
        
    
    def GetNumNewFilesSince( self, since ):
        
        num_files = 0
        
        with self._lock:
            
            for file_seed in self._file_seeds:
                
                source_timestamp = self._GetSourceTimestamp( file_seed )
                
                if source_timestamp >= since:
                    
                    num_files += 1
                    
                
            
        
        return num_files
        
    
    def GetPresentedHashes( self, file_import_options ):
        
        with self._lock:
            
            eligible_file_seeds = [ file_seed for file_seed in self._file_seeds if file_seed.HasHash() ]
            
            file_seed_hashes = [ file_seed.GetHash() for file_seed in eligible_file_seeds ]
            
            inbox_hashes = HG.client_controller.Read( 'in_inbox', file_seed_hashes )
            
            hashes = []
            
            for file_seed in eligible_file_seeds:
                
                hash = file_seed.GetHash()
                
                in_inbox = hash in inbox_hashes
                
                if file_seed.ShouldPresent( file_import_options, in_inbox = in_inbox ):
                    
                    hashes.append( hash )
                    
                
            
            return hashes
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache
            
        
    
    def GetStatusGenerationTime( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                return HydrusData.GetNow()
                
            
            return self._status_cache_generation_time
            
        
    
    def GetStatusesToCounts( self ):
        
        with self._lock:
            
            return self._GetStatusesToCounts()
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            ( status, simple_status, ( total_processed, total ) ) = self._status_cache
            
            return ( total_processed, total )
            
        
    
    def HasFileSeed( self, file_seed ):
        
        with self._lock:
            
            return self._HasFileSeed( file_seed )
            
        
    
    def InsertFileSeeds( self, index, file_seeds ):
        
        if len( file_seeds ) == 0:
            
            return 0 
            
        
        new_file_seeds = set()
        
        with self._lock:
            
            index = min( index, len( self._file_seeds ) )
            
            for file_seed in file_seeds:
                
                if self._HasFileSeed( file_seed ) or file_seed in new_file_seeds:
                    
                    continue
                    
                
                file_seed.Normalise()
                
                new_file_seeds.add( file_seed )
                
                self._file_seeds.insert( index, file_seed )
                
                index += 1
                
            
            self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
            
            self._SetStatusDirty()
            
        
        self.NotifyFileSeedsUpdated( new_file_seeds )
        
        return len( new_file_seeds )
        
    
    def NotifyFileSeedsUpdated( self, file_seeds ):
        
        with self._lock:
            
            self._SetStatusDirty()
            
        
        HG.client_controller.pub( 'file_seed_cache_file_seeds_updated', self._file_seed_cache_key, file_seeds )
        
    
    def RemoveFileSeeds( self, file_seeds ):
        
        with self._lock:
            
            file_seeds_to_delete = set( file_seeds )
            
            self._file_seeds = HydrusSerialisable.SerialisableList( [ file_seed for file_seed in self._file_seeds if file_seed not in file_seeds_to_delete ] )
            
            self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
            
            self._SetStatusDirty()
            
        
        self.NotifyFileSeedsUpdated( file_seeds_to_delete )
        
    
    def RemoveFileSeedsByStatus( self, statuses_to_remove ):
        
        with self._lock:
            
            file_seeds_to_delete = [ file_seed for file_seed in self._file_seeds if file_seed.status in statuses_to_remove ]
            
        
        self.RemoveFileSeeds( file_seeds_to_delete )
        
    
    def RemoveAllButUnknownFileSeeds( self ):
        
        with self._lock:
            
            file_seeds_to_delete = [ file_seed for file_seed in self._file_seeds if file_seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveFileSeeds( file_seeds_to_delete )
        
    
    def RetryFailures( self ):
        
        with self._lock:
            
            failed_file_seeds = self._GetFileSeeds( CC.STATUS_ERROR )
            
            for file_seed in failed_file_seeds:
                
                file_seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
        
        self.NotifyFileSeedsUpdated( failed_file_seeds )
        
    
    def RetryIgnored( self ):
        
        with self._lock:
            
            ignored_file_seeds = self._GetFileSeeds( CC.STATUS_VETOED )
            
            for file_seed in ignored_file_seeds:
                
                file_seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
        
        self.NotifyFileSeedsUpdated( ignored_file_seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            ( status, simple_status, ( total_processed, total ) ) = self._status_cache
            
            return total_processed < total
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE ] = FileSeedCache
