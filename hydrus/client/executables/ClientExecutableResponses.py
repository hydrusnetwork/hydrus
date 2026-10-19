from hydrus.client.parsing import ClientParsingResults

class ExecutableCallResponse( object ):
    
    def __init__( self ):
        
        self.parsed_posts: list[ ClientParsingResults.ParsedPost ] = []
        self.temp_file_info = None # ( os_file_handle, temp_path )
        
    
