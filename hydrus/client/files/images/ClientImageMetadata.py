from PIL import Image as PILImage
from PIL import IptcImagePlugin

from hydrus.core import HydrusText

# this big dict brought to you by ChatGPT, which grunked this whole https://www.iptc.org/std/IIM/4.2/specification/IIMV4.2.pdf for me
iptc_tuple_int_enums_to_strs_lookup = {
    # Record 1: Envelope Record
    (1, 0): "Model Version",
    (1, 5): "Destination",
    (1, 20): "File Format",
    (1, 22): "File Format Version",
    (1, 30): "Service Identifier",
    (1, 40): "Envelope Number",
    (1, 50): "Product I.D.",
    (1, 60): "Envelope Priority",
    (1, 70): "Date Sent",
    (1, 80): "Time Sent",
    (1, 90): "Coded Character Set",
    (1, 100): "UNO",
    (1, 120): "ARM Identifier",
    (1, 122): "ARM Version",

    # Record 2: Application Record
    (2, 0): "Record Version",
    (2, 3): "Object Type Reference",
    (2, 4): "Object Attribute Reference",
    (2, 5): "Object Name",
    (2, 7): "Edit Status",
    (2, 8): "Editorial Update",
    (2, 10): "Urgency",
    (2, 12): "Subject Reference",
    (2, 15): "Category",
    (2, 20): "Supplemental Category",
    (2, 22): "Fixture Identifier",
    (2, 25): "Keywords",
    (2, 26): "Content Location Code",
    (2, 27): "Content Location Name",
    (2, 30): "Release Date",
    (2, 35): "Release Time",
    (2, 37): "Expiration Date",
    (2, 38): "Expiration Time",
    (2, 40): "Special Instructions",
    (2, 42): "Action Advised",
    (2, 45): "Reference Service",
    (2, 47): "Reference Date",
    (2, 50): "Reference Number",
    (2, 55): "Date Created",
    (2, 60): "Time Created",
    (2, 62): "Digital Creation Date",
    (2, 63): "Digital Creation Time",
    (2, 65): "Originating Program",
    (2, 70): "Program Version",
    (2, 75): "Object Cycle",
    (2, 80): "By-line",
    (2, 85): "By-line Title",
    (2, 90): "City",
    (2, 92): "Sub-location",
    (2, 95): "Province/State",
    (2, 100): "Country/Primary Location Code",
    (2, 101): "Country/Primary Location Name",
    (2, 103): "Original Transmission Reference",
    (2, 105): "Headline",
    (2, 110): "Credit",
    (2, 115): "Source",
    (2, 116): "Copyright Notice",
    (2, 118): "Contact",
    (2, 120): "Caption/Abstract",
    (2, 122): "Writer/Editor",
    (2, 125): "Rasterized Caption",
    (2, 130): "Image Type",
    (2, 131): "Image Orientation",
    (2, 135): "Language Identifier",
    (2, 150): "Audio Type",
    (2, 151): "Audio Sampling Rate",
    (2, 152): "Audio Sampling Resolution",
    (2, 153): "Audio Duration",
    (2, 154): "Audio Outcue",
    (2, 200): "ObjectData Preview File Format",
    (2, 201): "ObjectData Preview File Format Version",
    (2, 202): "ObjectData Preview Data",

    # Record 7: Pre-ObjectData Descriptor Record
    (7, 10): "Size Mode",
    (7, 20): "Max Subfile Size",
    (7, 90): "ObjectData Size Announced",
    (7, 95): "Maximum ObjectData Size",

    # Record 8: ObjectData Record
    (8, 10): "Subfile",

    # Record 9: Post-ObjectData Descriptor Record
    (9, 10): "Confirmed ObjectData Size",
}

iptc_tuple_int_enums_we_want_to_show_to_the_user = {
    (1, 70), # "Date Sent",
    (1, 80), # "Time Sent",
    (1, 100), # "UNO",

    (2, 3), # "Object Type Reference",
    (2, 4), # "Object Attribute Reference",
    (2, 5), # "Object Name",
    (2, 7), # "Edit Status",
    (2, 8), # "Editorial Update",
    (2, 10), # "Urgency",
    (2, 12), # "Subject Reference",
    (2, 15), # "Category",
    (2, 20), # "Supplemental Category",
    (2, 22), # "Fixture Identifier",
    (2, 25), # "Keywords",
    (2, 26), # "Content Location Code",
    (2, 27), # "Content Location Name",
    (2, 30), # "Release Date",
    (2, 35), # "Release Time",
    (2, 37), # "Expiration Date",
    (2, 38), # "Expiration Time",
    (2, 40), # "Special Instructions",
    (2, 42), # "Action Advised",
    (2, 45), # "Reference Service",
    (2, 47), # "Reference Date",
    (2, 50), # "Reference Number",
    (2, 55), # "Date Created",
    (2, 60), # "Time Created",
    (2, 62), # "Digital Creation Date",
    (2, 63), # "Digital Creation Time",
    (2, 65), # "Originating Program",
    (2, 70), # "Program Version",
    (2, 75), # "Object Cycle",
    (2, 80), # "By-line",
    (2, 85), # "By-line Title",
    (2, 90), # "City",
    (2, 92), # "Sub-location",
    (2, 95), # "Province/State",
    (2, 100), # "Country/Primary Location Code",
    (2, 101), # "Country/Primary Location Name",
    (2, 103), # "Original Transmission Reference",
    (2, 105), # "Headline",
    (2, 110), # "Credit",
    (2, 115), # "Source",
    (2, 116), # "Copyright Notice",
    (2, 118), # "Contact",
    (2, 120), # "Caption/Abstract",
    (2, 122), # "Writer/Editor",
    (2, 125), # "Rasterized Caption",
    (2, 130), # "Image Type",
    (2, 131), # "Image Orientation",
    (2, 135), # "Language Identifier",
    (2, 150), # "Audio Type",
    (2, 151), # "Audio Sampling Rate",
    (2, 152), # "Audio Sampling Resolution",
    (2, 153), # "Audio Duration",
    (2, 154), # "Audio Outcue",
    (2, 200), # "ObjectData Preview File Format",
    (2, 201), # "ObjectData Preview File Format Version",
    (2, 202), # "ObjectData Preview Data",
}

def GetIPTCDict( pil_image: PILImage.Image ) -> dict | None:
    
    try:
        
        raw_iptc_dict = IptcImagePlugin.getiptcinfo( pil_image )
        
        def bytes_value_to_clean_string( b: bytes ):
            
            try:
                
                # ok sometimes this guy is utf-8, but it can other things hooray!! the ( 1, 90 ), 'Coded Character Set' specifies it otherwise
                # best practical solution is to try ur best
                ( clean_value, likely_encoding ) = HydrusText.NonFailingUnicodeDecode( b, 'utf-8' )
                
            except Exception as e:
                
                clean_value = f'weird encoding: {b}'
                
            
            return clean_value
            
        
        # this is an ugly two-variable-tuple-key-to-bytes dict like this:
        # ( 2, 25 ) : [ b'blah', b'blahblah' ],
        # which we may wish to build a nicer label lookup for and such, but let's just get it on screen for now
        
        clean_result = {}
        
        for ( key_tuple, bytes_or_bytes_list ) in raw_iptc_dict.items():
            
            if key_tuple not in iptc_tuple_int_enums_we_want_to_show_to_the_user:
                
                continue
                
            
            if isinstance( bytes_or_bytes_list, bytes ):
                
                clean_value = bytes_value_to_clean_string( bytes_or_bytes_list )
                
            elif isinstance( bytes_or_bytes_list, list ):
                
                clean_value = str( [ bytes_value_to_clean_string( by ) for by in bytes_or_bytes_list ] )
                
            else:
                
                clean_value = f'unknown IPTC value type: {bytes_or_bytes_list}'
                
            
            clean_value = clean_value.strip()
            
            if clean_value == '':
                
                continue
                
            
            if key_tuple in iptc_tuple_int_enums_to_strs_lookup:
                
                clean_key = iptc_tuple_int_enums_to_strs_lookup[ key_tuple ]
                
            else:
                
                clean_key = f'Unknown {key_tuple}'
                
            
            clean_result[ clean_key ] = clean_value
            
        
        if len( clean_result ) == 0:
            
            return None
            
        
        return clean_result
        
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
            
            try:
                
                root = ClientParsing.GetSoup( xmp_data, force_parser = 'xml' )
                
            except Exception as e:
                
                root = ClientParsing.GetSoup( xmp_data )
                
            
            def get_name( node: bs4.element.Tag ) -> str:
                
                # Pillow removes namespace with regex. maybe that's nice? one assumes a user who wants XMP wants the full course, though
                return str( node.name )
                
            
            def get_value( node: bs4.element.Tag ) -> str | dict | None:
                
                attribute_dict = {}
                
                for ( key, value ) in node.attrs.items():
                    
                    if isinstance( value, bs4.element.AttributeValueList ):
                        
                        value = [ v.strip() for v in value ]
                        
                        value = [ v for v in value if v != '' ]
                        
                        if len( value ) == 0:
                            
                            continue
                            
                        
                    else:
                        
                        value = str( value ).strip()
                        
                        if value == '':
                            
                            continue
                            
                        
                    
                    attribute_dict[ key ] = value
                    
                
                children = [ n for n in node.children if isinstance( n, bs4.element.Tag ) ]
                
                if len( list( children ) ) > 0:
                    
                    for child in children:
                        
                        key = get_name( child )
                        
                        value = get_value( child )
                        
                        if isinstance( value, str ) and value == '':
                            
                            continue
                            
                        elif isinstance( value, dict ) and len( value ) == 0:
                            
                            continue
                            
                        
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
    
