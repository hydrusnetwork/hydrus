import ClientConstants as CC
import ClientDefaults
import ClientDownloading
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusPaths
import HydrusSerialisable
import HydrusTags
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
        
        pretty_value = HydrusData.ToUnicode( value )
        
        if os.linesep in pretty_value:
            
            ( first_line, anything_else ) = pretty_value.split( os.linesep, 1 )
            
            trace = trace + os.linesep + anything_else
            
        else:
            
            first_line = pretty_value
            
        
        trace = HydrusData.ToUnicode( trace )
        
        job_key = ClientThreading.JobKey()
        
        if etype == HydrusExceptions.ShutdownException:
            
            return
            
        else:
            
            if etype == wx.PyDeadObjectError:
                
                HydrusData.Print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
                HydrusData.Print( trace )
                
                return
                
            
            try: job_key.SetVariable( 'popup_title', HydrusData.ToUnicode( etype.__name__ ) )
            except: job_key.SetVariable( 'popup_title', HydrusData.ToUnicode( etype ) )
            
            job_key.SetVariable( 'popup_text_1', first_line )
            job_key.SetVariable( 'popup_traceback', trace )
            
        
        text = job_key.ToString()
        
        HydrusData.Print( 'Uncaught exception:' )
        
        HydrusData.DebugPrint( text )
        
        HG.client_controller.pub( 'message', job_key )
        
    except:
        
        text = 'Encountered an error I could not parse:'
        
        text += os.linesep
        
        text += HydrusData.ToUnicode( ( etype, value, tb ) )
        
        try: text += traceback.format_exc()
        except: pass
        
        HydrusData.ShowText( text )
        
    
    time.sleep( 1 )
    
def ColourIsBright( colour ):
    
    ( r, g, b ) = colour.Get()
    
    brightness_estimate = ( r + g + b ) // 3
    
    it_is_bright = brightness_estimate > 127
    
    return it_is_bright
    
def ColourIsGreyish( colour ):
    
    ( r, g, b ) = colour.Get()
    
    greyish = r // 16 == g // 16 and g // 16 == b // 16
    
    return greyish
    
def ConvertHTTPSToHTTP( url ):
    
    if url.startswith( 'http://' ):
        
        return url
        
    elif url.startswith( 'https://' ):
        
        http_url = 'http://' + url[8:]
        
        return http_url
        
    else:
        
        raise Exception( 'Given a url that did not have a scheme!' )
        
    
def ConvertHTTPToHTTPS( url ):
    
    if url.startswith( 'https://' ):
        
        return url
        
    elif url.startswith( 'http://' ):
        
        https_url = 'https://' + url[7:]
        
        return https_url
        
    else:
        
        raise Exception( 'Given a url that did not have a scheme!' )
        
    
def ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates ):
    
    num_files = 0
    actions = set()
    locations = set()
    
    extra_words = ''
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
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
        
    
    s += ', '.join( actions ) + extra_words + ' ' + HydrusData.ConvertIntToPrettyString( num_files ) + ' files'
    
    return s
    
def ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hashes, service_keys_to_tags ):
    
    service_keys_to_content_updates = {}
    
    for ( service_key, tags ) in service_keys_to_tags.items():
        
        if service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            action = HC.CONTENT_UPDATE_PEND
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, action, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates[ service_key ] = content_updates
        
    
    return service_keys_to_content_updates
    
def ConvertShortcutToPrettyShortcut( modifier, key ):
    
    if modifier == wx.ACCEL_NORMAL: modifier = ''
    elif modifier == wx.ACCEL_ALT: modifier = 'alt'
    elif modifier == wx.ACCEL_CTRL: modifier = 'ctrl'
    elif modifier == wx.ACCEL_SHIFT: modifier = 'shift'
    
    if key in range( 65, 91 ): key = chr( key + 32 ) # + 32 for converting ascii A -> a
    elif key in range( 97, 123 ): key = chr( key )
    else: key = CC.wxk_code_string_lookup[ key ]
    
    return ( modifier, key )
    
def ConvertTagSliceToString( tag_slice ):
    
    if tag_slice == '':
        
        return 'unnamespaced tags'
        
    elif tag_slice == ':':
        
        return 'namespaced tags'
        
    elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
        
        namespace = tag_slice[ : -1 ]
        
        return '\'' + namespace + '\' tags'
        
    else:
        
        return tag_slice
        
    
def ConvertTextToPixels( window, ( char_rows, char_cols ) ):
    
    dialog_units = ( char_rows * 4, char_cols * 8 )
    
    return window.ConvertDialogSizeToPixels( dialog_units )
    
def ConvertTextToPixelWidth( window, char_rows ):
    
    ( width, height ) = ConvertTextToPixels( window, ( char_rows, 1 ) )
    
    return width
    
def ConvertZoomToPercentage( zoom ):
    
    zoom_percent = zoom * 100
    
    pretty_zoom = '%.2f' % zoom_percent + '%'
    
    if pretty_zoom.endswith( '00%' ):
        
        pretty_zoom = '%i' % zoom_percent + '%'
        
    
    return pretty_zoom
    
def DeletePath( path ):
    
    if HC.options[ 'delete_to_recycle_bin' ] == True:
        
        HydrusPaths.RecyclePath( path )
        
    else:
        
        HydrusPaths.DeletePath( path )
        
    
def GetDifferentLighterDarkerColour( colour, intensity = 3 ):
    
    ( r, g, b ) = colour.Get()
    
    if ColourIsGreyish( colour ):
        
        if ColourIsBright( colour ):
            
            colour = wx.Colour( int( g * ( 1 - 0.05 * intensity ) ), b, r )
            
        else:
            
            colour = wx.Colour( int( g * ( 1 + 0.05 * intensity ) ) / 2, b, r )
            
        
    else:
        
        colour = wx.Colour( g, b, r )
        
    
    return GetLighterDarkerColour( colour, intensity )
    
def GetLighterDarkerColour( colour, intensity = 3 ):
    
    if intensity is None or intensity == 0:
        
        return colour
        
    
    if ColourIsBright( colour ):
        
        return wx.lib.colourutils.AdjustColour( colour, -5 * intensity )
        
    else:
        
        ( r, g, b ) = colour.Get()
        
        ( r, g, b ) = [ max( value, 32 ) for value in ( r, g, b ) ]
        
        colour = wx.Colour( r, g, b )
        
        return wx.lib.colourutils.AdjustColour( colour, 5 * intensity )
        
    
def GetMediasTagCount( pool, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, collapse_siblings = False ):
    
    siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
    
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
    
def GetSearchURLs( url ):
    
    search_urls = [ url ]
    
    if url.startswith( 'http://' ):
        
        search_urls.append( ConvertHTTPToHTTPS( url ) )
        
    elif url.startswith( 'https://' ):
        
        search_urls.append( ConvertHTTPSToHTTP( url ) )
        
    
    return search_urls
    
def GetSortChoices( add_namespaces_and_ratings = True ):

    sort_choices = list( CC.SORT_CHOICES )
    
    if add_namespaces_and_ratings:
        
        sort_choices.extend( HC.options[ 'sort_by' ] )
        
        service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for service_key in service_keys:
            
            sort_choices.append( ( 'rating_descend', service_key ) )
            sort_choices.append( ( 'rating_ascend', service_key ) )
            
        
    
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
        
        for predicate in master_predicate_dict.values():
            
            if predicate.HasNonZeroCount():
                
                unnamespaced_predicate = predicate.GetUnnamespacedCopy()
                
                subtag_nonzero_instance_counter[ unnamespaced_predicate ] += 1
                
                if unnamespaced_predicate in unnamespaced_predicate_dict:
                    
                    unnamespaced_predicate_dict[ unnamespaced_predicate ].AddCounts( unnamespaced_predicate )
                    
                else:
                    
                    unnamespaced_predicate_dict[ unnamespaced_predicate ] = unnamespaced_predicate
                    
                
            
        
        for ( unnamespaced_predicate, count ) in subtag_nonzero_instance_counter.items():
            
            # if there were indeed several instances of this subtag, overwrte the master dict's instance with our new count total
            
            if count > 1:
                
                master_predicate_dict[ unnamespaced_predicate ] = unnamespaced_predicate_dict[ unnamespaced_predicate ]
                
            
        
    
    return master_predicate_dict.values()
    
def ReportShutdownException():
    
    text = 'A serious error occured while trying to exit the program. Its traceback may be shown next. It should have also been written to client.log. You may need to quit the program from task manager.'
    
    HydrusData.DebugPrint( text )
    
    HydrusData.DebugPrint( traceback.format_exc() )
    
    wx.CallAfter( wx.MessageBox, traceback.format_exc() )
    wx.CallAfter( wx.MessageBox, text )
    
def ShowExceptionClient( e, do_wait = True ):
    
    ( etype, value, tb ) = sys.exc_info()
    
    if etype is None:
        
        etype = type( e )
        value = HydrusData.ToUnicode( e )
        
        trace = ''.join( traceback.format_stack() )
        
    else:
        
        trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
    
    trace = HydrusData.ToUnicode( trace )
    
    pretty_value = HydrusData.ToUnicode( value )
    
    if os.linesep in pretty_value:
        
        ( first_line, anything_else ) = HydrusData.ToUnicode( value ).split( os.linesep, 1 )
        
        trace = trace + os.linesep + anything_else
        
    else:
        
        first_line = pretty_value
        
    
    job_key = ClientThreading.JobKey()
    
    if isinstance( e, HydrusExceptions.ShutdownException ):
        
        return
        
    else:
        
        if etype == wx.PyDeadObjectError:
            
            HydrusData.Print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
            HydrusData.Print( trace )
            
            return
            
        
        if hasattr( etype, '__name__' ): title = HydrusData.ToUnicode( etype.__name__ )
        else: title = HydrusData.ToUnicode( etype )
        
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
    
    job_key.SetVariable( 'popup_text_1', HydrusData.ToUnicode( text ) )
    
    text = job_key.ToString()
    
    HydrusData.Print( text )
    
    HG.client_controller.pub( 'message', job_key )
    
def SortTagsList( tags, sort_type ):
    
    if sort_type in ( CC.SORT_BY_LEXICOGRAPHIC_DESC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
        
        reverse = True
        
    else:
        
        reverse = False
        
    
    if sort_type in ( CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
        
        def key( tag ):
            
            # '{' is above 'z' in ascii, so this works for most situations
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace == '':
                
                return ( '{', subtag )
                
            else:
                
                return ( namespace, subtag )
                
            
        
    else:
        
        key = None
        
    
    tags.sort( key = key, reverse = reverse )
    
def WaitPolitely( page_key = None ):
    
    if page_key is not None:
        
        HG.client_controller.pub( 'waiting_politely', page_key, True )
        
    
    time.sleep( HC.options[ 'website_download_polite_wait' ] )
    
    if page_key is not None:
        
        HG.client_controller.pub( 'waiting_politely', page_key, False )
        
    
class ApplicationCommand( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_APPLICATION_COMMAND
    SERIALISABLE_VERSION = 1
    
    def __init__( self, command_type = None, data = None ):
        
        if command_type is None:
            
            command_type = CC.APPLICATION_COMMAND_TYPE_SIMPLE
            
        
        if data is None:
            
            data = 'archive_file'
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._command_type = command_type
        self._data = data
        
    
    def __cmp__( self, other ):
        
        return cmp( self.ToString(), other.ToString() )
        
    
    def __repr__( self ):
        
        return self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        if self._command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            serialisable_data = self._data
            
        elif self._command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( service_key, content_type, action, value ) = self._data
            
            serialisable_data = ( service_key.encode( 'hex' ), content_type, action, value )
            
        
        return ( self._command_type, serialisable_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._command_type, serialisable_data ) = serialisable_info
        
        if self._command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            self._data = serialisable_data
            
        elif self._command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( serialisable_service_key, content_type, action, value ) = serialisable_data
            
            self._data = ( serialisable_service_key.decode( 'hex' ), content_type, action, value )
            
        
    
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
            components.append( '"' + HydrusData.ToUnicode( value ) + '"' )
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
    
    yaml_tag = u'!Booru'
    
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
    
    def GetNamespaces( self ): return self._tag_classnames_to_namespaces.values()
    
sqlite3.register_adapter( Booru, yaml.safe_dump )

class ClientOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS
    SERIALISABLE_VERSION = 3
    
    def __init__( self, db_dir = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if db_dir is None:
            
            db_dir = HC.DEFAULT_DB_DIR
            
        
        self._dictionary = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
        self._InitialiseDefaults( db_dir )
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            serialisable_info = self._dictionary.GetSerialisableTuple()
            
            return serialisable_info
            
        
    
    def _InitialiseDefaults( self, db_dir ):
        
        self._dictionary[ 'booleans' ] = {}
        
        self._dictionary[ 'booleans' ][ 'advanced_mode' ] = False
        
        self._dictionary[ 'booleans' ][ 'apply_all_parents_to_all_services' ] = False
        self._dictionary[ 'booleans' ][ 'apply_all_siblings_to_all_services' ] = False
        self._dictionary[ 'booleans' ][ 'filter_inbox_and_archive_predicates' ] = False
        self._dictionary[ 'booleans' ][ 'waiting_politely_text' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_thumbnail_title_banner' ] = True
        self._dictionary[ 'booleans' ][ 'show_thumbnail_page' ] = True
        
        self._dictionary[ 'booleans' ][ 'disable_cv_for_gifs' ] = False
        
        self._dictionary[ 'booleans' ][ 'add_parents_on_manage_tags' ] = True
        self._dictionary[ 'booleans' ][ 'replace_siblings_on_manage_tags' ] = True
        
        self._dictionary[ 'booleans' ][ 'get_tags_if_url_known_and_file_redundant' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_related_tags' ] = False
        self._dictionary[ 'booleans' ][ 'show_file_lookup_script_tags' ] = False
        self._dictionary[ 'booleans' ][ 'hide_message_manager_on_gui_iconise' ] = HC.PLATFORM_OSX
        self._dictionary[ 'booleans' ][ 'hide_message_manager_on_gui_deactive' ] = False
        
        self._dictionary[ 'booleans' ][ 'load_images_with_pil' ] = HC.PLATFORM_LINUX or HC.PLATFORM_OSX
        
        self._dictionary[ 'booleans' ][ 'use_system_ffmpeg' ] = False
        
        self._dictionary[ 'booleans' ][ 'maintain_similar_files_duplicate_pairs_during_idle' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_namespaces' ] = True
        
        self._dictionary[ 'booleans' ][ 'verify_regular_https' ] = True
        
        #
        
        self._dictionary[ 'duplicate_action_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_BETTER ] = DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, TagCensor() ) ], [], True, True )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_SAME_QUALITY ] = DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, TagCensor() ) ], [], False, True )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_ALTERNATE ] = DuplicateActionOptions( [], [], False )
        self._dictionary[ 'duplicate_action_options' ][ HC.DUPLICATE_NOT_DUPLICATE ] = DuplicateActionOptions( [], [], False )
        
        #
        
        self._dictionary[ 'integers' ] = {}
        
        self._dictionary[ 'integers' ][ 'video_buffer_size_mb' ] = 96
        
        self._dictionary[ 'integers' ][ 'related_tags_search_1_duration_ms' ] = 250
        self._dictionary[ 'integers' ][ 'related_tags_search_2_duration_ms' ] = 2000
        self._dictionary[ 'integers' ][ 'related_tags_search_3_duration_ms' ] = 6000
        
        self._dictionary[ 'integers' ][ 'suggested_tags_width' ] = 300
        
        self._dictionary[ 'integers' ][ 'similar_files_duplicate_pairs_search_distance' ] = 0
        
        self._dictionary[ 'integers' ][ 'default_new_page_goes' ] = CC.NEW_PAGE_GOES_FAR_RIGHT
        
        #
        
        self._dictionary[ 'keys' ] = {}
        
        self._dictionary[ 'keys' ][ 'default_tag_service_search_page' ] = CC.COMBINED_TAG_SERVICE_KEY.encode( 'hex' )
        
        self._dictionary[ 'key_list' ] = {}
        
        self._dictionary[ 'key_list' ][ 'default_neighbouring_txt_tag_service_keys' ] = []
        
        #
        
        self._dictionary[ 'noneable_integers' ] = {}
        
        self._dictionary[ 'noneable_integers' ][ 'forced_search_limit' ] = None
        
        self._dictionary[ 'noneable_integers' ][ 'disk_cache_maintenance_mb' ] = 256
        self._dictionary[ 'noneable_integers' ][ 'disk_cache_init_period' ] = 4
        
        self._dictionary[ 'noneable_integers' ][ 'num_recent_tags' ] = 20
        
        self._dictionary[ 'noneable_integers' ][ 'maintenance_vacuum_period_days' ] = 30
        
        self._dictionary[ 'noneable_integers' ][ 'duplicate_background_switch_intensity' ] = 3
        
        #
        
        self._dictionary[ 'noneable_strings' ] = {}
        
        self._dictionary[ 'noneable_strings' ][ 'favourite_file_lookup_script' ] = 'gelbooru md5'
        self._dictionary[ 'noneable_strings' ][ 'suggested_tags_layout' ] = 'notebook'
        self._dictionary[ 'noneable_strings' ][ 'backup_path' ] = None
        
        self._dictionary[ 'strings' ] = {}
        
        self._dictionary[ 'strings' ][ 'main_gui_title' ] = 'hydrus client'
        self._dictionary[ 'strings' ][ 'namespace_connector' ] = ':'
        self._dictionary[ 'strings' ][ 'export_phrase' ] = '{hash}'
        
        self._dictionary[ 'string_list' ] = {}
        
        self._dictionary[ 'string_list' ][ 'default_media_viewer_custom_shortcuts' ] = []
        
        #
        
        client_files_default = os.path.join( db_dir, 'client_files' )
        
        self._dictionary[ 'client_files_locations_ideal_weights' ] = [ ( HydrusPaths.ConvertAbsPathToPortablePath( client_files_default ), 1.0 ) ]
        self._dictionary[ 'client_files_locations_resized_thumbnail_override' ] = None
        self._dictionary[ 'client_files_locations_full_size_thumbnail_override' ] = None
        
        #
        
        self._dictionary[ 'default_import_tag_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        #
        
        self._dictionary[ 'frame_locations' ] = {}
        
        # remember size, remember position, last_size, last_pos, default gravity, default position, maximised, fullscreen
        self._dictionary[ 'frame_locations' ][ 'file_import_status' ] = ( True, True, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'main_gui' ] = ( True, True, ( 640, 480 ), ( 20, 20 ), ( -1, -1 ), 'topleft', True, False )
        self._dictionary[ 'frame_locations' ][ 'manage_options_dialog' ] = ( False, False, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_subscriptions_dialog' ] = ( True, True, None, None, ( 1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_tags_dialog' ] = ( False, False, None, None, ( -1, 1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'manage_tags_frame' ] = ( False, False, None, None, ( -1, 1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'media_viewer' ] = ( True, True, ( 640, 480 ), ( 70, 70 ), ( -1, -1 ), 'topleft', True, True )
        self._dictionary[ 'frame_locations' ][ 'regular_dialog' ] = ( False, False, None, None, ( -1, -1 ), 'topleft', False, False )
        self._dictionary[ 'frame_locations' ][ 'review_services' ] = ( False, True, None, None, ( -1, -1 ), 'topleft', False, False )
        
        #
        
        self._dictionary[ 'media_view' ] = HydrusSerialisable.SerialisableDictionary() # integer keys, so got to be cleverer dict
        
        # media_show_action, preview_show_action, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) )
        
        image_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        gif_zoom_info = ( CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, True, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        flash_zoom_info = ( CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR )
        video_zoom_info = ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, CC.MEDIA_VIEWER_SCALE_TO_CANVAS, True, CC.ZOOM_LANCZOS4, CC.ZOOM_AREA )
        null_zoom_info = ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_100, False, CC.ZOOM_LINEAR, CC.ZOOM_LINEAR )
        
        self._dictionary[ 'media_view' ][ HC.IMAGE_JPEG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_PNG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, image_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_APNG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, gif_zoom_info )
        self._dictionary[ 'media_view' ][ HC.IMAGE_GIF ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, gif_zoom_info )
        
        if HC.PLATFORM_WINDOWS:
            
            self._dictionary[ 'media_view' ][ HC.APPLICATION_FLASH ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, CC.MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, flash_zoom_info )
            
        else:
            
            self._dictionary[ 'media_view' ][ HC.APPLICATION_FLASH ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
            
        
        self._dictionary[ 'media_view' ][ HC.APPLICATION_PDF ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_HYDRUS_UPDATE_CONTENT ] = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, null_zoom_info )
        
        self._dictionary[ 'media_view' ][ HC.VIDEO_AVI ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_FLV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MOV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MP4 ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MPEG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_MKV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_WEBM ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.VIDEO_WMV ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, CC.MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, video_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_MP3 ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_OGG ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_FLAC ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        self._dictionary[ 'media_view' ][ HC.AUDIO_WMA ] = ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, null_zoom_info )
        
        self._dictionary[ 'media_zooms' ] = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
        
        #
        
        self._dictionary[ 'suggested_tags' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'suggested_tags' ][ 'favourites' ] = {}
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
        
        for ( key, value ) in loaded_dictionary.items():
            
            if isinstance( value, dict ):
                
                self._dictionary[ key ].update( value )
                
            else:
                
                self._dictionary[ key ] = value
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( old_serialisable_info )
            
            if 'media_view' in loaded_dictionary:
                
                mimes = loaded_dictionary[ 'media_view' ].keys()
                
                for mime in mimes:
                    
                    if mime in self._dictionary[ 'media_view' ]:
                        
                        ( default_media_show_action, default_preview_show_action, default_zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
                        
                        ( media_show_action, preview_show_action, zoom_in_to_fit, exact_zooms_only, scale_up_quality, scale_down_quality ) = loaded_dictionary[ 'media_view' ][ mime ]
                        
                        loaded_dictionary[ 'media_view' ][ mime ] = ( media_show_action, preview_show_action, default_zoom_info )
                        
                    else:
                        
                        # while devving this, I discovered some u'20' stringified keys had snuck in and hung around. let's nuke them here, in case anyone else got similar
                        
                        del loaded_dictionary[ 'media_view' ][ mime ]
                        
                    
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            # as db_dir is now moveable, let's move portable base from base_dir to db_dir
            
            def update_portable_path( p ):
                
                if p is None:
                    
                    return p
                    
                
                p = os.path.normpath( p ) # collapses .. stuff and converts / to \\ for windows only
                
                if os.path.isabs( p ):
                    
                    a_p = p
                    
                else:
                    
                    a_p = os.path.normpath( os.path.join( HC.BASE_DIR, p ) )
                    
                
                if not HC.PLATFORM_WINDOWS and not os.path.exists( a_p ):
                    
                    a_p = a_p.replace( '\\', '/' )
                    
                
                try:
                    
                    db_dir = HG.controller.GetDBDir()
                    
                    p = os.path.relpath( a_p, db_dir )
                    
                    if p.startswith( '..' ):
                        
                        p = a_p
                        
                    
                except:
                    
                    p = a_p
                    
                
                if HC.PLATFORM_WINDOWS:
                    
                    p = p.replace( '\\', '/' ) # store seps as /, to maintain multiplatform uniformity
                    
                
                return p
                
            
            loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( old_serialisable_info )
            
            if 'client_files_locations_ideal_weights' in loaded_dictionary:
                
                updated_cfliw = []
                
                for ( old_portable_path, weight ) in loaded_dictionary[ 'client_files_locations_ideal_weights' ]:
                    
                    new_portable_path = update_portable_path( old_portable_path )
                    
                    updated_cfliw.append( ( new_portable_path, weight ) )
                    
                
                loaded_dictionary[ 'client_files_locations_ideal_weights' ] = updated_cfliw
                
            
            if 'client_files_locations_resized_thumbnail_override' in loaded_dictionary:
                
                loaded_dictionary[ 'client_files_locations_resized_thumbnail_override' ] = update_portable_path( loaded_dictionary[ 'client_files_locations_resized_thumbnail_override' ] )
                
            
            if 'client_files_locations_full_size_thumbnail_override' in loaded_dictionary:
                
                loaded_dictionary[ 'client_files_locations_full_size_thumbnail_override' ] = update_portable_path( loaded_dictionary[ 'client_files_locations_full_size_thumbnail_override' ] )
                
            
            new_serialisable_info = loaded_dictionary.GetSerialisableTuple()
            
            return ( 3, new_serialisable_info )
            
        
    
    def ClearDefaultImportTagOptions( self ):
        
        with self._lock:
            
            self._dictionary[ 'default_import_tag_options' ] = HydrusSerialisable.SerialisableDictionary()
            
        
    
    def GetBoolean( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetClientFilesLocationsToIdealWeights( self ):
        
        with self._lock:
            
            paths_to_weights = {}
            
            for ( portable_path, weight ) in self._dictionary[ 'client_files_locations_ideal_weights' ]:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_path )
                
                paths_to_weights[ abs_path ] = weight
                
            
            resized_thumbnail_override = self._dictionary[ 'client_files_locations_resized_thumbnail_override' ]
            
            if resized_thumbnail_override is not None:
                
                resized_thumbnail_override = HydrusPaths.ConvertPortablePathToAbsPath( resized_thumbnail_override )
                
            
            
            full_size_thumbnail_override = self._dictionary[ 'client_files_locations_full_size_thumbnail_override' ]
            
            if full_size_thumbnail_override is not None:
                
                full_size_thumbnail_override = HydrusPaths.ConvertPortablePathToAbsPath( full_size_thumbnail_override )
                
            
            return ( paths_to_weights, resized_thumbnail_override, full_size_thumbnail_override )
            
        
    
    def GetDefaultImportTagOptions( self, gallery_identifier = None ):
        
        with self._lock:
            
            default_import_tag_options = self._dictionary[ 'default_import_tag_options' ]
            
            if gallery_identifier is None:
                
                return default_import_tag_options
                
            else:
                
                if gallery_identifier in default_import_tag_options:
                    
                    import_tag_options = default_import_tag_options[ gallery_identifier ]
                    
                else:
                    
                    default_booru_gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU )
                    default_hentai_foundry_gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_HENTAI_FOUNDRY )
                    default_pixiv_gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_PIXIV )
                    default_gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEFAULT )
                    
                    guidance_import_tag_options = None
                    
                    site_type = gallery_identifier.GetSiteType()
                    
                    if site_type == HC.SITE_TYPE_BOORU and default_booru_gallery_identifier in default_import_tag_options:
                        
                        guidance_import_tag_options = default_import_tag_options[ default_booru_gallery_identifier ]
                        
                    elif site_type in ( HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST, HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS ) and default_hentai_foundry_gallery_identifier in default_import_tag_options:
                        
                        guidance_import_tag_options = default_import_tag_options[ default_hentai_foundry_gallery_identifier ]
                        
                    elif site_type in ( HC.SITE_TYPE_PIXIV_ARTIST_ID, HC.SITE_TYPE_PIXIV_TAG ) and default_pixiv_gallery_identifier in default_import_tag_options:
                        
                        guidance_import_tag_options = default_import_tag_options[ default_pixiv_gallery_identifier ]
                        
                    elif default_gallery_identifier in default_import_tag_options:
                        
                        guidance_import_tag_options = default_import_tag_options[ default_gallery_identifier ]
                        
                    
                    service_keys_to_namespaces = {}
                    service_keys_to_explicit_tags = {}
                    
                    if guidance_import_tag_options is not None:
                        
                        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
                        
                        guidance_service_keys_to_namespaces = guidance_import_tag_options.GetServiceKeysToNamespaces()
                        
                        for ( service_key, guidance_namespaces ) in guidance_service_keys_to_namespaces.items():
                            
                            if 'all namespaces' in guidance_namespaces:
                                
                                service_keys_to_namespaces[ service_key ] = namespaces
                                
                            else:
                                
                                service_keys_to_namespaces[ service_key ] = [ namespace for namespace in namespaces if namespace in guidance_namespaces ]
                                
                            
                        
                        service_keys_to_explicit_tags = guidance_import_tag_options.GetServiceKeysToExplicitTags()
                        
                    
                    import_tag_options = ImportTagOptions( service_keys_to_namespaces = service_keys_to_namespaces, service_keys_to_explicit_tags = service_keys_to_explicit_tags )
                    
                
                return import_tag_options
                
            
        
    
    def GetDuplicateActionOptions( self, duplicate_type ):
        
        with self._lock:
            
            return self._dictionary[ 'duplicate_action_options' ][ duplicate_type ]
            
        
    
    def GetFrameLocation( self, frame_key ):
        
        with self._lock:
            
            return self._dictionary[ 'frame_locations' ][ frame_key ]
            
        
    
    def GetFrameLocations( self ):
        
        with self._lock:
            
            return self._dictionary[ 'frame_locations' ].items()
            
        
    
    def GetInteger( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'integers' ][ name ]
            
        
    
    def GetKey( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'keys' ][ name ].decode( 'hex' )
            
        
    
    def GetKeyList( self, name ):
        
        with self._lock:
            
            return [ key.decode( 'hex' ) for key in self._dictionary[ 'key_list' ][ name ] ]
            
        
    
    def GetMediaShowAction( self, mime ):
        
        with self._lock:
            
            ( media_show_action, preview_show_action, zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
            
            return media_show_action
            
        
    
    def GetMediaViewOptions( self, mime ):
        
        with self._lock:
            
            return self._dictionary[ 'media_view' ][ mime ]
            
        
    
    def GetMediaZoomOptions( self, mime ):
        
        with self._lock:
            
            ( media_show_action, preview_show_action, zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
            
            return zoom_info
            
        
    
    def GetMediaZooms( self ):
        
        with self._lock:
            
            return list( self._dictionary[ 'media_zooms' ] )
            
        
    
    def GetMediaZoomQuality( self, mime ):
        
        with self._lock:
            
            ( media_show_action, preview_show_action, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) ) = self._dictionary[ 'media_view' ][ mime ]
            
            return ( scale_up_quality, scale_down_quality )
            
        
    
    def GetNoneableInteger( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_integers' ][ name ]
            
        
    
    def GetNoneableString( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_strings' ][ name ]
            
        
    
    def GetPreviewShowAction( self, mime ):
        
        with self._lock:
            
            ( media_show_action, preview_show_action, zoom_info ) = self._dictionary[ 'media_view' ][ mime ]
            
            return preview_show_action
            
        
    
    def GetString( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'strings' ][ name ]
            
        
    
    def GetStringList( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'string_list' ][ name ]
            
        
    
    def GetSuggestedTagsFavourites( self, service_key ):
        
        with self._lock:
            
            service_key_hex = service_key.encode( 'hex' )
            
            stf = self._dictionary[ 'suggested_tags' ][ 'favourites' ]
            
            if service_key_hex in stf:
                
                return set( stf[ service_key_hex ] )
                
            else:
                
                return set()
                
            
        
    
    def InvertBoolean( self, name ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = not self._dictionary[ 'booleans' ][ name ]
            
        
    
    def RemoveClientFilesLocation( self, location ):
        
        with self._lock:
            
            if len( self._dictionary[ 'client_files_locations_ideal_weights' ] ) < 2:
                
                raise Exception( 'Cannot remove any more files locations!' )
                
            
            portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
            
            self._dictionary[ 'client_files_locations_ideal_weights' ] = [ ( l, w ) for ( l, w ) in self._dictionary[ 'client_files_locations_ideal_weights' ] if l != portable_location ]
            
        
    
    def SetBoolean( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = value
            
        
    
    def SetClientFilesLocation( self, location, weight ):
        
        with self._lock:
            
            portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
            weight = float( weight )
            
            self._dictionary[ 'client_files_locations_ideal_weights' ] = [ ( l, w ) for ( l, w ) in self._dictionary[ 'client_files_locations_ideal_weights' ] if l != portable_location ]
            
            self._dictionary[ 'client_files_locations_ideal_weights' ].append( ( portable_location, weight ) )
            
        
    
    def SetDefaultImportTagOptions( self, gallery_identifier, import_tag_options ):
        
        with self._lock:
            
            self._dictionary[ 'default_import_tag_options' ][ gallery_identifier ] = import_tag_options
            
        
    
    def SetDuplicateActionOptions( self, duplicate_type, duplicate_action_options ):
        
        with self._lock:
            
            self._dictionary[ 'duplicate_action_options' ][ duplicate_type ] = duplicate_action_options
            
        
    
    def SetFrameLocation( self, frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ):
        
        with self._lock:
            
            self._dictionary[ 'frame_locations' ][ frame_key ] = ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
            
        
    
    def SetFullsizeThumbnailOverride( self, full_size_thumbnail_override ):
        
        with self._lock:
            
            self._dictionary[ 'client_files_locations_full_size_thumbnail_override' ] = full_size_thumbnail_override
            
        
    
    def SetInteger( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'integers' ][ name ] = value
            
        
    
    def SetKey( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'keys' ][ name ] = value.encode( 'hex' )
            
        
    
    def SetKeyList( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'key_list' ][ name ] = [ key.encode( 'hex' ) for key in value ]
            
        
    
    def SetMediaViewOptions( self, mime, value_tuple ):
        
        with self._lock:
            
            self._dictionary[ 'media_view' ][ mime ] = value_tuple
            
        
    
    def SetMediaZooms( self, zooms ):
        
        with self._lock:
            
            self._dictionary[ 'media_zooms' ] = zooms
            
        
    
    def SetNoneableInteger( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'noneable_integers' ][ name ] = value
            
        
    
    def SetNoneableString( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'noneable_strings' ][ name ] = value
            
        
    
    def SetResizedThumbnailOverride( self, resized_thumbnail_override ):
        
        with self._lock:
            
            self._dictionary[ 'client_files_locations_resized_thumbnail_override' ] = resized_thumbnail_override
            
        
    
    def SetString( self, name, value ):
        
        with self._lock:
            
            if value is not None and value != '':
                
                self._dictionary[ 'strings' ][ name ] = value
                
            
        
    
    def SetStringList( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'string_list' ][ name ] = value
            
        
    
    def SetSuggestedTagsFavourites( self, service_key, tags ):
        
        with self._lock:
            
            service_key_hex = service_key.encode( 'hex' )
            
            self._dictionary[ 'suggested_tags' ][ 'favourites' ][ service_key_hex ] = list( tags )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS ] = ClientOptions

class Credentials( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Credentials'
    
    def __init__( self, host, port, access_key = None ):
        
        HydrusData.HydrusYAMLBase.__init__( self )
        
        if host == 'localhost': host = '127.0.0.1'
        
        self._host = host
        self._port = port
        self._access_key = access_key
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._host, self._port, self._access_key ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Credentials: ' + HydrusData.ToUnicode( ( self._host, self._port, self._access_key.encode( 'hex' ) ) )
    
    def GetAccessKey( self ): return self._access_key
    
    def GetAddress( self ): return ( self._host, self._port )
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self.HasAccessKey(): connection_string += self._access_key.encode( 'hex' ) + '@'
        
        connection_string += self._host + ':' + str( self._port )
        
        return connection_string
        
    
    def HasAccessKey( self ): return self._access_key is not None and self._access_key is not ''
    
    def SetAccessKey( self, access_key ): self._access_key = access_key
    
class DuplicateActionOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS
    SERIALISABLE_VERSION = 2
    
    def __init__( self, tag_service_actions = None, rating_service_actions = None, delete_second_file = False, sync_archive = False, delete_both_files = False ):
        
        if tag_service_actions is None:
            
            tag_service_actions = []
            
        
        if rating_service_actions is None:
            
            rating_service_actions = []
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tag_service_actions = tag_service_actions
        self._rating_service_actions = rating_service_actions
        self._delete_second_file = delete_second_file
        self._sync_archive = sync_archive
        self._delete_both_files = delete_both_files
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            self._tag_service_actions = [ ( service_key, action, tag_censor ) for ( service_key, action, tag_censor ) in self._tag_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) ]
            self._rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._rating_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
        
        serialisable_tag_service_actions = [ ( service_key.encode( 'hex' ), action, tag_censor.GetSerialisableTuple() ) for ( service_key, action, tag_censor ) in self._tag_service_actions ]
        serialisable_rating_service_actions = [ ( service_key.encode( 'hex' ), action ) for ( service_key, action ) in self._rating_service_actions ]
        
        return ( serialisable_tag_service_actions, serialisable_rating_service_actions, self._delete_second_file, self._sync_archive, self._delete_both_files )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_tag_service_actions, serialisable_rating_service_actions, self._delete_second_file, self._sync_archive, self._delete_both_files ) = serialisable_info
        
        self._tag_service_actions = [ ( serialisable_service_key.decode( 'hex' ), action, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_censor ) ) for ( serialisable_service_key, action, serialisable_tag_censor ) in serialisable_tag_service_actions ]
        self._rating_service_actions = [ ( serialisable_service_key.decode( 'hex' ), action ) for ( serialisable_service_key, action ) in serialisable_rating_service_actions ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_service_actions, delete_second_file ) = old_serialisable_info
            
            tag_service_actions = []
            rating_service_actions = []
            
            # As the client isn't booted when this is loaded in options, there isn't a good way to figure out tag from rating
            # So, let's just dupe and purge later on, in serialisation
            for ( service_key_encoded, action ) in serialisable_service_actions:
                
                service_key = service_key_encoded.decode( 'hex' )
                
                tag_censor = TagCensor()
                
                tag_service_actions.append( ( service_key, action, tag_censor ) )
                
                rating_service_actions.append( ( service_key, action ) )
                
            
            serialisable_tag_service_actions = [ ( service_key.encode( 'hex' ), action, tag_censor.GetSerialisableTuple() ) for ( service_key, action, tag_censor ) in tag_service_actions ]
            serialisable_rating_service_actions = [ ( service_key.encode( 'hex' ), action ) for ( service_key, action ) in rating_service_actions ]
            
            sync_archive = delete_second_file
            delete_both_files = False
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetDeletedHashes( self, first_media, second_media ):
        
        first_hashes = first_media.GetHashes()
        second_hashes = second_media.GetHashes()
        
        if self._delete_second_file:
            
            return second_hashes
            
        elif self._delete_both_files:
            
            return first_hashes.union( second_hashes )
            
        else:
            
            return set()
            
        
    
    def SetTuple( self, tag_service_actions, rating_service_actions, delete_second_file, sync_archive, delete_both_files ):
        
        self._tag_service_actions = tag_service_actions
        self._rating_service_actions = rating_service_actions
        self._delete_second_file = delete_second_file
        self._sync_archive = sync_archive
        self._delete_both_files = delete_both_files
        
    
    def ToTuple( self ):
        
        return ( self._tag_service_actions, self._rating_service_actions, self._delete_second_file, self._sync_archive, self._delete_both_files )
        
    
    def ProcessPairIntoContentUpdates( self, first_media, second_media ):
        
        list_of_service_keys_to_content_updates = []
        
        first_hashes = first_media.GetHashes()
        second_hashes = second_media.GetHashes()
        
        #
        
        service_keys_to_content_updates = {}
        
        services_manager = HG.client_controller.services_manager
        
        for ( service_key, action, tag_censor ) in self._tag_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.LOCAL_TAG:
                
                add_content_action = HC.CONTENT_UPDATE_ADD
                
            elif service_type == HC.TAG_REPOSITORY:
                
                add_content_action = HC.CONTENT_UPDATE_PEND
                
            
            first_current_tags = first_media.GetTagsManager().GetCurrent( service_key )
            second_current_tags = second_media.GetTagsManager().GetCurrent( service_key )
            
            first_current_tags = tag_censor.Censor( first_current_tags )
            second_current_tags = tag_censor.Censor( second_current_tags )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_current_tags.difference( first_current_tags )
                second_needs = first_current_tags.difference( second_current_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, second_hashes ) ) for tag in second_needs ) )
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_current_tags.difference( first_current_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                
            elif service_type == HC.LOCAL_TAG and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_needs = second_current_tags.difference( first_current_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, second_hashes ) ) for tag in second_current_tags ) )
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        for ( service_key, action ) in self._rating_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            first_current_value = first_media.GetRatingsManager().GetRating( service_key )
            second_current_value = second_media.GetRatingsManager().GetRating( service_key )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                if first_current_value == second_current_value:
                    
                    continue
                    
                
                if first_current_value is None and second_current_value is not None:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                    
                elif first_current_value is not None and second_current_value is None:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( first_current_value, second_hashes ) ) )
                    
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                if first_current_value == second_current_value:
                    
                    continue
                    
                
                if first_current_value is None and second_current_value is not None:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                    
                
            elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                if second_current_value is not None:
                    
                    if first_current_value is None:
                        
                        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                        
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, second_hashes ) ) )
                    
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
            
        
        #
        
        service_keys_to_content_updates = {}
        
        if self._sync_archive:
            
            if first_media.HasInbox() and second_media.HasArchive():
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, first_hashes )
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ content_update ]
                
            elif first_media.HasArchive() and second_media.HasInbox():
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, second_hashes )
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ content_update ]
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
            
        
        #
        
        service_keys_to_content_updates = {}
        
        deletee_media = []
        
        if self._delete_second_file or self._delete_both_files:
            
            if self._delete_both_files:
                
                deletee_media.append( first_media )
                
            
            deletee_media.append( second_media )
            
        
        for media in deletee_media:
            
            current_locations = media.GetLocationsManager().GetCurrent()
            
            if CC.LOCAL_FILE_SERVICE_KEY in current_locations:
                
                deletee_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            elif CC.TRASH_SERVICE_KEY in current_locations:
                
                deletee_service_key = CC.TRASH_SERVICE_KEY
                
            else:
                
                deletee_service_key = None
                
            
            if deletee_service_key is not None:
                
                if deletee_service_key not in service_keys_to_content_updates:
                    
                    service_keys_to_content_updates[ deletee_service_key ] = []
                    
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, media.GetHashes() )
                
                service_keys_to_content_updates[ deletee_service_key ].append( content_update )
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
            
        
        #
        
        return list_of_service_keys_to_content_updates
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS ] = DuplicateActionOptions

class Imageboard( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Imageboard'
    
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

class ImportFileOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FILE_OPTIONS
    SERIALISABLE_VERSION = 1
    
    def __init__( self, automatic_archive = None, exclude_deleted = None, min_size = None, min_resolution = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._automatic_archive = automatic_archive
        self._exclude_deleted = exclude_deleted
        self._min_size = min_size
        self._min_resolution = min_resolution
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._automatic_archive, self._exclude_deleted, self._min_size, self._min_resolution )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._automatic_archive, self._exclude_deleted, self._min_size, self._min_resolution ) = serialisable_info
        
    
    def FileIsValid( self, size, resolution = None ):
        
        if self._min_size is not None and size < self._min_size:
            
            return False
            
        
        if resolution is not None and self._min_resolution is not None:
            
            ( x, y ) = resolution
            
            ( min_x, min_y ) = self._min_resolution
            
            if x < min_x or y < min_y:
                
                return False
                
            
        
        return True
        
    
    def GetAutomaticArchive( self ):
        
        return self._automatic_archive
        
    
    def GetExcludeDeleted( self ):
        
        return self._exclude_deleted
        
    
    def ToTuple( self ):
        
        return ( self._automatic_archive, self._exclude_deleted, self._min_size, self._min_resolution )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FILE_OPTIONS ] = ImportFileOptions

class ImportTagOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_TAG_OPTIONS
    SERIALISABLE_VERSION = 2
    
    def __init__( self, service_keys_to_namespaces = None, service_keys_to_explicit_tags = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if service_keys_to_namespaces is None:
            
            service_keys_to_namespaces = {}
            
        
        if service_keys_to_explicit_tags is None:
            
            service_keys_to_explicit_tags = {}
            
        
        self._service_keys_to_namespaces = service_keys_to_namespaces
        self._service_keys_to_explicit_tags = service_keys_to_explicit_tags
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            test_func = services_manager.ServiceExists
            
        else:
            
            def test_func( service_key ):
                
                return True
                
            
        
        safe_service_keys_to_namespaces = { service_key.encode( 'hex' ) : list( namespaces ) for ( service_key, namespaces ) in self._service_keys_to_namespaces.items() if test_func( service_key ) }
        safe_service_keys_to_explicit_tags = { service_key.encode( 'hex' ) : list( tags ) for ( service_key, tags ) in self._service_keys_to_explicit_tags.items() if test_func( service_key ) }
        
        return ( safe_service_keys_to_namespaces, safe_service_keys_to_explicit_tags )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( safe_service_keys_to_namespaces, safe_service_keys_to_explicit_tags ) = serialisable_info
        
        self._service_keys_to_namespaces = { service_key.decode( 'hex' ) : set( namespaces ) for ( service_key, namespaces ) in safe_service_keys_to_namespaces.items() }
        self._service_keys_to_explicit_tags = { service_key.decode( 'hex' ) : set( tags ) for ( service_key, tags ) in safe_service_keys_to_explicit_tags.items() }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            safe_service_keys_to_namespaces = old_serialisable_info
            
            safe_service_keys_to_explicit_tags = {}
            
            new_serialisable_info = ( safe_service_keys_to_namespaces, safe_service_keys_to_explicit_tags )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetServiceKeysToExplicitTags( self ):
        
        return dict( self._service_keys_to_explicit_tags )
        
    
    def GetServiceKeysToNamespaces( self ):
        
        return dict( self._service_keys_to_namespaces )
        
    
    def GetServiceKeysToContentUpdates( self, hash, tags ):
        
        tags = [ tag for tag in tags if tag is not None ]
        
        service_keys_to_tags = collections.defaultdict( set )
        
        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        
        for ( service_key, namespaces ) in self._service_keys_to_namespaces.items():
            
            tags_to_add_here = []
            
            if len( namespaces ) > 0:
                
                for namespace in namespaces:
                    
                    if namespace == '': tags_to_add_here.extend( [ tag for tag in tags if not ':' in tag ] )
                    else: tags_to_add_here.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                    
                
            
            tags_to_add_here = HydrusTags.CleanTags( tags_to_add_here )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( service_key, tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        for ( service_key, explicit_tags ) in self._service_keys_to_explicit_tags.items():
            
            tags_to_add_here = HydrusTags.CleanTags( explicit_tags )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( service_key, tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        service_keys_to_content_updates = ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
        
        return service_keys_to_content_updates
        
    
    def InterestedInTags( self ):
        
        i_am_interested = len( self._service_keys_to_namespaces ) > 0
        
        return i_am_interested
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_TAG_OPTIONS ] = ImportTagOptions

class Shortcut( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, shortcut_type = None, shortcut_key = None, modifiers = None ):
        
        if shortcut_type is None:
            
            shortcut_type = CC.SHORTCUT_TYPE_KEYBOARD
            
        
        if shortcut_key is None:
            
            shortcut_key = wx.WXK_F7
            
        
        if modifiers is None:
            
            modifiers = []
            
        
        modifiers.sort()
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._shortcut_type = shortcut_type
        self._shortcut_key = shortcut_key
        self._modifiers = modifiers
        
    
    def __cmp__( self, other ):
        
        return cmp( self.ToString(), other.ToString() )
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._shortcut_type, self._shortcut_key, tuple( self._modifiers ) ).__hash__()
        
    
    def __repr__( self ):
        
        return 'Shortcut: ' + self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._shortcut_type, self._shortcut_key, self._modifiers )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._shortcut_type, self._shortcut_key, self._modifiers ) = serialisable_info
        
    
    def GetShortcutType( self ):
        
        return self._shortcut_type
        
    
    def ToString( self ):
        
        components = []
        
        if CC.SHORTCUT_MODIFIER_CTRL in self._modifiers:
            
            components.append( 'ctrl' )
            
        
        if CC.SHORTCUT_MODIFIER_ALT in self._modifiers:
            
            components.append( 'alt' )
            
        
        if CC.SHORTCUT_MODIFIER_SHIFT in self._modifiers:
            
            components.append( 'shift' )
            
        
        if self._shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD:
            
            if self._shortcut_key in range( 65, 91 ):
                
                components.append( chr( self._shortcut_key + 32 ) ) # + 32 for converting ascii A -> a
                
            elif self._shortcut_key in range( 97, 123 ):
                
                components.append( chr( self._shortcut_key ) )
                
            else:
                
                components.append( CC.wxk_code_string_lookup[ self._shortcut_key ] )
                
            
        elif self._shortcut_type == CC.SHORTCUT_TYPE_MOUSE:
            
            components.append( CC.shortcut_mouse_string_lookup[ self._shortcut_key ] )
            
        
        return '+'.join( components )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT ] = Shortcut

class Shortcuts( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._shortcuts_to_commands = {}
        
    
    def __iter__( self ):
        
        for ( shortcut, command ) in self._shortcuts_to_commands.items():
            
            yield ( shortcut, command )
            
        
    
    def __len__( self ):
        
        return len( self._shortcuts_to_commands )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ ( shortcut.GetSerialisableTuple(), command.GetSerialisableTuple() ) for ( shortcut, command ) in self._shortcuts_to_commands.items() ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( serialisable_shortcut, serialisable_command ) in serialisable_info:
            
            shortcut = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_shortcut )
            command = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_command )
            
            self._shortcuts_to_commands[ shortcut ] = command
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_mouse_actions, serialisable_keyboard_actions ) = old_serialisable_info
            
            shortcuts_to_commands = {}
            
            # this never stored mouse actions, so skip
            
            services_manager = HG.client_controller.services_manager
            
            for ( modifier, key, ( serialisable_service_key, data ) ) in serialisable_keyboard_actions:
                
                if modifier not in CC.shortcut_wx_to_hydrus_lookup:
                    
                    modifiers = []
                    
                else:
                    
                    modifiers = [ CC.shortcut_wx_to_hydrus_lookup[ modifier ] ]
                    
                
                shortcut = Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, key, modifiers )
                
                if serialisable_service_key is None:
                    
                    command = ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, data )
                    
                else:
                    
                    service_key = serialisable_service_key.decode( 'hex' )
                    
                    if not services_manager.ServiceExists( service_key ):
                        
                        continue
                        
                    
                    action = HC.CONTENT_UPDATE_FLIP
                    
                    value = data
                    
                    service = services_manager.GetService( service_key )
                    
                    service_type = service.GetServiceType()
                    
                    if service_type in HC.TAG_SERVICES:
                        
                        content_type = HC.CONTENT_TYPE_MAPPINGS
                        
                    elif service_type in HC.RATINGS_SERVICES:
                        
                        content_type = HC.CONTENT_TYPE_RATINGS
                        
                    else:
                        
                        continue
                        
                    
                    command = ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, content_type, action, value ) )
                    
                
                shortcuts_to_commands[ shortcut ] = command
                
            
            new_serialisable_info = ( ( shortcut.GetSerialisableTuple(), command.GetSerialisableTuple() ) for ( shortcut, command ) in shortcuts_to_commands.items() )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetCommand( self, shortcut ):
        
        if shortcut in self._shortcuts_to_commands:
            
            return self._shortcuts_to_commands[ shortcut ]
            
        else:
            
            return None
            
        
    
    def SetCommand( self, shortcut, command ):
        
        self._shortcuts_to_commands[ shortcut ] = command
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS ] = Shortcuts

def ConvertKeyEventToShortcut( event ):
    
    key = event.KeyCode
    
    if key in range( 65, 91 ) or key in CC.wxk_code_string_lookup.keys():
        
        modifiers = []
        
        if event.AltDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_ALT )
            
        
        if event.CmdDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_CTRL )
            
        
        if event.ShiftDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_SHIFT )
            
        
        shortcut = Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, key, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'key event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
def ConvertKeyEventToSimpleTuple( event ):
    
    modifier = wx.ACCEL_NORMAL
    
    if event.AltDown(): modifier = wx.ACCEL_ALT
    elif event.CmdDown(): modifier = wx.ACCEL_CTRL
    elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
    
    key = event.KeyCode
    
    return ( modifier, key )
    
def ConvertMouseEventToShortcut( event ):
    
    key = None
    
    if event.LeftDown() or event.LeftDClick():
        
        key = CC.SHORTCUT_MOUSE_LEFT
        
    elif event.MiddleDown() or event.MiddleDClick():
        
        key = CC.SHORTCUT_MOUSE_MIDDLE
        
    elif event.RightDown() or event.RightDClick():
        
        key = CC.SHORTCUT_MOUSE_RIGHT
        
    elif event.GetWheelRotation() > 0:
        
        key = CC.SHORTCUT_MOUSE_SCROLL_UP
        
    elif event.GetWheelRotation() < 0:
        
        key = CC.SHORTCUT_MOUSE_SCROLL_DOWN
        
    
    if key is not None:
        
        modifiers = []
        
        if event.AltDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_ALT )
            
        
        if event.CmdDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_CTRL )
            
        
        if event.ShiftDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_SHIFT )
            
        
        shortcut = Shortcut( CC.SHORTCUT_TYPE_MOUSE, key, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'mouse event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
class TagCensor( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_CENSOR
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._tag_slices_to_rules = {}
        
    
    def __eq__( self, other ):
        
        return self._tag_slices_to_rules == other._tag_slices_to_rules
        
    
    def _GetRulesForTag( self, tag ):
        
        rules = []
        tag_slices = []
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        tag_slices.append( tag )
        
        if namespace != '':
            
            tag_slices.append( namespace + ':' )
            tag_slices.append( ':' )
            
        else:
            
            tag_slices.append( '' )
            
        
        for tag_slice in tag_slices:
            
            if tag_slice in self._tag_slices_to_rules:
                
                rule = self._tag_slices_to_rules[ tag_slice ]
                
                rules.append( rule )
                
            
        
        return rules
        
    
    def _GetSerialisableInfo( self ):
        
        return self._tag_slices_to_rules.items()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._tag_slices_to_rules = dict( serialisable_info )
        
    
    def _TagOK( self, tag ):
        
        rules = self._GetRulesForTag( tag )
        
        if CC.CENSOR_WHITELIST in rules: # There is an exception for this tag
            
            return True
            
        elif CC.CENSOR_BLACKLIST in rules: # There is a rule against this tag
            
            return False
            
        else: # There are no rules for this tag
            
            return True
            
        
    
    def Censor( self, tags ):
        
        with self._lock:
            
            return { tag for tag in tags if self._TagOK( tag ) }
            
        
    
    def GetTagSlicesToRules( self ):
        
        with self._lock:
            
            return dict( self._tag_slices_to_rules )
            
        
    
    def SetRule( self, tag_slice, rule ):
        
        with self._lock:
            
            self._tag_slices_to_rules[ tag_slice ] = rule
            
        
    
    def ToCensoredString( self ):
        
        blacklist = []
        whitelist = []
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if rule == CC.CENSOR_BLACKLIST:
                
                blacklist.append( tag_slice )
                
            elif rule == CC.CENSOR_WHITELIST:
                
                whitelist.append( tag_slice )
                
            
        
        blacklist.sort()
        whitelist.sort()
        
        if len( blacklist ) == 0:
            
            return 'all tags allowed'
            
        else:
            
            if set( blacklist ) == { '', ':' }:
                
                text = 'no tags allowed'
                
            else:
                
                text = 'censoring ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                
            
            if len( whitelist ) > 0:
                
                text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                
            
            return text
            
        
    
    def ToPermittedString( self ):
        
        blacklist = []
        whitelist = []
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if rule == CC.CENSOR_BLACKLIST:
                
                blacklist.append( tag_slice )
                
            elif rule == CC.CENSOR_WHITELIST:
                
                whitelist.append( tag_slice )
                
            
        
        blacklist.sort()
        whitelist.sort()
        
        if len( blacklist ) == 0:
            
            return 'all tags'
            
        else:
            
            if set( blacklist ) == { '', ':' }:
                
                text = 'no tags'
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
            else:
                
                text = 'all tags except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                
                if len( whitelist ) > 0:
                    
                    text += ' (except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) ) + ')'
                    
                
            
        
        text += ' permitted'
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_CENSOR ] = TagCensor
