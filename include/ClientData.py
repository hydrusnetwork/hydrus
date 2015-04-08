import ClientConstants as CC
import collections
import HydrusConstants as HC
import HydrusExceptions
import HydrusNetworking
import threading
import traceback
import os
import sqlite3
import sys
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
            
            job_key.SetVariable( 'popup_message_title', 'Database Error!' )
            job_key.SetVariable( 'popup_message_text_1', text )
            job_key.SetVariable( 'popup_message_caller_traceback', caller_traceback )
            job_key.SetVariable( 'popup_message_db_traceback', db_traceback )
            
        else:
            
            trace_list = traceback.format_tb( tb )
            
            trace = ''.join( trace_list )
            
            if etype == wx.PyDeadObjectError:
                
                print( 'Got a PyDeadObjectError, which can probably be ignored, but here it is anyway:' )
                print( HydrusData.ToString( value ) )
                print( trace )
                
                return
                
            
            try: job_key.SetVariable( 'popup_message_title', HydrusData.ToString( etype.__name__ ) )
            except: job_key.SetVariable( 'popup_message_title', HydrusData.ToString( etype ) )
            job_key.SetVariable( 'popup_message_text_1', HydrusData.ToString( value ) )
            job_key.SetVariable( 'popup_message_traceback', trace )
            
        
        HydrusGlobals.pubsub.pub( 'message', job_key )
        
    except:
        
        text = 'Encountered an error I could not parse:'
        
        text += os.linesep
        
        text += HydrusData.ToString( ( etype, value, tb ) )
        
        try: text += traceback.format_exc()
        except: pass
        
        HydrusData.ShowText( text )
    
def GenerateExportFilename( media, terms ):

    filename = ''
    
    for ( term_type, term ) in terms:
        
        tags_manager = media.GetTagsManager()
        
        if term_type == 'string': filename += term
        elif term_type == 'namespace':
            
            tags = tags_manager.GetNamespaceSlice( ( term, ), collapse_siblings = True )
            
            filename += ', '.join( [ tag.split( ':' )[1] for tag in tags ] )
            
        elif term_type == 'predicate':
            
            if term in ( 'tags', 'nn tags' ):
                
                current = tags_manager.GetCurrent()
                pending = tags_manager.GetPending()
                
                tags = list( current.union( pending ) )
                
                if term == 'nn tags': tags = [ tag for tag in tags if ':' not in tag ]
                else: tags = [ tag if ':' not in tag else tag.split( ':' )[1] for tag in tags ]
                
                tags.sort()
                
                filename += ', '.join( tags )
                
            elif term == 'hash':
                
                hash = media.GetHash()
                
                filename += hash.encode( 'hex' )
                
            
        elif term_type == 'tag':
            
            if ':' in term: term = term.split( ':' )[1]
            
            if tags_manager.HasTag( term ): filename += term
            
        
    
    return filename
    
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
    
def ParseExportPhrase( phrase ):
    
    try:
        
        terms = [ ( 'string', phrase ) ]
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '[' in term:
                    
                    ( pre, term ) = term.split( '[', 1 )
                    
                    ( namespace, term ) = term.split( ']', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'namespace', namespace ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '{' in term:
                    
                    ( pre, term ) = term.split( '{', 1 )
                    
                    ( predicate, term ) = term.split( '}', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'predicate', predicate ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
        new_terms = []
        
        for ( term_type, term ) in terms:
            
            if term_type == 'string':
                
                while '(' in term:
                    
                    ( pre, term ) = term.split( '(', 1 )
                    
                    ( tag, term ) = term.split( ')', 1 )
                    
                    new_terms.append( ( 'string', pre ) )
                    new_terms.append( ( 'tag', tag ) )
                    
                
            
            new_terms.append( ( term_type, term ) )
            
        
        terms = new_terms
        
    except: raise Exception( 'Could not parse that phrase!' )
    
    return terms
    
def ShowExceptionClient( e ):
    
    job_key = HydrusData.JobKey()
    
    if isinstance( e, HydrusExceptions.DBException ):
        
        ( text, caller_traceback, db_traceback ) = e.args
        
        job_key.SetVariable( 'popup_message_title', 'Database Error!' )
        job_key.SetVariable( 'popup_message_text_1', text )
        job_key.SetVariable( 'popup_message_caller_traceback', caller_traceback )
        job_key.SetVariable( 'popup_message_db_traceback', db_traceback )
        
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
        
        job_key.SetVariable( 'popup_message_title', title )
        job_key.SetVariable( 'popup_message_text_1', HydrusData.ToString( value ) )
        job_key.SetVariable( 'popup_message_traceback', trace )
        
    
    HydrusGlobals.pubsub.pub( 'message', job_key )
    
def ShowTextClient( text ):
    
    job_key = HydrusData.JobKey()
    
    job_key.SetVariable( 'popup_message_text_1', HydrusData.ToString( text ) )
    
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
                    
                
            
        
    
class FileSearchContext( object ):
    
    def __init__( self, file_service_key = CC.COMBINED_FILE_SERVICE_KEY, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True, predicates = None ):
        
        if predicates is None: predicates = []
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        self._include_current_tags = include_current_tags
        self._include_pending_tags = include_pending_tags
        
        self._predicates = predicates
        
        system_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_SYSTEM ]
        
        self._system_predicates = FileSystemPredicates( system_predicates )
        
        tag_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_TAG ]
        
        self._tags_to_include = []
        self._tags_to_exclude = []
        
        for predicate in tag_predicates:
            
            tag = predicate.GetValue()
            
            if predicate.GetInclusive(): self._tags_to_include.append( tag )
            else: self._tags_to_exclude.append( tag )
            
        
        namespace_predicates = [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_NAMESPACE ]
        
        self._namespaces_to_include = []
        self._namespaces_to_exclude = []
        
        for predicate in namespace_predicates:
            
            namespace = predicate.GetValue()
            
            if predicate.GetInclusive(): self._namespaces_to_include.append( namespace )
            else: self._namespaces_to_exclude.append( namespace )
            
        
        wildcard_predicates =  [ predicate for predicate in predicates if predicate.GetPredicateType() == HC.PREDICATE_TYPE_WILDCARD ]
        
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
            
            ( system_predicate_type, info ) = predicate.GetValue()
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_INBOX: self._inbox = True
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_ARCHIVE: self._archive = True
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_LOCAL: self._local = True
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL: self._not_local = True
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HASH:
                
                hash = info
                
                self._common_info[ 'hash' ] = hash
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_AGE:
                
                ( operator, years, months, days, hours ) = info
                
                age = ( ( ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 24 ) + hours ) * 3600 )
                
                now = HydrusData.GetNow()
                
                # this is backwards because we are talking about age, not timestamp
                
                if operator == '<': self._common_info[ 'min_timestamp' ] = now - age
                elif operator == '>': self._common_info[ 'max_timestamp' ] = now - age
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_timestamp' ] = now - int( age * 1.15 )
                    self._common_info[ 'max_timestamp' ] = now - int( age * 0.85 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_MIME:
                
                mimes = info
                
                if type( mimes ) == int: mimes = ( mimes, )
                
                self._common_info[ 'mimes' ] = mimes
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_DURATION:
                
                ( operator, duration ) = info
                
                if operator == '<': self._common_info[ 'max_duration' ] = duration
                elif operator == '>': self._common_info[ 'min_duration' ] = duration
                elif operator == '=': self._common_info[ 'duration' ] = duration
                elif operator == u'\u2248':
                    
                    if duration == 0: self._common_info[ 'duration' ] = 0
                    else:
                        
                        self._common_info[ 'min_duration' ] = int( duration * 0.85 )
                        self._common_info[ 'max_duration' ] = int( duration * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATING:
                
                ( service_key, operator, value ) = info
                
                self._ratings_predicates.append( ( service_key, operator, value ) )
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATIO:
                
                ( operator, ratio_width, ratio_height ) = info
                
                if operator == '=': self._common_info[ 'ratio' ] = ( ratio_width, ratio_height )
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width * 0.85, ratio_height )
                    self._common_info[ 'max_ratio' ] = ( ratio_width * 1.15, ratio_height )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_SIZE:
                
                ( operator, size, unit ) = info
                
                size = size * unit
                
                if operator == '<': self._common_info[ 'max_size' ] = size
                elif operator == '>': self._common_info[ 'min_size' ] = size
                elif operator == '=': self._common_info[ 'size' ] = size
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_size' ] = int( size * 0.85 )
                    self._common_info[ 'max_size' ] = int( size * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS:
                
                ( operator, num_tags ) = info
                
                if operator == '<': self._common_info[ 'max_num_tags' ] = num_tags
                elif operator == '=': self._common_info[ 'num_tags' ] = num_tags
                elif operator == '>': self._common_info[ 'min_num_tags' ] = num_tags
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_WIDTH:
                
                ( operator, width ) = info
                
                if operator == '<': self._common_info[ 'max_width' ] = width
                elif operator == '>': self._common_info[ 'min_width' ] = width
                elif operator == '=': self._common_info[ 'width' ] = width
                elif operator == u'\u2248':
                    
                    if width == 0: self._common_info[ 'width' ] = 0
                    else:
                        
                        self._common_info[ 'min_width' ] = int( width * 0.85 )
                        self._common_info[ 'max_width' ] = int( width * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_PIXELS:
                
                ( operator, num_pixels, unit ) = info
                
                num_pixels = num_pixels * unit
                
                if operator == '<': self._common_info[ 'max_num_pixels' ] = num_pixels
                elif operator == '>': self._common_info[ 'min_num_pixels' ] = num_pixels
                elif operator == '=': self._common_info[ 'num_pixels' ] = num_pixels
                elif operator == u'\u2248':
                    
                    self._common_info[ 'min_num_pixels' ] = int( num_pixels * 0.85 )
                    self._common_info[ 'max_num_pixels' ] = int( num_pixels * 1.15 )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT:
                
                ( operator, height ) = info
                
                if operator == '<': self._common_info[ 'max_height' ] = height
                elif operator == '>': self._common_info[ 'min_height' ] = height
                elif operator == '=': self._common_info[ 'height' ] = height
                elif operator == u'\u2248':
                    
                    if height == 0: self._common_info[ 'height' ] = 0
                    else:
                        
                        self._common_info[ 'min_height' ] = int( height * 0.85 )
                        self._common_info[ 'max_height' ] = int( height * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS:
                
                ( operator, num_words ) = info
                
                if operator == '<': self._common_info[ 'max_num_words' ] = num_words
                elif operator == '>': self._common_info[ 'min_num_words' ] = num_words
                elif operator == '=': self._common_info[ 'num_words' ] = num_words
                elif operator == u'\u2248':
                    
                    if num_words == 0: self._common_info[ 'num_words' ] = 0
                    else:
                        
                        self._common_info[ 'min_num_words' ] = int( num_words * 0.85 )
                        self._common_info[ 'max_num_words' ] = int( num_words * 1.15 )
                        
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_LIMIT:
                
                limit = info
                
                self._limit = limit
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE:
                
                ( operator, current_or_pending, service_key ) = info
                
                if operator == True:
                    
                    if current_or_pending == HC.CURRENT: self._file_services_to_include_current.append( service_key )
                    else: self._file_services_to_include_pending.append( service_key )
                    
                else:
                    
                    if current_or_pending == HC.CURRENT: self._file_services_to_exclude_current.append( service_key )
                    else: self._file_services_to_exclude_pending.append( service_key )
                    
                
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
                
                ( hash, max_hamming ) = info
                
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
    
    def CanDownload( self ): return self._info[ 'account' ].HasPermission( HC.GET_DATA ) and not self.HasRecentError()
    
    def CanDownloadUpdate( self ):
        
        update_due = self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 < HydrusData.GetNow()
        
        return not self.IsPaused() and self.CanDownload() and update_due
        
    
    def CanProcessUpdate( self ): return self._info[ 'next_download_timestamp' ] > self._info[ 'next_processing_timestamp' ]
    
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
    
    def GetLikeDislike( self ): return ( self._info[ 'like' ], self._info[ 'dislike' ] )
    
    def GetLowerUpper( self ): return ( self._info[ 'lower' ], self._info[ 'upper' ] )
    
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
            
        
        downloaded_text = HydrusData.ConvertIntToPrettyString( num_updates_downloaded ) + '/' + HydrusData.ConvertIntToPrettyString( num_updates )
        
        if not self._info[ 'account' ].HasPermission( HC.GET_DATA ): status = 'updates on hold'
        else:
            
            if self.CanDownloadUpdate(): status = 'downloaded up to ' + HydrusData.ConvertTimestampToPrettySync( self._info[ 'next_download_timestamp' ] )
            elif self.CanProcessUpdate(): status = 'processed up to ' + HydrusData.ConvertTimestampToPrettySync( self._info[ 'next_processing_timestamp' ] )
            elif self.HasRecentError(): status = 'due to a previous error, update is delayed - next check ' + self.GetRecentErrorPending()
            else: status = 'fully synchronised - next update ' + HydrusData.ConvertTimestampToPrettyPending( self._info[ 'next_download_timestamp' ] + HC.UPDATE_DURATION + 1800 )
            
        
        return downloaded_text + ' - ' + status
        
    
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
                            
                        
                    
                
            
        
    
    def Request( self, method, command, request_args = None, request_headers = None, report_hooks = None, temp_path = None, return_cookies = False ):
        
        if request_args is None: request_args = {}
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        try:
            
            credentials = self.GetCredentials()
            
            if command in ( 'access_key', 'init', '' ): pass
            elif command in ( 'session_key', 'access_key_verification' ): HydrusNetworking.AddHydrusCredentialsToHeaders( credentials, request_headers )
            else: HydrusNetworking.AddHydrusSessionKeyToHeaders( self._service_key, request_headers )
            
            if command == 'backup': long_timeout = True
            else: long_timeout = False
            
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
            
            ( response, size_of_response, response_headers, cookies ) = wx.GetApp().DoHTTP( method, url, request_headers, body, report_hooks = report_hooks, temp_path = temp_path, return_everything = True, long_timeout = long_timeout )
            
            HydrusNetworking.CheckHydrusVersion( self._service_key, self._service_type, response_headers )
            
            if method == HC.GET: data_used = size_of_response
            elif method == HC.POST: data_used = len( body )
            
            HydrusNetworking.DoHydrusBandwidth( self._service_key, method, command, data_used )
            
            if return_cookies: return ( response, cookies )
            else: return response
            
        except Exception as e:
            
            if isinstance( e, HydrusExceptions.ForbiddenException ):
                
                if HydrusData.ToString( e ) == 'Session not found!':
                    
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
        
    
    def ToTuple( self ): return ( self._service_key, self._service_type, self._name, self._info )
    
class ServicesManager( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        self._keys_to_services = {}
        
        self.RefreshServices()
        
        HydrusGlobals.pubsub.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def GetService( self, service_key ):
        
        with self._lock:
            
            try: return self._keys_to_services[ service_key ]
            except KeyError: raise HydrusExceptions.NotFoundException( 'That service was not found!' )
            
        
    
    def GetServices( self, types = HC.ALL_SERVICES ):
        
        with self._lock: return [ service for service in self._keys_to_services.values() if service.GetServiceType() in types ]
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = wx.GetApp().Read( 'services' )
            
            self._keys_to_services = { service.GetServiceKey() : service for service in services }

class UndoManager( object ):
    
    def __init__( self ):
        
        self._commands = []
        self._inverted_commands = []
        self._current_index = 0
        
        HydrusGlobals.pubsub.sub( self, 'Undo', 'undo' )
        HydrusGlobals.pubsub.sub( self, 'Redo', 'redo' )
        
    
    def _FilterServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        filtered_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_DATA_TYPE_FILES:
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_RESCIND_PETITION ): continue
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
        
        if self._current_index > 0:
            
            self._current_index -= 1
            
            ( action, args, kwargs ) = self._inverted_commands[ self._current_index ]
            
            wx.GetApp().WriteSynchronous( action, *args, **kwargs )
            
            HydrusGlobals.pubsub.pub( 'notify_new_undo' )
            
        
    
    def Redo( self ):
        
        if len( self._commands ) > 0 and self._current_index < len( self._commands ):
            
            ( action, args, kwargs ) = self._commands[ self._current_index ]
            
            self._current_index += 1
            
            wx.GetApp().WriteSynchronous( action, *args, **kwargs )
            
            HydrusGlobals.pubsub.pub( 'notify_new_undo' )

def GetDefaultAdvancedTagOptions( lookup ):
    
    backup_lookup = None
    
    if type( lookup ) == tuple:
        
        ( site_type, site_name ) = lookup
        
        if site_type == HC.SITE_TYPE_BOORU: backup_lookup = HC.SITE_TYPE_BOORU
        
    
    ato_options = HC.options[ 'default_advanced_tag_options' ]
    
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
