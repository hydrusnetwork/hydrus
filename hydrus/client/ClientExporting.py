import collections
import os
import re

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientFiles
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientSearch
from hydrus.client.media import ClientMediaManagers
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting

MAX_PATH_LENGTH = 240 # bit of padding from 255 for .txt neigbouring and other surprises

def GenerateExportFilename( destination_directory, media, terms, do_not_use_filenames = None ):
    
    def clean_tag_text( t ):
        
        if HC.PLATFORM_WINDOWS:
            
            t = re.sub( r'\\', '_', t )
            
        else:
            
            t = re.sub( '/', '_', t )
            
        
        return t
        
    
    if len( destination_directory ) > ( MAX_PATH_LENGTH - 10 ):
        
        raise Exception( 'The destination directory is too long!' )
        
    
    filename = ''
    
    for ( term_type, term ) in terms:
        
        tags_manager = media.GetTagsManager()
        
        if term_type == 'string':
            
            filename += term
            
        elif term_type == 'namespace':
            
            tags = tags_manager.GetNamespaceSlice( ( term, ), ClientTags.TAG_DISPLAY_ACTUAL )
            
            subtags = sorted( ( HydrusTags.SplitTag( tag )[1] for tag in tags ) )
            
            filename += clean_tag_text( ', '.join( subtags ) )
            
        elif term_type == 'predicate':
            
            if term in ( 'tags', 'nn tags' ):
                
                current = tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL )
                pending = tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL )
                
                tags = sorted( current.union( pending ) )
                
                if term == 'nn tags':
                    
                    tags = [ tag for tag in tags if ':' not in tag ]
                    
                else:
                    
                    tags = [ HydrusTags.SplitTag( tag )[1] for tag in tags ]
                    
                
                filename += clean_tag_text( ', '.join( tags ) )
                
            elif term == 'hash':
                
                hash = media.GetHash()
                
                filename += hash.hex()
                
            elif term == 'file_id':
                
                hash_id = media.GetHashId()
                
                filename += str( hash_id )
                
            
        elif term_type == 'tag':
            
            tag = term
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if tags_manager.HasTag( subtag, ClientTags.TAG_DISPLAY_ACTUAL ):
                
                filename += clean_tag_text( subtag )
                
            
        
    
    while filename.startswith( os.path.sep ):
        
        filename = filename[1:]
        
    
    if HC.PLATFORM_WINDOWS:
        
        # replace many consecutive backspace with single backspace
        filename = re.sub( '\\\\+', '\\\\', filename )
        
        # /, :, *, ?, ", <, >, |
        filename = re.sub( r'/|:|\*|\?|"|<|>|\|', '_', filename )
        
    else:
        
        filename = re.sub( '/+', '/', filename )
        
    
    #
    
    mime = media.GetMime()
    
    ext = HC.mime_ext_lookup[ mime ]
    
    if filename.endswith( ext ):
        
        filename = filename[ : - len( ext ) ]
        
    
    example_dest_path = os.path.join( destination_directory, filename + ext )
    
    excess_chars = len( example_dest_path ) - MAX_PATH_LENGTH
    
    if excess_chars > 0:
        
        filename = filename[ : - excess_chars ]
        
    
    if do_not_use_filenames is not None:
        
        i = 1
        
        possible_filename = '{}{}'.format( filename, ext )
        
        while possible_filename in do_not_use_filenames:
            
            possible_filename = '{} ({}){}'.format( filename, i, ext )
            
            i += 1
            
        
        filename = possible_filename
        
    else:
        
        filename += ext
        
    
    return filename
    
def GetExportPath():
    
    portable_path = HG.client_controller.options[ 'export_path' ]
    
    if portable_path is None:
        
        desired_path = os.path.join( '~', 'hydrus_export' )
        
        path = os.path.expanduser( desired_path )
        
        if path == desired_path:
            
            # could not figure it out, probably crazy user setup atm
            
            return None
            
        
        HydrusPaths.MakeSureDirectoryExists( path )
        
    else:
        
        path = HydrusPaths.ConvertPortablePathToAbsPath( portable_path )
        
    
    return path
    
def ParseExportPhrase( phrase ):
    
    try:
        
        terms = [ ( 'string', phrase ) ]
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '[' in term:
                    
                    ( pre, term ) = term.split( '[', 1 )
                    
                    ( namespace, term ) = term.split( ']', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'namespace', namespace ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '{' in term:
                    
                    ( pre, term ) = term.split( '{', 1 )
                    
                    ( predicate, term ) = term.split( '}', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'predicate', predicate ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '(' in term:
                    
                    ( pre, term ) = term.split( '(', 1 )
                    
                    ( tag, term ) = term.split( ')', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'tag', tag ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
    except Exception as e:
        
        raise Exception( 'Could not parse that phrase: ' + str( e ) )
        
    
    return terms
    

class ExportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER
    SERIALISABLE_NAME = 'Export Folder'
    SERIALISABLE_VERSION = 4
    SERIALISABLE_VERSION = 5
    
    def __init__( self, name, path = '', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, delete_from_client_after_export = False, file_search_context = None, run_regularly = True, period = 3600, phrase = None, last_checked = 0, paused = False, run_now = False, last_error = '' ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        if export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            delete_from_client_after_export = False
            
        
        if file_search_context is None:
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            file_search_context = ClientSearch.FileSearchContext( location_context = default_location_context )
            
        
        if phrase is None:
            
            phrase = HG.client_controller.new_options.GetString( 'export_phrase' )
            
        
        self._path = path
        self._export_type = export_type
        self._delete_from_client_after_export = delete_from_client_after_export
        self._file_search_context = file_search_context
        self._run_regularly = run_regularly
        self._period = period
        self._phrase = phrase
        self._last_checked = last_checked
        self._paused = paused and not run_now
        self._run_now = run_now
        self._last_error = last_error
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context = self._file_search_context.GetSerialisableTuple()
        
        return ( self._path, self._export_type, self._delete_from_client_after_export, serialisable_file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._paused, self._run_now, self._last_error )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._export_type, self._delete_from_client_after_export, serialisable_file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._paused, self._run_now, self._last_error ) = serialisable_info
        
        if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            self._delete_from_client_after_export = False
            
        
        self._file_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( export_type, serialisable_file_search_context, period, phrase, last_checked ) = old_serialisable_info
            
            path = self._name
            
            new_serialisable_info = ( path, export_type, serialisable_file_search_context, period, phrase, last_checked )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( path, export_type, serialisable_file_search_context, period, phrase, last_checked ) = old_serialisable_info
            
            delete_from_client_after_export = False
            
            new_serialisable_info = ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, period, phrase, last_checked )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, period, phrase, last_checked ) = old_serialisable_info
            
            run_regularly = True
            paused = False
            run_now = False
            
            new_serialisable_info = ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, run_regularly, period, phrase, last_checked, paused, run_now )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, run_regularly, period, phrase, last_checked, paused, run_now ) = old_serialisable_info
            
            last_error = ''
            
            new_serialisable_info = ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, run_regularly, period, phrase, last_checked, paused, run_now, last_error )
            
            return ( 5, new_serialisable_info )
            
        
    
    def _DoExport( self ):
        
        query_hash_ids = HG.client_controller.Read( 'file_query_ids', self._file_search_context )
        
        media_results = []
        
        i = 0
        
        base = 256
        
        while i < len( query_hash_ids ):
            
            if HC.options[ 'pause_export_folders_sync' ] or HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            if i == 0: ( last_i, i ) = ( 0, base )
            else: ( last_i, i ) = ( i, i + base )
            
            sub_query_hash_ids = query_hash_ids[ last_i : i ]
            
            more_media_results = HG.client_controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
        
        media_results.sort( key = lambda mr: mr.GetHashId() )
        
        #
        
        terms = ParseExportPhrase( self._phrase )
        
        previous_paths = set()
        
        for ( root, dirnames, filenames ) in os.walk( self._path ):
            
            previous_paths.update( ( os.path.join( root, filename ) for filename in filenames ) )
            
        
        sync_paths = set()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        num_copied = 0
        
        for media_result in media_results:
            
            if HC.options[ 'pause_export_folders_sync' ] or HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            size = media_result.GetSize()
            
            try:
                
                source_path = client_files_manager.GetFilePath( hash, mime )
                
            except HydrusExceptions.FileMissingException:
                
                raise Exception( 'A file to be exported, hash "{}", was missing! You should run file maintenance (under database->maintenance->files) to check the files for the export folder\'s search, and possibly all your files.' )
                
            
            filename = GenerateExportFilename( self._path, media_result, terms )
            
            dest_path = os.path.normpath( os.path.join( self._path, filename ) )
            
            if not dest_path.startswith( self._path ):
                
                raise Exception( 'It seems a destination path for export folder "{}" was above the main export directory! The file was "{}" and its destination path was "{}".'.format( self._path, hash.hex(), dest_path ) )
                
            
            dest_path_dir = os.path.dirname( dest_path )
            
            HydrusPaths.MakeSureDirectoryExists( dest_path_dir )
            
            if dest_path not in sync_paths:
                
                copied = HydrusPaths.MirrorFile( source_path, dest_path )
                
                if copied:
                    
                    num_copied += 1
                    
                    HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
                    
                
            
            sync_paths.add( dest_path )
            
        
        if num_copied > 0:
            
            HydrusData.Print( 'Export folder ' + self._name + ' exported ' + HydrusData.ToHumanInt( num_copied ) + ' files.' )
            
        
        if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            deletee_paths = previous_paths.difference( sync_paths )
            
            for deletee_path in deletee_paths:
                
                ClientPaths.DeletePath( deletee_path )
                
            
            deletee_dirs = set()
            
            for ( root, dirnames, filenames ) in os.walk( self._path, topdown = False ):
                
                if root == self._path:
                    
                    continue
                    
                
                no_files = len( filenames ) == 0
                
                useful_dirnames = [ dirname for dirname in dirnames if os.path.join( root, dirname ) not in deletee_dirs ]
                
                no_useful_dirs = len( useful_dirnames ) == 0
                
                if no_useful_dirs and no_files:
                    
                    deletee_dirs.add( root )
                    
                
            
            for deletee_dir in deletee_dirs:
                
                if os.path.exists( deletee_dir ):
                    
                    HydrusPaths.DeletePath( deletee_dir )
                    
                
            
            if len( deletee_paths ) > 0:
                
                HydrusData.Print( 'Export folder {} deleted {} files and {} folders.'.format( self._name, HydrusData.ToHumanInt( len( deletee_paths ) ), HydrusData.ToHumanInt( len( deletee_dirs ) ) ) )
                
            
        
        if self._delete_from_client_after_export:
            
            local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
            
            service_keys_to_deletee_hashes = collections.defaultdict( list )
            
            delete_lock_for_archived_files = HG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' )
            
            for media_result in media_results:
                
                if delete_lock_for_archived_files and not media_result.GetInbox():
                    
                    continue
                    
                
                hash = media_result.GetHash()
                
                deletee_service_keys = media_result.GetLocationsManager().GetCurrent().intersection( local_file_service_keys )
                
                for deletee_service_key in deletee_service_keys:
                    
                    service_keys_to_deletee_hashes[ deletee_service_key ].append( hash )
                    
                
            
            reason = 'Deleted after export to Export Folder "{}".'.format( self._path )
            
            for ( service_key, deletee_hashes ) in service_keys_to_deletee_hashes.items():
                
                chunks_of_hashes = HydrusData.SplitListIntoChunks( deletee_hashes, 64 )
                
                for chunk_of_hashes in chunks_of_hashes:
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason )
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', { service_key : [ content_update ] } )
                    
                
            
        
    
    def DoWork( self ):
        
        regular_run_due = self._run_regularly and HydrusData.TimeHasPassed( self._last_checked + self._period )
        
        good_to_go = ( regular_run_due or self._run_now ) and not self._paused
        
        if not good_to_go:
            
            return
            
        
        try:
            
            if self._path == '':
                
                raise Exception( 'No path set for the folder!' )
                
            
            if not os.path.exists( self._path ):
                
                raise Exception( 'The path, "{}", does not exist!'.format( self._path ) )
                
            
            if not os.path.isdir( self._path ):
                
                raise Exception( 'The path, "{}", is not a directory!'.format( self._path ) )
                
            
            self._DoExport()
            
            self._last_error = ''
            
        except Exception as e:
            
            self._paused = True
            
            HydrusData.ShowText( 'The export folder "' + self._name + '" encountered an error! It has now been paused. Please check the folder\'s settings and maybe report to hydrus dev if the error is complicated! The error follows:' )
            
            HydrusData.ShowException( e )
            
            self._last_error = str( e )
            
        finally:
            
            self._last_checked = HydrusData.GetNow()
            self._run_now = False
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
    
    def GetLastError( self ) -> str:
        
        return self._last_error
        
    
    def RunNow( self ):
        
        self._paused = False
        self._run_now = True
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._export_type, self._delete_from_client_after_export, self._file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._paused, self._run_now )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ] = ExportFolder

class SidecarExporter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SIDECAR_EXPORTER
    SERIALISABLE_NAME = 'Sidecar Exporter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, service_keys_to_tag_data = None ):
        
        if service_keys_to_tag_data is None:
            
            service_keys_to_tag_data = {}
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._service_keys_to_tag_data = service_keys_to_tag_data
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_service_keys_and_tag_data = [ ( service_key.hex(), tag_filter.GetSerialisableTuple(), tag_display_type ) for ( service_key, ( tag_filter, tag_display_type ) ) in self._service_keys_to_tag_data.items() ]
        
        return serialisable_service_keys_and_tag_data
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_service_keys_and_tag_data = serialisable_info
        
        self._service_keys_to_tag_data = { bytes.fromhex( service_key_hex ) : ( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter ), tag_display_type ) for ( service_key_hex, serialisable_tag_filter, tag_display_type ) in serialisable_service_keys_and_tag_data }
        
    
    def ExportSidecar( self, directory: str, filename: str, tags_manager: ClientMediaManagers.TagsManager ):
        
        my_service_keys = set( self._service_keys_to_tag_data.keys() )
        
        for service_key in my_service_keys:
            
            if not HG.client_controller.services_manager.ServiceExists( service_key ):
                
                del self._service_keys_to_tag_data[ service_key ]
                
            
        
        all_tags = set()
        
        for ( service_key, ( tag_filter, tag_display_type ) ) in self._service_keys_to_tag_data.items():
            
            tags = tags_manager.GetCurrent( service_key, tag_display_type )
            
            tags = tag_filter.Filter( tags )
            
            all_tags.update( tags )
            
        
        if len( all_tags ) > 0:
            
            all_tags = list( all_tags )
            
            tag_sort = ClientTagSorting.TagSort.STATICGetTextASCDefault()
            
            ClientTagSorting.SortTags( tag_sort, all_tags )
            
            txt_path = os.path.join( directory, filename + '.txt' )
            
            with open( txt_path, 'w', encoding = 'utf-8' ) as f:
                
                f.write( os.linesep.join( tags ) )
                
            
        
    
    def GetTagData( self ):
        
        return dict( self._service_keys_to_tag_data )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SIDECAR_EXPORTER ] = SidecarExporter
