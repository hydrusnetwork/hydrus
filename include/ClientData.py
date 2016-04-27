import ClientConstants as CC
import ClientDefaults
import ClientDownloading
import ClientFiles
import ClientNetworking
import ClientThreading
import collections
import datetime
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusPaths
import HydrusSerialisable
import HydrusTags
import threading
import traceback
import os
import random
import requests
import shutil
import sqlite3
import stat
import sys
import time
import urllib
import wx
import yaml
import HydrusData
import HydrusGlobals
import HydrusThreading

def AddPaddingToDimensions( dimensions, padding ):
    
    ( x, y ) = dimensions
    
    return ( x + padding, y + padding )
    
def CatchExceptionClient( etype, value, tb ):
    
    try:
        
        job_key = ClientThreading.JobKey()
        
        if etype == HydrusExceptions.ShutdownException:
            
            return
            
        elif etype == HydrusExceptions.DBException:
            
            ( text, caller_traceback, db_traceback ) = value
            
            job_key.SetVariable( 'popup_title', 'Database Error!' )
            job_key.SetVariable( 'popup_text_1', text )
            job_key.SetVariable( 'popup_caller_traceback', caller_traceback )
            job_key.SetVariable( 'popup_db_traceback', db_traceback )
            
        else:
            
            trace_list = traceback.format_tb( tb )
            
            trace = ''.join( trace_list )
            
            if etype == wx.PyDeadObjectError:
                
                HydrusData.Print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
                HydrusData.Print( HydrusData.ToUnicode( value ) )
                HydrusData.Print( trace )
                
                return
                
            
            try: job_key.SetVariable( 'popup_title', HydrusData.ToUnicode( etype.__name__ ) )
            except: job_key.SetVariable( 'popup_title', HydrusData.ToUnicode( etype ) )
            job_key.SetVariable( 'popup_text_1', HydrusData.ToUnicode( value ) )
            job_key.SetVariable( 'popup_traceback', trace )
            
        
        text = job_key.ToString()
        
        HydrusData.Print( 'Uncaught exception:' )
        
        HydrusData.DebugPrint( text )
        
        HydrusGlobals.client_controller.pub( 'message', job_key )
        
    except:
        
        text = 'Encountered an error I could not parse:'
        
        text += os.linesep
        
        text += HydrusData.ToUnicode( ( etype, value, tb ) )
        
        try: text += traceback.format_exc()
        except: pass
        
        HydrusData.ShowText( text )
        
    
    time.sleep( 1 )
    
def ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates ):
    
    num_files = 0
    actions = set()
    locations = set()
    
    extra_words = ''
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
        if len( content_updates ) > 0:
            
            name = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key ).GetName()
            
            locations.add( name )
            
        
        for content_update in content_updates:
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            if data_type == HC.CONTENT_TYPE_MAPPINGS: extra_words = ' tags for'
            
            actions.add( HC.content_update_string_lookup[ action ] )
            
            num_files += len( content_update.GetHashes() )
            
        
    
    s = ', '.join( locations ) + '->' + ', '.join( actions ) + extra_words + ' ' + HydrusData.ConvertIntToPrettyString( num_files ) + ' files'
    
    return s
    
def ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hashes, service_keys_to_tags ):
    
    service_keys_to_content_updates = {}
    
    for ( service_key, tags ) in service_keys_to_tags.items():
        
        if service_key == CC.LOCAL_TAG_SERVICE_KEY: action = HC.CONTENT_UPDATE_ADD
        else: action = HC.CONTENT_UPDATE_PEND
        
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
    
def ConvertZoomToPercentage( zoom ):
    
    zoom_percent = zoom * 100
    
    if zoom in CC.ZOOMS:
        
        pretty_zoom = '%i' % zoom_percent + '%'
        
    else:
        
        pretty_zoom = '%.2f' % zoom_percent + '%'
        
    
    return pretty_zoom
    
def DeletePath( path ):
    
    if HC.options[ 'delete_to_recycle_bin' ] == True:
        
        HydrusPaths.RecyclePath( path )
        
    else:
        
        HydrusPaths.DeletePath( path )
        
    
def GenerateService( service_key, service_type, name, info ):
    
    if service_type in HC.REPOSITORIES:
        
        cl = ServiceRepository
        
    elif service_type in HC.RESTRICTED_SERVICES:
        
        cl = ServiceRestricted
        
    elif service_type == HC.IPFS:
        
        cl = ServiceIPFS
        
    elif service_type in HC.REMOTE_SERVICES:
        
        cl = ServiceRemote
        
    elif service_type == HC.LOCAL_BOORU:
        
        cl = ServiceLocalBooru
        
    else:
        
        cl = Service
        
    
    return cl( service_key, service_type, name, info )
    
def GetMediasTagCount( pool, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, collapse_siblings = False ):
    
    siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
    
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
        
        if collapse_siblings:
            
            statuses_to_tags = siblings_manager.CollapseStatusesToTags( statuses_to_tags )
            
        
        current_tags_to_count.update( statuses_to_tags[ HC.CURRENT ] )
        deleted_tags_to_count.update( statuses_to_tags[ HC.DELETED ] )
        pending_tags_to_count.update( statuses_to_tags[ HC.PENDING ] )
        petitioned_tags_to_count.update( statuses_to_tags[ HC.PETITIONED ] )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    
def ShowExceptionClient( e ):
    
    job_key = ClientThreading.JobKey()
    
    if isinstance( e, HydrusExceptions.ShutdownException ):
        
        return
        
    elif isinstance( e, HydrusExceptions.DBException ):
        
        ( text, caller_traceback, db_traceback ) = e.args
        
        job_key.SetVariable( 'popup_title', 'Database Error!' )
        job_key.SetVariable( 'popup_text_1', text )
        job_key.SetVariable( 'popup_caller_traceback', caller_traceback )
        job_key.SetVariable( 'popup_db_traceback', db_traceback )
        
    else:
        
        ( etype, value, tb ) = sys.exc_info()
        
        if etype is None:
            
            etype = type( e )
            value = HydrusData.ToUnicode( e )
            
            trace = ''.join( traceback.format_stack() )
            
        else: trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
        if etype == wx.PyDeadObjectError:
            
            HydrusData.Print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
            HydrusData.Print( HydrusData.ToUnicode( value ) )
            HydrusData.Print( trace )
            
            return
            
        
        if hasattr( etype, '__name__' ): title = HydrusData.ToUnicode( etype.__name__ )
        else: title = HydrusData.ToUnicode( etype )
        
        job_key.SetVariable( 'popup_title', title )
        job_key.SetVariable( 'popup_text_1', HydrusData.ToUnicode( value ) )
        job_key.SetVariable( 'popup_traceback', trace )
        
    
    text = job_key.ToString()
    
    HydrusData.Print( 'Exception:' )
    
    HydrusData.DebugPrint( text )
    
    HydrusGlobals.client_controller.pub( 'message', job_key )
    
    time.sleep( 1 )
    
def ShowTextClient( text ):
    
    job_key = ClientThreading.JobKey()
    
    job_key.SetVariable( 'popup_text_1', HydrusData.ToUnicode( text ) )
    
    text = job_key.ToString()
    
    HydrusData.Print( text )
    
    HydrusGlobals.client_controller.pub( 'message', job_key )
    
def SortTagsList( tags, sort_type ):
    
    if sort_type in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC ):
        
        sort_type = CC.SORT_BY_INCIDENCE_ASC
        
    
    if sort_type in ( CC.SORT_BY_LEXICOGRAPHIC_DESC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
        
        reverse = True
        
    else:
        
        reverse = False
        
    
    if sort_type in ( CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
        
        def key( tag ):
            
            if ':' in tag:
                
                return tag.split( ':', 1 )
                
            else:
                
                return ( '{', tag ) # '{' is above 'z' in ascii, so this works for most situations
                
            
        
    else:
        
        key = None
        
    
    tags.sort( key = key, reverse = reverse )
    
def WaitPolitely( page_key = None ):
    
    if page_key is not None:
        
        HydrusGlobals.client_controller.pub( 'waiting_politely', page_key, True )
        
    
    time.sleep( HC.options[ 'website_download_polite_wait' ] )
    
    if page_key is not None:
        
        HydrusGlobals.client_controller.pub( 'waiting_politely', page_key, False )
        
    
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
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._dictionary = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
        self._InitialiseDefaults()
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            serialisable_info = self._dictionary.GetSerialisableTuple()
            
            return serialisable_info
            
        
    
    def _InitialiseDefaults( self ):
        
        self._dictionary[ 'default_import_tag_options' ] = HydrusSerialisable.SerialisableDictionary()
        
        self._dictionary[ 'booleans' ] = {}
        
        self._dictionary[ 'booleans' ][ 'apply_all_parents_to_all_services' ] = False
        self._dictionary[ 'booleans' ][ 'apply_all_siblings_to_all_services' ] = False
        self._dictionary[ 'booleans' ][ 'filter_inbox_and_archive_predicates' ] = True
        self._dictionary[ 'booleans' ][ 'waiting_politely_text' ] = False
        
        self._dictionary[ 'booleans' ][ 'show_thumbnail_title_banner' ] = True
        self._dictionary[ 'booleans' ][ 'show_thumbnail_page' ] = True
        
        self._dictionary[ 'booleans' ][ 'disable_cv_for_static_images' ] = False
        
        self._dictionary[ 'noneable_integers' ] = {}
        
        self._dictionary[ 'noneable_integers' ][ 'forced_search_limit' ] = None
        
        self._dictionary[ 'client_files_locations_ideal_weights' ] = [ ( HydrusPaths.ConvertAbsPathToPortablePath( HC.CLIENT_FILES_DIR ), 1.0 ) ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        loaded_dictionary = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
        
        for ( key, value ) in loaded_dictionary.items():
            
            if isinstance( value, dict ):
                
                self._dictionary[ key ].update( value )
                
            else:
                
                self._dictionary[ key ] = value
                
            
        
    
    def ClearDefaultImportTagOptions( self ):
        
        with self._lock:
            
            self._dictionary[ 'default_import_tag_options' ] = HydrusSerialisable.SerialisableDictionary()
            
        
    
    def GetBoolean( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'booleans' ][ name ]
            
        
    
    def GetClientFilesLocationsToIdealWeights( self ):
        
        with self._lock:
            
            result = {}
            
            for ( portable_path, weight ) in self._dictionary[ 'client_files_locations_ideal_weights' ]:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_path )
                
                result[ abs_path ] = weight
                
            
            return result
            
        
    
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
                
            
        
    
    def GetNoneableInteger( self, name ):
        
        with self._lock:
            
            return self._dictionary[ 'noneable_integers' ][ name ]
            
        
    
    def SetBoolean( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'booleans' ][ name ] = value
            
        
    
    def SetClientFilesLocationsToIdealWeights( self, locations_to_weights ):
        
        with self._lock:
            
            portable_locations_and_weights = [ ( HydrusPaths.ConvertAbsPathToPortablePath( location ), float( weight ) ) for ( location, weight ) in locations_to_weights.items() ]
            
            self._dictionary[ 'client_files_locations_ideal_weights' ] = portable_locations_and_weights
            
        
    
    def SetDefaultImportTagOptions( self, gallery_identifier, import_tag_options ):
        
        with self._lock:
            
            self._dictionary[ 'default_import_tag_options' ][ gallery_identifier ] = import_tag_options
            
        
    
    def SetNoneableInteger( self, name, value ):
        
        with self._lock:
            
            self._dictionary[ 'noneable_integers' ][ name ] = value
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS ] = ClientOptions

class CommandHandler( object ):
    
    def __init__( self, action_cache ):
        
        self._action_cache = action_cache
        self._commands_to_callables = {}
        
    
    def ProcessMenuEvent( self, menu_event ):
        
        event_id = menu_event.GetId()
        
        action = self._action_cache.GetAction( event_id )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command in self._commands_to_callables:
                
                callable = self._commands_to_callables[ command ]
                
                if data is None:
                    
                    wx.CallAfter( callable )
                    
                else:
                    
                    wx.CallAfter( callable, data )
                    
                
            
        
    
    def SetCallable( self, command, callable ):
        
        self._commands_to_callables[ command ] = callable
        

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

class Imageboard( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Imageboard'
    
    def __init__( self, name, post_url, flood_time, form_fields, restrictions ):
        
        self._name = name
        self._post_url = post_url
        self._flood_time = flood_time
        self._form_fields = form_fields
        self._restrictions = restrictions
        
    
    def IsOkToPost( self, media_result ):
        
        ( hash, inbox, size, mime, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = media_result.ToTuple()
        
        if CC.RESTRICTION_MIN_RESOLUTION in self._restrictions:
            
            ( min_width, min_height ) = self._restrictions[ CC.RESTRICTION_MIN_RESOLUTION ]
            
            if width < min_width or height < min_height: return False
            
        
        if CC.RESTRICTION_MAX_RESOLUTION in self._restrictions:
            
            ( max_width, max_height ) = self._restrictions[ CC.RESTRICTION_MAX_RESOLUTION ]
            
            if width > max_width or height > max_height: return False
            
        
        if CC.RESTRICTION_MAX_FILE_SIZE in self._restrictions and size > self._restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ]: return False
        
        if CC.RESTRICTION_ALLOWED_MIMES in self._restrictions and mime not in self._restrictions[ CC.RESTRICTION_ALLOWED_MIMES ]: return False
        
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
        
        safe_service_keys_to_namespaces = { service_key.encode( 'hex' ) : list( namespaces ) for ( service_key, namespaces ) in self._service_keys_to_namespaces.items() }
        safe_service_keys_to_explicit_tags = { service_key.encode( 'hex' ) : list( tags ) for ( service_key, tags ) in self._service_keys_to_explicit_tags.items() }
        
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
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
        
        for ( service_key, namespaces ) in self._service_keys_to_namespaces.items():
            
            tags_to_add_here = []
            
            if len( namespaces ) > 0:
                
                for namespace in namespaces:
                    
                    if namespace == '': tags_to_add_here.extend( [ tag for tag in tags if not ':' in tag ] )
                    else: tags_to_add_here.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                    
                
            
            tags_to_add_here = HydrusTags.CleanTags( tags_to_add_here )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        for ( service_key, explicit_tags ) in self._service_keys_to_explicit_tags.items():
            
            tags_to_add_here = HydrusTags.CleanTags( explicit_tags )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        service_keys_to_content_updates = ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
        
        return service_keys_to_content_updates
        
    
    def ShouldFetchTags( self ):
        
        i_am_interested_in_namespaces = len( self._service_keys_to_namespaces ) > 0
        
        return i_am_interested_in_namespaces
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_TAG_OPTIONS ] = ImportTagOptions

class Service( object ):
    
    def __init__( self, service_key, service_type, name, info ):
        
        self._service_key = service_key
        self._service_type = service_type
        self._name = name
        self._info = info
        
        self._lock = threading.Lock()
        
        HydrusGlobals.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        
    
    def __hash__( self ): return self._service_key.__hash__()
    
    def _ProcessServiceUpdate( self, service_update ):
        
        pass
        
    
    def GetInfo( self, key = None ):
        
        if key is None:
            
            return self._info
            
        else:
            
            return self._info[ key ]
            
        
    
    def GetServiceKey( self ): return self._service_key
    
    def GetName( self ): return self._name
    
    def GetServiceType( self ): return self._service_type
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                if service_key == self._service_key:
                    
                    self._ProcessServiceUpdate( service_update )
                    
                
            
        
    
    def ToTuple( self ): return ( self._service_key, self._service_type, self._name, self._info )
    
class ServiceLocalBooru( Service ):
    
    def _ProcessServiceUpdate( self, service_update ):
        
        Service._ProcessServiceUpdate( self, service_update )
        
        ( action, row ) = service_update.ToTuple()
        
        if action == HC.SERVICE_UPDATE_REQUEST_MADE:
            
            num_bytes = row
            
            self._info[ 'used_monthly_data' ] += num_bytes
            self._info[ 'used_monthly_requests' ] += 1
            
        
    
class ServiceRemote( Service ):
    
    def GetCredentials( self ):
        
        host = self._info[ 'host' ]
        port = self._info[ 'port' ]
        
        credentials = Credentials( host, port )
        
        return credentials
        
    
    def _GetErrorWaitPeriod( self ):
        
        return 3600 * 4
        
    
    def _ProcessServiceUpdate( self, service_update ):
        
        Service._ProcessServiceUpdate( self, service_update )
        
        ( action, row ) = service_update.ToTuple()
        
        if action == HC.SERVICE_UPDATE_ERROR:
            
            self._info[ 'last_error' ] = HydrusData.GetNow()
            
        elif action == HC.SERVICE_UPDATE_RESET:
            
            self._info[ 'last_error' ] = 0
            
        
    
    def GetRecentErrorPending( self ):
        
        return HydrusData.ConvertTimestampToPrettyPending( self._info[ 'last_error' ] + self._GetErrorWaitPeriod() )
        
    
    def HasRecentError( self ):
        
        return not HydrusData.TimeHasPassed( self._info[ 'last_error' ] + self._GetErrorWaitPeriod() )
        
    
    def SetCredentials( self, credentials ):
        
        ( host, port ) = credentials.GetAddress()
        
        self._info[ 'host' ] = host
        self._info[ 'port' ] = port
        
    
class ServiceRestricted( ServiceRemote ):
    
    def _GetErrorWaitPeriod( self ):
        
        if 'account' in self._info and self._info[ 'account' ].HasPermission( HC.GENERAL_ADMIN ):
            
            return 900
            
        else:
            
            return ServiceRemote._GetErrorWaitPeriod( self )
            
        
    
    def _ProcessServiceUpdate( self, service_update ):
        
        ServiceRemote._ProcessServiceUpdate( self, service_update )
        
        ( action, row ) = service_update.ToTuple()
        
        if action == HC.SERVICE_UPDATE_ACCOUNT:
            
            account = row
            
            self._info[ 'account' ] = account
            self._info[ 'last_error' ] = 0
            
        elif action == HC.SERVICE_UPDATE_REQUEST_MADE:
            
            num_bytes = row
            
            self._info[ 'account' ].RequestMade( num_bytes )
            
        
    
    def _RecordHydrusBandwidth( self, method, command, data_used ):
        
        if ( self._service_type, method, command ) in HC.BANDWIDTH_CONSUMING_REQUESTS:
            
            HydrusGlobals.client_controller.pub( 'service_updates_delayed', { self._service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_REQUEST_MADE, data_used ) ] } )
            
        
    
    def CanDownload( self ):
        
        return self._info[ 'account' ].HasPermission( HC.GET_DATA ) and not self.HasRecentError()
        
    
    def CanUpload( self ): return self._info[ 'account' ].HasPermission( HC.POST_DATA ) and not self.HasRecentError()
    
    def GetCredentials( self ):
        
        host = self._info[ 'host' ]
        port = self._info[ 'port' ]
        
        if 'access_key' in self._info:
            
            access_key = self._info[ 'access_key' ]
            
        else:
            
            access_key = None
            
        
        credentials = Credentials( host, port, access_key )
        
        return credentials
        
    
    def IsInitialised( self ):
        
        if self._service_type == HC.SERVER_ADMIN:
            
            return 'access_key' in self._info
            
        else:
            
            return True
            
        
    
    def Request( self, method, command, request_args = None, request_headers = None, report_hooks = None, temp_path = None, return_cookies = False ):
        
        if request_args is None: request_args = {}
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        try:
            
            credentials = self.GetCredentials()
            
            if command in ( 'access_key', 'init', '' ):
                
                pass
                
            elif command in ( 'session_key', 'access_key_verification' ):
                
                ClientNetworking.AddHydrusCredentialsToHeaders( credentials, request_headers )
                
            else:
                
                ClientNetworking.AddHydrusSessionKeyToHeaders( self._service_key, request_headers )
                
            
            path = '/' + command
            
            if method == HC.GET:
                
                query = ClientNetworking.ConvertHydrusGETArgsToQuery( request_args )
                
                body = ''
                
            elif method == HC.POST:
                
                query = ''
                
                if command == 'file':
                    
                    content_type = HC.APPLICATION_OCTET_STREAM
                    
                    body = request_args[ 'file' ]
                    
                    del request_args[ 'file' ]
                    
                else:
                    
                    if isinstance( request_args, HydrusSerialisable.SerialisableDictionary ):
                        
                        content_type = HC.APPLICATION_JSON
                        
                        body = request_args.DumpToNetworkString()
                        
                    else:
                        
                        content_type = HC.APPLICATION_YAML
                        
                        body = yaml.safe_dump( request_args )
                        
                    
                
                request_headers[ 'Content-Type' ] = HC.mime_string_lookup[ content_type ]
                
            
            if query != '':
                
                path_and_query = path + '?' + query
                
            else:
                
                path_and_query = path
                
            
            ( host, port ) = credentials.GetAddress()
            
            url = 'http://' + host + ':' + str( port ) + path_and_query
            
            ( response, size_of_response, response_headers, cookies ) = HydrusGlobals.client_controller.DoHTTP( method, url, request_headers, body, report_hooks = report_hooks, temp_path = temp_path, return_everything = True )
            
            ClientNetworking.CheckHydrusVersion( self._service_key, self._service_type, response_headers )
            
            if method == HC.GET:
                
                data_used = size_of_response
                
            elif method == HC.POST:
                
                data_used = len( body )
                
            
            self._RecordHydrusBandwidth( method, command, data_used )
            
            if return_cookies:
                
                return ( response, cookies )
                
            else:
                
                return response
                
            
        except Exception as e:
            
            if not isinstance( e, HydrusExceptions.ServerBusyException ):
                
                if isinstance( e, HydrusExceptions.SessionException ):
                    
                    session_manager = HydrusGlobals.client_controller.GetClientSessionManager()
                    
                    session_manager.DeleteSessionKey( self._service_key )
                    
                
                HydrusGlobals.client_controller.Write( 'service_updates', { self._service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ERROR, HydrusData.ToUnicode( e ) ) ] } )
                
                if isinstance( e, HydrusExceptions.PermissionException ):
                    
                    if 'account' in self._info:
                        
                        account_key = self._info[ 'account' ].GetAccountKey()
                        
                        unknown_account = HydrusData.GetUnknownAccount( account_key )
                        
                    else: unknown_account = HydrusData.GetUnknownAccount()
                    
                    HydrusGlobals.client_controller.Write( 'service_updates', { self._service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, unknown_account ) ] } )
                    
                
            
            raise
            
        
    
    def SetCredentials( self, credentials ):
        
        ServiceRemote.SetCredentials( self, credentials )
        
        if credentials.HasAccessKey():
            
            self._info[ 'access_key' ] = credentials.GetAccessKey()
            
        
    
class ServiceRepository( ServiceRestricted ):
    
    def _ProcessServiceUpdate( self, service_update ):
        
        ServiceRestricted._ProcessServiceUpdate( self, service_update )
        
        ( action, row ) = service_update.ToTuple()
        
        if action == HC.SERVICE_UPDATE_RESET:
            
            if 'next_processing_timestamp' in self._info:
                
                self._info[ 'next_processing_timestamp' ] = 0
                
            
        elif action == HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP:
            
            next_download_timestamp = row
            
            if next_download_timestamp > self._info[ 'next_download_timestamp' ]:
                
                if self._info[ 'first_timestamp' ] is None: self._info[ 'first_timestamp' ] = next_download_timestamp
                
                self._info[ 'next_download_timestamp' ] = next_download_timestamp
                
            
        elif action == HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP:
            
            next_processing_timestamp = row
            
            if next_processing_timestamp > self._info[ 'next_processing_timestamp' ]:
                
                self._info[ 'next_processing_timestamp' ] = next_processing_timestamp
                
            
        elif action == HC.SERVICE_UPDATE_PAUSE:
            
            self._info[ 'paused' ] = True
            
        
    
    def _ReportSyncProcessingError( self, path, error_text ):
        
        text = 'While synchronising ' + self._name + ', the expected update file ' + path + ', ' + error_text + '.'
        text += os.linesep * 2
        text += 'The service has been indefinitely paused.'
        text += os.linesep * 2
        text += 'This is a serious error. Unless you know what went wrong, you should contact the developer.'
        
        HydrusData.ShowText( text )
        
        service_updates = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_PAUSE ) ]
        
        service_keys_to_service_updates = { self._service_key : service_updates }
        
        self.ProcessServiceUpdates( service_keys_to_service_updates )
        
        HydrusGlobals.client_controller.Write( 'service_updates', service_keys_to_service_updates )
        
    
    def CanDownloadUpdate( self ):
        
        work_to_do = self.IsUpdateDueForDownload()
        
        return work_to_do and self.CanDownload() and not self.IsPaused()
        
    
    def CanProcessUpdate( self ):
        
        work_to_do = self.IsUpdateDueForProcessing()
        
        it_is_time = HydrusData.TimeHasPassed( self._info[ 'next_processing_timestamp' ] + HC.UPDATE_DURATION + HC.options[ 'processing_phase' ] )
        
        return work_to_do and it_is_time and not self.IsPaused()
        
    
    def GetTimestamps( self ): return ( self._info[ 'first_timestamp' ], self._info[ 'next_download_timestamp' ], self._info[ 'next_processing_timestamp' ] )
    
    def GetUpdateStatus( self ):
        
        account = self._info[ 'account' ]
        
        now = HydrusData.GetNow()
        first_timestamp = self._info[ 'first_timestamp' ]
        next_download_timestamp = self._info[ 'next_download_timestamp' ]
        next_processing_timestamp = self._info[ 'next_processing_timestamp' ]
        
        if first_timestamp is None:
            
            num_updates = 0
            num_updates_downloaded = 0
            num_updates_processed = 0
            
        else:
            
            num_updates = ( now - first_timestamp ) / HC.UPDATE_DURATION
            num_updates_downloaded = ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION
            num_updates_processed = max( 0, ( next_processing_timestamp - first_timestamp ) / HC.UPDATE_DURATION )
            
        
        downloaded_text = 'downloaded ' + HydrusData.ConvertValueRangeToPrettyString( num_updates_downloaded, num_updates )
        processed_text = 'processed ' + HydrusData.ConvertValueRangeToPrettyString( num_updates_processed, num_updates )
        
        if self.IsPaused() or not self._info[ 'account' ].HasPermission( HC.GET_DATA ): status = 'updates on hold'
        else:
            
            if self.CanDownloadUpdate(): status = 'downloaded up to ' + HydrusData.ConvertTimestampToPrettySync( self._info[ 'next_download_timestamp' ] )
            elif self.CanProcessUpdate(): status = 'processed up to ' + HydrusData.ConvertTimestampToPrettySync( self._info[ 'next_processing_timestamp' ] )
            elif self.HasRecentError(): status = 'due to a previous error, update is delayed - next check ' + self.GetRecentErrorPending()
            else:
                
                if HydrusData.TimeHasPassed( self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION ):
                    
                    status = 'next update will be downloaded soon'
                    
                else:
                    
                    status = 'fully synchronised - next update ' + HydrusData.ConvertTimestampToPrettyPending( self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 )
                    
                
            
        
        return downloaded_text + ' - ' + processed_text + ' - ' + status
        
    
    def IsPaused( self ):
        
        return self._info[ 'paused' ]
        
    
    def IsUpdateDueForDownload( self ):
        
        return HydrusData.TimeHasPassed( self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 )
        
    
    def IsUpdateDueForProcessing( self ):
        
        return self._info[ 'next_download_timestamp' ] > self._info[ 'next_processing_timestamp' ]
        
    
    def Sync( self, only_when_idle = False, stop_time = None ):
        
        if self.IsPaused():
            
            return
            
        
        if not self.CanDownloadUpdate() and not self.CanProcessUpdate():
            
            return
            
        
        job_key = ClientThreading.JobKey( pausable = False, cancellable = True, only_when_idle = only_when_idle, stop_time = stop_time )
        
        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
        
        if should_quit:
            
            return
            
        
        num_updates_downloaded = 0
        num_updates_processed = 0
        total_content_weight_processed = 0
        
        try:
            
            options = HydrusGlobals.client_controller.GetOptions()
            
            HydrusGlobals.client_controller.pub( 'splash_set_title_text', self._name )
            job_key.SetVariable( 'popup_title', 'repository synchronisation - ' + self._name )
            
            HydrusGlobals.client_controller.pub( 'message', job_key )
            
            try:
                
                while self.CanDownloadUpdate():
                    
                    if options[ 'pause_repo_sync' ]:
                        
                        break
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        break
                        
                    
                    if self._info[ 'first_timestamp' ] is None:
                        
                        gauge_range = None
                        gauge_value = 0
                        
                        update_index_string = 'initial update: '
                        
                    else:
                        
                        gauge_range = ( HydrusData.GetNow() - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION
                        gauge_value = ( ( self._info[ 'next_download_timestamp' ] - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION ) + 1
                        
                        update_index_string = 'update ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range ) + ': '
                        
                    
                    subupdate_index_string = 'service update: '
                    
                    HydrusGlobals.client_controller.pub( 'splash_set_title_text', self._name + ' - ' + update_index_string + subupdate_index_string )
                    HydrusGlobals.client_controller.pub( 'splash_set_status_text', 'downloading' )
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'downloading and parsing' )
                    job_key.SetVariable( 'popup_gauge_1', ( gauge_value, gauge_range ) )
                    
                    service_update_package = self.Request( HC.GET, 'service_update_package', { 'begin' : self._info[ 'next_download_timestamp' ] } )
                    
                    begin = service_update_package.GetBegin()
                    
                    subindex_count = service_update_package.GetSubindexCount()
                    
                    for subindex in range( subindex_count ):
                        
                        path = ClientFiles.GetExpectedContentUpdatePackagePath( self._service_key, begin, subindex )
                        
                        if os.path.exists( path ):
                            
                            size = os.path.getsize( path )
                            
                            if size == 0:
                                
                                os.remove( path )
                                
                            
                        
                        if not os.path.exists( path ):
                            
                            subupdate_index_string = 'content update ' + HydrusData.ConvertValueRangeToPrettyString( subindex + 1, subindex_count ) + ': '
                            
                            HydrusGlobals.client_controller.pub( 'splash_set_title_text', self._name + ' - ' + update_index_string + subupdate_index_string )
                            job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'downloading and parsing' )
                            
                            content_update_package = self.Request( HC.GET, 'content_update_package', { 'begin' : begin, 'subindex' : subindex } )
                            
                            obj_string = content_update_package.DumpToString()
                            
                            job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'saving to disk' )
                            
                            with open( path, 'wb' ) as f: f.write( obj_string )
                            
                        
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + 'committing' )
                    
                    path = ClientFiles.GetExpectedServiceUpdatePackagePath( self._service_key, begin )
                    
                    obj_string = service_update_package.DumpToString()
                    
                    with open( path, 'wb' ) as f: f.write( obj_string )
                    
                    service_updates = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP, service_update_package.GetNextBegin() ) ]
                    
                    service_keys_to_service_updates = { self._service_key : service_updates }
                    
                    self.ProcessServiceUpdates( service_keys_to_service_updates )
                    
                    HydrusGlobals.client_controller.Write( 'service_updates', service_keys_to_service_updates )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                    num_updates_downloaded += 1
                    
                
            except HydrusExceptions.ServerBusyException:
                
                job_key.SetVariable( 'popup_text_1', 'Server was too busy to respond for now, will continue with processing.' )
                
                time.sleep( 3 )
                
            except Exception as e:
                
                if 'Could not connect' in str( e ):
                    
                    job_key.SetVariable( 'popup_text_1', 'Could not connect to service, will continue with processing.' )
                    
                    time.sleep( 5 )
                    
                else:
                    
                    raise
                    
                
            
            while self.CanProcessUpdate():
                
                if options[ 'pause_repo_sync' ]:
                    
                    break
                    
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    break
                    
                
                gauge_range = ( ( HydrusData.GetNow() - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION )
                
                gauge_value = ( ( self._info[ 'next_processing_timestamp' ] - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION ) + 1
                
                update_index_string = 'update ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range ) + ': '
                
                subupdate_index_string = 'service update: '
                
                HydrusGlobals.client_controller.pub( 'splash_set_title_text', self._name + ' - ' + update_index_string + subupdate_index_string )
                HydrusGlobals.client_controller.pub( 'splash_set_status_text', 'processing' )
                job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'loading from disk' )
                job_key.SetVariable( 'popup_gauge_1', ( gauge_value, gauge_range ) )
                
                path = ClientFiles.GetExpectedServiceUpdatePackagePath( self._service_key, self._info[ 'next_processing_timestamp' ] )
                
                if not os.path.exists( path ):
                    
                    self._ReportSyncProcessingError( path, 'was missing' )
                    
                    return
                    
                
                with open( path, 'rb' ) as f: obj_string = f.read()
                
                try:
                    
                    service_update_package = HydrusSerialisable.CreateFromString( obj_string )
                    
                    if not isinstance( service_update_package, HydrusData.ServerToClientServiceUpdatePackage ):
                        
                        raise Exception()
                        
                    
                except:
                    
                    self._ReportSyncProcessingError( path, 'did not parse' )
                    
                    return
                    
                
                subindex_count = service_update_package.GetSubindexCount()
                
                processing_went_ok = True
                
                for subindex in range( subindex_count ):
                    
                    should_break = False
                    
                    if options[ 'pause_repo_sync' ]:
                        
                        should_break = True
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit or should_break:
                        
                        processing_went_ok = False
                        
                        break
                        
                    
                    subupdate_index_string = 'content update ' + HydrusData.ConvertValueRangeToPrettyString( subindex + 1, subindex_count ) + ': '
                    
                    path = ClientFiles.GetExpectedContentUpdatePackagePath( self._service_key, self._info[ 'next_processing_timestamp' ], subindex )
                    
                    if not os.path.exists( path ):
                        
                        self._ReportSyncProcessingError( path, 'was missing' )
                        
                        return
                        
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'loading from disk' )
                    
                    with open( path, 'rb' ) as f: obj_string = f.read()
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'parsing' )
                    
                    try:
                        
                        content_update_package = HydrusSerialisable.CreateFromString( obj_string )
                        
                        if not isinstance( content_update_package, HydrusData.ServerToClientContentUpdatePackage ):
                            
                            raise Exception()
                            
                        
                    except:
                        
                        self._ReportSyncProcessingError( path, 'did not parse' )
                        
                        return
                        
                    
                    HydrusGlobals.client_controller.pub( 'splash_set_title_text', self._name + ' - ' + update_index_string + subupdate_index_string )
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'processing' )
                    
                    ( did_it_all, c_u_p_weight_processed ) = HydrusGlobals.client_controller.WriteSynchronous( 'content_update_package', self._service_key, content_update_package, job_key )
                    
                    total_content_weight_processed += c_u_p_weight_processed
                    
                    if not did_it_all:
                        
                        processing_went_ok = False
                        
                        break
                        
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                    time.sleep( 1 )
                    
                
                if options[ 'pause_repo_sync' ]:
                    
                    break
                    
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    break
                    
                
                if processing_went_ok:
                    
                    job_key.SetVariable( 'popup_text_2', 'committing service updates' )
                    
                    service_updates = [ service_update for service_update in service_update_package.IterateServiceUpdates() ]
                    
                    service_updates.append( HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP, service_update_package.GetNextBegin() ) )
                    
                    service_keys_to_service_updates = { self._service_key : service_updates }
                    
                    self.ProcessServiceUpdates( service_keys_to_service_updates )
                    
                    HydrusGlobals.client_controller.Write( 'service_updates', service_keys_to_service_updates )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                
                job_key.SetVariable( 'popup_gauge_2', ( 0, 1 ) )
                job_key.SetVariable( 'popup_text_2', '' )
                
                num_updates_processed += 1
                
                time.sleep( 0.1 )
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            job_key.DeleteVariable( 'popup_text_2' )
            job_key.DeleteVariable( 'popup_gauge_2' )
            
            self.SyncThumbnails( job_key )
            
            HydrusGlobals.client_controller.pub( 'splash_set_status_text', '' )
            
            job_key.SetVariable( 'popup_title', 'repository synchronisation - ' + self._name + ' - finished' )
            
            updates_text = HydrusData.ConvertIntToPrettyString( num_updates_downloaded ) + ' updates downloaded, ' + HydrusData.ConvertIntToPrettyString( num_updates_processed ) + ' updates processed'
            
            if self._service_type == HC.TAG_REPOSITORY: content_text = HydrusData.ConvertIntToPrettyString( total_content_weight_processed ) + ' mappings added'
            elif self._service_type == HC.FILE_REPOSITORY: content_text = HydrusData.ConvertIntToPrettyString( total_content_weight_processed ) + ' files added'
            
            job_key.SetVariable( 'popup_text_1', updates_text + ', and ' + content_text )
            
            HydrusData.Print( job_key.ToString() )
            
            time.sleep( 3 )
            
            job_key.Delete()
            
        except Exception as e:
            
            job_key.Cancel()
            
            HydrusData.Print( traceback.format_exc() )
            
            HydrusData.ShowText( 'Failed to update ' + self._name + ':' )
            
            HydrusData.ShowException( e )
            
            time.sleep( 3 )
            
        finally:
            
            HydrusGlobals.client_controller.pub( 'notify_new_pending' )
            HydrusGlobals.client_controller.pub( 'notify_new_siblings' )
            HydrusGlobals.client_controller.pub( 'notify_new_parents' )
            
        
    
    def SyncThumbnails( self, job_key ):
        
        synced = not ( self.IsUpdateDueForDownload() or self.IsUpdateDueForProcessing() )
        
        if self._service_type == HC.FILE_REPOSITORY and synced and self.CanDownload():
            
            options = HydrusGlobals.client_controller.GetOptions()
            
            HydrusGlobals.client_controller.pub( 'splash_set_status_text', 'reviewing service thumbnails' )
            
            job_key.SetVariable( 'popup_text_1', 'reviewing service thumbnails' )
            
            remote_thumbnail_hashes_i_should_have = HydrusGlobals.client_controller.Read( 'remote_thumbnail_hashes_i_should_have', self._service_key )
            
            thumbnail_hashes_i_need = set()
            
            for hash in remote_thumbnail_hashes_i_should_have:
                
                path = ClientFiles.GetExpectedThumbnailPath( hash )
                
                if not os.path.exists( path ):
                    
                    thumbnail_hashes_i_need.add( hash )
                    
                
            
            if len( thumbnail_hashes_i_need ) > 0:
                
                def SaveThumbnails( batch_of_thumbnails ):
                    
                    job_key.SetVariable( 'popup_text_1', 'saving thumbnails to database' )
                    
                    HydrusGlobals.client_controller.WriteSynchronous( 'thumbnails', batch_of_thumbnails )
                    
                    HydrusGlobals.client_controller.pub( 'add_thumbnail_count', self._service_key, len( batch_of_thumbnails ) )
                    
                
                thumbnails = []
                
                for ( i, hash ) in enumerate( thumbnail_hashes_i_need ):
                    
                    if options[ 'pause_repo_sync' ]:
                        
                        break
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        break
                        
                    
                    job_key.SetVariable( 'popup_text_1', 'downloading thumbnail ' + HydrusData.ConvertValueRangeToPrettyString( i, len( thumbnail_hashes_i_need ) ) )
                    job_key.SetVariable( 'popup_gauge_1', ( i, len( thumbnail_hashes_i_need ) ) )
                    
                    request_args = { 'hash' : hash.encode( 'hex' ) }
                    
                    thumbnail = self.Request( HC.GET, 'thumbnail', request_args = request_args )
                    
                    thumbnails.append( ( hash, thumbnail ) )
                    
                    if i % 50 == 0:
                        
                        SaveThumbnails( thumbnails )
                        
                        thumbnails = []
                        
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                
                if len( thumbnails ) > 0:
                    
                    SaveThumbnails( thumbnails )
                    
                
                job_key.DeleteVariable( 'popup_gauge_1' )
                
            
        
    
class ServiceIPFS( ServiceRemote ):
    
    def _ConvertMultihashToURLTree( self, name, size, multihash ):
        
        api_base_url = self._GetAPIBaseURL()
        
        links_url = api_base_url + 'object/links/' + multihash
        
        response = ClientNetworking.RequestsGet( links_url )
        
        links_json = response.json()
        
        is_directory = False
        
        for link in links_json[ 'Links' ]:
            
            if link[ 'Name' ] != '':
                
                is_directory = True
                
            
        
        if is_directory:
            
            children = []
            
            for link in links_json[ 'Links' ]:
                
                subname = link[ 'Name' ]
                subsize = link[ 'Size' ]
                submultihash = link[ 'Hash' ]
                
                children.append( self._ConvertMultihashToURLTree( subname, subsize, submultihash ) )
                
            
            if size is None:
                
                size = sum( ( subsize for ( type_gumpf, subname, subsize, submultihash ) in children ) )
                
            
            return ( 'directory', name, size, children )
            
        else:
            
            url = api_base_url + 'cat/' + multihash
            
            return ( 'file', name, size, url )
            
        
    
    def _GetAPIBaseURL( self ):
        
        credentials = self.GetCredentials()
        
        ( host, port ) = credentials.GetAddress()
        
        api_base_url = 'http://' + host + ':' + str( port ) + '/api/v0/'
        
        return api_base_url
        
    
    def GetDaemonVersion( self ):
        
        api_base_url = self._GetAPIBaseURL()
        
        url = api_base_url + 'version'
        
        response = ClientNetworking.RequestsGet( url )
        
        j = response.json()
        
        return j[ 'Version' ]
        
    
    def ImportFile( self, multihash ):
        
        def on_wx_select_tree( job_key, url_tree ):
            
                import ClientGUIDialogs
                
                with ClientGUIDialogs.DialogSelectFromURLTree( None, url_tree ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        urls = dlg.GetURLs()
                        
                        if len( urls ) > 0:
                            
                            HydrusGlobals.client_controller.CallToThread( ClientDownloading.THREADDownloadURLs, job_key, urls, multihash )
                            
                        
                    
                
            
        
        def off_wx():
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_text_1', 'Looking up multihash information' )
            
            HydrusGlobals.client_controller.pub( 'message', job_key )
            
            url_tree = self._ConvertMultihashToURLTree( multihash, None, multihash )
            
            if url_tree[0] == 'file':
                
                url = url_tree[3]
                
                HydrusGlobals.client_controller.CallToThread( ClientDownloading.THREADDownloadURL, job_key, url, multihash )
                
            else:
                
                job_key.SetVariable( 'popup_text_1', 'Waiting for user selection' )
                
                wx.CallAfter( on_wx_select_tree, job_key, url_tree )
                
            
        
        HydrusGlobals.client_controller.CallToThread( off_wx )
        
    
    def PinFile( self, hash, mime ):
        
        mime_string = HC.mime_string_lookup[ mime ]
        
        api_base_url = self._GetAPIBaseURL()
        
        url = api_base_url + 'add'
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        files = { 'path' : ( hash.encode( 'hex' ), open( path, 'rb' ), mime_string ) }
        
        response = ClientNetworking.RequestsPost( url, files = files )
        
        j = response.json()
        
        multihash = j[ 'Hash' ]
        
        return multihash
        
    
    def UnpinFile( self, multihash ):
        
        api_base_url = self._GetAPIBaseURL()
        
        url = api_base_url + 'pin/rm/' + multihash
        
        ClientNetworking.RequestsGet( url )
        
    
class Shortcuts( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._mouse_actions = {}
        self._keyboard_actions = {}
        
    
    def _ConvertActionToSerialisableAction( self, action ):
        
        ( service_key, data ) = action
        
        if service_key is None:
            
            return [ service_key, data ]
            
        else:
            
            serialisable_service_key = service_key.encode( 'hex' )
            
            return [ serialisable_service_key, data ]
            
        
    
    def _ConvertSerialisableActionToAction( self, serialisable_action ):
        
        ( serialisable_service_key, data ) = serialisable_action
        
        if serialisable_service_key is None:
            
            return ( serialisable_service_key, data ) # important to return tuple, as serialisable_action is likely a list
            
        else:
            
            service_key = serialisable_service_key.decode( 'hex' )
            
            return ( service_key, data )
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_mouse_actions = []
        
        for ( ( modifier, mouse_button ), action ) in self._mouse_actions.items():
            
            serialisable_action = self._ConvertActionToSerialisableAction( action )
            
            serialisable_mouse_actions.append( ( modifier, mouse_button, serialisable_action ) )
            
        
        serialisable_keyboard_actions = []
        
        for ( ( modifier, key ), action ) in self._keyboard_actions.items():
            
            serialisable_action = self._ConvertActionToSerialisableAction( action )
            
            serialisable_keyboard_actions.append( ( modifier, key, serialisable_action ) )
            
        
        return ( serialisable_mouse_actions, serialisable_keyboard_actions )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_mouse_actions, serialisable_keyboard_actions ) = serialisable_info
        
        self._mouse_actions = {}
        
        for ( modifier, mouse_button, serialisable_action ) in serialisable_mouse_actions:
            
            action = self._ConvertSerialisableActionToAction( serialisable_action )
            
            self._mouse_actions[ ( modifier, mouse_button ) ] = action
            
        
        self._keyboard_actions = {}
        
        for ( modifier, key, serialisable_action ) in serialisable_keyboard_actions:
            
            action = self._ConvertSerialisableActionToAction( serialisable_action )
            
            self._keyboard_actions[ ( modifier, key ) ] = action
            
        
    
    def ClearActions( self ):
        
        self._mouse_actions = {}
        self._keyboard_actions = {}
        
    
    def DeleteKeyboardAction( self, modifier, key ):
        
        if ( modifier, key ) in self._keyboard_actions:
            
            del self._keyboard_actions[ ( modifier, key ) ]
            
        
    
    def DeleteMouseAction( self, modifier, mouse_button ):
        
        if ( modifier, mouse_button ) in self._mouse_actions:
            
            del self._mouse_actions[ ( modifier, mouse_button ) ]
            
        
    
    def GetKeyboardAction( self, modifier, key ):
        
        if ( modifier, key ) in self._keyboard_actions:
            
            return self._keyboard_actions[ ( modifier, key ) ]
            
        else:
            
            return None
            
        
    
    def GetMouseAction( self, modifier, mouse_button ):
        
        if ( modifier, mouse_button ) in self._mouse_actions:
            
            return self._mouse_actions[ ( modifier, mouse_button ) ]
            
        else:
            
            return None
            
        
    
    def IterateKeyboardShortcuts( self ):
        
        for ( ( modifier, key ), action ) in self._keyboard_actions.items(): yield ( ( modifier, key ), action )
        
    
    def IterateMouseShortcuts( self ):
        
        for ( ( modifier, mouse_button ), action ) in self._mouse_actions.items(): yield ( ( modifier, mouse_button ), action )
        
    
    def SetKeyboardAction( self, modifier, key, action ):
        
        self._keyboard_actions[ ( modifier, key ) ] = action
        
    
    def SetMouseAction( self, modifier, mouse_button, action ):
        
        self._mouse_actions[ ( modifier, mouse_button ) ] = action
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS ] = Shortcuts

def GetShortcutFromEvent( event ):
    
    modifier = wx.ACCEL_NORMAL
    
    if event.AltDown(): modifier = wx.ACCEL_ALT
    elif event.CmdDown(): modifier = wx.ACCEL_CTRL
    elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
    
    key = event.KeyCode
    
    return ( modifier, key )

class ClientServiceIdentifier( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!ClientServiceIdentifier'
    
    def __init__( self, service_key, service_type, name ):
        
        HydrusData.HydrusYAMLBase.__init__( self )
        
        self._service_key = service_key
        self._type = service_type
        self._name = name
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._service_key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Client Service Identifier: ' + HydrusData.ToUnicode( ( self._name, HC.service_string_lookup[ self._type ] ) )
    
    def GetInfo( self ): return ( self._service_key, self._type, self._name )
    
    def GetName( self ): return self._name
    
    def GetServiceKey( self ): return self._service_key
    
    def GetServiceType( self ): return self._type
