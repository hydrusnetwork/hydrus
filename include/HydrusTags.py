import collections
from . import HydrusConstants as HC
import itertools
import os
import threading
import time
import traceback
from . import HydrusData
from . import HydrusExceptions
import re
from . import HydrusGlobals as HG
from . import HydrusText

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
        
        raise HydrusExceptions.SizeException( 'Received a zero-length tag!' )
        
    
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
            
        except HydrusExceptions.SizeException:
            
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
        
    
def SplitTag( tag ):
    
    if ':' in tag:
        
        return tag.split( ':', 1 )
        
    else:
        
        return ( '', tag )
        
    
def StripTextOfGumpf( t ):
    
    t = HydrusText.re_newlines.sub( '', t )
    
    t = HydrusText.re_multiple_spaces.sub( ' ', t )
    
    t = t.strip()
    
    t = HydrusText.re_leading_space_or_garbage.sub( '', t )
    
    return t
    
