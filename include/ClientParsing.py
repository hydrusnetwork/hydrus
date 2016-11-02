import bs4
import ClientNetworking
import HydrusConstants as HC
import HydrusData
import HydrusSerialisable
import HydrusTags
import os
import urlparse

def ChildHasDesiredContent( child, desired_content ):
    
    return desired_content == 'all' or len( child.GetParsableContent().intersection( desired_content ) ) > 0
    
def ConvertContentResultToPrettyString( result ):
    
    ( ( name, content_type, additional_info ), parsed_text ) = result
    
    if content_type == HC.CONTENT_TYPE_MAPPINGS:
        
        return 'tag: ' + HydrusTags.CombineTag( additional_info, parsed_text )
        
    elif content_type == HC.CONTENT_TYPE_VETO:
        
        return 'veto'
        
    
    raise NotImplementedError()
    
def ConvertParsableContentToPrettyString( parsable_content, include_veto = False ):
    
    pretty_strings = []
    
    content_type_to_additional_infos = HydrusData.BuildKeyToSetDict( ( ( content_type, additional_infos ) for ( name, content_type, additional_infos ) in parsable_content ) )
    
    for ( content_type, additional_infos ) in content_type_to_additional_infos.items():
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespaces = [ namespace for namespace in additional_infos if namespace != '' ]
            
            if '' in additional_infos:
                
                namespaces.append( 'unnamespaced' )
                
            
            pretty_strings.append( 'tags: ' + ', '.join( namespaces ) )
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            if include_veto:
                
                pretty_strings.append( 'veto' )
                
            
        
    
    if len( pretty_strings ) == 0:
        
        return 'nothing'
        
    else:
        
        return ', '.join( pretty_strings )
        
    
def GetChildrenContent( children, data, referral_url, desired_content ):
    
    for child in children:
        
        if child.Vetoes( data ):
            
            return []
            
        
    
    content = []
    
    for child in children:
        
        if ChildHasDesiredContent( child, desired_content ):
            
            child_content = child.Parse( data, referral_url, desired_content )
            
            content.extend( child_content )
            
        
    
    return content
    
def GetVetoes( parsed_texts, additional_info ):
    
    ( veto_if_matches_found, match_if_text_present, search_text ) = additional_info
    
    if match_if_text_present:
        
        matches = [ 'veto' for parsed_text in parsed_texts if search_text in parsed_text ]
        
    else:
        
        matches = [ 'veto' for parsed_text in parsed_texts if search_text not in parsed_text ]
        
    
    if veto_if_matches_found:
        
        return matches
        
    else:
        
        if len( matches ) == 0:
            
            return [ 'veto through absence' ]
            
        else:
            
            return []
            
        
    
def RenderTagRule( ( name, attrs, index ) ):
    
    if index is None:
        
        result = 'all ' + name + ' tags'
        
    else:
        
        result = HydrusData.ConvertIntToFirst( index + 1 ) + ' ' + name + ' tag'
        
    
    if len( attrs ) > 0:
        
        result += ' with ' + ' and '.join( [ key + ' = ' + value for ( key, value ) in attrs.items() ] )
        
    
    return result
    
class ParseFormulaHTML( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_FORMULA_HTML
    SERIALISABLE_VERSION = 1
    
    def __init__( self, tag_rules = None, content_rule = None ):
        
        if tag_rules is None:
            
            tag_rules = [ ( 'a', {}, None ) ]
            
        
        self._tag_rules = tag_rules
        
        self._content_rule = content_rule
        
        # I need extra rules here for chopping stuff off the beginning or end and appending or prepending strings
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._tag_rules, self._content_rule )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._tag_rules, self._content_rule ) = serialisable_info
        
    
    def _ParseContent( self, root ):
        
        if self._content_rule is None:
            
            result = root.string
            
        else:
            
            if root.has_attr( self._content_rule ):
                
                result = root[ self._content_rule ]
                
            else:
                
                result = None
                
            
        
        if result == '':
            
            return None
            
        else:
            
            return result
            
        
    
    def _ParseTags( self, root, name, attrs, index ):
        
        results = root.find_all( name = name, attrs = attrs )
        
        if index is not None:
            
            if len( results ) < index + 1:
                
                results = []
                
            else:
                
                results = [ results[ index ] ]
                
            
        
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
        
        contents = [ content for content in contents if content is not None ]
        
        return contents
        
    
    def ToPrettyMultilineString( self ):
        
        pretty_strings = []
        
        for ( name, attrs, index ) in self._tag_rules:
            
            s = ''
            
            if index is None:
                
                s += 'get every'
                
            else:
                
                num = index + 1
                
                s += 'get the ' + HydrusData.ConvertIntToPrettyOrdinalString( num )
                
            
            s += ' <' + name + '> tag'
            
            if len( attrs ) > 0:
                
                s += ' with attributes ' + ', '.join( key + '=' + value for ( key, value ) in attrs.items() )
                
            
            pretty_strings.append( s )
            
        
        if self._content_rule is None:
            
            pretty_strings.append( 'get the text content of those tags' )
            
        else:
            
            pretty_strings.append( 'get the ' + self._content_rule + ' attribute of those tags' )
            
        
        separator = os.linesep + 'and then '
        
        pretty_multiline_string = separator.join( pretty_strings )
        
        return pretty_multiline_string
        
    
    def ToTuple( self ):
        
        return ( self._tag_rules, self._content_rule )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_FORMULA_HTML ] = ParseFormulaHTML

class ParseNodeContent( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = None, content_type = None, formula = None, additional_info = None ):
        
        if name is None:
            
            name = ''
            
        
        if content_type is None:
            
            content_type = HC.CONTENT_TYPE_MAPPINGS
            
        
        if formula is None:
            
            formula = ParseFormulaHTML()
            
        
        if additional_info is None:
            
            if content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                additional_info = ''
                
            
        
        self._name = name
        self._content_type = content_type
        self._formula = formula
        self._additional_info = additional_info
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_formula = self._formula.GetSerialisableTuple()
        
        return ( self._name, self._content_type, serialisable_formula, self._additional_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._name, self._content_type, serialisable_formula, self._additional_info ) = serialisable_info
        
        if isinstance( self._additional_info, list ):
            
            self._additional_info = tuple( self._additional_info )
            
        
        self._formula = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_formula )
        
    
    def GetParsableContent( self ):
        
        return { ( self._name, self._content_type, self._additional_info ) }
        
    
    def Parse( self, data, referral_url, desired_content ):
        
        content_description = ( self._name, self._content_type, self._additional_info )
        
        parsed_texts = self._formula.Parse( data )
        
        if self._content_type == HC.CONTENT_TYPE_VETO:
            
            vetoes = GetVetoes( parsed_texts, self._additional_info )
            
            return [ ( content_description, veto ) for veto in vetoes ]
            
        else:
            
            return [ ( content_description, parsed_text ) for parsed_text in parsed_texts ]
            
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, 'content', ConvertParsableContentToPrettyString( self.GetParsableContent(), include_veto = True ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._content_type, self._formula, self._additional_info )
        
    
    def Vetoes( self, data ):
        
        if self._content_type == HC.CONTENT_TYPE_VETO:
            
            parsed_texts = self._formula.Parse( data )
            
            vetoes = GetVetoes( parsed_texts, self._additional_info )
            
            return len( vetoes ) > 0
            
        else:
            
            return False
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT ] = ParseNodeContent

class ParseNodeContentLink( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT_LINK
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = None, formula = None, children = None ):
        
        if name is None:
            
            name = ''
            
        
        if formula is None:
            
            formula = ParseFormulaHTML()
            
        
        if children is None:
            
            children = []
            
        
        self._name = name
        self._formula = formula
        self._children = children
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_formula = self._formula.GetSerialisableTuple()
        serialisable_children = [ child.GetSerialisableTuple() for child in self._children ]
        
        return ( self._name, serialisable_formula, serialisable_children )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._name, serialisable_formula, serialisable_children ) = serialisable_info
        
        self._formula = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_formula )
        self._children = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_child ) for serialisable_child in serialisable_children ]
        
    
    def GetParsableContent( self ):
        
        children_parsable_content = set()
        
        for child in self._children:
            
            children_parsable_content.update( child.GetParsableContent() )
            
        
        return children_parsable_content
        
    
    def Parse( self, data, referral_url, desired_content ):
        
        search_urls = self.ParseURLs( data, referral_url )
        
        content = []
        
        for search_url in search_urls:
            
            headers = { 'Referer' : referral_url }
            
            response = ClientNetworking.RequestsGet( search_url, headers = headers )
            
            children_content = GetChildrenContent( self._children, data, search_url, desired_content )
            
            content.extend( children_content )
            
        
        return content
        
    
    def ParseURLs( self, data, referral_url ):
        
        basic_urls = self._formula.Parse( data )
        
        absolute_urls = [ urlparse.urljoin( referral_url, basic_url ) for basic_url in basic_urls ]
        
        return absolute_urls
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, 'link', ConvertParsableContentToPrettyString( self.GetParsableContent() ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._formula, self._children )
        
    
    def Vetoes( self, data ):
        
        return False
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT_LINK ] = ParseNodeContentLink

FILE_IDENTIFIER_TYPE_FILE = 0
FILE_IDENTIFIER_TYPE_MD5 = 1
FILE_IDENTIFIER_TYPE_SHA1 = 2
FILE_IDENTIFIER_TYPE_SHA256 = 3
FILE_IDENTIFIER_TYPE_SHA512 = 4
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
    
    def __init__( self, name, url = None, query_type = None, file_identifier_type = None, file_identifier_encoding = None, file_identifier_arg_name = None, static_args = None, children = None ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._url = url
        self._query_type = query_type
        self._file_identifier_type = file_identifier_type
        self._file_identifier_encoding = file_identifier_encoding
        self._file_identifier_arg_name = file_identifier_arg_name
        self._static_args = static_args
        self._children = children
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_children = [ child.GetSerialisableTuple() for child in self._children ]
        
        return ( self._url, self._query_type, self._file_identifier_type, self._file_identifier_encoding, self._file_identifier_arg_name, self._static_args, serialisable_children )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._url, self._query_type, self._file_identifier_type, self._file_identifier_encoding, self._file_identifier_arg_name, self._static_args, serialisable_children ) = serialisable_info
        
        self._children = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_child ) for serialisable_child in serialisable_children ]
        
    
    def FetchData( self, file_identifier ):
        
        request_args = dict( self._static_args )
        
        if self._file_identifier_type != FILE_IDENTIFIER_TYPE_FILE:
            
            request_args[ self._file_identifier_arg_name ] = HydrusData.EncodeBytes( self._file_identifier_encoding, file_identifier )
            
        
        if self._query_type == HC.GET:
            
            if self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
                
                raise Exception( 'Cannot have a file as an argument on a GET query!' )
                
            
            response = ClientNetworking.RequestsGet( self._url, params = request_args )
            
        elif self._query_type == HC.POST:
            
            if self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
                
                path  = file_identifier
                
                files = { self._file_identifier_arg_name : open( path, 'rb' ) }
                
            else:
                
                files = None
                
            
            response = ClientNetworking.RequestsPost( self._url, data = request_args, files = files )
            
        
        data = response.content
        
        return data
        
    
    def GetParsableContent( self ):
        
        children_parsable_content = set()
        
        for child in self._children:
            
            children_parsable_content.update( child.GetParsableContent() )
            
        
        return children_parsable_content
        
    
    def DoQuery( self, file_identifier, desired_content ):
        
        # this should eventually take a job_key that will be propagated down and will have obeyed cancel and so on
        
        data = self.FetchData( file_identifier )
        
        return self.Parse( data, desired_content )
        
    
    def GetFileIdentifier( self ):
        
        return ( self._file_identifier_type, self._file_identifier_encoding )
        
    
    def Parse( self, data, desired_content ):
        
        content = GetChildrenContent( self._children, data, self._url, desired_content )
        
        return content
        
    
    def SetChildren( self, children ):
        
        self._children = children
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, HC.query_type_string_lookup[ self._query_type ], 'File Lookup', ConvertParsableContentToPrettyString( self.GetParsableContent() ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._url, self._query_type, self._file_identifier_type, self._file_identifier_encoding,  self._file_identifier_arg_name, self._static_args, self._children )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ] = ParseRootFileLookup
