import sqlite3
import sys
import time
import traceback
import yaml

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading

def AddPaddingToDimensions( dimensions, padding ):
    
    ( x, y ) = dimensions
    
    return ( x + padding, y + padding )
    

def CatchExceptionClient( etype, value, tb ):
    
    try:
        
        if etype == HydrusExceptions.ShutdownException:
            
            return
            
        
        trace_list = traceback.format_tb( tb )
        
        trace = ''.join( trace_list )
        
        pretty_value = f'{value}'
        
        all_lines = pretty_value.splitlines()
        
        if len( all_lines ) > 0:
            
            first_line = all_lines[0]
            
            if len( all_lines ) > 1:
                
                the_rest = all_lines[1:]
                
                trace = trace + '\n' + '\n'.join( the_rest )
                
            
        else:
            
            first_line = 'textless exception!'
            
        
        job_status = ClientThreading.JobStatus()
        
        try:
            
            job_status.SetStatusTitle( str( etype.__name__ ) )
            
        except Exception as e:
            
            job_status.SetStatusTitle( str( etype ) )
            
        
        job_status.SetStatusText( first_line )
        job_status.SetTraceback( trace )
        
        text = job_status.ToString()
        
        HydrusData.Print( 'Uncaught exception:' )
        
        HydrusData.DebugPrint( text )
        
        CG.client_controller.pub( 'message', job_status )
        
    except Exception as e:
        
        text = 'Encountered an error I could not parse:'
        
        text += '\n'
        
        text += str( ( etype, value, tb ) )
        
        try:
            
            text += traceback.format_exc()
            
        except Exception as e:
            
            pass
            
        
        HydrusData.ShowText( text )
        
    
    time.sleep( 1 )
    

def ConvertZoomToPercentage( zoom ):
    
    zoom_percent = zoom * 100
    
    pretty_zoom = '{:.2f}%'.format( zoom_percent )
    
    if pretty_zoom.endswith( '00%' ):
        
        pretty_zoom = '{:.0f}%'.format( zoom_percent )
        
    
    return pretty_zoom
    
def MergeCounts( min_a: int, max_a: int, min_b: int, max_b: int ):
    
    # this no longer takes 'None' maxes, and it is now comfortable with 0-5 ranges
    
    # 100-100 and 100-100 returns 100-200
    # 1-1 and 4-5 returns 4-6
    # 1-2, and 5-7 returns 5-9
    
    min_answer = max( min_a, min_b )
    max_answer = max_a + max_b
    
    return ( min_answer, max_answer )
    
def OrdIsSensibleASCII( o ):
    
    return 32 <= o <= 127
    
def OrdIsAlphaLower( o ):
    
    return 97 <= o <= 122
    
def OrdIsAlphaUpper( o ):
    
    return 65 <= o <= 90
    
def OrdIsAlpha( o ):
    
    return OrdIsAlphaLower( o ) or OrdIsAlphaUpper( o )
    
def OrdIsNumber( o ):
    
    return 48 <= o <= 57
    

def ResolutionToPrettyString( resolution ):
    
    if resolution is None:
        
        return 'no resolution'
        
    
    if not isinstance( resolution, tuple ):
        
        try:
            
            resolution = tuple( resolution )
            
        except Exception as e:
            
            return 'broken resolution'
            
        
    
    if resolution in HC.NICE_RESOLUTIONS and CG.client_controller.new_options.GetBoolean( 'use_nice_resolution_strings' ):
        
        return HC.NICE_RESOLUTIONS[ resolution ]
        
    
    ( width, height ) = resolution
    
    return '{}x{}'.format( HydrusNumbers.ToHumanInt( width ), HydrusNumbers.ToHumanInt( height ) )
    

def ShowExceptionClient( e, do_wait = True ):
    
    ( etype, value, tb ) = sys.exc_info()
    
    if etype is None:
        
        etype = type( e )
        value = str( e )
        
    
    ShowExceptionTupleClient( etype, value, tb, do_wait = do_wait )
    

def ShowExceptionTupleClient( etype, value, tb, do_wait = True ):
    
    if etype is None:
        
        etype = HydrusExceptions.UnknownException
        
    
    if etype == HydrusExceptions.ShutdownException:
        
        return
        
    
    pretty_value = f'{value}'
    
    if value is None or len( pretty_value.splitlines() ) == 0:
        
        value = 'Unknown error'
        pretty_value = value
        
    
    all_lines = pretty_value.splitlines()
    
    first_line = 'Exception'
    
    if len( all_lines ) > 0:
        
        first_line = all_lines[0]
        
    
    job_status = ClientThreading.JobStatus()
    
    try:
        
        job_status.SetStatusTitle( str( etype.__name__ ) )
        
    except Exception as e:
        
        job_status.SetStatusTitle( str( etype ) )
        
    
    job_status.SetStatusText( first_line )
    
    message = HydrusData.PrintExceptionTuple( etype, value, tb, do_wait = False )
    
    job_status.SetTraceback( message )
    
    CG.client_controller.pub( 'message', job_status )
    
    if do_wait:
        
        time.sleep( 1 )
        
    
def ShowTextClient( text ):
    
    job_status = ClientThreading.JobStatus()
    
    job_status.SetStatusText( str( text ) )
    
    text = job_status.ToString()
    
    HydrusData.Print( text )
    
    CG.client_controller.pub( 'message', job_status )
    

def ToHumanBytes( size ):
    
    sig_figs = CG.client_controller.new_options.GetInteger( 'human_bytes_sig_figs' )
    
    return HydrusData.BaseToHumanBytes( size, sig_figs = sig_figs )
    

HydrusData.ToHumanBytes = ToHumanBytes

class Booru( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = '!Booru'
    
    def __init__( self, name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ):
        
        self._name = name
        self._search_url = search_url
        self._search_separator = search_separator
        self._advance_by_page_num = advance_by_page_num
        self._thumb_classname = thumb_classname
        self._image_id = image_id
        self._image_data = image_data
        self._tag_classnames_to_namespaces = tag_classnames_to_namespaces
        
    
    def GetData( self ): return ( self._search_url, self._search_separator, self._advance_by_page_num, self._thumb_classname, self._image_id, self._image_data, self._tag_classnames_to_namespaces )
    
    def GetGalleryParsingInfo( self ): return ( self._search_url, self._advance_by_page_num, self._search_separator, self._thumb_classname )
    
    def GetName( self ): return self._name
    
    def GetNamespaces( self ): return list(self._tag_classnames_to_namespaces.values())
    
sqlite3.register_adapter( Booru, yaml.safe_dump )

class Credentials( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = '!Credentials'
    
    def __init__( self, host, port, access_key = None ):
        
        super().__init__()
        
        if host == 'localhost':
            
            host = '127.0.0.1'
            
        
        self._host = host
        self._port = port
        self._access_key = access_key
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Credentials ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ): return ( self._host, self._port, self._access_key ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Credentials: ' + str( ( self._host, self._port, self._access_key.hex() ) )
    
    def GetAccessKey( self ): return self._access_key
    
    def GetAddress( self ): return ( self._host, self._port )
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self.HasAccessKey(): connection_string += self._access_key.hex() + '@'
        
        connection_string += self._host + ':' + str( self._port )
        
        return connection_string
        
    
    def GetPortedAddress( self ):
        
        if self._host.endswith( '/' ):
            
            host = self._host[:-1]
            
        else:
            
            host = self._host
            
        
        if '/' in host:
            
            ( actual_host, gubbins ) = self._host.split( '/', 1 )
            
            address = '{}:{}/{}'.format( actual_host, self._port, gubbins )
            
        else:
            
            address = '{}:{}'.format( self._host, self._port )
            
        
        return address
        
    
    def HasAccessKey( self ): return self._access_key is not None and self._access_key != ''
    
    def SetAccessKey( self, access_key ): self._access_key = access_key
    
class Imageboard( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = '!Imageboard'
    
    def __init__( self, name, post_url, flood_time, form_fields, restrictions ):
        
        self._name = name
        self._post_url = post_url
        self._flood_time = flood_time
        self._form_fields = form_fields
        self._restrictions = restrictions
        
    
    def IsOKToPost( self, media_result ):
        
        # deleted old code due to deprecation
        
        return True
        
    
    def GetBoardInfo( self ): return ( self._post_url, self._flood_time, self._form_fields, self._restrictions )
    
    def GetName( self ): return self._name
    
sqlite3.register_adapter( Imageboard, yaml.safe_dump )
