import typing

class PrettyMediaResultInfoLine( object ):
    
    def __init__( self, text: str, interesting: bool, tooltip: typing.Optional[ str ] = None ):
        
        self.text = text
        self.interesting = interesting
        self.tooltip = tooltip if tooltip is not None else text
        
    
    def IsSubmenu( self ) -> bool:
        
        return False
        
    

class PrettyMediaResultInfoLinesSubmenu( PrettyMediaResultInfoLine ):
    
    def __init__( self, text: str, interesting: bool, sublines: typing.List[ PrettyMediaResultInfoLine ], tooltip: typing.Optional[ str ] = None ):
        
        super().__init__( text, interesting, tooltip = tooltip )
        
        self.sublines = sublines
        
    
    def IsSubmenu( self ) -> bool:
        
        return True
        
    
