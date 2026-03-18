import collections.abc

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

class TagFilteringImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTERING_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Tag Filtering Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__(
        self,
        tag_blacklist = None,
        tag_whitelist = None,
    ):
        
        super().__init__()
        
        if tag_blacklist is None:
            
            tag_blacklist = HydrusTags.TagFilter()
            
        
        if tag_whitelist is None:
            
            tag_whitelist = []
            
        
        self._tag_blacklist = tag_blacklist
        self._tag_whitelist = tag_whitelist
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_tag_blacklist = self._tag_blacklist.GetSerialisableTuple()
        
        return ( serialisable_tag_blacklist, self._tag_whitelist )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_tag_blacklist, self._tag_whitelist ) = serialisable_info
        
        self._tag_blacklist = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_blacklist )
        
    
    def CheckTagsVeto( self, tags: collections.abc.Collection[ str ], sibling_tags: collections.abc.Collection[ str ] ):
        
        tags = set( tags )
        
        sibling_tags = set( sibling_tags )
        
        for test_tags in ( tags, sibling_tags ):
            
            ok_tags = self._tag_blacklist.Filter( test_tags, apply_unnamespaced_rules_to_namespaced_tags = True )
            
            if len( ok_tags ) < len( test_tags ):
                
                bad_tags = test_tags.difference( ok_tags )
                
                bad_tags = HydrusTags.SortNumericTags( bad_tags )
                
                raise HydrusExceptions.VetoException( ', '.join( bad_tags ) + ' is blacklisted!' )
                
            
        
        if len( self._tag_whitelist ) > 0:
            
            all_tags = tags.union( sibling_tags )
            
            for tag in list( all_tags ):
                
                ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                
                all_tags.add( subtag )
                
            
            intersecting_tags = all_tags.intersection( self._tag_whitelist )
            
            if len( intersecting_tags ) == 0:
                
                raise HydrusExceptions.VetoException( 'did not pass the whitelist!' )
                
            
        
    
    def GetSummary( self, show_downloader_options: bool = True ):
        
        statements = []
        
        if show_downloader_options:
            
            statements.append( self._tag_blacklist.ToBlacklistString() )
            
            if len( self._tag_whitelist ) > 0:
                
                statements.append( 'tag whitelist: ' + ', '.join( self._tag_whitelist ) )
                
            
        
        summary = '\n'.join( statements )
        
        return summary
        
    
    def GetTagBlacklist( self ):
        
        return self._tag_blacklist
        
    
    def GetTagWhitelist( self ):
        
        return self._tag_whitelist
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTERING_IMPORT_OPTIONS ] = TagFilteringImportOptions
