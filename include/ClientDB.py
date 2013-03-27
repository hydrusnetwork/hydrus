import collections
import dircache
import hashlib
import httplib
import itertools
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusFlashHandling
import HydrusImageHandling
import HydrusMessageHandling
import HydrusVideoHandling
import HydrusServer
import ClientConstants as CC
import ClientConstantsMessages
import os
import Queue
import random
import shutil
import sqlite3
import sys
import threading
import time
import traceback
import urlparse
import wx
import yaml

class FileDB():
    
    def _AddThumbnails( self, c, thumbnails ):
        
        for ( hash, thumbnail ) in thumbnails:
            
            hash_id = self._GetHashId( c, hash )
            
            thumbnail_path_to = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
            
            with open( thumbnail_path_to, 'wb' ) as f: f.write( thumbnail )
            
            phash = HydrusImageHandling.GeneratePerceptualHash( thumbnail )
            
            c.execute( 'INSERT OR IGNORE INTO perceptual_hashes ( hash_id, phash ) VALUES ( ?, ? );', ( hash_id, sqlite3.Binary( phash ) ) )
            
        
        self.pub( 'new_thumbnails', [ hash for ( hash, thumbnail ) in thumbnails ] )
        
    
    def _CopyFiles( self, hashes ):
        
        if len( hashes ) > 0:
            
            export_path = HC.TEMP_DIR
            
            if not os.path.exists( export_path ): os.mkdir( export_path )
            
            error_messages = set()
            
            paths = []
            
            for hash in hashes:
                
                try:
                    
                    path_from = HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    mime = HC.GetMimeFromPath( path_from )
                    
                    path_to = export_path + os.path.sep + hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ]
                    
                    shutil.copy( path_from, path_to )
                    
                    paths.append( path_to )
                    
                except Exception as e: error_messages.add( unicode( e ) )
                
            
            self.pub( 'clipboard', 'paths', paths )
            
            if len( error_messages ) > 0: raise Exception( 'Some of the file exports failed with the following error message(s):' + os.linesep + os.linesep.join( error_messages ) )
            
        
    
    def _ExportFiles( self, job_key, hashes, cancel_event ):
        
        num_hashes = len( hashes )
        
        if num_hashes > 0:
            
            export_path = HC.ConvertPortablePathToAbsPath( self._options[ 'export_path' ] )
            
            if export_path is None:
                
                with wx.DirDialog( None, message='Pick where to extract the files' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK: export_path = dlg.GetPath()
                    else: return
                    
                
            
            HC.pubsub.pub( 'progress_update', job_key, 0, num_hashes, 'The client is now exporting the files to ' + export_path + ' (0/' + HC.ConvertIntToPrettyString( num_hashes ) + ')' )
            
            error_messages = set()
            
            for ( index, hash ) in enumerate( hashes ):
                
                try:
                    
                    HC.pubsub.pub( 'progress_update', job_key, index, num_hashes, 'The client is now exporting the files to ' + export_path + ' (' + HC.ConvertIntToPrettyString( index + 1 ) + '/' + HC.ConvertIntToPrettyString( num_hashes ) + ')' )
                    
                    path_from = HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    mime = HC.GetMimeFromPath( path_from )
                    
                    # could search for some appropriate tags here, convert them to ascii or whatever, and make sure they are unique given the whole list
                    
                    path_to = export_path + os.path.sep + hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ]
                    
                    shutil.copy( path_from, path_to )
                    
                    if cancel_event.isSet(): break
                    
                except Exception as e: error_messages.add( unicode( e ) )
                
            
            if len( error_messages ) > 0:
                
                HC.pubsub.pub( 'progress_update', job_key, 1, 1, '' )
                
                raise Exception( 'Some of the file exports failed with the following error message(s):' + os.linesep + os.linesep.join( error_messages ) )
                
            
            HC.pubsub.pub( 'progress_update', job_key, num_hashes, num_hashes, 'done!' )
            
        else: HC.pubsub.pub( 'progress_update', job_key, 1, 1, '' )
        
    
    def _GenerateHashIdsEfficiently( self, c, hashes ):
        
        hashes_not_in_db = set( hashes )
        
        for i in range( 0, len( hashes ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            hashes_subset = hashes[ i : i + 250 ]
            
            hashes_not_in_db.difference_update( [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes WHERE hash IN (' + ','.join( '?' * len( hashes_subset ) ) + ');', [ sqlite3.Binary( hash ) for hash in hashes_subset ] ) ] )
            
        
        if len( hashes_not_in_db ) > 0: c.executemany( 'INSERT INTO hashes ( hash ) VALUES( ? );', [ ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ] )
        
    
    def _GetFile( self, hash ):
        
        try:
            
            with open( HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' ), 'rb' ) as f: file = f.read()
            
        except MemoryError: print( 'Memory error!' )
        except: raise Exception( 'Could not find that file!' )
        
        return file
        
    
    def _GetHash( self, c, hash_id ):
        
        result = c.execute( 'SELECT hash FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None: raise Exception( 'File hash error in database' )
        
        ( hash, ) = result
        
        return hash
        
    
    def _GetHashes( self, c, hash_ids ): return [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ) ]
    
    def _GetHashId( self, c, hash ):
        
        result = c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            hash_id = c.lastrowid
            
        else: ( hash_id, ) = result
        
        return hash_id
        
    
    def _GetHashIds( self, c, hashes ):
        
        hash_ids = []
        
        if type( hashes ) == type( set() ): hashes = list( hashes )
        
        for i in range( 0, len( hashes ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            hashes_subset = hashes[ i : i + 250 ]
            
            hash_ids.extend( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM hashes WHERE hash IN (' + ','.join( '?' * len( hashes_subset ) ) + ');', [ sqlite3.Binary( hash ) for hash in hashes_subset ] ) ] )
            
        
        if len( hashes ) > len( hash_ids ):
            
            if len( set( hashes ) ) > len( hash_ids ):
                
                # must be some new hashes the db has not seen before, so let's generate them as appropriate
                
                self._GenerateHashIdsEfficiently( c, hashes )
                
                hash_ids = self._GetHashIds( c, hashes )
                
            
        
        return hash_ids
        
    
    def _GetHashIdsToHashes( self, c, hash_ids ): return { hash_id : hash for ( hash_id, hash ) in c.execute( 'SELECT hash_id, hash FROM hashes WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ) }
    
    def _GetThumbnail( self, hash, full_size = False ):
        
        if full_size:
            
            path_to = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
            
            with open( path_to, 'rb' ) as f: thumbnail = f.read()
            
        else:
            
            path_to = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' ) + '_resized'
            
            if os.path.exists( path_to ):
                
                with open( path_to, 'rb' ) as f: thumbnail = f.read()
                
            else:
                
                path_to_full = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
                
                with open( path_to_full, 'rb' ) as f: thumbnail_full = f.read()
                
                thumbnail_dimensions = self._options[ 'thumbnail_dimensions' ]
                
                thumbnail = HydrusImageHandling.GenerateThumbnailFileFromFile( thumbnail_full, thumbnail_dimensions )
                
                with open( path_to, 'wb' ) as f: f.write( thumbnail )
                
            
        
        return thumbnail
        
    
class MessageDB():
    
    def _AddContact( self, c, contact ):
        
        ( public_key, name, host, port ) = contact.GetInfo()
        
        contact_key = contact.GetContactKey()
        
        if public_key is not None: contact_key = sqlite3.Binary( contact_key )
        
        c.execute( 'INSERT OR IGNORE INTO contacts ( contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ? );', ( contact_key, public_key, name, host, port ) )
        
    
    def _AddMessage( self, c, transport_message, serverside_message_key = None, forced_status = None ):
        
        ( contact_from, contacts_to, message_key, conversation_key, timestamp, subject, body, files ) = transport_message.GetInfo()
        
        if contact_from is None or contact_from.GetName() == 'Anonymous':
            
            contact_id_from = 1
            
        else:
            
            contact_id_from = self._GetContactId( c, contact_from )
            
            # changes whatever they want to say their name and public key is to whatever we prefer it to be
            contact_from = self._GetContact( c, contact_id_from )
            
            public_key = contact_from.GetPublicKey()
            
            try: transport_message.VerifyIsFromCorrectPerson( public_key )
            except:
                
                self.pub( 'log_message', 'synchronise messages daemon', 'received a message that did not verify' )
                
                return
                
            
        
        conversation_id = self._GetConversationId( c, conversation_key, subject )
        
        message_id = self._GetMessageId( c, message_key )
        
        result = c.execute( 'SELECT 1 FROM messages WHERE message_id = ?;', ( message_id, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT OR IGNORE INTO messages ( conversation_id, message_id, contact_id_from, timestamp ) VALUES ( ?, ?, ?, ? );', ( conversation_id, message_id, contact_id_from, timestamp ) )
            
            c.execute( 'INSERT OR IGNORE INTO message_bodies ( docid, body ) VALUES ( ?, ? );', ( message_id, body ) )
            
            attachment_hashes = []
            
            if len( files ) > 0:
                
                for file in files:
                    
                    try:
                        
                        ( result, hash ) = self._ImportFile( c, file, override_deleted = True ) # what if the file fails?
                        
                        attachment_hashes.append( hash )
                        
                    except: pass
                    
                
                hash_ids = self._GetHashIds( c, attachment_hashes )
                
                c.executemany( 'INSERT OR IGNORE INTO message_attachments ( message_id, hash_id ) VALUES ( ?, ? );', [ ( message_id, hash_id ) for hash_id in hash_ids ] )
                
            
            if forced_status is None: status = 'sent'
            else: status = forced_status
            
            status_id = self._GetStatusId( c, status )
            
            inboxable_contact_ids = { id for ( id, ) in c.execute( 'SELECT contact_id FROM message_depots;' ) }
            
            inbox = False
            
            for contact_to in contacts_to:
                
                contact_id_to = self._GetContactId( c, contact_to )
                
                if contact_id_to in inboxable_contact_ids:
                    
                    c.execute( 'INSERT OR IGNORE INTO message_inbox ( message_id ) VALUES ( ? );', ( message_id, ) )
                    
                    inbox = True
                    
                
                c.execute( 'INSERT OR IGNORE INTO message_destination_map ( message_id, contact_id_to, status_id ) VALUES ( ?, ?, ? );', ( message_id, contact_id_to, status_id ) )
                
            
            destinations = [ ( contact_to, status ) for contact_to in contacts_to ]
            
            message = ClientConstantsMessages.Message( message_key, contact_from, destinations, timestamp, body, attachment_hashes, inbox )
            
            self.pub( 'new_message', conversation_key, message )
            
        
        if serverside_message_key is not None:
            
            serverside_message_id = self._GetMessageId( c, serverside_message_key )
            
            c.execute( 'DELETE FROM message_downloads WHERE message_id = ?;', ( serverside_message_id, ) )
            
        
    
    def _AddMessageInfoSince( self, c, service_identifier, serverside_message_keys, statuses, new_last_check ):
        
        # message_keys
        
        service_id = self._GetServiceId( c, service_identifier )
        
        serverside_message_ids = set( self._GetMessageIds( c, serverside_message_keys ) )
        
        c.executemany( 'INSERT OR IGNORE INTO message_downloads ( service_id, message_id ) VALUES ( ?, ? );', [ ( service_id, serverside_message_id ) for serverside_message_id in serverside_message_ids ] )
        
        # statuses
        
        message_keys_dict = {}
        statuses_dict = {}
        
        inserts = []
        
        for ( message_key, contact_key, status ) in statuses:
            
            if message_key in message_keys_dict: message_id = message_keys_dict[ message_key ]
            else:
                
                message_id = self._GetMessageId( c, message_key )
                
                message_keys_dict[ message_key ] = message_id
                
            
            if status in statuses_dict: status_id = statuses_dict[ status ]
            else:
                
                status_id = self._GetStatusId( c, status )
                
                statuses_dict[ status ] = status_id
                
            
            inserts.append( ( message_id, sqlite3.Binary( contact_key ), status_id ) )
            
        
        # replace is important here
        c.executemany( 'INSERT OR REPLACE INTO incoming_message_statuses ( message_id, contact_key, status_id ) VALUES ( ?, ?, ? );', inserts )
        
        # finally:
        
        c.execute( 'UPDATE message_depots SET last_check = ? WHERE service_id = ?;', ( new_last_check, service_id ) )
        
    
    def _ArchiveConversation( self, c, conversation_key ):
        
        conversation_id = self._GetMessageId( c, conversation_key )
        
        message_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM messages WHERE conversation_id = ?;', ( conversation_id, ) ) ]
        
        c.execute( 'DELETE FROM message_inbox WHERE message_id IN ' + HC.SplayListForDB( message_ids ) + ';' )
        
        self.pub( 'archive_conversation_data', conversation_key )
        self.pub( 'archive_conversation_gui', conversation_key )
        
        self._DoStatusNumInbox( c )
        
    
    def _AssociateContact( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service = self._GetService( c, service_id )
        
        private_key = service.GetPrivateKey()
        
        public_key = HydrusMessageHandling.GetPublicKey( private_key )
        
        contact_key = hashlib.sha256( public_key ).digest()
        
        contact_id = self._GetContactId( c, service_id )
        
        c.execute( 'UPDATE contacts SET contact_key = ?, public_key = ? WHERE contact_id = ?;', ( sqlite3.Binary( contact_key ), public_key, contact_id ) )
        
    
    def _DeleteConversation( self, c, conversation_key ):
        
        conversation_id = self._GetMessageId( c, conversation_key )
        
        message_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM messages WHERE conversation_id = ?;', ( conversation_id, ) ) ]
        
        splayed_message_ids = HC.SplayListForDB( message_ids )
        
        c.execute( 'DELETE FROM message_keys WHERE message_id IN ' + splayed_message_ids + ';' )
        c.execute( 'DELETE FROM message_bodies WHERE docid IN ' + splayed_message_ids + ';' )
        c.execute( 'DELETE FROM conversation_subjects WHERE docid IN ' + splayed_message_ids + ';' )
        
        self.pub( 'delete_conversation_data', conversation_key )
        self.pub( 'delete_conversation_gui', conversation_key )
        
        self._DoStatusNumInbox( c )
        
    
    def _DeleteDraft( self, c, draft_key ):
        
        message_id = self._GetMessageId( c, draft_key )
        
        c.execute( 'DELETE FROM message_keys WHERE message_id = ?;', ( message_id, ) )
        c.execute( 'DELETE FROM message_bodies WHERE docid = ?;', ( message_id, ) )
        c.execute( 'DELETE FROM conversation_subjects WHERE docid = ?;', ( message_id, ) )
        
        self.pub( 'delete_draft_data', draft_key )
        self.pub( 'delete_draft_gui', draft_key )
        self.pub( 'notify_check_messages' )
        
    
    def _DoMessageQuery( self, c, query_key, search_context ):
        
        identity = search_context.GetIdentity()
        
        name = identity.GetName()
        
        contact_id = self._GetContactId( c, identity )
        
        system_predicates = search_context.GetSystemPredicates()
        
        ( inbox, archive, draft, status, contact_from, contact_to, contact_started, min_timestamp, max_timestamp ) = system_predicates.GetInfo()
        
        if draft:
            
            draft_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM messages, message_drafts USING ( message_id ) WHERE contact_id_from = ?;', ( contact_id, ) ) ]
            
            query_message_ids = draft_ids
            
        else:
            
            sql_predicates = [ '( contact_id_from = ' + str( contact_id ) + ' OR contact_id_to = ' + str( contact_id ) + ' )' ]
            
            if name != 'Anonymous':
                
                service = self._GetService( c, identity )
                
                if not service.ReceivesAnon(): sql_predicates.append( 'contact_id_from != 1' )
                
            
            if status is not None:
                
                if status == 'unread': status = 'sent'
                
                status_id = self._GetStatusId( c, status )
                
                sql_predicates.append( '( contact_id_to = ' + str( contact_id ) + ' AND status_id = ' + str( status_id ) + ')' )
                
            
            if contact_from is not None:
                
                contact_id_from = self._GetContactId( c, contact_from )
                
                sql_predicates.append( 'contact_id_from = ' + str( contact_id_from ) )
                
            
            if contact_to is not None:
                
                contact_id_to = self._GetContactId( c, contact_to )
                
                sql_predicates.append( 'contact_id_to = ' + str( contact_id_to ) )
                
            
            if contact_started is not None:
                
                contact_id_started = self._GetContactId( c, contact_started )
                
                sql_predicates.append( 'conversation_id = message_id AND contact_id_from = ' + str( contact_id_started ) )
                
            
            if min_timestamp is not None: sql_predicates.append( 'timestamp >= ' + str( min_timestamp ) )
            if max_timestamp is not None: sql_predicates.append( 'timestamp <= ' + str( max_timestamp ) )
            
            query_message_ids = { message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM messages, message_destination_map USING ( message_id ) WHERE ' + ' AND '.join( sql_predicates ) + ';' ) }
            
            if inbox or archive:
                
                inbox_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM message_inbox, message_destination_map USING ( message_id ) WHERE contact_id_to = ?;', ( contact_id, ) ) ]
                
                if inbox: query_message_ids.intersection_update( inbox_ids )
                elif archive: query_message_ids.difference_update( inbox_ids )
                
            
        
        for term in search_context.GetTermsToInclude():
            
            body_query_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT docid FROM message_bodies WHERE body MATCH ?;', ( term, ) ) ]
            subject_query_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT docid FROM conversation_subjects WHERE subject MATCH ?;', ( term, ) ) ]
            
            query_message_ids.intersection_update( body_query_ids + subject_query_ids )
            
        
        for term in search_context.GetTermsToExclude():
            
            body_query_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT docid FROM message_bodies WHERE body MATCH ?;', ( term, ) ) ]
            subject_query_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT docid FROM conversation_subjects WHERE subject MATCH ?;', ( term, ) ) ]
            
            query_message_ids.difference_update( body_query_ids + subject_query_ids )
            
        
        conversations = self._GetConversations( c, search_context, query_message_ids )
        
        self.pub( 'message_query_done', query_key, conversations )
        
    
    def _DoStatusNumInbox( self, c ):
        
        convo_ids = { id for ( id, ) in c.execute( 'SELECT conversation_id FROM messages, message_inbox USING ( message_id );' ) }
        
        num_inbox = len( convo_ids )
        
        if num_inbox == 0: inbox_string = 'inbox empty'
        else: inbox_string = str( num_inbox ) + ' in inbox'
        
        self.pub( 'inbox_status', inbox_string )
        
    
    def _DraftMessage( self, c, draft_message ):
        
        ( draft_key, conversation_key, subject, contact_from, contact_names_to, recipients_visible, body, attachment_hashes ) = draft_message.GetInfo()
        
        old_message_id = self._GetMessageId( c, draft_key )
        
        c.execute( 'DELETE FROM message_keys WHERE message_id = ?;', ( old_message_id, ) )
        c.execute( 'DELETE FROM message_bodies WHERE docid = ?;', ( old_message_id, ) )
        c.execute( 'DELETE FROM conversation_subjects WHERE docid = ?;', ( old_message_id, ) )
        
        message_id = self._GetMessageId( c, draft_key )
        
        conversation_id = self._GetConversationId( c, conversation_key, subject )
        
        contact_id_from = self._GetContactId( c, contact_from )
        
        c.execute( 'INSERT INTO messages ( conversation_id, message_id, contact_id_from, timestamp ) VALUES ( ?, ?, ?, ? );', ( conversation_id, message_id, contact_id_from, None ) )
        
        c.execute( 'INSERT INTO message_bodies ( docid, body ) VALUES ( ?, ? );', ( message_id, body ) )
        
        status_id = self._GetStatusId( c, 'draft' )
        
        contact_ids_to = [ self._GetContactId( c, contact_name_to ) for contact_name_to in contact_names_to ]
        
        c.executemany( 'INSERT INTO message_destination_map ( message_id, contact_id_to, status_id ) VALUES ( ?, ?, ? );', [ ( message_id, contact_id_to, status_id ) for contact_id_to in contact_ids_to ] )
        
        c.execute( 'INSERT INTO message_drafts ( message_id, recipients_visible ) VALUES ( ?, ? );', ( message_id, recipients_visible ) )
        
        hash_ids = self._GetHashIds( c, attachment_hashes )
        
        c.executemany( 'INSERT INTO message_attachments ( message_id, hash_id ) VALUES ( ?, ? );', [ ( message_id, hash_id ) for hash_id in hash_ids ] )
        
        self.pub( 'draft_saved', draft_key, draft_message )
        
    
    def _FlushMessageStatuses( self, c ):
        
        incoming_message_statuses = HC.BuildKeyToListDict( [ ( message_id, ( contact_key, status_id ) ) for ( message_id, contact_key, status_id ) in c.execute( 'SELECT message_id, contact_key, status_id FROM incoming_message_statuses, messages USING ( message_id );' ) ] )
        
        for ( message_id, status_infos ) in incoming_message_statuses.items():
            
            for ( contact_key, status_id ) in status_infos:
                
                try:
                    
                    contact_id_to = self._GetContactId( c, contact_key )
                    
                    c.execute( 'INSERT OR REPLACE INTO message_destination_map ( message_id, contact_id_to, status_id ) VALUES ( ?, ?, ? );', ( message_id, contact_id_to, status_id ) )
                    
                except: pass
                
            
            c.execute( 'DELETE FROM incoming_message_statuses WHERE message_id = ?;', ( message_id, ) )
            
            message_key = self._GetMessageKey( c, message_id )
            
            status_updates = [ ( contact_key, self._GetStatus( c, status_id ) ) for ( contact_key, status_id ) in status_infos ]
            
            self.pub( 'message_statuses_data', message_key, status_updates )
            self.pub( 'message_statuses_gui', message_key, status_updates )
            
        
    
    def _GenerateMessageIdsEfficiently( self, c, message_keys ):
        
        message_keys_not_in_db = set( message_keys )
        
        for i in range( 0, len( message_keys ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            message_keys_subset = message_keys[ i : i + 250 ]
            
            message_keys_not_in_db.difference_update( [ message_key for ( message_key, ) in c.execute( 'SELECT message_key FROM message_keys WHERE message_key IN (' + ','.join( '?' * len( message_keys_subset ) ) + ');', [ sqlite3.Binary( message_key ) for message_key in message_keys_subset ] ) ] )
            
        
        if len( message_keys_not_in_db ) > 0: c.executemany( 'INSERT INTO message_keys ( message_key ) VALUES( ? );', [ ( sqlite3.Binary( message_key ), ) for message_key in message_keys_not_in_db ] )
        
    
    def _GetAutocompleteContacts( self, c, half_complete_name, name_to_exclude = None ):
        
        # expand this later to do groups as well
        
        names = [ name for ( name, ) in c.execute( 'SELECT name FROM contacts WHERE name LIKE ? AND name != ? AND public_key NOTNULL;', ( half_complete_name + '%', 'Anonymous' ) ) ]
        
        if name_to_exclude is not None: names = [ name for name in names if name != name_to_exclude ]
        
        matches = CC.AutocompleteMatches( names )
        
        return matches
        
    
    def _GetContact( self, c, parameter ):
        
        if type( parameter ) == int: ( public_key, name, host, port ) = c.execute( 'SELECT public_key, name, host, port FROM contacts WHERE contact_id = ?;', ( parameter, ) ).fetchone()
        elif type( parameter ) in ( str, unicode ):
            try: ( public_key, name, host, port ) = c.execute( 'SELECT public_key, name, host, port FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( parameter ), ) ).fetchone()
            except: ( public_key, name, host, port ) = c.execute( 'SELECT public_key, name, host, port FROM contacts WHERE name = ?;', ( parameter, ) ).fetchone()
        else: print( type( parameter ) )
        
        return ClientConstantsMessages.Contact( public_key, name, host, port )
        
    
    def _GetContactId( self, c, parameter ):
        
        if type( parameter ) in ( str, unicode ): 
            
            if parameter == 'Anonymous': return 1
            
            try: ( contact_id, ) = c.execute( 'SELECT contact_id FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( parameter ), ) ).fetchone()
            except: ( contact_id, ) = c.execute( 'SELECT contact_id FROM contacts WHERE name = ?;', ( parameter, ) ).fetchone()
            
        elif type( parameter ) == int: ( contact_id, ) = c.execute( 'SELECT contact_id FROM contacts, message_depots USING ( contact_id ) WHERE service_id = ?;', ( parameter, ) ).fetchone()
        elif type( parameter ) == ClientConstantsMessages.Contact:
            
            contact_key = parameter.GetContactKey()
            
            name = parameter.GetName()
            
            if name == 'Anonymous': return 1
            
            if contact_key is not None:
                
                result = c.execute( 'SELECT contact_id FROM contacts WHERE contact_key = ?;', ( sqlite3.Binary( contact_key ), ) ).fetchone()
                
                if result is None:
                    
                    # we have a new contact from an outside source!
                    # let's generate a name that'll fit into the db
                    
                    while c.execute( 'SELECT 1 FROM contacts WHERE name = ?;', ( name, ) ).fetchone() is not None: name += str( random.randint( 0, 9 ) )
                    
                
            else:
                
                # one of our user-entered contacts that doesn't have a public key yet
                
                result = c.execute( 'SELECT contact_id FROM contacts WHERE name = ?;', ( name, ) ).fetchone()
                
            
            if result is None:
                
                public_key = parameter.GetPublicKey()
                ( host, port ) = parameter.GetAddress()
                
                if public_key is not None: contact_key = sqlite3.Binary( contact_key )
                
                c.execute( 'INSERT INTO contacts ( contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ? );', ( contact_key, public_key, name, host, port ) )
                
                contact_id = c.lastrowid
                
            else: ( contact_id, ) = result
            
        
        return contact_id
        
    
    def _GetContactIdsToContacts( self, c, contact_ids ): return { contact_id : ClientConstantsMessages.Contact( public_key, name, host, port ) for ( contact_id, public_key, name, host, port ) in c.execute( 'SELECT contact_id, public_key, name, host, port FROM contacts WHERE contact_id IN ' + HC.SplayListForDB( contact_ids ) + ';' ) }
    
    def _GetContactNames( self, c ): return [ name for ( name, ) in c.execute( 'SELECT name FROM contacts;' ) ]
    
    def _GetConversations( self, c, search_context, query_message_ids ):
        
        system_predicates = search_context.GetSystemPredicates()
        
        conversation_ids = { conversation_id for ( conversation_id, ) in c.execute( 'SELECT conversation_id FROM messages WHERE message_id IN ' + HC.SplayListForDB( query_message_ids ) + ';' ) }
        
        splayed_conversation_ids = HC.SplayListForDB( conversation_ids )
        
        conversation_infos = c.execute( 'SELECT message_id, message_key, subject FROM message_keys, conversation_subjects ON message_id = conversation_subjects.docid WHERE message_id IN ' + splayed_conversation_ids + ';' ).fetchall()
        
        conversation_ids_to_message_infos = HC.BuildKeyToListDict( [ ( conversation_id, ( message_id, contact_id_from, timestamp, body ) ) for ( conversation_id, message_id, contact_id_from, timestamp, body ) in c.execute( 'SELECT conversation_id, message_id, contact_id_from, timestamp, body FROM messages, message_bodies ON message_id = message_bodies.docid WHERE conversation_id IN ' + splayed_conversation_ids + ' ORDER BY timestamp ASC;' ) ] )
        
        message_ids = []
        contact_ids = set()
        
        for message_infos in conversation_ids_to_message_infos.values():
            
            message_ids.extend( [ message_id for ( message_id, contact_id_from, timestamp, body ) in message_infos ] )
            contact_ids.update( [ contact_id_from for ( message_id, contact_id_from, timestamp, body ) in message_infos ] )
            
        
        message_ids_to_message_keys = self._GetMessageIdsToMessageKeys( c, message_ids )
        
        splayed_message_ids = HC.SplayListForDB( message_ids )
        
        message_ids_to_destination_ids = HC.BuildKeyToListDict( [ ( message_id, ( contact_id_to, status_id ) ) for ( message_id, contact_id_to, status_id ) in c.execute( 'SELECT message_id, contact_id_to, status_id FROM message_destination_map WHERE message_id IN ' + splayed_message_ids + ';' ) ] )
        
        messages_ids_to_recipients_visible = { message_id : recipients_visible for ( message_id, recipients_visible ) in c.execute( 'SELECT message_id, recipients_visible FROM message_drafts;' ) }
        
        status_ids = set()
        
        for destination_ids in message_ids_to_destination_ids.values():
            
            contact_ids.update( [ contact_id_to for ( contact_id_to, status_id ) in destination_ids ] )
            status_ids.update( [ status_id for ( contact_id_to, status_id ) in destination_ids ] )
            
        
        contact_ids_to_contacts = self._GetContactIdsToContacts( c, contact_ids )
        status_ids_to_statuses = self._GetStatusIdsToStatuses( c, status_ids )
        
        message_ids_to_hash_ids = HC.BuildKeyToListDict( c.execute( 'SELECT message_id, hash_id FROM message_attachments WHERE message_id IN ' + splayed_message_ids + ';' ).fetchall() )
        
        hash_ids = set()
        
        for sub_hash_ids in message_ids_to_hash_ids.values(): hash_ids.update( sub_hash_ids )
        
        hash_ids_to_hashes = self._GetHashIdsToHashes( c, hash_ids )
        
        identity = search_context.GetIdentity()
        
        inbox_ids = { message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM message_inbox;' ) }
        
        conversations = []
        
        for ( conversation_id, conversation_key, subject ) in conversation_infos:
            
            messages = []
            drafts = []
            
            can_add = False
            
            for ( message_id, contact_id_from, timestamp, body ) in conversation_ids_to_message_infos[ conversation_id ]:
                
                message_key = message_ids_to_message_keys[ message_id ]
                
                contact_from = contact_ids_to_contacts[ contact_id_from ]
                
                attachment_hashes = [ hash_ids_to_hashes[ hash_id ] for hash_id in message_ids_to_hash_ids[ message_id ] ]
                
                if system_predicates.Ok( len( attachment_hashes ) ): can_add = True
                
                attachment_hashes.sort()
                
                destination_ids = message_ids_to_destination_ids[ message_id ]
                
                if message_id in messages_ids_to_recipients_visible:
                    
                    # this is a draft
                    
                    contact_names_to = [ contact_ids_to_contacts[ contact_id_to ].GetName() for ( contact_id_to, status_id ) in destination_ids ]
                    
                    recipients_visible = messages_ids_to_recipients_visible[ message_id ]
                    
                    drafts.append( ClientConstantsMessages.DraftMessage( message_key, conversation_key, subject, contact_from, contact_names_to, recipients_visible, body, attachment_hashes ) )
                    
                else:
                    
                    inbox = message_id in inbox_ids
                    
                    destinations = [ ( contact_ids_to_contacts[ contact_id_to ], status_ids_to_statuses[ status_id ] ) for ( contact_id_to, status_id ) in destination_ids ]
                    
                    messages.append( ClientConstantsMessages.Message( message_key, contact_from, destinations, timestamp, body, attachment_hashes, inbox ) )
                    
                
            
            if can_add: conversations.append( ClientConstantsMessages.Conversation( identity, conversation_key, subject, messages, drafts, search_context ) )
            
        
        return conversations
        
    
    def _GetConversationId( self, c, conversation_key, subject ):
        
        result = c.execute( 'SELECT message_id FROM message_keys, conversation_subjects ON message_id = conversation_subjects.docid WHERE message_key = ?;', ( sqlite3.Binary( conversation_key ), ) ).fetchone()
        
        if result is None:
            
            conversation_id = self._GetMessageId( c, conversation_key )
            
            c.execute( 'INSERT INTO conversation_subjects ( docid, subject ) VALUES ( ?, ? );', ( conversation_id, subject ) )
            
        else: ( conversation_id, ) = result
        
        return conversation_id
        
    
    def _GetIdentities( self, c ):
        
        my_identities = [ ClientConstantsMessages.Contact( public_key, name, host, port ) for ( public_key, name, host, port ) in c.execute( 'SELECT public_key, name, host, port FROM contacts, message_depots USING ( contact_id ) ORDER BY name ASC;' ) ]
        
        return my_identities + [ self._GetContact( c, 'Anonymous' ) ]
        
    
    def _GetIdentitiesAndContacts( self, c ):
        
        contacts_info = c.execute( 'SELECT contact_id, public_key, name, host, port FROM contacts ORDER BY name ASC;' ).fetchall()
        
        identity_ids = { contact_id for ( contact_id, ) in c.execute( 'SELECT contact_id FROM message_depots;' ) }
        
        identities = [ ClientConstantsMessages.Contact( public_key, name, host, port ) for ( contact_id, public_key, name, host, port ) in contacts_info if contact_id in identity_ids ]
        contacts = [ ClientConstantsMessages.Contact( public_key, name, host, port ) for ( contact_id, public_key, name, host, port ) in contacts_info if contact_id not in identity_ids and name != 'Anonymous' ]
        
        contact_contact_ids = [ contact_id for ( contact_id, public_key, name, host, port ) in contacts_info if contact_id not in identity_ids and name != 'Anonymous' ]
        
        deletable_names = { name for ( name, ) in c.execute( 'SELECT name FROM contacts WHERE contact_id IN ' + HC.SplayListForDB( contact_contact_ids ) + ' AND NOT EXISTS ( SELECT 1 FROM message_destination_map WHERE contact_id_to = contact_id ) AND NOT EXISTS ( SELECT 1 FROM messages WHERE contact_id_from = contact_id );' ) }
        
        return ( identities, contacts, deletable_names )
        
    
    def _GetMessageId( self, c, message_key ):
        
        result = c.execute( 'SELECT message_id FROM message_keys WHERE message_key = ?;', ( sqlite3.Binary( message_key ), ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO message_keys ( message_key ) VALUES ( ? );', ( sqlite3.Binary( message_key ), ) )
            
            message_id = c.lastrowid
            
        else: ( message_id, ) = result
        
        return message_id
        
    
    def _GetMessageIds( self, c, message_keys ):
        
        message_ids = []
        
        if type( message_keys ) == type( set() ): message_keys = list( message_keys )
        
        for i in range( 0, len( message_keys ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            message_keys_subset = message_keys[ i : i + 250 ]
            
            message_ids.extend( [ message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM message_keys WHERE message_key IN (' + ','.join( '?' * len( message_keys_subset ) ) + ');', [ sqlite3.Binary( message_key ) for message_key in message_keys_subset ] ) ] )
            
        
        if len( message_keys ) > len( message_ids ):
            
            if len( set( message_keys ) ) > len( message_ids ):
                
                # must be some new messages the db has not seen before, so let's generate them as appropriate
                
                self._GenerateMessageIdsEfficiently( c, message_keys )
                
                message_ids = self._GetMessageIds( c, message_keys )
                
            
        
        return message_ids
        
    
    def _GetMessageIdsToMessages( self, c, message_ids ): return { message_id : message for ( message_id, message ) in c.execute( 'SELECT message_id, message FROM messages WHERE message_id IN ' + HC.SplayListForDB( message_ids ) + ';' ) }
    
    def _GetMessageIdsToMessageKeys( self, c, message_ids ): return { message_id : message_key for ( message_id, message_key ) in c.execute( 'SELECT message_id, message_key FROM message_keys WHERE message_id IN ' + HC.SplayListForDB( message_ids ) + ';' ) }
    
    def _GetMessageKey( self, c, message_id ):
        
        result = c.execute( 'SELECT message_key FROM message_keys WHERE message_id = ?;', ( message_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Message key error in database' )
        
        ( message_key, ) = result
        
        return message_key
        
    
    def _GetMessageKeysToDownload( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        message_keys = [ message_key for ( message_key, ) in c.execute( 'SELECT message_key FROM message_downloads, message_keys USING ( message_id ) WHERE service_id = ?;', ( service_id, ) ) ]
        
        return message_keys
        
    
    def _GetMessagesToSend( self, c ):
        
        status_id = self._GetStatusId( c, 'pending' )
        
        message_id_to_contact_ids = HC.BuildKeyToListDict( c.execute( 'SELECT message_id, contact_id_to FROM message_destination_map WHERE status_id = ?;', ( status_id, ) ) )
        
        messages_to_send = [ ( self._GetMessageKey( c, message_id ), [ self._GetContact( c, contact_id_to ) for contact_id_to in contact_ids_to ] ) for ( message_id, contact_ids_to ) in message_id_to_contact_ids.items() ]
        
        return messages_to_send
        
    
    def _GetStatus( self, c, status_id ):
        
        result = c.execute( 'SELECT status FROM statuses WHERE status_id = ?;', ( status_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Status error in database' )
        
        ( status, ) = result
        
        return status
        
    
    def _GetStatusId( self, c, status ):
        
        result = c.execute( 'SELECT status_id FROM statuses WHERE status = ?;', ( status, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO statuses ( status ) VALUES ( ? );', ( status, ) )
            
            status_id = c.lastrowid
            
        else: ( status_id, ) = result
        
        return status_id
        
    
    def _GetStatusIdsToStatuses( self, c, status_ids ): return { status_id : status for ( status_id, status ) in c.execute( 'SELECT status_id, status FROM statuses WHERE status_id IN ' + HC.SplayListForDB( status_ids ) + ';' ) }
    
    def _GetTransportMessage( self, c, message_key ):
        
        message_id = self._GetMessageId( c, message_key )
        
        ( conversation_id, contact_id_from, timestamp ) = c.execute( 'SELECT conversation_id, contact_id_from, timestamp FROM messages WHERE message_id = ?;', ( message_id, ) ).fetchone()
        
        contact_ids_to = [ contact_id_to for ( contact_id_to, ) in c.execute( 'SELECT contact_id_to FROM message_destination_map WHERE message_id = ?;', ( message_id, ) ) ]
        
        ( subject, ) = c.execute( 'SELECT subject FROM conversation_subjects WHERE docid = ?;', ( conversation_id, ) ).fetchone()
        
        ( body, ) = c.execute( 'SELECT body FROM message_bodies WHERE docid = ?;', ( message_id, ) ).fetchone()
        
        attachment_hashes = [ hash for ( hash, ) in c.execute( 'SELECT hash FROM message_attachments, hashes USING ( hash_id ) WHERE message_id = ?;', ( message_id, ) ) ]
        
        attachment_hashes.sort()
        
        files = [ self._GetFile( c, hash ) for hash in attachment_hashes ]
        
        conversation_key = self._GetMessageKey( c, conversation_id )
        
        contact_from = self._GetContact( c, contact_id_from )
        
        contacts_to = [ self._GetContact( c, contact_id_to ) for contact_id_to in contact_ids_to ]
        
        if contact_from.GetName() == 'Anonymous':
            
            contact_from = None
            message_depot = None
            private_key = None
            
        else:
            
            message_depot = self._GetService( c, contact_from )
            private_key = message_depot.GetPrivateKey()
            
        
        if conversation_key == message_key: conversation_key = None
        
        message = HydrusMessageHandling.Message( conversation_key, contact_from, contacts_to, subject, body, timestamp, files = files, private_key = private_key )
        
        return message
        
    
    def _GetTransportMessagesFromDraft( self, c, draft_message ):
        
        ( draft_key, conversation_key, subject, contact_from, contact_names_to, recipients_visible, body, attachment_hashes ) = draft_message.GetInfo()
        
        ( xml, html ) = yaml.safe_load( body )
        
        body = html
        
        files = [ self._GetFile( c, hash ) for hash in attachment_hashes ]
        
        contact_id_from = self._GetContactId( c, contact_from )
        
        if contact_from.GetName() == 'Anonymous':
            
            contact_from = None
            message_depot = None
            private_key = None
            
        else:
            
            message_depot = self._GetService( c, contact_from )
            private_key = message_depot.GetPrivateKey()
            
        
        timestamp = int( time.time() )
        
        contacts_to = [ self._GetContact( c, contact_name_to ) for contact_name_to in contact_names_to ]
        
        if conversation_key == draft_key: conversation_key = None
        
        if recipients_visible: messages = [ HydrusMessageHandling.Message( conversation_key, contact_from, contacts_to, subject, body, timestamp, files = files, private_key = private_key ) ]
        else: messages = [ HydrusMessageHandling.Message( conversation_key, contact_from, [ contact_to ], subject, body, timestamp, files = files, private_key = private_key ) for contact_to in contacts_to ]
        
        return messages
        
    
    def _InboxConversation( self, c, conversation_key ):
        
        conversation_id = self._GetMessageId( c, conversation_key )
        
        inserts = c.execute( 'SELECT message_id FROM messages WHERE conversation_id = ?;', ( conversation_id, ) ).fetchall()
        
        c.executemany( 'INSERT OR IGNORE INTO message_inbox ( message_id ) VALUES ( ? );', inserts )
        
        self.pub( 'inbox_conversation_data', conversation_key )
        self.pub( 'inbox_conversation_gui', conversation_key )
        
        self._DoStatusNumInbox( c )
        
    
    def _UpdateContacts( self, c, edit_log ):
        
        for ( action, details ) in edit_log:
            
            if action == 'add':
                
                contact = details
                
                self._AddContact( c, contact )
                
            elif action == 'delete':
                
                name = details
                
                result = c.execute( 'SELECT 1 FROM contacts WHERE name = ? AND NOT EXISTS ( SELECT 1 FROM message_destination_map WHERE contact_id_to = contact_id ) AND NOT EXISTS ( SELECT 1 FROM messages WHERE contact_id_from = contact_id );', ( name, ) ).fetchone()
                
                if result is not None: c.execute( 'DELETE FROM contacts WHERE name = ?;', ( name, ) )
                
            elif action == 'edit':
                
                ( old_name, contact ) = details
                
                try:
                    
                    contact_id = self._GetContactId( c, old_name )
                    
                    ( public_key, name, host, port ) = contact.GetInfo()
                    
                    contact_key = contact.GetContactKey()
                    
                    if public_key is not None: contact_key = sqlite3.Binary( contact_key )
                    
                    c.execute( 'UPDATE contacts SET contact_key = ?, public_key = ?, name = ?, host = ?, port = ? WHERE contact_id = ?;', ( contact_key, public_key, name, host, port, contact_id ) )
                    
                except: pass
                
            
        
        self.pub( 'notify_new_contacts' )
        
    
    def _UpdateMessageStatuses( self, c, message_key, status_updates ):
        
        message_id = self._GetMessageId( c, message_key )
        
        updates = []
        
        for ( contact_key, status ) in status_updates:
            
            contact_id = self._GetContactId( c, contact_key )
            status_id = self._GetStatusId( c, status )
            
            updates.append( ( contact_id, status_id ) )
            
        
        c.executemany( 'UPDATE message_destination_map SET status_id = ? WHERE contact_id_to = ? AND message_id = ?;', [ ( status_id, contact_id, message_id ) for ( contact_id, status_id ) in updates ] )
        
        self.pub( 'message_statuses_data', message_key, status_updates )
        self.pub( 'message_statuses_gui', message_key, status_updates )
        self.pub( 'notify_check_messages' )
        
    
class RatingDB():
    
    def _GetRatingsMediaResult( self, c, service_identifier, min, max ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        half_point = ( min + max ) / 2
        
        tighter_min = ( min + half_point ) / 2
        tighter_max = ( max + half_point ) / 2
        
        # I know this is horrible, ordering by random, but I can't think of a better way to do it right now
        result = c.execute( 'SELECT hash_id FROM local_ratings, files_info USING ( hash_id ) WHERE local_ratings.service_id = ? AND files_info.service_id = ? AND rating BETWEEN ? AND ? ORDER BY RANDOM() LIMIT 1;', ( service_id, self._local_file_service_id, tighter_min, tighter_max ) ).fetchone()
        
        if result is None: result = c.execute( 'SELECT hash_id FROM local_ratings, files_info USING ( hash_id ) WHERE local_ratings.service_id = ? AND files_info.service_id = ? AND rating BETWEEN ? AND ? ORDER BY RANDOM() LIMIT 1;', ( service_id, self._local_file_service_id, min, max ) ).fetchone()
        
        if result is None: return None
        else:
            
            ( hash_id, ) = result
            
            search_context = CC.FileSearchContext()
            
            ( media_result, ) = self._GetMediaResults( c, search_context, set( ( hash_id, ) ) )
            
            return media_result
            
        
    
    def _GetRatingsFilter( self, c, service_identifier, hashes ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        hash_ids = self._GetHashIds( c, hashes )
        
        empty_rating = lambda: ( 0.0, 1.0 )
        
        ratings_filter = collections.defaultdict( empty_rating )
        
        ratings_filter.update( ( ( hash, ( min, max ) ) for ( hash, min, max ) in c.execute( 'SELECT hash, min, max FROM ratings_filter, hashes USING ( hash_id ) WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ) )
        
        return ratings_filter
        
    
    # leave this until I am more sure of how it'll work remotely
    # pending is involved here too
    def _UpdateRemoteRatings( self, c, service_identfier, ratings ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        hashes = [ hash for ( hash, count, rating ) in ratings ]
        
        hash_ids = self._GetHashIds( c, hashes )
        
        c.execute( 'DELETE FROM ratings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
        
        c.executemany( 'INSERT INTO ratings ( service_id, hash_id, count, rating, score ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, self._GetHashId( c, hash ), count, rating, HC.CalculateScoreFromRating( count, rating ) ) for ( hash, count, rating ) in ratings if count > 0 ] )
        
        # these need count and score in
        #self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_RATING_REMOTE, service_identifier, ( hash, ), rating ) for ( hash, rating ) in ratings ] )
        #self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_RATING_REMOTE, service_identifier, ( hash, ), rating ) for ( hash, rating ) in ratings ] )
        
    
class TagDB():
    
    def _GenerateTagIdsEfficiently( self, c, tags ):
        
        namespaced_tags = [ tag.split( ':', 1 ) for tag in tags if ':' in tag ]
        
        namespaces = [ namespace for ( namespace, tag ) in namespaced_tags ]
        
        tags = [ tag for tag in tags if ':' not in tag ] + [ tag for ( namespace, tag ) in namespaced_tags ]
        
        namespaces_not_in_db = set( namespaces )
        
        for i in range( 0, len( namespaces ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            namespaces_subset = namespaces[ i : i + 250 ]
            
            namespaces_not_in_db.difference_update( [ namespace for ( namespace, ) in c.execute( 'SELECT namespace FROM namespaces WHERE namespace IN (' + ','.join( '?' * len( namespaces_subset ) ) + ');', [ namespace for namespace in namespaces_subset ] ) ] )
            
        
        if len( namespaces_not_in_db ) > 0: c.executemany( 'INSERT INTO namespaces( namespace ) VALUES( ? );', [ ( namespace, ) for namespace in namespaces_not_in_db ] )
        
        tags_not_in_db = set( tags )
        
        for i in range( 0, len( tags ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            tags_subset = tags[ i : i + 250 ]
            
            tags_not_in_db.difference_update( [ tag for ( tag, ) in c.execute( 'SELECT tag FROM tags WHERE tag IN (' + ','.join( '?' * len( tags_subset ) ) + ');', [ tag for tag in tags_subset ] ) ] )
            
        
        if len( tags_not_in_db ) > 0: c.executemany( 'INSERT INTO tags( tag ) VALUES( ? );', [ ( tag, ) for tag in tags_not_in_db ] )
        
    
    def _GetNamespaceTag( self, c, namespace_id, tag_id ):
        
        result = c.execute( 'SELECT tag FROM tags WHERE tag_id = ?;', ( tag_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Tag error in database' )
        
        ( tag, ) = result
        
        if namespace_id == 1: return tag
        else:
            
            result = c.execute( 'SELECT namespace FROM namespaces WHERE namespace_id = ?;', ( namespace_id, ) ).fetchone()
            
            if result is None: raise Exception( 'Namespace error in database' )
            
            ( namespace, ) = result
            
            return namespace + ':' + tag
            
        
    
    def _GetNamespaceIdTagId( self, c, tag ):
        
        tag = HC.CleanTag( tag )
        
        if ':' in tag:
            
            ( namespace, tag ) = tag.split( ':', 1 )
            
            result = c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
            
            if result is None:
                
                c.execute( 'INSERT INTO namespaces ( namespace ) VALUES ( ? );', ( namespace, ) )
                
                namespace_id = c.lastrowid
                
            else: ( namespace_id, ) = result
            
        else: namespace_id = 1
        
        result = c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO tags ( tag ) VALUES ( ? );', ( tag, ) )
            
            tag_id = c.lastrowid
            
        else: ( tag_id, ) = result
        
        result = c.execute( 'SELECT 1 FROM existing_tags WHERE namespace_id = ? AND tag_id = ?;', ( namespace_id, tag_id ) ).fetchone()
        
        if result is None: c.execute( 'INSERT INTO existing_tags ( namespace_id, tag_id ) VALUES ( ?, ? );', ( namespace_id, tag_id ) )
        
        return ( namespace_id, tag_id )
        
    
class ServiceDB( FileDB, MessageDB, TagDB, RatingDB ):
    
    def _AddDownloads( self, c, service_identifier, hashes ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        hash_ids = self._GetHashIds( c, hashes )
        
        c.executemany( 'INSERT OR IGNORE INTO file_transfers ( service_id_from, service_id_to, hash_id ) VALUES ( ?, ?, ? );', [ ( service_id, self._local_file_service_id, hash_id ) for hash_id in hash_ids ] )
        
        self.pub( 'notify_new_downloads' )
        self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_PENDING, CC.LOCAL_FILE_SERVICE_IDENTIFIER, hashes ) ] )
        self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_PENDING, CC.LOCAL_FILE_SERVICE_IDENTIFIER, hashes ) ] )
        
    
    def _AddFiles( self, c, files_info_rows ):
        
        # service_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words
        
        c.executemany( 'INSERT OR IGNORE INTO files_info VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ? );', files_info_rows )
        
        service_ids_to_rows = HC.BuildKeyToListDict( [ ( row[ 0 ], row[ 1: ] ) for row in files_info_rows ] )
        
        for ( service_id, rows ) in service_ids_to_rows.items():
            
            hash_ids = [ row[ 0 ] for row in rows ]
            
            splayed_hash_ids = HC.SplayListForDB( hash_ids )
            
            c.execute( 'DELETE FROM deleted_files WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
            
            num_deleted_files_revoked = c.rowcount
            
            c.execute( 'DELETE FROM file_transfers WHERE service_id_to = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
            
            total_size = sum( [ row[ 1 ] for row in rows ] )
            num_files = len( rows )
            num_thumbnails = len( [ 1 for row in rows if row[ 2 ] in HC.MIMES_WITH_THUMBNAILS ] )
            
            service_info_updates = []
            
            service_info_updates.append( ( total_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( num_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( num_thumbnails, service_id, HC.SERVICE_INFO_NUM_THUMBNAILS ) )
            service_info_updates.append( ( -num_deleted_files_revoked, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
            
            c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
            c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type IN ' + HC.SplayListForDB( ( HC.SERVICE_INFO_NUM_INBOX, HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL ) ) + ';', ( service_id, ) )
            
            self._UpdateAutocompleteTagCacheFromFiles( c, service_id, hash_ids, 1 )
            
        
    
    def _AddFileRepositoryUpdate( self, c, service_id, update ):
        
        # new
        
        files = update.GetFiles()
        
        new_hashes = [ hash for ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) in files ]
        
        new_hash_ids = self._GetHashIds( c, new_hashes )
        
        files_info_rows = [ ( service_id, self._GetHashId( c, hash ), size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) in files ]
        
        self._AddFiles( c, files_info_rows )
        
        # deleted
        
        deleted_hashes = update.GetDeletedHashes()
        
        deleted_hash_ids = self._GetHashIds( c, deleted_hashes )
        
        self._DeleteFiles( c, service_id, deleted_hash_ids )
        
        # news
        
        c.executemany( 'INSERT OR IGNORE INTO news VALUES ( ?, ?, ? );', [ ( service_id, post, timestamp ) for ( post, timestamp ) in update.GetNews() ] )
        
        # done
        
        c.execute( 'UPDATE repositories SET first_begin = ? WHERE service_id = ? AND first_begin = ?;', ( update.GetNextBegin(), service_id, 0 ) )
        
        c.execute( 'UPDATE repositories SET next_begin = ? WHERE service_id = ?;', ( update.GetNextBegin(), service_id ) )
        
        deleted_hashes = [ hash for hash in update.GetDeletedHashes() ] # to proceess generator
        
        service_identifier = self._GetServiceIdentifier( c, service_id )
        
        if len( new_hashes ) > 0:
            
            self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, new_hashes ) ] )
            self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, new_hashes ) ] )
            
        
        if len( deleted_hashes ) > 0:
            
            self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, deleted_hashes ) ] )
            self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, deleted_hashes ) ] )
            
        
        if len( new_hashes ) > 0 or len( deleted_hashes ) > 0: self.pub( 'notify_new_thumbnails' )
        
    
    def _AddHydrusSession( self, c, service_identifier, session_key, expiry ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        c.execute( 'REPLACE INTO hydrus_sessions ( service_id, session_key, expiry ) VALUES ( ?, ?, ? );', ( service_id, sqlite3.Binary( session_key ), expiry ) )
        
    
    def _AddService( self, c, service_identifier, credentials, extra_info ):
        
        service_key = service_identifier.GetServiceKey()
        service_type = service_identifier.GetType()
        service_name = service_identifier.GetName()
        
        c.execute( 'INSERT INTO services ( service_key, type, name ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, service_name ) )
        
        service_id = c.lastrowid
        
        if service_type in HC.REMOTE_SERVICES:
            
            ( host, port ) = credentials.GetAddress()
            
            c.execute( 'INSERT OR IGNORE INTO addresses ( service_id, host, port, last_error ) VALUES ( ?, ?, ?, ? );', ( service_id, host, port, 0 ) )
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                access_key = credentials.GetAccessKey()
                
                account = CC.GetUnknownAccount()
                
                account.MakeStale()
                
                c.execute( 'INSERT OR IGNORE INTO accounts ( service_id, access_key, account ) VALUES ( ?, ?, ? );', ( service_id, sqlite3.Binary( access_key ), account ) )
                
                if service_type in HC.REPOSITORIES:
                    
                    c.execute( 'INSERT OR IGNORE INTO repositories ( service_id, first_begin, next_begin ) VALUES ( ?, ?, ? );', ( service_id, 0, 0 ) )
                    
                    if service_type == HC.TAG_REPOSITORY: c.execute( 'INSERT INTO tag_service_precedence ( service_id, precedence ) SELECT ?, CASE WHEN MAX( precedence ) NOT NULL THEN MAX( precedence ) + 1 ELSE 0 END FROM tag_service_precedence;', ( service_id, ) )
                    elif service_type == HC.RATING_LIKE_REPOSITORY:
                        
                        ( like, dislike ) = extra_info
                        
                        c.execute( 'INSERT INTO ratings_like ( service_id, like, dislike ) VALUES ( ?, ?, ? );', ( service_id, like, dislike ) )
                        
                    elif service_type == HC.RATING_LIKE_REPOSITORY:
                        
                        ( lower, upper ) = extra_info
                        
                        c.execute( 'INSERT INTO ratings_numerical ( service_id, lower, upper ) VALUES ( ?, ?, ? );', ( service_id, lower, upper ) )
                        
                    
                elif service_type == HC.MESSAGE_DEPOT:
                    
                    ( identity_name, check_period, private_key, receive_anon ) = extra_info
                    
                    public_key = HydrusMessageHandling.GetPublicKey( private_key )
                    
                    contact_key = hashlib.sha256( public_key ).digest()
                    
                    try:
                        
                        contact_id = self._GetContactId( c, contact_key )
                        
                        c.execute( 'UPDATE contacts SET contact_key = ?, public_key = ? WHERE contact_id = ?;', ( None, None, contact_id ) )
                        
                    except:
                        
                        c.execute( 'INSERT OR IGNORE INTO contacts ( contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ? );', ( None, None, identity_name, host, port ) )
                        
                        contact_id = c.lastrowid
                        
                    
                    c.execute( 'INSERT OR IGNORE INTO message_depots ( service_id, contact_id, last_check, check_period, private_key, receive_anon ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, contact_id, 0, check_period, private_key, receive_anon ) )
                    
                
            
        else:
            
            if service_type == HC.LOCAL_RATING_LIKE:
                
                ( like, dislike ) = extra_info
                
                c.execute( 'INSERT INTO ratings_like ( service_id, like, dislike ) VALUES ( ?, ?, ? );', ( service_id, like, dislike ) )
                
            elif HC.LOCAL_RATING_NUMERICAL:
                
                ( lower, upper ) = extra_info
                
                c.execute( 'INSERT INTO ratings_numerical ( service_id, lower, upper ) VALUES ( ?, ?, ? );', ( service_id, lower, upper ) )
                
            
        
    
    def _AddServiceUpdates( self, c, update_log ):
        
        do_new_permissions = False
        
        requests_made = []
        
        for service_update in update_log:
            
            action = service_update.GetAction()
            
            service_identifier = service_update.GetServiceIdentifier()
            
            try:
                
                service_id = self._GetServiceId( c, service_identifier )
                
                if action == CC.SERVICE_UPDATE_ACCOUNT:
                    
                    account = service_update.GetInfo()
                    
                    c.execute( 'UPDATE accounts SET account = ? WHERE service_id = ?;', ( account, service_id ) )
                    c.execute( 'UPDATE addresses SET last_error = ? WHERE service_id = ?;', ( 0, service_id ) )
                    
                    do_new_permissions = True
                    
                elif action == CC.SERVICE_UPDATE_ERROR: c.execute( 'UPDATE addresses SET last_error = ? WHERE service_id = ?;', ( int( time.time() ), service_id ) )
                elif action == CC.SERVICE_UPDATE_REQUEST_MADE: requests_made.append( ( service_id, service_update.GetInfo() ) )
                
            except: pass
            
            self.pub( 'service_update_data', service_update )
            self.pub( 'service_update_gui', service_update )
            
        
        for ( service_id, nums_bytes ) in HC.BuildKeyToListDict( requests_made ).items():
            
            ( account, ) = c.execute( 'SELECT account FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            for num_bytes in nums_bytes: account.RequestMade( num_bytes )
            
            c.execute( 'UPDATE accounts SET account = ? WHERE service_id = ?;', ( account, service_id ) )
            
        
        if do_new_permissions: self.pub( 'notify_new_permissions' )
        
    
    def _AddTagRepositoryUpdate( self, c, service_id, update ):
        
        # new
        
        mappings = update.GetMappings()
        
        mappings_ids = []
        
        for ( tag, hashes ) in mappings:
            
            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
            
            hash_ids = self._GetHashIds( c, hashes )
            
            mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
            
        
        # deleted
        
        deleted_mappings = update.GetDeletedMappings()
        
        deleted_mappings_ids = []
        
        for ( tag, hashes ) in update.GetDeletedMappings():
            
            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
            
            hash_ids = self._GetHashIds( c, hashes )
            
            deleted_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
            
        
        self._UpdateMappings( c, service_id, mappings_ids, deleted_mappings_ids )
        
        # news
        
        c.executemany( 'INSERT OR IGNORE INTO news VALUES ( ?, ?, ? );', [ ( service_id, post, timestamp ) for ( post, timestamp ) in update.GetNews() ] )
        
        # done
        
        if update.GetEnd() is not None:
            
            c.execute( 'UPDATE repositories SET first_begin = ? WHERE service_id = ? AND first_begin = ?;', ( update.GetNextBegin(), service_id, 0 ) )
            
            c.execute( 'UPDATE repositories SET next_begin = ? WHERE service_id = ?;', ( update.GetNextBegin(), service_id ) )
            
        
        service_identifier = self._GetServiceIdentifier( c, service_id )
        
        mappings = [ mapping for mapping in update.GetMappings() ] # to clear generator
        
        deleted_mappings = [ deleted_mapping for deleted_mapping in update.GetDeletedMappings() ] # to clear generator
        
        if len( mappings ) > 0:
            self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, hashes, info = tag ) for ( tag, hashes ) in mappings ] )
            self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, hashes, info = tag ) for ( tag, hashes ) in mappings ] )
        if len( deleted_mappings ) > 0:
            self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, hashes, info = tag ) for ( tag, hashes ) in deleted_mappings ] )
            self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, hashes, info = tag ) for ( tag, hashes ) in deleted_mappings ] )
        
    
    def _AddUpdate( self, c, service_identifier, update ):
        
        service_type = service_identifier.GetType()
        
        service_id = self._GetServiceId( c, service_identifier )
        
        if service_type == HC.FILE_REPOSITORY: self._AddFileRepositoryUpdate( c, service_id, update )
        elif service_type == HC.TAG_REPOSITORY: self._AddTagRepositoryUpdate( c, service_id, update )
        
    
    def _AddUploads( self, c, service_identifier, hashes ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service = self._GetService( c, service_id )
        
        hash_ids = set( self._GetHashIds( c, hashes ) )
        
        if not service.GetAccount().HasPermission( HC.RESOLVE_PETITIONS ):
            
            deleted_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_files WHERE service_id = ?;', ( service_id, ) ) ]
            
            hash_ids.difference_update( deleted_hash_ids )
            
        
        existing_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( service_id, ) ) ]
        
        hash_ids.difference_update( existing_hash_ids )
        
        c.executemany( 'INSERT OR IGNORE INTO file_transfers ( service_id_from, service_id_to, hash_id ) VALUES ( ?, ?, ? );', [ ( self._local_file_service_id, service_id, hash_id ) for hash_id in hash_ids ] )
        
        self.pub( 'notify_new_pending' )
        self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_PENDING, service_identifier, self._GetHashes( c, hash_ids ) ) ] )
        self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_PENDING, service_identifier, self._GetHashes( c, hash_ids ) ) ] )
        
    
    def _ArchiveFiles( self, c, hash_ids ):
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_inbox WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ) ]
        
        if len( valid_hash_ids ) > 0:
            
            splayed_hash_ids = HC.SplayListForDB( valid_hash_ids )
            
            c.execute( 'DELETE FROM file_inbox WHERE hash_id IN ' + splayed_hash_ids + ';' )
            
            updates = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id;' ).fetchall()
            
            c.executemany( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in updates ] )
            
        
    
    def _DeleteFiles( self, c, service_id, hash_ids ):
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        if service_id == self._local_file_service_id: c.execute( 'DELETE FROM file_inbox WHERE hash_id IN ' + splayed_hash_ids + ';' )
        
        info = c.execute( 'SELECT size, mime FROM files_info WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) ).fetchall()
        
        total_size = sum( [ row[ 0 ] for row in info ] )
        num_files = len( info )
        num_thumbnails = len( [ 1 for row in info if row[ 1 ] in HC.MIMES_WITH_THUMBNAILS ] )
        
        service_info_updates = []
        
        service_info_updates.append( ( total_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
        service_info_updates.append( ( num_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
        service_info_updates.append( ( num_thumbnails, service_id, HC.SERVICE_INFO_NUM_THUMBNAILS ) )
        service_info_updates.append( ( -num_files, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) ) # - because we want to increment in the following query
        
        c.executemany( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
        c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type IN ' + HC.SplayListForDB( ( HC.SERVICE_INFO_NUM_INBOX, HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL ) ) + ';', ( service_id, ) )
        
        c.execute( 'DELETE FROM files_info WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
        
        invalid_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM deleted_files WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) ) }
        
        actual_hash_ids_i_can_delete = set( hash_ids )
        
        actual_hash_ids_i_can_delete.difference_update( invalid_hash_ids )
        
        c.executemany( 'INSERT OR IGNORE INTO deleted_files ( service_id, hash_id ) VALUES ( ?, ? );', [ ( service_id, hash_id ) for hash_id in actual_hash_ids_i_can_delete ] )
        
        self._UpdateAutocompleteTagCacheFromFiles( c, service_id, actual_hash_ids_i_can_delete, -1 )
        
        self.pub( 'notify_new_pending' )
        
    
    def _DeleteHydrusSessionKey( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        c.execute( 'DELETE FROM hydrus_sessions WHERE service_id = ?;', ( service_id, ) )
        
    
    def _DeleteOrphans( self, c ):
        
        # careful of the .encode( 'hex' ) business here!
        
        # files
        
        deleted_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_files WHERE service_id = ?;', ( self._local_file_service_id, ) ) }
        
        pending_upload_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id_from = ?;', ( self._local_file_service_id, ) ) }
        
        message_attachment_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM message_attachments;' ) }
        
        deletee_hash_ids = ( deleted_hash_ids - pending_upload_hash_ids ) - message_attachment_hash_ids
        
        deletee_hashes = set( self._GetHashes( c, deletee_hash_ids ) )
        
        cached_filenames = dircache.listdir( HC.CLIENT_FILES_DIR )
        
        local_files_hashes = set()
        
        for filename in cached_filenames:
            
            try: local_files_hashes.add( filename.decode( 'hex' ) ) # this try ... except is for weird files that might have got into the directory by accident
            except: pass
            
        
        for hash in local_files_hashes & deletee_hashes: os.remove( HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' ) )
        
        # perceptual_hashes and thumbs
        
        perceptual_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM perceptual_hashes;' ) }
        
        hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info;' ) }
        
        perceptual_deletees = perceptual_hash_ids - hash_ids
        
        c.execute( 'DELETE FROM perceptual_hashes WHERE hash_id IN ' + HC.SplayListForDB( perceptual_deletees ) + ';' )
        
        all_thumbnail_filenames = dircache.listdir( HC.CLIENT_THUMBNAILS_DIR )
        
        thumbnails_i_have = set()
        
        for filename in all_thumbnail_filenames:
            
            if not filename.endswith( '_resized' ):
                
                try: thumbnails_i_have.add( filename.decode( 'hex' ) ) # this try ... except is for weird files that might have got into the directory by accident
                except: pass
                
            
        
        hashes = set( self._GetHashes( c, hash_ids ) )
        
        thumbnail_deletees = thumbnails_i_have - hashes
        
        for hash in thumbnail_deletees:
            
            path = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
            resized_path = path + '_resized'
            
            os.remove( path )
            
            if os.path.exists( resized_path ): os.remove( resized_path )
            
        
        c.execute( 'REPLACE INTO shutdown_timestamps ( shutdown_type, timestamp ) VALUES ( ?, ? );', ( CC.SHUTDOWN_TIMESTAMP_DELETE_ORPHANS, int( time.time() ) ) )
        
    
    def _DeletePending( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        if service_identifier.GetType() == HC.TAG_REPOSITORY:
            
            c.execute( 'DELETE FROM pending_mappings WHERE service_id = ?;', ( service_id, ) )
            
            c.execute( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id = ?;', ( service_id, ) )
            c.execute( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL;' )
            
            c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ?;', ( service_id, ) )
            
            self._RecalcActivePendingMappings( c )
            
        elif service_identifier.GetType() == HC.FILE_REPOSITORY:
            
            c.execute( 'DELETE FROM file_transfers WHERE service_id_to = ?;', ( service_id, ) )
            c.execute( 'DELETE FROM file_petitions WHERE service_id = ?;', ( service_id, ) )
            
        
        self.pub( 'notify_new_pending' )
        self.pub( 'service_update_db', CC.ServiceUpdate( CC.SERVICE_UPDATE_DELETE_PENDING, service_identifier ) )
        
    
    def _DoFileQuery( self, c, query_key, search_context ):
        
        # setting up
        
        system_predicates = search_context.GetSystemPredicates()
        
        file_service_identifier = search_context.GetFileServiceIdentifier()
        tag_service_identifier = search_context.GetTagServiceIdentifier()
        
        file_service_id = self._GetServiceId( c, file_service_identifier )
        tag_service_id = self._GetServiceId( c, tag_service_identifier )
        
        file_service_type = file_service_identifier.GetType()
        tag_service_type = tag_service_identifier.GetType()
        
        tags_to_include = search_context.GetTagsToInclude()
        tags_to_exclude = search_context.GetTagsToExclude()
        
        namespaces_to_include = search_context.GetNamespacesToInclude()
        namespaces_to_exclude = search_context.GetNamespacesToExclude()
        
        include_current_tags = search_context.IncludeCurrentTags()
        include_pending_tags = search_context.IncludePendingTags()
        
        sql_predicates = [ 'service_id = ' + str( file_service_id ) ]
        
        ( hash, min_size, size, max_size, mimes, min_timestamp, max_timestamp, min_width, width, max_width, min_height, height, max_height, min_num_words, num_words, max_num_words, min_duration, duration, max_duration ) = system_predicates.GetInfo()
        
        if min_size is not None: sql_predicates.append( 'size > ' + str( min_size ) )
        if size is not None: sql_predicates.append( 'size = ' + str( size ) )
        if max_size is not None: sql_predicates.append( 'size < ' + str( max_size ) )
        
        if mimes is not None:
            
            if len( mimes ) == 1:
                
                ( mime, ) = mimes
                
                sql_predicates.append( 'mime = ' + str( mime ) )
                
            else: sql_predicates.append( 'mime IN ' + HC.SplayListForDB( mimes ) )
            
        
        if min_timestamp is not None: sql_predicates.append( 'timestamp >= ' + str( min_timestamp ) )
        if max_timestamp is not None: sql_predicates.append( 'timestamp <= ' + str( max_timestamp ) )
        
        if min_width is not None: sql_predicates.append( 'width > ' + str( min_width ) )
        if width is not None: sql_predicates.append( 'width = ' + str( width ) )
        if max_width is not None: sql_predicates.append( 'width < ' + str( max_width ) )
        
        if min_height is not None: sql_predicates.append( 'height > ' + str( min_height ) )
        if height is not None: sql_predicates.append( 'height = ' + str( height ) )
        if max_height is not None: sql_predicates.append( 'height < ' + str( max_height ) )
        
        if min_num_words is not None: sql_predicates.append( 'num_words > ' + str( min_num_words ) )
        if num_words is not None: sql_predicates.append( 'num_words = ' + str( num_words ) )
        if max_num_words is not None: sql_predicates.append( 'num_words < ' + str( max_num_words ) )
        
        if min_duration is not None: sql_predicates.append( 'duration > ' + str( min_duration ) )
        if duration is not None:
            
            if duration == 0: sql_predicates.append( '( duration IS NULL OR duration = 0 )' )
            else: sql_predicates.append( 'duration = ' + str( duration ) )
            
        if max_duration is not None: sql_predicates.append( 'duration < ' + str( max_duration ) )
        
        if len( tags_to_include ) > 0 or len( namespaces_to_include ) > 0:
            
            query_hash_ids = None
            
            if len( tags_to_include ) > 0: query_hash_ids = HC.IntelligentMassIntersect( ( self._GetHashIdsFromTag( c, file_service_identifier, tag_service_identifier, tag, include_current_tags, include_pending_tags ) for tag in tags_to_include ) )
            
            if len( namespaces_to_include ) > 0:
                
                namespace_query_hash_ids = HC.IntelligentMassIntersect( ( self._GetHashIdsFromNamespace( c, file_service_identifier, tag_service_identifier, namespace, include_current_tags, include_pending_tags ) for namespace in namespaces_to_include ) )
                
                if query_hash_ids is None: query_hash_ids = namespace_query_hash_ids
                else: query_hash_ids.intersection_update( namespace_query_hash_ids )
                
            
            if len( sql_predicates ) > 1: query_hash_ids.intersection_update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE ' + ' AND '.join( sql_predicates ) + ';' ) ] )
            
        else:
            
            if file_service_identifier != CC.NULL_SERVICE_IDENTIFIER: query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE ' + ' AND '.join( sql_predicates ) + ';' ) }
            elif tag_service_identifier != CC.NULL_SERVICE_IDENTIFIER: query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ?;', ( tag_service_id, ) ) }
            else: query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings UNION SELECT hash_id FROM files_info;' ) }
            
        
        ( num_tags_zero, num_tags_nonzero ) = system_predicates.GetNumTagsInfo()
        
        if num_tags_zero:
            
            zero_tag_hash_ids = set()
            
            if include_current_tags:
                
                if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER: current_zero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM active_mappings;' ) }
                else: current_zero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ?;', ( tag_service_id, ) ) }
                
                zero_tag_hash_ids = current_zero_tag_hash_ids
                
            
            if include_pending_tags:
                
                if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER: pending_zero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM active_pending_mappings;' ) }
                else: pending_zero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM pending_mappings WHERE service_id = ?;', ( tag_service_id, ) ) }
                
                zero_tag_hash_ids.update( pending_zero_tag_hash_ids )
                
            
            query_hash_ids.difference_update( zero_tag_hash_ids )
            
        
        if num_tags_nonzero:
            
            nonzero_tag_hash_ids = set()
            
            if include_current_tags:
                
                if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER: current_nonzero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM active_mappings;' ) }
                else: current_nonzero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ?;', ( tag_service_id, ) ) }
                
                nonzero_tag_hash_ids = current_nonzero_tag_hash_ids
                
            
            if include_pending_tags:
                
                if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER: pending_nonzero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM active_pending_mappings;' ) }
                else: pending_nonzero_tag_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM pending_mappings WHERE service_id = ?;', ( tag_service_id, ) ) }
                
                nonzero_tag_hash_ids.update( pending_nonzero_tag_hash_ids )
                
            
            query_hash_ids.intersection_update( nonzero_tag_hash_ids )
            
        
        if hash is not None:
            
            hash_id = self._GetHashId( c, hash )
            
            query_hash_ids.intersection_update( { hash_id } )
            
        
        exclude_query_hash_ids = HC.IntelligentMassUnion( [ self._GetHashIdsFromTag( c, file_service_identifier, tag_service_identifier, tag, include_current_tags, include_pending_tags ) for tag in tags_to_exclude ] )
        
        exclude_query_hash_ids.update( HC.IntelligentMassUnion( [ self._GetHashIdsFromNamespace( c, file_service_identifier, tag_service_identifier, namespace, include_current_tags, include_pending_tags ) for namespace in namespaces_to_exclude ] ) )
        
        if file_service_type == HC.FILE_REPOSITORY and self._options[ 'exclude_deleted_files' ]: exclude_query_hash_ids.update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_files WHERE service_id = ?;', ( self._local_file_service_id, ) ) ] )
        
        query_hash_ids.difference_update( exclude_query_hash_ids )
        
        for service_identifier in system_predicates.GetFileRepositoriesToExclude():
            
            service_id = self._GetServiceId( c, service_identifier )
            
            query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for ( service_identifier, operator, value ) in system_predicates.GetRatingsPredicates():
            
            service_id = self._GetServiceId( c, service_identifier )
            
            if value == 'rated': query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ] )
            elif value == 'not rated': query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ] )
            elif value == 'uncertain': query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM ratings_filter WHERE service_id = ?;', ( service_id, ) ) ] )
            else:
                
                if operator == u'\u2248': predicate = str( value * 0.95 ) + ' < rating AND rating < ' + str( value * 1.05 )
                else: predicate = 'rating ' + operator + ' ' + str( value )
                
                query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ? AND ' + predicate + ';', ( service_id, ) ) ] )
                
            
        
        media_results = self._GetMediaResults( c, search_context, query_hash_ids )
        
        self.pub( 'file_query_done', query_key, media_results )
        
    
    def _FattenAutocompleteCache( self, c ):
        
        tag_service_identifiers = self._GetServiceIdentifiers( c, ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ) )
        file_service_identifiers = self._GetServiceIdentifiers( c, ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) )
        
        tag_service_identifiers.add( CC.NULL_SERVICE_IDENTIFIER )
        file_service_identifiers.add( CC.NULL_SERVICE_IDENTIFIER )
        
        for ( tag_service_identifier, file_service_identifier ) in itertools.product( tag_service_identifiers, file_service_identifiers ): self._GetAutocompleteTags( c, tag_service_identifier = tag_service_identifier, file_service_identifier = file_service_identifier )
        
        c.execute( 'REPLACE INTO shutdown_timestamps ( shutdown_type, timestamp ) VALUES ( ?, ? );', ( CC.SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE, int( time.time() ) ) )
        
    
    def _Get4chanPass( self, c ):
        
        result = c.execute( 'SELECT token, pin, timeout FROM fourchan_pass;' ).fetchone()
        
        if result is None: return ( '', '', 0 )
        else: return result
        
    
    def _GetAllDownloads( self, c ):
        
        id_result = HC.BuildKeyToListDict( c.execute( 'SELECT service_id_from, hash_id FROM file_transfers WHERE service_id_to = ?;', ( self._local_file_service_id, ) ) )
        
        all_downloads = { self._GetServiceIdentifier( c, service_id ) : self._GetHashes( c, hash_ids ) for ( service_id, hash_ids ) in id_result.items() }
        
        return all_downloads
        
    
    def _GetAutocompleteTags( self, c, tag_service_identifier = CC.NULL_SERVICE_IDENTIFIER, file_service_identifier = CC.NULL_SERVICE_IDENTIFIER, half_complete_tag = '', include_current = True, include_pending = True ):
        
        if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
            
            tag_service_id = None
            
            if file_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
                
                file_service_id = None
                
                current_tables_phrase = 'active_mappings WHERE '
                pending_tables_phrase = 'active_pending_mappings WHERE '
                
            else:
                
                file_service_id = self._GetServiceId( c, file_service_identifier )
                
                current_tables_phrase = 'active_mappings, files_info USING ( hash_id ) WHERE service_id = ' + str( file_service_id ) + ' AND '
                pending_tables_phrase = 'active_pending_mappings, files_info USING ( hash_id ) WHERE service_id = ' + str( file_service_id ) + ' AND '
                
            
        else:
            
            tag_service_id = self._GetServiceId( c, tag_service_identifier )
            
            if file_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
                
                file_service_id = None
                
                current_tables_phrase = 'mappings WHERE service_id = ' + str( tag_service_id ) + ' AND '
                pending_tables_phrase = 'pending_mappings WHERE service_id = ' + str( tag_service_id ) + ' AND '
                
            else:
                
                file_service_id = self._GetServiceId( c, file_service_identifier )
                
                current_tables_phrase = 'mappings, files_info USING ( hash_id ) WHERE mappings.service_id = ' + str( tag_service_id ) + ' AND files_info.service_id = ' + str( file_service_id ) + ' AND '
                pending_tables_phrase = 'pending_mappings, files_info USING ( hash_id ) WHERE pending_mappings.service_id = ' + str( tag_service_id ) + ' AND files_info.service_id = ' + str( file_service_id ) + ' AND '
                
            
        
        if tag_service_id is None: autocomplete_services_predicates_phrase = 'tag_service_id IS NULL AND '
        else: autocomplete_services_predicates_phrase = 'tag_service_id = ' + str( tag_service_id ) + ' AND '
        
        if file_service_id is None: autocomplete_services_predicates_phrase += 'file_service_id IS NULL AND'
        else: autocomplete_services_predicates_phrase += 'file_service_id = ' + str( file_service_id ) + ' AND'
        
        # precache search
        
        there_was_a_namespace = False
        
        if len( half_complete_tag ) > 0:
            
            if ':' in half_complete_tag:
                
                there_was_a_namespace = True
                
                ( namespace, half_complete_tag ) = half_complete_tag.split( ':', 1 )
                
                if half_complete_tag == '': return CC.AutocompleteMatchesCounted( {} )
                else:
                    
                    result = c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
                    
                    if result is None: return CC.AutocompleteMatchesCounted( {} )
                    else:
                        
                        ( namespace_id, ) = result
                        
                        possible_tag_ids = [ tag_id for ( tag_id, ) in c.execute( 'SELECT tag_id FROM tags WHERE tag LIKE ?;', ( half_complete_tag + '%', ) ) ]
                        
                        predicates_phrase = 'namespace_id = ' + str( namespace_id ) + ' AND tag_id IN ' + HC.SplayListForDB( possible_tag_ids )
                        
                    
                
            else:
                
                possible_tag_ids = [ tag_id for ( tag_id, ) in c.execute( 'SELECT tag_id FROM tags WHERE tag LIKE ?;', ( half_complete_tag + '%', ) ) ]
                
                predicates_phrase = 'tag_id IN ' + HC.SplayListForDB( possible_tag_ids )
                
            
        else:
            
            predicates_phrase = '1 = 1'
            
        
        results = { result for result in c.execute( 'SELECT namespace_id, tag_id FROM existing_tags WHERE ' + predicates_phrase + ';' ) }
        
        # fetch what we can from cache
        
        cache_results = []
        
        if len( half_complete_tag ) > 0:
            
            for ( namespace_id, tag_ids ) in HC.BuildKeyToListDict( results ).items(): cache_results.extend( c.execute( 'SELECT namespace_id, tag_id, current_count, pending_count FROM autocomplete_tags_cache WHERE ' + autocomplete_services_predicates_phrase + ' namespace_id = ? AND tag_id IN ' + HC.SplayListForDB( tag_ids ) + ';', ( namespace_id, ) ).fetchall() )
            
        else:
            
            cache_results = c.execute( 'SELECT namespace_id, tag_id, current_count, pending_count FROM autocomplete_tags_cache WHERE ' + autocomplete_services_predicates_phrase + ' 1=1;' ).fetchall()
            
        
        results_hit = { ( namespace_id, tag_id ) for ( namespace_id, tag_id, current_count, pending_count ) in cache_results }
        
        results_missed = results.difference( results_hit )
        
        zero = lambda: 0
        
        for ( namespace_id, tag_ids ) in HC.BuildKeyToListDict( results_missed ).items():
            
            current_counts = collections.defaultdict( zero )
            pending_counts = collections.defaultdict( zero )
            
            current_counts.update( { tag_id : count for ( tag_id, count ) in c.execute( 'SELECT tag_id, COUNT( * ) FROM ' + current_tables_phrase + 'namespace_id = ? AND tag_id IN ' + HC.SplayListForDB( tag_ids ) + ' GROUP BY tag_id;', ( namespace_id, ) ) } )
            pending_counts.update( { tag_id : count for ( tag_id, count ) in c.execute( 'SELECT tag_id, COUNT( * ) FROM ' + pending_tables_phrase + 'namespace_id = ? AND tag_id IN ' + HC.SplayListForDB( tag_ids ) + ' GROUP BY tag_id;', ( namespace_id, ) ) } )
            
            c.executemany( 'INSERT OR IGNORE INTO autocomplete_tags_cache ( file_service_id, tag_service_id, namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( file_service_id, tag_service_id, namespace_id, tag_id, current_counts[ tag_id ], pending_counts[ tag_id ] ) for tag_id in tag_ids ] )
            
            cache_results.extend( [ ( namespace_id, tag_id, current_counts[ tag_id ], pending_counts[ tag_id ] ) for tag_id in tag_ids ] )
            
        
        results = []
        
        if include_current: results += [ ( namespace_id, tag_id, current_count ) for ( namespace_id, tag_id, current_count, pending_count ) in cache_results ]
        if include_pending: results += [ ( namespace_id, tag_id, pending_count ) for ( namespace_id, tag_id, current_count, pending_count ) in cache_results ]
        
        tags_to_count = collections.Counter()
        
        [ tags_to_count.update( { ( namespace_id, tag_id ) : num_tags } ) for ( namespace_id, tag_id, num_tags ) in results ]
        
        if not there_was_a_namespace:
            
            unnamespaced_tag_ids = { tag_id for ( namespace_id, tag_id, num_tags ) in results if namespace_id == 1 }
            
            [ tags_to_count.update( { ( 1, tag_id ) : num_tags } ) for ( namespace_id, tag_id, num_tags ) in results if namespace_id != 1 and tag_id in unnamespaced_tag_ids ]
            
        
        matches = CC.AutocompleteMatchesPredicates( [ HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', self._GetNamespaceTag( c, namespace_id, tag_id ) ), num_tags ) for ( ( namespace_id, tag_id ), num_tags ) in tags_to_count.items() if num_tags > 0 ] )
        
        return matches
        
    
    def _GetFavouriteCustomFilterActions( self, c ): return dict( c.execute( 'SELECT name, actions FROM favourite_custom_filter_actions;' ).fetchall() )
    
    def _GetHashIdsFromNamespace( self, c, file_service_identifier, tag_service_identifier, namespace, include_current_tags, include_pending_tags ):
        
        hash_ids = set()
        
        if file_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
            
            if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
                
                current_tables_phrase = 'active_mappings'
                pending_tables_phrase = 'active_pending_mappings'
                
                current_predicates_phrase = ''
                pending_predicates_phrase = ''
                
            else:
                
                tag_service_id = self._GetServiceId( c, tag_service_identifier )
                
                current_tables_phrase = 'mappings'
                pending_tables_phrase = 'pending_mappings'
                
                current_predicates_phrase = 'service_id = ' + str( tag_service_id ) + ' AND '
                pending_predicates_phrase = 'service_id = ' + str( tag_service_id ) + ' AND '
                
            
        else:
            
            file_service_id = self._GetServiceId( c, file_service_identifier )
            
            if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
                
                current_tables_phrase = '( active_mappings, files_info USING ( hash_id ) )'
                pending_tables_phrase = '( active_pending_mappings, files_info USING ( hash_id ) )'
                
                current_predicates_phrase = 'service_id = ' + str( file_service_id ) + ' AND '
                pending_predicates_phrase = 'service_id = ' + str( file_service_id ) + ' AND '
                
            else:
                
                tag_service_id = self._GetServiceId( c, tag_service_identifier )
                
                # we have to do a crazy join because of the nested joins, which wipe out table-namespaced identifiers like mappings.service_id, replacing them with useless stuff like service_id:1
                
                current_tables_phrase = '( mappings, files_info ON ( mappings.hash_id = files_info.hash_id AND mappings.service_id = ' + str( tag_service_id ) + ' AND files_info.service_id = ' + str( file_service_id ) + ' ) )'
                pending_tables_phrase = '( pending_mappings, files_info ON ( pending_mappings.hash_id = files_info.hash_id AND pending_mappings.service_id = ' + str( tag_service_id ) + ' AND files_info.service_id = ' + str( file_service_id ) + ' ) )'
                
                current_predicates_phrase = ''
                pending_predicates_phrase = ''
                
            
            
        
        if include_current_tags: hash_ids.update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM namespaces, ' + current_tables_phrase + ' USING ( namespace_id ) WHERE ' + current_predicates_phrase + 'namespace = ?;', ( namespace, ) ) ] )
        if include_pending_tags: hash_ids.update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM namespaces, ' + pending_tables_phrase + ' USING ( namespace_id ) WHERE ' + pending_predicates_phrase + 'namespace = ?;', ( namespace, ) ) ] )
        
        return hash_ids
        
    
    def _GetHashIdsFromTag( self, c, file_service_identifier, tag_service_identifier, tag, include_current_tags, include_pending_tags ):
        
        hash_ids = set()
        
        if file_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
            
            if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
                
                current_tables_phrase = 'active_mappings'
                pending_tables_phrase = 'active_pending_mappings'
                
                current_predicates_phrase = ''
                pending_predicates_phrase = ''
                
            else:
                
                tag_service_id = self._GetServiceId( c, tag_service_identifier )
                
                current_tables_phrase = 'mappings'
                pending_tables_phrase = 'pending_mappings'
                
                current_predicates_phrase = 'service_id = ' + str( tag_service_id ) + ' AND '
                pending_predicates_phrase = 'service_id = ' + str( tag_service_id ) + ' AND '
                
            
        else:
            
            file_service_id = self._GetServiceId( c, file_service_identifier )
            
            if tag_service_identifier == CC.NULL_SERVICE_IDENTIFIER:
                
                current_tables_phrase = '( active_mappings, files_info USING ( hash_id ) )'
                pending_tables_phrase = '( active_pending_mappings, files_info USING ( hash_id ) )'
                
                current_predicates_phrase = 'service_id = ' + str( file_service_id ) + ' AND '
                pending_predicates_phrase = 'service_id = ' + str( file_service_id ) + ' AND '
                
            else:
                
                tag_service_id = self._GetServiceId( c, tag_service_identifier )
                
                # we have to do a crazy join because of the nested joins, which wipe out table-namespaced identifiers like mappings.service_id, replacing them with useless stuff like service_id:1
                
                current_tables_phrase = '( mappings, files_info ON ( mappings.hash_id = files_info.hash_id AND mappings.service_id = ' + str( tag_service_id ) + ' AND files_info.service_id = ' + str( file_service_id ) + ' ) )'
                pending_tables_phrase = '( pending_mappings, files_info ON ( pending_mappings.hash_id = files_info.hash_id AND pending_mappings.service_id = ' + str( tag_service_id ) + ' AND files_info.service_id = ' + str( file_service_id ) + ' ) )'
                
                current_predicates_phrase = ''
                pending_predicates_phrase = ''
                
            
            
        
        if ':' in tag:
            
            ( namespace, tag ) = tag.split( ':', 1 )
            
            if include_current_tags: hash_ids.update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM namespaces, ( tags, ' + current_tables_phrase + ' USING ( tag_id ) ) USING ( namespace_id ) WHERE ' + current_predicates_phrase + 'namespace = ? AND tag = ?;', ( namespace, tag ) ) ] )
            if include_pending_tags: hash_ids.update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM namespaces, ( tags, ' + pending_tables_phrase + ' USING ( tag_id ) ) USING ( namespace_id ) WHERE ' + pending_predicates_phrase + 'namespace = ? AND tag = ?;', ( namespace, tag ) ) ] )
            
        else:
            
            if include_current_tags: hash_ids.update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM tags, ' + current_tables_phrase + ' USING ( tag_id ) WHERE ' + current_predicates_phrase + 'tag = ?;', ( tag, ) ) ] )
            if include_pending_tags: hash_ids.update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM tags, ' + pending_tables_phrase + ' USING ( tag_id ) WHERE ' + pending_predicates_phrase + 'tag = ?;', ( tag, ) ) ] )
            
        
        return hash_ids
        
    
    def _GetHashesNamespaceIdsTagIds( self, c, hash_ids, mapping_type = 'regular' ):
        
        shared_namespace_ids_tag_ids = None
        
        for hash_id in hash_ids:
            
            if mapping_type == 'regular': namespace_ids_tag_ids = c.execute( 'SELECT namespace_id, tag_id FROM public_mappings WHERE hash_id = ?;', ( hash_id, ) ).fetchall()
            elif mapping_type == 'deleted': namespace_ids_tag_ids = c.execute( 'SELECT namespace_id, tag_id FROM deleted_public_mappings WHERE hash_id = ?;', ( hash_id, ) ).fetchall()
            elif mapping_type == 'pending': namespace_ids_tag_ids = c.execute( 'SELECT namespace_id, tag_id FROM pending_public_mappings WHERE hash_id = ?;', ( hash_id, ) ).fetchall()
            elif mapping_type == 'petitioned': namespace_ids_tag_ids = c.execute( 'SELECT namespace_id, tag_id FROM pending_public_mapping_petitions WHERE hash_id = ?;', ( hash_id, ) ).fetchall()
            
            if shared_namespace_ids_tag_ids is None: shared_namespace_ids_tag_ids = set( namespace_ids_tag_ids )
            else: shared_namespace_ids_tag_ids.intersection_update( namespace_ids_tag_ids )
            
            if len( shared_namespace_ids_tag_ids ) == 0: break
            
        
        if shared_namespace_ids_tag_ids is None: return set()
        
        return shared_namespace_ids_tag_ids
        
    
    def _GetHydrusSessions( self, c ):
        
        now = int( time.time() )
        
        c.execute( 'DELETE FROM hydrus_sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        results = c.execute( 'SELECT service_id, session_key, expiry FROM hydrus_sessions;' ).fetchall()
        
        for ( service_id, session_key, expiry ) in results:
            
            service_identifier = self._GetServiceIdentifier( c, service_id )
            
            sessions.append( ( service_identifier, session_key, expiry ) )
            
        
        return sessions
        
    
    def _GetMD5Status( self, c, md5 ):
        
        result = c.execute( 'SELECT hash_id FROM local_hashes WHERE md5 = ?;', ( sqlite3.Binary( md5 ), ) ).fetchone()
        
        if result is not None:
            
            ( hash_id, ) = result
            
            if self._options[ 'exclude_deleted_files' ]:
                
                result = c.execute( 'SELECT 1 FROM deleted_files WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                
                if result is not None: return ( 'deleted', None )
                
            
            result = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone()
            
            if result is not None:
                
                hash = self._GetHash( c, hash_id )
                
                return ( 'redundant', hash )
                
            
        
        return ( 'new', None )
        
    
    def _GetMediaResults( self, c, search_context, query_hash_ids ):
        
        file_service_identifier = search_context.GetFileServiceIdentifier()
        tag_service_identifier = search_context.GetTagServiceIdentifier()
        
        service_id = self._GetServiceId( c, file_service_identifier )
        
        system_predicates = search_context.GetSystemPredicates()
        
        limit = system_predicates.GetLimit()
        
        inbox_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM file_inbox;' ) }
        
        # get basic results
        
        must_be_local = system_predicates.MustBeLocal() or system_predicates.MustBeArchive()
        must_not_be_local = system_predicates.MustNotBeLocal()
        must_be_inbox = system_predicates.MustBeInbox()
        must_be_archive = system_predicates.MustBeArchive()
        
        if must_be_local or must_not_be_local:
            
            if service_id == self._local_file_service_id:
                
                if must_not_be_local: query_hash_ids = set()
                
            else:
                
                local_hash_ids = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( self._local_file_service_id, ) ) ]
                
                if must_be_local: query_hash_ids.intersection_update( local_hash_ids )
                else: query_hash_ids.difference_update( local_hash_ids )
                
            
        
        if must_be_inbox: query_hash_ids.intersection_update( inbox_hash_ids )
        elif must_be_archive: query_hash_ids.difference_update( inbox_hash_ids )
        
        # similar to
        
        if system_predicates.HasSimilarTo():
            
            ( hash, max_hamming ) = system_predicates.GetSimilarTo()
            
            hash_id = self._GetHashId( c, hash )
            
            result = c.execute( 'SELECT phash FROM perceptual_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
            if result is not None:
                
                ( phash, ) = result
                
                similar_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM perceptual_hashes WHERE hydrus_hamming( phash, ? ) <= ?;', ( sqlite3.Binary( phash ), max_hamming ) ) ]
                
                query_hash_ids.intersection_update( similar_hash_ids )
                
            
        
        # get first detailed results
        
        # since I've changed to new search model, this bit needs working over, I think?
        # null_service_identifier
        if file_service_identifier.GetType() not in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ):
            
            all_services_results = c.execute( 'SELECT hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( query_hash_ids ) + ';' ).fetchall()
            
            hash_ids_i_have_info_for = set()
            
            results = []
            
            for result in all_services_results:
                
                hash_id = result[0]
                
                if hash_id not in hash_ids_i_have_info_for:
                    
                    hash_ids_i_have_info_for.add( hash_id )
                    
                    results.append( result )
                    
                
            
            results.extend( [ ( hash_id, None, HC.APPLICATION_UNKNOWN, None, None, None, None, None, None ) for hash_id in query_hash_ids - hash_ids_i_have_info_for ] )
            
        else: results = c.execute( 'SELECT hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM files_info WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( query_hash_ids ) + ';', ( service_id, ) ).fetchall()
        
        # filtering basic results
        
        if system_predicates.CanPreFirstRoundLimit():
            
            if len( results ) > limit: results = random.sample( results, limit )
            
        else:
            
            results = [ ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in results if system_predicates.OkFirstRound( width, height ) ]
            
            if system_predicates.CanPreSecondRoundLimit():
                
                if len( results ) > limit: results = random.sample( results, system_predicates.GetLimit() )
                
            
        
        # get tagged results
        
        hash_ids = [ result[0] for result in results ]
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        hash_ids_to_hashes = self._GetHashIdsToHashes( c, hash_ids )
        
        hash_ids_to_current_tags = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, namespace + ':' + tag ) ) if namespace != '' else ( hash_id, ( service_id, tag ) ) for ( hash_id, service_id, namespace, tag ) in c.execute( 'SELECT hash_id, service_id, namespace, tag FROM namespaces, ( tags, mappings USING ( tag_id ) ) USING ( namespace_id ) WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        hash_ids_to_deleted_tags = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, namespace + ':' + tag ) ) if namespace != '' else ( hash_id, ( service_id, tag ) ) for ( hash_id, service_id, namespace, tag ) in c.execute( 'SELECT hash_id, service_id, namespace, tag FROM namespaces, ( tags, deleted_mappings USING ( tag_id ) ) USING ( namespace_id ) WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        hash_ids_to_pending_tags = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, namespace + ':' + tag ) ) if namespace != '' else ( hash_id, ( service_id, tag ) ) for ( hash_id, service_id, namespace, tag ) in c.execute( 'SELECT hash_id, service_id, namespace, tag FROM namespaces, ( tags, pending_mappings USING ( tag_id ) ) USING ( namespace_id ) WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        hash_ids_to_petitioned_tags = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, namespace + ':' + tag ) ) if namespace != '' else ( hash_id, ( service_id, tag ) ) for ( hash_id, service_id, namespace, tag ) in c.execute( 'SELECT hash_id, service_id, namespace, tag FROM namespaces, ( tags, mapping_petitions USING ( tag_id ) ) USING ( namespace_id ) WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        hash_ids_to_current_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM files_info WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_deleted_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM deleted_files WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_pending_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id_to FROM file_transfers WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_petitioned_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM file_petitions WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_local_ratings = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in c.execute( 'SELECT service_id, hash_id, rating FROM local_ratings WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        # do current and pending remote ratings here
        
        service_ids_to_service_identifiers = { service_id : HC.ClientServiceIdentifier( service_key, service_type, name ) for ( service_id, service_key, service_type, name ) in c.execute( 'SELECT service_id, service_key, type, name FROM services;' ) }
        
        # build it
        
        limit = system_predicates.GetLimit()
        
        include_current_tags = search_context.IncludeCurrentTags()
        include_pending_tags = search_context.IncludePendingTags()
        
        media_results = []
        
        random.shuffle( results ) # important for system:limit
        
        for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in results:
            
            if limit is not None and len( media_results ) >= limit: break
            
            hash = hash_ids_to_hashes[ hash_id ]
            
            if hash_id in hash_ids_to_current_tags: current_tags_dict = HC.BuildKeyToListDict( hash_ids_to_current_tags[ hash_id ] )
            else: current_tags_dict = {}
            
            if hash_id in hash_ids_to_deleted_tags: deleted_tags_dict = HC.BuildKeyToListDict( hash_ids_to_deleted_tags[ hash_id ] )
            else: deleted_tags_dict = {}
            
            if hash_id in hash_ids_to_pending_tags: pending_tags_dict = HC.BuildKeyToListDict( hash_ids_to_pending_tags[ hash_id ] )
            else: pending_tags_dict = {}
            
            if hash_id in hash_ids_to_petitioned_tags: petitioned_tags_dict = HC.BuildKeyToListDict( hash_ids_to_petitioned_tags[ hash_id ] )
            else: petitioned_tags_dict = {}
            
            tag_service_ids = { service_id for ( service_id, tags ) in current_tags_dict.items() + deleted_tags_dict.items() + pending_tags_dict.items() + petitioned_tags_dict.items() }
            
            service_identifiers_to_cdpp = {}
            
            for tag_service_id in tag_service_ids:
                
                if tag_service_id in current_tags_dict: current_tags = set( current_tags_dict[ tag_service_id ] )
                else: current_tags = set()
                
                if tag_service_id in deleted_tags_dict: deleted_tags = set( deleted_tags_dict[ tag_service_id ] )
                else: deleted_tags = set()
                
                if tag_service_id in pending_tags_dict: pending_tags = set( pending_tags_dict[ tag_service_id ] )
                else: pending_tags = set()
                
                if tag_service_id in petitioned_tags_dict: petitioned_tags = set( petitioned_tags_dict[ tag_service_id ] )
                else: petitioned_tags = set()
                
                tag_s_i = service_ids_to_service_identifiers[ tag_service_id ]
                
                service_identifiers_to_cdpp[ tag_s_i ] = ( current_tags, deleted_tags, pending_tags, petitioned_tags )
                
            
            tags_cdpp = CC.CDPPTagServiceIdentifiers( self._tag_service_precedence, service_identifiers_to_cdpp )
            
            if not system_predicates.OkSecondRound( tags_cdpp.GetNumTags( tag_service_identifier, include_current_tags = include_current_tags, include_pending_tags = include_pending_tags ) ): continue
            
            inbox = hash_id in inbox_hash_ids
            
            if hash_id in hash_ids_to_current_file_service_ids: current_file_service_identifiers = { service_ids_to_service_identifiers[ service_id ] for service_id in hash_ids_to_current_file_service_ids[ hash_id ] }
            else: current_file_service_identifiers = set()
            
            if hash_id in hash_ids_to_deleted_file_service_ids: deleted_file_service_identifiers = { service_ids_to_service_identifiers[ service_id ] for service_id in hash_ids_to_deleted_file_service_ids[ hash_id ] }
            else: deleted_file_service_identifiers = set()
            
            if hash_id in hash_ids_to_pending_file_service_ids: pending_file_service_identifiers = { service_ids_to_service_identifiers[ service_id ] for service_id in hash_ids_to_pending_file_service_ids[ hash_id ] }
            else: pending_file_service_identifiers = set()
            
            if hash_id in hash_ids_to_petitioned_file_service_ids: petitioned_file_service_identifiers = { service_ids_to_service_identifiers[ service_id ] for service_id in hash_ids_to_petitioned_file_service_ids[ hash_id ] }
            else: petitioned_file_service_identifiers = set()
            
            file_service_identifiers_cdpp = CC.CDPPFileServiceIdentifiers( current_file_service_identifiers, deleted_file_service_identifiers, pending_file_service_identifiers, petitioned_file_service_identifiers )
            
            if hash_id in hash_ids_to_local_ratings: local_ratings = { service_ids_to_service_identifiers[ service_id ] : rating for ( service_id, rating ) in hash_ids_to_local_ratings[ hash_id ] }
            else: local_ratings = {}
            
            local_ratings = CC.LocalRatings( local_ratings )
            remote_ratings = {}
            
            media_results.append( CC.MediaResult( ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_cdpp, file_service_identifiers_cdpp, local_ratings, remote_ratings ) ) )
            
        
        return CC.FileQueryResult( file_service_identifier, search_context.GetPredicates(), media_results )
        
    
    def _GetMediaResultsFromHashes( self, c, search_context, hashes ):
        
        query_hash_ids = set( self._GetHashIds( c, hashes ) )
        
        return self._GetMediaResults( c, search_context, query_hash_ids )
        
    
    def _GetMime( self, c, service_id, hash_id ):
        
        result = c.execute( 'SELECT mime FROM files_info USING ( hash_id ) WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None: raise HC.NotFoundException( 'Could not find that file\'s mime!' )
        
        ( mime, ) = result
        
        return mime
        
    
    def _GetNews( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        news = c.execute( 'SELECT post, timestamp FROM news WHERE service_id = ?;', ( service_id, ) ).fetchall()
        
        return news
        
    
    def _GetNumsPending( self, c ):
        
        tag_pending_1 = c.execute( 'SELECT service_id, COUNT( * ) FROM pending_mappings GROUP BY service_id;' ).fetchall()
        
        tag_pending_2 = c.execute( 'SELECT service_id, COUNT( * ) FROM mapping_petitions GROUP BY service_id;' ).fetchall()
        
        file_pending_1 = c.execute( 'SELECT service_id_to, COUNT( * ) FROM file_transfers WHERE service_id_to != ? GROUP BY service_id_to;', ( self._local_file_service_id, ) ).fetchall()
        
        file_pending_2 = c.execute( 'SELECT service_id, COUNT( * ) FROM file_petitions GROUP BY service_id;' ).fetchall()
        
        pendings_dict = {}
        
        for ( service_id, count ) in tag_pending_1 + tag_pending_2 + file_pending_1 + file_pending_2:
            
            if service_id in pendings_dict: pendings_dict[ service_id ] += count
            else: pendings_dict[ service_id ] = count
            
        
        pendings = { self._GetServiceIdentifier( c, service_id ) : count for ( service_id, count ) in pendings_dict.items() }
        
        return pendings
        
    
    def _GetPending( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service_type = service_identifier.GetType()
        
        repository = self._GetService( c, service_id )
        
        account = repository.GetAccount()
        
        if service_type == HC.TAG_REPOSITORY:
            
            mappings_dict = {}
            mappings_hash_ids = set()
            
            if account.HasPermission( HC.POST_DATA ):
                
                mappings_dict = HC.BuildKeyToListDict( [ ( ( namespace_id, tag_id ), hash_id ) for ( namespace_id, tag_id, hash_id ) in c.execute( 'SELECT namespace_id, tag_id, hash_id FROM pending_mappings WHERE service_id = ?;', ( service_id, ) ) ] )
                
            
            mappings = [ ( self._GetNamespaceTag( c, namespace_id, tag_id ), hash_ids ) for ( ( namespace_id, tag_id ), hash_ids ) in mappings_dict.items() ]
            
            mappings_hash_ids = HC.IntelligentMassUnion( mappings_dict.values() )
            
            mappings_hash_ids_to_hashes = self._GetHashIdsToHashes( c, mappings_hash_ids )
            
            petitions_dict = {}
            petitions_hash_ids = set()
            
            if account.HasPermission( HC.POST_PETITIONS ):
                
                petitions_dict = HC.BuildKeyToListDict( [ ( ( reason_id, namespace_id, tag_id ), hash_id ) for ( reason_id, namespace_id, tag_id, hash_id ) in c.execute( 'SELECT reason_id, namespace_id, tag_id, hash_id FROM mapping_petitions WHERE service_id = ?;', ( service_id, ) ) ] )
                
            
            petitions = [ ( self._GetReason( c, reason_id ), self._GetNamespaceTag( c, namespace_id, tag_id ), hash_ids ) for ( ( reason_id, namespace_id, tag_id ), hash_ids ) in petitions_dict.items() ]
            
            petitions_hash_ids = HC.IntelligentMassUnion( petitions_dict.values() )
            
            petitions_hash_ids_to_hashes = self._GetHashIdsToHashes( c, petitions_hash_ids )
            
            mappings_object = HC.ClientMappings( mappings, mappings_hash_ids_to_hashes )
            
            petitions_object = HC.ClientMappingPetitions( petitions, petitions_hash_ids_to_hashes )
            
            return ( mappings_object, petitions_object )
            
        elif service_type == HC.FILE_REPOSITORY:
            
            uploads = []
            
            petitions = []
            
            if account.HasPermission( HC.POST_DATA ): uploads = [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes, file_transfers USING ( hash_id ) WHERE service_id_to = ?;', ( service_id, ) ) ]
            
            if account.HasPermission( HC.POST_PETITIONS ):
                
                petitions = HC.BuildKeyToListDict( c.execute( 'SELECT reason, hash FROM reasons, ( hashes, file_petitions USING ( hash_id ) ) USING ( reason_id ) WHERE service_id = ?;', ( service_id, ) ) ).items()
                
                petitions_object = HC.ClientFilePetitions( petitions )
                
            
            return ( uploads, petitions_object )
            
        
    
    def _GetPixivAccount( self, c ):
        
        result = c.execute( 'SELECT pixiv_id, password FROM pixiv_account;' ).fetchone()
        
        if result is None: return ( '', '' )
        else: return result
        
    
    def _GetReason( self, c, reason_id ):
        
        result = c.execute( 'SELECT reason FROM reasons WHERE reason_id = ?;', ( reason_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Reason error in database' )
        
        ( reason, ) = result
        
        return reason
        
    
    def _GetReasonId( self, c, reason ):
        
        result = c.execute( 'SELECT reason_id FROM reasons WHERE reason=?;', ( reason, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO reasons ( reason ) VALUES ( ? );', ( reason, ) )
            
            reason_id = c.lastrowid
            
        else: ( reason_id, ) = result
        
        return reason_id
        
    
    def _GetResolution( self, c, hash ): return c.execute( 'SELECT width, height FROM files_info, hashes USING ( hash_id ) WHERE service_id = ? AND hash = ?;', ( self._local_file_service_id, sqlite3.Binary( hash ) ) ).fetchone()
    
    def _GetService( self, c, parameter ):
        
        try:
            
            if type( parameter ) == int: service_id = parameter
            elif type( parameter ) == HC.ClientServiceIdentifier: service_id = self._GetServiceId( c, parameter )
            elif type( parameter ) == ClientConstantsMessages.Contact:
                
                contact_id = self._GetContactId( c, parameter )
                
                ( service_id, ) = c.execute( 'SELECT service_id FROM message_depots WHERE contact_id = ?;', ( contact_id, ) ).fetchone()
                
            
        except: raise Exception( 'Service error in database.' )
        
        result = c.execute( 'SELECT service_key, type, name FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service error in database.' )
        
        ( service_key, service_type, name ) = result
        
        service_identifier = HC.ClientServiceIdentifier( service_key, service_type, name )
        
        if service_type in HC.REPOSITORIES:
            
            ( host, port, last_error, access_key, account, first_begin, next_begin ) = c.execute( 'SELECT host, port, last_error, access_key, account, first_begin, next_begin FROM repositories, ( accounts, addresses USING ( service_id ) ) USING ( service_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            credentials = CC.Credentials( host, port, access_key )
            
            if service_type == HC.RATING_LIKE_REPOSITORY:
                
                ( like, dislike ) = c.execute( 'SELECT like, dislike FROM ratings_like WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                service = CC.ServiceRemoteRestrictedRepositoryRatingLike( service_identifier, credentials, last_error, account, first_begin, next_begin, like, dislike )
                
            elif service_type == HC.RATING_NUMERICAL_REPOSITORY:
                
                ( lower, upper ) = c.execute( 'SELECT lower, upper FROM ratings_numerical WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                service = CC.ServiceRemoteRestrictedRepositoryRatingNumerical( service_identifier, credentials, last_error, account, first_begin, next_begin, lower, upper )
                
            else: service = CC.ServiceRemoteRestrictedRepository( service_identifier, credentials, last_error, account, first_begin, next_begin )
            
        elif service_type == HC.MESSAGE_DEPOT:
            
            ( host, port, last_error, access_key, account, contact_id, last_check, check_period, private_key, receive_anon ) = c.execute( 'SELECT host, port, last_error, access_key, account, contact_id, last_check, check_period, private_key, receive_anon FROM message_depots, ( accounts, addresses USING ( service_id ) ) USING ( service_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            credentials = CC.Credentials( host, port, access_key )
            
            contact = self._GetContact( c, contact_id )
            
            service = CC.ServiceRemoteRestrictedDepotMessage( service_identifier, credentials, last_error, account, last_check, check_period, contact, private_key, receive_anon )
            
        elif service_type in HC.RESTRICTED_SERVICES:
            
            ( host, port, last_error, access_key, account ) = c.execute( 'SELECT host, port, last_error, access_key, account FROM accounts, addresses USING ( service_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            credentials = CC.Credentials( host, port, access_key )
            
            service = CC.ServiceRemoteRestricted( service_identifier, credentials, last_error, account )
            
        elif service_type in HC.REMOTE_SERVICES:
            
            ( host, port, last_error ) = c.execute( 'SELECT host, port, last_error FROM addresses WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            credentials = CC.Credentials( host, port )
            
            service = CC.ServiceRemoteRestricted( service_identifier, credentials, last_error )
            
        elif service_type == HC.LOCAL_RATING_LIKE:
            
            ( like, dislike ) = c.execute( 'SELECT like, dislike FROM ratings_like WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            service = CC.ServiceLocalRatingLike( service_identifier, like, dislike )
            
        elif service_type == HC.LOCAL_RATING_NUMERICAL:
            
            ( lower, upper ) = c.execute( 'SELECT lower, upper FROM ratings_numerical WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            service = CC.ServiceLocalRatingNumerical( service_identifier, lower, upper )
            
        else: service = CC.Service( service_identifier )
        
        return service
        
    
    def _GetServices( self, c, limited_types = HC.ALL_SERVICES ):
        
        service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services WHERE type IN ' + HC.SplayListForDB( limited_types ) + ';' ) ]
        
        services = [ self._GetService( c, service_id ) for service_id in service_ids ]
        
        return services
        
    
    def _GetServiceId( self, c, parameter ):
        
        if type( parameter ) in ( str, unicode ):
            
            result = c.execute( 'SELECT service_id FROM services WHERE name = ?;', ( parameter, ) ).fetchone()
            
            if result is None: raise Exception( 'Service id error in database' )
            
            ( service_id, ) = result
            
        elif type( parameter ) == HC.ClientServiceIdentifier:
            
            service_type = parameter.GetType()
            
            if service_type == HC.NULL_SERVICE: return None
            elif service_type == HC.LOCAL_FILE: return self._local_file_service_id
            else:
                
                service_key = parameter.GetServiceKey()
                
                result = c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
                
                if result is None: raise Exception( 'Service id error in database' )
                
                ( service_id, ) = result
                
            
        
        return service_id
        
    
    def _GetServiceIds( self, c, service_type ): return [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services WHERE type = ?;', ( service_type, ) ) ]
    
    def _GetServiceIdentifier( self, c, service_id ):
        
        result = c.execute( 'SELECT service_key, type, name FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service type, name error in database' )
        
        ( service_key, service_type, name ) = result
        
        return HC.ClientServiceIdentifier( service_key, service_type, name )
        
    
    def _GetServiceIdentifiers( self, c, limited_types = HC.ALL_SERVICES ): return { HC.ClientServiceIdentifier( service_key, service_type, name ) for ( service_key, service_type, name ) in c.execute( 'SELECT service_key, type, name FROM services WHERE type IN ' + HC.SplayListForDB( limited_types ) + ';' ) }
    
    def _GetServiceInfo( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service_type = service_identifier.GetType()
        
        if service_type == HC.LOCAL_FILE: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES }
        elif service_type == HC.FILE_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES, HC.SERVICE_INFO_NUM_THUMBNAILS, HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL }
        elif service_type == HC.LOCAL_TAG: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS }
        elif service_type == HC.TAG_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS }
        elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): info_types = { HC.SERVICE_INFO_NUM_FILES }
        else: info_types = set()
        
        service_info = self._GetServiceInfoSpecific( c, service_id, service_type, info_types )
        
        return service_info
        
    
    def _GetServiceInfoSpecific( self, c, service_id, service_type, info_types ):
        
        save_it = True
        
        results = { info_type : info for ( info_type, info ) in c.execute( 'SELECT info_type, info FROM service_info WHERE service_id = ? AND info_type IN ' + HC.SplayListForDB( info_types ) + ';', ( service_id, ) ) }
        
        if len( results ) != len( info_types ):
            
            info_types_hit = results.keys()
            
            info_types_missed = info_types.difference( info_types_hit )
            
            if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                
                common_tag_info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS }
                
                if common_tag_info_types <= info_types_missed:
                    
                    ( num_files, num_namespaces, num_tags ) = c.execute( 'SELECT COUNT( DISTINCT hash_id ), COUNT( DISTINCT namespace_id ), COUNT( DISTINCT tag_id ) FROM mappings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                    results[ HC.SERVICE_INFO_NUM_FILES ] = num_files
                    results[ HC.SERVICE_INFO_NUM_NAMESPACES ] = num_namespaces
                    results[ HC.SERVICE_INFO_NUM_TAGS ] = num_tags
                    
                    c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_FILES, num_files ) )
                    c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_NAMESPACES, num_namespaces ) )
                    c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_TAGS, num_tags ) )
                    
                    info_types_missed.difference_update( common_tag_info_types )
                    
                
            
            for info_type in info_types_missed:
                
                if service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ):
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = c.execute( 'SELECT COUNT( * ) FROM files_info WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_TOTAL_SIZE: result = c.execute( 'SELECT SUM( size ) FROM files_info WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_FILES: result = c.execute( 'SELECT COUNT( * ) FROM deleted_files WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_THUMBNAILS: result = c.execute( 'SELECT COUNT( * ) FROM files_info WHERE service_id = ? AND mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ';', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL:
                        
                        thumbnails_i_have = { path.decode( 'hex' ) for path in dircache.listdir( HC.CLIENT_THUMBNAILS_DIR ) if not path.endswith( '_resized' ) }
                        
                        hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' AND service_id = ?;', ( service_id, ) ) ]
                        
                        thumbnails_i_should_have = self._GetHashes( c, hash_ids )
                        
                        thumbnails_i_have.intersection_update( thumbnails_i_should_have )
                        
                        result = ( len( thumbnails_i_have ), )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_INBOX: result = c.execute( 'SELECT COUNT( * ) FROM file_inbox, files_info USING ( hash_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = c.execute( 'SELECT COUNT( DISTINCT hash_id ) FROM mappings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_NAMESPACES: result = c.execute( 'SELECT COUNT( DISTINCT namespace_id ) FROM mappings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_TAGS: result = c.execute( 'SELECT COUNT( DISTINCT tag_id ) FROM mappings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_MAPPINGS: result = c.execute( 'SELECT COUNT( * ) FROM mappings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_MAPPINGS: result = c.execute( 'SELECT COUNT( * ) FROM deleted_mappings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = c.execute( 'SELECT COUNT( * ) FROM local_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type == HC.NULL_SERVICE:
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES:
                        
                        result = ( len( c.execute( 'SELECT hash_id FROM mappings UNION SELECT hash_id FROM files_info;' ).fetchall() ), )
                        
                        save_it = False
                        
                    
                
                if result is None: info = 0
                else: ( info, ) = result
                
                if info is None: info = 0
                
                if save_it: c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, info_type, info ) )
                
                results[ info_type ] = info
                
            
        
        return results
        
    
    def _GetServiceType( self, c, service_id ):
        
        result = c.execute( 'SELECT type FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_type, ) = result
        
        return service_type
        
    
    def _GetFileSystemPredicates( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service_type = service_identifier.GetType()
        
        predicates = []
        
        if service_type in ( HC.NULL_SERVICE, HC.TAG_REPOSITORY, HC.LOCAL_TAG ):
            
            service_info = self._GetServiceInfoSpecific( c, service_id, service_type, { HC.SERVICE_INFO_NUM_FILES } )
            
            num_everything = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None ), num_everything ) )
            
            predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ), None ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_HASH ] ] )
            
            # num local would be great
            # num inbox would be great
            
        elif service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ):
            
            service_info = self._GetServiceInfoSpecific( c, service_id, service_type, { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_INBOX } )
            
            num_everything = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            if service_type == HC.FILE_REPOSITORY:
                
                if self._options[ 'exclude_deleted_files' ]:
                    
                    ( num_everything_deleted, ) = c.execute( 'SELECT COUNT( * ) FROM files_info, deleted_files USING ( hash_id ) WHERE files_info.service_id = ? AND deleted_files.service_id = ?;', ( service_id, self._local_file_service_id ) ).fetchone()
                    
                    num_everything -= num_everything_deleted
                    
                
            
            num_inbox = service_info[ HC.SERVICE_INFO_NUM_INBOX ]
            num_archive = num_everything - num_inbox
            
            predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None ), num_everything ) )
            
            if num_inbox > 0:
                
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None ), num_inbox ) )
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None ), num_archive ) )
                
            
            if service_type == HC.FILE_REPOSITORY:
                
                ( num_local, ) = c.execute( 'SELECT COUNT( * ) FROM files_info AS remote_files_info, files_info USING ( hash_id ) WHERE remote_files_info.service_id = ? AND files_info.service_id = ?;', ( service_id, self._local_file_service_id ) ).fetchone()
                
                num_not_local = num_everything - num_local
                
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None ), num_local ) )
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None ), num_not_local ) )
                
            
            predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ), None ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_SIZE, HC.SYSTEM_PREDICATE_TYPE_AGE, HC.SYSTEM_PREDICATE_TYPE_HASH, HC.SYSTEM_PREDICATE_TYPE_WIDTH, HC.SYSTEM_PREDICATE_TYPE_HEIGHT, HC.SYSTEM_PREDICATE_TYPE_RATIO, HC.SYSTEM_PREDICATE_TYPE_DURATION, HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, HC.SYSTEM_PREDICATE_TYPE_MIME, HC.SYSTEM_PREDICATE_TYPE_RATING, HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO ] ] )
            
            predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_NOT_UPLOADED_TO, service_identifier ), None ) for service_identifier in self._GetServiceIdentifiers( c, ( HC.FILE_REPOSITORY, ) ) ] )
            
        
        return predicates
        
    
    def _GetMessageSystemPredicates( self, c, identity ):
        
        name = identity.GetName()
        
        is_anon = name == 'Anonymous'
        
        additional_predicate = ''
        
        if name != 'Anonymous':
            
            service = self._GetService( c, identity )
            
            if not service.ReceivesAnon(): additional_predicate = 'contact_id_from != 1 AND '
            
        
        contact_id = self._GetContactId( c, name )
        
        unread_status_id = self._GetStatusId( c, 'sent' )
        
        #service_info = self._GetServiceInfoSpecific( c, service_id, service_type, { HC.SERVICE_INFO_NUM_CONVERSATIONS, HC.SERVICE_INFO_NUM_INBOX, HC.SERVICE_INFO_NUM_UNREAD, HC.SERVICE_INFO_NUM_DRAFTS } )
        
        ( num_conversations, ) = c.execute( 'SELECT COUNT( DISTINCT conversation_id ) FROM messages, message_destination_map USING ( message_id ) WHERE ' + additional_predicate + '( contact_id_from = ? OR contact_id_to = ? );', ( contact_id, contact_id ) ).fetchone()
        ( num_inbox, ) = c.execute( 'SELECT COUNT( DISTINCT conversation_id ) FROM message_destination_map, ( messages, message_inbox USING ( message_id ) ) USING ( message_id ) WHERE ' + additional_predicate + 'contact_id_to = ?;', ( contact_id, ) ).fetchone()
        ( num_drafts, ) = c.execute( 'SELECT COUNT( DISTINCT conversation_id ) FROM messages, message_drafts USING ( message_id ) WHERE contact_id_from = ?;', ( contact_id, ) ).fetchone()
        ( num_unread, ) = c.execute( 'SELECT COUNT( DISTINCT conversation_id ) FROM messages, message_destination_map USING ( message_id ) WHERE ' + additional_predicate + 'contact_id_to = ? AND status_id = ?;', ( contact_id, unread_status_id ) ).fetchone()
        
        predicates = []
        
        # anon has no inbox, no received mail; only sent mail
        
        predicates.append( ( u'system:everything', num_conversations ) )
        if not is_anon:
            predicates.append( ( u'system:inbox', num_inbox ) )
            predicates.append( ( u'system:archive', num_conversations - num_inbox ) )
            predicates.append( ( u'system:unread', num_unread ) )
        predicates.append( ( u'system:drafts', num_drafts ) )
        if not is_anon:
            predicates.append( ( u'system:started_by', None ) )
            predicates.append( ( u'system:from', None ) )
        predicates.append( ( u'system:to', None ) )
        predicates.append( ( u'system:age', None ) )
        predicates.append( ( u'system:numattachments', None ) )
        # we can add more later
        
        return predicates
        
    
    def _GetShutdownTimestamps( self, c ):
        
        shutdown_timestamps = collections.defaultdict( lambda: 0 )
        
        shutdown_timestamps.update( c.execute( 'SELECT shutdown_type, timestamp FROM shutdown_timestamps;' ).fetchall() )
        
        return shutdown_timestamps
        
    
    def _GetTagServicePrecedence( self, c ):
        
        service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM tag_service_precedence ORDER BY precedence ASC;' ) ]
        
        # the first service_id is the most important
        
        return [ self._GetServiceIdentifier( c, service_id ) for service_id in service_ids ]
        
    
    def _GetThumbnailHashesIShouldHave( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' AND service_id = ?;', ( service_id, ) ) ]
        
        hashes = set( self._GetHashes( c, hash_ids ) )
        
        return hashes
        
    
    def _GetURLStatus( self, c, url ):
        
        result = c.execute( 'SELECT hash_id FROM urls WHERE url = ?;', ( url, ) ).fetchone()
        
        if result is not None:
            
            ( hash_id, ) = result
            
            if self._options[ 'exclude_deleted_files' ]:
                
                result = c.execute( 'SELECT 1 FROM deleted_files WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                
                if result is not None: return ( 'deleted', None )
                
            
            result = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone()
            
            if result is not None:
                
                hash = self._GetHash( c, hash_id )
                
                return ( 'redundant', hash )
                
            
        
        return ( 'new', None )
        
    
    def _ImportFile( self, c, file, advanced_import_options = {}, service_identifiers_to_tags = {}, generate_media_result = False, override_deleted = False, url = None ):
        
        result = 'successful'
        
        can_add = True
        
        archive = 'auto_archive' in advanced_import_options
        
        exclude_deleted_files = 'exclude_deleted_files' in advanced_import_options
        
        file = HydrusImageHandling.ConvertToPngIfBmp( file )
        
        size = len( file )
        
        if size == 0: can_add = False
        
        if 'min_size' in advanced_import_options:
            
            min_size = advanced_import_options[ 'min_size' ]
            
            if size < min_size: raise Exception( 'File too small' )
            
        
        hash = hashlib.sha256( file ).digest()
        
        hash_id = self._GetHashId( c, hash )
        
        if url is not None: c.execute( 'INSERT OR IGNORE INTO urls ( url, hash_id ) VALUES ( ?, ? );', ( url, hash_id ) )
        
        already_in_db = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone() is not None
        
        if already_in_db:
            
            result = 'redundant'
            
            if archive:
                
                c.execute( 'DELETE FROM file_inbox WHERE hash_id = ?;', ( hash_id, ) )
                
                self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ARCHIVE, CC.LOCAL_FILE_SERVICE_IDENTIFIER, set( ( hash, ) ) ) ] )
                self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ARCHIVE, CC.LOCAL_FILE_SERVICE_IDENTIFIER, set( ( hash, ) ) ) ] )
                
            
            can_add = False
            
        else:
            
            if not override_deleted:
                
                if exclude_deleted_files and c.execute( 'SELECT 1 FROM deleted_files WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone() is not None:
                    
                    result = 'deleted'
                    
                    can_add = False
                    
                
            
        
        if can_add:
            
            mime = HC.GetMimeFromString( file[:256] )
            
            width = None
            height = None
            duration = None
            num_frames = None
            num_words = None
            
            if mime in HC.IMAGES:
                
                image_container = HydrusImageHandling.RenderImageFromFile( file, hash )
                
                ( width, height ) = image_container.GetSize()
                
                image_container = HydrusImageHandling.RenderImageFromFile( file, hash )
                
                ( width, height ) = image_container.GetSize()
                
                if image_container.IsAnimated():
                    
                    duration = image_container.GetTotalDuration()
                    num_frames = image_container.GetNumFrames()
                    
                
            elif mime == HC.APPLICATION_FLASH:
                
                ( ( width, height ), duration, num_frames ) = HydrusFlashHandling.GetFlashProperties( file )
                
            elif mime == HC.VIDEO_FLV:
                
                ( ( width, height ), duration, num_frames ) = HydrusVideoHandling.GetFLVProperties( file )
                
            elif mime == HC.APPLICATION_PDF: num_words = HydrusDocumentHandling.GetPDFNumWords( file )
            
            if width is not None and height is not None:
                
                if 'min_resolution' in advanced_import_options:
                    
                    ( min_x, min_y ) = advanced_import_options[ 'min_resolution' ]
                    
                    if width < min_x or height < min_y: raise Exception( 'Resolution too small' )
                    
                
            
        
        if can_add:
            
            timestamp = int( time.time() )
            
            dest_path = HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' )
            
            if not os.path.exists( dest_path ):
                
                with open( dest_path, 'wb' ) as f: f.write( file )
                
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                thumbnail = HydrusImageHandling.GenerateThumbnailFileFromFile( file, HC.UNSCALED_THUMBNAIL_DIMENSIONS )
                
                thumbnail_path_to = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
                
                with open( thumbnail_path_to, 'wb' ) as f: f.write( thumbnail )
                
                thumbnail_resized = HydrusImageHandling.GenerateThumbnailFileFromFile( thumbnail, self._options[ 'thumbnail_dimensions' ] )
                
                thumbnail_resized_path_to = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' ) + '_resized'
                
                with open( thumbnail_resized_path_to, 'wb' ) as f: f.write( thumbnail_resized )
                
                phash = HydrusImageHandling.GeneratePerceptualHash( thumbnail )
                
                # replace is important here!
                c.execute( 'INSERT OR REPLACE INTO perceptual_hashes VALUES ( ?, ? );', ( hash_id, sqlite3.Binary( phash ) ) )
                
            
            files_info_rows = [ ( self._local_file_service_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) ]
            
            self._AddFiles( c, files_info_rows )
            
            md5 = hashlib.md5( file ).digest()
            
            sha1 = hashlib.sha1( file ).digest()
            
            c.execute( 'INSERT OR IGNORE INTO local_hashes ( hash_id, md5, sha1 ) VALUES ( ?, ?, ? );', ( hash_id, sqlite3.Binary( md5 ), sqlite3.Binary( sha1 ) ) )
            
            if not archive: self._InboxFiles( c, ( hash_id, ) )
            
        
        if len( service_identifiers_to_tags ) > 0 and c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone() is not None:
            
            for ( service_identifier, tags ) in service_identifiers_to_tags.items():
                
                if service_identifier == CC.LOCAL_TAG_SERVICE_IDENTIFIER: edit_log = [ ( CC.CONTENT_UPDATE_ADD, tag ) for tag in tags ]
                else: edit_log = [ ( CC.CONTENT_UPDATE_PENDING, tag ) for tag in tags ]
                
                content_updates = [ HC.ContentUpdate( CC.CONTENT_UPDATE_EDIT_LOG, service_identifier, ( hash, ), edit_log ) ]
                
                self._ProcessContentUpdates( c, content_updates )
                
            
        
        if generate_media_result:
            
            if ( can_add or already_in_db ):
                
                search_context = CC.FileSearchContext()
                
                ( media_result, ) = self._GetMediaResults( c, search_context, set( ( hash_id, ) ) )
                
                return ( result, hash, media_result )
                
            else: return ( result, hash, None )
            
        else: return ( result, hash )
        
    
    def _ImportFilePage( self, c, page_key, file, advanced_import_options = {}, service_identifiers_to_tags = {}, url = None ):
        
        try:
            
            ( result, hash, media_result ) = self._ImportFile( c, file, advanced_import_options = advanced_import_options, service_identifiers_to_tags = service_identifiers_to_tags, generate_media_result = True, url = url )
            
            if media_result is not None: self.pub( 'add_media_result', page_key, media_result )
            
            if result == 'successful':
                self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, CC.LOCAL_FILE_SERVICE_IDENTIFIER, ( hash, ) ) ] )
                self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, CC.LOCAL_FILE_SERVICE_IDENTIFIER, ( hash, ) ) ] )
            
            self.pub( 'import_done', page_key, result )
            
        except Exception as e:
            
            HC.pubsub.pub( 'import_done', page_key, 'failed', exception = e )
            
            raise
            
        
    
    def _InboxFiles( self, c, hash_ids ):
        
        c.executemany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', [ ( hash_id, ) for hash_id in hash_ids ] )
        
        num_added = c.rowcount
        
        if num_added > 0:
            
            splayed_hash_ids = HC.SplayListForDB( hash_ids )
            
            updates = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id;' ).fetchall()
            
            c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in updates ] )
            
        
    
    def _PetitionFiles( self, c, service_identifier, hashes, reason ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        hash_ids = self._GetHashIds( c, hashes )
        
        reason_id = self._GetReasonId( c, reason )
        
        c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
        
        c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, hash_id, reason_id ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, reason_id ) for hash_id in hash_ids ] )
        
        self.pub( 'notify_new_pending' )
        self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_PETITION, service_identifier, hashes ) ] )
        self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_PETITION, service_identifier, hashes ) ] )
        
    
    def _ProcessContentUpdates( self, c, content_updates ):
        
        for content_update in content_updates:
            
            service_identifier =  content_update.GetServiceIdentifier()
            
            service_type = service_identifier.GetType()
            
            service_id = self._GetServiceId( c, service_identifier )
            
            action = content_update.GetAction()
            
            if service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ):
                
                hashes = content_update.GetHashes()
                
                hash_ids = self._GetHashIds( c, hashes )
                
                if action == CC.CONTENT_UPDATE_ARCHIVE: self._ArchiveFiles( c, hash_ids )
                elif action == CC.CONTENT_UPDATE_INBOX: self._InboxFiles( c, hash_ids )
                elif action == CC.CONTENT_UPDATE_DELETE: self._DeleteFiles( c, service_id, hash_ids )
                elif action == CC.CONTENT_UPDATE_ADD:
                    
                    # this is really 'uploaded' rather than a strict add, so may need to improve it in future!
                    
                    files_info_rows = c.execute( 'SELECT ?, hash_id, size, mime, ?, width, height, duration, num_frames, num_words FROM files_info WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, int( time.time() ), self._local_file_service_id ) ).fetchall()
                    
                    self._AddFiles( c, files_info_rows )
                    
                
            elif service_type == HC.LOCAL_TAG:
                
                hashes = content_update.GetHashes()
                
                hash_ids = self._GetHashIds( c, hashes )
                
                info = content_update.GetInfo()
                
                if action == CC.CONTENT_UPDATE_EDIT_LOG:
                    
                    splayed_hash_ids = HC.SplayListForDB( hash_ids )
                    
                    hash_ids_set = set( hash_ids )
                    
                    edit_log = info
                    
                    mappings_ids = []
                    deleted_mappings_ids = []
                    
                    for ( action, info ) in edit_log:
                        
                        if action == CC.CONTENT_UPDATE_ADD:
                            
                            tag = info
                            
                            if tag == '': continue
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            
                        elif action == CC.CONTENT_UPDATE_DELETE:
                            
                            tag = info
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            deleted_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            
                        
                    
                    self._UpdateMappings( c, service_id, mappings_ids, deleted_mappings_ids )
                    
                    self.pub( 'notify_new_pending' )
                    
                
            elif service_type == HC.TAG_REPOSITORY:
                
                hashes = content_update.GetHashes()
                
                hash_ids = self._GetHashIds( c, hashes )
                
                info = content_update.GetInfo()
                
                if action == CC.CONTENT_UPDATE_ADD:
                    
                    tag = info
                    
                    ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                    
                    self._UpdateMappings( c, service_id, [ ( namespace_id, tag_id, hash_ids ) ], [] )
                    
                elif action == CC.CONTENT_UPDATE_DELETE:
                    
                    tag = info
                    
                    ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                    
                    self._UpdateMappings( c, service_id, [], [ ( namespace_id, tag_id, hash_ids ) ] )
                    
                elif action == CC.CONTENT_UPDATE_EDIT_LOG:
                    
                    ( precedence, ) = c.execute( 'SELECT precedence FROM tag_service_precedence WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                    higher_precedence_service_ids = [ id for ( id, ) in c.execute( 'SELECT service_id FROM tag_service_precedence WHERE precedence < ?;', ( precedence, ) ) ]
                    
                    splayed_higher_precedence_service_ids = HC.SplayListForDB( higher_precedence_service_ids )
                    
                    splayed_hash_ids = HC.SplayListForDB( hash_ids )
                    
                    hash_ids_set = set( hash_ids )
                    
                    edit_log = info
                    
                    for ( action, info ) in edit_log:
                        
                        if action == CC.CONTENT_UPDATE_PENDING:
                            
                            tag = info
                            
                            if tag == '': continue
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            already_in_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, namespace_id, tag_id ) ) }
                            
                            hash_ids_i_can_add = hash_ids_set - already_in_hash_ids
                            
                            c.executemany( 'INSERT OR IGNORE INTO pending_mappings VALUES ( ?, ?, ?, ? );', [ ( service_id, namespace_id, tag_id, hash_id ) for hash_id in hash_ids_i_can_add ] )
                            
                            self._UpdateAutocompleteTagCacheFromPendingTags( c, service_id, namespace_id, tag_id, hash_ids_i_can_add, 1 )
                            
                            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_mappings WHERE service_id IN ' + splayed_higher_precedence_service_ids + ' AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( namespace_id, tag_id ) ) }
                            
                            valid_hash_ids = hash_ids_i_can_add - invalid_hash_ids
                            
                            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM active_pending_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ';', ( namespace_id, tag_id ) ) }
                            
                            valid_hash_ids.difference_update( invalid_hash_ids )
                            
                            c.executemany( 'INSERT OR IGNORE INTO active_pending_mappings VALUES ( ?, ?, ? );', [ ( namespace_id, tag_id, hash_id ) for hash_id in valid_hash_ids ] )
                            
                            self._UpdateAutocompleteTagCacheFromActivePendingTags( c, namespace_id, tag_id, valid_hash_ids, 1 )
                            
                        elif action == CC.CONTENT_UPDATE_RESCIND_PENDING:
                            
                            tag = info
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            actual_hash_ids_i_can_delete = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM pending_mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, namespace_id, tag_id ) ) ]
                            
                            c.execute( 'DELETE FROM pending_mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( actual_hash_ids_i_can_delete ) + ';', ( service_id, namespace_id, tag_id ) )
                            
                            self._UpdateAutocompleteTagCacheFromPendingTags( c, service_id, namespace_id, tag_id, actual_hash_ids_i_can_delete, -1 )
                            
                            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM pending_mappings WHERE service_id IN ' + splayed_higher_precedence_service_ids + ' AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( namespace_id, tag_id ) ) }
                            
                            valid_hash_ids = set( hash_ids ) - invalid_hash_ids
                            
                            actual_hash_ids_i_can_delete = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM active_pending_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ';', ( namespace_id, tag_id ) ) ]
                            
                            c.execute( 'DELETE FROM active_pending_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( actual_hash_ids_i_can_delete ) + ';', ( namespace_id, tag_id ) )
                            
                            self._UpdateAutocompleteTagCacheFromActivePendingTags( c, namespace_id, tag_id, actual_hash_ids_i_can_delete, -1 )
                            
                        elif action == CC.CONTENT_UPDATE_PETITION:
                            
                            ( tag, reason ) = info
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            reason_id = self._GetReasonId( c, reason )
                            
                            c.executemany( 'INSERT OR IGNORE INTO mapping_petitions VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, namespace_id, tag_id, hash_id, reason_id ) for hash_id in hash_ids ] )
                            
                        elif action == CC.CONTENT_UPDATE_RESCIND_PETITION:
                            
                            tag = info
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, namespace_id, tag_id ) )
                            
                        
                    
                    self.pub( 'notify_new_pending' )
                    
                
            elif service_type in HC.RATINGS_SERVICES:
                
                action = content_update.GetAction()
                
                hashes = content_update.GetHashes()
                
                hash_ids = self._GetHashIds( c, hashes )
                
                splayed_hash_ids = HC.SplayListForDB( hash_ids )
                
                info = content_update.GetInfo()
                
                if action == CC.CONTENT_UPDATE_RATING:
                    
                    rating = info
                    
                    if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                        
                        ratings_added = 0
                        
                        c.execute( 'DELETE FROM local_ratings WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                        
                        ratings_added -= c.rowcount
                        
                        if rating is not None:
                            
                            c.execute( 'DELETE FROM ratings_filter WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                            
                            c.executemany( 'INSERT INTO local_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                            
                            ratings_added += c.rowcount
                            
                        
                        c.execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                        
                        # and then do a thing here where it looks up remote services links and then pends/rescinds pends appropriately
                        
                    
                elif action == CC.CONTENT_UPDATE_RATINGS_FILTER:
                    
                    ( min, max ) = info
                    
                    c.execute( 'DELETE FROM ratings_filter WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                    
                    c.executemany( 'INSERT INTO ratings_filter ( service_id, hash_id, min, max ) VALUES ( ?, ?, ?, ? );', [ ( service_id, hash_id, min, max ) for hash_id in hash_ids ] )
                    
                
            
        
        self.pub( 'content_updates_data', content_updates )
        self.pub( 'content_updates_gui', content_updates )
        
    
    def _RecalcActiveMappings( self, c ):
        
        service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM tag_service_precedence ORDER BY precedence DESC;' ) ]
        
        c.execute( 'DELETE FROM active_mappings;' )
        c.execute( 'DELETE FROM active_pending_mappings;' )
        
        first_round = True
        
        for service_id in service_ids:
            
            c.execute( 'INSERT OR IGNORE INTO active_mappings SELECT namespace_id, tag_id, hash_id FROM mappings WHERE service_id = ?;', ( service_id, ) )
            c.execute( 'INSERT OR IGNORE INTO active_pending_mappings SELECT namespace_id, tag_id, hash_id FROM pending_mappings WHERE service_id = ?;', ( service_id, ) )
            
            # is this incredibly inefficient?
            # if this is O( n-squared ) or whatever, just rewrite it as two queries using indices
            if not first_round:
                
                c.execute( 'DELETE FROM active_mappings WHERE namespace_id || "," || tag_id || "," || hash_id IN ( SELECT namespace_id || "," || tag_id || "," || hash_id FROM deleted_mappings WHERE service_id = ? );', ( service_id, ) )
                c.execute( 'DELETE FROM active_pending_mappings WHERE namespace_id || "," || tag_id || "," || hash_id IN ( SELECT namespace_id || "," || tag_id || "," || hash_id FROM deleted_mappings WHERE service_id = ? );', ( service_id, ) )
                
            
            first_round = False
            
        
        c.execute( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL;' )
        
    
    def _RecalcActivePendingMappings( self, c ):
        
        service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM tag_service_precedence ORDER BY precedence DESC;' ) ]
        
        c.execute( 'DELETE FROM active_pending_mappings;' )
        
        first_round = True
        
        for service_id in service_ids:
            
            c.execute( 'INSERT OR IGNORE INTO active_pending_mappings SELECT namespace_id, tag_id, hash_id FROM pending_mappings WHERE service_id = ?;', ( service_id, ) )
            
            # is this incredibly inefficient?
            # if this is O( n-squared ) or whatever, just rewrite it as two queries using indices
            if not first_round: c.execute( 'DELETE FROM active_pending_mappings WHERE namespace_id || "," || tag_id || "," || hash_id IN ( SELECT namespace_id || "," || tag_id || "," || hash_id FROM deleted_mappings WHERE service_id = ? );', ( service_id, ) )
            
            first_round = False
            
        
        c.execute( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL;' )
        
    
    def _ResetService( self, c, service_identifier ):
        
        service_id = self._GetServiceId( c, service_identifier )
        
        service_key = os.urandom( 32 )
        
        service_type = service_identifier.GetType()
        
        service_name = service_identifier.GetName()
        
        new_service_identifier = HC.ClientServiceIdentifier( service_key, service_type, service_name )
        
        kwargs = {}
        
        # we don't reset local services yet, so no need to check if address exists
        ( host, port ) = c.execute( 'SELECT host, port FROM addresses WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        result = c.execute( 'SELECT access_key FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        if result is None: access_key = None
        else: ( access_key, ) = result
        
        credentials = CC.Credentials( host, port, access_key )
        
        extra_info = None # we don't reset message depots yet, so no need to preserve
        
        c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
        
        if service_type == HC.TAG_REPOSITORY: self._RecalcActiveMappings( c )
        
        self._AddService( c, new_service_identifier, credentials, extra_info )
        
        self.pub( 'service_update_db', CC.ServiceUpdate( CC.SERVICE_UPDATE_RESET, service_identifier, new_service_identifier ) )
        self.pub( 'notify_new_pending' )
        self.pub( 'permissions_are_stale' )
        self.pub( 'log_message', 'database', 'reset ' + service_name )
        
    
    def _Set4chanPass( self, c, token, pin, timeout ):
        
        c.execute( 'DELETE FROM fourchan_pass;' )
        
        c.execute( 'INSERT INTO fourchan_pass ( token, pin, timeout ) VALUES ( ?, ?, ? );', ( token, pin, timeout ) )
        
    
    def _SetFavouriteCustomFilterActions( self, c, favourites ):
        
        c.execute( 'DELETE FROM favourite_custom_filter_actions;' )
        
        c.executemany( 'INSERT INTO favourite_custom_filter_actions ( name, actions ) VALUES ( ?, ? );', [ ( name, actions ) for ( name, actions ) in favourites.items() ] )
        
    
    def _SetPixivAccount( self, c, pixiv_id, password ):
        
        c.execute( 'DELETE FROM pixiv_account;' )
        
        c.execute( 'INSERT INTO pixiv_account ( pixiv_id, password ) VALUES ( ?, ? );', ( pixiv_id, password ) )
        
    
    def _SetTagServicePrecedence( self, c, service_identifiers ):
        
        del self._tag_service_precedence[:]
        
        self._tag_service_precedence.extend( service_identifiers )
        
        service_ids = [ self._GetServiceId( c, service_identifier ) for service_identifier in service_identifiers ]
        
        c.execute( 'DELETE FROM tag_service_precedence;' )
        
        c.executemany( 'INSERT INTO tag_service_precedence ( service_id, precedence ) VALUES ( ?, ? );', [ ( service_id, precedence ) for ( precedence, service_id ) in enumerate( service_ids ) ] )
        
        self._RecalcActiveMappings( c )
        
    
    def _UpdateAutocompleteTagCacheFromActiveCurrentTags( self, c, namespace_id, tag_id, hash_ids, direction ):
        
        info = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' GROUP BY service_id;' ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id = ? AND tag_service_id IS NULL AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, service_id, namespace_id, tag_id ) for ( service_id, count ) in info ] )
        
        c.execute( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id IS NULL AND tag_service_id IS NULL AND namespace_id = ? AND tag_id = ?;', ( len( hash_ids ) * direction, namespace_id, tag_id ) )
        
    
    def _UpdateAutocompleteTagCacheFromCurrentTags( self, c, tag_service_id, namespace_id, tag_id, hash_ids, direction ):
        
        info = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' GROUP BY service_id;' ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( file_service_id, count ) in info ] )
        
        c.execute( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id IS NULL AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', ( len( hash_ids ) * direction, tag_service_id, namespace_id, tag_id ) )
        
    
    def _UpdateAutocompleteTagCacheFromFiles( self, c, file_service_id, hash_ids, direction ):
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        current_tags = c.execute( 'SELECT service_id, namespace_id, tag_id, COUNT( * ) FROM mappings WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id, namespace_id, tag_id;' ).fetchall()
        pending_tags = c.execute( 'SELECT service_id, namespace_id, tag_id, COUNT( * ) FROM pending_mappings WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id, namespace_id, tag_id;' ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( tag_service_id, namespace_id, tag_id, count ) in current_tags ] )
        c.executemany( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( tag_service_id, namespace_id, tag_id, count ) in current_tags ] )
        
        active_tags = c.execute( 'SELECT namespace_id, tag_id, COUNT( * ) FROM active_mappings WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY namespace_id, tag_id;' ).fetchall()
        active_pending_tags = c.execute( 'SELECT namespace_id, tag_id, COUNT( * ) FROM active_pending_mappings WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY namespace_id, tag_id;' ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id = ? AND tag_service_id IS NULL AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, namespace_id, tag_id ) for ( namespace_id, tag_id, count ) in active_tags ] )
        c.executemany( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id = ? AND tag_service_id IS NULL AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, namespace_id, tag_id ) for ( namespace_id, tag_id, count ) in active_pending_tags ] )
        
    
    def _UpdateAutocompleteTagCacheFromActivePendingTags( self, c, namespace_id, tag_id, hash_ids, direction ):
        
        info = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' GROUP BY service_id;' ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id = ? AND tag_service_id IS NULL AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, service_id, namespace_id, tag_id ) for ( service_id, count ) in info ] )
        
        c.execute( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id IS NULL AND tag_service_id IS NULL AND namespace_id = ? AND tag_id = ?;', ( len( hash_ids ) * direction, namespace_id, tag_id ) )
        
    
    def _UpdateAutocompleteTagCacheFromPendingTags( self, c, tag_service_id, namespace_id, tag_id, hash_ids, direction ):
        
        info = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' GROUP BY service_id;' ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( file_service_id, count ) in info ] )
        
        c.execute( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id IS NULL AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', ( len( hash_ids ) * direction, tag_service_id, namespace_id, tag_id ) )
        
    
    def _UpdateMappings( self, c, service_id, mappings_ids, deleted_mappings_ids ):
        
        namespace_ids_being_added = { namespace_id for ( namespace_id, tag_id, hash_ids ) in mappings_ids }
        tag_ids_being_added = { tag_id for ( namespace_id, tag_id, hash_ids ) in mappings_ids }
        
        hash_ids_lists = [ hash_ids for ( namespace_id, tag_id, hash_ids ) in mappings_ids ]
        hash_ids_being_added = { hash_id for hash_id in itertools.chain( *hash_ids_lists ) }
        
        existing_namespace_ids = { namespace_id for namespace_id in namespace_ids_being_added if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT namespace_id FROM mappings WHERE namespace_id = ? AND service_id = ? );', ( namespace_id, service_id ) ).fetchone() is not None }
        existing_tag_ids = { tag_id for tag_id in tag_ids_being_added if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT tag_id FROM mappings WHERE tag_id = ? AND service_id = ? );', ( tag_id, service_id ) ).fetchone() is not None }
        existing_hash_ids = { hash_id for hash_id in hash_ids_being_added if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT hash_id FROM mappings WHERE hash_id = ? AND service_id = ? );', ( hash_id, service_id ) ).fetchone() is not None }
        
        #existing_namespace_ids = { id for id in c.execute( 'SELECT namespace_id FROM mappings WHERE service_id = ? AND namespace_id IN ' + HC.SplayListForDB( namespace_ids_being_added ) + ';', ( service_id, ) ) }
        #existing_tag_ids = { id for id in c.execute( 'SELECT tag_id FROM mappings WHERE service_id = ? AND tag_id IN ' + HC.SplayListForDB( tag_ids_being_added ) + ';', ( service_id, ) ) }
        #existing_hash_ids = { id for id in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids_being_added ) + ';', ( service_id, ) ) }
        
        #existing_namespace_ids = { id for ( id, ) in c.execute( 'SELECT namespace_id FROM mappings WHERE service_id = ?;', ( service_id, ) ) }
        #existing_tag_ids = { id for ( id, ) in c.execute( 'SELECT tag_id FROM mappings WHERE service_id = ?;', ( service_id, ) ) }
        #existing_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ?;', ( service_id, ) ) }
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = set( hash_ids )
            
            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, namespace_id, tag_id ) ) }
            
            hash_ids.difference_update( invalid_hash_ids )
            
            if len( hash_ids ) > 0:
                
                num_mappings = len( hash_ids )
                
                namespace_added = namespace_id not in existing_namespace_ids
                tag_added = tag_id not in existing_tag_ids
                num_new_files = len( hash_ids - existing_hash_ids )
                
                existing_namespace_ids.add( namespace_id )
                existing_tag_ids.add( tag_id )
                existing_hash_ids.update( hash_ids )
                
                c.executemany( 'INSERT OR IGNORE INTO mappings VALUES ( ?, ?, ?, ? );', [ ( service_id, namespace_id, tag_id, hash_id ) for hash_id in hash_ids ] )
                
                self._UpdateAutocompleteTagCacheFromCurrentTags( c, service_id, namespace_id, tag_id, hash_ids, 1 )
                
                splayed_hash_ids = HC.SplayListForDB( hash_ids )
                
                c.execute( 'DELETE FROM deleted_mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, namespace_id, tag_id ) )
                
                num_deleted_mappings_revoked = c.rowcount
                
                actual_hash_ids_i_can_delete = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM pending_mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, namespace_id, tag_id ) ) ]
                
                c.execute( 'DELETE FROM pending_mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( actual_hash_ids_i_can_delete ) + ';', ( service_id, namespace_id, tag_id ) )
                
                self._UpdateAutocompleteTagCacheFromPendingTags( c, service_id, namespace_id, tag_id, actual_hash_ids_i_can_delete, -1 )
                
                service_info_updates = []
                
                service_info_updates.append( ( num_mappings, service_id, HC.SERVICE_INFO_NUM_MAPPINGS ) )
                if num_deleted_mappings_revoked > 0: service_info_updates.append( ( num_deleted_mappings_revoked, service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
                if namespace_added: service_info_updates.append( ( 1, service_id, HC.SERVICE_INFO_NUM_NAMESPACES ) )
                if tag_added: service_info_updates.append( ( 1, service_id, HC.SERVICE_INFO_NUM_TAGS ) )
                if num_new_files > 0: service_info_updates.append( ( num_new_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                
                c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
                
            
        
        for ( namespace_id, tag_id, hash_ids ) in deleted_mappings_ids:
            
            c.executemany( 'INSERT OR IGNORE INTO deleted_mappings ( service_id, namespace_id, tag_id, hash_id ) VALUES ( ?, ?, ?, ? );', [ ( service_id, namespace_id, tag_id, hash_id ) for hash_id in hash_ids ] )
            
            service_info_updates = []
            
            num_deleted_mappings = len( hash_ids )
            
            service_info_updates.append( ( num_deleted_mappings, service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
            
            removeable_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, namespace_id, tag_id ) ) }
            
            if len( removeable_hash_ids ) > 0:
                
                splayed_removeable_hash_ids = HC.SplayListForDB( hash_ids )
                
                c.execute( 'DELETE FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_removeable_hash_ids + ';', ( service_id, namespace_id, tag_id ) )
                
                number_existing_mappings_actually_removed = c.rowcount
                
                self._UpdateAutocompleteTagCacheFromCurrentTags( c, service_id, namespace_id, tag_id, removeable_hash_ids, -1 )
                
                c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + splayed_removeable_hash_ids + ';', ( service_id, namespace_id, tag_id ) )
                
                ( result, ) = c.execute( 'SELECT EXISTS ( SELECT 1 FROM mappings WHERE service_id = ? AND namespace_id = ? );', ( service_id, namespace_id, ) ).fetchone()
                
                namespace_removed = not bool( result )
                
                ( result, ) = c.execute( 'SELECT EXISTS ( SELECT 1 FROM mappings WHERE service_id = ? AND tag_id = ? );', ( service_id, tag_id, ) ).fetchone()
                
                tag_removed = not bool( result )
                
                remaining_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ?;', ( service_id, ) ) }
                
                num_files_removed = len( removeable_hash_ids - remaining_hash_ids )
                
                service_info_updates.append( ( -number_existing_mappings_actually_removed, service_id, HC.SERVICE_INFO_NUM_MAPPINGS ) )
                if namespace_removed: service_info_updates.append( ( -1, service_id, HC.SERVICE_INFO_NUM_NAMESPACES ) )
                if tag_removed: service_info_updates.append( ( -1, service_id, HC.SERVICE_INFO_NUM_TAGS ) )
                if num_files_removed > 0: service_info_updates.append( ( -num_files_removed, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                
            
            c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
        
        # now update the active mappings
        
        ( precedence, ) = c.execute( 'SELECT precedence FROM tag_service_precedence WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        higher_precedence_service_ids = [ id for ( id, ) in c.execute( 'SELECT service_id FROM tag_service_precedence WHERE precedence < ?;', ( precedence, ) ) ]
        
        splayed_higher_precedence_service_ids = HC.SplayListForDB( higher_precedence_service_ids )
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_mappings WHERE service_id IN ' + splayed_higher_precedence_service_ids + ' AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( namespace_id, tag_id ) ) }
            
            valid_hash_ids = set( hash_ids ) - invalid_hash_ids
            
            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM active_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ';', ( namespace_id, tag_id ) ) }
            
            valid_hash_ids.difference_update( invalid_hash_ids )
            
            c.executemany( 'INSERT OR IGNORE INTO active_mappings VALUES ( ?, ?, ? );', [ ( namespace_id, tag_id, hash_id ) for hash_id in valid_hash_ids ] )
            
            self._UpdateAutocompleteTagCacheFromActiveCurrentTags( c, namespace_id, tag_id, valid_hash_ids, 1 )
            
            # now for removing any active pending
            
            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM pending_mappings WHERE service_id IN ' + splayed_higher_precedence_service_ids + ' AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( namespace_id, tag_id ) ) }
            
            valid_hash_ids = set( hash_ids ) - invalid_hash_ids
            
            actual_hash_ids_i_can_delete = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM active_pending_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ';', ( namespace_id, tag_id ) ) ]
            
            c.execute( 'DELETE FROM active_pending_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( actual_hash_ids_i_can_delete ) + ';', ( namespace_id, tag_id ) )
            
            self._UpdateAutocompleteTagCacheFromActivePendingTags( c, namespace_id, tag_id, actual_hash_ids_i_can_delete, -1 )
            
        
        for ( namespace_id, tag_id, hash_ids ) in deleted_mappings_ids:
            
            invalid_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id IN ' + splayed_higher_precedence_service_ids + ' AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( namespace_id, tag_id ) ) }
            
            valid_hash_ids = set( hash_ids ) - invalid_hash_ids
            
            actual_hash_ids_i_can_delete = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM active_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( valid_hash_ids ) + ';', ( namespace_id, tag_id ) ) ]
            
            c.execute( 'DELETE FROM active_mappings WHERE namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( actual_hash_ids_i_can_delete ) + ';', ( namespace_id, tag_id ) )
            
            self._UpdateAutocompleteTagCacheFromActiveCurrentTags( c, namespace_id, tag_id, actual_hash_ids_i_can_delete, -1 )
            
        
    
    def _UpdateServerServices( self, c, server_admin_service_identifier, edit_log ):
        
        server_admin_service_id = self._GetServiceId( c, server_admin_service_identifier )
        
        server_admin = self._GetService( c, server_admin_service_id )
        
        server_admin_credentials = server_admin.GetCredentials()
        
        access_key = server_admin_credentials.GetAccessKey()
        
        ( host, server_admin_port ) = server_admin_credentials.GetAddress()
        
        recalc_active_mappings = False
        
        for ( action, data ) in edit_log:
            
            if action == HC.ADD:
                
                server_service_identifier = data
                
                service_key = os.urandom( 32 )
                
                service_type = server_service_identifier.GetType()
                
                service_port = server_service_identifier.GetPort()
                
                service_name = HC.service_string_lookup[ service_type ] + ' at ' + host + ':' + str( service_port )
                
                client_service_identifier = HC.ClientServiceIdentifier( service_key, service_type, service_name )
                
                credentials = CC.Credentials( host, service_port, access_key )
                
                if service_type == HC.MESSAGE_DEPOT: extra_info = ( 'identity@' + service_name, 180, HydrusMessageHandling.GenerateNewPrivateKey(), True )
                else: extra_info = None
                
                self._AddService( c, client_service_identifier, credentials, extra_info )
                
            elif action == HC.EDIT:
                
                ( server_service_identifier, new_port ) = data
                
                current_port = server_service_identifier.GetPort()
                
                c.execute( 'UPDATE addresses SET port = ? WHERE host = ? AND port = ?;', ( new_port, host, current_port ) )
                
            elif action == HC.DELETE:
                
                server_service_identifier = data
                
                service_type = server_service_identifier.GetType()
                service_port = server_service_identifier.GetPort()
                
                service_info = c.execute( 'SELECT service_key, name FROM services, addresses USING ( service_id ) WHERE type = ? AND host = ? AND port = ?;', ( service_type, host, service_port ) ).fetchall()
                
                for ( service_key, name ) in service_info:
                    
                    client_service_identifier = HC.ClientServiceIdentifier( service_key, service_type, name )
                    
                    client_service_id = self._GetServiceId( c, client_service_identifier )
                    
                    c.execute( 'DELETE FROM services WHERE service_id = ?;', ( client_service_id, ) )
                    
                    self.pub( 'service_update_db', CC.ServiceUpdate( CC.SERVICE_UPDATE_RESET, client_service_identifier ) )
                    
                
                if len( names ) > 0: recalc_active_mappings = True
                
            
        
        if recalc_active_mappings: self._RecalcActiveMappings( c )
        
        self.pub( 'notify_new_pending' )
        self.pub( 'notify_new_services' )
        
    
    def _UpdateServices( self, c, edit_log ):
        
        recalc_active_mappings = False
        
        for ( action, details ) in edit_log:
            
            if action == 'add':
                
                ( service_identifier, credentials, extra_info ) = details
                
                self._AddService( c, service_identifier, credentials, extra_info )
                
            elif action == 'delete':
                
                service_identifier = details
                
                service_id = self._GetServiceId( c, service_identifier )
                
                c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
                
                self.pub( 'service_update_db', CC.ServiceUpdate( CC.SERVICE_UPDATE_RESET, service_identifier ) )
                
                service_type = service_identifier.GetType()
                
                if service_type == HC.TAG_REPOSITORY: recalc_active_mappings = True
                
            elif action == 'edit':
                
                ( old_service_identifier, ( new_service_identifier, credentials, extra_info ) ) = details
                
                service_type = old_service_identifier.GetType()
                
                service_id = self._GetServiceId( c, old_service_identifier )
                
                name = new_service_identifier.GetName()
                
                c.execute( 'UPDATE services SET name = ? WHERE service_id = ?;', ( name, service_id ) )
                
                if service_type in HC.REMOTE_SERVICES:
                    
                    ( host, port ) = credentials.GetAddress()
                    
                    c.execute( 'UPDATE addresses SET host = ?, port = ?, last_error = ? WHERE service_id = ?;', ( host, port, 0, service_id ) )
                    
                    if service_type in HC.RESTRICTED_SERVICES:
                        
                        ( account, ) = c.execute( 'SELECT account FROM accounts WHERE service_id = ?;', ( service_id, ) ).fetchone()
                        
                        account.MakeStale()
                        
                        if credentials.HasAccessKey(): access_key = credentials.GetAccessKey()
                        else: access_key = ''
                        
                        c.execute( 'UPDATE accounts SET access_key = ?, account = ? WHERE service_id = ?;', ( sqlite3.Binary( access_key ), account, service_id ) )
                        
                    
                
                if service_type == HC.MESSAGE_DEPOT:
                    
                    ( identity_name, check_period, private_key, receive_anon ) = extra_info
                    
                    contact_id = self._GetContactId( c, service_id )
                    
                    result = c.execute( 'SELECT 1 FROM contacts WHERE name = ? AND contact_id != ?;', ( identity_name, contact_id ) ).fetchone()
                    
                    while result is not None:
                        
                        identity_name += str( random.randint( 0, 9 ) )
                        
                        result = c.execute( 'SELECT 1 FROM contacts WHERE name = ?;', ( identity_name, ) ).fetchone()
                        
                    
                    c.execute( 'UPDATE contacts SET name = ?, host = ?, port = ? WHERE contact_id = ?;', ( identity_name, host, port, contact_id ) )
                    
                    c.execute( 'UPDATE message_depots SET check_period = ?, private_key = ?, receive_anon = ? WHERE service_id = ?;', ( check_period, private_key, receive_anon, service_id ) )
                    
                elif service_type in ( HC.RATING_LIKE_REPOSITORY, HC.LOCAL_RATING_LIKE ):
                    
                    ( like, dislike ) = extra_info
                    
                    c.execute( 'UPDATE ratings_like SET like = ?, dislike = ? WHERE service_id = ?;', ( like, dislike, service_id ) )
                    
                elif service_type in ( HC.RATING_LIKE_REPOSITORY, HC.LOCAL_RATING_NUMERICAL ):
                    
                    ( lower, upper ) = extra_info
                    
                    c.execute( 'UPDATE ratings_numerical SET lower = ?, upper = ? WHERE service_id = ?;', ( lower, upper, service_id ) )
                    
                
            
        
        if recalc_active_mappings: self._RecalcActiveMappings( c )
        
        self.pub( 'notify_new_pending' )
        self.pub( 'notify_new_services' )
        
    
    def _UploadPending( self, c, service_identifier, job_key, cancel_event = threading.Event() ):
        
        try:
            
            service_id = self._GetServiceId( c, service_identifier )
            
            service_type = service_identifier.GetType()
            
            service_name = service_identifier.GetName()
            
            repository = self._GetService( c, service_id )
            
            account = repository.GetAccount()
            
            if service_type == HC.TAG_REPOSITORY:
                
                HC.pubsub.pub( 'progress_update', job_key, 0, 7, u'gathering pending mappings' )
                
                mappings_dict = {}
                mappings_hash_ids = set()
                
                if account.HasPermission( HC.POST_DATA ):
                    
                    mappings_dict = HC.BuildKeyToListDict( [ ( ( namespace_id, tag_id ), hash_id ) for ( namespace_id, tag_id, hash_id ) in c.execute( 'SELECT namespace_id, tag_id, hash_id FROM pending_mappings WHERE service_id = ?;', ( service_id, ) ) ] )
                    
                
                mappings = [ ( self._GetNamespaceTag( c, namespace_id, tag_id ), hash_ids ) for ( ( namespace_id, tag_id ), hash_ids ) in mappings_dict.items() ]
                
                mappings_hash_ids = HC.IntelligentMassUnion( mappings_dict.values() )
                
                mappings_hash_ids_to_hashes = self._GetHashIdsToHashes( c, mappings_hash_ids )
                
                HC.pubsub.pub( 'progress_update', job_key, 1, 7, u'gathering petitioned mappings' )
                
                petitions_dict = {}
                petitions_hash_ids = set()
                
                if account.HasPermission( HC.POST_PETITIONS ):
                    
                    petitions_dict = HC.BuildKeyToListDict( [ ( ( reason_id, namespace_id, tag_id ), hash_id ) for ( reason_id, namespace_id, tag_id, hash_id ) in c.execute( 'SELECT reason_id, namespace_id, tag_id, hash_id FROM mapping_petitions WHERE service_id = ?;', ( service_id, ) ) ] )
                    
                
                petitions = [ ( self._GetReason( c, reason_id ), self._GetNamespaceTag( c, namespace_id, tag_id ), hash_ids ) for ( ( reason_id, namespace_id, tag_id ), hash_ids ) in petitions_dict.items() ]
                
                petitions_hash_ids = HC.IntelligentMassUnion( petitions_dict.values() )
                
                petitions_hash_ids_to_hashes = self._GetHashIdsToHashes( c, petitions_hash_ids )
                
                if len( mappings ) > 0 or len( petitions ) > 0:
                    
                    HC.pubsub.pub( 'progress_update', job_key, 2, 7, u'connecting to repository' )
                    
                    connection = repository.GetConnection()
                    
                    HC.pubsub.pub( 'progress_update', job_key, 3, 7, u'posting new mappings' )
                    
                    if len( mappings ) > 0:
                        
                        try:
                            
                            mappings_object = HC.ClientMappings( mappings, mappings_hash_ids_to_hashes )
                            
                            connection.Post( 'mappings', mappings = mappings_object )
                            
                        except Exception as e: raise Exception( 'Encountered an error while uploading public_mappings:' + os.linesep + unicode( e ) )
                        
                    
                    HC.pubsub.pub( 'progress_update', job_key, 4, 7, u'posting new petitions' )
                    
                    if len( petitions ) > 0:
                        
                        try:
                            
                            petitions_object = HC.ClientMappingPetitions( petitions, petitions_hash_ids_to_hashes )
                            
                            connection.Post( 'petitions', petitions = petitions_object )
                            
                        except Exception as e: raise Exception( 'Encountered an error while uploading petitions:' + os.linesep + unicode( e ) )
                        
                    
                    mappings_ids = [ ( namespace_id, tag_id, hash_ids ) for ( ( namespace_id, tag_id ), hash_ids ) in mappings_dict.items() ]
                    deleted_mappings_ids = [ ( namespace_id, tag_id, hash_ids ) for ( ( reason_id, namespace_id, tag_id ), hash_ids ) in petitions_dict.items() ]
                    
                    HC.pubsub.pub( 'progress_update', job_key, 5, 7, u'saving changes to local database' )
                    
                    self._UpdateMappings( c, service_id, mappings_ids, deleted_mappings_ids )
                    
                    num_mappings = sum( [ len( hash_ids ) for ( namespace_id, tag_id, hash_ids ) in mappings_ids ] )
                    num_deleted_mappings = sum( [ len( hash_ids ) for ( namespace_id, tag_id, hash_ids ) in deleted_mappings_ids ] )
                    
                    self.pub( 'log_message', 'upload mappings', 'uploaded ' + str( num_mappings ) + ' mappings to and deleted ' + str( num_deleted_mappings ) + ' mappings from ' + service_identifier.GetName() )
                    
                    content_updates = []
                    
                    content_updates += [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, self._GetHashes( c, hash_ids ), info = self._GetNamespaceTag( c, namespace_id, tag_id ) ) for ( namespace_id, tag_id, hash_ids ) in mappings_ids ]
                    content_updates += [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, self._GetHashes( c, hash_ids ), info = self._GetNamespaceTag( c, namespace_id, tag_id ) ) for ( namespace_id, tag_id, hash_ids ) in deleted_mappings_ids ]
                    
                    HC.pubsub.pub( 'progress_update', job_key, 6, 7, u'saving changes to gui' )
                    
                    self.pub( 'content_updates_data', content_updates )
                    self.pub( 'content_updates_gui', content_updates )
                    
                
                HC.pubsub.pub( 'progress_update', job_key, 7, 7, u'done!' )
                
            elif service_type == HC.FILE_REPOSITORY:
                
                uploads = []
                
                petitions = []
                
                HC.pubsub.pub( 'progress_update', job_key, 0, 1, u'gathering pending and petitioned file info' )
                
                if account.HasPermission( HC.POST_DATA ): uploads = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id_to = ?;', ( service_id, ) ) ]
                
                if account.HasPermission( HC.POST_PETITIONS ): petitions = HC.BuildKeyToListDict( c.execute( 'SELECT reason, hash FROM reasons, ( hashes, file_petitions USING ( hash_id ) ) USING ( reason_id ) WHERE service_id = ?;', ( service_id, ) ) ).items()
                
                num_uploads = len( uploads )
                num_petitions = len( petitions )
                
                if num_uploads > 0 or num_petitions > 0:
                    
                    HC.pubsub.pub( 'progress_update', job_key, 0, num_uploads + 4, u'connecting to repository' )
                    
                    connection = repository.GetConnection()
                    
                    if num_uploads > 0:
                        
                        error_messages = set()
                        
                        good_hash_ids = []
                        
                        for ( index, hash_id ) in enumerate( uploads ):
                            
                            HC.pubsub.pub( 'progress_update', job_key, index, num_uploads + 4, u'Uploading file ' + HC.ConvertIntToPrettyString( index + 1 ) + ' of ' + HC.ConvertIntToPrettyString( num_uploads ) )
                            
                            if cancel_event.isSet(): break
                            
                            try:
                                
                                ( hash, ) = self._GetHashes( c, ( hash_id, ) )
                                
                                file = self._GetFile( hash )
                                
                                connection.Post( 'file', file = file )
                                
                                good_hash_ids.append( hash_id )
                                
                            except Exception as e: error_messages.add( unicode( e ) )
                            
                        
                        splayed_good_hash_ids = HC.SplayListForDB( good_hash_ids )
                        
                        HC.pubsub.pub( 'progress_update', job_key, num_uploads, num_uploads + 4, u'saving changes to local database' )
                        
                        files_info_rows = c.execute( 'SELECT ?, hash_id, size, mime, ?, width, height, duration, num_frames, num_words FROM files_info WHERE service_id = ? AND hash_id IN ' + splayed_good_hash_ids + ';', ( service_id, int( time.time() ), self._local_file_service_id ) ).fetchall()
                        
                        self._AddFiles( c, files_info_rows )
                        
                        if len( error_messages ) > 0: raise Exception( 'Errors were encountered while trying to upload files to ' + service_name + ':' + os.linesep + os.linesep.join( error_messages ) )
                        
                        HC.pubsub.pub( 'progress_update', job_key, num_uploads + 2, num_uploads + 4, u'saving changes to gui' )
                        
                        if len( good_hash_ids ) > 0:
                            self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, self._GetHashes( c, good_hash_ids ) ) ] )
                            self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, service_identifier, self._GetHashes( c, good_hash_ids ) ) ] )
                        
                    
                    if num_petitions > 0:
                        
                        try:
                            
                            HC.pubsub.pub( 'progress_update', job_key, num_uploads + 3, num_uploads + 4, u'uploading petitions' )
                            
                            petitions_object = HC.ClientFilePetitions( petitions )
                            
                            connection.Post( 'petitions', petitions = petitions_object )
                            
                            hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_petitions WHERE service_id = ?;', ( service_id, ) ) ]
                            
                            self._DeleteFiles( c, service_id, hash_ids )
                            
                            self.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, self._GetHashes( c, hash_ids ) ) ] )
                            self.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_DELETE, service_identifier, self._GetHashes( c, hash_ids ) ) ] )
                            
                        except Exception as e: raise Exception( 'Encountered an error while trying to uploads petitions to '+ service_name + ':' + os.linesep + unicode( e ) )
                        
                    
                    self.pub( 'log_message', 'upload files', 'uploaded ' + str( num_uploads ) + ' files to and deleted ' + str( num_petitions ) + ' files from ' + service_identifier.GetName() )
                    
                
                HC.pubsub.pub( 'progress_update', job_key, num_uploads + 4, num_uploads + 4, u'done!' )
                
            
            self.pub( 'notify_new_pending' )
            
        except Exception as e:
            
            time.sleep( 2 )
            
            HC.pubsub.pub( 'progress_update', job_key, 0, 1, 'error: ' + unicode( e ) )
            
            time.sleep( 3 )
            
            HC.pubsub.pub( 'progress_update', job_key, 1, 1, 'quitting' )
            
            raise
            
        
    
class DB( ServiceDB ):
    
    def __init__( self ):
        
        self._db_path = HC.DB_DIR + os.path.sep + 'client.db'
        
        self._jobs = Queue.PriorityQueue()
        self._pubsubs = []
        
        self._InitDB()
        
        temp_dir = HC.TEMP_DIR
        
        try:
            if os.path.exists( temp_dir ): shutil.rmtree( temp_dir, ignore_errors = True )
        except: pass
        
        try:
            if not os.path.exists( temp_dir ): os.mkdir( temp_dir )
        except: pass
        
        # clean up if last connection closed badly
        ( db, c ) = self._GetDBCursor()
        
        db.close()
        # ok should be fine
        
        ( db, c ) = self._GetDBCursor()
        
        self._UpdateDB( c )
        
        # ####### put a temp db update here! ######
        
        # ###### ~~~~~~~~~~~~~~~~~~~~~~~~~~~ ######
        
        ( self._local_file_service_id, ) = c.execute( 'SELECT service_id FROM services WHERE type = ?;', ( HC.LOCAL_FILE, ) ).fetchone()
        
        ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
        
        self._tag_service_precedence = self._GetTagServicePrecedence( c )
        
        if not self._CheckPassword(): raise HC.PermissionException( 'No password!' )
        
        threading.Thread( target = self.MainLoop, name = 'Database Main Loop' ).start()
        
    
    def _InitPostGUI( self ):
        
        port = HC.DEFAULT_LOCAL_FILE_PORT
        
        local_file_server_service_identifier = HC.ServerServiceIdentifier( HC.LOCAL_FILE, port )
        
        self._server = HydrusServer.HydrusHTTPServer( local_file_server_service_identifier )
        
        server_thread = threading.Thread( target=self._server.serve_forever )
        server_thread.start()
        
        connection = httplib.HTTPConnection( '127.0.0.1:' + str( port ) )
        
        try:
            
            connection.connect()
            connection.close()
            
        except: print( 'Could not bind the client to port ' + str( port ) )
        
        HC.DAEMONWorker( 'DownloadFiles', self.DAEMONDownloadFiles, ( 'notify_new_downloads', 'notify_new_permissions' ) )
        HC.DAEMONWorker( 'DownloadThumbnails', self.DAEMONDownloadThumbnails, ( 'notify_new_permissions', 'notify_new_thumbnails' ) )
        HC.DAEMONWorker( 'ResizeThumbnails', self.DAEMONResizeThumbnails, () )
        HC.DAEMONWorker( 'SynchroniseAccounts', self.DAEMONSynchroniseAccounts, ( 'notify_new_services', 'permissions_are_stale' ) )
        HC.DAEMONWorker( 'SynchroniseMessages', self.DAEMONSynchroniseMessages, ( 'notify_new_permissions', 'notify_check_messages' ), period = 60 )
        HC.DAEMONWorker( 'SynchroniseRepositories', self.DAEMONSynchroniseRepositories, ( 'notify_new_permissions', ) )
        HC.DAEMONQueue( 'FlushRepositoryUpdates', self.DAEMONFlushServiceUpdates, 'service_update_db', period = 2 )
        
    
    def _CheckPassword( self ):
        
        if self._options[ 'password' ] is not None:
            
            while True:
                
                with wx.PasswordEntryDialog( None, 'Enter your password', 'Enter password' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        if hashlib.sha256( dlg.GetValue() ).digest() == self._options[ 'password' ]: return True
                        else: continue
                        
                    else: return False
                    
                
            
        else: return True
        
    
    def _GetDBCursor( self ):
        
        db = sqlite3.connect( self._db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        db.create_function( 'hydrus_hamming', 2, HydrusImageHandling.GetHammingDistance )
        
        c = db.cursor()
        
        c.execute( 'PRAGMA cache_size = 10000;' )
        c.execute( 'PRAGMA foreign_keys = ON;' )
        c.execute( 'PRAGMA recursive_triggers = ON;' )
        
        return ( db, c )
        
    
    def _GetBoorus( self, c ):
        
        boorus = [ booru for ( booru, ) in c.execute( 'SELECT booru FROM boorus;' ) ]
        
        return boorus
        
    
    def _GetImageboards( self, c ):
        
        all_imageboards = []
        
        all_sites = c.execute( 'SELECT site_id, name FROM imageboard_sites;' ).fetchall()
        
        for ( site_id, name ) in all_sites:
            
            imageboards = [ imageboard for ( imageboard, ) in c.execute( 'SELECT imageboard FROM imageboards WHERE site_id = ? ORDER BY name;', ( site_id, ) ) ]
            
            all_imageboards.append( ( name, imageboards ) )
            
        
        return all_imageboards
        
    
    def _GetSiteId( self, c, name ):
        
        result = c.execute( 'SELECT site_id FROM imageboard_sites WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO imageboard_sites ( name ) VALUES ( ? );', ( name, ) )
            
            site_id = c.lastrowid
            
        else: ( site_id, ) = result
        
        return site_id
        
    
    def _InitDB( self ):
        
        if not os.path.exists( self._db_path ):
            
            if not os.path.exists( HC.CLIENT_FILES_DIR ): os.mkdir( HC.CLIENT_FILES_DIR )
            if not os.path.exists( HC.CLIENT_THUMBNAILS_DIR ): os.mkdir( HC.CLIENT_THUMBNAILS_DIR )
            
            ( db, c ) = self._GetDBCursor()
            
            c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
            c.execute( 'PRAGMA journal_mode=WAL;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, type INTEGER, name TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX services_service_key_index ON services ( service_key );' )
            
            c.execute( 'CREATE TABLE fourchan_pass ( token TEXT, pin TEXT, timeout INTEGER );' )
            
            c.execute( 'CREATE TABLE accounts ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, access_key BLOB_BYTES, account TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE active_mappings ( namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX active_mappings_tag_id_index ON active_mappings ( tag_id );' )
            c.execute( 'CREATE INDEX active_mappings_hash_id_index ON active_mappings ( hash_id );' )
            
            c.execute( 'CREATE TABLE active_pending_mappings ( namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX active_pending_mappings_tag_id_index ON active_pending_mappings ( tag_id );' )
            c.execute( 'CREATE INDEX active_pending_mappings_hash_id_index ON active_pending_mappings ( hash_id );' )
            
            c.execute( 'CREATE TABLE addresses ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, host TEXT, port INTEGER, last_error INTEGER );' )
            
            c.execute( 'CREATE TABLE autocomplete_tags_cache ( file_service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, tag_service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, current_count INTEGER, pending_count INTEGER, PRIMARY KEY ( file_service_id, tag_service_id, namespace_id, tag_id ) );' )
            c.execute( 'CREATE INDEX autocomplete_tags_cache_tag_service_id_namespace_id_tag_id_index ON autocomplete_tags_cache ( tag_service_id, namespace_id, tag_id );' )
            
            c.execute( 'CREATE TABLE boorus ( name TEXT PRIMARY KEY, booru TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE contacts ( contact_id INTEGER PRIMARY KEY, contact_key BLOB_BYTES, public_key TEXT, name TEXT, host TEXT, port INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_name_index ON contacts ( name );' )
            
            c.execute( 'CREATE VIRTUAL TABLE conversation_subjects USING fts4( subject );' )
            
            c.execute( 'CREATE TABLE deleted_files ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            
            c.execute( 'CREATE TABLE deleted_mappings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX deleted_mappings_hash_id_index ON deleted_mappings ( hash_id );' )
            
            c.execute( 'CREATE TABLE existing_tags ( namespace_id INTEGER, tag_id INTEGER, PRIMARY KEY( namespace_id, tag_id ) );' )
            c.execute( 'CREATE INDEX existing_tags_tag_id_index ON existing_tags ( tag_id );' )
            
            c.execute( 'CREATE TABLE favourite_custom_filter_actions ( name TEXT, actions TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE file_inbox ( hash_id INTEGER PRIMARY KEY );' )
            
            c.execute( 'CREATE TABLE files_info ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, size INTEGER, mime INTEGER, timestamp INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX files_info_hash_id ON files_info ( hash_id );' )
            
            c.execute( 'CREATE TABLE file_transfers ( service_id_from INTEGER, service_id_to INTEGER REFERENCES services( service_id ) ON DELETE CASCADE, hash_id INTEGER, PRIMARY KEY( service_id_from, service_id_to, hash_id ), FOREIGN KEY( service_id_from, hash_id ) REFERENCES files_info ON DELETE CASCADE );' )
            c.execute( 'CREATE INDEX file_transfers_service_id_to ON file_transfers ( service_id_to );' )
            c.execute( 'CREATE INDEX file_transfers_hash_id ON file_transfers ( hash_id );' )
            
            c.execute( 'CREATE TABLE file_petitions ( service_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, hash_id, reason_id ), FOREIGN KEY( service_id, hash_id ) REFERENCES files_info ON DELETE CASCADE );' )
            c.execute( 'CREATE INDEX file_petitions_hash_id_index ON file_petitions ( hash_id );' )
            
            c.execute( 'CREATE TABLE hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES );' )
            c.execute( 'CREATE UNIQUE INDEX hashes_hash_index ON hashes ( hash );' )
            
            c.execute( 'CREATE TABLE hydrus_sessions ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, expiry INTEGER );' )
            
            c.execute( 'CREATE TABLE imageboard_sites ( site_id INTEGER PRIMARY KEY, name TEXT );', )
            
            c.execute( 'CREATE TABLE imageboards ( site_id INTEGER, name TEXT, imageboard TEXT_YAML, PRIMARY KEY ( site_id, name ) );', )
            
            c.execute( 'CREATE TABLE local_hashes ( hash_id INTEGER PRIMARY KEY, md5 BLOB_BYTES, sha1 BLOB_BYTES );' )
            c.execute( 'CREATE INDEX local_hashes_md5_index ON local_hashes ( md5 );' )
            c.execute( 'CREATE INDEX local_hashes_sha1_index ON local_hashes ( sha1 );' )
            
            c.execute( 'CREATE TABLE local_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, rating REAL, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX local_ratings_hash_id_index ON local_ratings ( hash_id );' )
            c.execute( 'CREATE INDEX local_ratings_rating_index ON local_ratings ( rating );' )
            
            c.execute( 'CREATE TABLE mappings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX mappings_hash_id_index ON mappings ( hash_id );' )
            c.execute( 'CREATE INDEX mappings_service_id_tag_id_index ON mappings ( service_id, tag_id );' )
            c.execute( 'CREATE INDEX mappings_service_id_hash_id_index ON mappings ( service_id, hash_id );' )
            
            c.execute( 'CREATE TABLE mapping_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id, reason_id ) );' )
            c.execute( 'CREATE INDEX mapping_petitions_hash_id_index ON mapping_petitions ( hash_id );' )
            
            c.execute( 'CREATE TABLE message_attachments ( message_id INTEGER PRIMARY KEY REFERENCES message_keys ON DELETE CASCADE, hash_id INTEGER );' )
            
            c.execute( 'CREATE TABLE message_depots ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, contact_id INTEGER, last_check INTEGER, check_period INTEGER, private_key TEXT, receive_anon INTEGER_BOOLEAN );' )
            c.execute( 'CREATE UNIQUE INDEX message_depots_contact_id_index ON message_depots ( contact_id );' )
            
            c.execute( 'CREATE TABLE message_destination_map ( message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, contact_id_to INTEGER, status_id INTEGER, PRIMARY KEY ( message_id, contact_id_to ) );' )
            c.execute( 'CREATE INDEX message_destination_map_contact_id_to_index ON message_destination_map ( contact_id_to );' )
            c.execute( 'CREATE INDEX message_destination_map_status_id_index ON message_destination_map ( status_id );' )
            
            c.execute( 'CREATE TABLE message_downloads ( service_id INTEGER REFERENCES services ON DELETE CASCADE, message_id INTEGER REFERENCES message_keys ON DELETE CASCADE );' )
            c.execute( 'CREATE INDEX message_downloads_service_id_index ON message_downloads ( service_id );' )
            
            c.execute( 'CREATE TABLE message_drafts ( message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, recipients_visible INTEGER_BOOLEAN );' )
            
            c.execute( 'CREATE TABLE message_inbox ( message_id INTEGER PRIMARY KEY REFERENCES message_keys ON DELETE CASCADE );' )
            
            c.execute( 'CREATE TABLE message_keys ( message_id INTEGER PRIMARY KEY, message_key BLOB_BYTES );' )
            c.execute( 'CREATE INDEX message_keys_message_key_index ON message_keys ( message_key );' )
            
            c.execute( 'CREATE VIRTUAL TABLE message_bodies USING fts4( body );' )
            
            c.execute( 'CREATE TABLE incoming_message_statuses ( message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, contact_key BLOB_BYTES, status_id INTEGER, PRIMARY KEY ( message_id, contact_key ) );' )
            
            c.execute( 'CREATE TABLE messages ( conversation_id INTEGER REFERENCES message_keys ( message_id ) ON DELETE CASCADE, message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, contact_id_from INTEGER, timestamp INTEGER, PRIMARY KEY( conversation_id, message_id ) );' )
            c.execute( 'CREATE UNIQUE INDEX messages_message_id_index ON messages ( message_id );' )
            c.execute( 'CREATE INDEX messages_contact_id_from_index ON messages ( contact_id_from );' )
            c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
            
            c.execute( 'CREATE TABLE namespaces ( namespace_id INTEGER PRIMARY KEY, namespace TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX namespaces_namespace_index ON namespaces ( namespace );' )
            
            c.execute( 'CREATE TABLE news ( service_id INTEGER REFERENCES services ON DELETE CASCADE, post TEXT, timestamp INTEGER );' )
            
            c.execute( 'CREATE TABLE options ( options TEXT_YAML );', )
            
            c.execute( 'CREATE TABLE pending_mappings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX pending_mappings_hash_id_index ON pending_mappings ( hash_id );' )
            c.execute( 'CREATE INDEX pending_mappings_service_id_tag_id_index ON pending_mappings ( service_id, tag_id );' )
            c.execute( 'CREATE INDEX pending_mappings_service_id_hash_id_index ON pending_mappings ( service_id, hash_id );' )
            
            c.execute( 'CREATE TABLE perceptual_hashes ( hash_id INTEGER PRIMARY KEY, phash BLOB_BYTES );' )
            
            c.execute( 'CREATE TABLE pixiv_account ( pixiv_id TEXT, password TEXT );' )
            
            c.execute( 'CREATE TABLE ratings_filter ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, min REAL, max REAL, PRIMARY KEY( service_id, hash_id ) );' )
            
            c.execute( 'CREATE TABLE ratings_numerical ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, lower INTEGER, upper INTEGER );' )
            
            c.execute( 'CREATE TABLE ratings_like ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, like TEXT, dislike TEXT );' )
            
            c.execute( 'CREATE TABLE reasons ( reason_id INTEGER PRIMARY KEY, reason TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX reasons_reason_index ON reasons ( reason );' )
            
            c.execute( 'CREATE TABLE remote_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, count INTEGER, rating REAL, score REAL, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX remote_ratings_hash_id_index ON remote_ratings ( hash_id );' )
            c.execute( 'CREATE INDEX remote_ratings_rating_index ON remote_ratings ( rating );' )
            c.execute( 'CREATE INDEX remote_ratings_score_index ON remote_ratings ( score );' )
            
            c.execute( 'CREATE TABLE repositories ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, first_begin INTEGER, next_begin INTEGER );' )
            
            c.execute( 'CREATE TABLE service_info ( service_id INTEGER REFERENCES services ON DELETE CASCADE, info_type INTEGER, info INTEGER, PRIMARY KEY ( service_id, info_type ) );' )
            
            c.execute( 'CREATE TABLE shutdown_timestamps ( shutdown_type INTEGER PRIMARY KEY, timestamp INTEGER );' )
            
            c.execute( 'CREATE TABLE statuses ( status_id INTEGER PRIMARY KEY, status TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX statuses_status_index ON statuses ( status );' )
            
            c.execute( 'CREATE TABLE tag_service_precedence ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, precedence INTEGER );' )
            
            c.execute( 'CREATE TABLE tags ( tag_id INTEGER PRIMARY KEY, tag TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX tags_tag_index ON tags ( tag );' )
            
            c.execute( 'CREATE TABLE urls ( url TEXT PRIMARY KEY, hash_id INTEGER );' )
            c.execute( 'CREATE INDEX urls_hash_id ON urls ( hash_id );' )
            
            c.execute( 'CREATE TABLE version ( version INTEGER );' )
            
            # inserts
            
            account = CC.GetUnknownAccount()
            account.MakeStale()
            
            c.execute( 'INSERT INTO services ( service_key, type, name ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( 'local files' ), HC.LOCAL_FILE, 'local files' ) )
            c.execute( 'INSERT INTO services ( service_key, type, name ) VALUES ( ?, ?, ? );', ( sqlite3.Binary( 'local tags' ), HC.LOCAL_TAG, 'local tags' ) )
            
            local_tag_service_id = c.lastrowid
            
            c.execute( 'INSERT INTO tag_service_precedence ( service_id, precedence ) VALUES ( ?, ? );', ( local_tag_service_id, 0 ) )
            
            c.executemany( 'INSERT INTO boorus VALUES ( ?, ? );', [ ( booru.GetName(), booru ) for booru in CC.DEFAULT_BOORUS ] )
            
            for ( site_name, imageboards ) in CC.DEFAULT_IMAGEBOARDS:
                
                site_id = self._GetSiteId( c, site_name )
                
                c.executemany( 'INSERT INTO imageboards VALUES ( ?, ?, ? );', [ ( site_id, imageboard.GetName(), imageboard ) for imageboard in imageboards ] )
                
            
            c.execute( 'INSERT INTO namespaces ( namespace_id, namespace ) VALUES ( ?, ? );', ( 1, '' ) )
            
            CLIENT_DEFAULT_OPTIONS = {}
            
            CLIENT_DEFAULT_OPTIONS[ 'default_sort' ] = 0
            CLIENT_DEFAULT_OPTIONS[ 'default_collect' ] = None
            CLIENT_DEFAULT_OPTIONS[ 'export_path' ] = 'export'
            CLIENT_DEFAULT_OPTIONS[ 'hpos' ] = 400
            CLIENT_DEFAULT_OPTIONS[ 'vpos' ] = 700
            CLIENT_DEFAULT_OPTIONS[ 'exclude_deleted_files' ] = False
            CLIENT_DEFAULT_OPTIONS[ 'thumbnail_cache_size' ] = 100 * 1048576
            CLIENT_DEFAULT_OPTIONS[ 'preview_cache_size' ] = 25 * 1048576
            CLIENT_DEFAULT_OPTIONS[ 'fullscreen_cache_size' ] = 200 * 1048576
            CLIENT_DEFAULT_OPTIONS[ 'thumbnail_dimensions' ] = [ 150, 125 ]
            CLIENT_DEFAULT_OPTIONS[ 'password' ] = None
            CLIENT_DEFAULT_OPTIONS[ 'num_autocomplete_chars' ] = 1
            CLIENT_DEFAULT_OPTIONS[ 'gui_capitalisation' ] = False
            
            system_predicates = {}
            
            system_predicates[ 'age' ] = ( 0, 0, 0, 7 )
            system_predicates[ 'duration' ] = ( 3, 0, 0 )
            system_predicates[ 'height' ] = ( 1, 1200 )
            system_predicates[ 'limit' ] = 600
            system_predicates[ 'mime' ] = ( 0, 0 )
            system_predicates[ 'num_tags' ] = ( 0, 4 )
            system_predicates[ 'local_rating_numerical' ] = ( 0, 3 )
            system_predicates[ 'local_rating_like' ] = 0
            system_predicates[ 'ratio' ] = ( 0, 16, 9 )
            system_predicates[ 'size' ] = ( 0, 200, 1 )
            system_predicates[ 'width' ] = ( 1, 1920 )
            system_predicates[ 'num_words' ] = ( 0, 30000 )
            
            CLIENT_DEFAULT_OPTIONS[ 'file_system_predicates' ] = system_predicates
            
            default_namespace_colours = {}
            
            default_namespace_colours[ 'system' ] = ( 153, 101, 21 )
            default_namespace_colours[ 'creator' ] = ( 170, 0, 0 )
            default_namespace_colours[ 'character' ] = ( 0, 170, 0 )
            default_namespace_colours[ 'series' ] = ( 170, 0, 170 )
            default_namespace_colours[ None ] = ( 114, 160, 193 )
            default_namespace_colours[ '' ] = ( 0, 111, 250 )
            
            CLIENT_DEFAULT_OPTIONS[ 'namespace_colours' ] = default_namespace_colours
            
            default_sort_by_choices = []
            
            default_sort_by_choices.append( ( 'namespaces', [ 'series', 'creator', 'title', 'volume', 'chapter', 'page' ] ) )
            default_sort_by_choices.append( ( 'namespaces', [ 'creator', 'series', 'title', 'volume', 'chapter', 'page' ] ) )
            
            CLIENT_DEFAULT_OPTIONS[ 'sort_by' ] = default_sort_by_choices
            CLIENT_DEFAULT_OPTIONS[ 'show_all_tags_in_autocomplete' ] = True
            CLIENT_DEFAULT_OPTIONS[ 'fullscreen_borderless' ] = True
            
            shortcuts = {}
            
            shortcuts[ wx.ACCEL_NORMAL ] = {}
            shortcuts[ wx.ACCEL_CTRL ] = {}
            shortcuts[ wx.ACCEL_ALT ] = {}
            shortcuts[ wx.ACCEL_SHIFT ] = {}
            
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F3 ] = 'manage_tags'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F4 ] = 'manage_ratings'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F5 ] = 'refresh'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F7 ] = 'archive'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F11 ] = 'ratings_filter'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F12 ] = 'filter'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F9 ] = 'new_page'
            shortcuts[ wx.ACCEL_NORMAL ][ ord( 'F' ) ] = 'fullscreen_switch'
            shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_F7 ] = 'inbox'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'B' ) ] = 'frame_back'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'N' ) ] = 'frame_next'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'T' ) ] = 'new_page'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'W' ) ] = 'close_page'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'R' ) ] = 'show_hide_splitters'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'S' ) ] = 'set_search_focus'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'M' ) ] = 'set_media_focus'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'I' ) ] = 'synchronised_wait_switch'
            
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_UP ] = 'previous'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_LEFT ] = 'previous'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_UP ] = 'previous'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_LEFT ] = 'previous'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_PAGEUP ] = 'previous'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_PAGEUP ] = 'previous'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_DOWN ] = 'next'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_RIGHT ] = 'next'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_DOWN ] = 'next'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_RIGHT ] = 'next'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_PAGEDOWN ] = 'next'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_PAGEDOWN ] = 'next'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_HOME ] = 'first'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_HOME ] = 'first'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_END ] = 'last'
            shortcuts[ wx.ACCEL_CTRL ][ wx.WXK_NUMPAD_END ] = 'last'
            
            CLIENT_DEFAULT_OPTIONS[ 'shortcuts' ] = shortcuts
            
            CLIENT_DEFAULT_OPTIONS[ 'default_tag_repository' ] = CC.LOCAL_TAG_SERVICE_IDENTIFIER
            CLIENT_DEFAULT_OPTIONS[ 'default_tag_sort' ] = CC.SORT_BY_LEXICOGRAPHIC_ASC
            
            c.execute( 'INSERT INTO options ( options ) VALUES ( ? );', ( CLIENT_DEFAULT_OPTIONS, ) )
            
            c.execute( 'INSERT INTO contacts ( contact_id, contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ?, ? );', ( 1, None, None, 'Anonymous', 'internet', 0 ) )
            
            with open( HC.STATIC_DIR + os.sep + 'contact - hydrus admin.yaml', 'rb' ) as f: hydrus_admin = yaml.safe_load( f.read() )
            
            ( public_key, name, host, port ) = hydrus_admin.GetInfo()
            
            contact_key = hydrus_admin.GetContactKey()
            
            c.execute( 'INSERT OR IGNORE INTO contacts ( contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ? );', ( sqlite3.Binary( contact_key ), public_key, name, host, port ) )
            
            c.execute( 'INSERT INTO version ( version ) VALUES ( ? );', ( HC.SOFTWARE_VERSION, ) )
            
            c.execute( 'COMMIT' )
            
        
    
    def _SaveOptions( self, c ):
        
        ( old_options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
        
        ( old_width, old_height ) = old_options[ 'thumbnail_dimensions' ]
        
        ( new_width, new_height ) = self._options[ 'thumbnail_dimensions' ]
        
        c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
        
        resize_thumbs = new_width != old_width or new_height != old_height
        
        if resize_thumbs:
            
            thumbnail_paths = [ path for path in dircache.listdir( HC.CLIENT_THUMBNAILS_DIR ) if path.endswith( '_resized' ) ]
            
            for path in thumbnail_paths: os.remove( HC.CLIENT_THUMBNAILS_DIR + os.path.sep + path )
            
            self.pub( 'thumbnail_resize' )
            
        
        self.pub( 'refresh_menu_bar' )
        self.pub( 'options_updated' )
        
    
    def _SetPassword( self, c, password ):
        
        if password is not None: self._options[ 'password' ] = hashlib.sha256( password ).digest()
        else: self._options[ 'password' ] = None
        
        self._SaveOptions( c )
        
    
    def _UpdateBoorus( self, c, edit_log ):
        
        for ( action, data ) in edit_log:
            
            if action == 'add':
                
                name = data
                
                booru = CC.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                
                c.execute( 'INSERT INTO boorus ( name, booru ) VALUES ( ?, ? );', ( name, booru ) )
                
            elif action == 'delete':
                
                name = data
                
                c.execute( 'DELETE FROM boorus WHERE name = ?;', ( name, ) )
                
            elif action == 'edit':
                
                ( name, booru ) = data
                
                c.execute( 'UPDATE boorus SET booru = ? WHERE name = ?;', ( booru, name ) )
                
            
        
    
    def _UpdateImageboards( self, c, site_edit_log ):
        
        for ( site_action, site_data ) in site_edit_log:
            
            if site_action == 'add':
                
                site_name = site_data
                
                self._GetSiteId( c, site_name )
                
            elif site_action == 'delete':
                
                site_name = site_data
                
                site_id = self._GetSiteId( c, site_name )
                
                c.execute( 'DELETE FROM imageboard_sites WHERE site_id = ?;', ( site_id, ) )
                c.execute( 'DELETE FROM imageboards WHERE site_id = ?;', ( site_id, ) )
                
            elif site_action == 'edit':
                
                ( site_name, edit_log ) = site_data
                
                site_id = self._GetSiteId( c, site_name )
                
                for ( action, data ) in edit_log:
                    
                    if action == 'add':
                        
                        name = data
                        
                        imageboard = CC.Imageboard( name, '', 60, [], {} )
                        
                        c.execute( 'INSERT INTO imageboards ( site_id, name, imageboard ) VALUES ( ?, ?, ? );', ( site_id, name, imageboard ) )
                        
                    elif action == 'delete':
                        
                        name = data
                        
                        c.execute( 'DELETE FROM imageboards WHERE site_id = ? AND name = ?;', ( site_id, name ) )
                        
                    elif action == 'edit':
                        
                        imageboard = data
                        
                        name = imageboard.GetName()
                        
                        c.execute( 'UPDATE imageboards SET imageboard = ? WHERE site_id = ? AND name = ?;', ( imageboard, site_id, name ) )
                        
                    
                
            
        
    
    def _UpdateDB( self, c ):
        
        ( version, ) = c.execute( 'SELECT version FROM version;' ).fetchone()
        
        if version < HC.SOFTWARE_VERSION:
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            try:
                
                self._UpdateDBOld( c, version )
                
                if version < 59:
                    
                    ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
                    
                    shortcuts = self._options[ 'shortcuts' ]
                    
                    shortcuts[ wx.ACCEL_NORMAL ][ ord( 'F' ) ] = 'fullscreen_switch'
                    
                    self._options[ 'fullscreen_borderless' ] = True
                    self._options[ 'default_collect' ] = None
                    
                    c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
                    
                
                if version < 60:
                    
                    c.execute( 'CREATE TABLE pixiv_account ( pixiv_id TEXT, password TEXT );' )
                    
                    c.execute( 'CREATE TABLE favourite_custom_filter_actions ( name TEXT, actions TEXT_YAML );' )
                    
                
                if version < 61:
                    
                    c.execute( 'CREATE TABLE hydrus_sessions ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, expiry INTEGER );' )
                    
                
                if version < 63:
                    
                    ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
                    
                    system_predicates = self._options[ 'file_system_predicates' ]
                    
                    ( sign, size, unit ) = system_predicates[ 'size' ]
                    
                    system_predicates[ 'size' ] = ( sign, size, 1 )
                    
                    system_predicates[ 'num_words' ] = ( 0, 30000 )
                    
                    c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
                    
                
                unknown_account = CC.GetUnknownAccount()
                
                unknown_account.MakeStale()
                
                c.execute( 'UPDATE accounts SET account = ?;', ( unknown_account, ) )
                
                c.execute( 'UPDATE version SET version = ?;', ( HC.SOFTWARE_VERSION, ) )
                
                c.execute( 'COMMIT' )
                
                wx.MessageBox( 'The client has updated successfully!' )
                
            except:
                
                c.execute( 'ROLLBACK' )
                
                print( traceback.format_exc() )
                
                raise Exception( 'Tried to update the client db, but something went wrong:' + os.linesep + traceback.format_exc() )
                
            
        
        self._UpdateDBOldPost( c, version )
        
    
    def _UpdateDBOld( self, c, version ):
        
        # upgrade to version 4 was too complicated, needs entire rebuild
        
        if version < 13:
            
            c.execute( 'ALTER TABLE public_tag_repository ADD COLUMN first_begin INTEGER;' )
            c.execute( 'ALTER TABLE file_repositories ADD COLUMN first_begin INTEGER;' )
            
            c.execute( 'UPDATE public_tag_repository SET first_begin = 0, next_begin = 0, last_error = 0;' )
            c.execute( 'DELETE FROM public_mappings;' )
            c.execute( 'DELETE FROM deleted_public_mappings;' )
            c.execute( 'DELETE FROM public_tag_repository_news;' )
            c.execute( 'DELETE FROM pending_public_mapping_petitions;' )
            
            c.execute( 'UPDATE file_repositories SET first_begin = 0, next_begin = 0, last_error = 0;' )
            c.execute( 'DELETE FROM remote_files;' )
            c.execute( 'DELETE FROM deleted_remote_files;' )
            c.execute( 'DELETE FROM file_repository_news;' )
            c.execute( 'DELETE FROM pending_file_petitions;' )
            c.execute( 'DELETE FROM file_downloads;' )
            
        
        if version < 16:
            
            c.execute( 'CREATE TABLE accounts ( service_id INTEGER, access_key BLOB_BYTES, account TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE addresses ( service_id INTEGER, host TEXT, port INTEGER, last_error INTEGER );' )
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, type INTEGER, name TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX services_type_name_index ON services ( type, name );' )
            
            c.execute( 'CREATE TABLE repositories ( service_id INTEGER PRIMARY KEY, first_begin INTEGER, next_begin INTEGER );' )
            
            c.execute( 'CREATE TABLE news ( service_id INTEGER, post TEXT, timestamp INTEGER );' )
            
            # mappings db
            
            c.execute( 'PRAGMA mappings_db.auto_vacuum = 1;' ) # full
            
            c.execute( 'CREATE TABLE mappings_db.deleted_mappings ( service_id INTEGER, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX mappings_db.deleted_mappings_hash_id_index ON deleted_mappings ( hash_id );' )
            
            c.execute( 'CREATE TABLE mappings_db.mapping_petitions ( service_id INTEGER, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id, reason_id ) );' )
            c.execute( 'CREATE INDEX mappings_db.mapping_petitions_hash_id_index ON mapping_petitions ( hash_id );' )
            
            c.execute( 'CREATE TABLE mappings_db.pending_mappings ( service_id INTEGER, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX mappings_db.pending_mappings_namespace_id_index ON pending_mappings ( namespace_id );' )
            c.execute( 'CREATE INDEX mappings_db.pending_mappings_tag_id_index ON pending_mappings ( tag_id );' )
            c.execute( 'CREATE INDEX mappings_db.pending_mappings_hash_id_index ON pending_mappings ( hash_id );' )
            
            c.execute( 'CREATE TABLE mappings_db.mappings ( service_id INTEGER, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX mappings_db.mappings_namespace_id_index ON mappings ( namespace_id );' )
            c.execute( 'CREATE INDEX mappings_db.mappings_tag_id_index ON mappings ( tag_id );' )
            c.execute( 'CREATE INDEX mappings_db.mappings_hash_id_index ON mappings ( hash_id );' )
            
            # active mappings db
            
            c.execute( 'PRAGMA active_mappings_db.auto_vacuum = 1;' ) # full
            
            c.execute( 'CREATE TABLE active_mappings_db.active_mappings ( namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX active_mappings_db.active_mappings_tag_id_index ON active_mappings ( tag_id );' )
            c.execute( 'CREATE INDEX active_mappings_db.active_mappings_hash_id_index ON active_mappings ( hash_id );' )
            
            # files info db
            
            c.execute( 'PRAGMA files_info_db.auto_vacuum = 1;' ) # full
            
            c.execute( 'CREATE TABLE files_info_db.deleted_files ( service_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            
            c.execute( 'CREATE TABLE files_info_db.files_info ( service_id INTEGER, hash_id INTEGER, size INTEGER, mime INTEGER, timestamp INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX files_info_db.files_info_hash_id ON files_info ( hash_id );' )
            
            c.execute( 'CREATE TABLE files_info_db.file_transfers ( service_id_from INTEGER, service_id_to INTEGER, hash_id INTEGER, PRIMARY KEY( service_id_from, service_id_to, hash_id ) );' )
            c.execute( 'CREATE INDEX files_info_db.file_transfers_service_id_to ON file_transfers ( service_id_to );' )
            c.execute( 'CREATE INDEX files_info_db.file_transfers_hash_id ON file_transfers ( hash_id );' )
            
            c.execute( 'CREATE TABLE files_info_db.file_petitions ( service_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, hash_id, reason_id ) );' )
            c.execute( 'CREATE INDEX files_info_db.file_petitions_hash_id_index ON file_petitions ( hash_id );' )
            
            c.execute( 'CREATE TABLE files_info_db.inbox ( hash_id INTEGER PRIMARY KEY );' )
            
            # thumbs dbs
            
            c.execute( 'CREATE TABLE thumbnails_db.thumbnails ( service_id INTEGER, hash_id INTEGER, thumbnail BLOB_BYTES, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE TABLE thumbnails_resized_db.thumbnails_resized ( service_id INTEGER, hash_id INTEGER, thumbnail BLOB_BYTES, PRIMARY KEY( service_id, hash_id ) );' )
            
            # copy over
            
            c.execute( 'INSERT INTO services SELECT file_repository_id, ?, name FROM file_repositories;', ( HC.FILE_REPOSITORY, ) )
            c.execute( 'INSERT INTO addresses SELECT file_repository_id, host, port, last_error FROM file_repositories;' )
            c.execute( 'INSERT INTO accounts SELECT file_repository_id, access_key, account FROM file_repositories;' )
            c.execute( 'INSERT INTO repositories SELECT file_repository_id, first_begin, next_begin FROM file_repositories;' )
            
            c.execute( 'INSERT INTO services ( type, name ) VALUES ( ?, ? );', ( HC.LOCAL_FILE, 'local' ) )
            
            local_service_id = c.lastrowid
            
            c.execute( 'INSERT INTO services ( type, name ) VALUES ( ?, ? );', ( HC.TAG_REPOSITORY, 'public tag repository' ) )
            
            public_tag_service_id = c.lastrowid
            
            c.execute( 'INSERT INTO addresses SELECT ?, host, port, last_error FROM public_tag_repository;', ( public_tag_service_id, ) )
            c.execute( 'INSERT INTO accounts SELECT ?, access_key, account FROM public_tag_repository;', ( public_tag_service_id, ) )
            c.execute( 'INSERT INTO repositories SELECT ?, first_begin, next_begin FROM public_tag_repository;', ( public_tag_service_id, ) )
            
            c.execute( 'INSERT INTO news SELECT file_repository_id, news, timestamp FROM file_repository_news;' )
            c.execute( 'INSERT INTO news SELECT ?, news, timestamp FROM public_tag_repository_news;', ( public_tag_service_id, ) )
            
            c.execute( 'INSERT INTO deleted_mappings SELECT ?, namespace_id, tag_id, hash_id FROM deleted_public_mappings;', ( public_tag_service_id, ) )
            c.execute( 'INSERT INTO mapping_petitions SELECT ?, namespace_id, tag_id, hash_id, reason_id FROM pending_public_mapping_petitions;', ( public_tag_service_id, ) )
            c.execute( 'INSERT INTO pending_mappings SELECT ?, namespace_id, tag_id, hash_id FROM pending_public_mappings;', ( public_tag_service_id, ) )
            c.execute( 'INSERT INTO mappings SELECT ?, namespace_id, tag_id, hash_id FROM public_mappings;', ( public_tag_service_id, ) )
            
            c.execute( 'INSERT INTO active_mappings SELECT namespace_id, tag_id, hash_id FROM mappings WHERE service_id = ?;', ( public_tag_service_id, ) )
            
            c.execute( 'INSERT INTO deleted_files SELECT ?, hash_id FROM deleted_local_files;', ( local_service_id, ) )
            c.execute( 'INSERT INTO deleted_files SELECT file_repository_id, hash_id FROM deleted_remote_files;' )
            c.execute( 'INSERT INTO files_info SELECT ?, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM local_files;', ( local_service_id, ) )
            c.execute( 'INSERT INTO files_info SELECT file_repository_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM remote_files;' )
            c.execute( 'INSERT INTO file_transfers SELECT file_repository_id, ?, hash_id FROM file_downloads;', ( local_service_id, ) )
            c.execute( 'INSERT INTO file_transfers SELECT ?, file_repository_id, hash_id FROM pending_files;', ( local_service_id, ) )
            c.execute( 'INSERT INTO file_petitions SELECT file_repository_id, reason_id, hash_id FROM pending_file_petitions;' )
            c.execute( 'INSERT INTO inbox SELECT hash_id FROM local_files WHERE inbox = ?;', ( True, ) )
            
            c.execute( 'INSERT INTO thumbnails SELECT file_repository_id, hash_id, thumbnail FROM remote_thumbnails;' )
            c.execute( 'INSERT INTO thumbnails SELECT ?, hash_id, thumbnail FROM local_thumbnails;', ( local_service_id, ) )
            c.execute( 'INSERT INTO thumbnails_resized SELECT file_repository_id, hash_id, thumbnail_resized FROM remote_thumbnails_resized;' )
            c.execute( 'INSERT INTO thumbnails_resized SELECT ?, hash_id, thumbnail_resized FROM local_thumbnails_resized;', ( local_service_id, ) )
            
            c.execute( 'DROP TABLE file_repositories;' )
            c.execute( 'DROP TABLE public_tag_repository;' )
            
            c.execute( 'DROP TABLE file_repository_news;' )
            c.execute( 'DROP TABLE public_tag_repository_news;' )
            
            c.execute( 'DROP TABLE deleted_public_mappings;' )
            c.execute( 'DROP TABLE pending_public_mapping_petitions;' )
            c.execute( 'DROP TABLE pending_public_mappings;' )
            c.execute( 'DROP TABLE public_mappings;' )
            
            c.execute( 'DROP TABLE main.deleted_local_files;' )
            c.execute( 'DROP TABLE main.deleted_remote_files;' )
            c.execute( 'DROP TABLE main.file_downloads;' )
            c.execute( 'DROP TABLE main.local_files;' )
            c.execute( 'DROP TABLE main.pending_file_petitions;' )
            c.execute( 'DROP TABLE main.pending_files;' )
            c.execute( 'DROP TABLE main.remote_files;' )
            
            c.execute( 'DROP TABLE remote_thumbnails;' )
            c.execute( 'DROP TABLE local_thumbnails;' )
            c.execute( 'DROP TABLE remote_thumbnails_resized;' )
            c.execute( 'DROP TABLE local_thumbnails_resized;' )
            
        
        if version < 19:
            
            c.execute( 'CREATE TABLE service_info ( service_id INTEGER, info_type INTEGER, info INTEGER, PRIMARY KEY ( service_id, info_type ) );', )
            
            c.execute( 'CREATE TABLE tag_service_precedence ( service_id INTEGER PRIMARY KEY, precedence INTEGER );' )
            
            c.execute( 'INSERT INTO tag_service_precedence ( service_id, precedence ) SELECT service_id, service_id FROM services WHERE type = ?;', ( HC.TAG_REPOSITORY, ) )
            
        
        if version < 21:
            
            c.execute( 'CREATE TABLE files_info_db.perceptual_hashes ( service_id INTEGER, hash_id INTEGER, phash BLOB_BYTES, PRIMARY KEY( service_id, hash_id ) );' )
            
        
        if version < 22:
            
            c.execute( 'DELETE FROM perceptual_hashes;' )
            
            # there is some type-casting problem here that I can't figure out, so have to do it the long way
            # c.execute( 'INSERT INTO perceptual_hashes SELECT service_id, hash_id, CAST hydrus_phash( thumbnail ) FROM thumbnails;' )
            
            thumbnail_ids = c.execute( 'SELECT service_id, hash_id FROM thumbnails;' ).fetchall()
            
            for ( service_id, hash_id ) in thumbnail_ids:
                
                ( thumbnail, ) = c.execute( 'SELECT thumbnail FROM thumbnails WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
                
                phash = HydrusImageHandling.GeneratePerceptualHash( thumbnail )
                
                c.execute( 'INSERT INTO perceptual_hashes VALUES ( ?, ?, ? );', ( service_id, hash_id, sqlite3.Binary( phash ) ) )
                
            
        
        if version < 24:
            
            c.execute( 'CREATE TABLE imageboard_sites ( site_id INTEGER PRIMARY KEY, name TEXT );', )
            
            c.execute( 'CREATE TABLE imageboards ( site_id INTEGER, name TEXT, imageboard TEXT_YAML, PRIMARY KEY ( site_id, name ) );', )
            
            for ( site_name, imageboards ) in CC.DEFAULT_IMAGEBOARDS:
                
                site_id = self._GetSiteId( c, site_name )
                
                c.executemany( 'INSERT INTO imageboards VALUES ( ?, ?, ? );', [ ( site_id, imageboard.GetName(), imageboard ) for imageboard in imageboards ] )
                
            
        
        if version < 26:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            self._options[ 'num_autocomplete_chars' ] = 1
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 27:
            
            c.execute( 'CREATE TABLE files_info_db.urls ( url TEXT PRIMARY KEY, hash_id INTEGER );' )
            c.execute( 'CREATE INDEX files_info_db.urls_hash_id ON urls ( hash_id );' )
            
        
        if version < 29:
            
            files_db_path = HC.DB_DIR + os.path.sep + 'client_files.db'
            
            c.execute( 'COMMIT' )
            
            # can't do it inside a transaction
            c.execute( 'ATTACH database "' + files_db_path + '" as files_db;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            os.mkdir( HC.CLIENT_FILES_DIR )
            
            ( local_service_id, ) = c.execute( 'SELECT service_id FROM services WHERE type = ?;', ( HC.LOCAL_FILE, ) ).fetchone()
            
            all_local_files = c.execute( 'SELECT hash_id, hash FROM files_info, hashes USING ( hash_id ) WHERE service_id = ?;', ( local_service_id, ) ).fetchall()
            
            for i in range( 0, len( all_local_files ), 100 ):
                
                wx.GetApp().SetSplashText( 'updating db to v29 ' + str( i ) + '/' + str( len( all_local_files ) ) )
                
                local_files_subset = all_local_files[ i : i + 100 ]
                
                for ( hash_id, hash ) in local_files_subset:
                    
                    ( file, ) = c.execute( 'SELECT file FROM files WHERE hash_id = ?', ( hash_id, ) ).fetchone()
                    
                    path_to = HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    with open( path_to, 'wb' ) as f: f.write( file )
                    
                
                c.execute( 'DELETE FROM files WHERE hash_id IN ' + HC.SplayListForDB( [ hash_id for ( hash_id, hash ) in local_files_subset ] ) + ';' )
                
                c.execute( 'COMMIT' )
                
                # slow truncate happens here!
                
                c.execute( 'BEGIN IMMEDIATE' )
                
            
            c.execute( 'COMMIT' )
            
            # can't do it inside a transaction
            c.execute( 'DETACH DATABASE files_db;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            os.remove( files_db_path )
            
        
        if version < 30:
            
            thumbnails_db_path = HC.DB_DIR + os.path.sep + 'client_thumbnails.db'
            thumbnails_resized_db_path = HC.DB_DIR + os.path.sep + 'client_thumbnails_resized.db'
            
            c.execute( 'COMMIT' )
            
            # can't do it inside a transaction
            c.execute( 'ATTACH database "' + thumbnails_db_path + '" as thumbnails_db;' )
            
            os.mkdir( HC.CLIENT_THUMBNAILS_DIR )
            
            all_thumbnails = c.execute( 'SELECT DISTINCT hash_id, hash FROM thumbnails, hashes USING ( hash_id );' ).fetchall()
            
            all_service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services;' ) ]
            
            for i in range( 0, len( all_thumbnails ), 500 ):
                
                wx.GetApp().SetSplashText( 'updating db to v30 ' + str( i ) + '/' + str( len( all_thumbnails ) ) )
                
                thumbnails_subset = all_thumbnails[ i : i + 500 ]
                
                for ( hash_id, hash ) in thumbnails_subset:
                    
                    ( thumbnail, ) = c.execute( 'SELECT thumbnail FROM thumbnails WHERE service_id IN ' + HC.SplayListForDB( all_service_ids ) + ' AND hash_id = ?', ( hash_id, ) ).fetchone()
                    
                    path_to = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    with open( path_to, 'wb' ) as f: f.write( thumbnail )
                    
                
            
            # can't do it inside a transaction
            c.execute( 'DETACH DATABASE thumbnails_db;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            os.remove( thumbnails_db_path )
            os.remove( thumbnails_resized_db_path )
            
            all_p_hashes = c.execute( 'SELECT DISTINCT hash_id, phash FROM perceptual_hashes;' ).fetchall()
            
            c.execute( 'DROP TABLE perceptual_hashes;' )
            
            c.execute( 'CREATE TABLE files_info_db.perceptual_hashes ( hash_id INTEGER PRIMARY KEY, phash BLOB_BYTES );' )
            
            c.executemany( 'INSERT OR IGNORE INTO perceptual_hashes ( hash_id, phash ) VALUES ( ?, ? );', [ ( hash_id, sqlite3.Binary( phash ) ) for ( hash_id, phash ) in all_p_hashes ] )
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            default_namespace_colours = {}
            
            default_namespace_colours[ 'system' ] = ( 153, 101, 21 )
            default_namespace_colours[ 'creator' ] = ( 170, 0, 0 )
            default_namespace_colours[ 'character' ] = ( 0, 170, 0 )
            default_namespace_colours[ 'series' ] = ( 170, 0, 170 )
            default_namespace_colours[ None ] = ( 114, 160, 193 )
            default_namespace_colours[ '' ] = ( 0, 111, 250 )
            
            self._options[ 'namespace_colours' ] = default_namespace_colours
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 31:
            
            c.execute( 'CREATE TABLE boorus ( name TEXT PRIMARY KEY, booru TEXT_YAML );', )
            
            c.executemany( 'INSERT INTO boorus VALUES ( ?, ? );', [ ( booru.GetName(), booru ) for booru in CC.DEFAULT_BOORUS ] )
            
        
        if version < 33:
            
            try: c.execute( 'SELECT name, booru FROM boorus;' ).fetchall()
            except:
                
                c.execute( 'CREATE TABLE boorus ( name TEXT PRIMARY KEY, booru TEXT_YAML );', )
                
                c.executemany( 'INSERT INTO boorus VALUES ( ?, ? );', [ ( booru.GetName(), booru ) for booru in CC.DEFAULT_BOORUS ] )
                
            
            c.execute( 'CREATE TABLE local_hashes ( hash_id INTEGER PRIMARY KEY, md5 BLOB_BYTES, sha1 BLOB_BYTES );' )
            c.execute( 'CREATE INDEX local_hashes_md5_index ON local_hashes ( md5 );' )
            c.execute( 'CREATE INDEX local_hashes_sha1_index ON local_hashes ( sha1 );' )
            
            ( local_service_id, ) = c.execute( 'SELECT service_id FROM services WHERE type = ?;', ( HC.LOCAL_FILE, ) ).fetchone()
            
            hashes = c.execute( 'SELECT hash_id, hash FROM hashes, files_info USING ( hash_id ) WHERE service_id = ?;', ( local_service_id, ) ).fetchall()
            
            for i in range( 0, len( hashes ), 100 ):
                
                wx.GetApp().SetSplashText( 'updating db to v33 ' + str( i ) + '/' + str( len( hashes ) ) )
                
                hashes_subset = hashes[ i : i + 100 ]
                
                inserts = []
                
                for ( hash_id, hash ) in hashes_subset:
                    
                    path = HC.CLIENT_FILES_DIR + os.path.sep + hash.encode( 'hex' )
                    
                    with open( path, 'rb' ) as f: file = f.read()
                    
                    md5 = hashlib.md5( file ).digest()
                    
                    sha1 = hashlib.sha1( file ).digest()
                    
                    inserts.append( ( hash_id, sqlite3.Binary( md5 ), sqlite3.Binary( sha1 ) ) )
                    
                
                c.executemany( 'INSERT INTO local_hashes ( hash_id, md5, sha1 ) VALUES ( ?, ?, ? );', inserts )
                
            
        
        if version < 35:
            
            c.execute( 'CREATE TABLE active_pending_mappings ( namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, PRIMARY KEY( namespace_id, tag_id, hash_id ) );' )
            c.execute( 'CREATE INDEX active_pending_mappings_tag_id_index ON active_pending_mappings ( tag_id );' )
            c.execute( 'CREATE INDEX active_pending_mappings_hash_id_index ON active_pending_mappings ( hash_id );' )
            
            service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM tag_service_precedence ORDER BY precedence DESC;' ) ]
            
            first_round = True
            
            for service_id in service_ids:
                
                c.execute( 'INSERT OR IGNORE INTO active_pending_mappings SELECT namespace_id, tag_id, hash_id FROM pending_mappings WHERE service_id = ?;', ( service_id, ) )
                
                # is this incredibly inefficient?
                # if this is O( n-squared ) or whatever, just rewrite it as two queries using indices
                if not first_round: c.execute( 'DELETE FROM active_pending_mappings WHERE namespace_id || "," || tag_id || "," || hash_id IN ( SELECT namespace_id || "," || tag_id || "," || hash_id FROM deleted_mappings WHERE service_id = ? );', ( service_id, ) )
                
                first_round = False
                
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            default_sort_by_choices = []
            
            default_sort_by_choices.append( ( 'namespaces', [ 'series', 'creator', 'title', 'volume', 'chapter', 'page' ] ) )
            default_sort_by_choices.append( ( 'namespaces', [ 'creator', 'series', 'title', 'volume', 'chapter', 'page' ] ) )
            
            self._options[ 'sort_by' ] = default_sort_by_choices
            
            self._options[ 'default_sort' ] = 0
            self._options[ 'default_collect' ] = 0
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 36:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            self._options[ 'gui_capitalisation' ] = False
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 37:
            
            # reconfig inbox -> file_inbox
            
            c.execute( 'CREATE TABLE file_inbox ( hash_id INTEGER PRIMARY KEY );' )
            
            c.execute( 'INSERT INTO file_inbox SELECT hash_id FROM inbox;' )
            
            c.execute( 'DROP TRIGGER inbox_insert_trigger;' )
            c.execute( 'DROP TRIGGER inbox_delete_trigger;' )
            
            c.execute( 'DROP TABLE inbox;' )
            
            inserts = []
            inserts.append( 'UPDATE service_info SET info = info + 1 WHERE service_id IN ( SELECT service_id FROM files_info WHERE hash_id = new.hash_id ) AND info_type = ' + str( HC.SERVICE_INFO_NUM_INBOX ) + ';' )
            c.execute( 'CREATE TRIGGER file_inbox_insert_trigger AFTER INSERT ON file_inbox BEGIN ' + ' '.join( inserts ) + ' END;' )
            deletes = []
            deletes.append( 'UPDATE service_info SET info = info - 1 WHERE service_id IN ( SELECT service_id FROM files_info WHERE hash_id = old.hash_id ) AND info_type = ' + str( HC.SERVICE_INFO_NUM_INBOX ) + ';' )
            c.execute( 'CREATE TRIGGER file_inbox_delete_trigger DELETE ON file_inbox BEGIN ' + ' '.join( deletes ) + ' END;' )
            
            # now set up new messaging stuff
            
            c.execute( 'CREATE TABLE contacts ( contact_id INTEGER PRIMARY KEY, contact_key BLOB_BYTES, public_key TEXT, name TEXT, host TEXT, port INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_name_index ON contacts ( name );' )
            
            c.execute( 'CREATE VIRTUAL TABLE conversation_subjects USING fts4( subject );' )
            
            c.execute( 'CREATE TABLE message_attachments ( message_id INTEGER PRIMARY KEY REFERENCES message_keys ON DELETE CASCADE, hash_id INTEGER );' )
            
            c.execute( 'CREATE TABLE message_depots ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, contact_id INTEGER, last_check INTEGER, check_period INTEGER, private_key TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX message_depots_contact_id_index ON message_depots ( contact_id );' )
            
            c.execute( 'CREATE TABLE message_destination_map ( message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, contact_id_to INTEGER, status_id INTEGER, PRIMARY KEY ( message_id, contact_id_to ) );' )
            c.execute( 'CREATE INDEX message_destination_map_contact_id_to_index ON message_destination_map ( contact_id_to );' )
            c.execute( 'CREATE INDEX message_destination_map_status_id_index ON message_destination_map ( status_id );' )
            
            c.execute( 'CREATE TABLE message_downloads ( service_id INTEGER REFERENCES services ON DELETE CASCADE, message_id INTEGER REFERENCES message_keys ON DELETE CASCADE );' )
            c.execute( 'CREATE INDEX message_downloads_service_id_index ON message_downloads ( service_id );' )
            
            c.execute( 'CREATE TABLE message_drafts ( message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, recipients_visible INTEGER_BOOLEAN );' )
            
            c.execute( 'CREATE TABLE message_inbox ( message_id INTEGER PRIMARY KEY REFERENCES message_keys ON DELETE CASCADE );' )
            
            c.execute( 'CREATE TABLE message_keys ( message_id INTEGER PRIMARY KEY, message_key BLOB_BYTES );' )
            c.execute( 'CREATE INDEX message_keys_message_key_index ON message_keys ( message_key );' )
            
            c.execute( 'CREATE VIRTUAL TABLE message_bodies USING fts4( body );' )
            
            c.execute( 'CREATE TABLE messages ( conversation_id INTEGER REFERENCES message_keys ( message_id ) ON DELETE CASCADE, message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, contact_id_from INTEGER, timestamp INTEGER, PRIMARY KEY( conversation_id, message_id ) );' )
            c.execute( 'CREATE UNIQUE INDEX messages_message_id_index ON messages ( message_id );' )
            c.execute( 'CREATE INDEX messages_contact_id_from_index ON messages ( contact_id_from );' )
            c.execute( 'CREATE INDEX messages_timestamp_index ON messages ( timestamp );' )
            
            c.execute( 'CREATE TABLE statuses ( status_id INTEGER PRIMARY KEY, status TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX statuses_status_index ON statuses ( status );' )
            
            c.execute( 'INSERT INTO contacts ( contact_id, contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ?, ? );', ( 1, None, None, 'Anonymous', 'internet', 0 ) )
            # fill the contact key and public key info in for hydrus admin
            
        
        if version < 38:
            
            c.execute( 'COMMIT' )
            c.execute( 'PRAGMA journal_mode=WAL;' ) # possibly didn't work last time, cause of sqlite dll issue
            c.execute( 'BEGIN IMMEDIATE' )
            
            contacts_contents = c.execute( 'SELECT * FROM contacts;' ).fetchall()
            
            c.execute( 'DROP TABLE contacts;' )
            
            c.execute( 'CREATE TABLE contacts ( contact_id INTEGER PRIMARY KEY, contact_key BLOB_BYTES, public_key TEXT, name TEXT, host TEXT, port INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_name_index ON contacts ( name );' )
            
            c.executemany( 'INSERT INTO contacts VALUES ( ?, ?, ?, ?, ?, ? );', contacts_contents )
            
            c.execute( 'CREATE TABLE message_statuses_to_apply ( message_id INTEGER, contact_key BLOB_BYTES, status_id INTEGER, PRIMARY KEY ( message_id, contact_key ) );' )
            
        
        if version < 39:
            
            # I accidentally added some buffer public keys in v38, so this is to str() them
            updates = [ ( str( public_key ), contact_id ) for ( contact_id, public_key ) in c.execute( 'SELECT contact_id, public_key FROM contacts;' ).fetchall() ]
            
            c.executemany( 'UPDATE contacts SET public_key = ? WHERE contact_id = ?;', updates )
            
            with open( HC.STATIC_DIR + os.sep + 'contact - hydrus admin.yaml', 'rb' ) as f: hydrus_admin = yaml.safe_load( f.read() )
            
            ( public_key, name, host, port ) = hydrus_admin.GetInfo()
            
            contact_key = hydrus_admin.GetContactKey()
            
            c.execute( 'INSERT OR IGNORE INTO contacts ( contact_key, public_key, name, host, port ) VALUES ( ?, ?, ?, ?, ? );', ( sqlite3.Binary( contact_key ), public_key, name, host, port ) )
            
        
        if version < 41:
            
            # better name and has foreign key assoc
            
            c.execute( 'CREATE TABLE incoming_message_statuses ( message_id INTEGER REFERENCES message_keys ON DELETE CASCADE, contact_key BLOB_BYTES, status_id INTEGER, PRIMARY KEY ( message_id, contact_key ) );' )
            
            incoming_status_inserts = c.execute( 'SELECT * FROM message_statuses_to_apply;' ).fetchall()
            
            c.executemany( 'INSERT INTO incoming_message_statuses VALUES ( ?, ?, ? );', incoming_status_inserts )
            
            c.execute( 'DROP TABLE message_statuses_to_apply;' )
            
            # delete all drafts cause of plaintext->xml conversion
            
            message_ids = [ message_id for ( message_id, ) in c.execute( 'SELECT message_id FROM message_drafts;' ) ]
            
            c.execute( 'DELETE FROM message_keys WHERE message_id IN ' + HC.SplayListForDB( message_ids ) + ';' )
            c.execute( 'DELETE FROM message_bodies WHERE docid IN ' + HC.SplayListForDB( message_ids ) + ';' )
            c.execute( 'DELETE FROM conversation_subjects WHERE docid IN ' + HC.SplayListForDB( message_ids ) + ';' )
            
            c.execute( 'ALTER TABLE message_depots ADD COLUMN receive_anon INTEGER_BOOLEAN' )
            c.execute( 'UPDATE message_depots SET receive_anon = ?;', ( True, ) )
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            system_predicates = {}
            
            system_predicates[ 'age' ] = ( 0, 0, 0, 7 )
            system_predicates[ 'duration' ] = ( 3, 0, 0 )
            system_predicates[ 'height' ] = ( 1, 1200 )
            system_predicates[ 'limit' ] = 600
            system_predicates[ 'mime' ] = ( 0, 0 )
            system_predicates[ 'num_tags' ] = ( 0, 4 )
            system_predicates[ 'ratio' ] = ( 0, 16, 9 )
            system_predicates[ 'size' ] = ( 0, 200, 3 )
            system_predicates[ 'width' ] = ( 1, 1920 )
            
            self._options[ 'file_system_predicates' ] = system_predicates
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 42:
            
            self._RecalcActiveMappings( c )
            
            c.execute( 'CREATE TABLE autocomplete_tags_cache ( file_service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, tag_service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, current_count INTEGER, pending_count INTEGER, PRIMARY KEY ( file_service_id, tag_service_id, namespace_id, tag_id ) );' )
            c.execute( 'CREATE INDEX autocomplete_tags_cache_tag_service_id_namespace_id_tag_id_index ON autocomplete_tags_cache ( tag_service_id, namespace_id, tag_id );' )
            
            c.execute( 'DROP TRIGGER files_info_insert_trigger;' )
            c.execute( 'DROP TRIGGER files_info_delete_trigger;' )
            
            c.execute( 'DROP TRIGGER mappings_insert_trigger;' )
            c.execute( 'DROP TRIGGER mappings_delete_trigger;' )
            
            inserts = []
            inserts.append( 'DELETE FROM deleted_files WHERE service_id = new.service_id AND hash_id = new.hash_id;' )
            inserts.append( 'DELETE FROM file_transfers WHERE service_id_to = new.service_id AND hash_id = new.hash_id;' )
            inserts.append( 'UPDATE service_info SET info = info + new.size WHERE service_id = new.service_id AND info_type = ' + str( HC.SERVICE_INFO_TOTAL_SIZE ) + ';' )
            inserts.append( 'UPDATE service_info SET info = info + 1 WHERE service_id = new.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_FILES ) + ';' )
            inserts.append( 'UPDATE service_info SET info = info + 1 WHERE service_id = new.service_id AND new.mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' AND info_type = ' + str( HC.SERVICE_INFO_NUM_THUMBNAILS ) + ';' )
            inserts.append( 'DELETE FROM service_info WHERE service_id = new.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_INBOX ) + ';' )
            inserts.append( 'DELETE FROM service_info WHERE service_id = new.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL ) + ';' )
            inserts.append( 'DELETE FROM autocomplete_tags_cache WHERE file_service_id = new.service_id;' )
            c.execute( 'CREATE TRIGGER files_info_insert_trigger AFTER INSERT ON files_info BEGIN ' + ' '.join( inserts ) + ' END;' )
            deletes = []
            deletes.append( 'DELETE FROM file_petitions WHERE service_id = old.service_id AND hash_id = old.hash_id;' )
            deletes.append( 'UPDATE service_info SET info = info - old.size WHERE service_id = old.service_id AND info_type = ' + str( HC.SERVICE_INFO_TOTAL_SIZE ) + ';' )
            deletes.append( 'UPDATE service_info SET info = info - 1 WHERE service_id = old.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_FILES ) + ';' )
            deletes.append( 'UPDATE service_info SET info = info - 1 WHERE service_id = old.service_id AND old.mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' AND info_type = ' + str( HC.SERVICE_INFO_NUM_THUMBNAILS ) + ';' )
            deletes.append( 'DELETE FROM service_info WHERE service_id = old.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_INBOX ) + ';' )
            deletes.append( 'DELETE FROM service_info WHERE service_id = old.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL ) + ';' )
            deletes.append( 'DELETE FROM autocomplete_tags_cache WHERE file_service_id = old.service_id;' )
            c.execute( 'CREATE TRIGGER files_info_delete_trigger DELETE ON files_info BEGIN ' + ' '.join( deletes ) + ' END;' )
            
            inserts = []
            inserts.append( 'DELETE FROM deleted_mappings WHERE service_id = new.service_id AND hash_id = new.hash_id AND namespace_id = new.namespace_id AND tag_id = new.tag_id;' )
            inserts.append( 'DELETE FROM pending_mappings WHERE service_id = new.service_id AND hash_id = new.hash_id AND namespace_id = new.namespace_id AND tag_id = new.tag_id;' )
            inserts.append( 'UPDATE service_info SET info = info + 1 WHERE service_id = new.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_MAPPINGS ) + ';' )
            inserts.append( 'DELETE FROM service_info WHERE service_id = new.service_id AND info_type IN ' + HC.SplayListForDB( ( HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS ) ) + ';' )
            inserts.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id = new.service_id AND namespace_id = new.namespace_id AND tag_id = new.tag_id;' )
            inserts.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL AND namespace_id = new.namespace_id AND tag_id = new.tag_id;' )
            c.execute( 'CREATE TRIGGER mappings_insert_trigger AFTER INSERT ON mappings BEGIN ' + ' '.join( inserts ) + ' END;' )
            deletes = []
            deletes.append( 'DELETE FROM mapping_petitions WHERE service_id = old.service_id AND hash_id = old.hash_id AND namespace_id = old.namespace_id AND tag_id = old.tag_id;' )
            deletes.append( 'UPDATE service_info SET info = info - 1 WHERE service_id = old.service_id AND info_type = ' + str( HC.SERVICE_INFO_NUM_MAPPINGS ) + ';' )
            deletes.append( 'DELETE FROM service_info WHERE service_id = old.service_id AND info_type IN ' + HC.SplayListForDB( ( HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS ) ) + ';' )
            deletes.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id = old.service_id AND namespace_id = old.namespace_id AND tag_id = old.tag_id;' )
            deletes.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL AND namespace_id = old.namespace_id AND tag_id = old.tag_id;' )
            c.execute( 'CREATE TRIGGER mappings_delete_trigger DELETE ON mappings BEGIN ' + ' '.join( deletes ) + ' END;' )
            
            inserts = []
            inserts.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id = new.service_id AND namespace_id = new.namespace_id AND tag_id = new.tag_id;' )
            inserts.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL AND namespace_id = new.namespace_id AND tag_id = new.tag_id;' )
            c.execute( 'CREATE TRIGGER pending_mappings_insert_trigger AFTER INSERT ON pending_mappings BEGIN ' + ' '.join( inserts ) + ' END;' )
            deletes = []
            deletes.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id = old.service_id AND namespace_id = old.namespace_id AND tag_id = old.tag_id;' )
            deletes.append( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id IS NULL AND namespace_id = old.namespace_id AND tag_id = old.tag_id;' )
            c.execute( 'CREATE TRIGGER pending_mappings_delete_trigger DELETE ON pending_mappings BEGIN ' + ' '.join( deletes ) + ' END;' )
            
            # All of 4chan's post urls are now https. There is a 301 redirect from the http, but let's update anyway.
            
            all_imageboards = c.execute( 'SELECT site_id, name, imageboard FROM imageboards;' ).fetchall()
            
            for ( site_id, name, imageboard ) in all_imageboards:
                
                imageboard._post_url = imageboard._post_url.replace( 'http', 'https' )
                
            
            c.executemany( 'UPDATE imageboards SET imageboard = ? WHERE site_id = ? AND name = ?;', [ ( imageboard, site_id, name ) for ( site_id, name, imageboard ) in all_imageboards ] )
            
        
        if version < 43:
            
            name = 'konachan'
            search_url = 'http://konachan.com/post?page=%index%&tags=%tags%'
            search_separator = '+'
            gallery_advance_num = 1
            thumb_classname = 'thumb'
            image_id = None
            image_data = 'View larger version'
            tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
            
            booru = CC.Booru( name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
            c.execute( 'INSERT INTO boorus VALUES ( ?, ? );', ( booru.GetName(), booru ) )
            
        
        if version < 44:
            
            name = 'e621'
            
            result = c.execute( 'SELECT booru FROM boorus WHERE name = ?;', ( name, ) ).fetchone()
            
            if result is not None:
                
                ( booru, ) = result
                
                ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
                
                thumb_classname = 'thumb blacklist' # from thumb_blacklisted
                
                booru = CC.Booru( name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
                
                c.execute( 'UPDATE boorus SET booru = ? WHERE name = ?;', ( booru, booru.GetName() ) )
                
            
            name = 'rule34@booru.org'
            
            result = c.execute( 'SELECT booru FROM boorus WHERE name = ?;', ( name, ) ).fetchone()
            
            if result is not None:
                
                ( booru, ) = result
                
                ( search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
                
                gallery_advance_num = 50
                
                booru = CC.Booru( name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
                
                c.execute( 'UPDATE boorus SET booru = ? WHERE name = ?;', ( booru, booru.GetName() ) )
                
            
            c.execute( 'DROP TRIGGER files_info_insert_trigger;' )
            c.execute( 'DROP TRIGGER files_info_delete_trigger;' )
            c.execute( 'DROP TRIGGER deleted_files_insert_trigger;' )
            c.execute( 'DROP TRIGGER deleted_files_delete_trigger;' )
            c.execute( 'DROP TRIGGER file_inbox_insert_trigger;' )
            c.execute( 'DROP TRIGGER file_inbox_delete_trigger;' )
            c.execute( 'DROP TRIGGER mappings_insert_trigger;' )
            c.execute( 'DROP TRIGGER mappings_delete_trigger;' )
            c.execute( 'DROP TRIGGER deleted_mappings_insert_trigger;' )
            c.execute( 'DROP TRIGGER deleted_mappings_delete_trigger;' )
            c.execute( 'DROP TRIGGER pending_mappings_insert_trigger;' )
            c.execute( 'DROP TRIGGER pending_mappings_delete_trigger;' )
            
            c.execute( 'UPDATE services SET name = ? WHERE name = ?;', ( 'local files renamed', 'local files' ) )
            c.execute( 'UPDATE services SET name = ? WHERE type = ?;', ( 'local files', HC.LOCAL_FILE ) )
            
            c.execute( 'INSERT INTO services ( type, name ) VALUES ( ?, ? );', ( HC.LOCAL_TAG, 'local tags' ) )
            
            local_tag_service_id = c.lastrowid
            
            c.execute( 'INSERT INTO tag_service_precedence ( service_id, precedence ) SELECT ?, CASE WHEN MIN( precedence ) NOT NULL THEN MIN( precedence ) - 1 ELSE 0 END FROM tag_service_precedence;', ( local_tag_service_id, ) )
            
        
        if version < 46:
            
            name = 'rule34@paheal'
            search_url = 'http://rule34.paheal.net/post/list/%tags%/%index%'
            search_separator = '%20'
            gallery_advance_num = 1
            thumb_classname = 'thumb'
            image_id = 'main_image'
            image_data = None
            tag_classnames_to_namespaces = { 'tag_name' : '' }
            
            booru = CC.Booru( name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
            c.execute( 'INSERT INTO boorus VALUES ( ?, ? );', ( booru.GetName(), booru ) )
            
            name = 'tbib'
            search_url = 'http://tbib.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
            search_separator = '+'
            gallery_advance_num = 25
            thumb_classname = 'thumb'
            image_id = None
            image_data = 'Original image'
            tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
            
            booru = CC.Booru( name, search_url, search_separator, gallery_advance_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
            c.execute( 'INSERT INTO boorus VALUES ( ?, ? );', ( booru.GetName(), booru ) )
            
        
        if version < 48:
            
            c.execute( 'CREATE TABLE local_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, rating REAL, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX local_ratings_hash_id_index ON local_ratings ( hash_id );' )
            c.execute( 'CREATE INDEX local_ratings_rating_index ON local_ratings ( rating );' )
            
            c.execute( 'CREATE TABLE remote_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, count INTEGER, rating REAL, score REAL, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX remote_ratings_hash_id_index ON remote_ratings ( hash_id );' )
            c.execute( 'CREATE INDEX remote_ratings_rating_index ON remote_ratings ( rating );' )
            c.execute( 'CREATE INDEX remote_ratings_score_index ON remote_ratings ( score );' )
            
            c.execute( 'CREATE TABLE ratings_numerical ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, lower INTEGER, upper INTEGER );' )
            
            c.execute( 'CREATE TABLE ratings_like ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, like TEXT, dislike TEXT );' )
            
        
        if version < 49:
            
            result = c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( '', ) ).fetchone()
            
            if result is not None:
                
                ( tag_id, ) = result
                
                c.execute( 'DELETE FROM mappings WHERE tag_id = ?;', ( tag_id, ) )
                c.execute( 'DELETE FROM pending_mappings WHERE tag_id = ?;', ( tag_id, ) )
                c.execute( 'DELETE FROM active_mappings WHERE tag_id = ?;', ( tag_id, ) )
                c.execute( 'DELETE FROM active_pending_mappings WHERE tag_id = ?;', ( tag_id, ) )
                
            
            wx.GetApp().SetSplashText( 'making new cache, may take a minute' )
            
            c.execute( 'CREATE TABLE existing_tags ( namespace_id INTEGER, tag_id INTEGER, PRIMARY KEY( namespace_id, tag_id ) );' )
            c.execute( 'CREATE INDEX existing_tags_tag_id_index ON existing_tags ( tag_id );' )
            
            all_tag_ids = set()
            
            all_tag_ids.update( c.execute( 'SELECT namespace_id, tag_id FROM mappings;' ).fetchall() )
            all_tag_ids.update( c.execute( 'SELECT namespace_id, tag_id FROM pending_mappings;' ).fetchall() )
            
            c.executemany( 'INSERT INTO existing_tags ( namespace_id, tag_id ) VALUES ( ?, ? );', all_tag_ids )
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            self._options[ 'show_all_tags_in_autocomplete' ] = True
            
            self._options[ 'file_system_predicates' ][ 'local_rating_numerical' ] = ( 0, 3 )
            self._options[ 'file_system_predicates' ][ 'local_rating_like' ] = 0
            
            shortcuts = {}
            
            shortcuts[ wx.ACCEL_NORMAL ] = {}
            shortcuts[ wx.ACCEL_CTRL ] = {}
            shortcuts[ wx.ACCEL_ALT ] = {}
            shortcuts[ wx.ACCEL_SHIFT ] = {}
            
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F3 ] = 'manage_tags'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F4 ] = 'manage_ratings'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F5 ] = 'refresh'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F7 ] = 'archive'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F12 ] = 'filter'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F9 ] = 'new_page'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'T' ) ] = 'new_page'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'W' ) ] = 'close_page'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'R' ) ] = 'show_hide_splitters'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'S' ) ] = 'set_search_focus'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'I' ) ] = 'synchronised_wait_switch'
            
            self._options[ 'shortcuts' ] = shortcuts
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 50:
            
            c.execute( 'CREATE TABLE fourchan_pass ( token TEXT, pin TEXT, timeout INTEGER );' )
            
        
        if version < 51:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            shortcuts = self._options[ 'shortcuts' ]
            
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'B' ) ] = 'frame_back'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'N' ) ] = 'frame_next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_F11 ] = 'ratings_filter'
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
            c.execute( 'CREATE TABLE ratings_filter ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, min REAL, max REAL, PRIMARY KEY( service_id, hash_id ) );' )
            
        
        if version < 52:
            
            wx.GetApp().SetSplashText( 'making new indices' )
            
            c.execute( 'DROP INDEX mappings_namespace_id_index;' )
            c.execute( 'DROP INDEX mappings_tag_id_index;' )
            
            c.execute( 'CREATE INDEX mappings_service_id_tag_id_index ON mappings ( service_id, tag_id );' )
            c.execute( 'CREATE INDEX mappings_service_id_hash_id_index ON mappings ( service_id, hash_id );' )
            
            wx.GetApp().SetSplashText( 'making some more new indices' )
            
            c.execute( 'DROP INDEX pending_mappings_namespace_id_index;' )
            c.execute( 'DROP INDEX pending_mappings_tag_id_index;' )
            
            c.execute( 'CREATE INDEX pending_mappings_service_id_tag_id_index ON pending_mappings ( service_id, tag_id );' )
            c.execute( 'CREATE INDEX pending_mappings_service_id_hash_id_index ON pending_mappings ( service_id, hash_id );' )
            
            c.execute( 'CREATE TABLE shutdown_timestamps ( shutdown_type INTEGER PRIMARY KEY, timestamp INTEGER );' )
            
        
        if version < 54:
            
            c.execute( 'DROP INDEX services_type_name_index;' )
            
            c.execute( 'ALTER TABLE services ADD COLUMN service_key BLOB_BYTES;' )
            c.execute( 'CREATE UNIQUE INDEX services_service_key_index ON services ( service_key );' )
            
            service_info = c.execute( 'SELECT service_id, type FROM services;' ).fetchall()
            
            updates = []
            
            for ( service_id, service_type ) in service_info:
                
                if service_type == HC.LOCAL_FILE: service_key = 'local files'
                elif service_type == HC.LOCAL_TAG: service_key = 'local tags'
                else: service_key = os.urandom( 32 )
                
                updates.append( ( sqlite3.Binary( service_key ), service_id ) )
                
            
            c.executemany( 'UPDATE services SET service_key = ? WHERE service_id = ?;', updates )
            
            c.execute( 'UPDATE files_info SET num_frames = num_frames / 1000 WHERE mime = ?;', ( HC.VIDEO_FLV, ) )
            
        
        if version < 55:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            self._options[ 'default_tag_repository' ] = CC.LOCAL_TAG_SERVICE_IDENTIFIER
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 56:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            self._options[ 'default_tag_sort' ] = CC.SORT_BY_LEXICOGRAPHIC_ASC
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 57:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            shortcuts = self._options[ 'shortcuts' ]
            
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_UP ] = 'previous'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_LEFT ] = 'previous'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_UP ] = 'previous'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_LEFT ] = 'previous'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_PAGEUP ] = 'previous'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_PAGEUP ] = 'previous'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_DOWN ] = 'next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_RIGHT ] = 'next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_DOWN ] = 'next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_RIGHT ] = 'next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_PAGEDOWN ] = 'next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_PAGEDOWN ] = 'next'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_HOME ] = 'first'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_HOME ] = 'first'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_END ] = 'last'
            shortcuts[ wx.ACCEL_NORMAL ][ wx.WXK_NUMPAD_END ] = 'last'
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
        if version < 58:
            
            ( self._options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            shortcuts = self._options[ 'shortcuts' ]
            
            shortcuts[ wx.ACCEL_SHIFT ][ wx.WXK_F7 ] = 'inbox'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'M' ) ] = 'set_media_focus'
            
            c.execute( 'UPDATE options SET options = ?;', ( self._options, ) )
            
        
    
    def _UpdateDBOldPost( self, c, version ):
        
        if version == 34: # == is important here
            
            try:
                
                main_db_path = HC.DB_DIR + os.path.sep + 'client_main.db'
                mappings_db_path = HC.DB_DIR + os.path.sep + 'client_mappings.db'
                active_mappings_db_path = HC.DB_DIR + os.path.sep + 'client_active_mappings.db'
                files_info_db_path = HC.DB_DIR + os.path.sep + 'client_files_info.db'
                
                if os.path.exists( main_db_path ):
                    
                    # can't do it inside transaction
                    
                    wx.GetApp().SetSplashText( 'consolidating db - preparing' )
                    
                    c.execute( 'ATTACH database "' + main_db_path + '" as main_db;' )
                    c.execute( 'ATTACH database "' + files_info_db_path + '" as files_info_db;' )
                    c.execute( 'ATTACH database "' + mappings_db_path + '" as mappings_db;' )
                    c.execute( 'ATTACH database "' + active_mappings_db_path + '" as active_mappings_db;' )
                    
                    c.execute( 'BEGIN IMMEDIATE' )
                    
                    c.execute( 'REPLACE INTO main.services SELECT * FROM main_db.services;' )
                    
                    all_service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM main.services;' ) ]
                    
                    c.execute( 'DELETE FROM main_db.accounts WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM main_db.addresses WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM main_db.news WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM main_db.repositories WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM main_db.service_info WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM main_db.tag_service_precedence WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    
                    c.execute( 'DELETE FROM mappings_db.deleted_mappings WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM mappings_db.mappings WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM mappings_db.mapping_petitions WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM mappings_db.pending_mappings WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    
                    c.execute( 'DELETE FROM files_info_db.deleted_files WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM files_info_db.files_info WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM files_info_db.file_transfers WHERE service_id_to NOT IN ' + HC.SplayListForDB( all_service_ids ) + ' OR service_id_from NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    c.execute( 'DELETE FROM files_info_db.file_petitions WHERE service_id NOT IN ' + HC.SplayListForDB( all_service_ids ) + ';' )
                    
                    c.execute( 'DELETE FROM main.options;' )
                    
                    wx.GetApp().SetSplashText( 'consolidating db - 1/4' )
                    
                    c.execute( 'REPLACE INTO main.accounts SELECT * FROM main_db.accounts;' )
                    c.execute( 'REPLACE INTO main.addresses SELECT * FROM main_db.addresses;' )
                    c.execute( 'REPLACE INTO main.boorus SELECT * FROM main_db.boorus;' )
                    c.execute( 'REPLACE INTO main.hashes SELECT * FROM main_db.hashes;' )
                    c.execute( 'REPLACE INTO main.imageboard_sites SELECT * FROM main_db.imageboard_sites;' )
                    c.execute( 'REPLACE INTO main.imageboards SELECT * FROM main_db.imageboards;' )
                    c.execute( 'REPLACE INTO main.local_hashes SELECT * FROM main_db.local_hashes;' )
                    c.execute( 'REPLACE INTO main.namespaces SELECT * FROM main_db.namespaces;' )
                    c.execute( 'REPLACE INTO main.news SELECT * FROM main_db.news;' )
                    c.execute( 'REPLACE INTO main.options SELECT * FROM main_db.options;' )
                    c.execute( 'REPLACE INTO main.reasons SELECT * FROM main_db.reasons;' )
                    c.execute( 'REPLACE INTO main.repositories SELECT * FROM main_db.repositories;' )
                    # don't do service info, so it gets recalced naturally
                    c.execute( 'REPLACE INTO main.tag_service_precedence SELECT * FROM main_db.tag_service_precedence;' )
                    c.execute( 'REPLACE INTO main.tags SELECT * FROM main_db.tags;' )
                    # don't do version, lol
                    
                    wx.GetApp().SetSplashText( 'consolidating db - 2/4' )
                    
                    c.execute( 'REPLACE INTO main.deleted_mappings SELECT * FROM mappings_db.deleted_mappings;' )
                    c.execute( 'REPLACE INTO main.mappings SELECT * FROM mappings_db.mappings;' )
                    c.execute( 'REPLACE INTO main.mapping_petitions SELECT * FROM mappings_db.mapping_petitions;' )
                    c.execute( 'REPLACE INTO main.pending_mappings SELECT * FROM mappings_db.pending_mappings;' )
                    
                    wx.GetApp().SetSplashText( 'consolidating db - 3/4' )
                    
                    c.execute( 'REPLACE INTO main.active_mappings SELECT * FROM active_mappings_db.active_mappings;' )
                    
                    wx.GetApp().SetSplashText( 'consolidating db - 4/4' )
                    
                    c.execute( 'REPLACE INTO main.deleted_files SELECT * FROM files_info_db.deleted_files;' )
                    c.execute( 'REPLACE INTO main.files_info SELECT * FROM files_info_db.files_info;' )
                    c.execute( 'REPLACE INTO main.file_transfers SELECT * FROM files_info_db.file_transfers;' )
                    c.execute( 'REPLACE INTO main.file_petitions SELECT * FROM files_info_db.file_petitions;' )
                    c.execute( 'REPLACE INTO main.inbox SELECT * FROM files_info_db.inbox;' )
                    c.execute( 'REPLACE INTO main.perceptual_hashes SELECT * FROM files_info_db.perceptual_hashes;' )
                    c.execute( 'REPLACE INTO main.urls SELECT * FROM files_info_db.urls;' )
                    
                    c.execute( 'COMMIT' )
                    
                    wx.GetApp().SetSplashText( 'consolidating db - cleaning up' )
                    
                    c.execute( 'DETACH database main_db;' )
                    c.execute( 'DETACH database files_info_db;' )
                    c.execute( 'DETACH database mappings_db;' )
                    c.execute( 'DETACH database active_mappings_db;' )
                    
                    os.remove( main_db_path )
                    os.remove( mappings_db_path )
                    os.remove( active_mappings_db_path )
                    os.remove( files_info_db_path )
                    
                
            except:
                
                print( traceback.format_exc() )
                
                try: c.execute( 'ROLLBACK' )
                except: pass
                
                raise Exception( 'Tried to update the client db, but something went wrong:' + os.linesep + traceback.format_exc() )
                
            
        
    
    def _Vacuum( self ):
        
        ( db, c ) = self._GetDBCursor()
        
        c.execute( 'VACUUM' )
        
        c.execute( 'REPLACE INTO shutdown_timestamps ( shutdown_type, timestamp ) VALUES ( ?, ? );', ( CC.SHUTDOWN_TIMESTAMP_VACUUM, int( time.time() ) ) )
        
        self.pub( 'log_message', 'database', 'vacuumed successfully' )
        
    
    def pub( self, topic, *args, **kwargs ): self._pubsubs.append( ( topic, args, kwargs ) )
    
    def DAEMONDownloadFiles( self ):
        
        all_downloads = self.Read( 'all_downloads', HC.LOW_PRIORITY )
        
        num_downloads = sum( [ len( hashes ) for ( service_identifier, hashes ) in all_downloads.items() ] ) 
        
        for ( service_identifier, hashes ) in all_downloads.items():
            
            try:
                
                try: file_repository = self.Read( 'service', HC.LOW_PRIORITY, service_identifier )
                except: continue
                
                HC.pubsub.pub( 'downloads_status', HC.ConvertIntToPrettyString( num_downloads ) + ' file downloads' )
                
                if file_repository.CanDownload(): 
                    
                    connection = file_repository.GetConnection()
                    
                    for hash in hashes:
                        
                        if HC.shutdown: return
                        
                        file = connection.Get( 'file', hash = hash.encode( 'hex' ) )
                        
                        num_downloads -= 1
                        
                        wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                        
                        HC.pubsub.pub( 'downloads_status', HC.ConvertIntToPrettyString( num_downloads ) + ' file downloads' )
                        
                        self.Write( 'import_file', HC.LOW_PRIORITY, file )
                        
                        HC.pubsub.pub( 'content_updates_data', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, CC.LOCAL_FILE_SERVICE_IDENTIFIER, ( hash, ) ) ] )
                        HC.pubsub.pub( 'content_updates_gui', [ HC.ContentUpdate( CC.CONTENT_UPDATE_ADD, CC.LOCAL_FILE_SERVICE_IDENTIFIER, ( hash, ) ) ] )
                        
                        self.pub( 'log_message', 'download files daemon', 'downloaded ' + hash.encode( 'hex' ) + ' from ' + file_repository.GetServiceIdentifier().GetName() )
                        
                        time.sleep( 0.25 )
                        
                    
                
            except: pass # if bad download, the repo gets dinged an error. no need to do anything here
            
        
        if num_downloads == 0: HC.pubsub.pub( 'downloads_status', 'no file downloads' )
        elif num_downloads > 0: HC.pubsub.pub( 'downloads_status', HC.ConvertIntToPrettyString( num_downloads ) + ' inactive file downloads' )
        
    
    def DAEMONDownloadThumbnails( self ):
        
        service_identifiers = self.Read( 'service_identifiers', HC.LOW_PRIORITY, ( HC.FILE_REPOSITORY, ) )
        
        thumbnail_hashes_i_have = { path.decode( 'hex' ) for path in dircache.listdir( HC.CLIENT_THUMBNAILS_DIR ) if not path.endswith( '_resized' ) }
        
        for service_identifier in service_identifiers:
            
            thumbnail_hashes_i_should_have = self.Read( 'thumbnail_hashes_i_should_have', HC.LOW_PRIORITY, service_identifier )
            
            thumbnail_hashes_i_need = list( thumbnail_hashes_i_should_have - thumbnail_hashes_i_have )
            
            if len( thumbnail_hashes_i_need ) > 0:
                
                try: file_repository = self.Read( 'service', HC.LOW_PRIORITY, service_identifier )
                except: continue
                
                if file_repository.CanDownload():
                    
                    try:
                        
                        connection = file_repository.GetConnection()
                        
                        num_per_round = 50
                        
                        for i in range( 0, len( thumbnail_hashes_i_need ), num_per_round ):
                            
                            if HC.shutdown: return
                            
                            thumbnails = []
                            
                            for hash in thumbnail_hashes_i_need[ i : i + num_per_round ]: thumbnails.append( ( hash, connection.Get( 'thumbnail', hash = hash.encode( 'hex' ) ) ) )
                            
                            wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                            
                            self.Write( 'thumbnails', HC.LOW_PRIORITY, thumbnails )
                            
                            self.pub( 'add_thumbnail_count', service_identifier, len( thumbnails ) )
                            
                            thumbnail_hashes_i_have.update( { hash for ( hash, thumbnail ) in thumbnails } )
                            
                            self.pub( 'log_message', 'download thumbnails daemon', 'downloaded ' + str( len( thumbnails ) ) + ' thumbnails from ' + service_identifier.GetName() )
                            
                            time.sleep( 0.25 )
                            
                        
                    except: pass # if bad download, the repo gets dinged an error. no need to do anything here
                    
                
            
        
    
    def DAEMONFlushServiceUpdates( self, update_log ): self.Write( 'service_updates', HC.HIGH_PRIORITY, update_log )
    
    def DAEMONResizeThumbnails( self ):
        
        all_thumbnail_paths = dircache.listdir( HC.CLIENT_THUMBNAILS_DIR )
        
        full_size_thumbnail_paths = { path for path in all_thumbnail_paths if not path.endswith( '_resized' ) }
        
        resized_thumbnail_paths = { path for path in all_thumbnail_paths if path.endswith( '_resized' ) }
        
        thumbnail_paths_to_render = full_size_thumbnail_paths.difference( resized_thumbnail_paths )
        
        i = 0
        
        limit = max( 100, len( thumbnail_paths_to_render ) / 10 )
        
        for thumbnail_path in thumbnail_paths_to_render:
            
            try:
                
                with open( HC.CLIENT_THUMBNAILS_DIR + os.path.sep + thumbnail_path, 'rb' ) as f: thumbnail = f.read()
                
                thumbnail_resized = HydrusImageHandling.GenerateThumbnailFileFromFile( thumbnail, self._options[ 'thumbnail_dimensions' ] )
                
                thumbnail_resized_path_to = thumbnail_path + '_resized'
                
                with open( HC.CLIENT_THUMBNAILS_DIR + os.path.sep + thumbnail_resized_path_to, 'wb' ) as f: f.write( thumbnail_resized )
                
            except: print( traceback.format_exc() )
            
            time.sleep( 1 )
            
            i += 1
            
            if i > limit: break
            
            if HC.shutdown: break
            
        
    
    def DAEMONSynchroniseAccounts( self ):
        
        services = self.Read( 'services', HC.LOW_PRIORITY, HC.RESTRICTED_SERVICES )
        
        do_notify = False
        
        for service in services:
            
            account = service.GetAccount()
            service_identifier = service.GetServiceIdentifier()
            credentials = service.GetCredentials()
            
            if not account.IsBanned() and account.IsStale() and credentials.HasAccessKey() and not service.HasRecentError():
                
                try:
                    
                    connection = service.GetConnection()
                    
                    connection.Get( 'account' )
                    
                    HC.pubsub.pub( 'log_message', 'synchronise accounts daemon', 'successfully refreshed account for ' + service_identifier.GetName() )
                    
                    do_notify = True
                    
                except Exception as e:
                    
                    name = service_identifier.GetName()
                    
                    error_message = 'failed to refresh account for ' + name + ':' + os.linesep + os.linesep + unicode( e )
                    
                    HC.pubsub.pub( 'log_error', 'synchronise accounts daemon', error_message )
                    
                    print( error_message )
                    
                
            
        
        if do_notify: HC.pubsub.pub( 'notify_new_permissions' )
        
    
    def DAEMONSynchroniseMessages( self ):
        
        service_identifiers = self.Read( 'service_identifiers', HC.LOW_PRIORITY, ( HC.MESSAGE_DEPOT, ) )
        
        for service_identifier in service_identifiers:
            
            try:
                
                name = service_identifier.GetName()
                
                service_type = service_identifier.GetType()
                
                try: service = self.Read( 'service', HC.LOW_PRIORITY, service_identifier )
                except: continue
                
                if service.CanCheck():
                    
                    contact = service.GetContact()
                    
                    connection = service.GetConnection()
                    
                    private_key = service.GetPrivateKey()
                    
                    # is the account associated?
                    
                    if not contact.HasPublicKey():
                        
                        try:
                            
                            public_key = HydrusMessageHandling.GetPublicKey( private_key )
                            
                            connection.Post( 'contact', public_key = public_key )
                            
                            self.Write( 'contact_associated', HC.HIGH_PRIORITY, service_identifier )
                            
                            service = self.Read( 'service', HC.LOW_PRIORITY, service_identifier )
                            
                            contact = service.GetContact()
                            
                            HC.pubsub.pub( 'log_message', 'synchronise messages daemon', 'associated public key with account at ' + service_identifier.GetName() )
                            
                        except:
                            
                            continue
                            
                        
                    
                    # see if there are any new message_keys to download or statuses
                    
                    last_check = service.GetLastCheck()
                    
                    ( message_keys, statuses ) = connection.Get( 'message_info_since', since = last_check )
                    
                    decrypted_statuses = []
                    
                    for status in statuses:
                        
                        try: decrypted_statuses.append( HydrusMessageHandling.UnpackageDeliveredStatus( status, private_key ) )
                        except: pass
                        
                    
                    new_last_check = int( time.time() ) - 5
                    
                    self.Write( 'message_info_since', HC.LOW_PRIORITY, service_identifier, message_keys, decrypted_statuses, new_last_check )
                    
                    if len( message_keys ) > 0: HC.pubsub.pub( 'log_message', 'synchronise messages daemon', 'checked ' + service_identifier.GetName() + ' up to ' + HC.ConvertTimestampToPrettyTime( new_last_check ) + ', finding ' + str( len( message_keys ) ) + ' new messages' )
                    
                
                self.WaitUntilGoodTimeToUseDBThread()
                
                # try to download any messages that still need downloading
                
                if service.CanDownload():
                    
                    serverside_message_keys = self.Read( 'message_keys_to_download', HC.LOW_PRIORITY, service_identifier )
                    
                    if len( serverside_message_keys ) > 0:
                        
                        connection = service.GetConnection()
                        
                        private_key = service.GetPrivateKey()
                        
                        num_processed = 0
                        
                        for serverside_message_key in serverside_message_keys:
                            
                            self.WaitUntilGoodTimeToUseDBThread()
                            
                            try:
                                
                                encrypted_message = connection.Get( 'message', message_key = serverside_message_key.encode( 'hex' ) )
                                
                                message = HydrusMessageHandling.UnpackageDeliveredMessage( encrypted_message, private_key )
                                
                                self.Write( 'message', HC.LOW_PRIORITY, message, serverside_message_key = serverside_message_key )
                                
                                num_processed += 1
                                
                            except Exception as e:
                                
                                if issubclass( e, httplib.HTTPException ): break # it was an http error; try again later
                                
                            
                        
                        if num_processed > 0:
                            
                            HC.pubsub.pub( 'log_message', 'synchronise messages daemon', 'downloaded and parsed ' + str( num_processed ) + ' messages from ' + service_identifier.GetName() )
                            
                        
                    
                
            except Exception as e:
                
                error_message = 'failed to check ' + name + ':' + os.linesep + os.linesep + unicode( e )
                
                HC.pubsub.pub( 'log_error', 'synchronise messages daemon', error_message )
                
                print( error_message )
                
            
        
        self.Write( 'flush_message_statuses', HC.LOW_PRIORITY )
        
        # send messages to recipients and update my status to sent/failed
        
        messages_to_send = self.Read( 'messages_to_send', HC.LOW_PRIORITY )
        
        for ( message_key, contacts_to ) in messages_to_send:
            
            message = self.Read( 'transport_message', HC.LOW_PRIORITY, message_key )
            
            contact_from = message.GetContactFrom()
            
            from_anon = contact_from is None or contact_from.GetName() == 'Anonymous'
            
            if not from_anon:
                
                my_public_key = contact_from.GetPublicKey()
                my_contact_key = contact_from.GetContactKey()
                
                my_message_depot = self.Read( 'service', HC.LOW_PRIORITY, contact_from )
                
                from_connection = my_message_depot.GetConnection()
                
            
            service_status_updates = []
            local_status_updates = []
            
            for contact_to in contacts_to:
                
                public_key = contact_to.GetPublicKey()
                contact_key = contact_to.GetContactKey()
                
                encrypted_message = HydrusMessageHandling.PackageMessageForDelivery( message, public_key )
                
                try:
                    
                    to_connection = contact_to.GetConnection()
                    
                    to_connection.Post( 'message', message = encrypted_message, contact_key = contact_key )
                    
                    status = 'sent'
                    
                except:
                    
                    print( traceback.format_exc() )
                    
                    HC.pubsub.pub( 'message', 'Sending a message failed: ' + os.linesep + traceback.format_exc() )
                    
                    status = 'failed'
                    
                
                status_key = hashlib.sha256( contact_key + message_key ).digest()
                
                if not from_anon: service_status_updates.append( ( status_key, HydrusMessageHandling.PackageStatusForDelivery( ( message_key, contact_key, status ), my_public_key ) ) )
                
                local_status_updates.append( ( contact_key, status ) )
                
            
            if not from_anon: from_connection.Post( 'message_statuses', contact_key = my_contact_key, statuses = service_status_updates )
            
            self.Write( 'message_statuses', HC.LOW_PRIORITY, message_key, local_status_updates )
            
        
        self.Read( 'status_num_inbox', HC.LOW_PRIORITY )
        
    
    def DAEMONSynchroniseRepositories( self ):
        
        service_identifiers = self.Read( 'service_identifiers', HC.LOW_PRIORITY, HC.REPOSITORIES )
        
        for service_identifier in service_identifiers:
            
            if HC.shutdown: raise Exception( 'Application shutting down!' )
            
            try:
                
                name = service_identifier.GetName()
                
                service_type = service_identifier.GetType()
                
                try: service = self.Read( 'service', HC.LOW_PRIORITY, service_identifier )
                except: continue
                
                if service.CanUpdate():
                    
                    connection = service.GetConnection()
                    
                    while service.CanUpdate():
                        
                        if HC.shutdown: raise Exception( 'Application shutting down!' )
                        
                        first_begin = service.GetFirstBegin()
                        
                        next_begin = service.GetNextBegin()
                        
                        if first_begin == 0: update_index_string = 'initial update'
                        else: update_index_string = 'update ' + str( ( ( next_begin - first_begin ) / HC.UPDATE_DURATION ) + 1 )
                        
                        HC.pubsub.pub( 'service_status', 'Downloading and parsing ' + update_index_string + ' for ' + name )
                        
                        update = connection.Get( 'update', begin = next_begin )
                        
                        if service_type == HC.TAG_REPOSITORY:
                            
                            HC.pubsub.pub( 'service_status', 'Generating tags for ' + name )
                            
                            self.Write( 'generate_tag_ids', HC.LOW_PRIORITY, update.GetTags() )
                            
                        
                        updates = update.SplitIntoSubUpdates()
                        
                        num_updates = len( updates )
                        
                        for ( i, sub_update ) in enumerate( updates ):
                            
                            wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                            
                            self.WaitUntilGoodTimeToUseDBThread()
                            
                            HC.pubsub.pub( 'service_status', 'Processing ' + update_index_string + ' part ' + str( i + 1 ) + '/' + str( num_updates ) + ' for ' + name )
                            
                            self.Write( 'update', HC.LOW_PRIORITY, service_identifier, sub_update )
                            
                        
                        HC.pubsub.pub( 'log_message', 'synchronise repositories daemon', 'successfully updated ' + service_identifier.GetName() + ' to ' + update_index_string + ' (' + HC.ConvertTimestampToPrettyTime( update.GetEnd() ) + ')' )
                        
                        HC.pubsub.pub( 'notify_new_pending' )
                        
                        now = int( time.time() )
                        
                        for ( news, timestamp ) in update.GetNews():
                            
                            if now - timestamp < 86400 * 7: HC.pubsub.pub( 'message', service_identifier.GetName() + ' at ' + time.ctime( timestamp ) + ':' + os.linesep + os.linesep + news )
                            
                        
                        try: service = self.Read( 'service', HC.LOW_PRIORITY, service_identifier )
                        except: break
                        
                    
                    HC.pubsub.pub( 'service_status', '' )
                    
                
            except Exception as e:
                
                error_message = 'failed to update ' + name + ':' + os.linesep + os.linesep + unicode( e )
                
                HC.pubsub.pub( 'log_error', 'synchronise repositories daemon', error_message )
                
                HC.pubsub.pub( 'service_status', error_message )
                
                print( error_message )
                print( traceback.format_exc() )
                
            
        
    
    def ProcessRequest( self, request_type, request, request_args ):
        
        response = HC.ResponseContext( 200 )
        
        if request_type == HC.GET:
            
            if request == 'file':
                
                hash = request_args[ 'hash' ]
                
                file = self.Read( 'file', HC.HIGH_PRIORITY, hash )
                
                mime = HC.GetMimeFromString( file )
                
                response = HC.ResponseContext( 200, mime = mime, body = file, filename = hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ] )
                
            elif request == 'thumbnail':
                
                hash = request_args[ 'hash' ]
                
                thumbnail = self.Read( 'thumbnail', HC.HIGH_PRIORITY, hash )
                
                mime = HC.GetMimeFromString( thumbnail )
                
                response = HC.ResponseContext( 200, mime = mime, body = thumbnail, filename = hash.encode( 'hex' ) + '_thumbnail' + HC.mime_ext_lookup[ mime ] )
                
            
        elif request_type == HC.POST: pass # nothing here yet!
        
        return response
        
    
    def _MainLoop_JobInternal( self, c, job ):
        
        action = job.GetAction()
        
        job_type = job.GetType()
        
        args = job.GetArgs()
        
        kwargs = job.GetKWArgs()
        
        if job_type in ( 'read', 'read_write' ):
            
            if job_type == 'read': c.execute( 'BEGIN DEFERRED' )
            else: c.execute( 'BEGIN IMMEDIATE' )
            
            try:
                
                result = self._MainLoop_Read( c, action, args, kwargs )
                
                c.execute( 'COMMIT' )
                
                for ( topic, args, kwargs ) in self._pubsubs: HC.pubsub.pub( topic, *args, **kwargs )
                
                if action != 'do_file_query': job.PutResult( result )
                
            except Exception as e:
                
                c.execute( 'ROLLBACK' )
                
                print( 'while attempting a read on the database, the hydrus client encountered the following problem:' )
                print( traceback.format_exc() )
                
                ( exception_type, value, tb ) = sys.exc_info()
                
                new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
                
                job.PutResult( new_e )
                
            
        elif job_type in ( 'write', 'write_special' ):
            
            if job_type == 'write': c.execute( 'BEGIN IMMEDIATE' )
            
            try:
                
                self._MainLoop_Write( c, action, args, kwargs )
                
                if job_type == 'write': c.execute( 'COMMIT' )
                
                for ( topic, args, kwargs ) in self._pubsubs: HC.pubsub.pub( topic, *args, **kwargs )
                
            except Exception as e:
                
                if job_type == 'write': c.execute( 'ROLLBACK' )
                
                print( 'while attempting a write on the database, the hydrus client encountered the following problem:' )
                print( traceback.format_exc() )
                
                action = job.GetAction()
                
                ( exception_type, value, tb ) = sys.exc_info()
                
                new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
                
                if action not in ( 'import_file', 'import_file_from_page' ): HC.pubsub.pub( 'exception', new_e )
                
            
        
    
    def _MainLoop_Read( self, c, action, args, kwargs ):
        
        if action == '4chan_pass': result = self._Get4chanPass( c, *args, **kwargs )
        elif action == 'all_downloads': result = self._GetAllDownloads( c, *args, **kwargs )
        elif action == 'autocomplete_contacts': result = self._GetAutocompleteContacts( c, *args, **kwargs )
        elif action == 'autocomplete_tags': result = self._GetAutocompleteTags( c, *args, **kwargs )
        elif action == 'boorus': result = self._GetBoorus( c, *args, **kwargs )
        elif action == 'contact_names': result = self._GetContactNames( c, *args, **kwargs )
        elif action == 'do_file_query': result = self._DoFileQuery( c, *args, **kwargs )
        elif action == 'do_message_query': result = self._DoMessageQuery( c, *args, **kwargs )
        elif action == 'favourite_custom_filter_actions': result = self._GetFavouriteCustomFilterActions( c, *args, **kwargs )
        elif action == 'file': result = self._GetFile( *args, **kwargs )
        elif action == 'file_system_predicates': result = self._GetFileSystemPredicates( c, *args, **kwargs )
        elif action == 'hydrus_sessions': result = self._GetHydrusSessions( c, *args, **kwargs )
        elif action == 'identities_and_contacts': result = self._GetIdentitiesAndContacts( c, *args, **kwargs )
        elif action == 'identities': result = self._GetIdentities( c, *args, **kwargs )
        elif action == 'imageboards': result = self._GetImageboards( c, *args, **kwargs )
        elif action == 'md5_status': result = self._GetMD5Status( c, *args, **kwargs )
        elif action == 'media_results': result = self._GetMediaResultsFromHashes( c, *args, **kwargs )
        elif action == 'message_keys_to_download': result = self._GetMessageKeysToDownload( c, *args, **kwargs )
        elif action == 'message_system_predicates': result = self._GetMessageSystemPredicates( c, *args, **kwargs )
        elif action == 'messages_to_send': result = self._GetMessagesToSend( c, *args, **kwargs )
        elif action == 'news': result = self._GetNews( c, *args, **kwargs )
        elif action == 'nums_pending': result = self._GetNumsPending( c, *args, **kwargs )
        elif action == 'options': result = self._options
        elif action == 'pending': result = self._GetPending( c, *args, **kwargs )
        elif action == 'pixiv_account': result = self._GetPixivAccount( c, *args, **kwargs )
        elif action == 'ratings_filter': result = self._GetRatingsFilter( c, *args, **kwargs )
        elif action == 'ratings_media_result': result = self._GetRatingsMediaResult( c, *args, **kwargs )
        elif action == 'resolution': result = self._GetResolution( c, *args, **kwargs )
        elif action == 'service': result = self._GetService( c, *args, **kwargs )
        elif action == 'service_identifiers': result = self._GetServiceIdentifiers( c, *args, **kwargs )
        elif action == 'service_info': result = self._GetServiceInfo( c, *args, **kwargs )
        elif action == 'services': result = self._GetServices( c, *args, **kwargs )
        elif action == 'shutdown_timestamps': result = self._GetShutdownTimestamps( c, *args, **kwargs )
        elif action == 'status_num_inbox': result = self._DoStatusNumInbox( c, *args, **kwargs )
        elif action == 'tag_service_precedence': result = self._tag_service_precedence
        elif action == 'thumbnail': result = self._GetThumbnail( *args, **kwargs )
        elif action == 'thumbnail_hashes_i_should_have': result = self._GetThumbnailHashesIShouldHave( c, *args, **kwargs )
        elif action == 'transport_message': result = self._GetTransportMessage( c, *args, **kwargs )
        elif action == 'transport_messages_from_draft': result = self._GetTransportMessagesFromDraft( c, *args, **kwargs )
        elif action == 'url_status': result = self._GetURLStatus( c, *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _MainLoop_Write( self, c, action, args, kwargs ):
        
        if action == '4chan_pass': self._Set4chanPass( c, *args, **kwargs )
        elif action == 'add_downloads': self._AddDownloads( c, *args, **kwargs )
        elif action == 'add_uploads': self._AddUploads( c, *args, **kwargs )
        elif action == 'archive_conversation': self._ArchiveConversation( c, *args, **kwargs )
        elif action == 'contact_associated': self._AssociateContact( c, *args, **kwargs )
        elif action == 'content_updates': self._ProcessContentUpdates( c, *args, **kwargs )
        elif action == 'copy_files': self._CopyFiles( *args, **kwargs )
        elif action == 'delete_conversation': self._DeleteConversation( c, *args, **kwargs )
        elif action == 'delete_draft': self._DeleteDraft( c, *args, **kwargs )
        elif action == 'delete_orphans': self._DeleteOrphans( c, *args, **kwargs )
        elif action == 'delete_pending': self._DeletePending( c, *args, **kwargs )
        elif action == 'delete_hydrus_session_key': self._DeleteHydrusSessionKey( c, *args, **kwargs )
        elif action == 'draft_message': self._DraftMessage( c, *args, **kwargs )
        elif action == 'export_files': self._ExportFiles( *args, **kwargs )
        elif action == 'fatten_autocomplete_cache': self._FattenAutocompleteCache( c, *args, **kwargs )
        elif action == 'favourite_custom_filter_actions': self._SetFavouriteCustomFilterActions( c, *args, **kwargs )
        elif action == 'flush_message_statuses': self._FlushMessageStatuses( c, *args, **kwargs )
        elif action == 'generate_tag_ids': self._GenerateTagIdsEfficiently( c, *args, **kwargs )
        elif action == 'hydrus_session': result = self._AddHydrusSession( c, *args, **kwargs )
        elif action == 'import_file': self._ImportFile( c, *args, **kwargs )
        elif action == 'import_file_from_page': self._ImportFilePage( c, *args, **kwargs )
        elif action == 'inbox_conversation': self._InboxConversation( c, *args, **kwargs )
        elif action == 'message': self._AddMessage( c, *args, **kwargs )
        elif action == 'message_info_since': self._AddMessageInfoSince( c, *args, **kwargs )
        elif action == 'message_statuses': self._UpdateMessageStatuses( c, *args, **kwargs )
        elif action == 'petition_files': self._PetitionFiles( c, *args, **kwargs )
        elif action == 'pixiv_account': self._SetPixivAccount( c, *args, **kwargs )
        elif action == 'reset_service': self._ResetService( c, *args, **kwargs )
        elif action == 'save_options': self._SaveOptions( c, *args, **kwargs )
        elif action == 'service_updates': self._AddServiceUpdates( c, *args, **kwargs )
        elif action == 'session': self._AddSession( c, *args, **kwargs )
        elif action == 'set_password': self._SetPassword( c, *args, **kwargs )
        elif action == 'set_tag_service_precedence': self._SetTagServicePrecedence( c, *args, **kwargs )
        elif action == 'thumbnails': self._AddThumbnails( c, *args, **kwargs )
        elif action == 'update': self._AddUpdate( c, *args, **kwargs )
        elif action == 'update_boorus': self._UpdateBoorus( c, *args, **kwargs )
        elif action == 'update_contacts': self._UpdateContacts( c, *args, **kwargs )
        elif action == 'update_imageboards': self._UpdateImageboards( c, *args, **kwargs )
        elif action == 'update_server_services': self._UpdateServerServices( c, *args, **kwargs )
        elif action == 'update_services': self._UpdateServices( c, *args, **kwargs )
        elif action == 'upload_pending': self._UploadPending( c, *args, **kwargs )
        elif action == 'vacuum': self._Vacuum()
        else: raise Exception( 'db received an unknown write command: ' + action )
        
    
    def MainLoop( self ):
        
        ( db, c ) = self._GetDBCursor()
        
        while not ( HC.shutdown and self._jobs.empty() ):
            
            try:
                
                ( priority, job ) = self._jobs.get( timeout = 1 )
                
                self._pubsubs = []
                
                try:
                    
                    if isinstance( job, HC.JobServer ):
                        
                        ( service_identifier, account_identifier, ip, request_type, request, request_args, request_length ) = job.GetInfo()
                        
                        # for now, we don't care about most of this here
                        # the server has already verified the ip and so on
                        
                        # do the server first before you do it here!
                        # just leave process request for now
                        
                    else: self._MainLoop_JobInternal( c, job )
                    
                except:
                    
                    self._jobs.put( ( priority, job ) ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
            except: pass # no jobs this second; let's see if we should shutdown
            
        
    
    def Read( self, action, priority, *args, **kwargs ):
        
        if action in ( 'service_info', 'system_predicates' ): job_type = 'read_write'
        else: job_type = 'read'
        
        job = HC.JobInternal( action, job_type, *args, **kwargs )
        
        if HC.shutdown: raise Exception( 'Application has shutdown!' )
        
        self._jobs.put( ( priority + 1, job ) ) # +1 so all writes of equal priority can clear out first
        
        if action != 'do_file_query': return job.GetResult()
        
    
    def ReadFile( self, hash ):
        
        return self._GetFile( hash )
        
    
    def ReadThumbnail( self, hash, full_size = False ):
        
        return self._GetThumbnail( hash, full_size )
        
    
    def WaitUntilGoodTimeToUseDBThread( self ):
        
        while True:
            
            if HC.shutdown: raise Exception( 'Client shutting down!' )
            elif self._jobs.empty(): return
            else: time.sleep( 0.04 )
            
        
    
    def Write( self, action, priority, *args, **kwargs ):
        
        if action == 'vacuum': job_type = 'write_special'
        else: job_type = 'write'
        
        job = HC.JobInternal( action, job_type, *args, **kwargs )
        
        if HC.shutdown: raise Exception( 'Application has shutdown!' )
        
        self._jobs.put( ( priority, job ) )
        
    