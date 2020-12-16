import collections
import itertools
import os
import random
import threading
import time
import traceback
import typing
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusFileHandling
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientImageHandling
from hydrus.client import ClientParsing
from hydrus.client import ClientPaths
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportOptions
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingDomain

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
        self._file_modified_timestamp = None
        
    
    def CheckIsGoodToImport( self ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job testing if good to import for file import options' )
            
        
        ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = self._file_info
        
        self._file_import_options.CheckFileIsValid( size, mime, width, height )
        
    
    def DoWork( self, status_hook = None ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job starting work.' )
            
        
        if status_hook is not None:
            
            status_hook( 'calculating pre-import status' )
            
        
        ( pre_import_status, hash, note ) = self.GenerateHashAndStatus()
        
        if self.IsNewToDB():
            
            if status_hook is not None:
                
                status_hook( 'generating metadata' )
                
            
            self.GenerateInfo()
            
            self.CheckIsGoodToImport()
            
            mime = self.GetMime()
            
            if status_hook is not None:
                
                status_hook( 'copying file' )
                
            
            HG.client_controller.client_files_manager.AddFile( hash, mime, self._temp_path, thumbnail_bytes = self._thumbnail_bytes )
            
            if status_hook is not None:
                
                status_hook( 'updating database' )
                
            
            ( import_status, note ) = HG.client_controller.WriteSynchronous( 'import_file', self )
            
        else:
            
            import_status = pre_import_status
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job is done, now publishing content updates' )
            
        
        self.PubsubContentUpdates()
        
        return ( import_status, hash, note )
        
    
    def GenerateHashAndStatus( self ):
        
        HydrusImageHandling.ConvertToPNGIfBMP( self._temp_path )
        
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
        
        ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = self._file_info
        
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
        
        self._file_modified_timestamp = HydrusFileHandling.GetFileModifiedTimestamp( self._temp_path )
        
    
    def GetExtraHashes( self ):
        
        return self._extra_hashes
        
    
    def GetFileImportOptions( self ):
        
        return self._file_import_options
        
    
    def GetFileInfo( self ):
        
        return self._file_info
        
    
    def GetFileModifiedTimestamp( self ):
        
        return self._file_modified_timestamp
        
    
    def GetHash( self ):
        
        return self._hash
        
    
    def GetMime( self ):
        
        ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = self._file_info
        
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
    SERIALISABLE_VERSION = 4
    
    def __init__( self, file_seed_type: int = None, file_seed_data: str = None ):
        
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
        
        self._external_filterable_tags = set()
        self._external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        self._urls = set()
        self._tags = set()
        self._hashes = {}
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FileSeed ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.file_seed_type, self.file_seed_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _CheckTagsVeto( self, tags, tag_import_options: ClientImportOptions.TagImportOptions ):
        
        tags_to_siblings = HG.client_controller.Read( 'tag_siblings_lookup', CC.COMBINED_TAG_SERVICE_KEY, tags )
        
        all_chain_tags = set( itertools.chain.from_iterable( tags_to_siblings.values() ) )
        
        tag_import_options.CheckTagsVeto( tags, all_chain_tags )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_external_filterable_tags = list( self._external_filterable_tags )
        serialisable_external_additional_service_keys_to_tags = self._external_additional_service_keys_to_tags.GetSerialisableTuple()
        
        serialisable_urls = list( self._urls )
        serialisable_tags = list( self._tags )
        serialisable_hashes = [ ( hash_type, hash.hex() ) for ( hash_type, hash ) in list(self._hashes.items()) if hash is not None ]
        
        return ( self.file_seed_type, self.file_seed_data, self.created, self.modified, self.source_time, self.status, self.note, self._referral_url, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.file_seed_type, self.file_seed_data, self.created, self.modified, self.source_time, self.status, self.note, self._referral_url, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes ) = serialisable_info
        
        self._external_filterable_tags = set( serialisable_external_filterable_tags )
        self._external_additional_service_keys_to_tags = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_external_additional_service_keys_to_tags )
        
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
        
    
    def _SetupTagImportOptions( self, given_tag_import_options: ClientImportOptions.TagImportOptions ) -> ClientImportOptions.TagImportOptions:
        
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
            
            external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
            serialisable_external_additional_service_keys_to_tags = external_additional_service_keys_to_tags.GetSerialisableTuple()
            
            new_serialisable_info = ( file_seed_type, file_seed_data, created, modified, source_time, status, note, referral_url, serialisable_external_additional_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( file_seed_type, file_seed_data, created, modified, source_time, status, note, referral_url, serialisable_external_additional_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes ) = old_serialisable_info
            
            external_filterable_tags = set()
            
            serialisable_external_filterable_tags = list( external_filterable_tags )
            
            new_serialisable_info = ( file_seed_type, file_seed_data, created, modified, source_time, status, note, referral_url, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, serialisable_urls, serialisable_tags, serialisable_hashes )
            
            return ( 4, new_serialisable_info )
            
        
    
    def AddParseResults( self, parse_results, file_import_options: ClientImportOptions.FileImportOptions ):
        
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
        
    
    def AddURL( self, url: str ):
        
        urls = ( url, )
        
        associable_urls = self._NormaliseAndFilterAssociableURLs( urls )
        
        associable_urls.discard( self.file_seed_data )
        
        self._urls.update( associable_urls )
        
    
    def CheckPreFetchMetadata( self, tag_import_options: ClientImportOptions.TagImportOptions ):
        
        self._CheckTagsVeto( self._tags, tag_import_options )
        
    
    def DownloadAndImportRawFile( self, file_url: str, file_import_options, network_job_factory, network_job_presentation_context_factory, status_hook, override_bandwidth = False ):
        
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
            
            self.Import( temp_path, file_import_options, status_hook = status_hook )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    def FetchPageMetadata( self, tag_import_options: ClientImportOptions.TagImportOptions ):
        
        pass
        
    
    def GetAPIInfoDict( self, simple: bool ):
        
        d = {}
        
        d[ 'import_data' ] = self.file_seed_data
        d[ 'created' ] = self.created
        d[ 'modified' ] = self.modified
        d[ 'source_time' ] = self.source_time
        d[ 'status' ] = self.status
        d[ 'note' ] = self.note
        
        return d
        
    
    def GetExampleNetworkJob( self, network_job_factory ):
        
        if self.IsAPostURL():
            
            post_url = self.file_seed_data
            
            try:
                
                ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
                
            except HydrusExceptions.URLClassException:
                
                url_to_check = post_url
                
            
        else:
            
            url_to_check = self.file_seed_data
            
        
        network_job = network_job_factory( 'GET', url_to_check )
        
        return network_job
        
    
    def GetHash( self ):
        
        if 'sha256' in self._hashes:
            
            return self._hashes[ 'sha256' ]
            
        
        return None
        
    
    def GetPreImportStatusPredictionHash( self, file_import_options: ClientImportOptions.FileImportOptions ):
        
        UNKNOWN_DEFAULT = ( CC.STATUS_UNKNOWN, None, '' )
        
        ( status, hash, note ) = UNKNOWN_DEFAULT
        
        if file_import_options.DoNotCheckHashesBeforeImporting():
            
            return ( status, hash, note )
            
        
        # hashes
        
        if status == CC.STATUS_UNKNOWN:
            
            for ( hash_type, found_hash ) in self._hashes.items():
                
                ( status, hash, note ) = HG.client_controller.Read( 'hash_status', hash_type, found_hash, prefix = 'hash recognised' )
                
                if status != CC.STATUS_UNKNOWN:
                    
                    break
                    
                
            
        
        if status == CC.STATUS_DELETED:
            
            if not file_import_options.ExcludesDeleted():
                
                ( status, hash, note ) = UNKNOWN_DEFAULT
                
            
        
        return ( status, hash, note )
        
    
    def GetPreImportStatusPredictionURL( self, file_import_options: ClientImportOptions.FileImportOptions, file_url = None ):
        
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
                                
                                media_result = HG.client_controller.Read( 'media_result', hash )
                                
                                this_files_urls = media_result.GetLocationsManager().GetURLs()
                                
                                for this_files_url in this_files_urls:
                                    
                                    if this_files_url != my_url:
                                        
                                        try:
                                            
                                            this_url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( this_files_url )
                                            
                                        except HydrusExceptions.URLClassException:
                                            
                                            continue
                                            
                                        
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
        
    
    def Import( self, temp_path: str, file_import_options: ClientImportOptions.FileImportOptions, status_hook = None ):
        
        file_import_job = FileImportJob( temp_path, file_import_options )
        
        ( status, hash, note ) = file_import_job.DoWork( status_hook = status_hook )
        
        self.SetStatus( status, note = note )
        self.SetHash( hash )
        
    
    def ImportPath( self, file_seed_cache: "FileSeedCache", file_import_options: ClientImportOptions.FileImportOptions, limited_mimes = None, status_hook = None ):
        
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
                    
                
                self.Import( temp_path, file_import_options, status_hook = status_hook )
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
            self.WriteContentUpdates()
            
        except HydrusExceptions.UnsupportedFileException as e:
            
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
            
            try:
                
                self.file_seed_data = HG.client_controller.network_engine.domain_manager.NormaliseURL( self.file_seed_data )
                
            except HydrusExceptions.URLClassException:
                
                pass
                
            
        
    
    def PredictPreImportStatus( self, file_import_options: ClientImportOptions.FileImportOptions, tag_import_options: ClientImportOptions.TagImportOptions, file_url = None ):
        
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
        
    
    def PresentToPage( self, page_key: bytes ):
        
        hash = self.GetHash()
        
        if hash is not None:
            
            media_result = HG.client_controller.Read( 'media_result', hash )
            
            HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
            
        
    
    def SetExternalAdditionalServiceKeysToTags( self, service_keys_to_tags ):
        
        self._external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags( service_keys_to_tags )
        
    
    def SetExternalFilterableTags( self, tags ):
        
        self._external_filterable_tags = set( tags )
        
    
    def SetHash( self, hash ):
        
        if hash is not None:
            
            self._hashes[ 'sha256' ] = hash
            
        
    
    def SetReferralURL( self, referral_url: str ):
        
        self._referral_url = referral_url
        
    
    def SetStatus( self, status: int, note: str = '', exception = None ):
        
        if exception is not None:
            
            first_line = str( exception ).split( os.linesep )[0]
            
            note = first_line + '\u2026 (Copy note to see full error)'
            note += os.linesep
            note += traceback.format_exc()
            
            HydrusData.Print( 'Error when processing {}!'.format( self.file_seed_data ) )
            HydrusData.Print( traceback.format_exc() )
            
        
        self.status = status
        self.note = note
        
        self._UpdateModified()
        
    
    def ShouldPresent( self, file_import_options: ClientImportOptions.FileImportOptions, in_inbox = None ):
        
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
        
    
    def WorkOnURL( self, file_seed_cache: "FileSeedCache", status_hook, network_job_factory, network_job_presentation_context_factory, file_import_options: ClientImportOptions.FileImportOptions, tag_import_options: ClientImportOptions.TagImportOptions ):
        
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
                    
                    actual_fetched_url = network_job.GetActualFetchedURL()
                    
                    if actual_fetched_url != url_to_check:
                        
                        ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( actual_fetched_url )
                        
                        if url_type == HC.URL_TYPE_POST and can_parse:
                            
                            post_url = actual_fetched_url
                            
                            ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
                            
                        
                    
                    parsing_context = {}
                    
                    parsing_context[ 'post_url' ] = post_url
                    parsing_context[ 'url' ] = url_to_check
                    
                    all_parse_results = parser.Parse( parsing_context, parsing_text )
                    
                    if len( all_parse_results ) == 0:
                        
                        it_was_a_real_file = False
                        
                        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                        
                        try:
                            
                            with open( temp_path, 'wb' ) as f:
                                
                                f.write( network_job.GetContentBytes() )
                                
                            
                            mime = HydrusFileHandling.GetMime( temp_path )
                            
                            if mime in HC.ALLOWED_MIMES:
                                
                                it_was_a_real_file = True
                                
                                status_hook( 'page was actually a file, trying to import' )
                                
                                self.Import( temp_path, file_import_options, status_hook = status_hook )
                                
                            
                        except:
                            
                            pass # in this special occasion, we will swallow the error
                            
                        finally:
                            
                            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                            
                        
                        if not it_was_a_real_file:
                            
                            raise HydrusExceptions.VetoException( 'The parser found nothing in the document, nor did it seem to be an importable file!' )
                            
                        
                    elif len( all_parse_results ) > 1:
                        
                        # multiple child urls generated by a subsidiary page parser
                        
                        file_seeds = ClientImporting.ConvertAllParseResultsToFileSeeds( all_parse_results, self.file_seed_data, file_import_options )
                        
                        for file_seed in file_seeds:
                            
                            file_seed.SetExternalFilterableTags( self._external_filterable_tags )
                            file_seed.SetExternalAdditionalServiceKeysToTags( self._external_additional_service_keys_to_tags )
                            
                            file_seed._urls.update( self._urls )
                            file_seed._tags.update( self._tags )
                            
                        
                        try:
                            
                            my_index = file_seed_cache.GetFileSeedIndex( self )
                            
                            insertion_index = my_index + 1
                            
                        except:
                            
                            insertion_index = len( file_seed_cache )
                            
                        
                        num_urls_added = file_seed_cache.InsertFileSeeds( insertion_index, file_seeds )
                        
                        status = CC.STATUS_SUCCESSFUL_AND_NEW
                        note = 'Found {} new URLs.'.format( HydrusData.ToHumanInt( num_urls_added ) )
                        
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
                                
                                raise HydrusExceptions.VetoException( 'Found a URL--{}--but could not understand/parse it!'.format( desired_url ) )
                                
                            
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
                            note = 'Found {} new URLs.'.format( HydrusData.ToHumanInt( num_urls_added ) )
                            
                            self.SetStatus( status, note = note )
                            
                        
                    
                
            else:
                
                if should_download_file:
                    
                    self.CheckPreFetchMetadata( tag_import_options )
                    
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
        
    
    def WriteContentUpdates( self, tag_import_options: typing.Optional[ ClientImportOptions.TagImportOptions ] = None ):
        
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
            
        
        if tag_import_options is None:
            
            for ( service_key, content_updates ) in ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( ( hash, ), self._external_additional_service_keys_to_tags ).items():
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
                did_work = True
                
            
        else:
            
            media_result = HG.client_controller.Read( 'media_result', hash )
            
            for ( service_key, content_updates ) in tag_import_options.GetServiceKeysToContentUpdates( self.status, media_result, set( self._tags ), external_filterable_tags = self._external_filterable_tags, external_additional_service_keys_to_tags = self._external_additional_service_keys_to_tags ).items():
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
                did_work = True
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        return did_work
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED ] = FileSeed

class FileSeedCacheStatus( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE_STATUS
    SERIALISABLE_NAME = 'Import File Status Cache Status'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        self._generation_time = HydrusData.GetNow()
        self._statuses_to_counts = collections.Counter()
        self._latest_added_time = 0
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_statuses_to_counts = list( self._statuses_to_counts.items() )
        
        return ( self._generation_time, serialisable_statuses_to_counts, self._latest_added_time )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._generation_time, serialisable_statuses_to_counts, self._latest_added_time ) = serialisable_info
        
        self._statuses_to_counts = collections.Counter()
        
        self._statuses_to_counts.update( dict( serialisable_statuses_to_counts ) )
        
    
    def GetFileSeedCount( self, status: typing.Optional[ int ] = None ) -> int:
        
        if status is None:
            
            return sum( self._statuses_to_counts.values() )
            
        else:
            
            return self._statuses_to_counts[ status ]
            
        
    
    def GetGenerationTime( self ) -> int:
        
        return self._generation_time
        
    
    def GetLatestAddedTime( self ) -> int:
        
        return self._latest_added_time
        
    
    def GetStatusText( self, simple = False ) -> str:
        
        num_successful_and_new = self._statuses_to_counts[ CC.STATUS_SUCCESSFUL_AND_NEW ]
        num_successful_but_redundant = self._statuses_to_counts[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ]
        num_ignored = self._statuses_to_counts[ CC.STATUS_VETOED ]
        num_deleted = self._statuses_to_counts[ CC.STATUS_DELETED ]
        num_failed = self._statuses_to_counts[ CC.STATUS_ERROR ]
        num_skipped = self._statuses_to_counts[ CC.STATUS_SKIPPED ]
        num_unknown = self._statuses_to_counts[ CC.STATUS_UNKNOWN ]
        
        if simple:
            
            total = sum( self._statuses_to_counts.values() )
            
            total_processed = total - num_unknown
            
            #
            
            status_text = ''
            
            if total > 0:
                
                if num_unknown > 0:
                    
                    status_text += HydrusData.ConvertValueRangeToPrettyString( total_processed, total )
                    
                else:
                    
                    status_text += HydrusData.ToHumanInt( total_processed )
                    
                
                show_new_on_file_seed_short_summary = HG.client_controller.new_options.GetBoolean( 'show_new_on_file_seed_short_summary' )
                
                if show_new_on_file_seed_short_summary and num_successful_and_new:
                    
                    status_text += ' - {}N'.format( HydrusData.ToHumanInt( num_successful_and_new ) )
                    
                
                simple_status_strings = []
                
                if num_ignored > 0:
                    
                    simple_status_strings.append( '{}Ig'.format( HydrusData.ToHumanInt( num_ignored ) ) )
                    
                
                show_deleted_on_file_seed_short_summary = HG.client_controller.new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' )
                
                if show_deleted_on_file_seed_short_summary and num_deleted > 0:
                    
                    simple_status_strings.append( '{}D'.format( HydrusData.ToHumanInt( num_deleted ) ) )
                    
                
                if num_failed > 0:
                    
                    simple_status_strings.append( '{}F'.format( HydrusData.ToHumanInt( num_failed ) ) )
                    
                
                if num_skipped > 0:
                    
                    simple_status_strings.append( '{}S'.format( HydrusData.ToHumanInt( num_skipped ) ) )
                    
                
                if len( simple_status_strings ) > 0:
                    
                    status_text += ' - {}'.format( ''.join( simple_status_strings ) )
                    
                
            
        else:
            
            status_strings = []
            
            num_successful = num_successful_and_new + num_successful_but_redundant
            
            if num_successful > 0:
                
                s = '{} successful'.format( HydrusData.ToHumanInt( num_successful ) )
                
                if num_successful_and_new > 0:
                    
                    if num_successful_but_redundant > 0:
                        
                        s += ' ({} already in db)'.format( HydrusData.ToHumanInt( num_successful_but_redundant ) )
                        
                    
                else:
                    
                    s += ' (all already in db)'
                    
                
                status_strings.append( s )
                
            
            if num_ignored > 0:
                
                status_strings.append( '{} ignored'.format( HydrusData.ToHumanInt( num_ignored ) ) )
                
            
            if num_deleted > 0:
                
                status_strings.append( '{} previously deleted'.format( HydrusData.ToHumanInt( num_deleted ) ) )
                
            
            if num_failed > 0:
                
                status_strings.append( '{} failed'.format( HydrusData.ToHumanInt( num_failed ) ) )
                
            
            if num_skipped > 0:
                
                status_strings.append( '{} skipped'.format( HydrusData.ToHumanInt( num_skipped ) ) )
                
            
            status_text = ', '.join( status_strings )
            
        
        return status_text
        
    
    def GetStatusesToCounts( self ) -> typing.Mapping[ int, int ]:
        
        return self._statuses_to_counts
        
    
    def GetValueRange( self ) -> typing.Tuple[ int, int ]:
        
        total = sum( self._statuses_to_counts.values() )
        
        num_unknown = self._statuses_to_counts[ CC.STATUS_UNKNOWN ]
        
        total_processed = total - num_unknown
        
        return ( total_processed, total )
        
    
    def HasWorkToDo( self ):
        
        ( num_done, num_total ) = self.GetValueRange()
        
        return num_done < num_total
        
    
    def Merge( self, file_seed_cache_status: "FileSeedCacheStatus" ):
        
        self._latest_added_time = max( self._latest_added_time, file_seed_cache_status.GetLatestAddedTime() )
        self._statuses_to_counts.update( file_seed_cache_status.GetStatusesToCounts() )
        
    
    def SetStatusesToCounts( self, statuses_to_counts: typing.Mapping[ int, int ] ):
        
        self._statuses_to_counts = collections.Counter()
        
        self._statuses_to_counts.update( statuses_to_counts )
        
    
    def SetLatestAddedTime( self, latest_added_time: int ):
        
        self._latest_added_time = latest_added_time
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE_STATUS ] = FileSeedCacheStatus

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
        
        self._status_cache = FileSeedCacheStatus()
        
        self._status_dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._file_seeds )
        
    
    def _GenerateStatus( self ):
        
        fscs = FileSeedCacheStatus()
        
        fscs.SetLatestAddedTime( self._GetLatestAddedTime() )
        fscs.SetStatusesToCounts( self._GetStatusesToCounts() )
        
        self._status_cache = fscs
        
        self._status_dirty = False
        
    
    def _GetFileSeeds( self, status: int = None ):
        
        if status is None:
            
            return list( self._file_seeds )
            
        else:
            
            return [ file_seed for file_seed in self._file_seeds if file_seed.status == status ]
            
        
    
    def _GetLatestAddedTime( self ):
        
        if len( self._file_seeds ) == 0:
            
            latest_timestamp = 0
            
        else:
            
            latest_timestamp = max( ( file_seed.created for file_seed in self._file_seeds ) )
            
        
        return latest_timestamp
        
    
    def _GetNextFileSeed( self, status: int ) -> typing.Optional[ FileSeed ]:
        
        for file_seed in self._file_seeds:
            
            if file_seed.status == status:
                
                return file_seed
                
            
        
        return None
        
    
    def _GetSerialisableInfo( self ):
        
        return self._file_seeds.GetSerialisableTuple()
        
    
    def _GetSourceTimestamp( self, file_seed: FileSeed ):
        
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
        
    
    def _HasFileSeed( self, file_seed: FileSeed ):
        
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
                
                raw_last_component = 'raw.{}'.format( file_ext )
                
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
                
                shorter_url = '{}://{}'.format( scheme, shorter_rest )
                
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
            
        
    
    def AddFileSeeds( self, file_seeds: typing.Collection[ FileSeed ] ):
        
        if len( file_seeds ) == 0:
            
            return 0 
            
        
        new_file_seeds = []
        
        with self._lock:
            
            for file_seed in file_seeds:
                
                if self._HasFileSeed( file_seed ):
                    
                    continue
                    
                
                try:
                    
                    file_seed.Normalise()
                    
                except HydrusExceptions.URLClassException:
                    
                    # this is some borked 'https://' url that makes no sense
                    
                    continue
                    
                
                new_file_seeds.append( file_seed )
                
                self._file_seeds.append( file_seed )
                
                self._file_seeds_to_indices[ file_seed ] = len( self._file_seeds ) - 1
                
            
            self._SetStatusDirty()
            
        
        self.NotifyFileSeedsUpdated( new_file_seeds )
        
        return len( new_file_seeds )
        
    
    def AdvanceFileSeed( self, file_seed: FileSeed ):
        
        with self._lock:
            
            if file_seed in self._file_seeds_to_indices:
                
                index = self._file_seeds_to_indices[ file_seed ]
                
                if index > 0:
                    
                    self._file_seeds.remove( file_seed )
                    
                    self._file_seeds.insert( index - 1, file_seed )
                    
                
                self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
                
            
        
        self.NotifyFileSeedsUpdated( ( file_seed, ) )
        
    
    def CanCompact( self, compact_before_this_source_time: int ):
        
        with self._lock:
            
            if len( self._file_seeds ) <= self.COMPACT_NUMBER:
                
                return False
                
            
            for file_seed in self._file_seeds[:-self.COMPACT_NUMBER]:
                
                if file_seed.status == CC.STATUS_UNKNOWN:
                    
                    continue
                    
                
                if self._GetSourceTimestamp( file_seed ) < compact_before_this_source_time:
                    
                    return True
                    
                
            
        
        return False
        
    
    def Compact( self, compact_before_this_source_time: int ):
        
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
            
        
    
    def DelayFileSeed( self, file_seed: FileSeed ):
        
        with self._lock:
            
            if file_seed in self._file_seeds_to_indices:
                
                index = self._file_seeds_to_indices[ file_seed ]
                
                if index < len( self._file_seeds ) - 1:
                    
                    self._file_seeds.remove( file_seed )
                    
                    self._file_seeds.insert( index + 1, file_seed )
                    
                
                self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
                
            
        
        self.NotifyFileSeedsUpdated( ( file_seed, ) )
        
    
    def GetAPIInfoDict( self, simple: bool ):
        
        with self._lock:
            
            d = {}
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            d[ 'status' ] = self._status_cache.GetStatusText()
            d[ 'simple_status' ] = self._status_cache.GetStatusText( simple = True )
            
            ( num_done, num_total ) = self._status_cache.GetValueRange()
            
            d[ 'total_processed' ] = num_done
            d[ 'total_to_process' ] = num_total
            
            if not simple:
                
                d[ 'import_items' ] = [ file_seed.GetAPIInfoDict( simple ) for file_seed in self._file_seeds ]
                
            
            return d
            
        
    
    def GetEarliestSourceTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return None
                
            
            earliest_timestamp = min( ( self._GetSourceTimestamp( file_seed ) for file_seed in self._file_seeds ) )
            
        
        return earliest_timestamp
        
    
    def GetExampleFileSeed( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return None
                
            else:
                
                example_seed = self._GetNextFileSeed( CC.STATUS_UNKNOWN )
                
                if example_seed is None:
                    
                    example_seed = random.choice( self._file_seeds[-10:] )
                    
                
                if example_seed.file_seed_type == FILE_SEED_TYPE_HDD:
                    
                    return None
                    
                else:
                    
                    return example_seed
                    
                
            
        
    
    def GetFileSeedCacheKey( self ):
        
        return self._file_seed_cache_key
        
    
    def GetFileSeedCount( self, status: int = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._file_seeds )
                
            else:
                
                for file_seed in self._file_seeds:
                    
                    if file_seed.status == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetFileSeeds( self, status: int = None ):
        
        with self._lock:
            
            return self._GetFileSeeds( status )
            
        
    
    def GetFileSeedIndex( self, file_seed: FileSeed ):
        
        with self._lock:
            
            return self._file_seeds_to_indices[ file_seed ]
            
        
    
    def GetHashes( self ):
        
        with self._lock:
            
            hashes = [ file_seed.GetHash() for file_seed in self._file_seeds if file_seed.HasHash() ]
            
        
        return hashes
        
    
    def GetLatestSourceTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetSourceTimestamp( file_seed ) for file_seed in self._file_seeds ) )
            
        
        return latest_timestamp
        
    
    def GetNextFileSeed( self, status: int ):
        
        with self._lock:
            
            return self._GetNextFileSeed( status )
            
        
    
    def GetNumNewFilesSince( self, since: int ):
        
        num_files = 0
        
        with self._lock:
            
            for file_seed in self._file_seeds:
                
                source_timestamp = self._GetSourceTimestamp( file_seed )
                
                if source_timestamp >= since:
                    
                    num_files += 1
                    
                
            
        
        return num_files
        
    
    def GetPresentedHashes( self, file_import_options: ClientImportOptions.FileImportOptions ):
        
        with self._lock:
            
            eligible_file_seeds = [ file_seed for file_seed in self._file_seeds if file_seed.HasHash() ]
            
        
        file_seed_hashes = [ file_seed.GetHash() for file_seed in eligible_file_seeds ]
        
        if len( file_seed_hashes ) > 0:
            
            inbox_hashes = HG.client_controller.Read( 'in_inbox', file_seed_hashes )
            
        else:
            
            inbox_hashes = set()
            
        
        hashes = []
        hashes_seen = set()
        
        for file_seed in eligible_file_seeds:
            
            hash = file_seed.GetHash()
            
            if hash in hashes_seen:
                
                continue
                
            
            in_inbox = hash in inbox_hashes
            
            if file_seed.ShouldPresent( file_import_options, in_inbox = in_inbox ):
                
                hashes.append( hash )
                hashes_seen.add( hash )
                
            
        
        return hashes
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache.GetValueRange()
            
        
    
    def HasFileSeed( self, file_seed: FileSeed ):
        
        with self._lock:
            
            return self._HasFileSeed( file_seed )
            
        
    
    def InsertFileSeeds( self, index: int, file_seeds: typing.Collection[ FileSeed ] ):
        
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
        
    
    def NotifyFileSeedsUpdated( self, file_seeds: typing.Collection[ FileSeed ] ):
        
        with self._lock:
            
            self._SetStatusDirty()
            
        
        HG.client_controller.pub( 'file_seed_cache_file_seeds_updated', self._file_seed_cache_key, file_seeds )
        
    
    def RemoveFileSeeds( self, file_seeds: typing.Iterable[ FileSeed ] ):
        
        with self._lock:
            
            file_seeds_to_delete = set( file_seeds )
            
            self._file_seeds = HydrusSerialisable.SerialisableList( [ file_seed for file_seed in self._file_seeds if file_seed not in file_seeds_to_delete ] )
            
            self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
            
            self._SetStatusDirty()
            
        
        self.NotifyFileSeedsUpdated( file_seeds_to_delete )
        
    
    def RemoveFileSeedsByStatus( self, statuses_to_remove: typing.Collection[ int ] ):
        
        with self._lock:
            
            file_seeds_to_delete = [ file_seed for file_seed in self._file_seeds if file_seed.status in statuses_to_remove ]
            
        
        self.RemoveFileSeeds( file_seeds_to_delete )
        
    
    def RemoveAllButUnknownFileSeeds( self ):
        
        with self._lock:
            
            file_seeds_to_delete = [ file_seed for file_seed in self._file_seeds if file_seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveFileSeeds( file_seeds_to_delete )
        
    
    def RetryFailed( self ):
        
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
                
            
            return self._status_cache.HasWorkToDo()
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE ] = FileSeedCache

def GenerateFileSeedCachesStatus( file_seed_caches: typing.Iterable[ FileSeedCache ] ):
    
    fscs = FileSeedCacheStatus()
    
    for file_seed_cache in file_seed_caches:
        
        fscs.Merge( file_seed_cache.GetStatus() )
        
    
    return fscs
    
