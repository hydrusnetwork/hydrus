def GetSidecarPath( actual_file_path: str, suffix: str, file_extension: str ):
    
    path_components = [ actual_file_path ]
    
    if suffix != '':
        
        path_components.append( suffix )
        
    
    path_components.append( file_extension )
    
    return '.'.join( path_components )
    

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
    
    def __init__( self, suffix: str ):
        
        self._suffix = suffix
        
    
    def GetSuffix( self ) -> str:
        
        return self._suffix
        
    
    def SetSuffix( self, suffix: str ):
        
        self._suffix = suffix
        
    
