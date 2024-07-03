def ConvertIndexToPrettyOrdinalString( index: int ):
    
    if index >= 0:
        
        return ConvertIntToPrettyOrdinalString( index + 1 )
        
    else:
        
        return ConvertIntToPrettyOrdinalString( index )
        
    

def ConvertIntToPrettyOrdinalString( num: int ):
    
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
    

def ToHumanInt( num ):
    
    num = int( num )
    
    # this got stomped on by mpv, which resets locale
    #text = locale.format_string( '%d', num, grouping = True )
    
    text = '{:,}'.format( num )
    
    return text
    
