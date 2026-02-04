import collections.abc
import os
import re
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchFileSearchContext

def GenerateExportFilename( destination_directory, media, terms, file_index, do_not_use_filenames = None ):
    
    def clean_tag_text( t ):
        
        if HC.PLATFORM_WINDOWS:
            
            t = re.sub( r'\\', '_', t )
            
        else:
            
            t = re.sub( '/', '_', t )
            
        
        return t
        
    
    filename = ''
    
    for ( term_type, term ) in terms:
        
        tags_manager = media.GetTagsManager()
        
        if term_type == 'string':
            
            filename += term
            
        elif term_type == 'namespace':
            
            tags = tags_manager.GetNamespaceSlice( CC.COMBINED_TAG_SERVICE_KEY, ( term, ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
            
            subtags = sorted( ( HydrusTags.SplitTag( tag )[1] for tag in tags ) )
            
            filename += clean_tag_text( ', '.join( subtags ) )
            
        elif term_type == 'predicate':
            
            if term in ( 'tags', 'nn tags' ):
                
                current = tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                pending = tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                
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
                
            elif term == '#':
                
                filename += str( file_index )
                
            
        elif term_type == 'tag':
            
            tag = term
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if tags_manager.HasTag( subtag, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ):
                
                filename += clean_tag_text( subtag )
                
            
        
    
    while filename.startswith( os.path.sep ):
        
        filename = filename[1:]
        
    
    # replace many consecutive (back)slash with single
    
    if HC.PLATFORM_WINDOWS:
        
        filename = re.sub( r'\\+', r'\\', filename )
        
    else:
        
        filename = re.sub( '/+', '/', filename )
        
    
    if CG.client_controller.new_options.GetBoolean( 'always_apply_ntfs_export_filename_rules' ):
        
        force_ntfs_rules = True
        
    else:
        
        fst = HydrusPaths.GetFileSystemType( destination_directory )
        
        if fst is None:
            
            force_ntfs_rules = False
            
        else:
            
            fst_lower = fst.lower()
            
            if fst_lower.startswith( 'fuse.' ):
                
                fst_lower = fst_lower[ 5 : ]
                
            
            force_ntfs_rules = fst_lower in ( 'ntfs', 'exfat', 'vfat', 'msdos', 'fat', 'fat32', 'cifs', 'smbfs', 'fuseblk' )
            
        
    
    #
    
    mime = media.GetMime()
    
    ext = HC.mime_ext_lookup[ mime ]
    
    if filename.endswith( ext ):
        
        filename = filename[ : - len( ext ) ]
        
    
    path_character_limit = CG.client_controller.new_options.GetNoneableInteger( 'export_path_character_limit' )
    dirname_character_limit = CG.client_controller.new_options.GetNoneableInteger( 'export_dirname_character_limit' )
    filename_character_limit = CG.client_controller.new_options.GetInteger( 'export_filename_character_limit' )
    
    ( subdirs, true_filename ) = os.path.split( filename )
    
    if true_filename == '':
        
        hash = media.GetHash()
        
        true_filename = hash.hex()
        
    
    ( subdirs_elided, filename_elided ) = HydrusPaths.ElideFilenameSafely( destination_directory, subdirs, true_filename, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules )
    
    if len( subdirs_elided ) > 0:
        
        filename_elided = os.path.join( subdirs_elided, filename_elided )
        
    
    if do_not_use_filenames is not None:
        
        i = 1
        
        possible_filename = '{}{}'.format( filename_elided, ext )
        
        while possible_filename in do_not_use_filenames:
            
            possible_filename = '{} ({}){}'.format( filename_elided, i, ext )
            
            i += 1
            
        
        filename_elided = possible_filename
        
    else:
        
        filename_elided += ext
        
    
    return filename_elided
    

def GetExportPath():
    
    portable_path = CG.client_controller.options[ 'export_path' ]
    
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
    SERIALISABLE_VERSION = 9
    
    def __init__(
        self,
        name,
        path = '',
        export_type = HC.EXPORT_FOLDER_TYPE_REGULAR,
        delete_from_client_after_export = False,
        export_symlinks = False,
        file_search_context = None,
        metadata_routers = None,
        run_regularly = True,
        period = 3600 * 24,
        phrase = None,
        last_checked = 0,
        run_now = False,
        last_error = '',
        show_working_popup = True
    ):
        
        super().__init__( name )
        
        if export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            delete_from_client_after_export = False
            
        
        if file_search_context is None:
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context )
            
        
        if metadata_routers is None:
            
            metadata_routers = []
            
        
        if phrase is None:
            
            phrase = CG.client_controller.new_options.GetString( 'export_phrase' )
            
        
        self._path = path
        self._export_type = export_type
        self._delete_from_client_after_export = delete_from_client_after_export
        self._export_symlinks = export_symlinks
        self._file_search_context = file_search_context
        self._metadata_routers = HydrusSerialisable.SerialisableList( metadata_routers )
        self._run_regularly = run_regularly
        self._period = period
        self._phrase = phrase
        self._last_checked = last_checked
        self._run_now = run_now
        self._last_error = last_error
        self._show_working_popup = show_working_popup
        self._overwrite_sidecars_on_next_run = False
        self._always_overwrite_sidecars = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context = self._file_search_context.GetSerialisableTuple()
        serialisable_metadata_routers = self._metadata_routers.GetSerialisableTuple()
        
        return (
            self._path,
            self._export_type,
            self._delete_from_client_after_export,
            self._export_symlinks,
            serialisable_file_search_context,
            serialisable_metadata_routers,
            self._run_regularly,
            self._period,
            self._phrase,
            self._last_checked,
            self._run_now,
            self._last_error,
            self._show_working_popup,
            self._overwrite_sidecars_on_next_run,
            self._always_overwrite_sidecars
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._path,
            self._export_type,
            self._delete_from_client_after_export,
            self._export_symlinks,
            serialisable_file_search_context,
            serialisable_metadata_routers,
            self._run_regularly,
            self._period,
            self._phrase,
            self._last_checked,
            self._run_now,
            self._last_error,
            self._show_working_popup,
            self._overwrite_sidecars_on_next_run,
            self._always_overwrite_sidecars
        ) = serialisable_info
        
        if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            self._delete_from_client_after_export = False
            
        
        self._file_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context )
        self._metadata_routers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_metadata_routers )
        
    
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
            
        
        if version == 5:
            
            ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, run_regularly, period, phrase, last_checked, paused, run_now, last_error ) = old_serialisable_info
            
            metadata_routers = HydrusSerialisable.SerialisableList()
            
            serialisable_metadata_routers = metadata_routers.GetSerialisableTuple()
            
            new_serialisable_info = ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, serialisable_metadata_routers, run_regularly, period, phrase, last_checked, paused, run_now, last_error )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( path, export_type, delete_from_client_after_export, serialisable_file_search_context, serialisable_metadata_routers, run_regularly, period, phrase, last_checked, paused, run_now, last_error ) = old_serialisable_info
            
            export_symlinks = False
            
            new_serialisable_info = ( path, export_type, delete_from_client_after_export, export_symlinks, serialisable_file_search_context, serialisable_metadata_routers, run_regularly, period, phrase, last_checked, paused, run_now, last_error )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            (
                path,
                export_type,
                delete_from_client_after_export,
                export_symlinks,
                serialisable_file_search_context,
                serialisable_metadata_routers,
                run_regularly,
                period,
                phrase,
                last_checked,
                paused,
                run_now,
                last_error
            ) = old_serialisable_info
            
            show_working_popup = True
            
            if paused:
                
                run_regularly = False
                
            
            new_serialisable_info = (
                path,
                export_type,
                delete_from_client_after_export,
                export_symlinks,
                serialisable_file_search_context,
                serialisable_metadata_routers,
                run_regularly,
                period,
                phrase,
                last_checked,
                run_now,
                last_error,
                show_working_popup
            )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            (
                path,
                export_type,
                delete_from_client_after_export,
                export_symlinks,
                serialisable_file_search_context,
                serialisable_metadata_routers,
                run_regularly,
                period,
                phrase,
                last_checked,
                run_now,
                last_error,
                show_working_popup
            ) = old_serialisable_info
            
            overwrite_sidecars_on_next_run = False
            always_overwrite_sidecars = False
            
            new_serialisable_info = (
                path,
                export_type,
                delete_from_client_after_export,
                export_symlinks,
                serialisable_file_search_context,
                serialisable_metadata_routers,
                run_regularly,
                period,
                phrase,
                last_checked,
                run_now,
                last_error,
                show_working_popup,
                overwrite_sidecars_on_next_run,
                always_overwrite_sidecars
            )
            
            return ( 9, new_serialisable_info )
            
        
    
    def _DoExport( self, job_status: ClientThreading.JobStatus ):
        
        query_hash_ids = CG.client_controller.Read( 'file_query_ids', self._file_search_context, apply_implicit_limit = False )
        
        media_results = []
        
        CHUNK_SIZE = 64
        
        for ( num_done, num_to_do, block_of_hash_ids ) in HydrusLists.SplitListIntoChunksRich( query_hash_ids, CHUNK_SIZE ):
            
            job_status.SetStatusText( 'searching: {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) ) )
            
            if job_status.IsCancelled():
                
                return
                
            
            if CG.client_controller.new_options.GetBoolean( 'pause_export_folders_sync' ) or HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            more_media_results = CG.client_controller.Read( 'media_results_from_ids', block_of_hash_ids )
            
            media_results.extend( more_media_results )
            
        
        media_results.sort( key = lambda mr: mr.GetHashId() )
        
        #
        
        terms = ParseExportPhrase( self._phrase )
        
        previous_paths = set()
        
        for ( root, dirnames, filenames ) in os.walk( self._path ):
            
            previous_paths.update( ( os.path.join( root, filename ) for filename in filenames ) )
            
        
        sync_paths = set()
        
        sidecar_paths_that_did_not_exist_before_this_run = set()
        sidecar_paths_that_did_exist_before_this_run = set()
        
        client_files_manager = CG.client_controller.client_files_manager
        
        num_actually_copied = 0
        
        dirs_we_checked_exist = set()
        
        for ( i, media_result ) in enumerate( media_results ):
            
            job_status.SetStatusText( 'exporting: {}'.format( HydrusNumbers.ValueRangeToPrettyString( i + 1, len( media_results ) ) ) )
            
            if job_status.IsCancelled():
                
                return
                
            
            if CG.client_controller.new_options.GetBoolean( 'pause_export_folders_sync' ) or HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            try:
                
                filename = GenerateExportFilename( self._path, media_result, terms, i + 1 )
                
            except Exception as e:
                
                fallback_filename_terms = ParseExportPhrase( '{hash}' )
                
                filename = GenerateExportFilename( self._path, media_result, fallback_filename_terms, i + 1 )
                
            
            dest_path = os.path.normpath( os.path.join( self._path, filename ) )
            
            if not dest_path.startswith( self._path ):
                
                raise Exception( 'It seems a destination path for export folder "{}" was above the main export directory! The file was "{}" and its destination path was "{}".'.format( self._path, hash.hex(), dest_path ) )
                
            
            dest_path_dir = os.path.dirname( dest_path )
            
            if dest_path_dir not in dirs_we_checked_exist:
                
                HydrusPaths.MakeSureDirectoryExists( dest_path_dir )
                
                dirs_we_checked_exist.add( dest_path_dir )
                
            
            if dest_path not in sync_paths:
                
                try:
                    
                    # IMPORTANT: this call is actually pretty expensive when you are doing like 10k of them regularly
                    # Unfortunately we need to do a disk hit to check size/modified time, but let's save what time we can
                    # TODO: perhaps we can have an option regarding how often we do this. maybe we only do the full time/size check versus existence check every week etc.., or indeed never
                    
                    source_path = client_files_manager.GetFilePath( hash, mime )
                    
                except HydrusExceptions.FileMissingException:
                    
                    raise Exception( f'A file to be exported, hash "{hash.hex()}", was missing! You should run "missing file" file maintenance (under database->file maintenance->manage scheduled jobs) to check if any other files in your export folder\'s search--or your whole database--are also missing.' )
                    
                
                if self._export_symlinks:
                    
                    if not os.path.exists( dest_path ):
                        
                        try:
                            
                            os.symlink( source_path, dest_path )
                            
                        except OSError as e:
                            
                            if HC.PLATFORM_WINDOWS:
                                
                                raise Exception( 'The symlink creation failed. It may be you need to run hydrus as Admin for this to work!' ) from e
                                
                            else:
                                
                                raise
                                
                            
                        
                        actually_copied = True
                        
                        num_actually_copied += 1
                        
                    else:
                        
                        actually_copied = False
                        
                    
                else:
                    
                    actually_copied = HydrusPaths.MirrorFile( source_path, dest_path )
                    
                    if actually_copied:
                        
                        HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
                        
                    
                
                if actually_copied:
                    
                    num_actually_copied += 1
                    
                
            
            sync_paths.add( dest_path )
            
            for metadata_router in self._metadata_routers:
                
                metadata_router = typing.cast( ClientMetadataMigration.SingleFileMetadataRouter, metadata_router )
                
                metadata_exporter = metadata_router.GetExporter()
                
                if isinstance( metadata_exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar ):
                    
                    # we have to be careful with path.exists regarding multiple routers going to one sidecar
                    
                    sidecar_path = metadata_exporter.GetExportPath( dest_path )
                    
                    if os.path.exists( sidecar_path ):
                        
                        if sidecar_path not in sidecar_paths_that_did_not_exist_before_this_run:
                            
                            if sidecar_path not in sidecar_paths_that_did_exist_before_this_run:
                                
                                sidecar_paths_that_did_exist_before_this_run.add( sidecar_path )
                                
                                if self._overwrite_sidecars_on_next_run or self._always_overwrite_sidecars:
                                    
                                    # ok this is the first time we have seen this guy. let's do a full delete so we can recreate from scratch
                                    # it is tempting to try for an 'update' instead of overwrite, but let's KISS
                                    # note non-recycling delete
                                    HydrusPaths.DeletePath( sidecar_path )
                                    
                                
                            
                        
                    else:
                        
                        sidecar_paths_that_did_not_exist_before_this_run.add( sidecar_path )
                        
                    
                    if sidecar_path in sidecar_paths_that_did_not_exist_before_this_run or self._overwrite_sidecars_on_next_run or self._always_overwrite_sidecars:
                        
                        metadata_router.Work( media_result, dest_path )
                        
                    
                    sync_paths.add( sidecar_path )
                    
                
            
        
        if num_actually_copied > 0:
            
            HydrusData.Print( 'Export folder ' + self._name + ' exported ' + HydrusNumbers.ToHumanInt( num_actually_copied ) + ' files.' )
            
        
        if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            deletee_paths = previous_paths.difference( sync_paths )
            
            for ( i, deletee_path ) in enumerate( deletee_paths ):
                
                if job_status.IsCancelled():
                    
                    return
                    
                
                job_status.SetStatusText( 'delete-synchronising: {}'.format( HydrusNumbers.ValueRangeToPrettyString( i + 1, len( deletee_paths ) ) ) )
                
                ClientPaths.DeletePath( deletee_path )
                
            
            deletee_dirs = set()
            
            for ( root, dirnames, filenames ) in os.walk( self._path, topdown = False ):
                
                if job_status.IsCancelled():
                    
                    return
                    
                
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
                
                HydrusData.Print( 'Export folder {} deleted {} files and {} folders.'.format( self._name, HydrusNumbers.ToHumanInt( len( deletee_paths ) ), HydrusNumbers.ToHumanInt( len( deletee_dirs ) ) ) )
                
            
        
        if not self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE and self._delete_from_client_after_export:
            
            my_files_media_results = [ media_result for media_result in media_results if CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY in media_result.GetLocationsManager().GetCurrent() ]
            
            reason = 'Deleted after export to Export Folder "{}".'.format( self._path )
            
            CHUNK_SIZE = 64
            
            for ( num_done, num_to_do, chunk_of_media_results ) in HydrusLists.SplitListIntoChunksRich( my_files_media_results, CHUNK_SIZE ):
                
                if job_status.IsCancelled():
                    
                    return
                    
                
                job_status.SetStatusText( 'deleting: {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) ) )
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { media_result.GetHash() for media_result in chunk_of_media_results }, reason = reason )
                
                CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, content_update ) )
                
            
        
        job_status.SetStatusText( 'Done!' )
        
    
    def DoWork( self ):
        
        regular_run_due = self._run_regularly and HydrusTime.TimeHasPassed( self._last_checked + self._period )
        
        good_to_go = regular_run_due or self._run_now
        
        if not good_to_go:
            
            return
            
        
        job_status = ClientThreading.JobStatus( pausable = False, cancellable = True )
        
        job_status.SetStatusTitle( 'export folder - ' + self._name )
        
        try:
            
            if self._path == '':
                
                raise Exception( 'No path set for the folder!' )
                
            
            if not os.path.exists( self._path ):
                
                raise Exception( 'The path, "{}", does not exist!'.format( self._path ) )
                
            
            if not os.path.isdir( self._path ):
                
                raise Exception( 'The path, "{}", is not a directory!'.format( self._path ) )
                
            
            popup_desired = self._show_working_popup or self._run_now
            
            if popup_desired:
                
                CG.client_controller.pub( 'message', job_status )
                
            
            self._DoExport( job_status )
            
            self._last_error = ''
            
        except Exception as e:
            
            if self._run_regularly:
                
                self._run_regularly = False
                
                pause_str = 'It has been set to not run regularly.'
                
            else:
                
                pause_str = ''
                
            
            message = f'The export folder "{self._name}" encountered an error! {pause_str}Please check the folder\'s settings and maybe report to hydrus dev if the error is complicated! The error follows:'
            
            HydrusData.ShowText( message )
            
            HydrusData.ShowException( e )
            
            self._last_error = str( e )
            
        finally:
            
            self._last_checked = HydrusTime.GetNow()
            self._overwrite_sidecars_on_next_run = False
            self._run_now = False
            
            CG.client_controller.WriteSynchronous( 'serialisable', self )
            
            job_status.FinishAndDismiss()
            
        
    
    def GetAlwaysOverwriteSidecars( self ):
        
        return self._always_overwrite_sidecars
        
    
    def GetLastError( self ) -> str:
        
        return self._last_error
        
    
    def GetMetadataRouters( self ) -> collections.abc.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ]:
        
        return self._metadata_routers
        
    
    def GetOverwriteSidecarsOnNextRun( self ):
        
        return self._overwrite_sidecars_on_next_run
        
    
    def RunNow( self ):
        
        self._run_now = True
        
    
    def SetAlwaysOverwriteSidecars( self, always_overwrite_sidecars: bool ):
        
        self._always_overwrite_sidecars = always_overwrite_sidecars
        
    
    def SetOverwriteSidecarsOnNextRun( self, overwrite_sidecars_on_next_run: bool ):
        
        self._overwrite_sidecars_on_next_run = overwrite_sidecars_on_next_run
        
    
    def ShowWorkingPopup( self ) -> bool:
        
        return self._show_working_popup
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._export_type, self._delete_from_client_after_export, self._export_symlinks, self._file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._run_now )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ] = ExportFolder
