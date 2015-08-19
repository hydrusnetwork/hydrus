import ClientConstants as CC
import ClientFiles
import collections
import datetime
import HydrusConstants as HC
import HydrusExceptions
import HydrusNetworking
import HydrusSerialisable
import HydrusTags
import threading
import traceback
import os
import random
import shutil
import sqlite3
import stat
import sys
import time
import wx
import yaml
import HydrusData
import ClientSearch
import HydrusGlobals

def AddPaddingToDimensions( dimensions, padding ):
    
    ( x, y ) = dimensions
    
    return ( x + padding, y + padding )
    
def CatchExceptionClient( etype, value, tb ):
    
    try:
        
        job_key = HydrusData.JobKey()
        
        if etype == HydrusExceptions.DBException:
            
            ( text, caller_traceback, db_traceback ) = value
            
            job_key.SetVariable( 'popup_title', 'Database Error!' )
            job_key.SetVariable( 'popup_text_1', text )
            job_key.SetVariable( 'popup_caller_traceback', caller_traceback )
            job_key.SetVariable( 'popup_db_traceback', db_traceback )
            
        else:
            
            trace_list = traceback.format_tb( tb )
            
            trace = ''.join( trace_list )
            
            if etype == wx.PyDeadObjectError:
                
                print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
                print( HydrusData.ToString( value ) )
                print( trace )
                
                return
                
            
            try: job_key.SetVariable( 'popup_title', HydrusData.ToString( etype.__name__ ) )
            except: job_key.SetVariable( 'popup_title', HydrusData.ToString( etype ) )
            job_key.SetVariable( 'popup_text_1', HydrusData.ToString( value ) )
            job_key.SetVariable( 'popup_traceback', trace )
            
        
        text = job_key.ToString()
        
        print( '' )
        print( 'The following uncaught exception occured at ' + HydrusData.ConvertTimestampToPrettyTime( HydrusData.GetNow() ) + ':' )
        
        try: print( text )
        except: print( repr( text ) )
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        HydrusGlobals.pubsub.pub( 'message', job_key )
        
    except:
        
        text = 'Encountered an error I could not parse:'
        
        text += os.linesep
        
        text += HydrusData.ToString( ( etype, value, tb ) )
        
        try: text += traceback.format_exc()
        except: pass
        
        HydrusData.ShowText( text )
        
    
def GetMediasTagCount( pool, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY ):
    
    tags_managers = []
    
    for media in pool:
        
        if media.IsCollection(): tags_managers.extend( media.GetSingletonsTagsManagers() )
        else: tags_managers.append( media.GetTagsManager() )
        
    
    current_tags_to_count = collections.Counter()
    deleted_tags_to_count = collections.Counter()
    pending_tags_to_count = collections.Counter()
    petitioned_tags_to_count = collections.Counter()
    
    for tags_manager in tags_managers:
        
        statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key )
        
        current_tags_to_count.update( statuses_to_tags[ HC.CURRENT ] )
        deleted_tags_to_count.update( statuses_to_tags[ HC.DELETED ] )
        pending_tags_to_count.update( statuses_to_tags[ HC.PENDING ] )
        petitioned_tags_to_count.update( statuses_to_tags[ HC.PETITIONED ] )
        
    
    return ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count )
    
def IsWXAncestor( child, ancestor ):
    
    parent = child
    
    while not isinstance( parent, wx.TopLevelWindow ):
        
        if parent == ancestor:
            
            return True
            
        
        parent = parent.GetParent()
        
    
    return False
    
def ShowExceptionClient( e ):
    
    job_key = HydrusData.JobKey()
    
    if isinstance( e, HydrusExceptions.DBException ):
        
        ( text, caller_traceback, db_traceback ) = e.args
        
        job_key.SetVariable( 'popup_title', 'Database Error!' )
        job_key.SetVariable( 'popup_text_1', text )
        job_key.SetVariable( 'popup_caller_traceback', caller_traceback )
        job_key.SetVariable( 'popup_db_traceback', db_traceback )
        
    else:
        
        ( etype, value, tb ) = sys.exc_info()
        
        if etype is None:
            
            etype = type( e )
            value = HydrusData.ToString( e )
            
            trace = ''.join( traceback.format_stack() )
            
        else: trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
        if etype == wx.PyDeadObjectError:
            
            print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
            print( HydrusData.ToString( value ) )
            print( trace )
            
            return
            
        
        if hasattr( etype, '__name__' ): title = HydrusData.ToString( etype.__name__ )
        else: title = HydrusData.ToString( etype )
        
        job_key.SetVariable( 'popup_title', title )
        job_key.SetVariable( 'popup_text_1', HydrusData.ToString( value ) )
        job_key.SetVariable( 'popup_traceback', trace )
        
    
    text = job_key.ToString()
    
    print( '' )
    print( 'The following exception occured at ' + HydrusData.ConvertTimestampToPrettyTime( HydrusData.GetNow() ) + ':' )
    
    try: print( text )
    except: print( repr( text ) )
    
    sys.stdout.flush()
    sys.stderr.flush()
    
    HydrusGlobals.pubsub.pub( 'message', job_key )
    
def ShowTextClient( text ):
    
    job_key = HydrusData.JobKey()
    
    job_key.SetVariable( 'popup_text_1', HydrusData.ToString( text ) )
    
    text = job_key.ToString()
    
    try: print( text )
    except: print( repr( text ) )
    
    HydrusGlobals.pubsub.pub( 'message', job_key )
    
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
    
    def __repr__( self ): return 'Credentials: ' + HydrusData.ToString( ( self._host, self._port, self._access_key.encode( 'hex' ) ) )
    
    def GetAccessKey( self ): return self._access_key
    
    def GetAddress( self ): return ( self._host, self._port )
    
    def GetConnectionString( self ):
        
        connection_string = ''
        
        if self.HasAccessKey(): connection_string += self._access_key.encode( 'hex' ) + '@'
        
        connection_string += self._host + ':' + HydrusData.ToString( self._port )
        
        return connection_string
        
    
    def HasAccessKey( self ): return self._access_key is not None and self._access_key is not ''
    
    def SetAccessKey( self, access_key ): self._access_key = access_key

class FileQueryResult( object ):
    
    def __init__( self, media_results ):
        
        self._hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
        self._hashes_ordered = [ media_result.GetHash() for media_result in media_results ]
        self._hashes = set( self._hashes_ordered )
        
        HydrusGlobals.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_data' )
        HydrusGlobals.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        
    
    def __iter__( self ):
        
        for hash in self._hashes_ordered: yield self._hashes_to_media_results[ hash ]
        
    
    def __len__( self ): return len( self._hashes_ordered )
    
    def _Remove( self, hashes ):
        
        for hash in hashes:
            
            if hash in self._hashes_to_media_results:
                
                del self._hashes_to_media_results[ hash ]
                
                self._hashes_ordered.remove( hash )
                
            
        
        self._hashes.difference_update( hashes )
        
    
    def AddMediaResults( self, media_results ):
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            
            if hash in self._hashes: continue # this is actually important, as sometimes we don't want the media result overwritten
            
            self._hashes_to_media_results[ hash ] = media_result
            
            self._hashes_ordered.append( hash )
            
            self._hashes.add( hash )
            
        
    
    def GetHashes( self ): return self._hashes
    
    def GetMediaResult( self, hash ): return self._hashes_to_media_results[ hash ]
    
    def GetMediaResults( self ): return [ self._hashes_to_media_results[ hash ] for hash in self._hashes_ordered ]
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            for content_update in content_updates:
                
                hashes = content_update.GetHashes()
                
                if len( hashes ) > 0:
                    
                    for hash in self._hashes.intersection( hashes ):
                        
                        media_result = self._hashes_to_media_results[ hash ]
                        
                        media_result.ProcessContentUpdate( service_key, content_update )
                        
                    
                
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                    
                    for media_result in self._hashes_to_media_results.values(): media_result.DeletePending( service_key )
                    
                elif action == HC.SERVICE_UPDATE_RESET:
                    
                    for media_result in self._hashes_to_media_results.values(): media_result.ResetService( service_key )
                    
                
            
        
    
class FileSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, file_service_key = CC.COMBINED_FILE_SERVICE_KEY, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True, predicates = None ):
        
        if predicates is None: predicates = []
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        self._include_current_tags = include_current_tags
        self._include_pending_tags = include_pending_tags
        
        self._predicates = predicates
        
        self._search_complete = False
        
        self._InitialiseTemporaryVariables()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_predicates = [ HydrusSerialisable.GetSerialisableTuple( predicate ) for predicate in self._predicates ]
        
        return ( self._file_service_key.encode( 'hex' ), self._tag_service_key.encode( 'hex' ), self._include_current_tags, self._include_pending_tags, serialisable_predicates, self._search_complete )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( file_service_key, tag_service_key, self._include_current_tags, self._include_pending_tags, serialisable_predicates, self._search_complete ) = serialisable_info
        
        self._file_service_key = file_service_key.decode( 'hex' )
        self._tag_service_key = tag_service_key.decode( 'hex' )
        
        self._predicates = [ HydrusSerialisable.CreateFromSerialisableTuple( pred_tuple ) for pred_tuple in serialisable_predicates ]
        
        self._InitialiseTemporaryVariables()
        
    
    def _InitialiseTemporaryVariables( self ):
        
        system_predicates = [ predicate for predicate in self._predicates if predicate.GetType() in HC.SYSTEM_PREDICATES ]
        
        self._system_predicates = FileSystemPredicates( system_predicates )
        
        tag_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG ]
        
        self._tags_to_include = []
        self._tags_to_exclude = []
        
        for predicate in tag_predicates:
            
            tag = predicate.GetValue()
            
            if predicate.GetInclusive(): self._tags_to_include.append( tag )
            else: self._tags_to_exclude.append( tag )
            
        
        namespace_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_NAMESPACE ]
        
        self._namespaces_to_include = []
        self._namespaces_to_exclude = []
        
        for predicate in namespace_predicates:
            
            namespace = predicate.GetValue()
            
            if predicate.GetInclusive(): self._namespaces_to_include.append( namespace )
            else: self._namespaces_to_exclude.append( namespace )
            
        
        wildcard_predicates =  [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_WILDCARD ]
        
        self._wildcards_to_include = []
        self._wildcards_to_exclude = []
        
        for predicate in wildcard_predicates:
            
            wildcard = predicate.GetValue()
            
            if predicate.GetInclusive(): self._wildcards_to_include.append( wildcard )
            else: self._wildcards_to_exclude.append( wildcard )
            
        
    
    def GetFileServiceKey( self ): return self._file_service_key
    def GetNamespacesToExclude( self ): return self._namespaces_to_exclude
    def GetNamespacesToInclude( self ): return self._namespaces_to_include
    def GetPredicates( self ): return self._predicates
    def GetSystemPredicates( self ): return self._system_predicates
    def GetTagServiceKey( self ): return self._tag_service_key
    def GetTagsToExclude( self ): return self._tags_to_exclude
    def GetTagsToInclude( self ): return self._tags_to_include
    def GetWildcardsToExclude( self ): return self._wildcards_to_exclude
    def GetWildcardsToInclude( self ): return self._wildcards_to_include
    def IncludeCurrentTags( self ): return self._include_current_tags
    def IncludePendingTags( self ): return self._include_pending_tags
    def IsComplete( self ): return self._search_complete
    def SetComplete( self ): self._search_complete = True
    
    def SetPredicates( self, predicates ):
        
        self._predicates = predicates
        
        self._InitialiseTemporaryVariables()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT ] = FileSearchContext

class FileSystemPredicates( object ):
    
    def __init__( self, system_predicates ):
        
        self._inbox = False
        self._archive = False
        self._local = False
        self._not_local = False
        
        self._common_info = {}
        
        self._limit = None
        self._similar_to = None
        
        self._file_services_to_include_current = []
        self._file_services_to_include_pending = []
        self._file_services_to_exclude_current = []
        self._file_services_to_exclude_pending = []
        
        self._ratings_predicates = []
        
        for predicate in system_predicates:
            
            predicate_type = predicate.GetType()
            value = predicate.GetValue()
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_INBOX: self._inbox = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_ARCHIVE: self._archive = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_LOCAL: self._local = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL: self._not_local = True
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
                
                hash = value
                
                self._common_info[ 'hash' ] = hash
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
                
                ( operator, years, months, days, hours ) = value
                
                age = ( ( ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 24 ) + hours ) * 3600 )
                
                now = HydrusData.GetNow()
                
                # this is backwards because we are talking about age, not timestamp
                
                if operator == '<': self._common_info[ 'min_timestamp' ] = now - age
                elif operator == '>': self._common_info[ 'max_timestamp' ] = now - age
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_timestamp' ] = now - int( age * 1.15 )
                    self._common_info[ 'max_timestamp' ] = now - int( age * 0.85 )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME:
                
                mimes = value
                
                if type( mimes ) == int: mimes = ( mimes, )
                
                self._common_info[ 'mimes' ] = mimes
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION:
                
                ( operator, duration ) = value
                
                if operator == '<': self._common_info[ 'max_duration' ] = duration
                elif operator == '>': self._common_info[ 'min_duration' ] = duration
                elif operator == '=': self._common_info[ 'duration' ] = duration
                elif operator == u'\u2248':
                    
                    if duration == 0: self._common_info[ 'duration' ] = 0
                    else:
                        
                        self._common_info[ 'min_duration' ] = int( duration * 0.85 )
                        self._common_info[ 'max_duration' ] = int( duration * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
                
                ( operator, value, service_key ) = value
                
                self._ratings_predicates.append( ( operator, value, service_key ) )
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATIO:
                
                ( operator, ratio_width, ratio_height ) = value
                
                if operator == '=': self._common_info[ 'ratio' ] = ( ratio_width, ratio_height )
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width * 0.85, ratio_height )
                    self._common_info[ 'max_ratio' ] = ( ratio_width * 1.15, ratio_height )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE:
                
                ( operator, size, unit ) = value
                
                size = size * unit
                
                if operator == '<': self._common_info[ 'max_size' ] = size
                elif operator == '>': self._common_info[ 'min_size' ] = size
                elif operator == '=': self._common_info[ 'size' ] = size
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_size' ] = int( size * 0.85 )
                    self._common_info[ 'max_size' ] = int( size * 1.15 )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                ( operator, num_tags ) = value
                
                if operator == '<': self._common_info[ 'max_num_tags' ] = num_tags
                elif operator == '=': self._common_info[ 'num_tags' ] = num_tags
                elif operator == '>': self._common_info[ 'min_num_tags' ] = num_tags
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_WIDTH:
                
                ( operator, width ) = value
                
                if operator == '<': self._common_info[ 'max_width' ] = width
                elif operator == '>': self._common_info[ 'min_width' ] = width
                elif operator == '=': self._common_info[ 'width' ] = width
                elif operator == u'\u2248':
                    
                    if width == 0: self._common_info[ 'width' ] = 0
                    else:
                        
                        self._common_info[ 'min_width' ] = int( width * 0.85 )
                        self._common_info[ 'max_width' ] = int( width * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                ( operator, num_pixels, unit ) = value
                
                num_pixels = num_pixels * unit
                
                if operator == '<': self._common_info[ 'max_num_pixels' ] = num_pixels
                elif operator == '>': self._common_info[ 'min_num_pixels' ] = num_pixels
                elif operator == '=': self._common_info[ 'num_pixels' ] = num_pixels
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_num_pixels' ] = int( num_pixels * 0.85 )
                    self._common_info[ 'max_num_pixels' ] = int( num_pixels * 1.15 )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_HEIGHT:
                
                ( operator, height ) = value
                
                if operator == '<': self._common_info[ 'max_height' ] = height
                elif operator == '>': self._common_info[ 'min_height' ] = height
                elif operator == '=': self._common_info[ 'height' ] = height
                elif operator == u'\u2248':
                    
                    if height == 0: self._common_info[ 'height' ] = 0
                    else:
                        
                        self._common_info[ 'min_height' ] = int( height * 0.85 )
                        self._common_info[ 'max_height' ] = int( height * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
                
                ( operator, num_words ) = value
                
                if operator == '<': self._common_info[ 'max_num_words' ] = num_words
                elif operator == '>': self._common_info[ 'min_num_words' ] = num_words
                elif operator == '=': self._common_info[ 'num_words' ] = num_words
                elif operator == u'\u2248':
                    
                    if num_words == 0: self._common_info[ 'num_words' ] = 0
                    else:
                        
                        self._common_info[ 'min_num_words' ] = int( num_words * 0.85 )
                        self._common_info[ 'max_num_words' ] = int( num_words * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT:
                
                limit = value
                
                self._limit = limit
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                ( operator, current_or_pending, service_key ) = value
                
                if operator == True:
                    
                    if current_or_pending == HC.CURRENT: self._file_services_to_include_current.append( service_key )
                    else: self._file_services_to_include_pending.append( service_key )
                    
                else:
                    
                    if current_or_pending == HC.CURRENT: self._file_services_to_exclude_current.append( service_key )
                    else: self._file_services_to_exclude_pending.append( service_key )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
                
                ( hash, max_hamming ) = value
                
                self._similar_to = ( hash, max_hamming )
                
            
        
    
    def GetFileServiceInfo( self ): return ( self._file_services_to_include_current, self._file_services_to_include_pending, self._file_services_to_exclude_current, self._file_services_to_exclude_pending )
    
    def GetSimpleInfo( self ): return self._common_info
    
    def GetLimit( self ): return self._limit
    
    def GetRatingsPredicates( self ): return self._ratings_predicates
    
    def GetSimilarTo( self ): return self._similar_to
    
    def HasSimilarTo( self ): return self._similar_to is not None
    
    def MustBeArchive( self ): return self._archive
    
    def MustBeInbox( self ): return self._inbox
    
    def MustBeLocal( self ): return self._local
    
    def MustNotBeLocal( self ): return self._not_local
    
class Imageboard( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Imageboard'
    
    def __init__( self, name, post_url, flood_time, form_fields, restrictions ):
        
        self._name = name
        self._post_url = post_url
        self._flood_time = flood_time
        self._form_fields = form_fields
        self._restrictions = restrictions
        
    
    def IsOkToPost( self, media_result ):
        
        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = media_result.ToTuple()
        
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
    SERIALISABLE_VERSION = 1
    
    def __init__( self, service_keys_to_namespaces = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if service_keys_to_namespaces is None:
            
            service_keys_to_namespaces = {}
            
        
        self._service_keys_to_namespaces = service_keys_to_namespaces
        
    
    def _GetSerialisableInfo( self ):
        
        safe_service_keys_to_namespaces = { service_key.encode( 'hex' ) : list( namespaces ) for ( service_key, namespaces ) in self._service_keys_to_namespaces.items() }
        
        return safe_service_keys_to_namespaces
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        safe_service_keys_to_namespaces = serialisable_info
        
        self._service_keys_to_namespaces = { service_key.decode( 'hex' ) : set( namespaces ) for ( service_key, namespaces ) in safe_service_keys_to_namespaces.items() }
        
    
    def GetServiceKeysToNamespaces( self ):
        
        return dict( self._service_keys_to_namespaces )
        
    
    def GetServiceKeysToTags( self, tags ):
        
        tags = [ tag for tag in tags if tag is not None ]
        
        service_keys_to_tags = {}
        
        siblings_manager = wx.GetApp().GetManager( 'tag_siblings' )
        parents_manager = wx.GetApp().GetManager( 'tag_parents' )
        
        for ( service_key, namespaces ) in self._service_keys_to_namespaces.items():
            
            if len( namespaces ) > 0:
                
                tags_to_add_here = []
                
                for namespace in namespaces:
                    
                    if namespace == '': tags_to_add_here.extend( [ tag for tag in tags if not ':' in tag ] )
                    else: tags_to_add_here.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                    
                
                tags_to_add_here = HydrusTags.CleanTags( tags_to_add_here )
                
                if len( tags_to_add_here ) > 0:
                    
                    tags_to_add_here = siblings_manager.CollapseTags( tags_to_add_here )
                    tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                    
                    service_keys_to_tags[ service_key ] = tags_to_add_here
                    
                
            
        
        return service_keys_to_tags
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_TAG_OPTIONS ] = ImportTagOptions

class Periodic( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PERIODIC
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._wavelength = CC.DAY
        self._multiplier = 1
        self._phase = 0
        self._last_run = 0
        self._failure_delay_timestamp = None
        self._paused = False
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._wavelength, self._multiplier, self._phase, self._last_run, self._failure_delay_timestamp, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._wavelength, self._multiplier, self._phase, self._last_run, self._failure_delay_timestamp, self._paused ) = serialisable_info
        
    
    def GetDue( self ):
        
        day_phase = self._phase / ( 24 * 3600 )
        hour_phase = ( self._phase % ( 24 * 3600 ) ) / 3600
        minute_phase = ( self._phase % 3600 ) / 60
        
        last_run_datetime = datetime.datetime.fromtimestamp( self._last_run )
        
        due_datetime = last_run_datetime.replace( hour = hour_phase, minute = minute_phase, second = 0, microsecond = 0 )
        
        one_day = datetime.timedelta( days = 1 )
        
        if self._wavelength == CC.DAY:
            
            due_datetime += one_day * self._multiplier
            
        elif self._wavelength == CC.WEEK:
            
            times_passed = 0
            
            while times_passed < self._multiplier:
                
                due_datetime += one_day
                
                if due_datetime.weekday() == day_phase:
                    
                    times_passed += 1
                    
                
            
        elif self._wavelength == CC.MONTH:
            
            times_passed = 0
            
            while times_passed < self._multiplier:
                
                due_datetime += one_day
                
                if due_datetime.day == day_phase + 1:
                    
                    times_passed += 1
                    
                
            
        
        due_timestamp = time.mktime( due_datetime.timetuple() )
        
        return due_timestamp
        
    
    def GetString( self ):
        
        s = 'last run was '
        s += HydrusData.ConvertTimestampToPrettyAgo( self._last_run )
        s += ', will next run in '
        
        if self.IsFailureDelaying():
            
            s += HydrusData.ConvertTimestampToPrettyPending( max( self.GetDue(), self._failure_delay_timestamp ) )
            s += ', which may be slightly delayed because of an error'
            
        else:
            
            s += HydrusData.ConvertTimestampToPrettyPending( self.GetDue() )
            
        
        return s
        
    
    def GetPeriodics( self ):
        
        return ( self._wavelength, self._multiplier, self._phase )
        
    
    def IsDue( self ):
        
        return HydrusData.TimeHasPassed( self.GetDue() )
        
    
    def IsFailureDelaying( self ):
        
        if self._failure_delay_timestamp is None:
            
            return False
            
        else:
            
            return HydrusData.TimeHasPassed( self._failure_delay_timestamp )
            
        
    
    def IsPaused( self ): return self._paused
    
    def IsReadyToRun( self ):
        
        if self.IsPaused(): return False
        
        if not self.IsDue(): return False
        
        if self.IsFailureDelaying(): return False
        
        return True
        
    
    def Pause( self ):
        
        self._paused = True
        
    
    def ReportError( self, delay ):
        
        self._failure_delay_timestamp = HydrusData.GetNow() + delay
        
    
    def ReportRun( self ):
        
        self._last_run = HydrusData.GetNow()
        
    
    def Reset( self ):
        
        self._last_run = 0
        self._failure_delay_timestamp = None
        self._paused = False
        
    
    def Resume( self ):
        
        self.paused = False
        
    
    def SetPeriodics( self, wavelength, multiplier, phase ):
        
        self._wavelength = wavelength
        self._multiplier = multiplier
        self._phase = phase
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PERIODIC ] = Periodic

class Service( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Service'
    
    def __init__( self, service_key, service_type, name, info ):
        
        HydrusData.HydrusYAMLBase.__init__( self )
        
        self._service_key = service_key
        self._service_type = service_type
        self._name = name
        self._info = info
        
        self._lock = threading.Lock()
        
        HydrusGlobals.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        
    
    def __hash__( self ): return self._service_key.__hash__()
    
    def _ReportSyncProcessingError( self, path ):
        
        text = 'While synchronising ' + self._name + ', the expected update file ' + path + ', was missing.'
        text += os.linesep * 2
        text += 'The service has been indefinitely paused.'
        text += os.linesep * 2
        text += 'This is a serious error. Unless you know where the file(s) went and can restore them, you should delete this service and recreate it from scratch.'
        
        HydrusData.ShowText( text )
        
        service_updates = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_PAUSE ) ]
        
        service_keys_to_service_updates = { self._service_key : service_updates }
        
        self.ProcessServiceUpdates( service_keys_to_service_updates )
        
        wx.GetApp().Write( 'service_updates', service_keys_to_service_updates )
        
    
    def CanDownload( self ):
        
        return self._info[ 'account' ].HasPermission( HC.GET_DATA ) and not self.HasRecentError()
        
    
    def CanDownloadUpdate( self ):
        
        update_due = HydrusData.TimeHasPassed( self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 )
        
        return self.CanDownload() and update_due and not self.IsPaused()
        
    
    def CanProcessUpdate( self ):
        
        update_is_downloaded = self._info[ 'next_download_timestamp' ] > self._info[ 'next_processing_timestamp' ]
        
        it_is_time = HydrusData.TimeHasPassed( self._info[ 'next_processing_timestamp' ] + HC.UPDATE_DURATION + HC.options[ 'processing_phase' ] )
        
        return update_is_downloaded and it_is_time and not self.IsPaused()
        
    
    def CanUpload( self ): return self._info[ 'account' ].HasPermission( HC.POST_DATA ) and not self.HasRecentError()
    
    def GetCredentials( self ):
        
        host = self._info[ 'host' ]
        port = self._info[ 'port' ]
        if 'access_key' in self._info: access_key = self._info[ 'access_key' ]
        else: access_key = None
        
        credentials = Credentials( host, port, access_key )
        
        return credentials
        
    
    def GetInfo( self, key = None ):
        
        if key is None: return self._info
        else: return self._info[ key ]
        
    
    def GetServiceKey( self ): return self._service_key
    
    def GetName( self ): return self._name
    
    def GetRecentErrorPending( self ):
        
        if 'account' in self._info and self._info[ 'account' ].HasPermission( HC.GENERAL_ADMIN ): return HydrusData.ConvertTimestampToPrettyPending( self._info[ 'last_error' ] + 600 )
        else: return HydrusData.ConvertTimestampToPrettyPending( self._info[ 'last_error' ] + 3600 * 4 )
        
    
    def GetServiceType( self ): return self._service_type
    
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
            num_updates_processed = ( next_processing_timestamp - first_timestamp ) / HC.UPDATE_DURATION
            
        
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
        
    
    def HasRecentError( self ):
        
        if 'account' in self._info and self._info[ 'account' ].HasPermission( HC.GENERAL_ADMIN ): return self._info[ 'last_error' ] + 900 > HydrusData.GetNow()
        else: return self._info[ 'last_error' ] + 3600 * 4 > HydrusData.GetNow()
        
    
    def IsInitialised( self ):
        
        if self._service_type == HC.SERVER_ADMIN: return 'access_key' in self._info
        else: return True
        
    
    def IsPaused( self ): return self._info[ 'paused' ]
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                if service_key == self._service_key:
                    
                    ( action, row ) = service_update.ToTuple()
                    
                    if action == HC.SERVICE_UPDATE_ERROR: self._info[ 'last_error' ] = HydrusData.GetNow()
                    elif action == HC.SERVICE_UPDATE_RESET:
                        
                        self._info[ 'last_error' ] = 0
                        
                        if 'next_processing_timestamp' in self._info: self._info[ 'next_processing_timestamp' ] = 0
                        
                    elif action == HC.SERVICE_UPDATE_ACCOUNT:
                        
                        account = row
                        
                        self._info[ 'account' ] = account
                        self._info[ 'last_error' ] = 0
                        
                    elif action == HC.SERVICE_UPDATE_REQUEST_MADE:
                        
                        num_bytes = row
                        
                        if self._service_type == HC.LOCAL_BOORU:
                            
                            self._info[ 'used_monthly_data' ] += num_bytes
                            self._info[ 'used_monthly_requests' ] += 1
                            
                        else: self._info[ 'account' ].RequestMade( num_bytes )
                        
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
                        
                    
                
            
        
    
    def Request( self, method, command, request_args = None, request_headers = None, report_hooks = None, temp_path = None, return_cookies = False ):
        
        if request_args is None: request_args = {}
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        try:
            
            credentials = self.GetCredentials()
            
            if command in ( 'access_key', 'init', '' ): pass
            elif command in ( 'session_key', 'access_key_verification' ): HydrusNetworking.AddHydrusCredentialsToHeaders( credentials, request_headers )
            else: HydrusNetworking.AddHydrusSessionKeyToHeaders( self._service_key, request_headers )
            
            path = '/' + command
            
            if method == HC.GET:
                
                query = HydrusNetworking.ConvertHydrusGETArgsToQuery( request_args )
                
                body = ''
                
            elif method == HC.POST:
                
                query = ''
                
                if command == 'file':
                    
                    content_type = HC.APPLICATION_OCTET_STREAM
                    
                    body = request_args[ 'file' ]
                    
                    del request_args[ 'file' ]
                    
                else:
                    
                    content_type = HC.APPLICATION_YAML
                    
                    body = yaml.safe_dump( request_args )
                    
                
                request_headers[ 'Content-Type' ] = HC.mime_string_lookup[ content_type ]
                
            
            if query != '': path_and_query = path + '?' + query
            else: path_and_query = path
            
            ( host, port ) = credentials.GetAddress()
            
            url = 'http://' + host + ':' + HydrusData.ToString( port ) + path_and_query
            
            ( response, size_of_response, response_headers, cookies ) = wx.GetApp().DoHTTP( method, url, request_headers, body, report_hooks = report_hooks, temp_path = temp_path, return_everything = True )
            
            HydrusNetworking.CheckHydrusVersion( self._service_key, self._service_type, response_headers )
            
            if method == HC.GET: data_used = size_of_response
            elif method == HC.POST: data_used = len( body )
            
            HydrusNetworking.DoHydrusBandwidth( self._service_key, method, command, data_used )
            
            if return_cookies: return ( response, cookies )
            else: return response
            
        except Exception as e:
            
            if not isinstance( e, HydrusExceptions.ServerBusyException ):
                
                if isinstance( e, HydrusExceptions.SessionException ):
                    
                    session_manager = wx.GetApp().GetManager( 'hydrus_sessions' )
                    
                    session_manager.DeleteSessionKey( self._service_key )
                    
                
                wx.GetApp().Write( 'service_updates', { self._service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ERROR, HydrusData.ToString( e ) ) ] } )
                
                if isinstance( e, HydrusExceptions.PermissionException ):
                    
                    if 'account' in self._info:
                        
                        account_key = self._info[ 'account' ].GetAccountKey()
                        
                        unknown_account = HydrusData.GetUnknownAccount( account_key )
                        
                    else: unknown_account = HydrusData.GetUnknownAccount()
                    
                    wx.GetApp().Write( 'service_updates', { self._service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, unknown_account ) ] } )
                    
                
            
            raise
            
        
    
    def SetCredentials( self, credentials ):
        
        ( host, port ) = credentials.GetAddress()
        
        self._info[ 'host' ] = host
        self._info[ 'port' ] = port
        
        if credentials.HasAccessKey(): self._info[ 'access_key' ] = credentials.GetAccessKey()
        
    
    def Sync( self ):
        
        job_key = HydrusData.JobKey( pausable = True, cancellable = True )
        
        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
        
        if should_quit:
            
            return
            
        
        if self._info[ 'paused' ]:
            
            return
            
        
        if not self.CanDownloadUpdate() and not self.CanProcessUpdate():
            
            return
            
        
        num_updates_downloaded = 0
        num_updates_processed = 0
        total_content_weight_processed = 0
        
        try:
            
            options = wx.GetApp().GetOptions()
            
            job_key.SetVariable( 'popup_title', 'repository synchronisation - ' + self._name )
            
            HydrusGlobals.pubsub.pub( 'message', job_key )
            
            try:
                
                while self.CanDownloadUpdate():
                    
                    while options[ 'pause_repo_sync' ]:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            break
                            
                        
                        time.sleep( 0.1 )
                        
                        job_key.SetVariable( 'popup_text_1', 'all repository synchronisation is paused' )
                        
                        if HydrusGlobals.repos_changed:
                            
                            job_key.SetVariable( 'popup_text_1', 'repositories were changed during processing; this job was abandoned' )
                            
                            print( job_key.ToString() )
                            
                            job_key.Cancel()
                            
                            time.sleep( 5 )
                            
                            job_key.Delete()
                            
                            HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                            
                            return
                            
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        break
                        
                    
                    if self._info[ 'first_timestamp' ] is None:
                        
                        gauge_range = None
                        gauge_value = 0
                        
                        update_index_string = 'initial update: '
                        
                    else:
                        
                        gauge_range = ( ( HydrusData.GetNow() - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION ) + 1
                        gauge_value = ( ( self._info[ 'next_download_timestamp' ] - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION ) + 1
                        
                        update_index_string = 'update ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range ) + ': '
                        
                    
                    subupdate_index_string = 'service update: '
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'downloading and parsing' )
                    job_key.SetVariable( 'popup_gauge_1', ( gauge_value, gauge_range ) )
                    
                    service_update_package = self.Request( HC.GET, 'service_update_package', { 'begin' : self._info[ 'next_download_timestamp' ] } )
                    
                    begin = service_update_package.GetBegin()
                    
                    subindex_count = service_update_package.GetSubindexCount()
                    
                    for subindex in range( subindex_count ):
                        
                        path = ClientFiles.GetExpectedContentUpdatePackagePath( self._service_key, begin, subindex )
                        
                        if not os.path.exists( path ):
                            
                            subupdate_index_string = 'content update ' + HydrusData.ConvertValueRangeToPrettyString( subindex + 1, subindex_count ) + ': '
                            
                            job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'downloading and parsing' )
                            
                            content_update_package = self.Request( HC.GET, 'content_update_package', { 'begin' : begin, 'subindex' : subindex } )
                            
                            obj_string = HydrusSerialisable.DumpToString( content_update_package )
                            
                            job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'saving to disk' )
                            
                            with open( path, 'wb' ) as f: f.write( obj_string )
                            
                        
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + 'committing' )
                    
                    path = ClientFiles.GetExpectedServiceUpdatePackagePath( self._service_key, begin )
                    
                    obj_string = HydrusSerialisable.DumpToString( service_update_package )
                    
                    with open( path, 'wb' ) as f: f.write( obj_string )
                    
                    service_updates = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP, service_update_package.GetNextBegin() ) ]
                    
                    service_keys_to_service_updates = { self._service_key : service_updates }
                    
                    self.ProcessServiceUpdates( service_keys_to_service_updates )
                    
                    wx.GetApp().Write( 'service_updates', service_keys_to_service_updates )
                    
                    wx.GetApp().WaitUntilWXThreadIdle()
                    
                    num_updates_downloaded += 1
                    
                
            except Exception as e:
                
                if 'Could not connect' in str( e ):
                    
                    job_key.SetVariable( 'popup_text_1', 'Could not connect to service, will continue with processing.' )
                    
                    time.sleep( 5 )
                    
                else:
                    
                    raise e
                    
                
            
            update_time_tracker = []
            update_speed_string = ''
            
            WEIGHT_THRESHOLD = 200.0
            
            while self.CanProcessUpdate():
                
                while options[ 'pause_repo_sync' ]:
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        break
                        
                    
                    time.sleep( 0.1 )
                    
                    job_key.SetVariable( 'popup_text_1', 'repository synchronisation paused' )
                    
                    if HydrusGlobals.repos_changed:
                        
                        job_key.SetVariable( 'popup_text_1', 'repositories were changed during processing; this job was abandoned' )
                        
                        print( job_key.ToString() )
                        
                        job_key.Cancel()
                        
                        time.sleep( 5 )
                        
                        job_key.Delete()
                        
                        HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                        
                        return
                        
                    
                    precise_timestamp = HydrusData.GetNowPrecise()
                    
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if i_paused:
                    
                    precise_timestamp = HydrusData.GetNowPrecise()
                    
                
                if should_quit:
                    
                    break
                    
                
                gauge_range = ( ( HydrusData.GetNow() - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION ) + 1
                
                gauge_value = ( ( self._info[ 'next_processing_timestamp' ] - self._info[ 'first_timestamp' ] ) / HC.UPDATE_DURATION ) + 1
                
                update_index_string = 'update ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range ) + ': '
                
                subupdate_index_string = 'service update: '
                
                job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'loading from disk' )
                job_key.SetVariable( 'popup_gauge_1', ( gauge_value, gauge_range ) )
                
                path = ClientFiles.GetExpectedServiceUpdatePackagePath( self._service_key, self._info[ 'next_processing_timestamp' ] )
                
                if not os.path.exists( path ):
                    
                    self._ReportSyncProcessingError( path )
                    
                    return
                    
                
                with open( path, 'rb' ) as f: obj_string = f.read()
                
                service_update_package = HydrusSerialisable.CreateFromString( obj_string )
                
                subindex_count = service_update_package.GetSubindexCount()
                
                pending_content_updates = []
                pending_weight = 0
                
                for subindex in range( subindex_count ):
                    
                    subupdate_index_string = 'content update ' + HydrusData.ConvertValueRangeToPrettyString( subindex + 1, subindex_count ) + ': '
                    
                    path = ClientFiles.GetExpectedContentUpdatePackagePath( self._service_key, self._info[ 'next_processing_timestamp' ], subindex )
                    
                    if not os.path.exists( path ):
                        
                        self._ReportSyncProcessingError( path )
                        
                        return
                        
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'loading from disk' )
                    
                    with open( path, 'rb' ) as f: obj_string = f.read()
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'parsing' )
                    
                    content_update_package = HydrusSerialisable.CreateFromString( obj_string )
                    
                    job_key.SetVariable( 'popup_text_1', update_index_string + subupdate_index_string + 'processing' )
                    
                    c_u_p_num_rows = content_update_package.GetNumRows()
                    c_u_p_total_weight_processed = 0
                    precise_timestamp = HydrusData.GetNowPrecise()
                    
                    for content_update in content_update_package.IterateContentUpdates():
                        
                        while options[ 'pause_repo_sync' ]:
                            
                            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                            
                            if should_quit:
                                
                                break
                                
                            
                            time.sleep( 0.1 )
                            
                            job_key.SetVariable( 'popup_text_2', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_text_2', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                job_key.Cancel()
                                
                                time.sleep( 5 )
                                
                                job_key.Delete()
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                            precise_timestamp = HydrusData.GetNowPrecise()
                            
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if i_paused:
                            
                            precise_timestamp = HydrusData.GetNowPrecise()
                            
                        
                        if should_quit:
                            
                            break
                            
                        
                        pending_content_updates.append( content_update )
                        
                        content_update_weight = len( content_update.GetHashes() )
                        
                        pending_weight += content_update_weight
                        
                        c_u_p_total_weight_processed += content_update_weight
                        
                        content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
                        
                        job_key.SetVariable( 'popup_text_2', content_update_index_string + 'committing' + update_speed_string )
                        
                        job_key.SetVariable( 'popup_gauge_2', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
                        
                        if pending_weight > WEIGHT_THRESHOLD:
                            
                            wx.GetApp().WaitUntilWXThreadIdle()
                            
                            wx.GetApp().WriteSynchronous( 'content_updates', { self._service_key : pending_content_updates } )
                            
                            it_took = HydrusData.GetNowPrecise() - precise_timestamp
                            
                            precise_timestamp = HydrusData.GetNowPrecise()
                            
                            if wx.GetApp().CurrentlyIdle(): ideal_packet_time = 10.0
                            else: ideal_packet_time = 0.5
                            
                            WEIGHT_THRESHOLD = max( 200.0, WEIGHT_THRESHOLD * ideal_packet_time / it_took )
                            
                            total_content_weight_processed += pending_weight
                            
                            #
                            
                            if len( update_time_tracker ) > 10:
                                
                                update_time_tracker.pop( 0 )
                                
                            
                            update_time_tracker.append( ( pending_weight, it_took ) )
                            
                            recent_total_weight = 0
                            recent_total_time = 0.0
                            
                            for ( weight, it_took ) in update_time_tracker:
                                
                                recent_total_weight += weight
                                recent_total_time += it_took
                                
                                recent_speed = int( recent_total_weight / recent_total_time )
                                
                                update_speed_string = ' at ' + HydrusData.ConvertIntToPrettyString( recent_speed ) + ' rows/s'
                                
                            
                            #
                            
                            pending_content_updates = []
                            pending_weight = 0
                            
                        
                    
                
                if len( pending_content_updates ) > 0:
                    
                    wx.GetApp().WaitUntilWXThreadIdle()
                    
                    wx.GetApp().WriteSynchronous( 'content_updates', { self._service_key : pending_content_updates } )
                    
                    WEIGHT_THRESHOLD = 200.0
                    
                    total_content_weight_processed += pending_weight
                    
                
                job_key.SetVariable( 'popup_text_2', 'committing service updates' )
                
                service_updates = [ service_update for service_update in service_update_package.IterateServiceUpdates() ]
                
                service_updates.append( HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP, service_update_package.GetNextBegin() ) )
                
                service_keys_to_service_updates = { self._service_key : service_updates }
                
                self.ProcessServiceUpdates( service_keys_to_service_updates )
                
                wx.GetApp().Write( 'service_updates', service_keys_to_service_updates )
                
                HydrusGlobals.pubsub.pub( 'notify_new_pending' )
                
                # this waits for pubsubs to flush, so service updates are processed
                wx.GetApp().WaitUntilWXThreadIdle()
                
                job_key.SetVariable( 'popup_gauge_2', ( 0, 1 ) )
                job_key.SetVariable( 'popup_text_2', '' )
                
                num_updates_processed += 1
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            job_key.DeleteVariable( 'popup_text_2' )
            job_key.DeleteVariable( 'popup_gauge_2' )
            
            if self._service_type == HC.FILE_REPOSITORY and self.CanDownload():
                
                job_key.SetVariable( 'popup_text_1', 'reviewing existing thumbnails' )
                
                thumbnail_hashes_i_have = ClientFiles.GetAllThumbnailHashes()
                
                job_key.SetVariable( 'popup_text_1', 'reviewing service thumbnails' )
                
                thumbnail_hashes_i_should_have = wx.GetApp().Read( 'thumbnail_hashes_i_should_have', self._service_key )
                
                thumbnail_hashes_i_need = thumbnail_hashes_i_should_have.difference( thumbnail_hashes_i_have )
                
                if len( thumbnail_hashes_i_need ) > 0:
                    
                    while options[ 'pause_repo_sync' ]:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            break
                            
                        
                        time.sleep( 0.1 )
                        
                        job_key.SetVariable( 'popup_text_1', 'repository synchronisation paused' )
                        
                        if HydrusGlobals.repos_changed:
                            
                            job_key.SetVariable( 'popup_text_1', 'repositories were changed during processing; this job was abandoned' )
                            
                            print( job_key.ToString() )
                            
                            job_key.Cancel()
                            
                            time.sleep( 5 )
                            
                            job_key.Delete()
                            
                            HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                            
                            return
                            
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    def SaveThumbnails( batch_of_thumbnails ):
                        
                        job_key.SetVariable( 'popup_text_1', 'saving thumbnails to database' )
                        
                        wx.GetApp().WriteSynchronous( 'thumbnails', batch_of_thumbnails )
                        
                        HydrusGlobals.pubsub.pub( 'add_thumbnail_count', self._service_key, len( batch_of_thumbnails ) )
                        
                    
                    thumbnails = []
                    
                    for ( i, hash ) in enumerate( thumbnail_hashes_i_need ):
                        
                        job_key.SetVariable( 'popup_text_1', 'downloading thumbnail ' + HydrusData.ConvertValueRangeToPrettyString( i, len( thumbnail_hashes_i_need ) ) )
                        job_key.SetVariable( 'popup_gauge_1', ( i, len( thumbnail_hashes_i_need ) ) )
                        
                        request_args = { 'hash' : hash.encode( 'hex' ) }
                        
                        thumbnail = self.Request( HC.GET, 'thumbnail', request_args = request_args )
                        
                        thumbnails.append( ( hash, thumbnail ) )
                        
                        if i % 50 == 0:
                            
                            SaveThumbnails( thumbnails )
                            
                            thumbnails = []
                            
                        
                        wx.GetApp().WaitUntilWXThreadIdle()
                        
                    
                    if len( thumbnails ) > 0: SaveThumbnails( thumbnails )
                    
                    job_key.DeleteVariable( 'popup_gauge_1' )
                    
                
            
            job_key.SetVariable( 'popup_title', 'repository synchronisation - ' + self._name + ' - finished' )
            
            updates_text = HydrusData.ConvertIntToPrettyString( num_updates_downloaded ) + ' updates downloaded, ' + HydrusData.ConvertIntToPrettyString( num_updates_processed ) + ' updates processed'
            
            if self._service_type == HC.TAG_REPOSITORY: content_text = HydrusData.ConvertIntToPrettyString( total_content_weight_processed ) + ' mappings added'
            elif self._service_type == HC.FILE_REPOSITORY: content_text = HydrusData.ConvertIntToPrettyString( total_content_weight_processed ) + ' files added'
            
            job_key.SetVariable( 'popup_text_1', updates_text + ', and ' + content_text )
            
            print( job_key.ToString() )
            
            if total_content_weight_processed > 0: job_key.Finish()
            else: job_key.Delete()
            
        except Exception as e:
            
            job_key.Cancel()
            
            print( traceback.format_exc() )
            
            HydrusData.ShowText( 'Failed to update ' + self._name + ':' )
            
            HydrusData.ShowException( e )
            
            time.sleep( 3 )
            
        
    
    def ToTuple( self ): return ( self._service_key, self._service_type, self._name, self._info )
    
class ServicesManager( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        self._keys_to_services = {}
        self._services_sorted = []
        
        self.RefreshServices()
        
        HydrusGlobals.pubsub.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def GetService( self, service_key ):
        
        with self._lock:
            
            try: return self._keys_to_services[ service_key ]
            except KeyError: raise HydrusExceptions.NotFoundException( 'That service was not found!' )
            
        
    
    def GetServices( self, types = HC.ALL_SERVICES ):
        
        with self._lock: return [ service for service in self._services_sorted if service.GetServiceType() in types ]
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = wx.GetApp().Read( 'services' )
            
            self._keys_to_services = { service.GetServiceKey() : service for service in services }
            
            compare_function = lambda a, b: cmp( a.GetName(), b.GetName() )
            
            self._services_sorted = list( services )
            self._services_sorted.sort( cmp = compare_function )
            
        
    
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

class UndoManager( object ):
    
    def __init__( self ):
        
        self._commands = []
        self._inverted_commands = []
        self._current_index = 0
        
        self._lock = threading.Lock()
        
        HydrusGlobals.pubsub.sub( self, 'Undo', 'undo' )
        HydrusGlobals.pubsub.sub( self, 'Redo', 'redo' )
        
    
    def _FilterServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        filtered_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_DATA_TYPE_FILES:
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_RESCIND_PETITION ): continue
                elif data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ): continue
                    
                else: continue
                
                filtered_content_update = HydrusData.ContentUpdate( data_type, action, row )
                
                filtered_content_updates.append( filtered_content_update )
                
            
            if len( filtered_content_updates ) > 0:
                
                filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
                
            
        
        return filtered_service_keys_to_content_updates
        
    
    def _InvertServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        inverted_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            inverted_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                inverted_row = row
                
                if data_type == HC.CONTENT_DATA_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_ARCHIVE: inverted_action = HC.CONTENT_UPDATE_INBOX
                    elif action == HC.CONTENT_UPDATE_INBOX: inverted_action = HC.CONTENT_UPDATE_ARCHIVE
                    elif action == HC.CONTENT_UPDATE_PENDING: inverted_action = HC.CONTENT_UPDATE_RESCIND_PENDING
                    elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: inverted_action = HC.CONTENT_UPDATE_PENDING
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( hashes, reason ) = row
                        
                        inverted_row = hashes
                        
                    
                elif data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
                    
                    if action == HC.CONTENT_UPDATE_ADD: inverted_action = HC.CONTENT_UPDATE_DELETE
                    elif action == HC.CONTENT_UPDATE_DELETE: inverted_action = HC.CONTENT_UPDATE_ADD
                    elif action == HC.CONTENT_UPDATE_PENDING: inverted_action = HC.CONTENT_UPDATE_RESCIND_PENDING
                    elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: inverted_action = HC.CONTENT_UPDATE_PENDING
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( tag, hashes, reason ) = row
                        
                        inverted_row = ( tag, hashes )
                        
                    
                
                inverted_content_update = HydrusData.ContentUpdate( data_type, inverted_action, inverted_row )
                
                inverted_content_updates.append( inverted_content_update )
                
            
            inverted_service_keys_to_content_updates[ service_key ] = inverted_content_updates
            
        
        return inverted_service_keys_to_content_updates
        
    
    def AddCommand( self, action, *args, **kwargs ):
        
        with self._lock:
            
            inverted_action = action
            inverted_args = args
            inverted_kwargs = kwargs
            
            if action == 'content_updates':
                
                ( service_keys_to_content_updates, ) = args
                
                service_keys_to_content_updates = self._FilterServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( service_keys_to_content_updates ) == 0: return
                
                inverted_service_keys_to_content_updates = self._InvertServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( inverted_service_keys_to_content_updates ) == 0: return
                
                inverted_args = ( inverted_service_keys_to_content_updates, )
                
            else: return
            
            self._commands = self._commands[ : self._current_index ]
            self._inverted_commands = self._inverted_commands[ : self._current_index ]
            
            self._commands.append( ( action, args, kwargs ) )
            
            self._inverted_commands.append( ( inverted_action, inverted_args, inverted_kwargs ) )
            
            self._current_index += 1
            
            HydrusGlobals.pubsub.pub( 'notify_new_undo' )
            
        
    
    def GetUndoRedoStrings( self ):
        
        with self._lock:
            
            ( undo_string, redo_string ) = ( None, None )
            
            if self._current_index > 0:
                
                undo_index = self._current_index - 1
                
                ( action, args, kwargs ) = self._commands[ undo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    undo_string = 'undo ' + HydrusData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                redo_index = self._current_index
                
                ( action, args, kwargs ) = self._commands[ redo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    redo_string = 'redo ' + HydrusData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            return ( undo_string, redo_string )
            
        
    
    def Undo( self ):
        
        action = None
        
        with self._lock:
            
            if self._current_index > 0:
                
                self._current_index -= 1
                
                ( action, args, kwargs ) = self._inverted_commands[ self._current_index ]
                
        
        if action is not None:
            
            wx.GetApp().WriteSynchronous( action, *args, **kwargs )
            
            HydrusGlobals.pubsub.pub( 'notify_new_undo' )
            
        
    
    def Redo( self ):
        
        action = None
        
        with self._lock:
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                ( action, args, kwargs ) = self._commands[ self._current_index ]
                
                self._current_index += 1
                
            
        
        if action is not None:
            
            wx.GetApp().WriteSynchronous( action, *args, **kwargs )
            
            HydrusGlobals.pubsub.pub( 'notify_new_undo' )
            
        
    
def GetDefaultAdvancedTagOptions( lookup ):
    
    backup_lookup = None
    
    if type( lookup ) == tuple:
        
        ( site_type, site_name ) = lookup
        
        if site_type == HC.SITE_TYPE_BOORU: backup_lookup = HC.SITE_TYPE_BOORU
        
    
    options = wx.GetApp().GetOptions()
    
    ato_options = options[ 'default_advanced_tag_options' ]
    
    if lookup in ato_options: ato = ato_options[ lookup ]
    elif backup_lookup is not None and backup_lookup in ato_options: ato = ato_options[ backup_lookup ]
    elif 'default' in ato_options: ato = ato_options[ 'default' ]
    else: ato = {}
    
    return ato

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
    
    def __repr__( self ): return 'Client Service Identifier: ' + HydrusData.ToString( ( self._name, HC.service_string_lookup[ self._type ] ) )
    
    def GetInfo( self ): return ( self._service_key, self._type, self._name )
    
    def GetName( self ): return self._name
    
    def GetServiceKey( self ): return self._service_key
    
    def GetServiceType( self ): return self._type
