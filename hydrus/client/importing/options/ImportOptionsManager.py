import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.importing.options import ExternalProgramsImportOptions
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import ImportOptionsConstants as IOC
from hydrus.client.importing.options import ImportOptionsContainer
from hydrus.client.importing.options import LocationImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.importing.options import TagFilteringImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.networking import ClientNetworkingFunctions

def GetImportOptionsCallerTypesPreferenceOrderFull( import_options_caller_type: int, url_class_keys: list[ bytes ] ):
    """
    The types of caller we should examine, from most to least specific, to layer our swiss cheese model.
    """
    
    preference_stack = [ IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ]
    
    if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION:
        
        preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
        preference_stack.append( import_options_caller_type )
        preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
        
    elif import_options_caller_type in ( IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS, IOC.IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS ):
        
        preference_stack.append( import_options_caller_type )
        preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
        
        we_are_confident_in_what_it_is = False
        it_is_watchable = False
        
        for url_class_key in url_class_keys:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                
                if url_class.GetURLType() == HC.URL_TYPE_WATCHABLE:
                    
                    it_is_watchable = True
                    
                
                we_are_confident_in_what_it_is = True
                
                break
                
            except HydrusExceptions.DataMissing:
                
                pass
                
            
        
        if we_are_confident_in_what_it_is:
            
            if it_is_watchable:
                
                preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS )
                preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
                
            else:
                
                preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
                preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
                
            
        else:
            
            preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
            preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
            
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER:
        
        preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT )
        preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER )
        
    else:
        
        preference_stack.append( import_options_caller_type )
        
    
    if import_options_caller_type != IOC.IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API:
        
        preference_stack.append( IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
        
    
    preference_stack.reverse()
    
    return preference_stack
    

def GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type: int, url_class_key: bytes | None = None ) -> str:
    """
    Given this type of caller in the options UI, what are we showing to the user to say about what is consulted?
    """
    
    if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
        
        return 'global'
        
    
    preference_stack = [ IOC.import_options_caller_type_str_lookup[ IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ] ]
    
    if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION:
        
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS ] )
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any matching URL Class' )
        preference_stack.append( 'any custom import options for the particular subscription' )
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS:
        
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'maybe "subscription"' )
        preference_stack.append( 'any matching URL Class' )
        preference_stack.append( 'any custom import options for the particular downloader page or subscription' )
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS:
        
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any matching URL Class' )
        preference_stack.append( 'any custom import options for the particular watcher page' )
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
        
        we_are_confident_in_what_it_is = False
        it_is_watchable = False
        url_class_name = 'any matching URL Class'
        
        if url_class_key is not None:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                
                if url_class.GetURLType() == HC.URL_TYPE_WATCHABLE:
                    
                    it_is_watchable = True
                    
                
                url_class_name = f'urls of class "{url_class.GetName()}"'
                
                we_are_confident_in_what_it_is = True
                
            except HydrusExceptions.DataMissing:
                
                pass
                
            
        
        if we_are_confident_in_what_it_is:
            
            if it_is_watchable:
                
                preference_stack.append( IOC.import_options_caller_type_str_lookup[ IOC.IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS ] )
                preference_stack.append( url_class_name )
                preference_stack.append( 'any custom import options for the particular watcher page' )
                
            else:
                
                preference_stack.append( IOC.import_options_caller_type_str_lookup[ IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS ] )
                preference_stack.append( 'maybe "subscription"' )
                preference_stack.append( url_class_name )
                preference_stack.append( 'any custom import options for the particular downloader page or subscription' )
                
            
        else:
            
            preference_stack.append( 'a gallery/post or watcher url' )
            preference_stack.append( 'maybe "subscription", if it is a gallery/post url class' )
            preference_stack.append( url_class_name )
            preference_stack.append( 'any custom import options for the particular watcher page, downloader page, or subscription' )
            
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER:
        
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT ] )
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any custom import options for the particular import folder' )
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API:
        
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] )
        
    elif import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT:
        
        preference_stack.append( IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any custom import options for the particular local import page' )
        
    
    preference_stack.reverse()
    
    return '\n'.join( preference_stack )
    

class ImportOptionsManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER
    SERIALISABLE_NAME = 'Import Options Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary()
        self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary()
        
        self._names_to_favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary()
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
    
    def _AddFavourite( self, name: str, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        actual_name = HydrusData.GetNonDupeName( name, set( self._names_to_favourite_import_options_containers.keys() ) )
        
        self._names_to_favourite_import_options_containers[ actual_name ] = import_options_container
        
        return actual_name
        
    
    def _DeleteFavourite( self, name: str ):
        
        if name in self._names_to_favourite_import_options_containers:
            
            del self._names_to_favourite_import_options_containers[ name ]
            
        
    
    def _GenerateFullImportOptionsContainer( self, caller_import_options_container_slice: ImportOptionsContainer.ImportOptionsContainer, import_options_caller_type: int, url_class_keys_in_preference_order: list[ bytes ] ):
        
        import_options_container_slices_in_preference_order_with_source_labels = self._GetImportOptionsContainerSlicesInPreferenceOrderWithSourceLabels( import_options_caller_type, url_class_keys_in_preference_order, specific_import_options_container = caller_import_options_container_slice )
        
        import_options_container_result = ImportOptionsContainer.ImportOptionsContainer()
        
        # we have a bunch of slices, now we fill in all the holes
        for ( import_options_container_slice, source_label ) in import_options_container_slices_in_preference_order_with_source_labels:
            
            import_options_container_result.FillInWithThisSlice( import_options_container_slice, source_label = source_label )
            
        
        return import_options_container_result
        
    
    def _GetImportOptionsContainerSlicesInPreferenceOrderWithSourceLabels( self, import_options_caller_type: int, url_class_keys: list[ bytes ], specific_import_options_container: ImportOptionsContainer.ImportOptionsContainer | None = None ) -> list[ ImportOptionsContainer.ImportOptionsContainer ]:
        
        preference_stack = GetImportOptionsCallerTypesPreferenceOrderFull( import_options_caller_type, url_class_keys )
        
        import_options_container_slices_in_preference_order_with_source_labels = []
        
        for preference_import_options_caller_type in preference_stack:
            
            if preference_import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER:
                
                if specific_import_options_container is not None:
                    
                    import_options_container_slices_in_preference_order_with_source_labels.append( ( specific_import_options_container, IOC.import_options_caller_type_str_lookup[ preference_import_options_caller_type ] ) )
                    
                
            elif preference_import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
                
                for url_class_key in url_class_keys:
                    
                    if url_class_key not in self._url_class_keys_to_default_import_options_containers:
                        
                        ClientNetworkingFunctions.NetworkReportMode( f'URL Class did not have any custom import options.' )
                        
                    else:
                        
                        ClientNetworkingFunctions.NetworkReportMode( f'URL Class did have custom import options.' )
                        
                        try:
                            
                            url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                            
                            source_label = f'url class: "{url_class.GetName()}"'
                            
                        except HydrusExceptions.DataMissing:
                            
                            source_label = f'url class: unknown/missing'
                            
                        
                        import_options_container_slices_in_preference_order_with_source_labels.append( ( self._url_class_keys_to_default_import_options_containers[ url_class_key ], source_label ) )
                        
                        break
                        
                    
                
            else:
                
                import_options_container_slices_in_preference_order_with_source_labels.append(
                    (
                        self._import_options_caller_types_to_default_import_options_containers[ preference_import_options_caller_type ],
                        IOC.import_options_caller_type_str_lookup[ preference_import_options_caller_type ]
                    )
                )
                
            
        
        return import_options_container_slices_in_preference_order_with_source_labels
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options_caller_types_to_default_import_options_containers = self._import_options_caller_types_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_import_options_containers = self._url_class_keys_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_names_to_favourite_import_options_containers = self._names_to_favourite_import_options_containers.GetSerialisableTuple()
        
        return (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_names_to_favourite_import_options_containers
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_names_to_favourite_import_options_containers,
        ) = serialisable_info
        
        self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options_caller_types_to_default_import_options_containers )
        self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_keys_to_default_import_options_containers )
        self._names_to_favourite_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_names_to_favourite_import_options_containers )
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def AddFavourite( self, name: str, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        with self._lock:
            
            actual_name = self._AddFavourite( name, import_options_container )
            
            self._SetDirty()
            
            return actual_name
            
        
    
    def DeleteDefaultImportOptionsContainerForURLClass( self, url_class_key: bytes ):
        
        with self._lock:
            
            if url_class_key in self._url_class_keys_to_default_import_options_containers:
                
                del self._url_class_keys_to_default_import_options_containers[ url_class_key ]
                
            
            self._SetDirty()
            
        
    
    def DeleteFavourite( self, name: str ):
        
        with self._lock:
            
            self._DeleteFavourite( name )
            
            self._SetDirty()
            
        
    
    def EditFavourite( self, original_name: str, name: str, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        with self._lock:
            
            self._DeleteFavourite( original_name )
            
            actual_name = self._AddFavourite( name, import_options_container )
            
            self._SetDirty()
            
            return actual_name
            
        
    
    def GenerateFullImportOptionsContainer( self, caller_import_options_container_slice: ImportOptionsContainer.ImportOptionsContainer, import_options_caller_type: int, urls: list[ str ] | None = None ) -> ImportOptionsContainer.ImportOptionsContainer:
        
        if urls is None:
            
            urls = []
            
        
        ClientNetworkingFunctions.NetworkReportMode( f'Doing an import options container freeze lookup for "{IOC.import_options_caller_type_str_lookup[ import_options_caller_type ]}", with URLs "{urls}".' )
        
        url_class_keys_in_preference_order = []
        
        for url in urls:
            
            some_url_class_keys = CG.client_controller.network_engine.domain_manager.GetAPIPertinentURLClassKeysInPreferenceOrder( url )
            
            if len( some_url_class_keys ) == 0:
                
                ClientNetworkingFunctions.NetworkReportMode( f'When doing options lookup, URL "{url}" did not match any URL Class.' )
                
            else:
                
                url_class_keys_in_preference_order.extend( some_url_class_keys )
                
            
        
        with self._lock:
            
            import_options_container_result = self._GenerateFullImportOptionsContainer( caller_import_options_container_slice, import_options_caller_type, url_class_keys_in_preference_order )
            
            if not import_options_container_result.IsFull():
                
                try:
                    
                    global_import_options_container = self._import_options_caller_types_to_default_import_options_containers[ IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ]
                    
                    if global_import_options_container.IsFull():
                        
                        raise Exception( 'Hey, there is a serious problem in the import options system. Your "global" options container is fully populated, but the stack is not producing a full container. Please let hydev know immediately!' )
                        
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Your "global" import options container was missing!' )
                    
                    global_import_options_container = ImportOptionsContainer.ImportOptionsContainer()
                    
                
                for empty_import_options in [
                    FileFilteringImportOptions.FileFilteringImportOptions(),
                    LocationImportOptions.LocationImportOptions(),
                    NoteImportOptions.NoteImportOptions(),
                    PrefetchImportOptions.PrefetchImportOptions(),
                    ExternalProgramsImportOptions.ExternalProgramsImportOptions(),
                    PresentationImportOptions.PresentationImportOptions(),
                    TagFilteringImportOptions.TagFilteringImportOptions(),
                    TagImportOptions.TagImportOptions(),
                ]:
                    
                    if not global_import_options_container.HasImportOptions( empty_import_options.IMPORT_OPTIONS_TYPE ):
                        
                        global_import_options_container.SetImportOptions( empty_import_options )
                        
                    
                    self._import_options_caller_types_to_default_import_options_containers[ IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ] = global_import_options_container
                    
                
                HydrusData.ShowText( 'Hey, it looks like something went wrong with the import options system. Your "global" options container was missing entirely or missing entries. I have repopulated the missing data with defaults and saved it back. You may have encountered database damage. If you do not know what is going on, please tell hydev about it.' )
                
                import_options_container_result = self._GenerateFullImportOptionsContainer( caller_import_options_container_slice, import_options_caller_type, url_class_keys_in_preference_order )
                
            
        
        # this guy is now ready to answer any import question the caller has
        return import_options_container_result
        
    
    def GetDefaultImportOptionsContainerForCallerType( self, import_options_caller_type: int ) -> ImportOptionsContainer.ImportOptionsContainer:
        
        with self._lock:
            
            return self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ]
            
        
    
    def GetDefaultImportOptionsContainerForURLClass( self, url_class_key: bytes ) -> ImportOptionsContainer.ImportOptionsContainer | None:
        
        with self._lock:
            
            return self._url_class_keys_to_default_import_options_containers.get( url_class_key, None )
            
        
    
    def GetFavouriteImportOptionContainers( self ) -> dict[ str, ImportOptionsContainer.ImportOptionsContainer ]:
        
        with self._lock:
            
            return dict( self._names_to_favourite_import_options_containers )
            
        
    
    def GetImportOptionsCallerTypesToDefaultImportOptionsContainers( self ) -> dict[ int, ImportOptionsContainer.ImportOptionsContainer ]:
        
        with self._lock:
            
            return dict( self._import_options_caller_types_to_default_import_options_containers )
            
        
    
    def GetURLClassKeysToDefaultImportOptionsContainers( self ) -> dict[ bytes, ImportOptionsContainer.ImportOptionsContainer ]:
        
        with self._lock:
            
            return dict( self._url_class_keys_to_default_import_options_containers )
            
        
    
    def IsDirty( self ):
        
        return self._dirty
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetFavouriteImportOptionContainers( self, names_to_favourite_import_options_containers: dict[ str, ImportOptionsContainer.ImportOptionsContainer ] ):
        
        with self._lock:
            
            self._names_to_favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary( names_to_favourite_import_options_containers )
            
            self._SetDirty()
            
        
    
    def SetDefaultImportOptionsContainerForCallerType( self, import_options_caller_type: int, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            if not import_options_container.IsFull():
                
                try:
                    
                    raise Exception( 'Hey, something just tried to set a non-full global import options container default! Please let hydev know.' )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
                return
                
            
        
        with self._lock:
            
            self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ] = import_options_container
            
            self._SetDirty()
            
        
    
    def SetDefaultImportOptionsContainerForURLClass( self, url_class_key: bytes, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        with self._lock:
            
            if import_options_container.IsEmpty():
                
                if url_class_key in self._url_class_keys_to_default_import_options_containers:
                    
                    del self._url_class_keys_to_default_import_options_containers[ url_class_key ]
                    
                
            else:
                
                self._url_class_keys_to_default_import_options_containers[ url_class_key ] = import_options_container
                
            
            self._SetDirty()
            
        
    
    @staticmethod
    def STATICGetDefaultInitialisedManager() -> "ImportOptionsManager":
            
            import_options_manager = ImportOptionsManager.STATICGetEmptyButValidManager()
            
            ImportOptionsManager.STATICPopulateManagerWithDefaultDefaults( import_options_manager )
            ImportOptionsManager.STATICPopulateManagerWithDefaultURLClassDefaults( import_options_manager )
            ImportOptionsManager.STATICPopulateManagerWithDefaultFavourites( import_options_manager )
            
            return import_options_manager
            
        
    
    @staticmethod
    def STATICGetEmptyButValidManager() -> "ImportOptionsManager":
            
            import_options_manager = ImportOptionsManager()
            
            for import_options_caller_type in IOC.IMPORT_OPTIONS_CALLER_TYPES_EDITABLE_CANONICAL_ORDER:
                
                import_options_container = ImportOptionsContainer.ImportOptionsContainer()
                
                if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
                    
                    import_options_container.SetImportOptions( FileFilteringImportOptions.FileFilteringImportOptions() )
                    import_options_container.SetImportOptions( LocationImportOptions.LocationImportOptions() )
                    import_options_container.SetImportOptions( NoteImportOptions.NoteImportOptions() )
                    import_options_container.SetImportOptions( PrefetchImportOptions.PrefetchImportOptions() )
                    import_options_container.SetImportOptions( ExternalProgramsImportOptions.ExternalProgramsImportOptions() )
                    import_options_container.SetImportOptions( PresentationImportOptions.PresentationImportOptions() )
                    import_options_container.SetImportOptions( TagFilteringImportOptions.TagFilteringImportOptions() )
                    import_options_container.SetImportOptions( TagImportOptions.TagImportOptions() )
                    
                
                import_options_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, import_options_container )
                
            
            return import_options_manager
            
        
    
    @staticmethod
    def STATICPopulateManagerWithDefaultDefaults( import_options_manager: "ImportOptionsManager" ):
        
        prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
        
        prefetch_import_options.SetPreImportHashCheckType( PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE )
        prefetch_import_options.SetPreImportURLCheckType( PrefetchImportOptions.DO_CHECK )
        prefetch_import_options.SetPreImportURLCheckLooksForNeighbourSpam( True )
        
        file_filtering_import_options = FileFilteringImportOptions.FileFilteringImportOptions()
        
        file_filtering_import_options.SetAllowsDecompressionBombs( True )
        file_filtering_import_options.SetExcludesDeleted( True )
        
        location_import_options = LocationImportOptions.LocationImportOptions()
        
        location_import_options.SetAutomaticallyArchives( False )
        location_import_options.SetShouldAssociatePrimaryURLs( True )
        location_import_options.SetShouldAssociateSourceURLs( True )
        location_import_options.SetDestinationLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ) )
        
        import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        import_options_container.SetImportOptions( file_filtering_import_options )
        import_options_container.SetImportOptions( location_import_options )
        import_options_container.SetImportOptions( NoteImportOptions.NoteImportOptions() )
        import_options_container.SetImportOptions( prefetch_import_options )
        import_options_container.SetImportOptions( ExternalProgramsImportOptions.ExternalProgramsImportOptions() )
        import_options_container.SetImportOptions( PresentationImportOptions.PresentationImportOptions() )
        import_options_container.SetImportOptions( TagFilteringImportOptions.TagFilteringImportOptions() )
        import_options_container.SetImportOptions( TagImportOptions.TagImportOptions() )
        
        import_options_manager.SetDefaultImportOptionsContainerForCallerType( IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL, import_options_container )
        
        #
        
        quiet_presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        quiet_presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        
        quiet_import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        quiet_import_options_container.SetImportOptions( quiet_presentation_import_options )
        
        #
        
        import_options_manager.SetDefaultImportOptionsContainerForCallerType( IOC.IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION, quiet_import_options_container.Duplicate() )
        
        #
        
        import_options_manager.SetDefaultImportOptionsContainerForCallerType( IOC.IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER, quiet_import_options_container.Duplicate() )
        
        #
        
        service_tag_import_options = TagImportOptions.ServiceTagImportOptions( get_tags = True )
        
        service_keys_to_service_tag_import_options = { CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY : service_tag_import_options }
        
        tag_import_options = TagImportOptions.TagImportOptions( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        import_options_container.SetImportOptions( tag_import_options )
        
        import_options_manager.SetDefaultImportOptionsContainerForCallerType( IOC.IMPORT_OPTIONS_CALLER_TYPE_POST_URLS, import_options_container )
        
        #
        
        tag_import_options = TagImportOptions.TagImportOptions()
        
        import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        import_options_container.SetImportOptions( tag_import_options )
        
        import_options_manager.SetDefaultImportOptionsContainerForCallerType( IOC.IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS, import_options_container )
        
    
    @staticmethod
    def STATICPopulateManagerWithDefaultFavourites( import_options_manager: "ImportOptionsManager" ):
        
        import_options_manager.AddFavourite(
            'no tags',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 4], [2, [151, 1, []]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'show new files',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 6], [2, [108, 2, [[103, 1, [["616c6c206c6f63616c206d65646961"], []]], 1, 0]]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'show all files',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 6], [2, [108, 2, [[103, 1, [["616c6c206c6f63616c206d65646961"], []]], 0, 0]]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'example blacklist',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 2], [2, [150, 1, [[44, 1, [["goblin", 1], ["orc", 1]]], []]]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'force metadata refetch',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 0], [2, [145, 2, [2, 1, true, true, true]]]]]]]'
            )
        )
        
    
    @staticmethod
    def STATICPopulateManagerWithDefaultURLClassDefaults( import_options_manager: "ImportOptionsManager" ):
        
        # no url class defaults right now
        pass
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER ] = ImportOptionsManager
