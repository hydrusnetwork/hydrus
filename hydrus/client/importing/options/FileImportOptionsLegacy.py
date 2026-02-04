from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import LocationImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.search import ClientSearchPredicate

IMPORT_TYPE_QUIET = 0
IMPORT_TYPE_LOUD = 1

def GetRealFileImportOptions( file_import_options: "FileImportOptionsLegacy", loud_or_quiet: int ) -> "FileImportOptionsLegacy":
    
    if file_import_options.IsDefault():
        
        file_import_options = CG.client_controller.new_options.GetDefaultFileImportOptions( loud_or_quiet )
        
    
    return file_import_options
    

def GetRealPresentationImportOptions( file_import_options: "FileImportOptionsLegacy", loud_or_quiet: int ) -> PresentationImportOptions.PresentationImportOptions:
    
    real_file_import_options = GetRealFileImportOptions( file_import_options, loud_or_quiet )
    
    return real_file_import_options.GetPresentationImportOptions()
    

# don't delete this guy; generally leave him functional as-is. some ye olde importers might still want him for an old _UpdateSerialisable
class FileImportOptionsLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS_LEGACY
    SERIALISABLE_NAME = 'File Import Options (Legacy)'
    SERIALISABLE_VERSION = 15
    
    def __init__( self ):
        
        super().__init__()
        
        self._prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
        self._file_filtering_import_options = FileFilteringImportOptions.FileFilteringImportOptions()
        self._location_import_options = LocationImportOptions.LocationImportOptions()
        self._presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        self._is_default = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_prefetch_import_options = self._prefetch_import_options.GetSerialisableTuple()
        serialisable_file_filtering_import_options = self._file_filtering_import_options.GetSerialisableTuple()
        serialisable_location_import_options = self._location_import_options.GetSerialisableTuple()
        serialisable_presentation_import_options = self._presentation_import_options.GetSerialisableTuple()
        
        return ( serialisable_prefetch_import_options, serialisable_file_filtering_import_options, serialisable_location_import_options, serialisable_presentation_import_options, self._is_default )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_prefetch_import_options, serialisable_file_filtering_import_options, serialisable_location_import_options, serialisable_presentation_import_options, self._is_default ) = serialisable_info
        
        self._prefetch_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_prefetch_import_options )
        self._file_filtering_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_filtering_import_options )
        self._location_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_location_import_options )
        self._presentation_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_presentation_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( automatic_archive, exclude_deleted, min_size, min_resolution ) = old_serialisable_info
            
            present_new_files = True
            present_already_in_inbox_files = False
            present_already_in_archive_files = False
            
            new_serialisable_info = ( automatic_archive, exclude_deleted, present_new_files, present_already_in_inbox_files, present_already_in_archive_files, min_size, min_resolution )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( automatic_archive, exclude_deleted, present_new_files, present_already_in_inbox_files, present_already_in_archive_files, min_size, min_resolution ) = old_serialisable_info
            
            max_size = None
            max_resolution = None
            
            allow_decompression_bombs = True
            max_gif_size = 32 * 1048576
            
            pre_import_options = ( exclude_deleted, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
            post_import_options = automatic_archive
            presentation_options = ( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
            
            new_serialisable_info = ( pre_import_options, post_import_options, presentation_options )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( pre_import_options, post_import_options, presentation_options ) = old_serialisable_info
            
            ( exclude_deleted, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution ) = pre_import_options
            
            automatic_archive = post_import_options
            
            do_not_check_known_urls_before_importing = False
            do_not_check_hashes_before_importing = False
            associate_source_urls = True
            
            pre_import_options = ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
            
            post_import_options = ( automatic_archive, associate_source_urls )
            
            new_serialisable_info = ( pre_import_options, post_import_options, presentation_options )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( pre_import_options, post_import_options, presentation_options ) = old_serialisable_info
            
            ( automatic_archive, associate_source_urls ) = post_import_options
            
            associate_primary_urls = True
            
            post_import_options = ( automatic_archive, associate_primary_urls, associate_source_urls )
            
            new_serialisable_info = ( pre_import_options, post_import_options, presentation_options )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( pre_import_options, post_import_options, presentation_options ) = old_serialisable_info
            
            ( present_new_files, present_already_in_inbox_files, present_already_in_archive_files ) = presentation_options
            
            presentation_import_options = PresentationImportOptions.PresentationImportOptions()
            
            if not present_new_files:
                
                presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NONE )
                
            else:
                
                if present_already_in_archive_files and present_already_in_inbox_files:
                    
                    presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_ANY_GOOD )
                    
                else:
                    
                    presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
                    
                    if present_already_in_inbox_files:
                        
                        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX )
                        
                    
                
            
            serialisable_presentation_import_options = presentation_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options ) = old_serialisable_info
            
            ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution ) = pre_import_options
            
            import_destination_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
            
            serialisable_import_destination_location_context = import_destination_location_context.GetSerialisableTuple()
            
            pre_import_options = ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context )
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options ) = old_serialisable_info
            
            ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context ) = pre_import_options
            
            filetype_filter_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = set( HC.GENERAL_FILETYPES ) )
            
            serialisable_filetype_filter_predicate = filetype_filter_predicate.GetSerialisableTuple()
            
            pre_import_options = ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context )
            
            is_default = False
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context ) = pre_import_options
            
            if do_not_check_hashes_before_importing:
                
                preimport_hash_check_type = PrefetchImportOptions.DO_NOT_CHECK
                
            else:
                
                preimport_hash_check_type = PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
                
            
            if do_not_check_known_urls_before_importing:
                
                preimport_url_check_type = PrefetchImportOptions.DO_NOT_CHECK
                
            else:
                
                preimport_url_check_type = PrefetchImportOptions.DO_CHECK
                
            
            preimport_url_check_looks_for_neighbour_spam = True
            
            pre_import_options = ( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, preimport_url_check_looks_for_neighbour_spam, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context )
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, preimport_url_check_looks_for_neighbour_spam, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context ) = pre_import_options
            
            filetype_filter_predicate = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filetype_filter_predicate )
            
            mimes = list( filetype_filter_predicate.GetValue() )
            
            if HC.GENERAL_APPLICATION in mimes:
                
                mimes.append( HC.GENERAL_APPLICATION_ARCHIVE )
                mimes.append( HC.GENERAL_IMAGE_PROJECT )
                
                filetype_filter_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = mimes )
                
            
            serialisable_filetype_filter_predicate = filetype_filter_predicate.GetSerialisableTuple()
            
            pre_import_options = ( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, preimport_url_check_looks_for_neighbour_spam, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context )
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 10, new_serialisable_info )
            
        
        if version == 10:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( automatic_archive, associate_primary_urls, associate_source_urls ) = post_import_options
            
            do_content_updates_on_already_in_db_files = True
            
            post_import_options = ( automatic_archive, associate_primary_urls, associate_source_urls, do_content_updates_on_already_in_db_files )
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 11, new_serialisable_info )
            
        
        if version == 11:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( automatic_archive, associate_primary_urls, associate_source_urls, do_content_updates_on_already_in_db_files ) = post_import_options
            
            do_archive_on_already_in_db_files = do_content_updates_on_already_in_db_files
            do_import_destinations_on_already_in_db_files = False # I vacillated on what to set this as, but let's default to non-annoying
            
            post_import_options = ( automatic_archive, associate_primary_urls, associate_source_urls, do_archive_on_already_in_db_files, do_import_destinations_on_already_in_db_files )
            
            new_serialisable_info = ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 12, new_serialisable_info )
            
        
        if version == 12:
            
            ( pre_import_options, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, preimport_url_check_looks_for_neighbour_spam, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context ) = pre_import_options
            
            prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
            
            prefetch_import_options.SetPreImportHashCheckType( preimport_hash_check_type )
            prefetch_import_options.SetPreImportURLCheckType( preimport_url_check_type )
            prefetch_import_options.SetPreImportURLCheckLooksForNeighbourSpam( preimport_url_check_looks_for_neighbour_spam )
            
            serialisable_prefetch_import_options = prefetch_import_options.GetSerialisableTuple()
            
            pre_import_options = ( exclude_deleted, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context )
            
            new_serialisable_info = ( serialisable_prefetch_import_options, pre_import_options, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 13, new_serialisable_info )
            
        
        if version == 13:
            
            ( serialisable_prefetch_import_options, pre_import_options, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( exclude_deleted, allow_decompression_bombs, serialisable_filetype_filter_predicate, min_size, max_size, max_gif_size, min_resolution, max_resolution, serialisable_import_destination_location_context ) = pre_import_options
            
            filetype_filter_predicate = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filetype_filter_predicate )
            
            file_filtering_import_options = FileFilteringImportOptions.FileFilteringImportOptions()
            
            file_filtering_import_options.SetAllowsDecompressionBombs( allow_decompression_bombs )
            file_filtering_import_options.SetExcludesDeleted( exclude_deleted )
            file_filtering_import_options.SetAllowedSpecificFiletypes( ClientSearchPredicate.ConvertSummaryFiletypesToSpecific( filetype_filter_predicate.GetValue(), only_searchable = False ) )
            file_filtering_import_options.SetMaxGifSize( max_gif_size )
            file_filtering_import_options.SetMaxResolution( max_resolution )
            file_filtering_import_options.SetMaxSize( max_size )
            file_filtering_import_options.SetMinResolution( min_resolution )
            file_filtering_import_options.SetMinSize( min_size )
            
            serialisable_file_filtering_import_options = file_filtering_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_prefetch_import_options, serialisable_file_filtering_import_options, serialisable_import_destination_location_context, post_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 14, new_serialisable_info )
            
        
        if version == 14:
            
            ( serialisable_prefetch_import_options, serialisable_file_filtering_import_options, serialisable_import_destination_location_context, post_import_options, serialisable_presentation_import_options, is_default ) = old_serialisable_info
            
            ( automatic_archive, associate_primary_urls, associate_source_urls, do_archive_on_already_in_db_files, do_import_destinations_on_already_in_db_files ) = post_import_options
            
            import_destination_location_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_destination_location_context )
            
            location_import_options = LocationImportOptions.LocationImportOptions()
            
            location_import_options.SetDestinationLocationContext( import_destination_location_context )
            location_import_options.SetAutomaticallyArchives( automatic_archive )
            location_import_options.SetDoAutomaticArchiveOnAlreadyInDBFiles( do_archive_on_already_in_db_files )
            location_import_options.SetDoImportDestinationsOnAlreadyInDBFiles( do_import_destinations_on_already_in_db_files )
            location_import_options.SetShouldAssociatePrimaryURLs( associate_primary_urls )
            location_import_options.SetShouldAssociateSourceURLs( associate_source_urls )
            
            serialisable_location_import_options = location_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_prefetch_import_options, serialisable_file_filtering_import_options, serialisable_location_import_options, serialisable_presentation_import_options, is_default )
            
            return ( 15, new_serialisable_info )
            
        
    
    def GetFileFilteringImportOptions( self ) -> FileFilteringImportOptions.FileFilteringImportOptions:
        
        return self._file_filtering_import_options
        
    
    def GetLocationImportOptions( self ) -> LocationImportOptions.LocationImportOptions:
        
        return self._location_import_options
        
    
    def GetPrefetchImportOptions( self ) -> PrefetchImportOptions.PrefetchImportOptions:
        
        return self._prefetch_import_options
        
    
    def GetPresentationImportOptions( self ) -> PresentationImportOptions.PresentationImportOptions:
        
        return self._presentation_import_options
        
    
    def GetSummary( self ):
        
        if self._is_default:
            
            return 'Using whatever the default file import options is at at time of import.'
            
        
        statements = []
        
        #
        
        statements.append( self._file_filtering_import_options.GetSummary() )
        
        #
        
        statements.append( self._location_import_options.GetSummary() )
        
        #
        
        statements.append( self._presentation_import_options.GetSummary() )
        
        #
        
        summary = '\n'.join( statements )
        
        return summary
        
    
    def IsDefault( self ) -> bool:
        
        return self._is_default
        
    
    def SetFileFilteringImportOptions( self, file_filtering_import_options: FileFilteringImportOptions.FileFilteringImportOptions ):
        
        self._file_filtering_import_options = file_filtering_import_options
        
    
    def SetIsDefault( self, value: bool ) -> None:
        
        self._is_default = value
        
    
    def SetLocationImportOptions( self, location_import_options: LocationImportOptions.LocationImportOptions ):
        
        self._location_import_options = location_import_options
        
    
    def SetPrefetchImportOptions( self, prefetch_import_options: PrefetchImportOptions.PrefetchImportOptions ):
        
        self._prefetch_import_options = prefetch_import_options
        
    
    def SetPresentationImportOptions( self, presentation_import_options: PresentationImportOptions.PresentationImportOptions ):
        
        self._presentation_import_options = presentation_import_options
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS_LEGACY ] = FileImportOptionsLegacy
