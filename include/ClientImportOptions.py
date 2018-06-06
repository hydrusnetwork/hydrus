import ClientConstants as CC
import ClientData
import ClientTags
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import HydrusText
import os
import re

class CheckerOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CHECKER_OPTIONS
    SERIALISABLE_NAME = 'Checker Timing Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, intended_files_per_check = 8, never_faster_than = 300, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._intended_files_per_check = intended_files_per_check
        self._never_faster_than = never_faster_than
        self._never_slower_than = never_slower_than
        self._death_file_velocity = death_file_velocity
        
    
    def _GetCurrentFilesVelocity( self, seed_cache, last_check_time ):
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        since = last_check_time - death_time_delta
        
        current_files_found = seed_cache.GetNumNewFilesSince( since )
        
        # when a thread is only 30mins old (i.e. first file was posted 30 mins ago), we don't want to calculate based on a longer delete time delta
        # we want next check to be like 30mins from now, not 12 hours
        # so we'll say "5 files in 30 mins" rather than "5 files in 24 hours"
        
        earliest_source_time = seed_cache.GetEarliestSourceTime()
        
        if earliest_source_time is None:
            
            current_time_delta = death_time_delta
            
        else:
            
            early_time_delta = max( last_check_time - earliest_source_time, 30 )
            
            current_time_delta = min( early_time_delta, death_time_delta )
            
        
        return ( current_files_found, current_time_delta )
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity ) = serialisable_info
        
    
    def GetDeathFileVelocityPeriod( self ):
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        return death_time_delta
        
    
    def GetNextCheckTime( self, seed_cache, last_check_time ):
        
        if len( seed_cache ) == 0:
            
            if last_check_time == 0:
                
                return 0 # haven't checked yet, so should check immediately
                
            else:
                
                return HydrusData.GetNow() + self._never_slower_than
                
            
        else:
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( seed_cache, last_check_time )
            
            if current_files_found == 0:
                
                # this shouldn't typically matter, since a dead checker won't care about next check time
                # so let's just have a nice safe value in case this is ever asked legit
                check_period = self._never_slower_than
                
            else:
                
                approx_time_per_file = current_time_delta / current_files_found
                
                ideal_check_period = self._intended_files_per_check * approx_time_per_file
                
                # if a thread produced lots of files and then stopped completely for whatever reason, we don't want to keep checking fast
                # so, we set a lower limit of time since last file upload, neatly doubling our check period in these situations
                
                latest_source_time = seed_cache.GetLatestSourceTime()
                
                time_since_latest_file = max( last_check_time - latest_source_time, 30 )
                
                never_faster_than = max( self._never_faster_than, time_since_latest_file )
                
                check_period = min( max( never_faster_than, ideal_check_period ), self._never_slower_than )
                
            
            return last_check_time + check_period
            
        
    
    def GetRawCurrentVelocity( self, seed_cache, last_check_time ):
        
        return self._GetCurrentFilesVelocity( seed_cache, last_check_time )
        
    
    def GetPrettyCurrentVelocity( self, seed_cache, last_check_time, no_prefix = False ):
        
        if len( seed_cache ) == 0:
            
            if last_check_time == 0:
                
                pretty_current_velocity = 'no files yet'
                
            else:
                
                pretty_current_velocity = 'no files, unable to determine velocity'
                
            
        else:
            
            if no_prefix:
                
                pretty_current_velocity = ''
                
            else:
                
                pretty_current_velocity = 'at last check, found '
                
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( seed_cache, last_check_time )
            
            pretty_current_velocity += HydrusData.ConvertIntToPrettyString( current_files_found ) + ' files in previous ' + HydrusData.ConvertTimeDeltaToPrettyString( current_time_delta )
            
        
        return pretty_current_velocity
        
    
    def IsDead( self, seed_cache, last_check_time ):
        
        if len( seed_cache ) == 0 and last_check_time == 0:
            
            return False
            
        else:
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( seed_cache, last_check_time )
            
            ( death_files_found, deleted_time_delta ) = self._death_file_velocity
            
            current_file_velocity_float = current_files_found / float( current_time_delta )
            death_file_velocity_float = death_files_found / float( deleted_time_delta )
            
            return current_file_velocity_float < death_file_velocity_float
            
        
    
    def ToTuple( self ):
        
        return ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CHECKER_OPTIONS ] = CheckerOptions

class FilenameTaggingOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS
    SERIALISABLE_NAME = 'Filename Tagging Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tags_for_all = set()
        
        self._load_from_neighbouring_txt_files = False
        
        self._add_filename = ( False, '' )
        self._add_first_directory = ( False, '' )
        self._add_second_directory = ( False, '' )
        self._add_third_directory = ( False, '' )
        
        self._quick_namespaces = []
        self._regexes = []
        
    
    def _GetSerialisableInfo( self ):
        
        return ( list( self._tags_for_all ), self._load_from_neighbouring_txt_files, self._add_filename, self._add_first_directory, self._add_second_directory, self._add_third_directory, self._quick_namespaces, self._regexes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( tags_for_all_list, self._load_from_neighbouring_txt_files, self._add_filename, self._add_first_directory, self._add_second_directory, self._add_third_directory, self._quick_namespaces, self._regexes ) = serialisable_info
        
        # converting [ namespace, regex ] to ( namespace, regex ) for listctrl et al to handle better
        self._quick_namespaces = [ tuple( item ) for item in self._quick_namespaces ]
        self._tags_for_all = set( tags_for_all_list )
        
    
    def AdvancedSetTuple( self, quick_namespaces, regexes ):
        
        self._quick_namespaces = quick_namespaces
        self._regexes = regexes
        
    
    def AdvancedToTuple( self ):
        
        return ( self._quick_namespaces, self._regexes )
        
    
    def GetTags( self, service_key, path ):
        
        tags = set()
        
        tags.update( self._tags_for_all )
        
        if self._load_from_neighbouring_txt_files:
            
            txt_path = path + '.txt'
            
            if os.path.exists( txt_path ):
                
                with open( txt_path, 'rb' ) as f:
                    
                    txt_tags_string = f.read()
                    
                
                try:
                    
                    txt_tags_string = HydrusData.ToUnicode( txt_tags_string )
                    
                    txt_tags = [ tag for tag in HydrusText.DeserialiseNewlinedTexts( txt_tags_string ) ]
                    
                    if True in ( len( txt_tag ) > 1024 for txt_tag in txt_tags ):
                        
                        HydrusData.ShowText( 'Tags were too long--I think this was not a regular text file!' )
                        
                        raise Exception()
                        
                    
                    tags.update( txt_tags )
                    
                except:
                    
                    HydrusData.ShowText( 'Could not parse the tags from ' + txt_path + '!' )
                    
                    tags.add( '___had problem parsing .txt file' )
                    
                
            
        
        ( base, filename ) = os.path.split( path )
        
        ( filename, any_ext_gumpf ) = os.path.splitext( filename )
        
        ( filename_boolean, filename_namespace ) = self._add_filename
        
        if filename_boolean:
            
            if filename_namespace != '':
                
                tag = filename_namespace + ':' + filename
                
            else:
                
                tag = filename
                
            
            tags.add( tag )
            
        
        ( drive, dirs ) = os.path.splitdrive( base )
        
        while dirs.startswith( os.path.sep ):
            
            dirs = dirs[1:]
            
        
        dirs = dirs.split( os.path.sep )
        
        ( dir_1_boolean, dir_1_namespace ) = self._add_first_directory
        
        if len( dirs ) > 0 and dir_1_boolean:
            
            if dir_1_namespace != '':
                
                tag = dir_1_namespace + ':' + dirs[0]
                
            else:
                
                tag = dirs[0]
                
            
            tags.add( tag )
            
        
        ( dir_2_boolean, dir_2_namespace ) = self._add_second_directory
        
        if len( dirs ) > 1 and dir_2_boolean:
            
            if dir_2_namespace != '':
                
                tag = dir_2_namespace + ':' + dirs[1]
                
            else:
                
                tag = dirs[1]
                
            
            tags.add( tag )
            
        
        ( dir_3_boolean, dir_3_namespace ) = self._add_third_directory
        
        if len( dirs ) > 2 and dir_3_boolean:
            
            if dir_3_namespace != '':
                
                tag = dir_3_namespace + ':' + dirs[2]
                
            else:
                
                tag = dirs[2]
                
            
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
        
        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        tag_censorship_manager = HG.client_controller.GetManager( 'tag_censorship' )
        
        tags = siblings_manager.CollapseTags( service_key, tags )
        tags = parents_manager.ExpandTags( service_key, tags )
        tags = tag_censorship_manager.FilterTags( service_key, tags )
        
        return tags
        
    
    def SimpleSetTuple( self, tags_for_all, load_from_neighbouring_txt_files, add_filename, add_first_directory, add_second_directory, add_third_directory ):
        
        self._tags_for_all = tags_for_all
        self._load_from_neighbouring_txt_files = load_from_neighbouring_txt_files
        self._add_filename = add_filename
        self._add_first_directory = add_first_directory
        self._add_second_directory = add_second_directory
        self._add_third_directory = add_third_directory
        
    
    def SimpleToTuple( self ):
        
        return ( self._tags_for_all, self._load_from_neighbouring_txt_files, self._add_filename, self._add_first_directory, self._add_second_directory, self._add_third_directory )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS ] = FilenameTaggingOptions    

class FileImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'File Import Options'
    SERIALISABLE_VERSION = 3
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._exclude_deleted = True
        self._allow_decompression_bombs = False
        self._min_size = None
        self._max_size = None
        self._max_gif_size = None
        self._min_resolution = None
        self._max_resolution = None
        self._automatic_archive = False
        self._present_new_files = True
        self._present_already_in_inbox_files = True
        self._present_already_in_archive_files = True
        
    
    def _GetSerialisableInfo( self ):
        
        pre_import_options = ( self._exclude_deleted, self._allow_decompression_bombs, self._min_size, self._max_size, self._max_gif_size, self._min_resolution, self._max_resolution )
        post_import_options = self._automatic_archive
        presentation_options = ( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files )
        
        return ( pre_import_options, post_import_options, presentation_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( pre_import_options, post_import_options, presentation_options ) = serialisable_info
        
        ( self._exclude_deleted, self._allow_decompression_bombs, self._min_size, self._max_size, self._max_gif_size, self._min_resolution, self._max_resolution ) = pre_import_options
        self._automatic_archive = post_import_options
        ( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files ) = presentation_options 
        
    
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
            
            allow_decompression_bombs = False
            max_gif_size = 32 * 1048576
            
            pre_import_options = ( exclude_deleted, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
            post_import_options = automatic_archive
            presentation_options = ( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
            
            new_serialisable_info = ( pre_import_options, post_import_options, presentation_options )
            
            return ( 3, new_serialisable_info )
            
        
    
    def AllowsDecompressionBombs( self ):
        
        return self._allow_decompression_bombs
        
    
    def AutomaticallyArchives( self ):
        
        return self._automatic_archive
        
    
    def CheckFileIsValid( self, size, mime, width, height ):
        
        if self._min_size is not None and size < self._min_size:
            
            raise HydrusExceptions.SizeException( 'File was ' + HydrusData.ConvertIntToBytes( size ) + ' but the lower limit is ' + HydrusData.ConvertIntToBytes( self._min_size ) + '.' )
            
        
        if self._max_size is not None and size > self._max_size:
            
            raise HydrusExceptions.SizeException( 'File was ' + HydrusData.ConvertIntToBytes( size ) + ' but the upper limit is ' + HydrusData.ConvertIntToBytes( self._max_size ) + '.' )
            
        
        if mime == HC.IMAGE_GIF and self._max_gif_size is not None and size > self._max_gif_size:
            
            raise HydrusExceptions.SizeException( 'File was ' + HydrusData.ConvertIntToBytes( size ) + ' but the upper limit for gifs is ' + HydrusData.ConvertIntToBytes( self._max_gif_size ) + '.' )
            
        
        if self._min_resolution is not None:
            
            ( min_width, min_height ) = self._min_resolution
            
            too_thin = width is not None and width < min_width
            too_short = height is not None and height < min_height
            
            if too_thin or too_short:
                
                raise HydrusExceptions.SizeException( 'File had resolution ' + HydrusData.ConvertResolutionToPrettyString( ( width, height ) ) + ' but the lower limit is ' + HydrusData.ConvertResolutionToPrettyString( self._min_resolution ) )
                
            
        
        if self._max_resolution is not None:
            
            ( max_width, max_height ) = self._max_resolution
            
            too_wide = width is not None and width > max_width
            too_tall = height is not None and height > max_height
            
            if too_wide or too_tall:
                
                raise HydrusExceptions.SizeException( 'File had resolution ' + HydrusData.ConvertResolutionToPrettyString( ( width, height ) ) + ' but the upper limit is ' + HydrusData.ConvertResolutionToPrettyString( self._max_resolution ) )
                
            
        
    
    def CheckNetworkDownload( self, possible_mime, size, certain ):
        
        if certain:
            
            # by certain, we really mean 'content-length said', hence the 'apparently'
            
            error_prefix = 'Download was apparently '
            
        else:
            
            error_prefix = 'Download was at least '
            
        
        if possible_mime is not None:
            
            if possible_mime == HC.IMAGE_GIF and self._max_gif_size is not None and size > self._max_gif_size:
                
                raise HydrusExceptions.SizeException( error_prefix + HydrusData.ConvertIntToBytes( size ) + ' but the upper limit for gifs is ' + HydrusData.ConvertIntToBytes( self._max_gif_size ) + '.' )
                
            
        
        if self._max_size is not None and size > self._max_size:
            
            raise HydrusExceptions.SizeException( error_prefix + HydrusData.ConvertIntToBytes( size ) + ' but the upper limit is ' + HydrusData.ConvertIntToBytes( self._max_size ) + '.' )
            
        
        if certain:
            
            if self._min_size is not None and size < self._min_size:
                
                raise HydrusExceptions.SizeException( error_prefix + HydrusData.ConvertIntToBytes( size ) + ' but the lower limit is ' + HydrusData.ConvertIntToBytes( self._min_size ) + '.' )
                
            
        
    
    def ExcludesDeleted( self ):
        
        return self._exclude_deleted
        
    
    def GetPostImportOptions( self ):
        
        post_import_options = self._automatic_archive
        
        return post_import_options
        
    
    def GetPresentationOptions( self ):
        
        presentation_options = ( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files )
        
        return presentation_options
        
    
    def GetPreImportOptions( self ):
        
        pre_import_options = ( self._exclude_deleted, self._allow_decompression_bombs, self._min_size, self._max_size, self._max_gif_size, self._min_resolution, self._max_resolution )
        
        return pre_import_options
        
    
    def GetSummary( self ):
        
        statements = []
        
        if self._exclude_deleted:
            
            statements.append( 'excluding previously deleted' )
            
        
        if not self._allow_decompression_bombs:
            
            statements.append( 'excluding decompression bombs' )
            
        
        if self._min_size is not None:
            
            statements.append( 'excluding < ' + HydrusData.ConvertIntToBytes( self._min_size ) )
            
        
        if self._max_size is not None:
            
            statements.append( 'excluding > ' + HydrusData.ConvertIntToBytes( self._max_size ) )
            
        
        if self._max_gif_size is not None:
            
            statements.append( 'excluding gifs > ' + HydrusData.ConvertIntToBytes( self._max_gif_size ) )
            
        
        if self._min_resolution is not None:
            
            ( width, height ) = self._min_resolution
            
            statements.append( 'excluding < ( ' + HydrusData.ConvertIntToPrettyString( width ) + ' x ' + HydrusData.ConvertIntToPrettyString( height ) + ' )' )
            
        
        if self._max_resolution is not None:
            
            ( width, height ) = self._max_resolution
            
            statements.append( 'excluding > ( ' + HydrusData.ConvertIntToPrettyString( width ) + ' x ' + HydrusData.ConvertIntToPrettyString( height ) + ' )' )
            
        
        #
        
        if self._automatic_archive:
            
            statements.append( 'automatically archiving' )
            
        
        #
        
        presentation_statements = []
        
        if self._present_new_files:
            
            presentation_statements.append( 'new' )
            
        
        if self._present_already_in_inbox_files:
            
            presentation_statements.append( 'already in inbox' )
            
        
        if self._present_already_in_archive_files:
            
            presentation_statements.append( 'already in archive' )
            
        
        if len( presentation_statements ) == 0:
            
            statements.append( 'not presenting any files' )
            
        elif len( presentation_statements ) == 3:
            
            statements.append( 'presenting all files' )
            
        else:
            
            statements.append( 'presenting ' + ', '.join( presentation_statements ) + ' files' )
            
        
        summary = os.linesep.join( statements )
        
        return summary
        
    
    def SetPostImportOptions( self, automatic_archive ):
        
        self._automatic_archive = automatic_archive
        
    
    def SetPresentationOptions( self, present_new_files, present_already_in_inbox_files, present_already_in_archive_files ):
        
        self._present_new_files = present_new_files
        self._present_already_in_inbox_files = present_already_in_inbox_files
        self._present_already_in_archive_files = present_already_in_archive_files
        
    
    def SetPreImportOptions( self, exclude_deleted, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution ):
        
        self._exclude_deleted = exclude_deleted
        self._allow_decompression_bombs = allow_decompression_bombs
        self._min_size = min_size
        self._max_size = max_size
        self._max_gif_size = max_gif_size
        self._min_resolution = min_resolution
        self._max_resolution = max_resolution
        
    
    def ShouldPresent( self, status, inbox ):
        
        if status == CC.STATUS_SUCCESSFUL_AND_NEW and self._present_new_files:
            
            return True
            
        elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
            
            if inbox and self._present_already_in_inbox_files:
                
                return True
                
            elif not inbox and self._present_already_in_archive_files:
                
                return True
                
            
        
        return False
        
    
    def ShouldPresentIgnorantOfInbox( self, status ):
        
        if status == CC.STATUS_SUCCESSFUL_AND_NEW and self._present_new_files:
            
            return True
            
        else:
            
            if self._present_already_in_archive_files and self._present_already_in_inbox_files:
                
                return True
                
            
        
        return False
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS ] = FileImportOptions

class TagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Tag Import Options'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, fetch_tags_even_if_url_known_and_file_already_in_db = False, tag_blacklist = None, service_keys_to_namespaces = None, service_keys_to_additional_tags = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if tag_blacklist is None:
            
            tag_blacklist = ClientTags.TagFilter()
            
        
        if service_keys_to_namespaces is None:
            
            service_keys_to_namespaces = {}
            
        
        if service_keys_to_additional_tags is None:
            
            service_keys_to_additional_tags = {}
            
        
        self._fetch_tags_even_if_url_known_and_file_already_in_db = fetch_tags_even_if_url_known_and_file_already_in_db
        self._tag_blacklist = tag_blacklist
        self._service_keys_to_namespaces = service_keys_to_namespaces
        self._service_keys_to_additional_tags = service_keys_to_additional_tags
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            test_func = services_manager.ServiceExists
            
        else:
            
            def test_func( service_key ):
                
                return True
                
            
        
        serialisable_tag_blacklist = self._tag_blacklist.GetSerialisableTuple()
        safe_service_keys_to_namespaces = { service_key.encode( 'hex' ) : list( namespaces ) for ( service_key, namespaces ) in self._service_keys_to_namespaces.items() if test_func( service_key ) }
        safe_service_keys_to_additional_tags = { service_key.encode( 'hex' ) : list( tags ) for ( service_key, tags ) in self._service_keys_to_additional_tags.items() if test_func( service_key ) }
        
        return ( self._fetch_tags_even_if_url_known_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._fetch_tags_even_if_url_known_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = serialisable_info
        
        self._tag_blacklist = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_blacklist )
        self._service_keys_to_namespaces = { service_key.decode( 'hex' ) : set( namespaces ) for ( service_key, namespaces ) in safe_service_keys_to_namespaces.items() }
        self._service_keys_to_additional_tags = { service_key.decode( 'hex' ) : set( tags ) for ( service_key, tags ) in safe_service_keys_to_additional_tags.items() }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            safe_service_keys_to_namespaces = old_serialisable_info
            
            safe_service_keys_to_additional_tags = {}
            
            new_serialisable_info = ( safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            fetch_tags_even_if_url_known_and_file_already_in_db = False
            
            new_serialisable_info = ( fetch_tags_even_if_url_known_and_file_already_in_db, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( fetch_tags_even_if_url_known_and_file_already_in_db, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            tag_blacklist = ClientTags.TagFilter()
            
            serialisable_tag_blacklist = tag_blacklist.GetSerialisableTuple()
            
            new_serialisable_info = ( fetch_tags_even_if_url_known_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 4, new_serialisable_info )
            
        
    
    def CheckBlacklist( self, tags ):
        
        ok_tags = self._tag_blacklist.Filter( tags )
        
        if len( ok_tags ) < len( tags ):
            
            bad_tags = set( tags ).difference( ok_tags )
            
            bad_tags = HydrusTags.SortNumericTags( bad_tags )
            
            raise HydrusExceptions.VetoException( ', '.join( bad_tags ) + ' is blacklisted!' )
            
        
    
    def ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_url_known_and_file_already_in_db
        
    
    def GetServiceKeysToAdditionalTags( self ):
        
        return dict( self._service_keys_to_additional_tags )
        
    
    def GetServiceKeysToNamespaces( self ):
        
        return dict( self._service_keys_to_namespaces )
        
    
    def GetServiceKeysToContentUpdates( self, hash, tags ):
        
        tags = HydrusTags.CleanTags( tags )
        
        service_keys_to_tags = collections.defaultdict( set )
        
        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        
        for ( service_key, namespaces ) in self._service_keys_to_namespaces.items():
            
            if len( namespaces ) == 0:
                
                continue
                
            
            tags_to_add_here = [ tag for tag in tags if HydrusTags.SplitTag( tag )[0] in namespaces ]
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( service_key, tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        for ( service_key, additional_tags ) in self._service_keys_to_additional_tags.items():
            
            tags_to_add_here = HydrusTags.CleanTags( additional_tags )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( service_key, tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
        
        return service_keys_to_content_updates
        
    
    def GetSummary( self, show_url_options ):
        
        statements = []
        
        service_keys_to_do = set( self._service_keys_to_additional_tags.keys() ).union( self._service_keys_to_namespaces.keys() )
        
        service_keys_to_do = list( service_keys_to_do )
        
        service_keys_to_do.sort()
        
        for service_key in service_keys_to_do:
            
            sub_statements = []
            
            if service_key in self._service_keys_to_namespaces:
                
                namespaces = list( self._service_keys_to_namespaces[ service_key ] )
                
                if len( namespaces ) > 0:
                    
                    namespaces = [ ClientTags.RenderNamespaceForUser( namespace ) for namespace in namespaces ]
                    
                    namespaces.sort()
                    
                    sub_statements.append( 'namespaces: ' + ', '.join( namespaces ) )
                    
                
            
            if service_key in self._service_keys_to_additional_tags:
                
                additional_tags = list( self._service_keys_to_additional_tags[ service_key ] )
                
                if len( additional_tags ) > 0:
                    
                    additional_tags.sort()
                    
                    sub_statements.append( 'additional tags: ' + ', '.join( additional_tags ) )
                    
                
            
            if len( sub_statements ) > 0:
                
                name = HG.client_controller.services_manager.GetName( service_key )
                
                service_statement = name + ':' + os.linesep * 2 + os.linesep.join( sub_statements )
                
                statements.append( service_statement )
                
            
        
        if len( statements ) > 0:
            
            if show_url_options:
                
                pre_statements = []
                
                pre_statements.append( self._tag_blacklist.ToBlacklistString() )
                
                if self._fetch_tags_even_if_url_known_and_file_already_in_db:
                    
                    s = 'fetching tags even if url is known and file already in db'
                    
                else:
                    
                    s = 'not fetching tags if url is known and file already in db'
                    
                
                pre_statements.append( s )
                
                statements = pre_statements + [ '---' ] + statements
                
            
            separator = os.linesep * 2
            
            summary = separator.join( statements )
            
        else:
            
            summary = 'not adding any tags'
            
        
        return summary
        
    
    def GetTagBlacklist( self ):
        
        return self._tag_blacklist
        
    
    def WorthFetchingTags( self ):
        
        return len( self._service_keys_to_namespaces ) > 0
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS ] = TagImportOptions
