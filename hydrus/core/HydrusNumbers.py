def FloatToPercentage( f, sf = 1 ):
    
    percent = f * 100
    
    if percent == int( percent ):
        
        return f'{int( percent )}%'
        
    else:
        
        # this actually works!
        return f'{percent:.{sf}f}%'
        
    

def IndexToPrettyOrdinalString( index: int ):
    
    if index >= 0:
        
        return IntToPrettyOrdinalString( index + 1 )
        
    else:
        
        return IntToPrettyOrdinalString( index )
        
    

def IntToPixels( i ):
    
    if i == 1: return 'pixels'
    elif i == 1000: return 'kilopixels'
    elif i == 1000000: return 'megapixels'
    else: return 'megapixels'
    

def IntToUnit( unit ):
    
    if unit == 1: return 'B'
    elif unit == 1024: return 'KB'
    elif unit == 1048576: return 'MB'
    elif unit == 1073741824: return 'GB'
    

def IntToPrettyOrdinalString( num: int ):
    
    if num == 0:
        
        return 'unknown position'
        
    
    tens = ( abs( num ) % 100 ) // 10
    
    if tens == 1:
        
        ordinal = 'th'
        
    else:
        
        remainder = abs( num ) % 10
        
        if remainder == 1:
            
            ordinal = 'st'
            
        elif remainder == 2:
            
            ordinal = 'nd'
            
        elif remainder == 3:
            
            ordinal = 'rd'
            
        else:
            
            ordinal = 'th'
            
        
    
    s = '{}{}'.format( ToHumanInt( abs( num ) ), ordinal )
    
    if num < 0:
        
        if num == -1:
            
            s = 'last'
            
        else:
            
            s = '{} from last'.format( s )
            
        
    
    return s
    

def PixelsToInt( unit ):
    
    if unit == 'pixels': return 1
    elif unit == 'kilopixels': return 1000
    elif unit == 'megapixels': return 1000000
    

def ToHumanInt( num ):
    
    try:
        
        num = int( num )
        
    except Exception as e:
        
        return 'unknown'
        
    
    # this got stomped on by mpv, which resets locale
    #text = locale.format_string( '%d', num, grouping = True )
    
    text = '{:,}'.format( num )
    
    return text
    

def UnitToInt( unit ):
    
    if unit == 'B': return 1
    elif unit == 'KB': return 1024
    elif unit == 'MB': return 1024 ** 2
    elif unit == 'GB': return 1024 ** 3
    elif unit == 'TB': return 1024 ** 4
    

def ValueRangeToPrettyString( value, range ):
    
    if value is not None and range is not None:
        
        value = min( value, range )
        
    
    return ToHumanInt( value ) + '/' + ToHumanInt( range )
    
