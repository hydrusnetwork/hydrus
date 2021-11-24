import collections
import os
import re
import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

def CensorshipMatch( tag, censorships ):
    
    for censorship in censorships:
        
        if censorship == '': # '' - all non namespaced tags
            
            ( namespace, subtag ) = SplitTag( tag )
            
            if namespace == '':
                
                return True
                
            
        elif censorship == ':': # ':' - all namespaced tags
            
            ( namespace, subtag ) = SplitTag( tag )
            
            if namespace != '':
                
                return True
                
            
        elif ':' in censorship:
            
            if censorship.endswith( ':' ): # 'series:' - namespaced tags
                
                ( namespace, subtag ) = SplitTag( tag )
                
                if namespace == censorship[:-1]:
                    
                    return True
                    
                
            else: # 'series:evangelion' - exact match with namespace
                
                if tag == censorship:
                    
                    return True
                    
                
            
        else:
            
            # 'table' - normal tag, or namespaced version of same
            
            ( namespace, subtag ) = SplitTag( tag )
            
            if subtag == censorship:
                
                return True
                
            
        
    
    return False
    
def CollapseMultipleSortedNumericTagsToMinMax( tags ):
    
    if len( tags ) <= 2:
        
        return tags
        
    else:
        
        includes_non_numeric_tag = True in ( not isinstance( ConvertTagToSortable( tag ), tuple ) for tag in tags )
        
        if includes_non_numeric_tag:
            
            return tags
            
        else:
            
            # this list of tags is entirely numeric and may well be something like 1, 2, 3, 4, 5
            # the caller wants to present 1-5 instead, so lets cut out the first and last
            
            if not isinstance( tags, list ):
                
                tags = list( tags )
                
            
            return [ tags[0], tags[-1] ]
            
        
    
def ConvertTagToSortable( tag ):
    
    # this copies the human sort in hydrusdata
    
    convert = lambda text: ( '', int( text ) ) if text.isdecimal() else ( text, 0 )
    
    return tuple( [ convert( c ) for c in re.split( '([0-9]+)', tag.lower() ) ] )
    
    # old method
    
    '''if len( t ) > 0 and t[0].isdecimal():
        
        # We want to maintain that:
        # 0 < 0a < 0b < 1 ( lexicographic comparison )
        # -and-
        # 2 < 22 ( value comparison )
        # So, if the first bit can be turned into an int, split it into ( int, extra )
        
        int_component = ''
        
        i = 0
        
        for character in t:
            
            if character.isdecimal():
                
                int_component += character
                
            else:
                
                break
                
            
            i += 1
            
        
        str_component = t[i:]
        
        number = int( int_component )
        
        return ( number, str_component )
        
    else:
        
        return t
        '''

def FilterNamespaces( tags, namespaces ):
    
    processed_tags = collections.defaultdict( set )
    
    for tag in tags:
        
        ( namespace, subtag ) = SplitTag( tag )
        
        processed_tags[ namespace ].add( tag )
        
    
    result = set()
    
    for namespace in namespaces:
        
        if namespace == None:
            
            result.update( processed_tags[ '' ] )
            
        else:
            
            result.update( processed_tags[ namespace ] )
            
        
    
    return result
    
def SortNumericTags( tags ):
    
    tags = list( tags )
    
    tags.sort( key = ConvertTagToSortable )
    
    return tags
    
def CheckTagNotEmpty( tag ):
    
    ( namespace, subtag ) = SplitTag( tag )
    
    if subtag == '':
        
        raise HydrusExceptions.TagSizeException( 'Received a zero-length tag!' )
        
    
def CleanTag( tag ):
    
    try:
        
        if tag is None:
            
            raise Exception()
            
        
        tag = tag[:1024]
        
        tag = tag.lower()
        
        tag = HydrusText.re_leading_single_colon.sub( '::', tag ) # Convert anything starting with one colon to start with two i.e. :D -> ::D
        
        if ':' in tag:
            
            tag = StripTextOfGumpf( tag ) # need to repeat here to catch 'system:' stuff
            
            ( namespace, subtag ) = SplitTag( tag )
            
            namespace = StripTextOfGumpf( namespace )
            subtag = StripTextOfGumpf( subtag )
            
            tag = CombineTag( namespace, subtag )
            
        else:
            
            tag = StripTextOfGumpf( tag )
            
        
    except Exception as e:
        
        text = 'Was unable to parse the tag: ' + str( tag )
        text += os.linesep * 2
        text += str( e )
        
        raise Exception( text )
        
    
    return tag

def CleanTags( tags ):
    
    clean_tags = set()
    
    for tag in tags:
        
        if tag is None:
            
            continue
            
        
        tag = CleanTag( tag )
        
        try:
            
            CheckTagNotEmpty( tag )
            
        except HydrusExceptions.TagSizeException:
            
            continue
            
        
        clean_tags.add( tag )
        
    
    return clean_tags
    
def CombineTag( namespace, subtag ):
    
    if namespace == '':
        
        if HydrusText.re_leading_single_colon.search( subtag ) is not None:
            
            return ':' + subtag
            
        else:
            
            return subtag
            
        
    else:
        
        return namespace + ':' + subtag
        
    
def ConvertTagSliceToString( tag_slice ):
    
    if tag_slice == '':
        
        return 'unnamespaced tags'
        
    elif tag_slice == ':':
        
        return 'namespaced tags'
        
    elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
        
        namespace = tag_slice[ : -1 ]
        
        return '\'' + namespace + '\' tags'
        
    else:
        
        return tag_slice
        
    
def IsUnnamespaced( tag ):
    
    return SplitTag( tag )[0] == ''
    
def SplitTag( tag ):
    
    if ':' in tag:
        
        return tuple( tag.split( ':', 1 ) )
        
    else:
        
        return ( '', tag )
        
    
NULL_CHARACTER = '\x00'

def StripTextOfGumpf( t ):
    
    t = HydrusText.re_newlines.sub( '', t )
    
    t = HydrusText.re_multiple_spaces.sub( ' ', t )
    
    t = t.strip()
    
    t = HydrusText.re_leading_space_or_garbage.sub( '', t )
    
    if NULL_CHARACTER in t:
        
        t = t.replace( NULL_CHARACTER, '' )
        
    
    return t
    
def TagOK( t ):
    
    try:
        
        CheckTagNotEmpty( CleanTag( t ) )
        
        return True
        
    except:
        
        return False
        
    
class TagFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Tag Filter Rules'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._tag_slices_to_rules = {}
        
        self._all_unnamespaced_whitelisted = False
        self._all_namespaced_whitelisted = False
        self._namespaces_whitelist = set()
        self._tags_whitelist = set()
        
        self._all_unnamespaced_blacklisted = False
        self._all_namespaced_blacklisted = False
        self._namespaces_blacklist = set()
        self._tags_blacklist = set()
        
        self._namespaced_interesting = False
        self._tags_interesting = False
        
    
    def __eq__( self, other ):
        
        if isinstance( other, TagFilter ):
            
            return self._tag_slices_to_rules == other._tag_slices_to_rules
            
        
        return NotImplemented
        
    
    def _IterateTagSlices( self, tag, apply_unnamespaced_rules_to_namespaced_tags ):
        
        # this guy gets called a lot, so we are making it an iterator
        
        yield tag
        
        ( namespace, subtag ) = SplitTag( tag )
        
        if tag != subtag and apply_unnamespaced_rules_to_namespaced_tags:
            
            yield subtag
            
        
        if namespace != '':
            
            yield '{}:'.format( namespace )
            yield ':'
            
        else:
            
            yield ''
            
        
    
    def _GetSerialisableInfo( self ):
        
        return list( self._tag_slices_to_rules.items() )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._tag_slices_to_rules = dict( serialisable_info )
        
        self._UpdateRuleCache()
        
    
    def _TagOK( self, tag, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        # old method, has a bunch of overhead due to iteration
        '''
        blacklist_encountered = False
        
        for tag_slice in self._IterateTagSlices( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags ):
            
            if tag_slice in self._tag_slices_to_rules:
                
                rule = self._tag_slices_to_rules[ tag_slice ]
                
                if rule == HC.FILTER_WHITELIST:
                    
                    return True # there is an exception for this class of tag
                    
                elif rule == HC.FILTER_BLACKLIST: # there is a rule against this class of tag
                    
                    blacklist_encountered = True
                    
                
            
        
        if blacklist_encountered: # rule against and no exceptions
            
            return False
            
        else:
            
            return True # no rules against or explicitly for, so permitted
            
        '''
        
        #
        
        # since this is called a whole bunch and overhead piles up, we are now splaying the logic out to hardcoded tests
        
        blacklist_encountered = False
        
        if self._tags_interesting:
            
            if tag in self._tags_whitelist:
                
                return True
                
            
            if tag in self._tags_blacklist:
                
                blacklist_encountered = True
                
            
        
        if self._namespaced_interesting or apply_unnamespaced_rules_to_namespaced_tags:
            
            ( namespace, subtag ) = SplitTag( tag )
            
            if apply_unnamespaced_rules_to_namespaced_tags and self._tags_interesting and subtag != tag:
                
                if subtag in self._tags_whitelist:
                    
                    return True
                    
                
                if subtag in self._tags_blacklist:
                    
                    blacklist_encountered = True
                    
                
            
            if self._namespaced_interesting:
                
                if namespace == '':
                    
                    if self._all_unnamespaced_whitelisted:
                        
                        return True
                        
                    
                    if self._all_unnamespaced_blacklisted:
                        
                        blacklist_encountered = True
                        
                    
                else:
                    
                    if self._all_namespaced_whitelisted or namespace in self._namespaces_whitelist:
                        
                        return True
                        
                    
                    if self._all_namespaced_blacklisted or namespace in self._namespaces_blacklist:
                        
                        blacklist_encountered = True
                        
                    
                
            
        
        if blacklist_encountered: # rule against and no exceptions
            
            return False
            
        else:
            
            return True # no rules against or explicitly for, so permitted
            
        
    
    def _UpdateRuleCache( self ):
        
        self._all_unnamespaced_whitelisted = False
        self._all_namespaced_whitelisted = False
        self._namespaces_whitelist = set()
        self._tags_whitelist = set()
        
        self._all_unnamespaced_blacklisted = False
        self._all_namespaced_blacklisted = False
        self._namespaces_blacklist = set()
        self._tags_blacklist = set()
        
        self._namespaced_interesting = False
        self._tags_interesting = False
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if tag_slice == '':
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._all_unnamespaced_whitelisted = True
                    
                else:
                    
                    self._all_unnamespaced_blacklisted = True
                    
                
                self._namespaced_interesting = True
                
            elif tag_slice == ':':
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._all_namespaced_whitelisted = True
                    
                else:
                    
                    self._all_namespaced_blacklisted = True
                    
                
                self._namespaced_interesting = True
                
            elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._namespaces_whitelist.add( tag_slice[:-1] )
                    
                else:
                    
                    self._namespaces_blacklist.add( tag_slice[:-1] )
                    
                
                self._namespaced_interesting = True
                
            else:
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._tags_whitelist.add( tag_slice )
                    
                else:
                    
                    self._tags_blacklist.add( tag_slice )
                    
                
                self._tags_interesting = True
                
            
        
    
    def AllowsEverything( self ):
        
        with self._lock:
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == HC.FILTER_BLACKLIST:
                    
                    return False
                    
                
            
            return True
            
        
    
    def CleanRules( self ):
        
        new_tag_slices_to_rules = {}
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if tag_slice == '':
                
                pass
                
            elif tag_slice == ':':
                
                pass
                
            elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
                
                example_tag = tag_slice + 'example'
                
                try:
                    
                    clean_example_tag = CleanTag( example_tag )
                    
                except:
                    
                    continue
                    
                
                tag_slice = clean_example_tag[:-7]
                
            else:
                
                tag = tag_slice
                
                try:
                    
                    clean_tag = CleanTag( tag )
                    
                except:
                    
                    continue
                    
                
                tag_slice = clean_tag
                
            
            new_tag_slices_to_rules[ tag_slice ] = rule
            
        
        self._tag_slices_to_rules = new_tag_slices_to_rules
        
        self._UpdateRuleCache()
        
    
    def Filter( self, tags, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        with self._lock:
            
            return { tag for tag in tags if self._TagOK( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags ) }
            
        
    
    def GetTagSlicesToRules( self ):
        
        with self._lock:
            
            return dict( self._tag_slices_to_rules )
            
        
    
    def SetRule( self, tag_slice, rule ):
        
        with self._lock:
            
            self._tag_slices_to_rules[ tag_slice ] = rule
            
            self._UpdateRuleCache()
            
        
    
    def TagOK( self, tag, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        with self._lock:
            
            return self._TagOK( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags )
            
        
    
    def ToBlacklistString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == HC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == HC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'no blacklist set'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    text = 'blacklisting on any tags'
                    
                else:
                    
                    text = 'blacklisting on ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                    
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
                return text
                
            
        
    
    def ToCensoredString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in list(self._tag_slices_to_rules.items()):
                
                if rule == HC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == HC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'all tags allowed'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    text = 'no tags allowed'
                    
                else:
                    
                    text = 'all but ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) ) + ' allowed'
                    
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
                return text
                
            
        
    
    def ToPermittedString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in list(self._tag_slices_to_rules.items()):
                
                if rule == HC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == HC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'all tags'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    if len( whitelist ) == 0:
                        
                        text = 'no tags'
                        
                    else:
                        
                        text = 'only ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                elif set( blacklist ) == { '' }:
                    
                    text = 'all namespaced tags'
                    
                    if len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                elif set( blacklist ) == { ':' }:
                    
                    text = 'all unnamespaced tags'
                    
                    if len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                else:
                    
                    text = 'all tags except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                    
                    if len( whitelist ) > 0:
                        
                        text += ' (except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) ) + ')'
                        
                    
                
            
            return text
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER ] = TagFilter

