import collections
import collections.abc
import itertools
import os
import random
import re
import threading
import time
import traceback
import typing
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTemp
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing import ClientImporting
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.parsing import ClientParsing
from hydrus.client.parsing import ClientParsingResults

FILE_SEED_TYPE_HDD = 0
FILE_SEED_TYPE_URL = 1

def FilterOneFileURLs( urls ):
    
    one_file_urls = []
    
    for url in urls:
        
        url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url )
        
        if url_class is None:
            
            continue
            
        
        # direct file URLs do not care about neighbours, since that can mean tokenised or different CDN URLs, so skip file/unknown
        if url_class.GetURLType() != HC.URL_TYPE_POST:
            
            continue
            
        
        if not url_class.RefersToOneFile():
            
            continue
            
        
        one_file_urls.append( url )
        
    
    return one_file_urls
    

def FileURLMappingHasUntrustworthyNeighbours( hash: bytes, lookup_urls: collections.abc.Collection[ str ] ):
    
    # TODO: Revisiting this guy, it feels too complicated and opaque
    # why do we not care about the exact caller URL that got us this hash? in the caller it seems like any match to this hash will fail, no matter how we got there?
    # is that what we want? if it is, this needs to be clearer
    # some unit tests couldn't hurt either mate
    
    # let's see if the file that has this url has any other interesting urls
    # if the file has--or would have, after import--multiple URLs from the same domain with the same URL Class, but those URLs are supposed to only refer to one file, then we have a dodgy spam URL mapping so we cannot trust it
    # maybe this is the correct file, but we can't trust that it is mate
    
    lookup_urls = [ url for url in lookup_urls if ClientNetworkingFunctions.LooksLikeAFullURL( url ) ]
    
    lookup_urls = CG.client_controller.network_engine.domain_manager.NormaliseURLs( lookup_urls )
    
    # this has probably already been done by the caller, but let's be sure
    lookup_urls = FilterOneFileURLs( lookup_urls )
    
    if len( lookup_urls ) == 0:
        
        # ok, this method was likely called with only File/Unknown URLs, probably, or at least those are the only things that could be providing trustworthy results
        # we cannot adjudicate File/Unknown URL trustworthiness here, so we return False
        return False
        
    
    lookup_url_domains = { ClientNetworkingFunctions.ConvertURLIntoDomain( lookup_url ) for lookup_url in lookup_urls } 
    lookup_url_classes = { CG.client_controller.network_engine.domain_manager.GetURLClass( lookup_url ) for lookup_url in lookup_urls }
    
    media_result = CG.client_controller.Read( 'media_result', hash )
    
    existing_file_urls = media_result.GetLocationsManager().GetURLs()
    
    existing_file_urls = [ url for url in existing_file_urls if ClientNetworkingFunctions.LooksLikeAFullURL( url ) ]
    
    # normalise to collapse http/https dupes
    existing_file_urls = CG.client_controller.network_engine.domain_manager.NormaliseURLs( existing_file_urls )
    
    existing_file_urls = FilterOneFileURLs( existing_file_urls )
    
    for file_url in existing_file_urls:
        
        if file_url in lookup_urls:
            
            # obviously when we find ourselves, that's fine
            # this should happen at least once every time this method is called, since that's how we found the file!
            continue
            
        
        if ClientNetworkingFunctions.ConvertURLIntoDomain( file_url ) not in lookup_url_domains:
            
            # this existing URL has a unique domain, so there is no domain spam here
            continue
            
        
        file_url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( file_url )
        
        if file_url_class in lookup_url_classes:
            
            # oh no, the file these lookup urls refer to has a different known url in the same domain+url_class
            # it is likely that an edit on this site points to the original elsewhere
            
            HydrusData.Print( f'INFO: When a URL status lookup suggested {hash.hex()}, I discovered that that file\'s existing URL "{file_url}" had the same URL Class as one of the lookup URLs, which were{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary(lookup_urls)}. This made the lookup untrustworthy (probably evidence of a previous bad booru source reference, or merged URLs during duplicate processing).' )
            
            return True
            
        
    
    return False
    

class FileSeed( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED
    SERIALISABLE_NAME = 'File Import'
    SERIALISABLE_VERSION = 8
    
    top_wew_default = 'https://big-guys.4u/monica_lewinsky_hott.tiff.exe.vbs'
    
    def __init__( self, file_seed_type: int = None, file_seed_data: str = None ):
        
        if file_seed_type is None:
            
            file_seed_type = FILE_SEED_TYPE_URL
            
        
        if file_seed_data is None:
            
            file_seed_data = self.top_wew_default
            
        
        super().__init__()
        
        self.file_seed_type = file_seed_type
        self.file_seed_data = file_seed_data
        self.file_seed_data_for_comparison = file_seed_data
        
        if self.file_seed_data != self.top_wew_default:
            
            self.Normalise() # this fixes the comparison file seed data and fails safely
            
        
        self.created = HydrusTime.GetNow()
        self.modified = self.created
        self.source_time = None
        self.status = CC.STATUS_UNKNOWN
        self.note = ''
        
        self._cloudflare_last_modified_time = None
        
        self._referral_url = None
        self._request_headers = {}
        
        self._external_filterable_tags = set()
        self._external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        self._primary_urls = set()
        self._source_urls = set()
        self._tags = set()
        self._names_and_notes_dict = dict()
        self._hashes = {}
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FileSeed ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        if self.file_seed_data_for_comparison is None:
            
            self.file_seed_data_for_comparison = self.file_seed_data
            
        
        return ( self.file_seed_type, self.file_seed_data_for_comparison ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _AddPrimaryURLs( self, urls ):
        
        if len( urls ) == 0:
            
            return
            
        
        urls = ClientNetworkingFunctions.NormaliseAndFilterAssociableURLs( urls )
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            urls.discard( self.file_seed_data )
            urls.discard( self.file_seed_data_for_comparison )
            
        
        if self._referral_url is not None:
            
            urls.discard( self._referral_url )
            
        
        self._primary_urls.update( urls )
        self._source_urls.difference_update( urls )
        
    
    def _AddSourceURLs( self, urls ):
        
        if len( urls ) == 0:
            
            return
            
        
        urls = ClientNetworkingFunctions.NormaliseAndFilterAssociableURLs( urls )
        
        all_primary_urls = set()
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            all_primary_urls.add( self.file_seed_data )
            all_primary_urls.add( self.file_seed_data_for_comparison )
            
        
        if self._referral_url is not None:
            
            all_primary_urls.add( self._referral_url )
            
        
        all_primary_urls.update( self._primary_urls )
        
        urls.difference_update( all_primary_urls )
        
        primary_url_classes = { CG.client_controller.network_engine.domain_manager.GetURLClass( url ) for url in all_primary_urls }
        primary_url_classes.discard( None )
        
        # ok when a booru has a """"""source"""""" url that points to a file alternate on the same booru, that isn't what we call a source url
        # so anything that has a source url with the same url class as our primaries, just some same-site loopback, we'll dump
        urls = { url for url in urls if CG.client_controller.network_engine.domain_manager.GetURLClass( url ) not in primary_url_classes }
        
        self._source_urls.update( urls )
        
    
    def _CheckTagsVeto( self, tags, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        if len( tags ) > 0:
            
            tags_to_siblings = CG.client_controller.Read( 'tag_siblings_lookup', CC.COMBINED_TAG_SERVICE_KEY, tags )
            
            all_chain_tags = set( itertools.chain.from_iterable( tags_to_siblings.values() ) )
            
            tag_import_options.CheckTagsVeto( tags, all_chain_tags )
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_external_filterable_tags = list( self._external_filterable_tags )
        serialisable_external_additional_service_keys_to_tags = self._external_additional_service_keys_to_tags.GetSerialisableTuple()
        
        serialisable_primary_urls = list( self._primary_urls )
        serialisable_source_urls = list( self._source_urls )
        serialisable_tags = list( self._tags )
        serialisable_names_and_notes_dict = list( self._names_and_notes_dict.items() )
        serialisable_hashes = [ ( hash_type, hash.hex() ) for ( hash_type, hash ) in self._hashes.items() if hash is not None ]
        
        return (
            self.file_seed_type,
            self.file_seed_data,
            self.file_seed_data_for_comparison,
            self.created,
            self.modified,
            self.source_time,
            self.status,
            self.note,
            self._referral_url,
            self._request_headers,
            serialisable_external_filterable_tags,
            serialisable_external_additional_service_keys_to_tags,
            serialisable_primary_urls,
            serialisable_source_urls,
            serialisable_tags,
            serialisable_names_and_notes_dict,
            serialisable_hashes
        )
        
    
    def _GiveChildFileSeedMyInfo( self, file_seed: "FileSeed", url_for_child_referral: str ):
        
        file_seed.AddRequestHeaders( self._request_headers )
        
        file_seed.SetReferralURL( url_for_child_referral )
        
        if self._referral_url is not None:
            
            file_seed.AddSourceURLs( ( self._referral_url, ) )
            
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            file_seed.AddPrimaryURLs( ( self.file_seed_data, ) )
            
        
        file_seed.AddPrimaryURLs( set( self._primary_urls ) )
        
        file_seed.AddSourceURLs( set( self._source_urls ) )
        
        file_seed.AddExternalFilterableTags( self._external_filterable_tags )
        file_seed.AddExternalAdditionalServiceKeysToTags( self._external_additional_service_keys_to_tags )
        
        file_seed.AddTags( set( self._tags ) )
        
        file_seed.AddNamesAndNotes( sorted( self._names_and_notes_dict.items() ) )
        
        file_seed.source_time = self.source_time
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self.file_seed_type,
            self.file_seed_data,
            self.file_seed_data_for_comparison,
            self.created,
            self.modified,
            self.source_time,
            self.status,
            self.note,
            self._referral_url,
            self._request_headers,
            serialisable_external_filterable_tags,
            serialisable_external_additional_service_keys_to_tags,
            serialisable_primary_urls,
            serialisable_source_urls,
            serialisable_tags,
            serialisable_names_and_notes_dict,
            serialisable_hashes
        ) = serialisable_info
        
        self._external_filterable_tags = set( serialisable_external_filterable_tags )
        self._external_additional_service_keys_to_tags = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_external_additional_service_keys_to_tags )
        
        # fixing a problem when updating to v8 of this object, originally I accidentally reset this to None for local path guys
        if self.file_seed_data_for_comparison is None:
            
            self.file_seed_data_for_comparison = self.file_seed_data
            
        
        self._primary_urls = set( serialisable_primary_urls )
        self._source_urls = set( serialisable_source_urls )
        self._tags = set( serialisable_tags )
        self._names_and_notes_dict = dict( serialisable_names_and_notes_dict )
        self._hashes = { hash_type : bytes.fromhex( encoded_hash ) for ( hash_type, encoded_hash ) in serialisable_hashes if encoded_hash is not None }
        
    
    def _SetupNoteImportOptions( self, given_note_import_options: NoteImportOptions.NoteImportOptions ) -> NoteImportOptions.NoteImportOptions:
        
        if given_note_import_options.IsDefault():
            
            note_import_options = CG.client_controller.network_engine.domain_manager.GetDefaultNoteImportOptionsForURL( self._referral_url, self.file_seed_data )
            
        else:
            
            note_import_options = given_note_import_options
            
        
        return note_import_options
        
    
    def _SetupTagImportOptions( self, given_tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ) -> TagImportOptionsLegacy.TagImportOptionsLegacy:
        
        if given_tag_import_options.IsDefault():
            
            tag_import_options = CG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( self._referral_url, self.file_seed_data )
            
        else:
            
            tag_import_options = given_tag_import_options
            
        
        return tag_import_options
        
    
    def _UpdateModified( self ):
        
        self.modified = HydrusTime.GetNow()
        
    
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
            
        
        if version == 4:
            
            (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_urls,
                serialisable_tags,
                serialisable_hashes
            ) = old_serialisable_info
            
            serialisable_primary_urls = serialisable_urls
            serialisable_source_urls = []
            
            new_serialisable_info = (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                serialisable_hashes
            )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                serialisable_hashes
            ) = old_serialisable_info
            
            names_and_notes = []
            
            new_serialisable_info = (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                names_and_notes,
                serialisable_hashes
            )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                names_and_notes,
                serialisable_hashes
            ) = old_serialisable_info
            
            request_headers = {}
            
            new_serialisable_info = (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                request_headers,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                names_and_notes,
                serialisable_hashes
            )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            (
                file_seed_type,
                file_seed_data,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                request_headers,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                names_and_notes,
                serialisable_hashes
            ) = old_serialisable_info
            
            file_seed_data_for_comparison = None
            
            if file_seed_type == FILE_SEED_TYPE_URL:
                
                try:
                    
                    file_seed_data_for_comparison = CG.client_controller.network_engine.domain_manager.NormaliseURL( file_seed_data )
                    
                except Exception as e:
                    
                    pass
                    
                
            else:
                
                file_seed_data_for_comparison = file_seed_data
                
            
            new_serialisable_info = (
                file_seed_type,
                file_seed_data,
                file_seed_data_for_comparison,
                created,
                modified,
                source_time,
                status,
                note,
                referral_url,
                request_headers,
                serialisable_external_filterable_tags,
                serialisable_external_additional_service_keys_to_tags,
                serialisable_primary_urls,
                serialisable_source_urls,
                serialisable_tags,
                names_and_notes,
                serialisable_hashes
            )
            
            return ( 8, new_serialisable_info )
            
        
    
    def AddExternalAdditionalServiceKeysToTags( self, service_keys_to_tags ):
        
        self._external_additional_service_keys_to_tags.update( service_keys_to_tags )
        
    
    def AddExternalFilterableTags( self, tags ):
        
        self._external_filterable_tags.update( tags )
        
    
    def AddParsedPost( self, parsed_post: ClientParsingResults.ParsedPost, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        parsed_request_headers = parsed_post.GetHTTPHeaders()
        
        self.AddRequestHeaders( parsed_request_headers )
        
        hash_data = parsed_post.GetHashes()
        
        for ( hash_type, hash ) in hash_data:
            
            if hash_type not in self._hashes:
                
                self._hashes[ hash_type ] = hash
                
            
        
        source_urls = parsed_post.GetURLs( ( HC.URL_TYPE_SOURCE, ) )
        
        self._AddSourceURLs( source_urls )
        
        tags = parsed_post.GetTags()
        
        self._tags.update( tags )
        
        names_and_notes = parsed_post.GetNamesAndNotes()
        
        self._names_and_notes_dict.update( names_and_notes )
        
        source_timestamp = parsed_post.GetTimestamp( HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN )
        
        if source_timestamp is not None and ClientTime.TimestampIsSensible( source_timestamp ):
            
            source_timestamp = min( HydrusTime.GetNow() - 30, source_timestamp )
            
            self.source_time = ClientTime.MergeModifiedTimes( self.source_time, source_timestamp )
            
        
        self._UpdateModified()
        
    
    def AddRequestHeaders( self, request_headers: dict ):
        
        self._request_headers.update( request_headers )
        
    
    def AddTags( self, tags ):
        
        tags = HydrusTags.CleanTags( tags )
        
        self._tags.update( tags )
        
        self._UpdateModified()
        
    
    def AddNamesAndNotes( self, names_and_notes ):
        
        self._names_and_notes_dict.update( names_and_notes )
        
        self._UpdateModified()
        
    
    def AddPrimaryURLs( self, urls ):
        
        self._AddPrimaryURLs( urls )
        
        self._UpdateModified()
        
    
    def AddSourceURLs( self, urls ):
        
        self._AddSourceURLs( urls )
        
        self._UpdateModified()
        
    
    def CheckPreFetchMetadata( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        self._CheckTagsVeto( self._tags, tag_import_options )
        
    
    def DownloadAndImportRawFile( self, file_url: str, file_import_options, loud_or_quiet: int, network_job_factory, network_job_presentation_context_factory, status_hook, override_bandwidth = False, spawning_url = None, forced_referral_url = None, file_seed_cache = None ):
        
        file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( file_import_options, loud_or_quiet )
        
        self.AddPrimaryURLs( ( file_url, ) )
        
        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
        
        try:
            
            if forced_referral_url is not None:
                
                referral_url = forced_referral_url
                
            elif self.file_seed_data != file_url:
                
                referral_url = self.file_seed_data
                
            else:
                
                referral_url = self._referral_url
                
            
            status_hook( 'downloading file' )
            
            url_to_fetch = CG.client_controller.network_engine.domain_manager.GetURLToFetch( file_url )
            
            network_job = network_job_factory( 'GET', url_to_fetch, temp_path = temp_path, referral_url = referral_url )
            
            for ( key, value ) in self._request_headers.items():
                
                network_job.AddAdditionalHeader( key, value )
                
            
            if spawning_url is not None:
                
                network_job.AddBandwidthURL( spawning_url )
                
            
            if override_bandwidth:
                
                network_job.OverrideBandwidth( 3 )
                
            
            network_job.SetFileFilteringImportOptions( file_import_options.GetFileFilteringImportOptions() )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            with network_job_presentation_context_factory( network_job ) as njpc:
                
                network_job.WaitUntilDone()
                
            
            if url_to_fetch != file_url:
                
                self._AddPrimaryURLs( ( url_to_fetch, ) )
                
            
            actual_fetched_url = network_job.GetActualFetchedURL()
            
            if actual_fetched_url not in ( file_url, url_to_fetch ):
                
                self._AddPrimaryURLs( ( actual_fetched_url, ) )
                
                ( actual_url_type, actual_match_name, actual_can_parse, actual_cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( actual_fetched_url )
                
                if actual_url_type == HC.URL_TYPE_POST and actual_can_parse:
                    
                    # we just had a 3XX redirect to a Post URL!
                    
                    if file_seed_cache is None:
                        
                        raise Exception( 'The downloader thought it had a raw file url with "{}", but that redirected to the apparent Post URL "{}", but then there was no file log in which to queue that download!'.format( file_url, actual_fetched_url ) )
                        
                    else:
                        
                        ( original_url_type, original_match_name, original_can_parse, original_cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
                        
                        if original_url_type == actual_url_type and original_match_name == actual_match_name:
                            
                            raise Exception( 'The downloader thought it had a raw file url with "{}", but that redirected to the apparent Post URL "{}". As that URL has the same class as this import job\'s original URL, we are stopping here in case this is a looping redirect!'.format( file_url, actual_fetched_url ) )
                            
                        
                        file_seed = FileSeed( FILE_SEED_TYPE_URL, actual_fetched_url )
                        
                        file_seed.SetReferralURL( file_url )
                        
                        file_seeds = [ file_seed ]
                        
                        file_seed_cache.AddFileSeeds( file_seeds )
                        
                        status = CC.STATUS_SUCCESSFUL_AND_CHILD_FILES
                        
                        note = 'was redirected on file download to a post url, which has been queued in the parent file log'
                        
                        self.SetStatus( status, note = note )
                        
                        return
                        
                    
                
            
            last_modified_time = network_job.GetLastModifiedTime()
            
            if self.source_time is not None and last_modified_time is not None:
                
                # even with timezone weirdness, does the current source time have something reasonable?
                current_source_time_looks_good = HydrusTime.TimeHasPassed( self.source_time - 86400 )
                
                # if CF is delivering a timestamp from 17 days before source time, this is probably some unusual CDN situation or delayed post
                # we don't _really_ want this CF timestamp since it throws the domain-based timestamp ordering out
                # in future maybe we'll save it as a misc 'cloudflare' domain or something, but for now we'll discard
                if network_job.IsCloudFlareCache() and abs( self.source_time - last_modified_time ) > 86400 * 2:
                    
                    self._cloudflare_last_modified_time = last_modified_time
                    last_modified_time = None
                    
                
            
            if ClientTime.TimestampIsSensible( last_modified_time ):
                
                self.source_time = ClientTime.MergeModifiedTimes( self.source_time, last_modified_time )
                
            
            status_hook( 'importing file' )
            
            self.Import( temp_path, file_import_options, status_hook = status_hook )
            
        finally:
            
            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
    def FetchPageMetadata( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        pass
        
    
    def GetAPIInfoDict( self, simple: bool ):
        
        d = {}
        
        d[ 'import_data' ] = self.file_seed_data
        d[ 'created' ] = self.created
        d[ 'modified' ] = self.modified
        d[ 'source_time' ] = self.source_time
        d[ 'status' ] = self.status
        d[ 'note' ] = self.note
        
        hash = self.GetHash()
        
        d[ 'hash' ] = hash.hex() if hash is not None else hash
        
        return d
        
    
    def GetExampleNetworkJob( self, network_job_factory ):
        
        if self.IsAPostURL():
            
            post_url = self.file_seed_data
            
            try:
                
                url_to_fetch = CG.client_controller.network_engine.domain_manager.GetURLToFetch( post_url )
                
            except HydrusExceptions.URLClassException:
                
                url_to_fetch = post_url
                
            
        else:
            
            url_to_fetch = self.file_seed_data
            
        
        network_job = network_job_factory( 'GET', url_to_fetch )
        
        return network_job
        
    
    def GetHash( self ):
        
        if 'sha256' in self._hashes:
            
            return self._hashes[ 'sha256' ]
            
        
        return None
        
    
    def GetHashTypesToHashes( self ):
        
        return dict( self._hashes )
        
    
    def GetPreImportStatusPredictionHash( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ) -> tuple[ bool, bool, ClientImportFiles.FileImportStatus ]:
        
        # TODO: a user raised the spectre of multiple hash parses on some site that actually provides somehow the pre- and post- optimised versions of a file
        # some I guess support multiple hashes at some point, maybe, or figure out a different solution, or draw a harder line in parsing about one-hash-per-parse
        
        prefetch_import_options = file_import_options.GetPrefetchImportOptions()
        
        preimport_hash_check_type = prefetch_import_options.GetPreImportHashCheckType()
        
        match_found = False
        matches_are_dispositive = preimport_hash_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
        
        if len( self._hashes ) == 0 or preimport_hash_check_type == PrefetchImportOptions.DO_NOT_CHECK:
            
            return ( match_found, matches_are_dispositive, ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
        
        # hashes
        
        jobs = []
        
        if 'sha256' in self._hashes:
            
            jobs.append( ( 'sha256', self._hashes[ 'sha256' ] ) )
            
        
        for ( hash_type, found_hash ) in self._hashes.items():
            
            if hash_type == 'sha256':
                
                continue
                
            
            jobs.append( ( hash_type, found_hash ) )
            
        
        for ( hash_type, found_hash ) in jobs:
            
            file_import_status = CG.client_controller.Read( 'hash_status', hash_type, found_hash, prefix = '{} hash recognised'.format( hash_type ) )
            
            # there's some subtle gubbins going on here
            # an sha256 'haven't seen this before' result will not set the hash here and so will not count as a match
            # this is the same as if we do an md5 lookup and get no sha256 result back. we just aren't trusting a novel sha256 as a 'match'
            # this is _useful_ to reduce the dispositivity of this lad in this specific case
            
            if file_import_status.hash is None:
                
                continue
                
            
            match_found = True
            
            file_import_status = ClientImportFiles.CheckFileImportStatus( file_import_status )
            
            return ( match_found, matches_are_dispositive, file_import_status )
            
        
        return ( match_found, matches_are_dispositive, ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
        
    
    def GetPreImportStatusPredictionURL( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, file_url = None ) -> tuple[ bool, bool, ClientImportFiles.FileImportStatus ]:
        
        prefetch_import_options = file_import_options.GetPrefetchImportOptions()
        
        preimport_url_check_type = prefetch_import_options.GetPreImportURLCheckType()
        
        preimport_url_check_looks_for_neighbour_spam = prefetch_import_options.PreImportURLCheckLooksForNeighbourSpam()
        
        match_found = False
        matches_are_dispositive = preimport_url_check_type == PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
        
        if preimport_url_check_type == PrefetchImportOptions.DO_NOT_CHECK:
            
            return ( match_found, matches_are_dispositive, ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
        
        # urls
        
        lookup_urls = []
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            lookup_urls.append( self.file_seed_data_for_comparison )
            
        
        if file_url is not None:
            
            lookup_urls.append( file_url )
            
        
        lookup_urls.extend( self._primary_urls )
        
        # now that we store primary and source urls separately, we'll trust any primary but be careful about source
        # trusting classless source urls was too much of a hassle with too many boorus providing bad source urls like user account pages
        
        source_lookup_urls = [ url for url in self._source_urls if CG.client_controller.network_engine.domain_manager.URLDefinitelyRefersToOneFile( url ) ]
        
        all_neighbour_useful_lookup_urls = list( lookup_urls )
        all_neighbour_useful_lookup_urls.extend( source_lookup_urls )
        
        if file_import_options.GetLocationImportOptions().ShouldAssociateSourceURLs():
            
            lookup_urls.extend( source_lookup_urls )
            
        
        # now discard gallery pages or post urls that can hold multiple files
        lookup_urls = [ url for url in lookup_urls if not CG.client_controller.network_engine.domain_manager.URLCanReferToMultipleFiles( url ) ]
        
        lookup_urls = CG.client_controller.network_engine.domain_manager.NormaliseURLs( lookup_urls )
        
        all_neighbour_useful_lookup_urls = [ url for url in all_neighbour_useful_lookup_urls if not CG.client_controller.network_engine.domain_manager.URLCanReferToMultipleFiles( url ) ]
        
        all_neighbour_useful_lookup_urls = CG.client_controller.network_engine.domain_manager.NormaliseURLs( all_neighbour_useful_lookup_urls )
        
        untrustworthy_domains = set()
        untrustworthy_hashes = set()
        
        for lookup_url in lookup_urls:
            
            lookup_url_domain = ClientNetworkingFunctions.ConvertURLIntoDomain( lookup_url )
            
            if lookup_url_domain in untrustworthy_domains:
                
                continue
                
            
            results = CG.client_controller.Read( 'url_statuses', lookup_url )
            
            # I was tempted to write a duplicate-merge system here that would discount lesser quality dupes, but what metadata to assign is a tricky question!!
            # better solved with an ongoing duplicate content sync than retroactive metadata refetch gubbins
            
            if len( results ) == 0: # if no match found, this is a new URL, no useful data discovered
                
                continue
                
            elif len( results ) > 1: # if more than one file claims this url, it cannot be relied on to guess the file
                
                continue
                
            else: # this url is matched to one known file--sounds good!
                
                file_import_status = results[0]
                
                file_import_status = ClientImportFiles.CheckFileImportStatus( file_import_status )
                
                possible_hash = file_import_status.hash
                
                if possible_hash in untrustworthy_hashes:
                    
                    untrustworthy_domains.add( lookup_url_domain )
                    
                    continue
                    
                
                if preimport_url_check_looks_for_neighbour_spam and FileURLMappingHasUntrustworthyNeighbours( possible_hash, all_neighbour_useful_lookup_urls ):
                    
                    untrustworthy_domains.add( lookup_url_domain )
                    untrustworthy_hashes.add( possible_hash )
                    
                    continue
                    
                
                match_found = True
                
                # we have discovered a single-file match with a hash and no controversial urls; we have a result
                # this may be a 'needs to be imported' result, but that's fine. probably a record of a previously deleted file that is now ok to import
                
                return ( match_found, matches_are_dispositive, file_import_status )
                
            
        
        # no good matches found
        return ( match_found, matches_are_dispositive, ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
        
    
    def GetSearchFileSeeds( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            search_urls = ClientNetworkingFunctions.GetSearchURLs( self.file_seed_data_for_comparison )
            
            search_file_seeds = [ FileSeed( FILE_SEED_TYPE_URL, search_url ) for search_url in search_urls ]
            
        else:
            
            search_file_seeds = [ self ]
            
        
        return search_file_seeds
        
    
    def GetExternalTags( self ):
        
        t = set( self._tags )
        t.update( self._external_filterable_tags )
        
        return t
        
    
    def GetPrimaryURLs( self ):
        
        return set( self._primary_urls )
        
    
    def GetReferralURL( self ):
        
        return self._referral_url
        
    
    def GetSourceURLs( self ):
        
        return set( self._source_urls )
        
    
    def GetHTTPHeaders( self ) -> dict:
        
        return self._request_headers
        
    
    def HasHash( self ):
        
        return self.GetHash() is not None
        
    
    def Import( self, temp_path: str, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, status_hook = None ):
        
        if file_import_options.IsDefault():
            
            file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
        
        file_import_job = ClientImportFiles.FileImportJob( temp_path, file_import_options, human_file_description = self.file_seed_data )
        
        file_import_status = file_import_job.DoWork( status_hook = status_hook )
        
        self.SetStatus( file_import_status.status, note = file_import_status.note )
        self.SetHash( file_import_status.hash )
        
    
    def ImportPath( self, file_seed_cache: "FileSeedCache", file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, loud_or_quiet: int, status_hook = None ):
        
        try:
            
            file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( file_import_options, loud_or_quiet )
            
            if self.file_seed_type != FILE_SEED_TYPE_HDD:
                
                raise HydrusExceptions.VetoException( 'Attempted to import as a path, but I do not think I am a path!' )
                
            
            path = self.file_seed_data
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.VetoException( 'Source file does not exist!' )
                
            
            ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
            
            try:
                
                if status_hook is not None:
                    
                    status_hook( 'copying file to temp location' )
                    
                
                HydrusPaths.MirrorFile( path, temp_path )
                
                self.Import( temp_path, file_import_options, status_hook = status_hook )
                
            finally:
                
                HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
                
            
            self.WriteContentUpdates( file_import_options = file_import_options )
            
        except HydrusExceptions.VetoException as e:
            
            self.SetStatus( CC.STATUS_VETOED, note = str( e ) )
            
        except HydrusExceptions.UnsupportedFileException as e:
            
            self.SetStatus( CC.STATUS_ERROR, note = str( e ) )
            
        except Exception as e:
            
            self.SetStatus( CC.STATUS_ERROR, exception = e )
            
        
        file_seed_cache.NotifyFileSeedsUpdated( ( self, ) )
        
    
    def IsAPostURL( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            try:
                
                ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
                
            except HydrusExceptions.URLClassException:
                
                return False
                
            
            if url_type == HC.URL_TYPE_POST:
                
                return True
                
            
        
        return False
        
    
    def IsDeleted( self ):
        
        return self.status == CC.STATUS_DELETED
        
    
    def IsLocalFileImport( self ):
        
        return self.file_seed_type == FILE_SEED_TYPE_HDD
        
    
    def IsURLFileImport( self ):
        
        return self.file_seed_type == FILE_SEED_TYPE_URL
        
    
    def Normalise( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            try:
                
                self.file_seed_data = CG.client_controller.network_engine.domain_manager.NormaliseURL( self.file_seed_data, for_server = True )
                self.file_seed_data_for_comparison = CG.client_controller.network_engine.domain_manager.NormaliseURL( self.file_seed_data )
                
            except HydrusExceptions.URLClassException:
                
                pass
                
            
        
    
    def PredictPreImportStatus( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy, note_import_options: NoteImportOptions.NoteImportOptions, file_url = None ):
        
        ( hash_match_found, hash_matches_are_dispositive, hash_file_import_status ) = self.GetPreImportStatusPredictionHash( file_import_options )
        ( url_match_found, url_matches_are_dispositive, url_file_import_status ) = self.GetPreImportStatusPredictionURL( file_import_options, file_url = file_url )
        
        # now let's set the prediction
        
        if hash_match_found and hash_matches_are_dispositive:
            
            file_import_status = hash_file_import_status
            
        elif url_match_found and url_matches_are_dispositive:
            
            file_import_status = url_file_import_status
            
        else:
            
            # prefer the one that says already in db/previously deleted
            if hash_file_import_status.ShouldImport( file_import_options.GetFileFilteringImportOptions() ):
                
                file_import_status = url_file_import_status
                
            else:
                
                file_import_status = hash_file_import_status
                
            
        
        # and make some recommendations
        
        should_download_file = file_import_status.ShouldImport( file_import_options.GetFileFilteringImportOptions() )
        
        should_download_metadata = should_download_file # if we want the file, we need the metadata to get the file_url!
        
        # but if we otherwise still want to force some tags, let's do it
        if not should_download_metadata and tag_import_options.WorthFetchingTags():
            
            url_override = url_file_import_status.AlreadyInDB() and tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB()
            hash_override = hash_file_import_status.AlreadyInDB() and tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB()
            
            if url_override or hash_override:
                
                should_download_metadata = True
                
            
        
        if not should_download_metadata and note_import_options.GetGetNotes():
            
            # here we could have a 'fetch notes even if url known and file already in db' option
            
            pass
            
        
        # update private status store if predictions are useful
        
        if self.status == CC.STATUS_UNKNOWN and not should_download_file:
            
            self.status = file_import_status.status
            
            if file_import_status.hash is not None:
                
                self._hashes[ 'sha256' ] = file_import_status.hash
                
            
            self.note = file_import_status.note
            
            self._UpdateModified()
            
        
        return ( should_download_metadata, should_download_file )
        
    
    def PresentToPage( self, page_key: bytes ):
        
        hash = self.GetHash()
        
        if hash is not None:
            
            media_result = CG.client_controller.Read( 'media_result', hash )
            
            # TODO: rewangle this to a GUI-level overseer that'll do Qt signals or whatever. page_key is probably unavoidable
            CG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
            
        
    
    def SetFileSeedData( self, file_seed_data: str ):
        
        self.file_seed_data = file_seed_data
        self.file_seed_data_for_comparison = file_seed_data
        
        self.Normalise() # this fixes the comparison file seed data and fails safely
        
    
    def SetHash( self, hash ):
        
        if hash is not None:
            
            self._hashes[ 'sha256' ] = hash
            
        
    
    def SetReferralURL( self, referral_url: str ):
        
        self._referral_url = referral_url
        
    
    def SetStatus( self, status: int, note: str = '', exception = None ):
        
        if exception is not None:
            
            first_line = HydrusText.GetFirstLine( repr( exception ) )
            
            note = f'{first_line}{HC.UNICODE_ELLIPSIS} (Copy note to see full error)'
            note += '\n'
            note += traceback.format_exc()
            
        
        self.status = status
        self.note = note
        
        if status == CC.STATUS_UNKNOWN:
            
            # if user is 'try again'ing for a complicated 'the destination file changed' situation,
            # we want to scrub any db-assigned sha256 that was allocated by a previous 'already in db' file import result
            # also kill any md5 or whatever, just in case that was causing the original mess-up
            self._hashes = {}
            
        
        self._UpdateModified()
        
    
    def ShouldPresent( self, presentation_import_options: PresentationImportOptions.PresentationImportOptions ):
        
        if not self.HasHash():
            
            return False
            
        
        was_just_imported = not HydrusTime.TimeHasPassed( self.modified + 5 )
        
        should_check_location = not was_just_imported
        
        return presentation_import_options.ShouldPresentHashAndStatus( self.GetHash(), self.status, should_check_location = should_check_location )
        
    
    def WorksInNewSystem( self ):
        
        if self.file_seed_type == FILE_SEED_TYPE_URL:
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
            
            if url_type == HC.URL_TYPE_FILE:
                
                return True
                
            
            if url_type == HC.URL_TYPE_POST and can_parse:
                
                return True
                
            
            if url_type == HC.URL_TYPE_UNKNOWN and self._referral_url is not None: # this is likely be a multi-file child of a post url file_seed
                
                ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( self._referral_url )
                
                if url_type == HC.URL_TYPE_POST: # we must have got here through parsing that m8, so let's assume this is an unrecognised file url
                    
                    return True
                    
                
            
        
        return False
        
    
    def WorkOnURL( self, file_seed_cache: "FileSeedCache", status_hook, network_job_factory, network_job_presentation_context_factory, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, loud_or_quiet: int, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        did_substantial_work = False
        
        try:
            
            ClientNetworkingFunctions.CheckLooksLikeAFullURL( self.file_seed_data )
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.file_seed_data )
            
            if url_type not in ( HC.URL_TYPE_POST, HC.URL_TYPE_FILE, HC.URL_TYPE_UNKNOWN ):
                
                raise HydrusExceptions.VetoException( 'This URL appeared to be a "{}", which is not a File or Post URL!'.format( match_name ) )
                
            
            if url_type == HC.URL_TYPE_POST and not can_parse:
                
                raise HydrusExceptions.VetoException( 'Cannot parse {}: {}'.format( match_name, cannot_parse_reason ) )
                
            
            file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( file_import_options, loud_or_quiet )
            tag_import_options = self._SetupTagImportOptions( tag_import_options )
            note_import_options = self._SetupNoteImportOptions( note_import_options )
            
            status_hook( 'checking url status' )
            
            ( should_download_metadata, should_download_file ) = self.PredictPreImportStatus( file_import_options, tag_import_options, note_import_options )
            
            if self.IsAPostURL():
                
                if should_download_metadata:
                    
                    did_substantial_work = True
                    
                    post_url = self.file_seed_data
                    
                    ( url_to_fetch, parser ) = CG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
                    
                    status_hook( 'downloading file page' )
                    
                    network_job = network_job_factory( 'GET', url_to_fetch, referral_url = self._referral_url )
                    
                    for ( key, value ) in self._request_headers.items():
                        
                        network_job.AddAdditionalHeader( key, value )
                        
                    
                    CG.client_controller.network_engine.AddJob( network_job )
                    
                    with network_job_presentation_context_factory( network_job ) as njpc:
                        
                        network_job.WaitUntilDone()
                        
                    
                    parsing_text = network_job.GetContentText()
                    
                    # this headache can go when I do my own 3XX redirects?
                    actual_fetched_url = network_job.GetActualFetchedURL()
                    
                    url_for_child_referral = actual_fetched_url
                    
                    if actual_fetched_url != url_to_fetch:
                        
                        # we have redirected, a 3XX response
                        
                        ( actual_url_type, actual_match_name, actual_can_parse, actual_cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( actual_fetched_url )
                        
                        if actual_url_type == HC.URL_TYPE_POST and actual_can_parse:
                            
                            self._AddPrimaryURLs( ( actual_fetched_url, ) )
                            
                            post_url = actual_fetched_url
                            
                            ( url_to_fetch, parser ) = CG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( post_url )
                            
                        
                    
                    parsing_context = {}
                    
                    parsing_context[ 'post_url' ] = post_url
                    parsing_context[ 'url' ] = url_to_fetch
                    
                    parser = typing.cast( ClientParsing.PageParser, parser )
                    
                    parsed_posts = parser.Parse( parsing_context, parsing_text )
                    
                    if len( parsed_posts ) == 0:
                        
                        ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
                        
                        it_was_a_real_file = False
                        
                        try:
                            
                            network_job.WriteContentBytesToPath( temp_path )
                            
                            mime = HydrusFileHandling.GetMime( temp_path )
                            
                            if mime in HC.ALLOWED_MIMES:
                                
                                status_hook( 'page was actually a file, trying to import' )
                                
                                self.Import( temp_path, file_import_options, status_hook = status_hook )
                                
                                it_was_a_real_file = True
                                
                            
                        except Exception as e:
                            
                            # something crazy happened, like FFMPEG thinking JSON was an MP4 wew, so let's bail out
                            raise HydrusExceptions.VetoException( 'The parser found nothing in the document, and while the document initially seemed to actually be an importable file, it looks like it failed to import too!' )
                            
                        finally:
                            
                            HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
                            
                        
                        if not it_was_a_real_file:
                            
                            raise HydrusExceptions.VetoException( 'The parser found nothing in the document, nor did it seem to be an importable file!' )
                            
                        
                    elif len( parsed_posts ) > 1:
                        
                        # multiple child urls generated by a subsidiary page parser
                        
                        file_seeds = ClientImporting.ConvertParsedPostsToFileSeeds( parsed_posts, url_for_child_referral, file_import_options )
                        
                        for file_seed in file_seeds:
                            
                            self._GiveChildFileSeedMyInfo( file_seed, url_for_child_referral )
                            
                        
                        try:
                            
                            my_index = file_seed_cache.GetFileSeedIndex( self )
                            
                            insertion_index = my_index + 1
                            
                        except Exception as e:
                            
                            insertion_index = len( file_seed_cache )
                            
                        
                        num_urls_added = file_seed_cache.InsertFileSeeds( insertion_index, file_seeds )
                        
                        status = CC.STATUS_SUCCESSFUL_AND_CHILD_FILES
                        note = f'Found {HydrusNumbers.ToHumanInt( num_urls_added )} new URLs in {HydrusNumbers.ToHumanInt( len( parsed_posts ) )} sub-posts.'
                        
                        self.SetStatus( status, note = note )
                        
                    else:
                        
                        # no subsidiary page parser results, just one
                        
                        parsed_post = parsed_posts[0]
                        
                        self.AddParsedPost( parsed_post, file_import_options )
                        
                        self.CheckPreFetchMetadata( tag_import_options )
                        
                        desired_urls = parsed_post.GetURLs( ( HC.URL_TYPE_DESIRED, ), only_get_top_priority = True )
                        
                        child_urls = []
                        
                        if len( desired_urls ) == 0:
                            
                            raise HydrusExceptions.VetoException( 'Could not find a file or post URL to download!' )
                            
                        elif len( desired_urls ) == 1:
                            
                            desired_url = desired_urls[0]
                            
                            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( desired_url )
                            
                            if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_UNKNOWN ):
                                
                                file_url = desired_url
                                
                                ( should_download_metadata, should_download_file ) = self.PredictPreImportStatus( file_import_options, tag_import_options, note_import_options, file_url )
                                
                                if should_download_file:
                                    
                                    # this could become an url class property on the post url url class
                                    override_bandwidth = CG.client_controller.new_options.GetBoolean( 'override_bandwidth_on_file_urls_from_post_urls' )
                                    
                                    self.DownloadAndImportRawFile( file_url, file_import_options, loud_or_quiet, network_job_factory, network_job_presentation_context_factory, status_hook, override_bandwidth = override_bandwidth, spawning_url = url_to_fetch, forced_referral_url = url_for_child_referral, file_seed_cache = file_seed_cache )
                                    
                                
                            elif url_type == HC.URL_TYPE_POST and can_parse:
                                
                                # a pixiv mode=medium page has spawned a mode=manga page, so we need a new file_seed to go pursue that
                                
                                child_urls = [ desired_url ]
                                
                            else:
                                
                                if can_parse:
                                    
                                    raise HydrusExceptions.VetoException( 'Found a URL--{}--but it was not a file/post URL!'.format( desired_url ) )
                                    
                                else:
                                    
                                    raise HydrusExceptions.VetoException( 'Found a URL--{}--but it was not a file/post URL! Also, even then, it seems I cannot parse it anyway: {}'.format( desired_url, cannot_parse_reason ) )
                                    
                                
                            
                        else:
                            
                            child_urls = desired_urls
                            
                        
                        child_urls = HydrusLists.DedupeList( child_urls )
                        
                        if len( child_urls ) > 0:
                            
                            child_file_seeds = []
                            
                            for child_url in child_urls:
                                
                                file_seed = FileSeed( FILE_SEED_TYPE_URL, child_url )
                                
                                self._GiveChildFileSeedMyInfo( file_seed, url_for_child_referral )
                                
                                child_file_seeds.append( file_seed )
                                
                            
                            try:
                                
                                my_index = file_seed_cache.GetFileSeedIndex( self )
                                
                                insertion_index = my_index + 1
                                
                            except Exception as e:
                                
                                insertion_index = len( file_seed_cache )
                                
                            
                            num_urls_added = file_seed_cache.InsertFileSeeds( insertion_index, child_file_seeds )
                            
                            status = CC.STATUS_SUCCESSFUL_AND_CHILD_FILES
                            note = 'Found {} new URLs in one post.'.format( HydrusNumbers.ToHumanInt( num_urls_added ) )
                            
                            self.SetStatus( status, note = note )
                            
                        
                    
                
            else:
                
                if should_download_file:
                    
                    self.CheckPreFetchMetadata( tag_import_options )
                    
                    did_substantial_work = True
                    
                    file_url = self.file_seed_data
                    
                    self.DownloadAndImportRawFile( file_url, file_import_options, loud_or_quiet, network_job_factory, network_job_presentation_context_factory, status_hook, spawning_url = self._referral_url, file_seed_cache = file_seed_cache )
                    
                
            
            did_substantial_work |= self.WriteContentUpdates( file_import_options = file_import_options, tag_import_options = tag_import_options, note_import_options = note_import_options )
            
            if self.status == CC.STATUS_UNKNOWN:
                
                raise HydrusExceptions.VetoException( 'Managed to work this job without getting a result! Please report to hydrus_dev!' )
                
            
        except HydrusExceptions.ShutdownException:
            
            return False
            
        except ( HydrusExceptions.VetoException, HydrusExceptions.URLClassException ) as e:
            
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
            
        except HydrusExceptions.CensorshipException:
            
            status = CC.STATUS_VETOED
            note = 'site reports http status code 451: Unavailable For Legal Reasons'
            
            self.SetStatus( status, note = note )
            
            status_hook( '451 censorship!' )
            
            time.sleep( 2 )
            
        except HydrusExceptions.UnsupportedFileException as e:
            
            status = CC.STATUS_ERROR
            
            note = str( e )
            
            self.SetStatus( status, note = note )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            self.SetStatus( status, exception = e )
            
            status_hook( 'error!' )
            
            time.sleep( 3 )
            
        finally:
            
            file_seed_cache.NotifyFileSeedsUpdated( ( self, ) )
            
        
        return did_substantial_work
        
    
    def WriteContentUpdates( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy | None = None, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy | None = None, note_import_options: NoteImportOptions.NoteImportOptions | None = None ):
        
        did_work = False
        
        if self.status == CC.STATUS_ERROR:
            
            return did_work
            
        
        hash = self.GetHash()
        
        if hash is None:
            
            return did_work
            
        
        # changed this to say that urls alone are not 'did work' since all url results are doing this, and when they have no tags, they are usually superfast db hits anyway
        # better to scream through an 'already in db' import list that flicker
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        potentially_associable_urls = set()
        
        media_result = None
        
        if file_import_options is not None:
            
            if file_import_options.GetLocationImportOptions().ShouldAssociatePrimaryURLs():
                
                potentially_associable_urls.update( self._primary_urls )
                
                if self.file_seed_type == FILE_SEED_TYPE_URL:
                    
                    potentially_associable_urls.add( self.file_seed_data_for_comparison )
                    
                    # TODO: Ok, if we get URL renaming, we'll want to say domain_manager.GetCanonicalDomain( self.file_seed_data ) or something here!
                    domain = ClientNetworkingFunctions.ConvertURLIntoDomain( self.file_seed_data )
                    
                    if self.source_time is None:
                        
                        domain_modified_timestamp = self.created
                        
                    else:
                        
                        domain_modified_timestamp = self.source_time
                        
                    
                    if ClientTime.TimestampIsSensible( domain_modified_timestamp ):
                        
                        timestamp_data = ClientTime.TimestampData.STATICDomainModifiedTime( domain, HydrusTime.MillisecondiseS( domain_modified_timestamp ) )
                        
                        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_ADD, ( ( hash, ), timestamp_data ) )
                        
                        content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
                        
                    
                    if self._cloudflare_last_modified_time is not None and ClientTime.TimestampIsSensible( self._cloudflare_last_modified_time ):
                        
                        timestamp_data = ClientTime.TimestampData.STATICDomainModifiedTime( 'cloudflare.com', HydrusTime.MillisecondiseS( self._cloudflare_last_modified_time ) )
                        
                        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_ADD, ( ( hash, ), timestamp_data ) )
                        
                        content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
                        
                    
                
                if self._referral_url is not None:
                    
                    potentially_associable_urls.add( self._referral_url )
                    
                
            
            if file_import_options.GetLocationImportOptions().ShouldAssociateSourceURLs():
                
                potentially_associable_urls.update( self._source_urls )
                
            
            if self.status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                
                if media_result is None:
                    
                    media_result = CG.client_controller.Read( 'media_result', hash )
                    
                
                extra_content_update_package = file_import_options.GetLocationImportOptions().GetAlreadyInDBPostImportContentUpdatePackage( media_result )
                
                content_update_package.AddContentUpdatePackage( extra_content_update_package )
                
            
        
        associable_urls = ClientNetworkingFunctions.NormaliseAndFilterAssociableURLs( potentially_associable_urls )
        
        if len( associable_urls ) > 0:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( associable_urls, ( hash, ) ) )
            
            content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
            
        
        if tag_import_options is None:
            
            if len( self._external_additional_service_keys_to_tags ) > 0:
                
                content_update_package.AddServiceKeysToTags( ( hash, ), self._external_additional_service_keys_to_tags )
                
                did_work = True
                
            
        else:
            
            if media_result is None:
                
                media_result = CG.client_controller.Read( 'media_result', hash )
                
            
            for ( service_key, content_updates ) in tag_import_options.GetContentUpdatePackage( self.status, media_result, set( self._tags ), external_filterable_tags = self._external_filterable_tags, external_additional_service_keys_to_tags = self._external_additional_service_keys_to_tags ).IterateContentUpdates():
                
                content_update_package.AddContentUpdates( service_key, content_updates )
                
                did_work = True
                
            
        
        if note_import_options is not None:
            
            if media_result is None:
                
                media_result = CG.client_controller.Read( 'media_result', hash )
                
            
            names_and_notes = sorted( self._names_and_notes_dict.items() )
            
            for ( service_key, content_updates ) in note_import_options.GetContentUpdatePackage( media_result, names_and_notes ).IterateContentUpdates():
                
                content_update_package.AddContentUpdates( service_key, content_updates )
                
                did_work = True
                
            
        
        if content_update_package.HasContent():
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
        return did_work
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED ] = FileSeed

class FileSeedCacheStatus( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE_STATUS
    SERIALISABLE_NAME = 'Import File Status Cache Status'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        self._generation_time = HydrusTime.GetNow()
        self._statuses_to_counts = collections.Counter()
        self._latest_added_time = 0
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_statuses_to_counts = list( self._statuses_to_counts.items() )
        
        return ( self._generation_time, serialisable_statuses_to_counts, self._latest_added_time )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._generation_time, serialisable_statuses_to_counts, self._latest_added_time ) = serialisable_info
        
        self._statuses_to_counts = collections.Counter()
        
        self._statuses_to_counts.update( dict( serialisable_statuses_to_counts ) )
        
    
    def GetFileSeedCount( self, status: int | None = None ) -> int:
        
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
                    
                    status_text += HydrusNumbers.ValueRangeToPrettyString( total_processed, total )
                    
                else:
                    
                    status_text += HydrusNumbers.ToHumanInt( total_processed )
                    
                
                show_new_on_file_seed_short_summary = CG.client_controller.new_options.GetBoolean( 'show_new_on_file_seed_short_summary' )
                
                if show_new_on_file_seed_short_summary and num_successful_and_new:
                    
                    status_text += ' - {}N'.format( HydrusNumbers.ToHumanInt( num_successful_and_new ) )
                    
                
                simple_status_strings = []
                
                if num_ignored > 0:
                    
                    simple_status_strings.append( '{}Ign'.format( HydrusNumbers.ToHumanInt( num_ignored ) ) )
                    
                
                show_deleted_on_file_seed_short_summary = CG.client_controller.new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' )
                
                if show_deleted_on_file_seed_short_summary and num_deleted > 0:
                    
                    simple_status_strings.append( '{}D'.format( HydrusNumbers.ToHumanInt( num_deleted ) ) )
                    
                
                if num_failed > 0:
                    
                    simple_status_strings.append( '{}F'.format( HydrusNumbers.ToHumanInt( num_failed ) ) )
                    
                
                if num_skipped > 0:
                    
                    simple_status_strings.append( '{}S'.format( HydrusNumbers.ToHumanInt( num_skipped ) ) )
                    
                
                if len( simple_status_strings ) > 0:
                    
                    status_text += ' - {}'.format( ''.join( simple_status_strings ) )
                    
                
            
        else:
            
            status_strings = []
            
            num_successful = num_successful_and_new + num_successful_but_redundant
            
            if num_successful > 0:
                
                s = '{} successful'.format( HydrusNumbers.ToHumanInt( num_successful ) )
                
                if num_successful_and_new > 0:
                    
                    if num_successful_but_redundant > 0:
                        
                        s += ' ({} already in db)'.format( HydrusNumbers.ToHumanInt( num_successful_but_redundant ) )
                        
                    
                else:
                    
                    s += ' (all already in db)'
                    
                
                status_strings.append( s )
                
            
            if num_ignored > 0:
                
                status_strings.append( '{} ignored'.format( HydrusNumbers.ToHumanInt( num_ignored ) ) )
                
            
            if num_deleted > 0:
                
                status_strings.append( '{} previously deleted'.format( HydrusNumbers.ToHumanInt( num_deleted ) ) )
                
            
            if num_failed > 0:
                
                status_strings.append( '{} failed'.format( HydrusNumbers.ToHumanInt( num_failed ) ) )
                
            
            if num_skipped > 0:
                
                status_strings.append( '{} skipped'.format( HydrusNumbers.ToHumanInt( num_skipped ) ) )
                
            
            status_text = ', '.join( status_strings )
            
        
        return status_text
        
    
    def GetStatusesToCounts( self ) -> typing.Mapping[ int, int ]:
        
        return self._statuses_to_counts
        
    
    def GetValueRange( self ) -> tuple[ int, int ]:
        
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

def WalkToNextFileSeed( status, starting_file_seed, file_seeds, file_seeds_to_indices, statuses_to_file_seeds ):
    
    # the file seed given is the starting point and can be the answer
    # but if it is wrong, or no longer tracked, then let's walk through them until we get one, or None
    # along the way, we'll note what's in the wrong place
    
    wrong_file_seeds = set()
    
    if starting_file_seed in file_seeds_to_indices:
        
        index = file_seeds_to_indices[ starting_file_seed ]
        
    else:
        
        index = 0
        
    
    file_seed = starting_file_seed
    
    while True:
        
        # no need to walk further, we are good
        
        if file_seed.status == status:
            
            result = file_seed
            
            break
            
        
        # this file seed has the wrong status, move on
        
        if file_seed in statuses_to_file_seeds[ status ]:
            
            wrong_file_seeds.add( file_seed )
            
        
        index += 1
        
        if index >= len( file_seeds ):
            
            result = None
            
            break
            
        
        file_seed = file_seeds[ index ]
        
    
    return ( result, wrong_file_seeds )
    

class FileSeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE
    SERIALISABLE_NAME = 'Import File Status Cache'
    SERIALISABLE_VERSION = 8
    
    def __init__( self ):
        
        super().__init__()
        
        self._file_seeds = HydrusSerialisable.SerialisableList()
        
        self._file_seeds_to_indices = {}
        
        # if there's a file seed here, it is the earliest
        # if there's none in here, we know the count is 0
        # if status is absent, we don't know
        self._observed_statuses_to_next_file_seeds = {}
        
        self._file_seeds_to_observed_statuses = {}
        self._statuses_to_file_seeds = collections.defaultdict( set )
        
        self._file_seed_cache_key = HydrusData.GenerateKey()
        
        self._status_cache = FileSeedCacheStatus()
        
        self._status_dirty = True
        self._statuses_to_file_seeds_dirty = True
        self._file_seeds_to_indices_dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._file_seeds )
        
    
    def _FixStatusesToFileSeeds( self, file_seeds: collections.abc.Collection[ FileSeed ] ):
        
        if self._statuses_to_file_seeds_dirty:
            
            return
            
        
        file_seeds_to_indices = self._GetFileSeedsToIndices()
        statuses_to_file_seeds = self._GetStatusesToFileSeeds()
        
        if len( file_seeds ) == 0:
            
            return
            
        
        outstanding_others_to_fix = set()
        
        for file_seed in file_seeds:
            
            want_a_record = file_seed in file_seeds_to_indices
            record_exists = file_seed in self._file_seeds_to_observed_statuses
            
            if not want_a_record and not record_exists:
                
                continue
                
            
            correct_status = file_seed.status
            
            if record_exists:
                
                set_status = self._file_seeds_to_observed_statuses[ file_seed ]
                
                if set_status != correct_status or not want_a_record:
                    
                    if set_status in self._observed_statuses_to_next_file_seeds:
                        
                        if self._observed_statuses_to_next_file_seeds[ set_status ] == file_seed:
                            
                            # this 'next' is now wrong, so fast forward to the correct one, or None
                            ( result, wrong_file_seeds ) = WalkToNextFileSeed( set_status, file_seed, self._file_seeds, file_seeds_to_indices, statuses_to_file_seeds )
                            
                            self._observed_statuses_to_next_file_seeds[ set_status ] = result
                            
                            outstanding_others_to_fix.update( wrong_file_seeds )
                            
                        
                    
                    statuses_to_file_seeds[ set_status ].discard( file_seed )
                    
                    del self._file_seeds_to_observed_statuses[ file_seed ]
                    
                    record_exists = False
                    
                
            
            if want_a_record:
                
                if not record_exists:
                    
                    statuses_to_file_seeds[ correct_status ].add( file_seed )
                    
                    self._file_seeds_to_observed_statuses[ file_seed ] = correct_status
                    
                
                if correct_status in self._observed_statuses_to_next_file_seeds:
                    
                    current_next_file_seed = self._observed_statuses_to_next_file_seeds[ correct_status ]
                    
                    if current_next_file_seed is None or file_seeds_to_indices[ file_seed ] < file_seeds_to_indices[ current_next_file_seed ]:
                        
                        self._observed_statuses_to_next_file_seeds[ correct_status ] = file_seed
                        
                    
                
            
        
        outstanding_others_to_fix.difference_update( file_seeds )
        
        if len( outstanding_others_to_fix ) > 0:
            
            self._FixStatusesToFileSeeds( outstanding_others_to_fix )
            
        
    
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
            
            statuses_to_file_seeds = self._GetStatusesToFileSeeds()
            file_seeds_to_indices = self._GetFileSeedsToIndices()
            
            return sorted( statuses_to_file_seeds[ status ], key = lambda f_s: file_seeds_to_indices[ f_s ] )
            
        
    
    def _GetFileSeedsToIndices( self ) -> dict[ FileSeed, int ]:
        
        if self._file_seeds_to_indices_dirty:
            
            self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
            
            if len( self._file_seeds_to_indices ) != len( self._file_seeds ):
                
                # woah, we have some dupes! maybe url classes changed and renormalisation happened, maybe hydev fixed some bad dupe file paths or something
                # let's correct ourselves now we have the chance; this guy simply cannot handle dupes atm
                
                self._file_seeds = HydrusSerialisable.SerialisableList( HydrusLists.DedupeList( self._file_seeds ) )
                
                self._file_seeds_to_indices = { file_seed : index for ( index, file_seed ) in enumerate( self._file_seeds ) }
                
                self._statuses_to_file_seeds_dirty = True
                
            
            self._file_seeds_to_indices_dirty = False
            
        
        return self._file_seeds_to_indices
        
    
    def _GetLatestAddedTime( self ):
        
        if len( self._file_seeds ) == 0:
            
            latest_timestamp = 0
            
        else:
            
            latest_timestamp = max( ( file_seed.created for file_seed in self._file_seeds ) )
            
        
        return latest_timestamp
        
    
    def _GetMyFileSeed( self, file_seed: FileSeed ) -> FileSeed | None:
        
        search_file_seeds = file_seed.GetSearchFileSeeds()
        
        for f_s in self._file_seeds:
            
            if f_s in search_file_seeds:
                
                return f_s
                
            
        
        return None
        
    
    def _GetNextFileSeed( self, status: int ) -> FileSeed | None:
        
        statuses_to_file_seeds = self._GetStatusesToFileSeeds()
        file_seeds_to_indices = self._GetFileSeedsToIndices()
        
        # the problem with this is if a file seed recently changed but 'notifyupdated' hasn't had a chance to go yet
        # there could be a FS in a list other than the one we are looking at that has the status we want
        # _however_, it seems like I do not do any async calls to notifyupdated in the actual FSC, only from notifyupdated to GUI elements, so we _seem_ to be good to talk to this in this way
        
        if status not in self._observed_statuses_to_next_file_seeds:
            
            file_seeds = statuses_to_file_seeds[ status ]
            
            if len( file_seeds ) == 0:
                
                self._observed_statuses_to_next_file_seeds[ status ] = None
                
            else:
                
                self._observed_statuses_to_next_file_seeds[ status ] = min( file_seeds, key = lambda f_s: file_seeds_to_indices[ f_s ] )
                
            
        
        file_seed = self._observed_statuses_to_next_file_seeds[ status ]
        
        if file_seed is None:
            
            return None
            
        
        ( result, wrong_file_seeds ) = WalkToNextFileSeed( status, file_seed, self._file_seeds, file_seeds_to_indices, statuses_to_file_seeds )
        
        self._observed_statuses_to_next_file_seeds[ status ] = result
        
        self._FixStatusesToFileSeeds( wrong_file_seeds )
        
        return file_seed
        
    
    def _GetListOfParentsWithChildren( self ):
        
        list_of_parents_with_children: list[ list[ FileSeed ] ] = []
        current_parent_and_children: list[ FileSeed ] = []
        
        num_additional_children_in_current_batch = 0
        add_children_until_you_hit_a_parent = False
        
        for file_seed in self._file_seeds:
            
            file_seed = typing.cast( FileSeed, file_seed )
            
            if add_children_until_you_hit_a_parent and file_seed.status == CC.STATUS_SUCCESSFUL_AND_CHILD_FILES:
                
                list_of_parents_with_children.append( current_parent_and_children )
                
                current_parent_and_children = []
                
                add_children_until_you_hit_a_parent = False
                
            
            current_parent_and_children.append( file_seed )
            
            if num_additional_children_in_current_batch > 0:
                
                num_additional_children_in_current_batch -= 1
                
            
            if file_seed.status == CC.STATUS_SUCCESSFUL_AND_CHILD_FILES:
                
                note = file_seed.note
                
                try:
                    
                    # Found 2 new URLs in 3 sub-posts.
                    result = re.search( r'(?<=^Found )\d+', note )
                    
                    if result is None:
                        
                        raise Exception()
                        
                    
                    num_additional_children_in_current_batch += max( 0, int( result.group() ) )
                    
                except Exception as e:
                    
                    add_children_until_you_hit_a_parent = True
                    
                
            
            if not add_children_until_you_hit_a_parent and num_additional_children_in_current_batch == 0:
                
                list_of_parents_with_children.append( current_parent_and_children )
                
                current_parent_and_children = []
                
            
        
        if len( current_parent_and_children ) > 0:
            
            list_of_parents_with_children.append( current_parent_and_children )
            
        
        return list_of_parents_with_children
        
    
    def _GetPotentiallyCompactibleFileSeeds( self, compaction_number: int ) -> list[ FileSeed ]:
        
        # get all the file seeds at the start of my list, excluding the n at the end of the list
        # were things simple, this would be self._file_seeds[:-compaction_number], i.e. "abcdef"[:-2] = "abcd"
        # HOWEVER, we need to deal with child posts. our n should discount all child posts
        # so let's break out list into what we guess is parent posts and any children
        # and let's try to make it failsafe, delivering smaller potentially compatible lists when it is uncertain
        
        list_of_parents_with_children = self._GetListOfParentsWithChildren()
        
        list_of_potentially_compactible_parents_with_children = list_of_parents_with_children[ : - compaction_number ]
        
        potentially_compactible_file_seeds = [ file_seed for potentially_compactible_parents_with_children in list_of_potentially_compactible_parents_with_children for file_seed in potentially_compactible_parents_with_children ]
        
        return potentially_compactible_file_seeds
        
    
    def _GetSerialisableInfo( self ):
        
        if not isinstance( self._file_seeds, HydrusSerialisable.SerialisableList ):
            
            self._file_seeds = HydrusSerialisable.SerialisableList( self._file_seeds )
            
        
        return self._file_seeds.GetSerialisableTuple()
        
    
    def _GetSourceTimestampForVelocityCalculations( self, file_seed: FileSeed ):
        
        source_timestamp = file_seed.source_time
        
        if source_timestamp is None:
            
            # decent fallback compromise
            # -30 since added and 'last check' timestamps are often the same, and this messes up calculations
            
            source_timestamp = file_seed.created - 30
            
        
        return source_timestamp
        
    
    def _GetStatusesToCounts( self ):
        
        statuses_to_counts = collections.Counter()
        
        statuses_to_file_seeds = self._GetStatusesToFileSeeds()
        
        for ( status, file_seeds ) in statuses_to_file_seeds.items():
            
            count = len( file_seeds )
            
            if count > 0:
                
                statuses_to_counts[ status ] = count
                
            
        
        return statuses_to_counts
        
    
    def _GetStatusesToFileSeeds( self ) -> dict[ int, set[ FileSeed ] ]:
        
        file_seeds_to_indices = self._GetFileSeedsToIndices()
        
        if self._statuses_to_file_seeds_dirty:
            
            self._file_seeds_to_observed_statuses = {}
            self._statuses_to_file_seeds = collections.defaultdict( set )
            self._observed_statuses_to_next_file_seeds = {}
            
            for ( file_seed, index ) in file_seeds_to_indices.items():
                
                status = file_seed.status
                
                self._statuses_to_file_seeds[ status ].add( file_seed )
                self._file_seeds_to_observed_statuses[ file_seed ] = status
                
                if status not in self._observed_statuses_to_next_file_seeds:
                    
                    self._observed_statuses_to_next_file_seeds[ status ] = file_seed
                    
                else:
                    
                    current_next = self._observed_statuses_to_next_file_seeds[ status ]
                    
                    if current_next is not None and index < file_seeds_to_indices[ current_next ]:
                        
                        self._observed_statuses_to_next_file_seeds[ status ] = file_seed
                        
                    
                
            
            self._statuses_to_file_seeds_dirty = False
            
        
        return self._statuses_to_file_seeds
        
    
    def _HasFileSeed( self, file_seed: FileSeed ):
        
        file_seeds_to_indices = self._GetFileSeedsToIndices()
        
        search_file_seeds = file_seed.GetSearchFileSeeds()
        
        has_file_seed = True in ( search_file_seed in file_seeds_to_indices for search_file_seed in search_file_seeds )
        
        return has_file_seed
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            self._file_seeds = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
            
        
    
    def _NotifyFileSeedsUpdated( self, file_seeds: collections.abc.Collection[ FileSeed ] ):
        
        if len( file_seeds ) == 0:
            
            return
            
        
        CG.client_controller.pub( 'file_seed_cache_file_seeds_updated', self._file_seed_cache_key, file_seeds )
        
    
    def _SetFileSeedsToIndicesDirty( self ):
        
        self._file_seeds_to_indices_dirty = True
        
        self._observed_statuses_to_next_file_seeds = {}
        
    
    def _SetStatusesToFileSeedsDirty( self ):
        
        # this is never actually called in normal usage, which is neat! I think we are 'perfect' on this thing maintaining itself after inital generation
        
        self._statuses_to_file_seeds_dirty = True
        
    
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
                        
                        file_seed = ClientNetworkingFunctions.ConvertHTTPToHTTPS( file_seed )
                        
                    
                    if 'pixiv.net' in parse.netloc:
                        
                        file_seed = ClientNetworkingFunctions.ConvertHTTPToHTTPS( file_seed )
                        
                    
                    if file_seed in good_file_seeds: # we hit a dupe, so skip it
                        
                        continue
                        
                    
                except Exception as e:
                    
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
                        
                    
                except Exception as e:
                    
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
            
        
    
    def AddFileSeeds( self, file_seeds: collections.abc.Collection[ FileSeed ], dupe_try_again = False ):
        
        if len( file_seeds ) == 0:
            
            return 0 
            
        
        updated_or_new_file_seeds = []
        
        with self._lock:
            
            file_seeds_to_indices = self._GetFileSeedsToIndices()
            
            for file_seed in file_seeds:
                
                if self._HasFileSeed( file_seed ):
                    
                    if dupe_try_again:
                        
                        f_s = self._GetMyFileSeed( file_seed )
                        
                        if f_s is not None:
                            
                            if f_s.status == CC.STATUS_ERROR:
                                
                                f_s.SetStatus( CC.STATUS_UNKNOWN )
                                
                                updated_or_new_file_seeds.append( f_s )
                                
                            
                        
                    
                    continue
                    
                
                try:
                    
                    file_seed.Normalise()
                    
                except HydrusExceptions.URLClassException:
                    
                    # this is some borked 'https://' url that makes no sense
                    
                    continue
                    
                
                updated_or_new_file_seeds.append( file_seed )
                
                self._file_seeds.append( file_seed )
                
                index = len( self._file_seeds ) - 1
                
                file_seeds_to_indices[ file_seed ] = index
                
            
            self._FixStatusesToFileSeeds( updated_or_new_file_seeds )
            
            self._SetStatusDirty()
            
        
        self._NotifyFileSeedsUpdated( updated_or_new_file_seeds )
        
        return len( updated_or_new_file_seeds )
        
    
    def AdvanceFileSeed( self, file_seed: FileSeed ):
        
        updated_file_seeds = []
        
        with self._lock:
            
            file_seeds_to_indices = self._GetFileSeedsToIndices()
            
            if file_seed in file_seeds_to_indices:
                
                index = file_seeds_to_indices[ file_seed ]
                
                if index > 0:
                    
                    swapped_file_seed = self._file_seeds[ index - 1 ]
                    
                    self._file_seeds.remove( file_seed )
                    
                    self._file_seeds.insert( index - 1, file_seed )
                    
                    file_seeds_to_indices[ file_seed ] = index - 1
                    file_seeds_to_indices[ swapped_file_seed ] = index
                    
                    updated_file_seeds = [ file_seed, swapped_file_seed ]
                    
                    self._FixStatusesToFileSeeds( updated_file_seeds )
                    
                
            
        
        self._NotifyFileSeedsUpdated( updated_file_seeds )
        
    
    def CanCompact( self, compaction_number: int, compact_before_this_source_time: int ):
        
        with self._lock:
            
            if len( self._file_seeds ) <= compaction_number:
                
                return False
                
            
            potentially_compactible_file_seeds = self._GetPotentiallyCompactibleFileSeeds( compaction_number )
            
            for file_seed in potentially_compactible_file_seeds:
                
                if file_seed.status == CC.STATUS_UNKNOWN:
                    
                    continue
                    
                
                if self._GetSourceTimestampForVelocityCalculations( file_seed ) < compact_before_this_source_time:
                    
                    return True
                    
                
            
        
        return False
        
    
    def Compact( self, compaction_number: int, compact_before_this_source_time: int ):
        
        with self._lock:
            
            if len( self._file_seeds ) <= compaction_number:
                
                return
                
            
            removee_file_seeds = set()
            
            potentially_compactible_file_seeds = self._GetPotentiallyCompactibleFileSeeds( compaction_number )
            
            for file_seed in potentially_compactible_file_seeds:
                
                still_to_do = file_seed.status == CC.STATUS_UNKNOWN
                still_relevant = self._GetSourceTimestampForVelocityCalculations( file_seed ) > compact_before_this_source_time
                
                if not ( still_to_do or still_relevant ):
                    
                    removee_file_seeds.add( file_seed )
                    
                
            
        
        self.RemoveFileSeeds( removee_file_seeds )
        
    
    def DelayFileSeed( self, file_seed: FileSeed ):
        
        updated_file_seeds = []
        
        with self._lock:
            
            file_seeds_to_indices = self._GetFileSeedsToIndices()
            
            if file_seed in file_seeds_to_indices:
                
                index = file_seeds_to_indices[ file_seed ]
                
                if index < len( self._file_seeds ) - 1:
                    
                    swapped_file_seed = self._file_seeds[ index + 1 ]
                    
                    self._file_seeds.remove( file_seed )
                    
                    self._file_seeds.insert( index + 1, file_seed )
                    
                    file_seeds_to_indices[ swapped_file_seed ] = index
                    file_seeds_to_indices[ file_seed ] = index + 1
                    
                    updated_file_seeds = [ file_seed, swapped_file_seed ]
                    
                    self._FixStatusesToFileSeeds( updated_file_seeds )
                    
                
            
        
        self._NotifyFileSeedsUpdated( updated_file_seeds )
        
    
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
            
        
    
    def GetApproxNumMasterFileSeeds( self ):
        
        return len( self._GetListOfParentsWithChildren() )
        
    
    def GetEarliestSourceTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return None
                
            
            earliest_timestamp = min( ( self._GetSourceTimestampForVelocityCalculations( file_seed ) for file_seed in self._file_seeds ) )
            
        
        return earliest_timestamp
        
    
    def GetExampleURLFileSeed( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return None
                
            else:
                
                good_file_seeds = [ file_seed for file_seed in self._file_seeds[-30:] if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES ]
                
                if len( good_file_seeds ) > 0:
                    
                    example_seed = random.choice( good_file_seeds )
                    
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
        
        with self._lock:
            
            if status is None:
                
                result = len( self._file_seeds )
                
            else:
                
                statuses_to_file_seeds = self._GetStatusesToFileSeeds()
                
                return len( statuses_to_file_seeds[ status ] )
                
            
        
        return result
        
    
    def GetFileSeeds( self, status: int = None ):
        
        with self._lock:
            
            return self._GetFileSeeds( status )
            
        
    
    def GetFileSeedIndex( self, file_seed: FileSeed ):
        
        with self._lock:
            
            file_seeds_to_indices = self._GetFileSeedsToIndices()
            
            return file_seeds_to_indices[ file_seed ]
            
        
    
    def GetFirstFileSeed( self ) -> FileSeed | None:
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return None
                
            else:
                
                return self._file_seeds[0]
                
            
        
    
    def GetHashes( self ):
        
        with self._lock:
            
            hashes = [ file_seed.GetHash() for file_seed in self._file_seeds if file_seed.HasHash() ]
            
        
        return hashes
        
    
    def GetLatestSourceTime( self ):
        
        with self._lock:
            
            if len( self._file_seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetSourceTimestampForVelocityCalculations( file_seed ) for file_seed in self._file_seeds ) )
            
        
        return latest_timestamp
        
    
    def GetNextFileSeed( self, status: int ) -> FileSeed | None:
        
        with self._lock:
            
            return self._GetNextFileSeed( status )
            
        
    
    def GetNumNewFilesSince( self, since: int ):
        
        num_files = 0
        
        with self._lock:
            
            for file_seed in self._file_seeds:
                
                source_timestamp = self._GetSourceTimestampForVelocityCalculations( file_seed )
                
                if source_timestamp >= since:
                    
                    num_files += 1
                    
                
            
        
        return num_files
        
    
    def GetPresentedHashes( self, presentation_import_options: PresentationImportOptions.PresentationImportOptions ):
        
        with self._lock:
            
            hashes_and_statuses = [ ( file_seed.GetHash(), file_seed.status ) for file_seed in self._file_seeds if file_seed.HasHash() ]
            
        
        return presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
    
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
            
        
    
    def InsertFileSeeds( self, index: int, file_seeds: collections.abc.Collection[ FileSeed ] ):
        
        file_seeds = HydrusLists.DedupeList( file_seeds )
        
        with self._lock:
            
            new_file_seeds = []
            
            for file_seed in file_seeds:
                
                file_seed.Normalise()
                
                if self._HasFileSeed( file_seed ):
                    
                    continue
                    
                
                new_file_seeds.append( file_seed )
                
            
            if len( file_seeds ) == 0:
                
                return 0
                
            
            index = min( index, len( self._file_seeds ) )
            
            original_insertion_index = index
            
            for file_seed in new_file_seeds:
                
                self._file_seeds.insert( index, file_seed )
                
                index += 1
                
            
            self._SetFileSeedsToIndicesDirty()
            
            self._SetStatusDirty()
            
            self._FixStatusesToFileSeeds( new_file_seeds )
            
            updated_file_seeds = self._file_seeds[ original_insertion_index : ]
            
        
        self._NotifyFileSeedsUpdated( updated_file_seeds )
        
        return len( new_file_seeds )
        
    
    def IsURLFileSeeds( self ) -> bool:
        
        if len( self._file_seeds ) == 0:
            
            return True
            
        
        first = self._file_seeds[0]
        
        return first.file_seed_type == FILE_SEED_TYPE_URL
        
    
    def NotifyFileSeedsUpdated( self, file_seeds: collections.abc.Collection[ FileSeed ] ):
        
        if len( file_seeds ) == 0:
            
            return
            
        
        with self._lock:
            
            self._FixStatusesToFileSeeds( file_seeds )
            
            self._SetStatusDirty()
            
        
        self._NotifyFileSeedsUpdated( file_seeds )
        
    
    def RemoveFileSeeds( self, file_seeds_to_delete: collections.abc.Iterable[ FileSeed ] ):
        
        with self._lock:
            
            file_seeds_to_indices = self._GetFileSeedsToIndices()
            
            file_seeds_to_delete = { file_seed for file_seed in file_seeds_to_delete if file_seed in file_seeds_to_indices }
            
            if len( file_seeds_to_delete ) == 0:
                
                return
                
            
            earliest_affected_index = min( ( file_seeds_to_indices[ file_seed ] for file_seed in file_seeds_to_delete ) )
            
            self._file_seeds = HydrusSerialisable.SerialisableList( [ file_seed for file_seed in self._file_seeds if file_seed not in file_seeds_to_delete ] )
            
            self._SetFileSeedsToIndicesDirty()
            
            self._SetStatusDirty()
            
            self._FixStatusesToFileSeeds( file_seeds_to_delete )
            
            index_shuffled_file_seeds = self._file_seeds[ earliest_affected_index : ]
            
        
        updated_file_seeds = file_seeds_to_delete.union( index_shuffled_file_seeds )
        
        self._NotifyFileSeedsUpdated( updated_file_seeds )
        
    
    def RemoveFileSeedsByStatus( self, statuses_to_remove: collections.abc.Collection[ int ] ):
        
        with self._lock:
            
            file_seeds_to_delete = [ file_seed for file_seed in self._file_seeds if file_seed.status in statuses_to_remove ]
            
        
        self.RemoveFileSeeds( file_seeds_to_delete )
        
    
    def RemoveAllButUnknownFileSeeds( self ):
        
        with self._lock:
            
            file_seeds_to_delete = [ file_seed for file_seed in self._file_seeds if file_seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveFileSeeds( file_seeds_to_delete )
        
    
    def RenormaliseURLs( self ):
        
        with self._lock:
            
            # first make a fake pool of what we'll end up with and figure out what to discard, given that
            
            file_seeds_to_remove = []
            
            new_file_seeds_fast = set()
            
            for file_seed in self._file_seeds:
                
                file_seed_copy = file_seed.Duplicate()
                
                file_seed_copy.Normalise()
                
                if file_seed_copy not in new_file_seeds_fast:
                    
                    new_file_seeds_fast.add( file_seed_copy )
                    
                else:
                    
                    file_seeds_to_remove.append( file_seed )
                    
                
            
        
        self.RemoveFileSeeds( file_seeds_to_remove )
        
        with self._lock:
            
            for file_seed in self._file_seeds:
                
                file_seed.Normalise()
                
            
        
        self._NotifyFileSeedsUpdated( self._file_seeds )
        
    
    def RetryFailed( self ):
        
        with self._lock:
            
            failed_file_seeds = self._GetFileSeeds( CC.STATUS_ERROR )
            
            for file_seed in failed_file_seeds:
                
                file_seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
            self._FixStatusesToFileSeeds( failed_file_seeds )
            
            self._SetStatusDirty()
            
        
        self._NotifyFileSeedsUpdated( failed_file_seeds )
        
    
    def RetryIgnored( self, ignored_regex = None ):
        
        with self._lock:
            
            ignored_file_seeds = self._GetFileSeeds( CC.STATUS_VETOED )
            
            for file_seed in ignored_file_seeds:
                
                if ignored_regex is not None:
                    
                    if re.search( ignored_regex, file_seed.note ) is None:
                        
                        continue
                        
                    
                
                file_seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
            self._FixStatusesToFileSeeds( ignored_file_seeds )
            
            self._SetStatusDirty()
            
        
        self._NotifyFileSeedsUpdated( ignored_file_seeds )
        
    
    def Reverse( self ):
        
        with self._lock:
            
            self._file_seeds.reverse()
            
            self._SetFileSeedsToIndicesDirty()
            
            updated_file_seeds = list( self._file_seeds )
            
        
        self._NotifyFileSeedsUpdated( updated_file_seeds )
        
    
    def SetStatusToStatus( self, old_status, new_status ):
        
        with self._lock:
            
            file_seeds = self._GetFileSeeds( old_status )
            
            for file_seed in file_seeds:
                
                file_seed.SetStatus( new_status )
                
            
            self._FixStatusesToFileSeeds( file_seeds )
            
            self._SetStatusDirty()
            
        
        self._NotifyFileSeedsUpdated( file_seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache.HasWorkToDo()
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEED_CACHE ] = FileSeedCache

def GenerateFileSeedCachesStatus( file_seed_caches: collections.abc.Iterable[ FileSeedCache ] ):
    
    fscs = FileSeedCacheStatus()
    
    for file_seed_cache in file_seed_caches:
        
        fscs.Merge( file_seed_cache.GetStatus() )
        
    
    return fscs
    
