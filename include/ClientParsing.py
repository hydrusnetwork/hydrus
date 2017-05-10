import bs4
import ClientNetworking
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import os
import time
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
        
    
def GetChildrenContent( job_key, children, data, referral_url, desired_content ):
    
    for child in children:
        
        if child.Vetoes( data ):
            
            return []
            
        
    
    content = []
    
    for child in children:
        
        if ChildHasDesiredContent( child, desired_content ):
            
            child_content = child.Parse( job_key, data, referral_url, desired_content )
            
            content.extend( child_content )
            
        
    
    return content
    
def GetTagsFromContentResults( results ):
    
    tag_results = []
    
    for ( ( name, content_type, additional_info ), parsed_text ) in results:
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            tag_results.append( HydrusTags.CombineTag( additional_info, parsed_text ) )
            
        
    
    tag_results = HydrusTags.CleanTags( tag_results )
    
    return tag_results
    
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
    SERIALISABLE_VERSION = 2
    
    def __init__( self, tag_rules = None, content_rule = None, culling_and_adding = None ):
        
        if tag_rules is None:
            
            tag_rules = [ ( 'a', {}, None ) ]
            
        
        if culling_and_adding is None:
            
            culling_and_adding = ( 0, 0, '', '' )
            
        
        self._tag_rules = tag_rules
        
        self._content_rule = content_rule
        
        self._culling_and_adding = culling_and_adding
        
    
    def _CullAndAdd( self, text ):
        
        ( cull_front, cull_back, prepend, append ) = self._culling_and_adding
        
        if cull_front != 0:
            
            text = text[ cull_front : ]
            
        
        if cull_back != 0:
            
            text = text[ : - cull_back ]
            
        
        if text == '':
            
            return None
            
        
        text = prepend + text + append
        
        return text
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._tag_rules, self._content_rule, self._culling_and_adding )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._tag_rules, self._content_rule, self._culling_and_adding ) = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( tag_rules, content_rule ) = old_serialisable_info
            
            culling_and_adding = ( 0, 0, '', '' )
            
            new_serialisable_info = ( tag_rules, content_rule, culling_and_adding )
            
            return ( 2, new_serialisable_info )
            
        
    
    def _ParseContent( self, root ):
        
        if self._content_rule is None:
            
            result = root.string
            
        else:
            
            if root.has_attr( self._content_rule ):
                
                unknown_attr_result = root[ self._content_rule ]
                
                # 'class' attr returns a list because it has multiple values under html spec, wew
                if isinstance( unknown_attr_result, list ):
                    
                    if len( unknown_attr_result ) == 0:
                        
                        result = None
                        
                    else:
                        
                        result = ' '.join( unknown_attr_result )
                        
                    
                else:
                    
                    result = unknown_attr_result
                    
                
            else:
                
                result = None
                
            
        
        if result == '' or result is None:
            
            return None
            
        else:
            
            return self._CullAndAdd( result )
            
        
    
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
            
        
        cull_munge_strings = []
        
        ( cull_front, cull_back, prepend, append ) = self._culling_and_adding
        
        if cull_front > 0:
            
            cull_munge_strings.append( 'the first ' + HydrusData.ConvertIntToPrettyString( cull_front ) + ' characters' )
            
        elif cull_front < 0:
            
            cull_munge_strings.append( 'all but the last ' + HydrusData.ConvertIntToPrettyString( abs( cull_front ) ) + ' characters' )
            
        
        if cull_back > 0:
            
            cull_munge_strings.append( 'the last ' + HydrusData.ConvertIntToPrettyString( cull_back ) + ' characters' )
            
        elif cull_back < 0:
            
            cull_munge_strings.append( 'all but the first ' + HydrusData.ConvertIntToPrettyString( abs( cull_back ) ) + ' characters' )
            
        
        if len( cull_munge_strings ) > 0:
            
            pretty_strings.append( 'remove ' + ' and '.join( cull_munge_strings ) )
            
        
        add_munge_strings = []
        
        if prepend != '':
            
            add_munge_strings.append( 'prepend "' + prepend + '"' )
            
        
        if append != '':
            
            add_munge_strings.append( 'append "' + append + '"' )
            
        
        if len( add_munge_strings ) > 0:
            
            pretty_strings.append( ' and '.join( add_munge_strings ) )
            
        
        separator = os.linesep + 'and then '
        
        pretty_multiline_string = separator.join( pretty_strings )
        
        return pretty_multiline_string
        
    
    def ToTuple( self ):
        
        return ( self._tag_rules, self._content_rule, self._culling_and_adding )
        
    
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
        
    
    def Parse( self, job_key, data, referral_url, desired_content ):
        
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
        
    
    def Parse( self, job_key, data, referral_url, desired_content ):
        
        search_urls = self.ParseURLs( job_key, data, referral_url )
        
        content = []
        
        for search_url in search_urls:
            
            try:
                
                job_key.SetVariable( 'script_status', 'fetching ' + search_url )
                
                headers = { 'Referer' : referral_url }
                
                response = ClientNetworking.RequestsGet( search_url, headers = headers )
                
            except HydrusExceptions.NotFoundException:
                
                job_key.SetVariable( 'script_status', '404 - nothing found' )
                
                time.sleep( 2 )
                
                continue
                
            except HydrusExceptions.NetworkException as e:
                
                job_key.SetVariable( 'script_status', 'Network error! Details written to log.' )
                
                HydrusData.Print( 'Problem fetching ' + search_url + ':' )
                HydrusData.PrintException( e )
                
                time.sleep( 2 )
                
                continue
                
            
            linked_data = response.text
            
            children_content = GetChildrenContent( job_key, self._children, linked_data, search_url, desired_content )
            
            content.extend( children_content )
            
            if job_key.IsCancelled():
                
                raise HydrusExceptions.CancelledException()
                
            
        
        return content
        
    
    def ParseURLs( self, job_key, data, referral_url ):
        
        basic_urls = self._formula.Parse( data )
        
        absolute_urls = [ urlparse.urljoin( referral_url, basic_url ) for basic_url in basic_urls ]
        
        for url in absolute_urls:
            
            job_key.AddURL( url )
            
        
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
        
    
    def ConvertMediaToFileIdentifier( self, media ):
        
        if self._file_identifier_type == FILE_IDENTIFIER_TYPE_USER_INPUT:
            
            raise Exception( 'Cannot convert media to file identifier--this script takes user input!' )
            
        elif self._file_identifier_type == FILE_IDENTIFIER_TYPE_SHA256:
            
            return media.GetHash()
            
        elif self._file_identifier_type in ( FILE_IDENTIFIER_TYPE_MD5, FILE_IDENTIFIER_TYPE_SHA1, FILE_IDENTIFIER_TYPE_SHA512 ):
            
            sha256_hash = media.GetHash()
            
            if self._file_identifier_type == FILE_IDENTIFIER_TYPE_MD5:
                
                hash_type = 'md5'
                
            elif self._file_identifier_type == FILE_IDENTIFIER_TYPE_SHA1:
                
                hash_type = 'sha1'
                
            elif self._file_identifier_type == FILE_IDENTIFIER_TYPE_SHA512:
                
                hash_type = 'sha512'
                
            
            try:
                
                ( other_hash, ) = HG.client_controller.Read( 'file_hashes', ( sha256_hash, ), 'sha256', hash_type )
                
                return other_hash
                
            except:
                
                raise Exception( 'I do not know that file\'s ' + hash_type + ' hash, so I cannot look it up!' )
                
            
        elif self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            client_files_manager = HG.client_controller.GetClientFilesManager()
            
            try:
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                return path
                
            except HydrusExceptions.FileMissingException as e:
                
                raise Exception( 'That file is not in the database\'s local files, so I cannot look it up!' )
                
            
        
    
    def FetchData( self, job_key, file_identifier ):
        
        try:
            
            # add gauge report hook and in-stream cancel support to the get/post calls
            
            request_args = dict( self._static_args )
            
            if self._file_identifier_type != FILE_IDENTIFIER_TYPE_FILE:
                
                request_args[ self._file_identifier_arg_name ] = HydrusData.EncodeBytes( self._file_identifier_encoding, file_identifier )
                
            
            if self._query_type == HC.GET:
                
                if self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
                    
                    raise Exception( 'Cannot have a file as an argument on a GET query!' )
                    
                
                rendered_url = self._url + '?' + '&'.join( ( HydrusData.ToByteString( key ) + '=' + HydrusData.ToByteString( value ) for ( key, value ) in request_args.items() ) )
                
                job_key.SetVariable( 'script_status', 'fetching ' + rendered_url )
                
                job_key.AddURL( rendered_url )
                
                response = ClientNetworking.RequestsGet( self._url, params = request_args )
                
            elif self._query_type == HC.POST:
                
                if self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
                    
                    job_key.SetVariable( 'script_status', 'uploading file' )
                    
                    path  = file_identifier
                    
                    files = { self._file_identifier_arg_name : open( path, 'rb' ) }
                    
                else:
                    
                    job_key.SetVariable( 'script_status', 'uploading identifier' )
                    
                    files = None
                    
                
                response = ClientNetworking.RequestsPost( self._url, data = request_args, files = files )
                
            
            if job_key.IsCancelled():
                
                raise HydrusExceptions.CancelledException()
                
            
            data = response.text
            
            return data
            
        except HydrusExceptions.NotFoundException:
            
            job_key.SetVariable( 'script_status', '404 - nothing found' )
            
            raise
            
        except HydrusExceptions.NetworkException as e:
            
            job_key.SetVariable( 'script_status', 'Network error!' )
            
            HydrusData.ShowException( e )
            
            raise
            
        
    
    def GetParsableContent( self ):
        
        children_parsable_content = set()
        
        for child in self._children:
            
            children_parsable_content.update( child.GetParsableContent() )
            
        
        return children_parsable_content
        
    
    def DoQuery( self, job_key, file_identifier, desired_content ):
        
        try:
            
            try:
                
                data = self.FetchData( job_key, file_identifier )
                
            except HydrusExceptions.NetworkException as e:
                
                return []
                
            
            content_results = self.Parse( job_key, data, desired_content )
            
            return content_results
            
        except HydrusExceptions.CancelledException:
            
            job_key.SetVariable( 'script_status', 'Cancelled!' )
            
            return []
            
        finally:
            
            job_key.Finish()
            
        
    
    def UsesUserInput( self ):
        
        return self._file_identifier_type == FILE_IDENTIFIER_TYPE_USER_INPUT
        
    
    def Parse( self, job_key, data, desired_content ):
        
        content_results = GetChildrenContent( job_key, self._children, data, self._url, desired_content )
        
        if len( content_results ) == 0:
            
            job_key.SetVariable( 'script_status', 'Did not find anything.' )
            
        else:
            
            job_key.SetVariable( 'script_status', 'Found ' + HydrusData.ConvertIntToPrettyString( len( content_results ) ) + ' rows.' )
            
        
        return content_results
        
    
    def SetChildren( self, children ):
        
        self._children = children
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, HC.query_type_string_lookup[ self._query_type ], 'File Lookup', ConvertParsableContentToPrettyString( self.GetParsableContent() ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._url, self._query_type, self._file_identifier_type, self._file_identifier_encoding,  self._file_identifier_arg_name, self._static_args, self._children )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ] = ParseRootFileLookup
