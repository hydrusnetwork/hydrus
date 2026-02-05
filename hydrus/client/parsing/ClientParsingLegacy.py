import time
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.parsing import ClientParsing
from hydrus.client.parsing import ClientParsingResults

def GetChildrenContent( job_status, children, parsing_text, referral_url ) -> ClientParsingResults.ParsedPost:
    
    master_parsed_post = ClientParsingResults.ParsedPost( [] )
    
    for child in children:
        
        try:
            
            if isinstance( child, ParseNodeContentLink ):
                
                parsed_post = child.Parse( job_status, parsing_text, referral_url )
                
            elif isinstance( child, ClientParsing.ContentParser ):
                
                parsed_post = child.Parse( {}, parsing_text )
                
            else:
                
                continue
                
            
        except HydrusExceptions.VetoException:
            
            return ClientParsingResults.ParsedPost( [] )
            
        
        master_parsed_post.MergeParsedPost( parsed_post )
        
    
    return master_parsed_post
    

class ParseNodeContentLink( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_NODE_CONTENT_LINK
    SERIALISABLE_NAME = 'Content Parsing Link'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name = None, formula = None, children = None ):
        
        if name is None:
            
            name = ''
            
        
        if formula is None:
            
            formula = ClientParsing.ParseFormulaHTML()
            
        
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
        
    
    def GetParsableContentDescriptions( self ):
        
        children_parsable_content_descriptions = set()
        
        for child in self._children:
            
            children_parsable_content_descriptions.update( child.GetParsableContentDescriptions() )
            
        
        return children_parsable_content_descriptions
        
    
    def Parse( self, job_status, parsing_text, referral_url ) -> ClientParsingResults.ParsedPost:
        
        search_urls = self.ParseURLs( job_status, parsing_text, referral_url )
        
        master_parsed_post = ClientParsingResults.ParsedPost( [] )
        
        for search_url in search_urls:
            
            job_status.SetVariable( 'script_status', 'fetching ' + HydrusText.ElideText( search_url, 32 ) )
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', search_url, referral_url = referral_url )
            
            network_job.OverrideBandwidth()
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
            except HydrusExceptions.CancelledException:
                
                break
                
            except HydrusExceptions.NetworkException as e:
                
                if isinstance( e, HydrusExceptions.NotFoundException ):
                    
                    job_status.SetVariable( 'script_status', '404 - nothing found' )
                    
                    time.sleep( 2 )
                    
                    continue
                    
                elif isinstance( e, HydrusExceptions.NetworkException ):
                    
                    job_status.SetVariable( 'script_status', 'Network error! Details written to log.' )
                    
                    HydrusData.Print( 'Problem fetching ' + HydrusText.ElideText( search_url, 256 ) + ':' )
                    HydrusData.PrintException( e )
                    
                    time.sleep( 2 )
                    
                    continue
                    
                else:
                    
                    raise
                    
                
            
            linked_text = network_job.GetContentText()
            
            parsed_post = GetChildrenContent( job_status, self._children, linked_text, search_url )
            
            master_parsed_post.MergeParsedPost( parsed_post )
            
            if job_status.IsCancelled():
                
                raise HydrusExceptions.CancelledException( 'Job was cancelled.' )
                
            
        
        return master_parsed_post
        
    
    def ParseURLs( self, job_status, parsing_text, referral_url ):
        
        collapse_newlines = True
        
        basic_urls = self._formula.Parse( {}, parsing_text, collapse_newlines )
        
        absolute_urls = [ urllib.parse.urljoin( referral_url, basic_url ) for basic_url in basic_urls ]
        
        for url in absolute_urls:
            
            job_status.AddURL( url )
            
        
        return absolute_urls
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, 'link', ClientParsingResults.ConvertParsableContentDescriptionsToPrettyString( self.GetParsableContentDescriptions() ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._formula, self._children )
        
    
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

# eventually transition this to be a flat 'generate page/gallery urls'
# the rest of the parsing system can pick those up automatically
# this nullifies the need for contentlink stuff, at least in its current borked form
class ParseRootFileLookup( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP
    SERIALISABLE_NAME = 'File Lookup Script'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name, url = None, query_type = None, file_identifier_type = None, file_identifier_string_converter = None, file_identifier_arg_name = None, static_args = None, children = None ):
        
        super().__init__( name )
        
        self._url = url
        self._query_type = query_type
        self._file_identifier_type = file_identifier_type
        self._file_identifier_string_converter = file_identifier_string_converter
        self._file_identifier_arg_name = file_identifier_arg_name
        self._static_args = static_args
        self._children = children
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_children = [ child.GetSerialisableTuple() for child in self._children ]
        serialisable_file_identifier_string_converter = self._file_identifier_string_converter.GetSerialisableTuple()
        
        return ( self._url, self._query_type, self._file_identifier_type, serialisable_file_identifier_string_converter, self._file_identifier_arg_name, self._static_args, serialisable_children )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._url, self._query_type, self._file_identifier_type, serialisable_file_identifier_string_converter, self._file_identifier_arg_name, self._static_args, serialisable_children ) = serialisable_info
        
        self._children = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_child ) for serialisable_child in serialisable_children ]
        self._file_identifier_string_converter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_identifier_string_converter )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( url, query_type, file_identifier_type, file_identifier_encoding, file_identifier_arg_name, static_args, serialisable_children ) = old_serialisable_info
            
            conversions = []
            
            if file_identifier_encoding == HC.ENCODING_RAW:
                
                pass
                
            elif file_identifier_encoding == HC.ENCODING_HEX:
                
                conversions.append( ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_HEX_UTF8 ) )
                
            elif file_identifier_encoding == HC.ENCODING_BASE64:
                
                conversions.append( ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_BASE64_UTF8 ) )
                
            
            file_identifier_string_converter = ClientStrings.StringConverter( conversions, 'some hash bytes' )
            
            serialisable_file_identifier_string_converter = file_identifier_string_converter.GetSerialisableTuple()
            
            new_serialisable_info = ( url, query_type, file_identifier_type, serialisable_file_identifier_string_converter, file_identifier_arg_name, static_args, serialisable_children )
            
            return ( 2, new_serialisable_info )
            
        
    
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
                
                source_to_desired = CG.client_controller.Read( 'file_hashes', ( sha256_hash, ), 'sha256', hash_type )
                
                other_hash = list( source_to_desired.values() )[0]
                
                return other_hash
                
            except Exception as e:
                
                raise Exception( 'I do not know that file\'s ' + hash_type + ' hash, so I cannot look it up!' )
                
            
        elif self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            client_files_manager = CG.client_controller.client_files_manager
            
            try:
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                return path
                
            except HydrusExceptions.FileMissingException as e:
                
                raise Exception( 'That file is not in the database\'s local files, so I cannot look it up!' )
                
            
        
    
    def FetchParsingText( self, job_status, file_identifier ):
        
        # add gauge report hook and in-stream cancel support to the get/post calls
        
        request_args = dict( self._static_args )
        
        if self._file_identifier_type != FILE_IDENTIFIER_TYPE_FILE:
            
            request_args[ self._file_identifier_arg_name ] = self._file_identifier_string_converter.Convert( file_identifier )
            
        
        f = None
        
        if self._query_type == HC.GET:
            
            if self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
                
                raise Exception( 'Cannot have a file as an argument on a GET query!' )
                
            
            single_value_parameters = []
            
            full_request_url = self._url + '?' + ClientNetworkingFunctions.ConvertQueryDictToText( request_args, single_value_parameters )
            
            job_status.SetVariable( 'script_status', 'fetching ' + HydrusText.ElideText( full_request_url, 32 ) )
            
            job_status.AddURL( full_request_url )
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', full_request_url )
            
        elif self._query_type == HC.POST:
            
            additional_headers = {}
            files = None
            
            if self._file_identifier_type == FILE_IDENTIFIER_TYPE_FILE:
                
                job_status.SetVariable( 'script_status', 'uploading file' )
                
                path  = file_identifier
                
                if self._file_identifier_string_converter.MakesChanges():
                    
                    with open( path, 'rb' ) as f:
                        
                        file_bytes = f.read()
                        
                    
                    f_altered = self._file_identifier_string_converter.Convert( file_bytes )
                    
                    request_args[ self._file_identifier_arg_name ] = f_altered
                    
                    additional_headers[ 'content-type' ] = 'application/x-www-form-urlencoded'
                    
                else:
                    
                    f = open( path, 'rb' )
                    
                    files = { self._file_identifier_arg_name : f }
                    
                
            else:
                
                job_status.SetVariable( 'script_status', 'uploading identifier' )
                
                files = None
                
            
            network_job = ClientNetworkingJobs.NetworkJob( 'POST', self._url, body = request_args )
            
            if files is not None:
                
                network_job.SetFiles( files )
                
            
            for ( key, value ) in additional_headers.items():
                
                network_job.AddAdditionalHeader( key, value )
                
            
        
        # send nj to nj control on this panel here
        
        network_job.OverrideBandwidth()
        
        CG.client_controller.network_engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.NotFoundException:
            
            job_status.SetVariable( 'script_status', '404 - nothing found' )
            
            raise
            
        except HydrusExceptions.NetworkException as e:
            
            job_status.SetVariable( 'script_status', 'Network error!' )
            
            HydrusData.ShowException( e )
            
            raise
            
        finally:
            
            if f is not None:
                
                f.close()
                
            
        
        if self._query_type == HC.GET:
            
            actual_fetched_url = network_job.GetActualFetchedURL()
            
            job_status.AddURL( actual_fetched_url )
            
        
        if job_status.IsCancelled():
            
            raise HydrusExceptions.CancelledException( 'Job was cancelled.' )
            
        
        parsing_text = network_job.GetContentText()
        
        return parsing_text
        
    
    def GetParsableContentDescriptions( self ):
        
        children_parsable_content_descriptions = set()
        
        for child in self._children:
            
            children_parsable_content_descriptions.update( child.GetParsableContentDescriptions() )
            
        
        return children_parsable_content_descriptions
        
    
    def DoQuery( self, job_status, file_identifier ) -> ClientParsingResults.ParsedPost:
        
        try:
            
            try:
                
                parsing_text = self.FetchParsingText( job_status, file_identifier )
                
            except HydrusExceptions.NetworkException as e:
                
                return ClientParsingResults.ParsedPost( [] )
                
            
            parsed_post = self.Parse( job_status, parsing_text )
            
            return parsed_post
            
        except HydrusExceptions.CancelledException:
            
            job_status.SetVariable( 'script_status', 'Cancelled!' )
            
            return ClientParsingResults.ParsedPost( [] )
            
        finally:
            
            job_status.Finish()
            
        
    
    def UsesUserInput( self ):
        
        return self._file_identifier_type == FILE_IDENTIFIER_TYPE_USER_INPUT
        
    
    def Parse( self, job_status, parsing_text ) -> ClientParsingResults.ParsedPost:
        
        parsed_post = GetChildrenContent( job_status, self._children, parsing_text, self._url )
        
        if len( parsed_post ) == 0:
            
            job_status.SetVariable( 'script_status', 'Did not find anything.' )
            
        else:
            
            job_status.SetVariable( 'script_status', f'Found {HydrusNumbers.ToHumanInt( len( parsed_post ) )} rows.' )
            
        
        return parsed_post
        
    
    def SetChildren( self, children ):
        
        self._children = children
        
    
    def ToPrettyStrings( self ):
        
        return ( self._name, HC.query_type_string_lookup[ self._query_type ], 'File Lookup', ClientParsingResults.ConvertParsableContentDescriptionsToPrettyString( self.GetParsableContentDescriptions() ) )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._url, self._query_type, self._file_identifier_type, self._file_identifier_string_converter,  self._file_identifier_arg_name, self._static_args, self._children )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ] = ParseRootFileLookup
