import bs4
import HydrusData
import HydrusSerialisable

def RenderTagRule( ( name, attrs, index ) ):
    
    if index is None:
        
        result = 'all ' + name + ' tags'
        
    else:
        
        result = HydrusData.ConvertIntToFirst( index + 1 ) + name + ' tag'
        
    
    if len( attrs ) > 0:
        
        result += ' with ' + ' and '.join( [ key + ' = ' + value for ( key, value ) in attrs.items() ] )
        
    
    return result
    
class ParseFormula( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HTML_PARSE_FORMULA
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
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HTML_PARSE_FORMULA ] = ParseFormula