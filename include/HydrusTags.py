import collections
import HydrusConstants as HC
import itertools
import os
import threading
import time
import traceback
import HydrusData
import HydrusExceptions
import re
import HydrusGlobals

def CensorshipMatch( tag, censorships ):
    
    for censorship in censorships:
        
        if censorship == '': # '' - all non namespaced tags
            
            if ':' not in tag:
                
                return True
                
            
        elif censorship == ':': # ':' - all namespaced tags
            
            if ':' in tag:
                
                return True
                
            
        elif ':' in censorship:
            
            if censorship.endswith( ':' ): # 'series:' - namespaced tags
                
                if tag.startswith( censorship ):
                    
                    return True
                    
                
            else: # 'series:evangelion' - exact match with namespace
                
                if tag == censorship:
                    
                    return True
                    
                
            
        else:
            
            # 'table' - normal tag, or namespaced version of same
            
            if ':' in tag:
                
                ( namespace, comparison_tag ) = tag.split( ':', 1 )
                
                if comparison_tag == censorship:
                    
                    return True
                    
                
            else:
                
                if tag == censorship:
                    
                    return True
                    
                
            
        
    
    return False
    
def ConvertTagToSortable( t ):
    
    if t[0].isdecimal():
        
        # We want to maintain that:
        # 0 < 0a < 0b < 1 ( lexicographic comparison )
        # -and-
        # 2 < 22 ( value comparison )
        # So, if the first bit can be turned into an int, split it into ( int, extra )
        
        int_component = ''
        
        i = 0
        
        for character in t:
            
            if character.isdecimal(): int_component += character
            else: break
            
            i += 1
            
        
        str_component = t[i:]
        
        number = int( int_component )
        
        
        return ( number, str_component )
        
    else:
        
        return t
        

def FilterNamespaces( tags, namespaces ):
    
    processed_tags = collections.defaultdict( set )
    
    for tag in tags:
        
        if ':' in tag:
            
            ( namespace, subtag ) = tag.split( ':', 1 )
            
            processed_tags[ namespace ].add( tag )
            
        else: processed_tags[ '' ].add( tag )
        
    
    result = set()
    
    for namespace in namespaces:
        
        if namespace in ( '', None ): result.update( processed_tags[ '' ] )
        
        result.update( processed_tags[ namespace ] )
        
    
    return result
    
def SortNumericTags( tags ):
    
    tags = list( tags )
    
    tags.sort( key = ConvertTagToSortable )
    
    return tags
    
def CheckTagNotEmpty( tag ):
    
    empty_tag = False
    
    if tag == '': empty_tag = True
    
    if ':' in tag:
        
        ( namespace, subtag ) = tag.split( ':', 1 )
        
        if subtag == '': empty_tag = True
        
    
    if empty_tag: raise HydrusExceptions.SizeException( 'Received a zero-length tag!' )

def CleanTag( tag ):
    
    try:
        
        tag = tag[:1024]
        
        tag = tag.lower()
        
        tag = HydrusData.ToUnicode( tag )
        
        tag.replace( '\r', '' )
        tag.replace( '\n', '' )
        
        tag = re.sub( '[\\s]+', ' ', tag, flags = re.UNICODE ) # turns multiple spaces into single spaces
        
        tag = re.sub( '\\s\\Z', '', tag, flags = re.UNICODE ) # removes space at the end
        
        while re.match( '\\s|-|system:', tag, flags = re.UNICODE ) is not None:
            
            tag = re.sub( '\\A(\\s|-|system:)', '', tag, flags = re.UNICODE ) # removes spaces or garbage at the beginning
            
        
        tag = re.sub( '^:(?!:)', '::', tag, flags = re.UNICODE ) # Convert anything starting with one colon to start with two i.e. :D -> ::D
        
    except Exception as e:
        
        text = 'Was unable to parse the tag: ' + HydrusData.ToUnicode( tag )
        text += os.linesep * 2
        text += str( e )
        
        raise Exception( text )
        
    
    return tag

def CleanTags( tags ):
    
    clean_tags = set()
    
    for tag in tags:
        
        tag = CleanTag( tag )
        
        try: CheckTagNotEmpty( tag )
        except HydrusExceptions.SizeException: continue
        
        clean_tags.add( tag )
        
    
    return clean_tags
    
def CombineTag( namespace, tag ):
    
    if namespace == '':
        
        if tag.startswith( ':' ):
            
            return ':' + tag
            
        else:
            
            return tag
            
        
    else:
        
        return namespace + ':' + tag
        
    
def RenderTag( tag ):
    
    if tag.startswith( '::' ):
        
        return tag[1:]
        
    else:
        
        return tag
        
    
