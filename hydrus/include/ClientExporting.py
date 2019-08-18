from . import ClientConstants as CC
from . import ClientPaths
from . import ClientSearch
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusThreading
import os
import re
import stat

MAX_PATH_LENGTH = 245 # bit of padding from 255 for .txt neigbouring and other surprises

def GenerateExportFilename( destination_directory, media, terms ):
    
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
            
            tags = tags_manager.GetNamespaceSlice( ( term, ) )
            
            subtags = [ HydrusTags.SplitTag( tag )[1] for tag in tags ]
            
            subtags.sort()
            
            filename += clean_tag_text( ', '.join( subtags ) )
            
        elif term_type == 'predicate':
            
            if term in ( 'tags', 'nn tags' ):
                
                current = tags_manager.GetCurrent()
                pending = tags_manager.GetPending()
                
                tags = list( current.union( pending ) )
                
                if term == 'nn tags':
                    
                    tags = [ tag for tag in tags if ':' not in tag ]
                    
                else:
                    
                    tags = [ HydrusTags.SplitTag( tag )[1] for tag in tags ]
                    
                
                tags.sort()
                
                filename += clean_tag_text( ', '.join( tags ) )
                
            elif term == 'hash':
                
                hash = media.GetHash()
                
                filename += hash.hex()
                
            
        elif term_type == 'tag':
            
            tag = term
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if tags_manager.HasTag( subtag ):
                
                filename += clean_tag_text( subtag )
                
            
        
    
    if HC.PLATFORM_WINDOWS:
        
        # replace many consecutive backspace with single backspace
        filename = re.sub( r'\\+', r'\\', filename )
        
        # /, :, *, ?, ", <, >, |
        filename = re.sub( r'/|:|\*|\?|"|<|>|\|', '_', filename )
        
    else:
        
        filename = re.sub( '/', '_', filename )
        
    
    #
    
    mime = media.GetMime()
    
    ext = HC.mime_ext_lookup[ mime ]
    
    if filename.endswith( ext ):
        
        filename = filename[ : - len( ext ) ]
        
    
    example_dest_path = os.path.join( destination_directory, filename + ext )
    
    excess_chars = len( example_dest_path ) - MAX_PATH_LENGTH
    
    if excess_chars > 0:
        
        filename = filename[ : - excess_chars ]
        
    
    filename = filename + ext
    
    return filename
    
def GetExportPath():
    
    portable_path = HG.client_controller.options[ 'export_path' ]
    
    if portable_path is None:
        
        path = os.path.join( os.path.expanduser( '~' ), 'hydrus_export' )
        
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
    
    def __init__( self, name, path = '', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, delete_from_client_after_export = False, file_search_context = None, run_regularly = True, period = 3600, phrase = None, last_checked = 0, paused = False, run_now = False ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        if export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            delete_from_client_after_export = False
            
        
        if file_search_context is None:
            
            file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
            
        
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
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context = self._file_search_context.GetSerialisableTuple()
        
        return ( self._path, self._export_type, self._delete_from_client_after_export, serialisable_file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._paused, self._run_now )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._export_type, self._delete_from_client_after_export, serialisable_file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._paused, self._run_now ) = serialisable_info
        
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
            
            source_path = client_files_manager.GetFilePath( hash, mime )
            
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
                    
                    HydrusPaths.MakeFileWritable( dest_path )
                    
                
            
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
            
            deletee_hashes = { media_result.GetHash() for media_result in media_results }
            
            chunks_of_hashes = HydrusData.SplitListIntoChunks( deletee_hashes, 64 )
            
            reason = 'Deleted after export to Export Folder "{}".'.format( self._path )
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason ) for chunk_of_hashes in chunks_of_hashes ]
            
            for content_update in content_updates:
                
                HG.client_controller.WriteSynchronous( 'content_updates', { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
                
            
        
    
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
            
        except Exception as e:
            
            self._paused = True
            
            HydrusData.ShowText( 'The export folder "' + self._name + '" encountered an error! The error will follow! It has now been paused. Please check the folder\'s settings and maybe report to hydrus dev if the error is complicated!' )
            
            HydrusData.ShowException( e )
            
        finally:
            
            self._last_checked = HydrusData.GetNow()
            self._run_now = False
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
    
    def RunNow( self ):
        
        self._paused = False
        self._run_now = True
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._export_type, self._delete_from_client_after_export, self._file_search_context, self._run_regularly, self._period, self._phrase, self._last_checked, self._paused, self._run_now )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ] = ExportFolder
