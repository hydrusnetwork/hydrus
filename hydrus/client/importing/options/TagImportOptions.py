import collections.abc

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
            
            statements.append( self._get_tags_filter.ToFilterString() )
            
        
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

class TagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Tag Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__(
        self,
        service_keys_to_service_tag_import_options = None
    ):
        
        super().__init__()
        
        if service_keys_to_service_tag_import_options is None:
            
            service_keys_to_service_tag_import_options = {}
            
        
        self._service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options
        
    
    def _GetSerialisableInfo( self ):
        
        if CG.client_controller.IsBooted():
            
            services_manager = CG.client_controller.services_manager
            
            test_func = services_manager.ServiceExists
            
        else:
            
            def test_func( service_key ):
                
                return True
                
            
        
        serialisable_service_keys_to_service_tag_import_options = [ ( service_key.hex(), service_tag_import_options.GetSerialisableTuple() ) for ( service_key, service_tag_import_options ) in self._service_keys_to_service_tag_import_options.items() if test_func( service_key ) ]
        
        return serialisable_service_keys_to_service_tag_import_options
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_service_keys_to_service_tag_import_options = serialisable_info
        
        self._service_keys_to_service_tag_import_options = { bytes.fromhex( encoded_service_key ) : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_service_tag_import_options ) for ( encoded_service_key, serialisable_service_tag_import_options ) in serialisable_service_keys_to_service_tag_import_options }
        
    
    def CanAddTags( self ):
        
        return self.HasAdditionalTags() or self.WorthFetchingTags()
        
    
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
        
    
    def GetSummary( self, show_downloader_options: bool = True ):
        
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
            
            summary = ', '.join( statements )
            
        else:
            
            summary = 'not adding any tags'
            
        
        return summary
        
    
    def HasAdditionalTags( self ):
        
        return True in ( service_tag_import_options.HasAdditionalTags() for service_tag_import_options in self._service_keys_to_service_tag_import_options.values() )
        
    
    def WorthFetchingTags( self ):
        
        return True in ( service_tag_import_options.WorthFetchingTags() for service_tag_import_options in self._service_keys_to_service_tag_import_options.values() )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS ] = TagImportOptions
