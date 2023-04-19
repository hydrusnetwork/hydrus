import os.path

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

from hydrus.client import ClientStrings

NOTE_CONNECTOR_STRING = ': '
NOTE_NAME_ESCAPE_STRING = ':\\ '

def GetSidecarPath( actual_file_path: str, remove_actual_filename_ext: bool, suffix: str, filename_string_converter: ClientStrings.StringConverter, file_extension: str ):
    
    path_components = []
    
    if remove_actual_filename_ext and '.' in actual_file_path:
    
        ( filename_without_ext, gumpf ) = actual_file_path.rsplit( '.', 1 )
        
        path_components.append( filename_without_ext )
        
    else:
        
        path_components.append( actual_file_path )
        
    
    if suffix != '':
        
        path_components.append( suffix )
        
    
    path_components.append( file_extension )
    
    path = '.'.join( path_components )
    
    if filename_string_converter.MakesChanges():
        
        try:
            
            ( d, f ) = os.path.split( path )
            
            f = filename_string_converter.Convert( f )
            
            path = os.path.join( d, f )
            
        except HydrusExceptions.StringConvertException:
            
            HydrusData.Print( 'Failed to convert the sidecar path "{}"!'.format( path ) )
            
        
    
    return path
    

class ImporterExporterNode( object ):
    
    def __str__( self ):
        
        return self.ToString()
        
    
    def GetExampleStrings( self ):
        
        examples = [
            'blue eyes',
            'blonde hair',
            'skirt',
            'character:jane smith',
            'series:jane smith adventures',
            'creator:some guy',
            'https://example.com/gallery/index.php?post=123456&page=show',
            'https://cdn3.expl.com/files/file_id?id=123456&token=0123456789abcdef'
        ]
        
        return examples
        
    
    def ToString( self ) -> str:
        
        raise NotImplementedError()
        
    

class SidecarNode( object ):
    
    def __init__( self, remove_actual_filename_ext: bool, suffix: str, filename_string_converter: ClientStrings.StringConverter ):
        
        self._remove_actual_filename_ext = remove_actual_filename_ext
        self._suffix = suffix
        self._filename_string_converter = filename_string_converter
        
    
    def GetFilenameStringConverter( self ) -> ClientStrings.StringConverter:
        
        return self._filename_string_converter
        
    
    def GetRemoveActualFilenameExt( self ) -> bool:
        
        return self._remove_actual_filename_ext
        
    
    def GetSuffix( self ) -> str:
        
        return self._suffix
        
    
    def SetFilenameStringConverter( self, filename_string_converter: ClientStrings.StringConverter ):
        
        self._filename_string_converter = filename_string_converter
        
    
    def SetRemoveActualFilenameExt( self, remove_actual_filename_ext: bool ):
        
        self._remove_actual_filename_ext = remove_actual_filename_ext
        
    
    def SetSuffix( self, suffix: str ):
        
        self._suffix = suffix
        
    
