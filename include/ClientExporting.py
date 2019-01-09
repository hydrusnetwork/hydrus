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
    SERIALISABLE_VERSION = 3
    
    def __init__( self, name, path = '', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, delete_from_client_after_export = False, file_search_context = None, period = 3600, phrase = None ):
        
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
        self._period = period
        self._phrase = phrase
        self._last_checked = 0
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context = self._file_search_context.GetSerialisableTuple()
        
        return ( self._path, self._export_type, self._delete_from_client_after_export, serialisable_file_search_context, self._period, self._phrase, self._last_checked )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._export_type, self._delete_from_client_after_export, serialisable_file_search_context, self._period, self._phrase, self._last_checked ) = serialisable_info
        
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
            
        
    
    def DoWork( self ):
        
        try:
            
            if HydrusData.TimeHasPassed( self._last_checked + self._period ):
                
                if self._path != '' and os.path.exists( self._path ) and os.path.isdir( self._path ):
                    
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
                        
                    
                    #
                    
                    terms = ParseExportPhrase( self._phrase )
                    
                    previous_filenames = set( os.listdir( self._path ) )
                    
                    sync_filenames = set()
                    
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
                        
                        dest_path = os.path.join( self._path, filename )
                        
                        dest_path_dir = os.path.dirname( dest_path )
                        
                        HydrusPaths.MakeSureDirectoryExists( dest_path_dir )
                        
                        if filename not in sync_filenames:
                            
                            copied = HydrusPaths.MirrorFile( source_path, dest_path )
                            
                            if copied:
                                
                                num_copied += 1
                                
                                try: os.chmod( dest_path, stat.S_IWRITE | stat.S_IREAD )
                                except: pass
                                
                            
                        
                        sync_filenames.add( filename )
                        
                    
                    if num_copied > 0:
                        
                        HydrusData.Print( 'Export folder ' + self._name + ' exported ' + HydrusData.ToHumanInt( num_copied ) + ' files.' )
                        
                    
                    if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
                        
                        deletee_filenames = previous_filenames.difference( sync_filenames )
                        
                        for deletee_filename in deletee_filenames:
                            
                            deletee_path = os.path.join( self._path, deletee_filename )
                            
                            ClientPaths.DeletePath( deletee_path )
                            
                        
                        if len( deletee_filenames ) > 0:
                            
                            HydrusData.Print( 'Export folder ' + self._name + ' deleted ' + HydrusData.ToHumanInt( len( deletee_filenames ) ) + ' files.' )
                            
                        
                    
                    if self._delete_from_client_after_export:
                        
                        deletee_hashes = { media_result.GetHash() for media_result in media_results }
                        
                        chunks_of_hashes = HydrusData.SplitListIntoChunks( deletee_hashes, 64 )
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
                        
                        for content_update in content_updates:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
                            
                        
                    
                
            
        except Exception as e:
            
            HG.client_controller.options[ 'pause_export_folders_sync' ] = True
            
            HydrusData.ShowText( 'The export folder "' + self._name + '" encountered an error! The error will follow! All export folders have now been paused. Please check the folder\'s settings and maybe report to hydrus dev if the error is complicated!' )
            
            HydrusData.ShowException( e )
            
        
        self._last_checked = HydrusData.GetNow()
        
        HG.client_controller.WriteSynchronous( 'serialisable', self )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._export_type, self._delete_from_client_after_export, self._file_search_context, self._period, self._phrase )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ] = ExportFolder
