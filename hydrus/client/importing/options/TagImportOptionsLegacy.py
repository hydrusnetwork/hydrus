import collections.abc
import os
import re

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

class FilenameTaggingOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS
    SERIALISABLE_NAME = 'Filename Tagging Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        super().__init__()
        
        self._tags_for_all = set()
        
        # Note we are leaving this here for a bit, even though it is no longer used, to leave a window so ImportFolder can rip existing values
        # it can be nuked in due time
        self._load_from_neighbouring_txt_files = False
        
        self._add_filename = ( False, 'filename' )
        
        self._directories_dict = {}
        
        for index in ( 0, 1, 2, -3, -2, -1 ):
            
            self._directories_dict[ index ] = ( False, '' )
            
        
        self._quick_namespaces = []
        self._regexes = []
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_directories_dict = list(self._directories_dict.items())
        
        return ( list( self._tags_for_all ), self._load_from_neighbouring_txt_files, self._add_filename, serialisable_directories_dict, self._quick_namespaces, self._regexes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( tags_for_all_list, self._load_from_neighbouring_txt_files, self._add_filename, serialisable_directories_dict, self._quick_namespaces, self._regexes ) = serialisable_info
        
        self._directories_dict = dict( serialisable_directories_dict )
        
        # converting [ namespace, regex ] to ( namespace, regex ) for listctrl et al to handle better
        self._quick_namespaces = [ tuple( item ) for item in self._quick_namespaces ]
        self._tags_for_all = set( tags_for_all_list )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( tags_for_all_list, load_from_neighbouring_txt_files, add_filename, add_first_directory, add_second_directory, add_third_directory, quick_namespaces, regexes ) = old_serialisable_info
            
            directories_dict = {}
            
            directories_dict[ 0 ] = add_first_directory
            directories_dict[ 1 ] = add_second_directory
            directories_dict[ 2 ] = add_third_directory
            
            for index in ( -3, -2, -1 ):
                
                directories_dict[ index ] = ( False, '' )
                
            
            serialisable_directories_dict = list(directories_dict.items())
            
            new_serialisable_info = ( tags_for_all_list, load_from_neighbouring_txt_files, add_filename, serialisable_directories_dict, quick_namespaces, regexes )
            
            return ( 2, new_serialisable_info )
            
        
    
    def AdvancedSetTuple( self, quick_namespaces, regexes ):
        
        self._quick_namespaces = quick_namespaces
        self._regexes = regexes
        
    
    def AdvancedToTuple( self ):
        
        return ( self._quick_namespaces, self._regexes )
        
    
    def GetTags( self, service_key, path ):
        
        tags = set()
        
        tags.update( self._tags_for_all )
        
        ( base, filename ) = os.path.split( path )
        
        ( filename, any_ext_gumpf ) = os.path.splitext( filename )
        
        ( filename_boolean, filename_namespace ) = self._add_filename
        
        if filename_boolean:
            
            if filename_namespace != '':
                
                tag = filename_namespace + ':' + filename
                
            else:
                
                tag = filename
                
            
            tags.add( tag )
            
        
        ( drive, directories ) = os.path.splitdrive( base )
        
        while directories.startswith( os.path.sep ):
            
            directories = directories[1:]
            
        
        directories = directories.split( os.path.sep )
        
        for ( index, ( dir_boolean, dir_namespace ) ) in list(self._directories_dict.items()):
            
            # we are talking -3 through 2 here
            
            if not dir_boolean:
                
                continue
                
            
            try:
                
                directory = directories[ index ]
                
            except IndexError:
                
                continue
                
            
            if dir_namespace != '':
                
                tag = dir_namespace + ':' + directory
                
            else:
                
                tag = directory
                
            
            tags.add( tag )
            
        
        #
        
        for regex in self._regexes:
            
            try:
                
                result = re.findall( regex, path )
                
                for match in result:
                    
                    if isinstance( match, tuple ):
                        
                        for submatch in match:
                            
                            tags.add( submatch )
                            
                        
                    else:
                        
                        tags.add( match )
                        
                    
                
            except:
                
                pass
                
            
        
        for ( namespace, regex ) in self._quick_namespaces:
            
            try:
                
                result = re.findall( regex, path )
                
                for match in result:
                    
                    if isinstance( match, tuple ):
                        
                        for submatch in match:
                            
                            tags.add( namespace + ':' + submatch )
                            
                        
                    else:
                        
                        tags.add( namespace + ':' + match )
                        
                    
                
            except:
                
                pass
                
            
        
        #
        
        tags = HydrusTags.CleanTags( tags )
        
        tags = CG.client_controller.tag_display_manager.FilterTags( ClientTags.TAG_DISPLAY_STORAGE, service_key, tags )
        
        return tags
        
    
    def SimpleSetTuple( self, tags_for_all, add_filename, directories_dict ):
        
        self._tags_for_all = tags_for_all
        self._add_filename = add_filename
        self._directories_dict = directories_dict
        
    
    def SimpleToTuple( self ):
        
        return ( self._tags_for_all, self._add_filename, self._directories_dict )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS ] = FilenameTaggingOptions    

class TagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Tag Import Options'
    SERIALISABLE_VERSION = 8
    
    def __init__(
        self,
        fetch_tags_even_if_url_recognised_and_file_already_in_db = False,
        fetch_tags_even_if_hash_recognised_and_file_already_in_db = False,
        tag_blacklist = None,
        tag_whitelist = None,
        service_keys_to_service_tag_import_options = None,
        is_default = False
    ):
        
        super().__init__()
        
        if tag_blacklist is None:
            
            tag_blacklist = HydrusTags.TagFilter()
            
        
        if tag_whitelist is None:
            
            tag_whitelist = []
            
        
        if service_keys_to_service_tag_import_options is None:
            
            service_keys_to_service_tag_import_options = {}
            
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_hash_recognised_and_file_already_in_db
        self._tag_blacklist = tag_blacklist
        self._tag_whitelist = tag_whitelist
        self._service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options
        self._is_default = is_default
        
    
    def _GetSerialisableInfo( self ):
        
        if CG.client_controller.IsBooted():
            
            services_manager = CG.client_controller.services_manager
            
            test_func = services_manager.ServiceExists
            
        else:
            
            def test_func( service_key ):
                
                return True
                
            
        
        serialisable_tag_blacklist = self._tag_blacklist.GetSerialisableTuple()
        
        serialisable_service_keys_to_service_tag_import_options = [ ( service_key.hex(), service_tag_import_options.GetSerialisableTuple() ) for ( service_key, service_tag_import_options ) in list(self._service_keys_to_service_tag_import_options.items()) if test_func( service_key ) ]
        
        return ( self._fetch_tags_even_if_url_recognised_and_file_already_in_db, self._fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, self._tag_whitelist, serialisable_service_keys_to_service_tag_import_options, self._is_default )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._fetch_tags_even_if_url_recognised_and_file_already_in_db, self._fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, self._tag_whitelist, serialisable_service_keys_to_service_tag_import_options, self._is_default ) = serialisable_info
        
        self._tag_blacklist = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_blacklist )
        
        self._service_keys_to_service_tag_import_options = { bytes.fromhex( encoded_service_key ) : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_service_tag_import_options ) for ( encoded_service_key, serialisable_service_tag_import_options ) in serialisable_service_keys_to_service_tag_import_options }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            safe_service_keys_to_namespaces = old_serialisable_info
            
            safe_service_keys_to_additional_tags = {}
            
            new_serialisable_info = ( safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            fetch_tags_even_if_url_recognised_and_file_already_in_db = False
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            tag_blacklist = HydrusTags.TagFilter()
            
            serialisable_tag_blacklist = tag_blacklist.GetSerialisableTuple()
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            serialisable_get_all_service_keys = []
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_get_all_service_keys, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_get_all_service_keys, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db
            
            get_all_service_keys = { bytes.fromhex( encoded_service_key ) for encoded_service_key in serialisable_get_all_service_keys }
            service_keys_to_namespaces = { bytes.fromhex( service_key ) : set( namespaces ) for ( service_key, namespaces ) in list(safe_service_keys_to_namespaces.items()) }
            service_keys_to_additional_tags = { bytes.fromhex( service_key ) : set( tags ) for ( service_key, tags ) in list(safe_service_keys_to_additional_tags.items()) }
            
            service_keys_to_service_tag_import_options = {}
            
            service_keys = set()
            
            service_keys.update( get_all_service_keys )
            service_keys.update( list(service_keys_to_namespaces.keys()) )
            service_keys.update( list(service_keys_to_additional_tags.keys()) )
            
            for service_key in service_keys:
                
                get_tags = False
                namespaces = []
                additional_tags = []
                
                if service_key in service_keys_to_namespaces:
                    
                    namespaces = service_keys_to_namespaces[ service_key ]
                    
                
                if service_key in get_all_service_keys or 'all namespaces' in namespaces:
                    
                    get_tags = True
                    
                
                if service_key in service_keys_to_additional_tags:
                    
                    additional_tags = service_keys_to_additional_tags[ service_key ]
                    
                
                ( to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags ) = ( True, True, True, False )
                
                service_tag_import_options = ServiceTagImportOptions( get_tags = get_tags, additional_tags = additional_tags, to_new_files = to_new_files, to_already_in_inbox = to_already_in_inbox, to_already_in_archive = to_already_in_archive, only_add_existing_tags = only_add_existing_tags )
                
                service_keys_to_service_tag_import_options[ service_key ] = service_tag_import_options
                
            
            serialisable_service_keys_to_service_tag_import_options = [ ( service_key.hex(), service_tag_import_options.GetSerialisableTuple() ) for ( service_key, service_tag_import_options ) in list(service_keys_to_service_tag_import_options.items()) ]
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options ) = old_serialisable_info
            
            is_default = False
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options, is_default )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options, is_default ) = old_serialisable_info
            
            tag_whitelist = []
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, tag_whitelist, serialisable_service_keys_to_service_tag_import_options, is_default )
            
            return ( 8, new_serialisable_info )
            
        
    
    def CanAddTags( self ):
        
        return self.HasAdditionalTags() or self.WorthFetchingTags()
        
    
    def CheckTagsVeto( self, tags: collections.abc.Collection[ str ], sibling_tags: collections.abc.Collection[ str ] ):
        
        tags = set( tags )
        
        sibling_tags = set( sibling_tags )
        
        for test_tags in ( tags, sibling_tags ):
            
            ok_tags = self._tag_blacklist.Filter( test_tags, apply_unnamespaced_rules_to_namespaced_tags = True )
            
            if len( ok_tags ) < len( test_tags ):
                
                bad_tags = test_tags.difference( ok_tags )
                
                bad_tags = HydrusTags.SortNumericTags( bad_tags )
                
                raise HydrusExceptions.VetoException( ', '.join( bad_tags ) + ' is blacklisted!' )
                
            
        
        if len( self._tag_whitelist ) > 0:
            
            all_tags = tags.union( sibling_tags )
            
            for tag in list( all_tags ):
                
                ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                
                all_tags.add( subtag )
                
            
            intersecting_tags = all_tags.intersection( self._tag_whitelist )
            
            if len( intersecting_tags ) == 0:
                
                raise HydrusExceptions.VetoException( 'did not pass the whitelist!' )
                
            
        
    
    def GetContentUpdatePackage( self, status: int, media_result: ClientMediaResult.MediaResult, filterable_tags: collections.abc.Iterable[ str ], external_filterable_tags = None, external_additional_service_keys_to_tags = None ) -> ClientContentUpdates.ContentUpdatePackage:
        
        if external_filterable_tags is None:
            
            external_filterable_tags = set()
            
        
        if external_additional_service_keys_to_tags is None:
            
            external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        filterable_tags = HydrusTags.CleanTags( filterable_tags )
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        for service_key in CG.client_controller.services_manager.GetServiceKeys( HC.REAL_TAG_SERVICES ):
            
            service_additional_tags = set()
            
            if service_key in external_additional_service_keys_to_tags:
                
                service_additional_tags.update( external_additional_service_keys_to_tags[ service_key ] )
                
            
            if service_key in self._service_keys_to_service_tag_import_options:
                
                service_tag_import_options = self._service_keys_to_service_tag_import_options[ service_key ]
                
                service_filterable_tags = set( filterable_tags )
                
                service_filterable_tags.update( external_filterable_tags )
                
                service_tags = service_tag_import_options.GetTags( service_key, status, media_result, service_filterable_tags, service_additional_tags )
                
            else:
                
                service_tags = service_additional_tags
                
            
            if len( service_tags ) > 0:
                
                service_keys_to_tags[ service_key ] = service_tags
                
            
        
        hash = media_result.GetHash()
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromServiceKeysToTags( { hash }, service_keys_to_tags )
        
        return content_update_package
        
    
    def GetServiceTagImportOptions( self, service_key ):
        
        if service_key not in self._service_keys_to_service_tag_import_options:
            
            self._service_keys_to_service_tag_import_options[ service_key ] = ServiceTagImportOptions()
            
        
        return self._service_keys_to_service_tag_import_options[ service_key ]
        
    
    def GetSummary( self, show_downloader_options ):
        
        if self._is_default:
            
            return 'Using whatever the default tag import options is at at time of import.'
            
        
        statements = []
        
        for ( service_key, service_tag_import_options ) in list(self._service_keys_to_service_tag_import_options.items()):
            
            sub_statements = service_tag_import_options.GetSummaryStatements()
            
            if len( sub_statements ) > 0:
                
                try:
                    
                    name = CG.client_controller.services_manager.GetName( service_key )
                    
                except HydrusExceptions.DataMissing:
                    
                    continue
                    
                
                service_statement = f'{name}:{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( sub_statements, no_trailing_whitespace = True )}'
                
                statements.append( service_statement )
                
            
        
        if len( statements ) > 0:
            
            if show_downloader_options:
                
                pre_statements = []
                
                pre_statements.append( self._tag_blacklist.ToBlacklistString() )
                
                if self._fetch_tags_even_if_url_recognised_and_file_already_in_db:
                    
                    s = 'fetching tags even if url is recognised and file already in db'
                    
                else:
                    
                    s = 'not fetching tags if url is recognised and file already in db'
                    
                
                pre_statements.append( s )
                
                if self._fetch_tags_even_if_hash_recognised_and_file_already_in_db:
                    
                    s = 'fetching tags even if hash is recognised and file already in db'
                    
                else:
                    
                    s = 'not fetching tags if hash is recognised and file already in db'
                    
                
                pre_statements.append( s )
                
                statements = pre_statements + [ '---' ] + statements
                
            
            separator = '\n'
            
            summary = separator.join( statements )
            
        else:
            
            summary = 'not adding any tags'
            
        
        return summary
        
    
    def GetTagBlacklist( self ):
        
        return self._tag_blacklist
        
    
    def GetTagWhitelist( self ):
        
        return self._tag_whitelist
        
    
    def HasAdditionalTags( self ):
        
        return True in ( service_tag_import_options.HasAdditionalTags() for service_tag_import_options in self._service_keys_to_service_tag_import_options.values() )
        
    
    def IsDefault( self ):
        
        return self._is_default
        
    
    def SetIsDefault( self, value: bool ):
        
        self._is_default = value
        
    
    def SetShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB( self, value: bool ):
        
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = value
        
    
    def SetShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( self, value: bool ):
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = value
        
    
    def ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_hash_recognised_and_file_already_in_db
        
    
    def ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_url_recognised_and_file_already_in_db
        
    
    def WorthFetchingTags( self ):
        
        return True in ( service_tag_import_options.WorthFetchingTags() for service_tag_import_options in self._service_keys_to_service_tag_import_options.values() )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS ] = TagImportOptions

def NewInboxArchiveMatch( new_files, inbox_files, archive_files, status, inbox ):
    
    if status == CC.STATUS_SUCCESSFUL_AND_NEW and new_files:
        
        return True
        
    elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
        
        if inbox and inbox_files:
            
            return True
            
        elif not inbox and archive_files:
            
            return True
            
        
    
    return False
    
class ServiceTagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Service Tag Import Options'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, get_tags = False, get_tags_filter = None, additional_tags = None, to_new_files = True, to_already_in_inbox = True, to_already_in_archive = True, only_add_existing_tags = False, only_add_existing_tags_filter = None, get_tags_overwrite_deleted = False, additional_tags_overwrite_deleted = False ):
        
        if get_tags_filter is None:
            
            get_tags_filter = HydrusTags.TagFilter()
            
        
        if additional_tags is None:
            
            additional_tags = []
            
        
        if only_add_existing_tags_filter is None:
            
            only_add_existing_tags_filter = HydrusTags.TagFilter()
            
        
        super().__init__()
        
        self._get_tags = get_tags
        self._get_tags_filter = get_tags_filter
        self._additional_tags = additional_tags
        self._to_new_files = to_new_files
        self._to_already_in_inbox = to_already_in_inbox
        self._to_already_in_archive = to_already_in_archive
        self._only_add_existing_tags = only_add_existing_tags
        self._only_add_existing_tags_filter = only_add_existing_tags_filter
        self._get_tags_overwrite_deleted = get_tags_overwrite_deleted
        self._additional_tags_overwrite_deleted = additional_tags_overwrite_deleted
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_get_tags_filter = self._get_tags_filter.GetSerialisableTuple()
        serialisable_only_add_existing_tags_filter = self._only_add_existing_tags_filter.GetSerialisableTuple()
        
        return ( self._get_tags, serialisable_get_tags_filter, list( self._additional_tags ), self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, serialisable_only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._get_tags, serialisable_get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, serialisable_only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted ) = serialisable_info
        
        self._get_tags_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_get_tags_filter )
        self._only_add_existing_tags_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_only_add_existing_tags_filter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( get_tags, namespaces, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags ) = old_serialisable_info
            
            get_tags_filter = HydrusTags.TagFilter()
            only_add_existing_tags_filter = HydrusTags.TagFilter()
            
            serialisable_get_tags_filter = get_tags_filter.GetSerialisableTuple()
            serialisable_only_add_existing_tags_filter = only_add_existing_tags_filter.GetSerialisableTuple()
            
            new_serialisable_info = ( get_tags, serialisable_get_tags_filter, namespaces, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( get_tags, serialisable_get_tags_filter, namespaces, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter ) = old_serialisable_info
            
            if not get_tags and len( namespaces ) > 0:
                
                get_tags = True
                get_tags_filter = HydrusTags.TagFilter()
                
                namespaces = list( namespaces )
                
                get_tags_filter.SetRule( ':', HC.FILTER_BLACKLIST )
                
                if '' in namespaces: # if unnamespaced in original checkboxes, then leave it unblocked
                    
                    namespaces.remove( '' )
                    
                else: # else block it
                    
                    get_tags_filter.SetRule( '', HC.FILTER_BLACKLIST )
                    
                
                for namespace in namespaces:
                    
                    get_tags_filter.SetRule( namespace + ':', HC.FILTER_WHITELIST )
                    
                
                serialisable_get_tags_filter = get_tags_filter.GetSerialisableTuple()
                
            
            new_serialisable_info = ( get_tags, serialisable_get_tags_filter, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( get_tags, serialisable_get_tags_filter, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter ) = old_serialisable_info
            
            get_tags_overwrite_deleted = False
            additional_tags_overwrite_deleted = False
            
            new_serialisable_info = ( get_tags, serialisable_get_tags_filter, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter, get_tags_overwrite_deleted, additional_tags_overwrite_deleted )
            
            return ( 4, new_serialisable_info )
            
        
    
    def GetSummaryStatements( self ):
        
        statements = []
        
        if self._get_tags:
            
            statements.append( self._get_tags_filter.ToPermittedString() )
            
        
        if len( self._additional_tags ) > 0:
            
            pretty_additional_tags = sorted( self._additional_tags )
            
            statements.append( 'additional tags: ' + ', '.join( pretty_additional_tags ) )
            
        
        return statements
        
    
    def GetTags( self, service_key: bytes, status: int, media_result: ClientMediaResult.MediaResult, filterable_tags: collections.abc.Collection[ str ], additional_tags: collections.abc.Collection[ str ] | None = None ):
        
        if additional_tags is None:
            
            additional_tags = set()
            
        
        tags = set()
        
        in_inbox = media_result.GetInbox()
        
        if NewInboxArchiveMatch( self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, status, in_inbox ):
            
            if self._get_tags:
                
                filtered_tags = self._get_tags_filter.Filter( filterable_tags )
                
                if not self._get_tags_overwrite_deleted:
                    
                    filtered_tags = ClientImportOptions.FilterNotPreviouslyDeletedTags( service_key, media_result, filtered_tags )
                    
                
                tags.update( filtered_tags )
                
            
            additional_tags = set( additional_tags )
            additional_tags.update( self._additional_tags )
            
            additional_tags = HydrusTags.CleanTags( additional_tags )
            
            if not self._additional_tags_overwrite_deleted:
                
                additional_tags = ClientImportOptions.FilterNotPreviouslyDeletedTags( service_key, media_result, additional_tags )
                
            
            tags.update( additional_tags )
            
            if self._only_add_existing_tags:
                
                applicable_tags = self._only_add_existing_tags_filter.Filter( tags )
                
                tags.difference_update( applicable_tags )
                
                existing_applicable_tags = CG.client_controller.Read( 'filter_existing_tags', service_key, applicable_tags )
                
                tags.update( existing_applicable_tags )
                
            
        
        return tags
        
    
    def HasAdditionalTags( self ):
        
        return len( self._additional_tags ) > 0
        
    
    def ToTuple( self ):
        
        return ( self._get_tags, self._get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted )
        
    
    def WorthFetchingTags( self ):
        
        return self._get_tags
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_TAG_IMPORT_OPTIONS ] = ServiceTagImportOptions
