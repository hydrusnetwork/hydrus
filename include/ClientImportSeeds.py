import ClientConstants as CC
import ClientImageHandling
import ClientNetworkingDomain
import ClientParsing
import ClientPaths
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusGlobals as HG
import HydrusPaths
import HydrusSerialisable
import HydrusTags
import os
import threading
import time
import traceback
import urlparse

def GenerateSeedCacheStatus( statuses_to_counts ):
    
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
        
        s = HydrusData.ConvertIntToPrettyString( num_successful ) + ' successful'
        
        if num_successful_and_new > 0:
            
            if num_successful_but_redundant > 0:
                
                s += ' (' + HydrusData.ConvertIntToPrettyString( num_successful_but_redundant ) + ' already in db)'
                
            
        else:
            
            s += ' (all already in db)'
            
        
        status_strings.append( s )
        
    
    if num_ignored > 0:
        
        status_strings.append( HydrusData.ConvertIntToPrettyString( num_ignored ) + ' ignored' )
        
    
    if num_deleted > 0:
        
        status_strings.append( HydrusData.ConvertIntToPrettyString( num_deleted ) + ' previously deleted' )
        
    
    if num_failed > 0:
        
        status_strings.append( HydrusData.ConvertIntToPrettyString( num_failed ) + ' failed' )
        
    
    if num_skipped > 0:
        
        status_strings.append( HydrusData.ConvertIntToPrettyString( num_skipped ) + ' skipped' )
        
    
    status = ', '.join( status_strings )
    
    total = sum( statuses_to_counts.values() )
    
    total_processed = total - num_unknown
    
    return ( status, ( total_processed, total ) )
    
class FileImportJob( object ):
    
    def __init__( self, temp_path, file_import_options = None ):
        
        if file_import_options is None:
            
            file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
            
        
        self._temp_path = temp_path
        self._file_import_options = file_import_options
        
        self._hash = None
        self._pre_import_status = None
        
        self._file_info = None
        self._thumbnail = None
        self._phashes = None
        self._extra_hashes = None
        
    
    def CheckIsGoodToImport( self ):
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        self._file_import_options.CheckFileIsValid( size, mime, width, height )
        
    
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
        
    
    def GetTempPathAndThumbnail( self ):
        
        return ( self._temp_path, self._thumbnail )
        
    
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
        
    
    def GenerateHashAndStatus( self ):
        
        HydrusImageHandling.ConvertToPngIfBmp( self._temp_path )
        
        self._hash = HydrusFileHandling.GetHashFromPath( self._temp_path )
        
        ( self._pre_import_status, hash, note ) = HG.client_controller.Read( 'hash_status', 'sha256', self._hash, prefix = 'recognised during import' )
        
        return ( self._pre_import_status, self._hash, note )
        
    
    def GenerateInfo( self ):
        
        mime = HydrusFileHandling.GetMime( self._temp_path )
        
        new_options = HG.client_controller.new_options
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and not self._file_import_options.AllowsDecompressionBombs():
            
            if HydrusImageHandling.IsDecompressionBomb( self._temp_path ):
                
                raise HydrusExceptions.DecompressionBombException( 'Image seems to be a Decompression Bomb!' )
                
            
        
        self._file_info = HydrusFileHandling.GetFileInfo( self._temp_path, mime )
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            percentage_in = HG.client_controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
            
            self._thumbnail = HydrusFileHandling.GenerateThumbnail( self._temp_path, mime, percentage_in = percentage_in )
            
        
        if mime in HC.MIMES_WE_CAN_PHASH:
            
            self._phashes = ClientImageHandling.GenerateShapePerceptualHashes( self._temp_path, mime )
            
        
        self._extra_hashes = HydrusFileHandling.GetExtraHashesFromPath( self._temp_path )
        
    
SEED_TYPE_HDD = 0
SEED_TYPE_URL = 1

class Seed( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED
    SERIALISABLE_NAME = 'File Import'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, seed_type = None, seed_data = None ):
        
        if seed_type is None:
            
            seed_type = SEED_TYPE_URL
            
        
        if seed_data is None:
            
            seed_data = 'https://big-guys.4u/monica_lewinsky_hott.tiff.exe.vbs'
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.seed_type = seed_type
        self.seed_data = seed_data
        
        self.created = HydrusData.GetNow()
        self.modified = self.created
        self.source_time = None
        self.status = CC.STATUS_UNKNOWN
        self.note = ''
        
        self._referral_url = None
        
        self._urls = set()
        self._tags = set()
        self._hashes = {}
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.seed_type, self.seed_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _CheckTagsBlacklist( self, tags, tag_import_options ):
        
        tag_import_options.CheckBlacklist( tags )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_urls = list( self._urls )
        serialisable_tags = list( self._tags )
        serialisable_hashes = [ ( hash_type, hash.encode( 'hex' ) ) for ( hash_type, hash ) in self._hashes.items() if hash is not None ]
        
        return ( self.seed_type, self.seed_data, self.created, self.modified, self.source_time, self.status, self.note, self._referral_url, serialisable_urls, serialisable_tags, serialisable_hashes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.seed_type, self.seed_data, self.created, self.modified, self.source_time, self.status, self.note, self._referral_url, serialisable_urls, serialisable_tags, serialisable_hashes ) = serialisable_info
        
        self._urls = set( serialisable_urls )
        self._tags = set( serialisable_tags )
        self._hashes = { hash_type : encoded_hash.decode( 'hex' ) for ( hash_type, encoded_hash ) in serialisable_hashes if encoded_hash is not None }
        
    
    def _NormaliseAndFilterAssociableURLs( self, urls ):
        
        normalised_urls = { HG.client_controller.network_engine.domain_manager.NormaliseURL( url ) for url in urls }
        
        associable_urls = { url for url in normalised_urls if HG.client_controller.network_engine.domain_manager.ShouldAssociateURLWithFiles( url ) }
        
        return associable_urls
        
    
    def _UpdateModified( self ):
        
        self.modified = HydrusData.GetNow()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( seed_type, seed_data, created, modified, source_time, status, note, serialisable_urls, serialisable_tags, serialisable_hashes ) = old_serialisable_info
            
            referral_url = None
            
            new_serialisable_info = ( seed_type, seed_data, created, modified, source_time, status, note, referral_url, serialisable_urls, serialisable_tags, serialisable_hashes )
            
            return ( 2, new_serialisable_info )
            
        
    
    def AddParseResults( self, parse_results ):
        
        for ( hash_type, hash ) in ClientParsing.GetHashesFromParseResults( parse_results ):
            
            if hash_type not in self._hashes:
                
                self._hashes[ hash_type ] = hash
                
            
        
        urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_SOURCE, ) )
        
        associable_urls = self._NormaliseAndFilterAssociableURLs( urls )
        
        associable_urls.discard( self.seed_data )
        
        self._urls.update( associable_urls )
        
        tags = ClientParsing.GetTagsFromParseResults( parse_results )
        
        self._tags.update( tags )
        
        source_timestamp = ClientParsing.GetTimestampFromParseResults( parse_results, HC.TIMESTAMP_TYPE_SOURCE )
        
        source_timestamp = min( HydrusData.GetNow() - 30, source_timestamp )
        
        if source_timestamp is not None:
            
            self.source_time = source_timestamp
            
        
        self._UpdateModified()
        
    
    def AddTags( self, tags ):
        
        tags = HydrusTags.CleanTags( tags )
        
        self._tags.update( tags )
        
        self._UpdateModified()
        
    
    def AddURL( self, url ):
        
        urls = ( url, )
        
        associable_urls = self._NormaliseAndFilterAssociableURLs( urls )
        
        associable_urls.discard( self.seed_data )
        
        self._urls.update( associable_urls )
        
    
    def CheckPreFetchMetadata( self, tag_import_options ):
        
        self._CheckTagsBlacklist( self._tags, tag_import_options )
        
    
    def DownloadAndImportRawFile( self, file_url, file_import_options, network_job_factory, network_job_presentation_context_factory ):
        
        self.AddURL( file_url )
        
        ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
        
        try:
            
            if self.seed_data != file_url:
                
                referral_url = self.seed_data
                
            else:
                
                referral_url = self._referral_url
                
            
            network_job = network_job_factory( 'GET', file_url, temp_path = temp_path, referral_url = referral_url )
            
            network_job.SetFileImportOptions( file_import_options )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            with network_job_presentation_context_factory( network_job ) as njpc:
                
                network_job.WaitUntilDone()
                
            
            self.Import( temp_path, file_import_options )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    def FetchPageMetadata( self, tag_import_options ):
        
        pass
        
    
    def PredictPreImportStatus( self, file_import_options, file_url = None ):
        
        if self.status != CC.STATUS_UNKNOWN:
            
            return
            
        
        UNKNOWN_DEFAULT = ( CC.STATUS_UNKNOWN, None, '' )
        
        ( status, hash, note ) = UNKNOWN_DEFAULT
        
        # urls
        
        urls = set( self._urls )
        
        if file_url is not None:
            
            urls.add( file_url )
            
        
        if self.seed_type == SEED_TYPE_URL:
            
            urls.add( self.seed_data )
            
        
        unrecognised_url_results = set()
        
        for url in urls:
            
            if HG.client_controller.network_engine.domain_manager.URLCanReferToMultipleFiles( url ):
                
                continue
                
            
            # we now only trust url-matched single urls and the post/file urls
            # trusting unmatched source urls was too much of a hassle with too many boorus providing bad source urls like user account pages
            
            if HG.client_controller.network_engine.domain_manager.URLDefinitelyRefersToOneFile( url ) or url in ( self.seed_data, file_url ):
                
                results = HG.client_controller.Read( 'url_statuses', url )
                
                if len( results ) == 0: # if no match found, no useful data discovered
                    
                    continue
                    
                elif len( results ) > 1: # if more than one file claims this url, it cannot be relied on to guess the file
                    
                    continue
                    
                else: # i.e. 1 match found
                    
                    ( status, hash, note ) = results[0]
                    
                    if status != CC.STATUS_UNKNOWN:
                        
                        break # if a known one-file url gives a single clear result, that result is reliable
                        
                    
                
            
        
        # hashes
        
        if status == CC.STATUS_UNKNOWN:
            
            for ( hash_type, found_hash ) in self._hashes.items():
                
                ( status, hash, note ) = HG.client_controller.Read( 'hash_status', hash_type, found_hash )
                
                if status != CC.STATUS_UNKNOWN:
                    
                    break
                    
                
            
        
        #
        
        if status == CC.STATUS_DELETED:
            
            if not file_import_options.ExcludesDeleted():
                
                status = CC.STATUS_UNKNOWN
                note = ''
                
            
        
        self.status = status
        
        if hash is not None:
            
            self._hashes[ 'sha256' ] = hash
            
        
        self.note = note
        
        self._UpdateModified()
        
    
    def GetHash( self ):
        
        if 'sha256' in self._hashes:
            
            return self._hashes[ 'sha256' ]
            
        
        return None
        
    
    def GetSearchSeeds( self ):
        
        if self.seed_type == SEED_TYPE_URL:
            
            search_urls = ClientNetworkingDomain.GetSearchURLs( self.seed_data )
            
            search_seeds = [ Seed( SEED_TYPE_URL, search_url ) for search_url in search_urls ]
            
        else:
            
            search_seeds = [ self ]
            
        
        return search_seeds
        
    
    def HasHash( self ):
        
        return self.GetHash() is not None
        
    
    def Import( self, temp_path, file_import_options ):
        
        file_import_job = FileImportJob( temp_path, file_import_options )
        
        ( status, hash, note ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
        
        self.SetStatus( status, note = note )
        self.SetHash( hash )
        
    
    def ImportPath( self, file_import_options ):
        
        if self.seed_type != SEED_TYPE_HDD:
            
            raise Exception( 'Attempted to import as a path, but I do not think I am a path!' )
            
        
        ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
        
        try:
            
            path = self.seed_data
            
            copied = HydrusPaths.MirrorFile( path, temp_path )
            
            if not copied:
                
                raise Exception( 'File failed to copy to temp path--see log for error.' )
                
            
            self.Import( temp_path, file_import_options )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    def IsAPostURL( self ):
        
        if self.seed_type == SEED_TYPE_URL:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.seed_data )
            
            if url_type == HC.URL_TYPE_POST:
                
                return True
                
            
        
        return False
        
    
    def Normalise( self ):
        
        if self.seed_type == SEED_TYPE_URL:
            
            self.seed_data = HG.client_controller.network_engine.domain_manager.NormaliseURL( self.seed_data )
            
        
    
    def PresentToPage( self, page_key ):
        
        hash = self.GetHash()
        
        if hash is not None:
            
            ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
            
            HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
            
        
    
    def SetHash( self, hash ):
        
        if hash is not None:
            
            self._hashes[ 'sha256' ] = hash
            
        
    
    def SetReferralURL( self, referral_url ):
        
        self._referral_url = referral_url
        
    
    def SetStatus( self, status, note = '', exception = None ):
        
        if exception is not None:
            
            first_line = HydrusData.ToUnicode( exception ).split( os.linesep )[0]
            
            note = first_line + u'\u2026 (Copy note to see full error)'
            note += os.linesep
            note += HydrusData.ToUnicode( traceback.format_exc() )
            
            HydrusData.Print( 'Error when processing ' + self.seed_data + ' !' )
            HydrusData.Print( traceback.format_exc() )
            
        
        self.status = status
        self.note = note
        
        self._UpdateModified()
        
    
    def ShouldDownloadFile( self ):
        
        return self.status == CC.STATUS_UNKNOWN
        
    
    def ShouldFetchPageMetadata( self, tag_import_options ):
        
        if self.status == CC.STATUS_UNKNOWN:
            
            return True
            
        
        if self.status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
            
            if tag_import_options.WorthFetchingTags() and tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB():
                
                return True
                
            
        
        return False
        
    
    def ShouldPresent( self, file_import_options ):
        
        hash = self.GetHash()
        
        if hash is not None and self.status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if file_import_options.ShouldPresentIgnorantOfInbox( self.status ):
                
                return True
                
            
            in_inbox = HG.client_controller.Read( 'in_inbox', hash )
            
            if file_import_options.ShouldPresent( self.status, in_inbox ):
                
                return True
                
            
        
        return False
        
    
    def WorksInNewSystem( self ):
        
        if self.seed_type == SEED_TYPE_URL:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.seed_data )
            
            if url_type == HC.URL_TYPE_FILE:
                
                return True
                
            
            if url_type == HC.URL_TYPE_POST and can_parse:
                
                return True
                
            
            if url_type == HC.URL_TYPE_UNKNOWN and self._referral_url is not None: # this is likely be a multi-file child of a post url seed
                
                ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self._referral_url )
                
                if url_type == HC.URL_TYPE_POST: # we must have got here through parsing that m8, so let's assume this is an unrecognised file url
                    
                    return True
                    
                
            
        
        return False
        
    
    def WorkOnURL( self, seed_cache, status_hook, network_job_factory, network_job_presentation_context_factory, file_import_options, tag_import_options = None ):
        
        did_substantial_work = False
        
        try:
            
            status_hook( 'checking url status' )
            
            self.PredictPreImportStatus( file_import_options )
            
            if self.IsAPostURL():
                
                if tag_import_options is None:
                    
                    tag_import_options = HG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( self.seed_data )
                    
                
                if self.ShouldFetchPageMetadata( tag_import_options ):
                    
                    did_substantial_work = True
                    
                    post_url = self.seed_data
                    
                    ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
                    
                    status_hook( 'downloading page' )
                    
                    if self._referral_url not in ( post_url, url_to_check ):
                        
                        referral_url = self._referral_url
                        
                    else:
                        
                        referral_url = None
                        
                    
                    network_job = network_job_factory( 'GET', url_to_check, referral_url = referral_url )
                    
                    HG.client_controller.network_engine.AddJob( network_job )
                    
                    with network_job_presentation_context_factory( network_job ) as njpc:
                        
                        network_job.WaitUntilDone()
                        
                    
                    data = network_job.GetContent()
                    
                    parsing_context = {}
                    
                    parsing_context[ 'post_url' ] = post_url
                    parsing_context[ 'url' ] = url_to_check
                    
                    all_parse_results = parser.Parse( parsing_context, data )
                    
                    if len( all_parse_results ) == 0:
                        
                        raise HydrusExceptions.VetoException( 'Could not parse any data!' )
                        
                    
                    parse_results = all_parse_results[0]
                    
                    self.AddParseResults( parse_results )
                    
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
                            
                            self.PredictPreImportStatus( file_import_options, file_url )
                            
                            if self.ShouldDownloadFile():
                                
                                status_hook( 'downloading file' )
                                
                                self.DownloadAndImportRawFile( file_url, file_import_options, network_job_factory, network_job_presentation_context_factory )
                                
                            
                        elif url_type == HC.URL_TYPE_POST and can_parse:
                            
                            # a pixiv mode=medium page has spawned a mode=manga page, so we need a new seed to go pursue that
                            
                            child_urls = [ desired_url ]
                            
                        else:
                            
                            raise HydrusExceptions.VetoException( 'Found a URL--' + desired_url + '--but could not understand/parse it!' )
                            
                        
                    else:
                        
                        child_urls = desired_urls
                        
                    
                    if len( child_urls ) > 0:
                        
                        child_seeds = []
                        
                        for child_url in child_urls:
                            
                            duplicate_seed = self.Duplicate() # inherits all urls and tags from here
                            
                            duplicate_seed.seed_data = child_url
                            
                            duplicate_seed.SetReferralURL( self.seed_data )
                            
                            if self._referral_url is not None:
                                
                                duplicate_seed.AddURL( self._referral_url )
                                
                            
                            child_seeds.append( duplicate_seed )
                            
                        
                        try:
                            
                            my_index = seed_cache.GetSeedIndex( self )
                            
                            insertion_index = my_index + 1
                            
                        except:
                            
                            insertion_index = len( seed_cache )
                            
                        
                        seed_cache.InsertSeeds( insertion_index, child_seeds )
                        
                        status = CC.STATUS_SUCCESSFUL_AND_NEW
                        note = 'Found ' + HydrusData.ConvertIntToPrettyString( len( child_urls ) ) + ' new URLs.'
                        
                        self.SetStatus( status, note = note )
                        
                    
                
            else:
                
                if tag_import_options is None:
                    
                    if self._referral_url is not None:
                        
                        tio_lookup_url = self._referral_url
                        
                    else:
                        
                        tio_lookup_url = self.seed_data
                        
                    
                    tag_import_options = HG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( tio_lookup_url )
                    
                
                if self.ShouldDownloadFile():
                    
                    did_substantial_work = True
                    
                    file_url = self.seed_data
                    
                    status_hook( 'downloading file' )
                    
                    self.DownloadAndImportRawFile( file_url, file_import_options, network_job_factory, network_job_presentation_context_factory )
                    
                
            
            did_substantial_work |= self.WriteContentUpdates( tag_import_options )
            
        except HydrusExceptions.ShutdownException:
            
            return False
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = HydrusData.ToUnicode( e )
            
            self.SetStatus( status, note = note )
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                status_hook( 'cancelled!' )
                
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
            
        
        return did_substantial_work
        
    
    def WriteContentUpdates( self, tag_import_options = None ):
        
        did_work = False
        
        if self.status == CC.STATUS_ERROR:
            
            return did_work
            
        
        hash = self.GetHash()
        
        if hash is None:
            
            return did_work
            
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        urls = set( self._urls )
        
        if self.seed_type == SEED_TYPE_URL:
            
            urls.add( self.seed_data )
            
        
        if self._referral_url is not None:
            
            urls.add( self._referral_url )
            
        
        associable_urls = self._NormaliseAndFilterAssociableURLs( urls )
        
        if len( associable_urls ) > 0:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( associable_urls, ( hash, ) ) )
            
            service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].append( content_update )
            
        
        if tag_import_options is not None:
            
            for ( service_key, content_updates ) in tag_import_options.GetServiceKeysToContentUpdates( hash, set( self._tags ) ).items():
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            did_work = True
            
        
        return did_work
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED ] = Seed

class SeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE
    SERIALISABLE_NAME = 'Import File Status Cache'
    SERIALISABLE_VERSION = 8
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._seeds = HydrusSerialisable.SerialisableList()
        
        self._seeds_to_indices = {}
        
        self._seed_cache_key = HydrusData.GenerateKey()
        
        self._status_cache = None
        self._status_cache_generation_time = 0
        
        self._status_dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._seeds )
        
    
    def _GenerateStatus( self ):
        
        statuses_to_counts = self._GetStatusesToCounts()
        
        self._status_cache = GenerateSeedCacheStatus( statuses_to_counts )
        self._status_cache_generation_time = HydrusData.GetNow()
        
        self._status_dirty = False
        
    
    def _GetStatusesToCounts( self ):
        
        statuses_to_counts = collections.Counter()
        
        for seed in self._seeds:
            
            statuses_to_counts[ seed.status ] += 1
            
        
        return statuses_to_counts
        
    
    def _GetSeeds( self, status = None ):
        
        if status is None:
            
            return list( self._seeds )
            
        else:
            
            return [ seed for seed in self._seeds if seed.status == status ]
            
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            return self._seeds.GetSerialisableTuple()
            
        
    
    def _GetSourceTimestamp( self, seed ):
        
        source_timestamp = seed.source_time
        
        if source_timestamp is None:
            
            # decent fallback compromise
            # -30 since added and 'last check' timestamps are often the same, and this messes up calculations
            
            source_timestamp = seed.created - 30
            
        
        return source_timestamp
        
    
    def _HasSeed( self, seed ):
        
        search_seeds = seed.GetSearchSeeds()
        
        has_seed = True in ( search_seed in self._seeds_to_indices for search_seed in search_seeds )
        
        return has_seed
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            self._seeds = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
            
        
    
    def _SetStatusDirty( self ):
        
        self._status_dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                if 'note' in seed_info:
                    
                    seed_info[ 'note' ] = HydrusData.ToUnicode( seed_info[ 'note' ] )
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 2, new_serialisable_info )
            
        
        if version in ( 2, 3 ):
            
            # gelbooru replaced their thumbnail links with this redirect spam
            # 'https://gelbooru.com/redirect.php?s=Ly9nZWxib29ydS5jb20vaW5kZXgucGhwP3BhZ2U9cG9zdCZzPXZpZXcmaWQ9MzY4ODA1OA=='
            
            # I missed some http ones here, so I've broadened the test and rescheduled it
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                if 'gelbooru.com/redirect.php' in seed:
                    
                    continue
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
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
            
            good_seeds = set()
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                try:
                    
                    parse = urlparse.urlparse( seed )
                    
                    if 'media.tumblr.com' in parse.netloc:
                        
                        seed = Remove68Subdomain( seed )
                        
                        seed = ConvertRegularToRawURL( seed )
                        
                        seed = ClientNetworkingDomain.ConvertHTTPToHTTPS( seed )
                        
                    
                    if 'pixiv.net' in parse.netloc:
                        
                        seed = ClientNetworkingDomain.ConvertHTTPToHTTPS( seed )
                        
                    
                    if seed in good_seeds: # we hit a dupe, so skip it
                        
                        continue
                        
                    
                except:
                    
                    pass
                    
                
                good_seeds.add( seed )
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                seed_info[ 'source_timestamp' ] = None
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                try:
                    
                    magic_phrase = '//media.tumblr.com'
                    replacement = '//data.tumblr.com'
                    
                    if magic_phrase in seed:
                        
                        seed = seed.replace( magic_phrase, replacement )
                        
                    
                except:
                    
                    pass
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            seeds = HydrusSerialisable.SerialisableList()
            
            for ( seed_text, seed_info ) in old_serialisable_info:
                
                if seed_text.startswith( 'http' ):
                    
                    seed_type = SEED_TYPE_URL
                    
                else:
                    
                    seed_type = SEED_TYPE_HDD
                    
                
                seed = Seed( seed_type, seed_text )
                
                seed.status = seed_info[ 'status' ]
                seed.created = seed_info[ 'added_timestamp' ]
                seed.modified = seed_info[ 'last_modified_timestamp' ]
                seed.source_time = seed_info[ 'source_timestamp' ]
                seed.note = seed_info[ 'note' ]
                
                seeds.append( seed )
                
            
            new_serialisable_info = seeds.GetSerialisableTuple()
            
            return ( 8, new_serialisable_info )
            
        
    
    def AddSeeds( self, seeds ):
        
        if len( seeds ) == 0:
            
            return 0 
            
        
        new_seeds = []
        
        with self._lock:
            
            for seed in seeds:
                
                if self._HasSeed( seed ):
                    
                    continue
                    
                
                seed.Normalise()
                
                new_seeds.append( seed )
                
                self._seeds.append( seed )
                
                self._seeds_to_indices[ seed ] = len( self._seeds ) - 1
                
            
            self._SetStatusDirty()
            
        
        self.NotifySeedsUpdated( new_seeds )
        
        return len( new_seeds )
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_indices:
                
                index = self._seeds_to_indices[ seed ]
                
                if index > 0:
                    
                    self._seeds.remove( seed )
                    
                    self._seeds.insert( index - 1, seed )
                    
                
                self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
                
            
        
        self.NotifySeedsUpdated( ( seed, ) )
        
    
    def CanCompact( self, compact_before_this_source_time ):
        
        with self._lock:
            
            if len( self._seeds ) <= 100:
                
                return False
                
            
            for seed in self._seeds[:-100]:
                
                if seed.status == CC.STATUS_UNKNOWN:
                    
                    continue
                    
                
                if self._GetSourceTimestamp( seed ) < compact_before_this_source_time:
                    
                    return True
                    
                
            
        
        return False
        
    
    def Compact( self, compact_before_this_source_time ):
        
        with self._lock:
            
            if len( self._seeds ) <= 100:
                
                return
                
            
            new_seeds = HydrusSerialisable.SerialisableList()
            
            for seed in self._seeds[:-100]:
                
                still_to_do = seed.status == CC.STATUS_UNKNOWN
                still_relevant = self._GetSourceTimestamp( seed ) > compact_before_this_source_time
                
                if still_to_do or still_relevant:
                    
                    new_seeds.append( seed )
                    
                
            
            new_seeds.extend( self._seeds[-100:] )
            
            self._seeds = new_seeds
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
            
            self._SetStatusDirty()
            
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_indices:
                
                index = self._seeds_to_indices[ seed ]
                
                if index < len( self._seeds ) - 1:
                    
                    self._seeds.remove( seed )
                    
                    self._seeds.insert( index + 1, seed )
                    
                
                self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
                
            
        
        self.NotifySeedsUpdated( ( seed, ) )
        
    
    def GetEarliestSourceTime( self ):
        
        with self._lock:
            
            if len( self._seeds ) == 0:
                
                return None
                
            
            earliest_timestamp = min( ( self._GetSourceTimestamp( seed ) for seed in self._seeds ) )
            
        
        return earliest_timestamp
        
    
    def GetLatestAddedTime( self ):
        
        with self._lock:
            
            if len( self._seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( seed.created for seed in self._seeds ) )
            
        
        return latest_timestamp
        
    
    def GetLatestSourceTime( self ):
        
        with self._lock:
            
            if len( self._seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetSourceTimestamp( seed ) for seed in self._seeds ) )
            
        
        return latest_timestamp
        
    
    def GetNextSeed( self, status ):
        
        with self._lock:
            
            for seed in self._seeds:
                
                if seed.status == status:
                    
                    return seed
                    
                
            
        
        return None
        
    
    def GetNumNewFilesSince( self, since ):
        
        num_files = 0
        
        with self._lock:
            
            for seed in self._seeds:
                
                source_timestamp = self._GetSourceTimestamp( seed )
                
                if source_timestamp >= since:
                    
                    num_files += 1
                    
                
            
        
        return num_files
        
    
    def GetPresentedHashes( self, file_import_options ):
        
        with self._lock:
            
            hashes = []
            
            for seed in self._seeds:
                
                if seed.HasHash() and seed.ShouldPresent( file_import_options ):
                    
                    hashes.append( seed.GetHash() )
                    
                
            
            return hashes
            
        
    
    def GetSeedCacheKey( self ):
        
        return self._seed_cache_key
        
    
    def GetSeedCount( self, status = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._seeds )
                
            else:
                
                for seed in self._seeds:
                    
                    if seed.status == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetSeeds( self, status = None ):
        
        with self._lock:
            
            return self._GetSeeds( status )
            
        
    
    def GetSeedIndex( self, seed ):
        
        with self._lock:
            
            return self._seeds_to_indices[ seed ]
            
        
    
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
                
            
            ( status, ( total_processed, total ) ) = self._status_cache
            
            return ( total_processed, total )
            
        
    
    def HasSeed( self, seed ):
        
        with self._lock:
            
            return self._HasSeed( seed )
            
        
    
    def InsertSeeds( self, index, seeds ):
        
        if len( seeds ) == 0:
            
            return 0 
            
        
        new_seeds = []
        
        with self._lock:
            
            index = min( index, len( self._seeds ) )
            
            for seed in seeds:
                
                if self._HasSeed( seed ):
                    
                    continue
                    
                
                seed.Normalise()
                
                new_seeds.append( seed )
                
                self._seeds.insert( index, seed )
                
                index += 1
                
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
            
            self._SetStatusDirty()
            
        
        self.NotifySeedsUpdated( new_seeds )
        
        return len( new_seeds )
        
    
    def NotifySeedsUpdated( self, seeds ):
        
        with self._lock:
            
            self._SetStatusDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds )
        
    
    def RemoveSeeds( self, seeds ):
        
        with self._lock:
            
            seeds_to_delete = set( seeds )
            
            self._seeds = HydrusSerialisable.SerialisableList( [ seed for seed in self._seeds if seed not in seeds_to_delete ] )
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
            
            self._SetStatusDirty()
            
        
        self.NotifySeedsUpdated( seeds_to_delete )
        
    
    def RemoveSeedsByStatus( self, statuses_to_remove ):
        
        with self._lock:
            
            seeds_to_delete = [ seed for seed in self._seeds if seed.status in statuses_to_remove ]
            
        
        self.RemoveSeeds( seeds_to_delete )
        
    
    def RemoveAllButUnknownSeeds( self ):
        
        with self._lock:
            
            seeds_to_delete = [ seed for seed in self._seeds if seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveSeeds( seeds_to_delete )
        
    
    def RetryFailures( self ):
        
        with self._lock:
            
            failed_seeds = self._GetSeeds( CC.STATUS_ERROR )
            
            for seed in failed_seeds:
                
                seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
        
        self.NotifySeedsUpdated( failed_seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            ( status, ( total_processed, total ) ) = self._status_cache
            
            return total_processed < total
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE ] = SeedCache
