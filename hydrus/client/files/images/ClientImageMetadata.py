from PIL import Image as PILImage
from PIL import IptcImagePlugin

def GetIPTCDict( pil_image: PILImage.Image ) -> dict | None:
    
    try:
        
        iptc_dict = IptcImagePlugin.getiptcinfo( pil_image )
        
        # this is an ugly two-variable-tuple-key-to-bytes dict like this:
        # ( 2, 25 ) : [ b'blah', b'blahblah' ],
        # which we may wish to build a nicer label lookup for and such, but let's just get it on screen for now
        
        return { str( key ) : str( value ) for ( key, value ) in iptc_dict.items() }
        
    except Exception as e:
        
        pass
        
    
    return None
    

def GetXMPDict( pil_image: PILImage.Image ) -> dict | None:
    
    try:
        
        # note that pil_image.getxmp() does not work unless you have 'defusedxml' or whatever lib, so we just roll our own html solution that will def work 400%
        
        if 'xmp' in pil_image.info:
            
            xmp_data_bytes = pil_image.info[ 'xmp' ].rstrip(b"\x00 ")
            
            xmp_data = xmp_data_bytes.decode( 'utf-8' )
            
            import bs4
            from hydrus.client.parsing import ClientParsing
            
            root = ClientParsing.GetSoup( xmp_data )
            
            def get_name( node: bs4.element.Tag ) -> str:
                
                # Pillow removes namespace with regex. maybe that's nice? one assumes a user who wants XMP wants the full course, though
                return node.name
                
            
            def get_value( node: bs4.element.Tag ) -> str | dict | None:
                
                attribute_dict = {}
                
                for ( key, value ) in node.attrs.items():
                    
                    if isinstance( value, bs4.element.AttributeValueList ):
                        
                        value = list( value )
                        
                    
                    attribute_dict[ key ] = value
                    
                
                children = [ n for n in node.children if isinstance( n, bs4.element.Tag ) ]
                
                if len( list( children ) ) > 0:
                    
                    for child in children:
                        
                        key = get_name( child )
                        
                        value = get_value( child )
                        
                        attribute_dict[ key ] = value
                        
                    
                elif node.text is not None and node.text != '':
                    
                    attribute_dict[ 'text' ] = node.text
                    
                
                return attribute_dict
                
            
            xmp_dict = { get_name( root ) : get_value( root ) }
            
            return xmp_dict
            
        
    except Exception as e:
        
        pass
        
    
    return None
    

def HasIPTC( pil_image: PILImage.Image ) -> bool:
    
    try:
        
        result = GetIPTCDict( pil_image )
        
    except Exception as e:
        
        return False
        
    
    return result is not None
    

def HasXMP( pil_image: PILImage.Image ) -> bool:
    
    try:
        
        result = GetXMPDict( pil_image )
        
    except Exception as e:
        
        return False
        
    
    return result is not None
    
