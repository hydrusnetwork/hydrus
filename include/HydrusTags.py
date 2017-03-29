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
    
def ConvertTagToSortable( t ):
    
    if len( t ) > 0 and t[0].isdecimal():
        
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
        
        def strip_gumpf_out( t ):
            
            t.replace( '\r', '' )
            t.replace( '\n', '' )
            
            t = re.sub( '[\\s]+', ' ', t, flags = re.UNICODE ) # turns multiple spaces into single spaces
            
            t = re.sub( '\\s\\Z', '', t, flags = re.UNICODE ) # removes space at the end
            
            while re.match( '\\s|-|system:', t, flags = re.UNICODE ) is not None:
                
                t = re.sub( '\\A(\\s|-|system:)', '', t, flags = re.UNICODE ) # removes spaces or garbage at the beginning
                
            
            return t
            
        
        tag = tag[:1024]
        
        tag = tag.lower()
        
        tag = HydrusData.ToUnicode( tag )
        
        if tag.startswith( ':' ):
            
            tag = re.sub( '^:(?!:)', '::', tag, flags = re.UNICODE ) # Convert anything starting with one colon to start with two i.e. :D -> ::D
            
            tag = strip_gumpf_out( tag )
            
        elif ':' in tag:
            
            ( namespace, subtag ) = SplitTag( tag )
            
            namespace = strip_gumpf_out( namespace )
            subtag = strip_gumpf_out( subtag )
            
            tag = CombineTag( namespace, subtag )
            
        else:
            
            tag = strip_gumpf_out( tag )
            
        
    except Exception as e:
        
        text = 'Was unable to parse the tag: ' + HydrusData.ToUnicode( tag )
        text += os.linesep * 2
        text += HydrusData.ToUnicode( e )
        
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
    
def CombineTag( namespace, subtag ):
    
    if namespace == '':
        
        if subtag.startswith( ':' ):
            
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
        
    
