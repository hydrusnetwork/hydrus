import base64
import collections
import collections.abc
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client.metadata import ClientTags

def ConvertParsableContentDescriptionsToPrettyString( parsable_content_descriptions: collections.abc.Collection[ "ParsableContentDescription" ], include_veto = False ):
    
    # when this was tuple hell, this guy used to go "tags: creator, series, unnamespaced". it would be neat to have that compression again, so think about it
    # maybe each subclass could have the ability to do STATICToMassString( pcds ) or something, and then I just group by
    
    content_types_to_pcds = HydrusData.BuildKeyToSetDict( [ ( pcd.content_type, pcd ) for pcd in parsable_content_descriptions ] )
    
    content_types = sorted( content_types_to_pcds.keys(), key = lambda content_type: HC.content_type_string_lookup[ content_type ] )
    
    pretty_strings = []
    
    for content_type in content_types:
        
        pcds = typing.cast( list[ ParsableContentDescription ], list( content_types_to_pcds[ content_type ] ) )
        
        shorthand_strings = sorted( { s for s in { pcd.GetShorthandContentSpecificInfoString() for pcd in pcds } if s is not None } )
        
        if len( shorthand_strings ) == 0:
            
            pretty_string = HC.content_type_string_lookup[ content_type ]
            
        else:
            
            comma_gubbins = ', '.join( shorthand_strings )
            
            pretty_string = f'{HC.content_type_string_lookup[ content_type ]}: {comma_gubbins}'
            
        
        pretty_strings.append( pretty_string )
        
    
    if len( pretty_strings ) == 0:
        
        return 'nothing'
        
    else:
        
        return ', '.join( pretty_strings )
        
    

def GetHashFromParsedText( hash_encoding, parsed_text ) -> bytes:
    
    encodings_to_attempt = []
    
    if hash_encoding == 'hex':
        
        encodings_to_attempt = [ 'hex', 'base64' ]
        
    elif hash_encoding == 'base64':
        
        encodings_to_attempt = [ 'base64' ]
        
    
    main_error_text = None
    
    for encoding_to_attempt in encodings_to_attempt:
        
        try:
            
            if encoding_to_attempt == 'hex':
                
                return bytes.fromhex( parsed_text )
                
            elif encoding_to_attempt == 'base64':
                
                return base64.b64decode( parsed_text )
                
            
        except Exception as e:
            
            if main_error_text is None:
                
                main_error_text = str( e )
                
            
            continue
            
        
    
    raise Exception( 'Could not decode hash: {}'.format( main_error_text ) )
    

def GetNamespacesFromParsableContentDescriptions( parsable_content_descriptions: list[ "ParsableContentDescription" ] ):
    
    namespaces = set()
    
    for parsable_content_description in parsable_content_descriptions:
        
        if isinstance( parsable_content_description, ParsableContentDescriptionTag ):
            
            namespace = parsable_content_description.namespace
            
            if namespace is None:
                
                namespace = ''
                
            
            namespaces.add( namespace )
            
        
    
    namespaces = sorted( namespaces )
    
    return namespaces
    

def GetTitleFromParsedPosts( parsed_posts: list[ "ParsedPost" ] ) -> str | None:
    
    titles = []
    
    for parsed_post in parsed_posts:
        
        for parsed_content in parsed_post.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionTitle ):
                
                titles.append( ( parsed_content_description.priority, parsed_content.parsed_text ) )
                
            
        
    
    if len( titles ) > 0:
        
        titles.sort( reverse = True ) # highest priority first
        
        ( priority, title ) = titles[0]
        
        return title
        
    else:
        
        return None
        
    

# TODO: Ok all these guys needs to be serialisable, aaarghhhaaaiiieeeeeeeeeee
class ParsableContentDescription( object ):
    
    def __init__( self, name: str, content_type: int ):
        
        self.name = name
        self.content_type = content_type
        
    
    def __eq__( self, other ):
        
        if isinstance( other, ParsableContentDescription ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return 'unknown'
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = f'{HC.content_type_string_lookup[ self.content_type ]}: {self.name}'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            return f'{descriptor}: {parsed_text}'
            
        
    

class ParsableContentDescriptionHash( ParsableContentDescription ):
    
    def __init__( self, name: str, hash_type: str, hash_encoding: str ):
        
        self.hash_type = hash_type
        self.hash_encoding = hash_encoding
        
        super().__init__( name, HC.CONTENT_TYPE_HASH )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.hash_type, self.hash_encoding ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return self.hash_type
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = f'{self.hash_type} hash'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            try:
                
                hash = GetHashFromParsedText( self.hash_encoding, parsed_text )
                
                parsed_text_hex = hash.hex()
                
            except Exception as e:
                
                parsed_text_hex = 'Could not decode a hash from {}: {}'.format( parsed_text, repr( e ) )
                
            
            return f'{descriptor}: {parsed_text_hex}'
            
        
    

class ParsableContentDescriptionHTTPHeaders( ParsableContentDescription ):
    
    def __init__( self, name: str, header_name: str ):
        
        self.header_name = header_name
        
        super().__init__( name, HC.CONTENT_TYPE_HTTP_HEADERS )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.header_name ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return self.header_name
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = f'http header "{self.header_name}"'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            return f'{descriptor}: {parsed_text}'
            
        
    

class ParsableContentDescriptionNote( ParsableContentDescription ):
    
    def __init__( self, name: str, note_name: str ):
        
        self.note_name = note_name
        
        super().__init__( name, HC.CONTENT_TYPE_NOTES )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.note_name ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return self.note_name
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = f'note "{self.note_name}"'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            return f'{descriptor}:\n{parsed_text}'
            
        
    

class ParsableContentDescriptionTag( ParsableContentDescription ):
    
    def __init__( self, name: str, namespace: str | None ):
        
        self.namespace = namespace
        
        super().__init__( name, HC.CONTENT_TYPE_MAPPINGS )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.namespace ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        if self.namespace is None:
            
            return None
            
        else:
            
            return ClientTags.RenderNamespaceForUser( self.namespace )
            
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        if parsed_text is None:
            
            if self.namespace is not None:
                
                return f'{ClientTags.RenderNamespaceForUser( self.namespace )} tag'
                
            else:
                
                return 'tag'
                
            
        else:
            
            try:
                
                if self.namespace is None:
                    
                    combined_tag = parsed_text
                    
                else:
                    
                    combined_tag = HydrusTags.CombineTag( self.namespace, parsed_text )
                    
                
                tag = HydrusTags.CleanTag( combined_tag )
                
            except:
                
                tag = 'unparsable tag, will likely be discarded'
                
            
            try:
                
                HydrusTags.CheckTagNotEmpty( tag )
                
            except HydrusExceptions.TagSizeException:
                
                tag = 'empty tag, will be discarded'
                
            
            return f'tag: {tag}'
            
        
    

class ParsableContentDescriptionTimestamp( ParsableContentDescription ):
    
    def __init__( self, name: str, timestamp_type: int | None ):
        
        self.timestamp_type = timestamp_type
        
        super().__init__( name, HC.CONTENT_TYPE_TIMESTAMP )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.timestamp_type ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        if self.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            return 'source/post time'
            
        else:
            
            return 'unknown timestamp type!'
            
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = self.GetShorthandContentSpecificInfoString()
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            try:
                
                timestamp = int( parsed_text )
                
                timestamp_string = HydrusTime.TimestampToPrettyTime( timestamp )
                
            except:
                
                timestamp_string = 'could not convert to integer'
                
            
            return f'{descriptor}: {timestamp_string}'
            
        
    

class ParsableContentDescriptionTitle( ParsableContentDescription ):
    
    def __init__( self, name: str, priority: int ):
        
        self.priority = priority
        
        super().__init__( name, HC.CONTENT_TYPE_TITLE )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.priority ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return None
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = f'watcher page title (priority {self.priority})'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            return f'{descriptor}: {parsed_text}'
            
        
    

class ParsableContentDescriptionURL( ParsableContentDescription ):
    
    def __init__( self, name: str, url_type: int, priority: int ):
        
        self.url_type = url_type
        self.priority = priority
        
        super().__init__( name, HC.CONTENT_TYPE_URLS )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.url_type, self.priority ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        if self.url_type == HC.URL_TYPE_DESIRED:
            
            return 'downloadable/pursuable url'
            
        elif self.url_type == HC.URL_TYPE_SOURCE:
            
            return 'associable/source url'
            
        elif self.url_type == HC.URL_TYPE_NEXT:
            
            return 'next page url'
            
        elif self.url_type == HC.URL_TYPE_SUB_GALLERY:
            
            return 'sub-gallery url'
            
        else:
            
            return 'unknown url type!'
            
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        url_type_string = self.GetShorthandContentSpecificInfoString()
        
        descriptor = f'{url_type_string} (priority {self.priority})'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            return f'{descriptor}: {parsed_text}'
            
        
    

class ParsableContentDescriptionVariable( ParsableContentDescription ):
    
    def __init__( self, name: str, temp_variable_name: str ):
        
        self.temp_variable_name = temp_variable_name
        
        super().__init__( name, HC.CONTENT_TYPE_VARIABLE )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type, self.temp_variable_name ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return self.temp_variable_name
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        descriptor = f'temp variable "{self.temp_variable_name}"'
        
        if parsed_text is None:
            
            return descriptor
            
        else:
            
            return f'{descriptor}: {parsed_text}'
            
        
    

class ParsableContentDescriptionVeto( ParsableContentDescription ):
    
    def __init__( self, name: str ):
        
        super().__init__( name, HC.CONTENT_TYPE_VETO )
        
    
    def __hash__( self ):
        
        return ( self.name, self.content_type ).__hash__()
        
    
    def GetShorthandContentSpecificInfoString( self ) -> str | None:
        
        return self.name
        
    
    def ToString( self, parsed_text: str | None = None ) -> str:
        
        return f'veto: {self.name}'
        
    

class ParsedContent( object ):
    
    def __init__( self, parsed_content_description: ParsableContentDescription, parsed_text: str ):
        
        self.parsed_content_description = parsed_content_description
        self.parsed_text = parsed_text
        
    
    def ToString( self ) -> str:
        
        return self.parsed_content_description.ToString( parsed_text = self.parsed_text )
        
    

class ParsedPost( object ):
    
    def __init__( self, parsed_contents: list[ ParsedContent ] ):
        
        self.parsed_contents = parsed_contents
        
    
    def __len__( self ):
        
        return len( self.parsed_contents )
        
    
    def GetHashes( self ) -> list[ tuple[ str, bytes ] ]:
        
        hash_results = []
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionHash ):
                
                try:
                    
                    hash = GetHashFromParsedText( parsed_content_description.hash_encoding, parsed_content.parsed_text )
                    
                except:
                    
                    continue
                    
                
                hash_results.append( ( parsed_content_description.hash_type, hash ) )
                
            
        
        return hash_results
        

    def GetHTTPHeaders( self ) -> dict[ str, str ]:
        
        headers = {}
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionHTTPHeaders ):
                
                headers[ parsed_content_description.header_name ] = parsed_content.parsed_text
                
            
        
        return headers
        
    
    def GetNamesAndNotes( self ) -> list[ tuple[ str, str ] ]:
        
        name_and_note_results = []
        
        ordered_by_description_name = sorted( self.parsed_contents, key = lambda parsed_content: parsed_content.parsed_content_description.name )
        
        for parsed_content in ordered_by_description_name:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionNote ):
                
                note_text = HydrusText.CleanNoteText( parsed_content.parsed_text )
                
                if note_text == '':
                    
                    continue
                    
                
                name_and_note_results.append( ( parsed_content_description.note_name, note_text ) )
                
            
        
        return name_and_note_results
        

    def GetTags( self ) -> list[ str ]:
        
        tag_results = []
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionTag ):
                
                namespace = parsed_content_description.namespace
                
                make_no_namespace_changes = namespace is None
                
                subtag_or_tag = parsed_content.parsed_text
                
                if make_no_namespace_changes:
                    
                    combined_tag = subtag_or_tag
                    
                else:
                    
                    combined_tag = HydrusTags.CombineTag( namespace, subtag_or_tag )
                    
                
                tag_results.append( combined_tag )
                
            
        
        tag_results = HydrusTags.CleanTags( tag_results )
        
        return tag_results
        

    def GetTimestamp( self, desired_timestamp_type ) -> int | None:
        
        timestamp_results = []
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionTimestamp ):
                
                timestamp_type = parsed_content_description.timestamp_type
                
                if timestamp_type == desired_timestamp_type:
                    
                    try:
                        
                        timestamp = int( parsed_content.parsed_text )
                        
                    except:
                        
                        continue
                        
                    
                    if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
                        
                        timestamp = min( HydrusTime.GetNow() - 5, timestamp )
                        
                    
                    timestamp_results.append( timestamp )
                    
                
            
        
        if len( timestamp_results ) == 0:
            
            return None
            
        else:
            
            return min( timestamp_results )
            
        
    
    def GetURLs( self, desired_url_types, only_get_top_priority = False ) -> list[ str ]:
        
        url_results = collections.defaultdict( list )
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionURL ):
                
                if parsed_content_description.url_type in desired_url_types:
                    
                    url_results[ parsed_content_description.priority ].append( parsed_content.parsed_text )
                    
                
            
        
        if only_get_top_priority:
            
            # ( priority, url_list ) pairs
            
            url_results = list( url_results.items() )
            
            # ordered by descending priority
            
            url_results.sort( reverse = True )
            
            # url_lists of descending priority
            
            if len( url_results ) > 0:
                
                ( priority, url_list ) = url_results[0]
                
            else:
                
                url_list = []
                
            
        else:
            
            url_list = []
            
            for u_l in url_results.values():
                
                url_list.extend( u_l )
                
            
        
        url_list = HydrusLists.DedupeList( url_list )
        
        return url_list
        
    
    def GetVariable( self ) -> tuple[ str, str ] | None:
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionVariable ):
                
                return ( parsed_content_description.temp_variable_name, parsed_content.parsed_text )
                
            
        
        return None
        
    
    def HasPursuableURLs( self ) -> bool:
        
        for parsed_content in self.parsed_contents:
            
            parsed_content_description = parsed_content.parsed_content_description
            
            if isinstance( parsed_content_description, ParsableContentDescriptionURL ):
                
                if parsed_content_description.url_type == HC.URL_TYPE_DESIRED:
                    
                    return True
                    
                
            
        
        return False
        

    def MergeParsedPost( self, parsed_post: "ParsedPost" ):
        
        self.parsed_contents.extend( parsed_post.parsed_contents )
        
    
