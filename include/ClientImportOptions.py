from . import ClientConstants as CC
from . import ClientData
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusText
import os
import re

def NewInboxArchiveMatch( new_files, inbox_files, archive_files, status, inbox ):
    
    if status == CC.STATUS_SUCCESSFUL_AND_NEW and new_files:
        
        return True
        
    elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
        
        if inbox and inbox_files:
            
            return True
            
        elif not inbox and archive_files:
            
            return True
            
        
    
    return False
    
def NewInboxArchiveMatchIgnorantOfInbox( new_files, inbox_files, archive_files, status ):
    
    if status == CC.STATUS_SUCCESSFUL_AND_NEW and new_files:
        
        return True
        
    elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT and archive_files and inbox_files:
        
        return True
        
    
    return False
    
def NewInboxArchiveNonMatchIgnorantOfInbox( new_files, inbox_files, archive_files, status ):
    
    if status == CC.STATUS_SUCCESSFUL_AND_NEW and not new_files:
        
        return True
        
    elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT and not ( archive_files or inbox_files ):
        
        return True
        
    
    return False
    
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
        
    
    def _GetCurrentFilesVelocity( self, file_seed_cache, last_check_time ):
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        since = last_check_time - death_time_delta
        
        current_files_found = file_seed_cache.GetNumNewFilesSince( since )
        
        # when a thread is only 30mins old (i.e. first file was posted 30 mins ago), we don't want to calculate based on a longer delete time delta
        # we want next check to be like 30mins from now, not 12 hours
        # so we'll say "5 files in 30 mins" rather than "5 files in 24 hours"
        
        earliest_source_time = file_seed_cache.GetEarliestSourceTime()
        
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
        
    
    def GetNextCheckTime( self, file_seed_cache, last_check_time, last_next_check_time ):
        
        if len( file_seed_cache ) == 0:
            
            if last_check_time == 0:
                
                return 0 # haven't checked yet, so should check immediately
                
            else:
                
                return HydrusData.GetNow() + self._never_slower_than
                
            
        elif self._never_faster_than == self._never_slower_than:
            
            if last_next_check_time is None or last_next_check_time == 0:
                
                next_check_time = last_check_time - 5
                
            else:
                
                next_check_time = last_next_check_time
                
            
            while HydrusData.TimeHasPassed( next_check_time ):
                
                next_check_time += self._never_slower_than
                
            
            return next_check_time
            
        else:
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
            
            if current_files_found == 0:
                
                # this shouldn't typically matter, since a dead checker won't care about next check time
                # so let's just have a nice safe value in case this is ever asked legit
                check_period = self._never_slower_than
                
            else:
                
                approx_time_per_file = current_time_delta // current_files_found
                
                ideal_check_period = self._intended_files_per_check * approx_time_per_file
                
                # if a thread produced lots of files and then stopped completely for whatever reason, we don't want to keep checking fast
                # so, we set a lower limit of time since last file upload, neatly doubling our check period in these situations
                
                latest_source_time = file_seed_cache.GetLatestSourceTime()
                
                time_since_latest_file = max( last_check_time - latest_source_time, 30 )
                
                never_faster_than = max( self._never_faster_than, time_since_latest_file )
                
                check_period = min( max( never_faster_than, ideal_check_period ), self._never_slower_than )
                
            
            return last_check_time + check_period
            
        
    
    def GetPrettyCurrentVelocity( self, file_seed_cache, last_check_time, no_prefix = False ):
        
        if len( file_seed_cache ) == 0:
            
            if last_check_time == 0:
                
                pretty_current_velocity = 'no files yet'
                
            else:
                
                pretty_current_velocity = 'no files, unable to determine velocity'
                
            
        else:
            
            if no_prefix:
                
                pretty_current_velocity = ''
                
            else:
                
                pretty_current_velocity = 'at last check, found '
                
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
            
            pretty_current_velocity += HydrusData.ToHumanInt( current_files_found ) + ' files in previous ' + HydrusData.TimeDeltaToPrettyTimeDelta( current_time_delta )
            
        
        return pretty_current_velocity
        
    
    def GetRawCurrentVelocity( self, file_seed_cache, last_check_time ):
        
        return self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
        
    
    def GetSummary( self ):
        
        if self._never_faster_than == self._never_slower_than:
            
            timing_statement = 'Checking every ' + HydrusData.TimeDeltaToPrettyTimeDelta( self._never_faster_than ) + '.'
            
        else:
            
            timing_statement = 'Trying to get ' + HydrusData.ToHumanInt( self._intended_files_per_check ) + ' files per check, never faster than ' + HydrusData.TimeDeltaToPrettyTimeDelta( self._never_faster_than ) + ' and never slower than ' + HydrusData.TimeDeltaToPrettyTimeDelta( self._never_slower_than ) + '.'
            
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        if death_files_found == 0:
            
            death_statement = 'Never stopping.'
            
        else:
            
            death_statement = 'Stopping if file velocity falls below ' + HydrusData.ToHumanInt( death_files_found ) + ' files per ' + HydrusData.TimeDeltaToPrettyTimeDelta( death_time_delta ) + '.'
            
        
        return timing_statement + os.linesep * 2 + death_statement
        
    
    def IsDead( self, file_seed_cache, last_check_time ):
        
        if len( file_seed_cache ) == 0 and last_check_time == 0:
            
            return False
            
        else:
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
            
            ( death_files_found, deleted_time_delta ) = self._death_file_velocity
            
            current_file_velocity_float = current_files_found / current_time_delta
            death_file_velocity_float = death_files_found / deleted_time_delta
            
            return current_file_velocity_float < death_file_velocity_float
            
        
    
    def ToTuple( self ):
        
        return ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CHECKER_OPTIONS ] = CheckerOptions

class FilenameTaggingOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS
    SERIALISABLE_NAME = 'Filename Tagging Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tags_for_all = set()
        
        self._load_from_neighbouring_txt_files = False
        
        self._add_filename = ( False, '' )
        
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
        
        if self._load_from_neighbouring_txt_files:
            
            txt_path = path + '.txt'
            
            if os.path.exists( txt_path ):
                
                with open( txt_path, 'r', encoding = 'utf-8'  ) as f:
                    
                    txt_tags_string = f.read()
                    
                
                try:
                    
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
        
        siblings_manager = HG.client_controller.tag_siblings_manager
        parents_manager = HG.client_controller.tag_parents_manager
        
        tags = siblings_manager.CollapseTags( service_key, tags )
        tags = parents_manager.ExpandTags( service_key, tags )
        tags = HG.client_controller.tag_censorship_manager.FilterTags( service_key, tags )
        
        return tags
        
    
    def SimpleSetTuple( self, tags_for_all, load_from_neighbouring_txt_files, add_filename, directories_dict ):
        
        self._tags_for_all = tags_for_all
        self._load_from_neighbouring_txt_files = load_from_neighbouring_txt_files
        self._add_filename = add_filename
        self._directories_dict = directories_dict
        
    
    def SimpleToTuple( self ):
        
        return ( self._tags_for_all, self._load_from_neighbouring_txt_files, self._add_filename, self._directories_dict )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS ] = FilenameTaggingOptions    

class FileImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'File Import Options'
    SERIALISABLE_VERSION = 4
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._exclude_deleted = True
        self._do_not_check_known_urls_before_importing = False
        self._do_not_check_hashes_before_importing = False
        self._allow_decompression_bombs = False
        self._min_size = None
        self._max_size = None
        self._max_gif_size = None
        self._min_resolution = None
        self._max_resolution = None
        self._automatic_archive = False
        self._associate_source_urls = True
        self._present_new_files = True
        self._present_already_in_inbox_files = True
        self._present_already_in_archive_files = True
        
    
    def _GetSerialisableInfo( self ):
        
        pre_import_options = ( self._exclude_deleted, self._do_not_check_known_urls_before_importing, self._do_not_check_hashes_before_importing, self._allow_decompression_bombs, self._min_size, self._max_size, self._max_gif_size, self._min_resolution, self._max_resolution )
        post_import_options = ( self._automatic_archive, self._associate_source_urls )
        presentation_options = ( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files )
        
        return ( pre_import_options, post_import_options, presentation_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( pre_import_options, post_import_options, presentation_options ) = serialisable_info
        
        ( self._exclude_deleted, self._do_not_check_known_urls_before_importing, self._do_not_check_hashes_before_importing, self._allow_decompression_bombs, self._min_size, self._max_size, self._max_gif_size, self._min_resolution, self._max_resolution ) = pre_import_options
        ( self._automatic_archive, self._associate_source_urls ) = post_import_options
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
            
        
    
    def AllowsDecompressionBombs( self ):
        
        return self._allow_decompression_bombs
        
    
    def AutomaticallyArchives( self ):
        
        return self._automatic_archive
        
    
    def CheckFileIsValid( self, size, mime, width, height ):
        
        if self._min_size is not None and size < self._min_size:
            
            raise HydrusExceptions.SizeException( 'File was ' + HydrusData.ToHumanBytes( size ) + ' but the lower limit is ' + HydrusData.ToHumanBytes( self._min_size ) + '.' )
            
        
        if self._max_size is not None and size > self._max_size:
            
            raise HydrusExceptions.SizeException( 'File was ' + HydrusData.ToHumanBytes( size ) + ' but the upper limit is ' + HydrusData.ToHumanBytes( self._max_size ) + '.' )
            
        
        if mime == HC.IMAGE_GIF and self._max_gif_size is not None and size > self._max_gif_size:
            
            raise HydrusExceptions.SizeException( 'File was ' + HydrusData.ToHumanBytes( size ) + ' but the upper limit for gifs is ' + HydrusData.ToHumanBytes( self._max_gif_size ) + '.' )
            
        
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
                
            
        
    
    def CheckNetworkDownload( self, possible_mime, num_bytes, is_complete_file_size ):
        
        if is_complete_file_size:
            
            error_prefix = 'Download was apparently '
            
        else:
            
            error_prefix = 'Download was at least '
            
        
        if possible_mime is not None:
            
            if possible_mime == HC.IMAGE_GIF and self._max_gif_size is not None and num_bytes > self._max_gif_size:
                
                raise HydrusExceptions.SizeException( error_prefix + HydrusData.ToHumanBytes( num_bytes ) + ' but the upper limit for gifs is ' + HydrusData.ToHumanBytes( self._max_gif_size ) + '.' )
                
            
        
        if self._max_size is not None and num_bytes > self._max_size:
            
            raise HydrusExceptions.SizeException( error_prefix + HydrusData.ToHumanBytes( num_bytes ) + ' but the upper limit is ' + HydrusData.ToHumanBytes( self._max_size ) + '.' )
            
        
        if is_complete_file_size:
            
            if self._min_size is not None and num_bytes < self._min_size:
                
                raise HydrusExceptions.SizeException( error_prefix + HydrusData.ToHumanBytes( num_bytes ) + ' but the lower limit is ' + HydrusData.ToHumanBytes( self._min_size ) + '.' )
                
            
        
    
    def ExcludesDeleted( self ):
        
        return self._exclude_deleted
        
    
    def GetPostImportOptions( self ):
        
        post_import_options = ( self._automatic_archive, self._associate_source_urls )
        
        return post_import_options
        
    
    def GetPresentationOptions( self ):
        
        presentation_options = ( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files )
        
        return presentation_options
        
    
    def GetPreImportOptions( self ):
        
        pre_import_options = ( self._exclude_deleted, self._do_not_check_known_urls_before_importing, self._do_not_check_hashes_before_importing, self._allow_decompression_bombs, self._min_size, self._max_size, self._max_gif_size, self._min_resolution, self._max_resolution )
        
        return pre_import_options
        
    
    def GetSummary( self ):
        
        statements = []
        
        if self._exclude_deleted:
            
            statements.append( 'excluding previously deleted' )
            
        
        if not self._allow_decompression_bombs:
            
            statements.append( 'excluding decompression bombs' )
            
        
        if self._min_size is not None:
            
            statements.append( 'excluding < ' + HydrusData.ToHumanBytes( self._min_size ) )
            
        
        if self._max_size is not None:
            
            statements.append( 'excluding > ' + HydrusData.ToHumanBytes( self._max_size ) )
            
        
        if self._max_gif_size is not None:
            
            statements.append( 'excluding gifs > ' + HydrusData.ToHumanBytes( self._max_gif_size ) )
            
        
        if self._min_resolution is not None:
            
            ( width, height ) = self._min_resolution
            
            statements.append( 'excluding < ( ' + HydrusData.ToHumanInt( width ) + ' x ' + HydrusData.ToHumanInt( height ) + ' )' )
            
        
        if self._max_resolution is not None:
            
            ( width, height ) = self._max_resolution
            
            statements.append( 'excluding > ( ' + HydrusData.ToHumanInt( width ) + ' x ' + HydrusData.ToHumanInt( height ) + ' )' )
            
        
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
        
    
    def SetPostImportOptions( self, automatic_archive, associate_source_urls ):
        
        self._automatic_archive = automatic_archive
        self._associate_source_urls = associate_source_urls
        
    
    def SetPresentationOptions( self, present_new_files, present_already_in_inbox_files, present_already_in_archive_files ):
        
        self._present_new_files = present_new_files
        self._present_already_in_inbox_files = present_already_in_inbox_files
        self._present_already_in_archive_files = present_already_in_archive_files
        
    
    def SetPreImportOptions( self, exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution ):
        
        self._exclude_deleted = exclude_deleted
        self._do_not_check_known_urls_before_importing = do_not_check_known_urls_before_importing
        self._do_not_check_hashes_before_importing = do_not_check_hashes_before_importing
        self._allow_decompression_bombs = allow_decompression_bombs
        self._min_size = min_size
        self._max_size = max_size
        self._max_gif_size = max_gif_size
        self._min_resolution = min_resolution
        self._max_resolution = max_resolution
        
    
    def ShouldAssociateSourceURLs( self ):
        
        return self._associate_source_urls
        
    
    def DoNotCheckHashesBeforeImporting( self ):
        
        return self._do_not_check_hashes_before_importing
        
    
    def DoNotCheckKnownURLsBeforeImporting( self ):
        
        return self._do_not_check_known_urls_before_importing
        
    
    def ShouldNotPresentIgnorantOfInbox( self, status ):
        
        return NewInboxArchiveNonMatchIgnorantOfInbox( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files, status )
        
    
    def ShouldPresent( self, status, inbox ):
        
        return NewInboxArchiveMatch( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files, status, inbox )
        
    
    def ShouldPresentIgnorantOfInbox( self, status ):
        
        return NewInboxArchiveMatchIgnorantOfInbox( self._present_new_files, self._present_already_in_inbox_files, self._present_already_in_archive_files, status )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS ] = FileImportOptions

class TagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Tag Import Options'
    SERIALISABLE_VERSION = 7
    
    def __init__( self, fetch_tags_even_if_url_recognised_and_file_already_in_db = False, fetch_tags_even_if_hash_recognised_and_file_already_in_db = False, tag_blacklist = None, service_keys_to_service_tag_import_options = None, is_default = False ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if tag_blacklist is None:
            
            tag_blacklist = ClientTags.TagFilter()
            
        
        if service_keys_to_service_tag_import_options is None:
            
            service_keys_to_service_tag_import_options = {}
            
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_hash_recognised_and_file_already_in_db
        self._tag_blacklist = tag_blacklist
        self._service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options
        self._is_default = is_default
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            test_func = services_manager.ServiceExists
            
        else:
            
            def test_func( service_key ):
                
                return True
                
            
        
        serialisable_tag_blacklist = self._tag_blacklist.GetSerialisableTuple()
        
        serialisable_service_keys_to_service_tag_import_options = [ ( service_key.hex(), service_tag_import_options.GetSerialisableTuple() ) for ( service_key, service_tag_import_options ) in list(self._service_keys_to_service_tag_import_options.items()) if test_func( service_key ) ]
        
        return ( self._fetch_tags_even_if_url_recognised_and_file_already_in_db, self._fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options, self._is_default )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._fetch_tags_even_if_url_recognised_and_file_already_in_db, self._fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options, self._is_default ) = serialisable_info
        
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
            
            tag_blacklist = ClientTags.TagFilter()
            
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
            
        
    
    def CheckBlacklist( self, tags ):
        
        sibling_tags = HG.client_controller.tag_siblings_manager.CollapseTags( CC.COMBINED_TAG_SERVICE_KEY, tags )
        
        for test_tags in ( tags, sibling_tags ):
            
            ok_tags = self._tag_blacklist.Filter( test_tags )
            
            if len( ok_tags ) < len( test_tags ):
                
                bad_tags = set( test_tags ).difference( ok_tags )
                
                bad_tags = HydrusTags.SortNumericTags( bad_tags )
                
                raise HydrusExceptions.VetoException( ', '.join( bad_tags ) + ' is blacklisted!' )
                
            
        
    
    def GetServiceKeysToContentUpdates( self, status, in_inbox, hash, parsed_tags ):
        
        siblings_manager = HG.client_controller.tag_siblings_manager
        parents_manager = HG.client_controller.tag_parents_manager
        
        parsed_tags = HydrusTags.CleanTags( parsed_tags )
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        for ( service_key, service_tag_import_options ) in list(self._service_keys_to_service_tag_import_options.items()):
            
            service_parsed_tags = siblings_manager.CollapseTags( service_key, parsed_tags )
            service_parsed_tags = parents_manager.ExpandTags( service_key, service_parsed_tags )
            
            service_tags = service_tag_import_options.GetTags( service_key, status, in_inbox, hash, service_parsed_tags )
            
            if len( service_tags ) > 0:
                
                service_tags = siblings_manager.CollapseTags( service_key, service_tags )
                service_tags = parents_manager.ExpandTags( service_key, service_tags )
                
                service_keys_to_tags[ service_key ] = service_tags
                
            
        
        service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
        
        return service_keys_to_content_updates
        
    
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
                    
                    name = HG.client_controller.services_manager.GetName( service_key )
                    
                except HydrusExceptions.DataMissing:
                    
                    continue
                    
                
                service_statement = name + ':' + os.linesep * 2 + os.linesep.join( sub_statements )
                
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
                
            
            separator = os.linesep * 2
            
            summary = separator.join( statements )
            
        else:
            
            summary = 'not adding any tags'
            
        
        return summary
        
    
    def GetTagBlacklist( self ):
        
        return self._tag_blacklist
        
    
    def HasAdditionalTags( self ):
        
        return True in ( service_tag_import_options.HasAdditionalTags() for service_tag_import_options in list(self._service_keys_to_service_tag_import_options.values()) )
        
    
    def IsDefault( self ):
        
        return self._is_default
        
    
    def SetDefault( self ):
        
        self._is_default = True
        
    
    def ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_hash_recognised_and_file_already_in_db
        
    
    def ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_url_recognised_and_file_already_in_db
        
    
    def WorthFetchingTags( self ):
        
        return True in ( service_tag_import_options.WorthFetchingTags() for service_tag_import_options in list(self._service_keys_to_service_tag_import_options.values()) )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS ] = TagImportOptions

class ServiceTagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Service Tag Import Options'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, get_tags = False, get_tags_filter = None, additional_tags = None, to_new_files = True, to_already_in_inbox = True, to_already_in_archive = True, only_add_existing_tags = False, only_add_existing_tags_filter = None ):
        
        if get_tags_filter is None:
            
            get_tags_filter = ClientTags.TagFilter()
            
        
        if additional_tags is None:
            
            additional_tags = []
            
        
        if only_add_existing_tags_filter is None:
            
            only_add_existing_tags_filter = ClientTags.TagFilter()
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._get_tags = get_tags
        self._get_tags_filter = get_tags_filter
        self._additional_tags = additional_tags
        self._to_new_files = to_new_files
        self._to_already_in_inbox = to_already_in_inbox
        self._to_already_in_archive = to_already_in_archive
        self._only_add_existing_tags = only_add_existing_tags
        self._only_add_existing_tags_filter = only_add_existing_tags_filter
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_get_tags_filter = self._get_tags_filter.GetSerialisableTuple()
        serialisable_only_add_existing_tags_filter = self._only_add_existing_tags_filter.GetSerialisableTuple()
        
        return ( self._get_tags, serialisable_get_tags_filter, list( self._additional_tags ), self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, serialisable_only_add_existing_tags_filter )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._get_tags, serialisable_get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, serialisable_only_add_existing_tags_filter ) = serialisable_info
        
        self._get_tags_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_get_tags_filter )
        self._only_add_existing_tags_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_only_add_existing_tags_filter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( get_tags, namespaces, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags ) = old_serialisable_info
            
            get_tags_filter = ClientTags.TagFilter()
            only_add_existing_tags_filter = ClientTags.TagFilter()
            
            serialisable_get_tags_filter = get_tags_filter.GetSerialisableTuple()
            serialisable_only_add_existing_tags_filter = only_add_existing_tags_filter.GetSerialisableTuple()
            
            new_serialisable_info = ( get_tags, serialisable_get_tags_filter, namespaces, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( get_tags, serialisable_get_tags_filter, namespaces, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter ) = old_serialisable_info
            
            if not get_tags and len( namespaces ) > 0:
                
                get_tags = True
                get_tags_filter = ClientTags.TagFilter()
                
                namespaces = list( namespaces )
                
                get_tags_filter.SetRule( ':', CC.FILTER_BLACKLIST )
                
                if '' in namespaces: # if unnamespaced in original checkboxes, then leave it unblocked
                    
                    namespaces.remove( '' )
                    
                else: # else block it
                    
                    get_tags_filter.SetRule( '', CC.FILTER_BLACKLIST )
                    
                
                for namespace in namespaces:
                    
                    get_tags_filter.SetRule( namespace + ':', CC.FILTER_WHITELIST )
                    
                
                serialisable_get_tags_filter = get_tags_filter.GetSerialisableTuple()
                
            
            new_serialisable_info = ( get_tags, serialisable_get_tags_filter, additional_tags, to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags, serialisable_only_add_existing_tags_filter )
            
            return ( 3, new_serialisable_info )
            
        
    
    def GetSummaryStatements( self ):
        
        statements = []
        
        if self._get_tags:
            
            statements.append( self._get_tags_filter.ToPermittedString() )
            
        
        if len( self._additional_tags ) > 0:
            
            pretty_additional_tags = list( self._additional_tags )
            
            pretty_additional_tags.sort()
            
            statements.append( 'additional tags: ' + ', '.join( pretty_additional_tags ) )
            
        
        return statements
        
    
    def GetTags( self, service_key, status, in_inbox, hash, parsed_tags ):
        
        tags = set()
        
        if NewInboxArchiveMatch( self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, status, in_inbox ):
            
            if self._get_tags:
                
                filtered_tags = self._get_tags_filter.Filter( parsed_tags )
                
                tags.update( filtered_tags )
                
            
            tags.update( HydrusTags.CleanTags( self._additional_tags ) )
            
            if self._only_add_existing_tags:
                
                applicable_tags = self._only_add_existing_tags_filter.Filter( tags )
                
                tags.difference_update( applicable_tags )
                
                existing_applicable_tags = HG.client_controller.Read( 'filter_existing_tags', service_key, tags )
                
                tags.update( existing_applicable_tags )
                
            
        
        return tags
        
    
    def HasAdditionalTags( self ):
        
        return len( self._additional_tags ) > 0
        
    
    def ToTuple( self ):
        
        return ( self._get_tags, self._get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter )
        
    
    def WorthFetchingTags( self ):
        
        return self._get_tags
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_TAG_IMPORT_OPTIONS ] = ServiceTagImportOptions
