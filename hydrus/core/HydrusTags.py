import collections
import collections.abc
import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusText

def CollapseMultipleSortedNumericTagsToMinMax( tags ):
    
    if len( tags ) <= 2:
        
        return tags
        
    else:
        
        includes_non_numeric_tag = False in ( tag.isdecimal() for tag in tags )
        
        if includes_non_numeric_tag:
            
            return tags
            
        else:
            
            # this list of tags is entirely numeric and may well be something like 1, 2, 3, 4, 5
            # the caller wants to present 1-5 instead, so lets cut out the first and last
            
            if not isinstance( tags, list ):
                
                tags = list( tags )
                
            
            return [ tags[0], tags[-1] ]
            
        
    

def FilterNamespaces( tags, namespaces ):
    
    processed_tags = collections.defaultdict( set )
    
    for tag in tags:
        
        ( namespace, subtag ) = SplitTag( tag )
        
        processed_tags[ namespace ].add( tag )
        
    
    result = set()
    
    for namespace in namespaces:
        
        if namespace is None:
            
            result.update( processed_tags[ '' ] )
            
        else:
            
            result.update( processed_tags[ namespace ] )
            
        
    
    return result
    

def SortNumericTags( tags ):
    
    tags = list( tags )
    
    tags.sort( key = HydrusText.HumanTextSortKey )
    
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
        
        if HydrusText.re_leading_single_colon_and_no_more_colons.match( tag ) is not None:
            
            # Convert anything starting with one colon to start with two i.e. :D -> ::D
            # but don't do :weird:stuff, which is a forced unnamespaced tag that includes a colon in the subtag
            tag = ':' + tag
            
        
        if ':' in tag:
            
            tag = StripTagTextOfGumpf( tag ) # need to repeat here to catch 'system:' stuff
            
            ( namespace, subtag ) = SplitTag( tag )
            
            namespace = StripTagTextOfGumpf( namespace )
            subtag = StripTagTextOfGumpf( subtag )
            
            tag = CombineTag( namespace, subtag )
            
        else:
            
            tag = StripTagTextOfGumpf( tag )
            
        
    except Exception as e:
        
        text = 'Was unable to parse the tag: ' + str( tag )
        text += '\n' * 2
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
    

def CombineTag( namespace, subtag ) -> str:
    
    if namespace == '':
        
        if ':' in subtag:
            
            return ':' + subtag
            
        else:
            
            return subtag
            
        
    else:
        
        return namespace + ':' + subtag
        
    

def ConvertTagSliceToPrettyString( tag_slice ):
    
    if tag_slice == '':
        
        return 'unnamespaced tags'
        
    elif tag_slice == ':':
        
        return 'namespaced tags'
        
    elif IsNamespaceTagSlice( tag_slice ):
        
        namespace = tag_slice[ : -1 ]
        
        return '\'' + namespace + '\' tags'
        
    else:
        
        return tag_slice
        
    

def ConvertUglyNamespaceToPrettyString( namespace ):
    
    if namespace is None or namespace == '':
        
        return 'no namespace'
        
    else:
        
        return namespace
        
    

def ConvertUglyNamespacesToPrettyStrings( namespaces ):
    
    namespaces = sorted( namespaces )
    
    result = [ ConvertUglyNamespaceToPrettyString( namespace ) for namespace in namespaces ]
    
    return result
    

ALL_UNNAMESPACED_TAG_SLICE = ''
ALL_NAMESPACED_TAG_SLICE = ':'

CORE_TAG_SLICES = { ALL_UNNAMESPACED_TAG_SLICE, ALL_NAMESPACED_TAG_SLICE }

def IsNamespaceTagSlice( tag_slice: str ):
    
    # careful about the [-1] here! it works, but only because of the '' check in core_tag_slices
    return tag_slice not in CORE_TAG_SLICES and tag_slice[-1] == ':' and tag_slice.count( ':' ) == 1
    

def IsUnnamespaced( tag ):
    
    return SplitTag( tag )[0] == ''
    

def SplitTag( tag ):
    
    if ':' in tag:
        
        return tuple( tag.split( ':', 1 ) )
        
    else:
        
        return ( '', tag )
        
    

def StripTagTextOfGumpf( t ):
    
    t = HydrusText.re_undesired_control_characters.sub( '', t )
    
    t = HydrusText.re_one_or_more_whitespace.sub( ' ', t )
    
    t = t.strip()
    
    t = HydrusText.re_leading_garbage.sub( '', t )
    
    t = t.strip()
    
    if HydrusText.re_looks_like_hangul.search( t ) is None: # if we ain't korean, get that thing out of here
        
        t = t.replace( HydrusText.HANGUL_FILLER_CHARACTER, '' )
        
    
    if HydrusText.re_this_is_all_latin_and_zero_width.match( t ) is not None: # if we are "blue_eyes[ZWNJ]", get it out of here
        
        t = HydrusText.re_zero_width_joiners.sub( '', t )
        
    
    t = HydrusText.re_oops_all_zero_width_joiners.sub( '', t )
    
    t = HydrusText.re_one_or_more_whitespace.sub( ' ', t )
    
    t = t.strip()
    
    return t
    

def TagOK( t ):
    
    try:
        
        CheckTagNotEmpty( CleanTag( t ) )
        
        return True
        
    except Exception as e:
        
        return False
        
    
class TagFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Tag Filter Rules'
    SERIALISABLE_VERSION = 1
    
    WOAH_TOO_MANY_RULES_THRESHOLD = 12
    
    def __init__( self ):
        
        super().__init__()
        
        # TODO: update this guy to more carefully navigate how it does advanced filters
        # we want to support both:
            # "all namespaces, except blocking creator:, but allowing creator:yo"
            # "no namespaces, except allowing creator:, but still blocking creator:yo"
        # the 'all namespaces' applies first, then namespaces, then tags
        # I updated _TagOK to basically reflect this, but these cached values and whether the 'all' white/blacklist rule actually exists or is implicit is all fuzzy, so clean it up!
        # also the UI should display this properly, atm it just does Case 1
        
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
        
        self._namespaces_interesting = False
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
        
        # this is called a whole bunch and overhead piles up, so try to splay the logic out to hardcoded tests
        # we handle exceptions by testing tags before namespaces and namespaces before all namespaces
        
        if self._tags_interesting:
            
            if tag in self._tags_whitelist:
                
                return True
                
            
            if tag in self._tags_blacklist:
                
                return False
                
            
            if apply_unnamespaced_rules_to_namespaced_tags:
                
                ( namespace, subtag ) = SplitTag( tag )
                
                if namespace != '':
                    
                    if subtag in self._tags_whitelist:
                        
                        return True
                        
                    
                    if subtag in self._tags_blacklist:
                        
                        return False
                        
                    
                
            
        
        if self._namespaces_interesting:
            
            ( namespace, subtag ) = SplitTag( tag )
            
            if namespace == '':
                
                if self._all_unnamespaced_whitelisted:
                    
                    return True
                    
                
                if self._all_unnamespaced_blacklisted:
                    
                    return False
                    
                
            else:
                
                if namespace in self._namespaces_whitelist:
                    
                    return True
                    
                
                if namespace in self._namespaces_blacklist:
                    
                    return False
                    
                
                if self._all_namespaced_whitelisted:
                    
                    return True
                    
                
                if self._all_namespaced_blacklisted:
                    
                    return False
                    
                
            
        
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
        
        self._namespaces_interesting = False
        self._tags_interesting = False
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if tag_slice == '':
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._all_unnamespaced_whitelisted = True
                    
                else:
                    
                    self._all_unnamespaced_blacklisted = True
                    
                
                self._namespaces_interesting = True # yes, the namespace of a tag matters to the outcome
                
            elif tag_slice == ':':
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._all_namespaced_whitelisted = True
                    
                else:
                    
                    self._all_namespaced_blacklisted = True
                    
                
                self._namespaces_interesting = True # yes, the namespace of a tag matters to the outcome
                
            elif IsNamespaceTagSlice( tag_slice ):
                
                if rule == HC.FILTER_WHITELIST:
                    
                    self._namespaces_whitelist.add( tag_slice[:-1] )
                    
                else:
                    
                    self._namespaces_blacklist.add( tag_slice[:-1] )
                    
                
                self._namespaces_interesting = True
                
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
                
            elif IsNamespaceTagSlice( tag_slice ):
                
                example_tag = tag_slice + 'example'
                
                try:
                    
                    clean_example_tag = CleanTag( example_tag )
                    
                except Exception as e:
                    
                    continue
                    
                
                tag_slice = clean_example_tag[:-7]
                
            else:
                
                tag = tag_slice
                
                try:
                    
                    clean_tag = CleanTag( tag )
                    
                except Exception as e:
                    
                    continue
                    
                
                tag_slice = clean_tag
                
            
            new_tag_slices_to_rules[ tag_slice ] = rule
            
        
        self._tag_slices_to_rules = new_tag_slices_to_rules
        
        self._UpdateRuleCache()
        
    
    def Filter( self, tags, apply_unnamespaced_rules_to_namespaced_tags = False ):
        
        with self._lock:
            
            return { tag for tag in tags if self._TagOK( tag, apply_unnamespaced_rules_to_namespaced_tags = apply_unnamespaced_rules_to_namespaced_tags ) }
            
        
    
    def GetChanges( self, old_tag_filter: "TagFilter" ):
        
        old_slices_to_rules = old_tag_filter.GetTagSlicesToRules()
        
        new_rules = [ ( slice, rule ) for ( slice, rule ) in self._tag_slices_to_rules.items() if slice not in old_slices_to_rules ]
        changed_rules = [ ( slice, rule ) for ( slice, rule ) in self._tag_slices_to_rules.items() if slice in old_slices_to_rules and rule != old_slices_to_rules[ slice ] ]
        deleted_rules = [ ( slice, rule ) for ( slice, rule ) in old_slices_to_rules.items() if slice not in self._tag_slices_to_rules ]
        
        return ( new_rules, changed_rules, deleted_rules )
        
    
    def GetChangesSummaryText( self, old_tag_filter: "TagFilter" ):
        
        ( new_rules, changed_rules, deleted_rules ) = self.GetChanges( old_tag_filter )
        
        summary_components = []
        
        if len( new_rules ) > 0:
            
            if len( new_rules ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                
                summary_components.append( 'Added {} rules'.format( HydrusNumbers.ToHumanInt( len( new_rules ) ) ) )
                
            else:
                
                rows = [ 'Added rule: {} - {}'.format( HC.filter_black_white_str_lookup[ rule ], ConvertTagSliceToPrettyString( slice ) ) for ( slice, rule ) in new_rules ]
                
                summary_components.append( '\n'.join( rows ) )
                
            
        
        if len( changed_rules ) > 0:
            
            if len( new_rules ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                
                summary_components.append( 'Changed {} rules'.format( HydrusNumbers.ToHumanInt( len( new_rules ) ) ) )
                
            else:
                
                rows = [ 'Flipped rule: to {} - {}'.format( HC.filter_black_white_str_lookup[ rule ], ConvertTagSliceToPrettyString( slice ) ) for ( slice, rule ) in changed_rules ]
                
                summary_components.append( '\n'.join( rows ) )
                
            
        
        if len( deleted_rules ) > 0:
            
            if len( new_rules ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                
                summary_components.append( 'Deleted {} rules'.format( HydrusNumbers.ToHumanInt( len( new_rules ) ) ) )
                
            else:
                
                rows = [ 'Deleted rule: {} - {}'.format( HC.filter_black_white_str_lookup[ rule ], ConvertTagSliceToPrettyString( slice ) ) for ( slice, rule ) in deleted_rules ]
                
                summary_components.append( '\n'.join( rows ) )
                
            
        
        return '\n'.join( summary_components )
        
    
    def GetInvertedFilter( self ) -> "TagFilter":
        
        inverted_tag_filter = TagFilter()
        
        if '' not in self._tag_slices_to_rules:
            
            inverted_tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
            
        
        if ':' not in self._tag_slices_to_rules:
            
            inverted_tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
            
        
        inverted_tag_filter.SetRules( [ tag_slice for ( tag_slice, rule ) in self._tag_slices_to_rules.items() if rule == HC.FILTER_BLACKLIST ], HC.FILTER_WHITELIST )
        inverted_tag_filter.SetRules( [ tag_slice for ( tag_slice, rule ) in self._tag_slices_to_rules.items() if rule == HC.FILTER_WHITELIST ], HC.FILTER_BLACKLIST )
        
        return inverted_tag_filter
        
    
    def GetTagSlicesToRules( self ):
        
        with self._lock:
            
            return dict( self._tag_slices_to_rules )
            
        
    
    def SetRule( self, tag_slice, rule ):
        
        self.SetRules( ( tag_slice, ), rule )
        
    
    def SetRules( self, tag_slices, rule ):
        
        with self._lock:
            
            for tag_slice in tag_slices:
                
                self._tag_slices_to_rules[ tag_slice ] = rule
                
            
            # TODO: do a thing here that says 'if we have a whitelist rule for something that would be allowed without the exception, then remove the whitelist'
            # maybe in the updaterulecache, purgesurpluswhitelist, something like that
            # and figure out how we _actually_ want to do ''/':' whitelist/blacklist
            
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
                    
                    if len( blacklist ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                        
                        text = 'blacklisting on {} rules'.format( HydrusNumbers.ToHumanInt( len( blacklist ) ) )
                        
                    else:
                        
                        text = 'blacklisting on ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in blacklist ) )
                        
                    
                
                if len( whitelist ) > 0:
                    
                    if len( whitelist ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                        
                        text += ' except {} other rules'.format( HydrusNumbers.ToHumanInt( len( whitelist ) ) )
                        
                    else:
                        
                        text += ' except ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                
                return text
                
            
        
    
    def ToPermittedString( self ):
        
        # TODO: Could make use of a modified version of the new `HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine()` here, rather than WOAH_TOO_MANY_RULES_THRESHOLD
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == HC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == HC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist_set = set( blacklist )
            functional_blacklist_set = blacklist_set.difference( { '', ':' } )
            
            whitelist_set = set( whitelist )
            functional_whitelist_set = whitelist_set.difference( { '', ':' } )
            
            if len( blacklist ) == 0:
                
                return 'allowing all tags'
                
            else:
                
                if blacklist_set.issuperset( { '', ':' } ):
                    
                    if len( whitelist ) == 0:
                        
                        text = 'not allowing any tags'
                        
                    else:
                        
                        if len( whitelist ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                            
                            text = 'only allowing on {} rules'.format( HydrusNumbers.ToHumanInt( len( whitelist ) ) )
                            
                        else:
                            
                            text = 'only allowing ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in sorted( whitelist ) ) )
                            
                        
                        if len( functional_blacklist_set ) > 0:
                            
                            if len( functional_blacklist_set ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                                
                                text += ' while still disllowing {} rules'.format( HydrusNumbers.ToHumanInt( len( functional_blacklist_set ) ) )
                                
                            else:
                                
                                text += ' while still disallowing ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in sorted( functional_blacklist_set ) ) )
                                
                            
                        
                    
                elif '' in blacklist_set or ':' in blacklist_set:
                    
                    if '' in blacklist_set:
                        
                        text = 'allowing all namespaced tags'
                        
                    else:
                        
                        text = 'allowing all unnamespaced tags'
                        
                    
                    if len( whitelist ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                        
                        text += ' and {} other rules'.format( HydrusNumbers.ToHumanInt( len( functional_whitelist_set ) ) )
                        
                    elif len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in sorted( functional_whitelist_set ) ) )
                        
                    
                    if len( functional_blacklist_set ) > 0:
                        
                        if len( functional_blacklist_set ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                            
                            text += ' while still disllowing {} rules'.format( HydrusNumbers.ToHumanInt( len( functional_blacklist_set ) ) )
                            
                        else:
                            
                            text += ' while still disallowing ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in sorted( functional_blacklist_set ) ) )
                            
                        
                    
                else:
                    
                    if len( blacklist ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                        
                        text = 'allowing all tags except on {} rules'.format( HydrusNumbers.ToHumanInt( len( blacklist ) ) )
                        
                    else:
                        
                        text = 'allowing all tags except ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in sorted( blacklist ) ) )
                        
                    
                    if len( functional_whitelist_set ) > self.WOAH_TOO_MANY_RULES_THRESHOLD:
                        
                        text += ' while still allowing {} rules'.format( HydrusNumbers.ToHumanInt( len( functional_whitelist_set ) ) )
                        
                    elif len( functional_whitelist_set ) > 0:
                        
                        text += ' while still allowing ' + ', '.join( ( ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in sorted( functional_whitelist_set ) ) )
                        
                    
                
            
            return text
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER ] = TagFilter

