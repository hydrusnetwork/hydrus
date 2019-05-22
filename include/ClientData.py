from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientDownloading
from . import ClientThreading
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
import threading
import traceback
import os
import sqlite3
import sys
import time
import wx
import wx.lib.colourutils
import yaml

def AddPaddingToDimensions( dimensions, padding ):
    
    ( x, y ) = dimensions
    
    return ( x + padding, y + padding )
    
def CatchExceptionClient( etype, value, tb ):
    
    try:
        
        trace_list = traceback.format_tb( tb )
        
        trace = ''.join( trace_list )
        
        pretty_value = str( value )
        
        if os.linesep in pretty_value:
            
            ( first_line, anything_else ) = pretty_value.split( os.linesep, 1 )
            
            trace = trace + os.linesep + anything_else
            
        else:
            
            first_line = pretty_value
            
        
        job_key = ClientThreading.JobKey()
        
        if etype == HydrusExceptions.ShutdownException:
            
            return
            
        else:
            
            try: job_key.SetVariable( 'popup_title', str( etype.__name__ ) )
            except: job_key.SetVariable( 'popup_title', str( etype ) )
            
            job_key.SetVariable( 'popup_text_1', first_line )
            job_key.SetVariable( 'popup_traceback', trace )
            
        
        text = job_key.ToString()
        
        HydrusData.Print( 'Uncaught exception:' )
        
        HydrusData.DebugPrint( text )
        
        HG.client_controller.pub( 'message', job_key )
        
    except:
        
        text = 'Encountered an error I could not parse:'
        
        text += os.linesep
        
        text += str( ( etype, value, tb ) )
        
        try: text += traceback.format_exc()
        except: pass
        
        HydrusData.ShowText( text )
        
    
    time.sleep( 1 )
    
def ColourIsBright( colour ):
    
    ( r, g, b, a ) = colour.Get()
    
    brightness_estimate = ( r + g + b ) // 3
    
    it_is_bright = brightness_estimate > 127
    
    return it_is_bright
    
def ColourIsGreyish( colour ):
    
    ( r, g, b, a ) = colour.Get()
    
    greyish = r // 16 == g // 16 and g // 16 == b // 16
    
    return greyish
    
def ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates ):
    
    num_files = 0
    actions = set()
    locations = set()
    
    extra_words = ''
    
    for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
        
        if len( content_updates ) > 0:
            
            name = HG.client_controller.services_manager.GetName( service_key )
            
            locations.add( name )
            
        
        for content_update in content_updates:
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            if data_type == HC.CONTENT_TYPE_MAPPINGS:
                
                extra_words = ' tags for'
                
            
            actions.add( HC.content_update_string_lookup[ action ] )
            
            if action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX ):
                
                locations = set()
                
            
            num_files += len( content_update.GetHashes() )
            
        
    
    s = ''
    
    if len( locations ) > 0:
        
        s += ', '.join( locations ) + '->'
        
    
    s += ', '.join( actions ) + extra_words + ' ' + HydrusData.ToHumanInt( num_files ) + ' files'
    
    return s
    
def ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hashes, service_keys_to_tags ):
    
    service_keys_to_content_updates = {}
    
    for ( service_key, tags ) in service_keys_to_tags.items():
        
        if len( tags ) == 0:
            
            continue
            
        
        if service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            action = HC.CONTENT_UPDATE_PEND
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, action, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates[ service_key ] = content_updates
        
    
    return service_keys_to_content_updates
    
def ConvertZoomToPercentage( zoom ):
    
    zoom_percent = zoom * 100
    
    pretty_zoom = '{:.2f}%'.format( zoom_percent )
    
    if pretty_zoom.endswith( '00%' ):
        
        pretty_zoom = '{:.0f}%'.format( zoom_percent )
        
    
    return pretty_zoom
    
def GetAlphaOfColour( colour, alpha ):
    
    ( r, g, b, a ) = colour.Get()
    
    return wx.Colour( r, g, b, alpha )
    
def GetDifferentLighterDarkerColour( colour, intensity = 3 ):
    
    ( r, g, b, a ) = colour.Get()
    
    if ColourIsGreyish( colour ):
        
        if ColourIsBright( colour ):
            
            colour = wx.Colour( int( g * ( 1 - 0.05 * intensity ) ), b, r )
            
        else:
            
            colour = wx.Colour( int( g * ( 1 + 0.05 * intensity ) / 2 ), b, r )
            
        
    else:
        
        colour = wx.Colour( g, b, r )
        
    
    return GetLighterDarkerColour( colour, intensity )
    
def GetLighterDarkerColour( colour, intensity = 3 ):
    
    if intensity is None or intensity == 0:
        
        return colour
        
    
    if ColourIsBright( colour ):
        
        return wx.lib.colourutils.AdjustColour( colour, -5 * intensity )
        
    else:
        
        ( r, g, b, a ) = colour.Get()
        
        ( r, g, b ) = [ max( value, 32 ) for value in ( r, g, b ) ]
        
        colour = wx.Colour( r, g, b )
        
        return wx.lib.colourutils.AdjustColour( colour, 5 * intensity )
        
    
def GetMediasTagCount( pool, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, collapse_siblings = False ):
    
    siblings_manager = HG.client_controller.tag_siblings_manager
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection():
            
            tags_managers.extend( media.GetSingletonsTagsManagers() )
            
        else:
            
            tags_managers.append( media.GetTagsManager() )
            
        
    
    current_tags_to_count = collections.Counter()
    deleted_tags_to_count = collections.Counter()
    pending_tags_to_count = collections.Counter()
    petitioned_tags_to_count = collections.Counter()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key )
        
        # combined is already collapsed
        if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY and collapse_siblings:
            
            statuses_to_tags = siblings_manager.CollapseStatusesToTags( tag_service_key, statuses_to_tags )
            
        
        current_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_CURRENT ] )
        deleted_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_DELETED ] )
        pending_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_PENDING ] )
        petitioned_tags_to_count.update( statuses_to_tags[ HC.CONTENT_STATUS_PETITIONED ] )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    
def GetSortTypeChoices():

    sort_choices = list( CC.SORT_CHOICES )
    
    for ( namespaces_text, namespaces_list ) in HC.options[ 'sort_by' ]:
        
        sort_choices.append( ( namespaces_text, tuple( namespaces_list ) ) )
        
    
    service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
    
    for service_key in service_keys:
        
        sort_choices.append( ( 'rating', service_key ) )
        
    
    return sort_choices
    
def MergeCounts( min_a, max_a, min_b, max_b ):
    
    # 100-None and 100-None returns 100-200
    # 1-None and 4-5 returns 5-6
    # 1-2, and 5-7 returns 6, 9
    
    if min_a == 0:
        
        ( min_answer, max_answer ) = ( min_b, max_b )
        
    elif min_b == 0:
        
        ( min_answer, max_answer ) = ( min_a, max_a )
        
    else:
        
        if max_a is None:
            
            max_a = min_a
            
        
        if max_b is None:
            
            max_b = min_b
            
        
        min_answer = max( min_a, min_b )
        max_answer = max_a + max_b
        
    
    return ( min_answer, max_answer )
    
def MergePredicates( predicates, add_namespaceless = False ):
    
    master_predicate_dict = {}
    
    for predicate in predicates:
        
        # this works because predicate.__hash__ exists
        
        if predicate in master_predicate_dict:
            
            master_predicate_dict[ predicate ].AddCounts( predicate )
            
        else:
            
            master_predicate_dict[ predicate ] = predicate
            
        
    
    if add_namespaceless:
        
        # we want to include the count for namespaced tags in the namespaceless version when:
        # there exists more than one instance of the subtag with different namespaces, including '', that has nonzero count
        
        unnamespaced_predicate_dict = {}
        subtag_nonzero_instance_counter = collections.Counter()
        
        for predicate in list(master_predicate_dict.values()):
            
            if predicate.HasNonZeroCount():
                
                unnamespaced_predicate = predicate.GetUnnamespacedCopy()
                
                subtag_nonzero_instance_counter[ unnamespaced_predicate ] += 1
                
                if unnamespaced_predicate in unnamespaced_predicate_dict:
                    
                    unnamespaced_predicate_dict[ unnamespaced_predicate ].AddCounts( unnamespaced_predicate )
                    
                else:
                    
                    unnamespaced_predicate_dict[ unnamespaced_predicate ] = unnamespaced_predicate
                    
                
            
        
        for ( unnamespaced_predicate, count ) in list(subtag_nonzero_instance_counter.items()):
            
            # if there were indeed several instances of this subtag, overwrte the master dict's instance with our new count total
            
            if count > 1:
                
                master_predicate_dict[ unnamespaced_predicate ] = unnamespaced_predicate_dict[ unnamespaced_predicate ]
                
            
        
    
    return list(master_predicate_dict.values())
    
def OrdIsSensibleASCII( o ):
    
    return 32 <= o and o <= 127
    
def OrdIsAlphaLower( o ):
    
    return 97 <= o and o <= 122
    
def OrdIsAlphaUpper( o ):
    
    return 65 <= o and o <= 90
    
def OrdIsAlpha( o ):
    
    return OrdIsAlphaLower( o ) or OrdIsAlphaUpper( o )
    
def OrdIsNumber( o ):
    
    return 48 <= o and o <= 57
    
def ReportShutdownException():
    
    text = 'A serious error occurred while trying to exit the program. Its traceback may be shown next. It should have also been written to client.log. You may need to quit the program from task manager.'
    
    HydrusData.DebugPrint( text )
    
    HydrusData.DebugPrint( traceback.format_exc() )
    
    wx.SafeShowMessage( 'shutdown error', text )
    wx.SafeShowMessage( 'shutdown error', traceback.format_exc() )
    
def ShowExceptionClient( e, do_wait = True ):
    
    ( etype, value, tb ) = sys.exc_info()
    
    if etype is None:
        
        etype = type( e )
        value = str( e )
        
        trace = 'No error trace--here is the stack:' + os.linesep + ''.join( traceback.format_stack() )
        
    else:
        
        trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
    
    pretty_value = str( value )
    
    if os.linesep in pretty_value:
        
        ( first_line, anything_else ) = pretty_value.split( os.linesep, 1 )
        
        trace = trace + os.linesep + anything_else
        
    else:
        
        first_line = pretty_value
        
    
    job_key = ClientThreading.JobKey()
    
    if isinstance( e, HydrusExceptions.ShutdownException ):
        
        return
        
    else:
        
        if hasattr( etype, '__name__' ):
            
            title = str( etype.__name__ )
            
        else:
            
            title = str( etype )
            
        
        job_key.SetVariable( 'popup_title', title )
        
        job_key.SetVariable( 'popup_text_1', first_line )
        job_key.SetVariable( 'popup_traceback', trace )
        
    
    text = job_key.ToString()
    
    HydrusData.Print( 'Exception:' )
    
    HydrusData.DebugPrint( text )
    
    HG.client_controller.pub( 'message', job_key )
    
    if do_wait:
        
        time.sleep( 1 )
        
    
def ShowTextClient( text ):
    
    job_key = ClientThreading.JobKey()
    
    job_key.SetVariable( 'popup_text_1', str( text ) )
    
    text = job_key.ToString()
    
    HydrusData.Print( text )
    
    HG.client_controller.pub( 'message', job_key )
    
class ApplicationCommand( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_APPLICATION_COMMAND
    SERIALISABLE_NAME = 'Application Command'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, command_type = None, data = None ):
        
        if command_type is None:
            
            command_type = CC.APPLICATION_COMMAND_TYPE_SIMPLE
            
        
        if data is None:
            
            data = 'archive_file'
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._command_type = command_type
        self._data = data
        
    
    def __repr__( self ):
        
        return self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        if self._command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            serialisable_data = self._data
            
        elif self._command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( service_key, content_type, action, value ) = self._data
            
            serialisable_data = ( service_key.hex(), content_type, action, value )
            
        
        return ( self._command_type, serialisable_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._command_type, serialisable_data ) = serialisable_info
        
        if self._command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            self._data = serialisable_data
            
        elif self._command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( serialisable_service_key, content_type, action, value ) = serialisable_data
            
            self._data = ( bytes.fromhex( serialisable_service_key ), content_type, action, value )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
                
                if serialisable_data == 'duplicate_filter_this_is_better':
                    
                    serialisable_data = 'duplicate_filter_this_is_better_and_delete_other'
                    
                elif serialisable_data == 'duplicate_filter_not_dupes':
                    
                    serialisable_data = 'duplicate_filter_false_positive'
                    
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetCommandType( self ):
        
        return self._command_type
        
    
    def GetData( self ):
        
        return self._data
        
    
    def ToString( self ):
        
        if self._command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            return self._data
            
        elif self._command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( service_key, content_type, action, value ) = self._data
            
            components = []
            
            components.append( HC.content_update_string_lookup[ action ] )
            components.append( HC.content_type_string_lookup[ content_type ] )
            components.append( '"' + str( value ) + '"' )
            components.append( 'for' )
            
            services_manager = HG.client_controller.services_manager
            
            if services_manager.ServiceExists( service_key ):
                
                service = services_manager.GetService( service_key )
                
                components.append( service.GetName() )
                
            else:
                
                components.append( 'unknown service!' )
                
            
            return ' '.join( components )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_APPLICATION_COMMAND ] = ApplicationCommand

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
        
        HydrusData.HydrusYAMLBase.__init__( self )
        
        if host == 'localhost':
            
            host = '127.0.0.1'
            
        
        self._host = host
        self._port = port
        self._access_key = access_key
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
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
        
    
    def HasAccessKey( self ): return self._access_key is not None and self._access_key is not ''
    
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
