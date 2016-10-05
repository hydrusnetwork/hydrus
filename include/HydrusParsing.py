import bs4
import HydrusConstants as HC
import HydrusData
import HydrusSerialisable

def ConvertParsableContentToPrettyString( parsable_content ):
    
    if len( parsable_content ) == 0:
        
        return 'nothing'
        
    else:
        
        # make this prettier
        
        return ', '.join( parsable_content )
        
    
def RenderTagRule( ( name, attrs, index ) ):
    
    if index is None:
        
        result = 'all ' + name + ' tags'
        
    else:
        
        result = HydrusData.ConvertIntToFirst( index + 1 ) + name + ' tag'
        
    
    if len( attrs ) > 0:
        
        result += ' with ' + ' and '.join( [ key + ' = ' + value for ( key, value ) in attrs.items() ] )
        
    
    return result
    
class ParseFormulaHTML( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_FORMULA_HTML
    SERIALISABLE_VERSION = 1
    
    def __init__( self, tag_rules = None, content_rule = None ):
        
        if tag_rules is None:
            
            tag_rules = [ ( 'a', {}, None ) ]
            
        
        if content_rule is None:
            
            content_rule = 'src'
            
        
        self._tag_rules = tag_rules
        
        self._content_rule = content_rule
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._tag_rules, self._content_rule )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._tag_rules, self._content_rule ) = serialisable_info
        
    
    def _ParseContent( self, root ):
        
        if self._content_rule is None:
            
            return root.string
            
        else:
            
            return root[ self._content_rule ]
            
        
    
    def _ParseTags( self, root, name, attrs, index ):
        
        results = root.find_all( name = name, attrs = attrs )
        
        if index is not None:
            
            try:
                
                results = ( results[index], )
                
            except IndexError:
                
                text = 'Trying to parse ' + name + ' tags '
                if len( attrs ) > 0: text += 'with attrs ' + str( attrs ) + ' '
                text += 'failed because index ' + str( index ) + ' was requested, but only ' + str( len( results ) ) + ' tags were found.'
                
                raise IndexError( text )
                
            
        
        return results
        
    
    def Parse( self, html ):
        
        root = bs4.BeautifulSoup( html, 'lxml' )
        
        roots = ( root, )
        
        for ( name, attrs, index ) in self._tag_rules:
            
            next_roots = []
            
            for root in roots:
                
                next_roots.extend( self._ParseTags( root, name, attrs, index ) )
                
            
            roots = next_roots
            
        
        contents = [ self._ParseContent( root ) for root in roots ]
        
        return contents
        
    
    def ToTuple( self ):
        
        return ( self._tag_rules, self._content_rule )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_FORMULA_HTML ] = ParseFormulaHTML

class ParseNodeContent( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = None, content_type = None, formula = None, additional_info = None ):
        
        self._name = name
        self._content_type = content_type
        self._formula = formula
        self._additional_info = additional_info
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_formula = self._formula.GetSerialisableTuple()
        
        return ( self._name, self._content_type, serialisable_formula, self._additional_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._name, self._content_type, serialisable_formula, self._additional_info ) = serialisable_info
        
        self._formula = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_formula )
        
    
    def GetParsableContent( self ):
        
        return ( self._name, self._content_type )
        
    
    def Parse( self, data, referral_url, desired_content ):
        
        parsed_texts = self._formula.Parse( data )
        
        # maybe make this a dict, with name,type : result
        
        # file additional info is a niceness value so we can prefer full scale urls if they exist
        # tag is namespace
        # rating could be several things.
            # maybe a mapping of text to value, like sfw->1, questionable->2, explicit->3
            # or a multiplier to adjust 3.0 stars to 0.6
        
        return [ ( self._name, self._content_type, parsed_text, self._additional_info ) for parsed_text in parsed_texts ]
        
    
    def SetChildren( self, children ):
        
        self._children = children
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT ] = ParseNodeContent

class ParseNodeContentLink( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT_LINK
    SERIALISABLE_VERSION = 1
    
    def __init__( self, formula = None, children = None, description = None ):
        
        self._formula = formula
        self._children = children
        self._description = description
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_formula = self._formula.GetSerialisableTuple()
        serialisable_children = [ child.GetSerialisableTuple() for child in self._children ]
        
        return ( serialisable_formula, serialisable_children, self._description )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_formula, serialisable_children, self._description ) = serialisable_info
        
        self._formula = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_formula )
        self._children = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_child ) for serialisable_child in serialisable_children ]
        
    
    def GetParsableContent( self ):
        
        children_parsable_content = set()
        
        for child in self._children:
            
            children_parsable_content.update( child.GetParsableContent() )
            
        
        return children_parsable_content
        
    
    def Parse( self, data, referral_url, desired_content ):
        
        search_urls = self._formula.Parse( data )
        
        content = []
        
        for search_url in search_urls:
            
            # convert /muh_query to muh_domain.com/muh_query using the referral_url if needed
            # this could have additional_info one day to do more complicated url munging
            
            data = 'blah' # fetch with requests or w/e using referral url
            
            for child in self._children:
                
                # if what the child provides is in our desired list:
                
                content.extend( child.Parse( data, search_url, desired_content ) )
                
            
        
        return content
        
    
    def SetChildren( self, children ):
        
        self._children = children
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT_LINK ] = ParseNodeContentLink

FILE_IDENTIFIER_TYPE_FILE = 0
FILE_IDENTIFIER_TYPE_MD5 = 1
FILE_IDENTIFIER_TYPE_SHA1 = 2
FILE_IDENTIFIER_TYPE_SHA256 = 3
FILE_IDENTIFIER_TYPE_SHA512 = 3
FILE_IDENTIFIER_TYPE_USER_INPUT = 5

file_identifier_string_lookup = {}

file_identifier_string_lookup[ FILE_IDENTIFIER_TYPE_FILE ] = 'the actual file (POST only)'
file_identifier_string_lookup[ FILE_IDENTIFIER_TYPE_MD5 ] = 'md5 hash'
file_identifier_string_lookup[ FILE_IDENTIFIER_TYPE_SHA1 ] = 'sha1 hash'
file_identifier_string_lookup[ FILE_IDENTIFIER_TYPE_SHA256 ] = 'sha256 hash'
file_identifier_string_lookup[ FILE_IDENTIFIER_TYPE_SHA512 ] = 'sha512 hash'
file_identifier_string_lookup[ FILE_IDENTIFIER_TYPE_USER_INPUT ] = 'custom user input'

class ParseRootFileLookup( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, example_url = None, query_type = None, file_identifier_type = None, file_identifier_encoding = None, file_identifier_arg_name = None, static_args = None, children = None ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._example_url = example_url
        self._query_type = query_type
        self._file_identifier_type = file_identifier_type
        self._file_identifier_encoding = file_identifier_encoding
        self._file_identifier_arg_name = file_identifier_arg_name
        self._static_args = static_args
        self._children = children
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_children = [ child.GetSerialisableTuple() for child in self._children ]
        
        return ( self._example_url, self._query_type, self._file_identifier_type, self._file_identifier_encoding, self._file_identifier_arg_name, self._static_args, serialisable_children )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._example_url, self._query_type, self._file_identifier_type, self._file_identifier_encoding, self._file_identifier_arg_name, self._static_args, serialisable_children ) = serialisable_info
        
        self._children = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_child ) for serialisable_child in serialisable_children ]
        
    
    def FetchData( self, url, file_identifier ):
        
        if self._query_type == HC.POST and self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
            
            raise Exception( 'Cannot have a file as an argument on a GET query!' )
            
        
        # do a query on url in GET/POST, using the provided arg
        
        data = 'blah'
        
        return data
        
    
    def GetParsableContent( self ):
        
        children_parsable_content = set()
        
        for child in self._children:
            
            children_parsable_content.update( child.GetParsableContent() )
            
        
        return children_parsable_content
        
    
    def DoQuery( self, url, file_identifier, desired_content ):
        
        # this should take a job_key that will be propagated down and will have obeyed cancel and so on
        
        data = self.FetchData( url, file_identifier )
        
        content = []
        
        for child in self._children:
            
            # if what the child provides is in our desired list:
            
            content.extend( child.Parse( data, url, desired_content ) )
            
        
        return content
        
    
    def GetFileIdentifierInfo( self ):
        
        return ( self._file_identifier_type, self._file_identifier_encoding )
        
    
    def SetChildren( self, children ):
        
        self._children = children
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, HC.query_type_string_lookup[ self._query_type ], 'File Lookup returning ' + ConvertParsableContentToPrettyString( self.GetParsableContent() ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._example_url, self._query_type, self._file_identifier_type, self._file_identifier_encoding,  self._file_identifier_arg_name, self._static_args, self._children )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ] = ParseRootFileLookup
