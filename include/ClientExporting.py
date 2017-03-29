import ClientConstants as CC
import ClientData
import ClientSearch
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusPaths
import HydrusSerialisable
import HydrusTags
import os
import re
import stat

def GenerateExportFilename( media, terms ):
    
    mime = media.GetMime()
    
    filename = ''
    
    for ( term_type, term ) in terms:
        
        tags_manager = media.GetTagsManager()
        
        if term_type == 'string':
            
            filename += term
            
        elif term_type == 'namespace':
            
            tags = tags_manager.GetNamespaceSlice( ( term, ) )
            
            subtags = [ HydrusTags.SplitTag( tag )[1] for tag in tags ]
            
            subtags.sort()
            
            filename += ', '.join( subtags )
            
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
                
                filename += ', '.join( tags )
                
            elif term == 'hash':
                
                hash = media.GetHash()
                
                filename += hash.encode( 'hex' )
                
            
        elif term_type == 'tag':
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if tags_manager.HasTag( subtag ):
                
                filename += subtag
                
            
        
    
    if HC.PLATFORM_WINDOWS:
        
        filename = re.sub( '\\\\|/|:|\\*|\\?|"|<|>|\\|', '_', filename, flags = re.UNICODE )
        
    else:
        
        filename = re.sub( '/', '_', filename, flags = re.UNICODE )
        
    
    ext = HC.mime_ext_lookup[ mime ]
    
    if not filename.endswith( ext ):
        
        filename += ext
        
    
    return filename
    
def GetExportPath():
    
    options = HydrusGlobals.client_controller.GetOptions()
    
    portable_path = options[ 'export_path' ]
    
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
        
    except: raise Exception( 'Could not parse that phrase!' )
    
    return terms
    

class ExportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name, path = '', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, file_search_context = None, period = 3600, phrase = None ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        if file_search_context is None:
            
            file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
            
        
        if phrase is None:
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            phrase = new_options.GetString( 'export_phrase' )
            
        
        self._path = path
        self._export_type = export_type
        self._file_search_context = file_search_context
        self._period = period
        self._phrase = phrase
        self._last_checked = 0
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_search_context = self._file_search_context.GetSerialisableTuple()
        
        return ( self._path, self._export_type, serialisable_file_search_context, self._period, self._phrase, self._last_checked )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._export_type, serialisable_file_search_context, self._period, self._phrase, self._last_checked ) = serialisable_info
        
        self._file_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( export_type, serialisable_file_search_context, period, phrase, last_checked ) = old_serialisable_info
            
            path = self._name
            
            new_serialisable_info = ( path, export_type, serialisable_file_search_context, period, phrase, last_checked )
            
            return ( 2, new_serialisable_info )
            
        
    
    def DoWork( self ):
        
        if HydrusData.TimeHasPassed( self._last_checked + self._period ):
            
            folder_path = HydrusData.ToUnicode( self._path )
            
            if folder_path != '' and os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                
                query_hash_ids = HydrusGlobals.client_controller.Read( 'file_query_ids', self._file_search_context )
                
                media_results = []
                
                i = 0
                
                base = 256
                
                while i < len( query_hash_ids ):
                    
                    if HC.options[ 'pause_export_folders_sync' ]:
                        
                        return
                        
                    
                    if i == 0: ( last_i, i ) = ( 0, base )
                    else: ( last_i, i ) = ( i, i + base )
                    
                    sub_query_hash_ids = query_hash_ids[ last_i : i ]
                    
                    more_media_results = HydrusGlobals.client_controller.Read( 'media_results_from_ids', sub_query_hash_ids )
                    
                    media_results.extend( more_media_results )
                    
                
                #
                
                terms = ParseExportPhrase( self._phrase )
                
                previous_filenames = set( os.listdir( folder_path ) )
                
                sync_filenames = set()
                
                client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                
                num_copied = 0
                
                for media_result in media_results:
                    
                    hash = media_result.GetHash()
                    mime = media_result.GetMime()
                    size = media_result.GetSize()
                    
                    source_path = client_files_manager.GetFilePath( hash, mime )
                    
                    filename = GenerateExportFilename( media_result, terms )
                    
                    dest_path = os.path.join( folder_path, filename )
                    
                    if filename not in sync_filenames:
                        
                        copied = HydrusPaths.MirrorFile( source_path, dest_path )
                        
                        if copied:
                            
                            num_copied += 1
                            
                            try: os.chmod( dest_path, stat.S_IWRITE | stat.S_IREAD )
                            except: pass
                            
                        
                    
                    sync_filenames.add( filename )
                    
                
                if num_copied > 0:
                    
                    HydrusData.Print( 'Export folder ' + self._name + ' exported ' + HydrusData.ConvertIntToPrettyString( num_copied ) + ' files.' )
                    
                
                if self._export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
                    
                    deletee_filenames = previous_filenames.difference( sync_filenames )
                    
                    for deletee_filename in deletee_filenames:
                        
                        deletee_path = os.path.join( folder_path, deletee_filename )
                        
                        ClientData.DeletePath( deletee_path )
                        
                    
                    if len( deletee_filenames ) > 0:
                        
                        HydrusData.Print( 'Export folder ' + self._name + ' deleted ' + HydrusData.ConvertIntToPrettyString( len( deletee_filenames ) ) + ' files.' )
                        
                    
                
            
            self._last_checked = HydrusData.GetNow()
            
            HydrusGlobals.client_controller.WriteSynchronous( 'serialisable', self )
            
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._export_type, self._file_search_context, self._period, self._phrase )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ] = ExportFolder
