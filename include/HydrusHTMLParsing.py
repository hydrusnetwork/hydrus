import bs4
import HydrusSerialisable

class ParseFormula( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HTML_PARSE_FORMULA
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        self._tag_rules = []
        
        self._content_rule = None
        
    
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
        
    
    def IsValid( self ):
        
        return len( self._tag_rules ) > 0 and self._content_rule is not None
        
    
    def PopTagsRule( self ):
        
        self._tag_rules.pop()
        
    
    def PushTagsRule( self, name = None, attrs = {}, index = None ):
        
        self._tag_rules.append( ( name, attrs, index ) )
        
    
    def Duplicate( self ):
        
        new_formula = ParseFormula()
        
        for ( name, attrs, index ) in self._tag_rules:
            
            new_formula.PushTagsRule( name, dict( attrs ), index )
            
        
        new_formula.SetContentRule( self._content_rule )
        
        return new_formula
        
    
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
        
    
    def SetContentRule( self, attr = None ):
        
        self._content_rule = attr
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HTML_PARSE_FORMULA ] = ParseFormula