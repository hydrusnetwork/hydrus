import collections
import dircache
import hashlib
import httplib
import itertools
import HydrusConstants as HC
import HydrusDownloading
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusMessageHandling
import HydrusNATPunch
import HydrusServer
import HydrusTagArchive
import HydrusTags
import HydrusThreading
import ClientConstants as CC
import ClientConstantsMessages
import os
import Queue
import random
import shutil
import sqlite3
import stat
import sys
import threading
import time
import traceback
import wx
import yaml

YAML_DUMP_ID_SINGLE = 0
YAML_DUMP_ID_REMOTE_BOORU = 1
YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS = 2
YAML_DUMP_ID_GUI_SESSION = 3
YAML_DUMP_ID_IMAGEBOARD = 4
YAML_DUMP_ID_IMPORT_FOLDER = 5
YAML_DUMP_ID_EXPORT_FOLDER = 6
YAML_DUMP_ID_SUBSCRIPTION = 7
YAML_DUMP_ID_LOCAL_BOORU = 8

class FileDB( object ):
    
    def _AddThumbnails( self, c, thumbnails ):
        
        for ( hash, thumbnail ) in thumbnails:
            
            thumbnail_path = CC.GetExpectedThumbnailPath( hash, True )
            
            with open( thumbnail_path, 'wb' ) as f: f.write( thumbnail )
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( thumbnail_path, HC.options[ 'thumbnail_dimensions' ] )
            
            thumbnail_resized_path = CC.GetExpectedThumbnailPath( hash, False )
            
            with open( thumbnail_resized_path, 'wb' ) as f: f.write( thumbnail_resized )
            
            phash = HydrusImageHandling.GeneratePerceptualHash( thumbnail_path )
            
            hash_id = self._GetHashId( c, hash )
            
            c.execute( 'INSERT OR REPLACE INTO perceptual_hashes ( hash_id, phash ) VALUES ( ?, ? );', ( hash_id, sqlite3.Binary( phash ) ) )
            
        
        hashes = { hash for ( hash, thumbnail ) in thumbnails }
        
        self.pub_after_commit( 'new_thumbnails', hashes )
        
    
    def _CopyFiles( self, c, hashes ):
        
        if len( hashes ) > 0:
            
            export_dir = HC.TEMP_DIR
            
            if not os.path.exists( export_dir ): os.mkdir( export_dir )
            
            error_messages = set()
            
            paths = []
            
            for hash in hashes:
                
                try:
                    
                    hash_id = self._GetHashId( c, hash )
                    
                    path_from = CC.GetFilePath( hash )
                    
                    filename = os.path.basename( path_from )
                    
                    path_to = export_dir + os.path.sep + filename
                    
                    shutil.copy( path_from, path_to )
                    
                    os.chmod( path_to, stat.S_IWRITE )
                    
                    paths.append( path_to )
                    
                except Exception as e: error_messages.add( HC.u( e ) )
                
            
            self.pub_after_commit( 'clipboard', 'paths', paths )
            
            if len( error_messages ) > 0: raise Exception( 'Some of the file exports failed with the following error message(s):' + os.linesep + os.linesep.join( error_messages ) )
            
        
    
    def _GenerateHashIdsEfficiently( self, c, hashes ):
        
        hashes_not_in_db = set( hashes )
        
        for i in range( 0, len( hashes ), 250 ): # there is a limit on the number of parameterised variables in sqlite, so only do a few at a time
            
            hashes_subset = hashes[ i : i + 250 ]
            
            hashes_not_in_db.difference_update( [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes WHERE hash IN (' + ','.join( '?' * len( hashes_subset ) ) + ');', [ sqlite3.Binary( hash ) for hash in hashes_subset ] ) ] )
            
        
        if len( hashes_not_in_db ) > 0: c.executemany( 'INSERT INTO hashes ( hash ) VALUES( ? );', [ ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ] )
        
    
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
        
        path = CC.GetThumbnailPath( hash, full_size )
        
        with open( path, 'rb' ) as f: thumbnail = f.read()
        
        return thumbnail
        
    
class MessageDB( object ):
    
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
                
                HC.ShowText( 'received a message that did not verify' )
                
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
                    
                    temp_path = HC.GetTempPath()
                    
                    with open( temp_path, 'wb' ) as f: f.write( temp_path )
                    
                    try:
                        
                        ( result, hash ) = self._ImportFile( c, temp_path, override_deleted = True ) # what if the file fails?
                        
                        attachment_hashes.append( hash )
                        
                    except: pass
                    
                    try: os.remove( temp_path )
                    except: pass # sometimes this fails, I think due to old handles not being cleaned up fast enough. np--it'll be cleaned up later
                    
                
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
            
            self.pub_after_commit( 'new_message', conversation_key, message )
            
        
        if serverside_message_key is not None:
            
            serverside_message_id = self._GetMessageId( c, serverside_message_key )
            
            c.execute( 'DELETE FROM message_downloads WHERE message_id = ?;', ( serverside_message_id, ) )
            
        
    
    def _AddMessageInfoSince( self, c, service_key, serverside_message_keys, statuses, new_last_check ):
        
        # message_keys
        
        service_id = self._GetServiceId( c, service_key )
        
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
        
        self.pub_after_commit( 'archive_conversation_data', conversation_key )
        self.pub_after_commit( 'archive_conversation_gui', conversation_key )
        
        self._DoStatusNumInbox( c )
        
    
    def _AssociateContact( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service = self._GetService( c, service_id )
        
        private_key = service.GetPrivateKey()
        
        public_key = HydrusEncryption.GetPublicKey( private_key )
        
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
        
        self.pub_after_commit( 'delete_conversation_data', conversation_key )
        self.pub_after_commit( 'delete_conversation_gui', conversation_key )
        
        self._DoStatusNumInbox( c )
        
    
    def _DeleteDraft( self, c, draft_key ):
        
        message_id = self._GetMessageId( c, draft_key )
        
        c.execute( 'DELETE FROM message_keys WHERE message_id = ?;', ( message_id, ) )
        c.execute( 'DELETE FROM message_bodies WHERE docid = ?;', ( message_id, ) )
        c.execute( 'DELETE FROM conversation_subjects WHERE docid = ?;', ( message_id, ) )
        
        self.pub_after_commit( 'delete_draft_data', draft_key )
        self.pub_after_commit( 'delete_draft_gui', draft_key )
        self.pub_after_commit( 'notify_check_messages' )
        
    
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
            
            sql_predicates = [ '( contact_id_from = ' + HC.u( contact_id ) + ' OR contact_id_to = ' + HC.u( contact_id ) + ' )' ]
            
            if name != 'Anonymous':
                
                service = self._GetService( c, identity )
                
                if not service.ReceivesAnon(): sql_predicates.append( 'contact_id_from != 1' )
                
            
            if status is not None:
                
                if status == 'unread': status = 'sent'
                
                status_id = self._GetStatusId( c, status )
                
                sql_predicates.append( '( contact_id_to = ' + HC.u( contact_id ) + ' AND status_id = ' + HC.u( status_id ) + ')' )
                
            
            if contact_from is not None:
                
                contact_id_from = self._GetContactId( c, contact_from )
                
                sql_predicates.append( 'contact_id_from = ' + HC.u( contact_id_from ) )
                
            
            if contact_to is not None:
                
                contact_id_to = self._GetContactId( c, contact_to )
                
                sql_predicates.append( 'contact_id_to = ' + HC.u( contact_id_to ) )
                
            
            if contact_started is not None:
                
                contact_id_started = self._GetContactId( c, contact_started )
                
                sql_predicates.append( 'conversation_id = message_id AND contact_id_from = ' + HC.u( contact_id_started ) )
                
            
            if min_timestamp is not None: sql_predicates.append( 'timestamp >= ' + HC.u( min_timestamp ) )
            if max_timestamp is not None: sql_predicates.append( 'timestamp <= ' + HC.u( max_timestamp ) )
            
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
        
        self.pub_after_commit( 'message_query_done', query_key, conversations )
        
    
    def _DoStatusNumInbox( self, c ):
        
        convo_ids = { id for ( id, ) in c.execute( 'SELECT conversation_id FROM messages, message_inbox USING ( message_id );' ) }
        
        num_inbox = len( convo_ids )
        
        if num_inbox == 0: inbox_string = 'message inbox empty'
        else: inbox_string = HC.u( num_inbox ) + ' in message inbox'
        
        self.pub_after_commit( 'inbox_status', inbox_string )
        
    
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
        
        self.pub_after_commit( 'draft_saved', draft_key, draft_message )
        
    
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
            
            self.pub_after_commit( 'message_statuses_data', message_key, status_updates )
            self.pub_after_commit( 'message_statuses_gui', message_key, status_updates )
            
        
    
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
                    
                    while c.execute( 'SELECT 1 FROM contacts WHERE name = ?;', ( name, ) ).fetchone() is not None: name += HC.u( random.randint( 0, 9 ) )
                    
                
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
        
    
    def _GetMessageKeysToDownload( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
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
        
        files = []
        
        for hash in attachment_hashes:
            
            path = CC.GetFilePath( hash )
            
            with open( path, 'rb' ) as f: file = f.read()
            
            files.append( file )
            
        
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
        
        files = []
        
        for hash in attachment_hashes:
            
            path = CC.GetFilePath( hash )
            
            with open( path, 'rb' ) as f: file = f.read()
            
            files.append( file )
            
        
        contact_id_from = self._GetContactId( c, contact_from )
        
        if contact_from.GetName() == 'Anonymous':
            
            contact_from = None
            message_depot = None
            private_key = None
            
        else:
            
            message_depot = self._GetService( c, contact_from )
            private_key = message_depot.GetPrivateKey()
            
        
        timestamp = HC.GetNow()
        
        contacts_to = [ self._GetContact( c, contact_name_to ) for contact_name_to in contact_names_to ]
        
        if conversation_key == draft_key: conversation_key = None
        
        if recipients_visible: messages = [ HydrusMessageHandling.Message( conversation_key, contact_from, contacts_to, subject, body, timestamp, files = files, private_key = private_key ) ]
        else: messages = [ HydrusMessageHandling.Message( conversation_key, contact_from, [ contact_to ], subject, body, timestamp, files = files, private_key = private_key ) for contact_to in contacts_to ]
        
        return messages
        
    
    def _InboxConversation( self, c, conversation_key ):
        
        conversation_id = self._GetMessageId( c, conversation_key )
        
        inserts = c.execute( 'SELECT message_id FROM messages WHERE conversation_id = ?;', ( conversation_id, ) ).fetchall()
        
        c.executemany( 'INSERT OR IGNORE INTO message_inbox ( message_id ) VALUES ( ? );', inserts )
        
        self.pub_after_commit( 'inbox_conversation_data', conversation_key )
        self.pub_after_commit( 'inbox_conversation_gui', conversation_key )
        
        self._DoStatusNumInbox( c )
        
    
    def _UpdateContacts( self, c, edit_log ):
        
        for ( action, details ) in edit_log:
            
            if action == HC.ADD:
                
                contact = details
                
                self._AddContact( c, contact )
                
            elif action == HC.DELETE:
                
                name = details
                
                result = c.execute( 'SELECT 1 FROM contacts WHERE name = ? AND NOT EXISTS ( SELECT 1 FROM message_destination_map WHERE contact_id_to = contact_id ) AND NOT EXISTS ( SELECT 1 FROM messages WHERE contact_id_from = contact_id );', ( name, ) ).fetchone()
                
                if result is not None: c.execute( 'DELETE FROM contacts WHERE name = ?;', ( name, ) )
                
            elif action == HC.EDIT:
                
                ( old_name, contact ) = details
                
                try:
                    
                    contact_id = self._GetContactId( c, old_name )
                    
                    ( public_key, name, host, port ) = contact.GetInfo()
                    
                    contact_key = contact.GetContactKey()
                    
                    if public_key is not None: contact_key = sqlite3.Binary( contact_key )
                    
                    c.execute( 'UPDATE contacts SET contact_key = ?, public_key = ?, name = ?, host = ?, port = ? WHERE contact_id = ?;', ( contact_key, public_key, name, host, port, contact_id ) )
                    
                except: pass
                
            
        
        self.pub_after_commit( 'notify_new_contacts' )
        
    
    def _UpdateMessageStatuses( self, c, message_key, status_updates ):
        
        message_id = self._GetMessageId( c, message_key )
        
        updates = []
        
        for ( contact_key, status ) in status_updates:
            
            contact_id = self._GetContactId( c, contact_key )
            status_id = self._GetStatusId( c, status )
            
            updates.append( ( contact_id, status_id ) )
            
        
        c.executemany( 'UPDATE message_destination_map SET status_id = ? WHERE contact_id_to = ? AND message_id = ?;', [ ( status_id, contact_id, message_id ) for ( contact_id, status_id ) in updates ] )
        
        self.pub_after_commit( 'message_statuses_data', message_key, status_updates )
        self.pub_after_commit( 'message_statuses_gui', message_key, status_updates )
        self.pub_after_commit( 'notify_check_messages' )
        
    
class RatingDB( object ):
    
    def _GetRatingsMediaResult( self, c, service_key, min, max ):
        
        service_id = self._GetServiceId( c, service_key )
        
        half_point = ( min + max ) / 2
        
        tighter_min = ( min + half_point ) / 2
        tighter_max = ( max + half_point ) / 2
        
        # I know this is horrible, ordering by random, but I can't think of a better way to do it right now
        result = c.execute( 'SELECT hash_id FROM local_ratings, files_info USING ( hash_id ) WHERE local_ratings.service_id = ? AND files_info.service_id = ? AND rating BETWEEN ? AND ? ORDER BY RANDOM() LIMIT 1;', ( service_id, self._local_file_service_id, tighter_min, tighter_max ) ).fetchone()
        
        if result is None: result = c.execute( 'SELECT hash_id FROM local_ratings, files_info USING ( hash_id ) WHERE local_ratings.service_id = ? AND files_info.service_id = ? AND rating BETWEEN ? AND ? ORDER BY RANDOM() LIMIT 1;', ( service_id, self._local_file_service_id, min, max ) ).fetchone()
        
        if result is None: return None
        else:
            
            ( hash_id, ) = result
            
            ( media_result, ) = self._GetMediaResults( c, HC.COMBINED_FILE_SERVICE_KEY, { hash_id } )
            
            return media_result
            
        
    
    def _GetRatingsFilter( self, c, service_key, hashes ):
        
        service_id = self._GetServiceId( c, service_key )
        
        hash_ids = self._GetHashIds( c, hashes )
        
        empty_rating = lambda: ( 0.0, 1.0 )
        
        ratings_filter = collections.defaultdict( empty_rating )
        
        ratings_filter.update( ( ( hash, ( min, max ) ) for ( hash, min, max ) in c.execute( 'SELECT hash, min, max FROM ratings_filter, hashes USING ( hash_id ) WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ) )
        
        return ratings_filter
        
    
    # leave this until I am more sure of how it'll work remotely
    # pending is involved here too
    def _UpdateRemoteRatings( self, c, service_key, ratings ):
        
        service_id = self._GetServiceId( c, service_key )
        
        hashes = [ hash for ( hash, count, rating ) in ratings ]
        
        hash_ids = self._GetHashIds( c, hashes )
        
        c.execute( 'DELETE FROM ratings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
        
        c.executemany( 'INSERT INTO ratings ( service_id, hash_id, count, rating, score ) VALUES ( ?, ?, ?, ?, ? );', [ ( service_id, self._GetHashId( c, hash ), count, rating, HC.CalculateScoreFromRating( count, rating ) ) for ( hash, count, rating ) in ratings if count > 0 ] )
        
        # these need count and score in
        #self.pub_after_commit( 'content_updates_data', [ HC.ContentUpdate( HC.CONTENT_UPDATE_RATING_REMOTE, service_key, ( hash, ), rating ) for ( hash, rating ) in ratings ] )
        #self.pub_after_commit( 'content_updates_gui', [ HC.ContentUpdate( HC.CONTENT_UPDATE_RATING_REMOTE, service_key, ( hash, ), rating ) for ( hash, rating ) in ratings ] )
        
    
class TagDB( object ):
    
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
            
        
        if len( tags_not_in_db ) > 0:
            
            inserts = [ ( tag, ) for tag in tags_not_in_db ]
            
            c.executemany( 'INSERT INTO tags ( tag ) VALUES ( ? );', inserts )
            
            c.executemany( 'INSERT INTO tags_fts4 ( docid, tag ) SELECT tag_id, tag FROM tags WHERE tag = ?;', inserts )
            
        
    
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
            
        
    
    def _GetNamespaceId( self, c, namespace ):
        
        result = c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO namespaces ( namespace ) VALUES ( ? );', ( namespace, ) )
            
            namespace_id = c.lastrowid
            
        else: ( namespace_id, ) = result
        
        return namespace_id
        
    
    def _GetNamespaceIdTagId( self, c, tag ):
        
        tag = HC.CleanTag( tag )
        
        if ':' in tag:
            
            ( namespace, tag ) = tag.split( ':', 1 )
            
            namespace_id = self._GetNamespaceId( c, namespace )
            
        else: namespace_id = 1
        
        result = c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO tags ( tag ) VALUES ( ? );', ( tag, ) )
            
            tag_id = c.lastrowid
            
            c.execute( 'INSERT INTO tags_fts4 ( docid, tag ) VALUES ( ?, ? );', ( tag_id, tag ) )
            
        else: ( tag_id, ) = result
        
        result = c.execute( 'SELECT 1 FROM existing_tags WHERE namespace_id = ? AND tag_id = ?;', ( namespace_id, tag_id ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO existing_tags ( namespace_id, tag_id ) VALUES ( ?, ? );', ( namespace_id, tag_id ) )
            
            tag_service_ids = self._GetServiceIds( c, ( HC.TAG_REPOSITORY, HC.LOCAL_TAG, HC.COMBINED_TAG ) )
            file_service_ids = self._GetServiceIds( c, ( HC.FILE_REPOSITORY, HC.LOCAL_FILE, HC.COMBINED_FILE ) )
            
            c.executemany( 'INSERT OR IGNORE INTO autocomplete_tags_cache ( file_service_id, tag_service_id, namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ?, ?, ? );', [ ( file_service_id, tag_service_id, namespace_id, tag_id, 0, 0 ) for ( tag_service_id, file_service_id ) in itertools.product( tag_service_ids, file_service_ids ) ] )
            
        
        return ( namespace_id, tag_id )
        
    
class ServiceDB( FileDB, MessageDB, TagDB, RatingDB ):
    
    def _AddFile( self, c, service_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ):
        
        result = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT OR IGNORE INTO files_info VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ? );', ( service_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) )
            
            service_info_updates = []
            
            result = c.execute( 'SELECT 1 FROM deleted_files WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
            
            if result is not None:
                
                c.execute( 'DELETE FROM deleted_files WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) )
                
                service_info_updates.append( ( -1, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
            
            if service_id != self._local_file_service_id:
                
                result = c.execute( 'SELECT 1 FROM file_inbox WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                
                if result is not None: service_info_updates.append( ( 1, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
                
            
            service_info_updates.append( ( size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( 1, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            if mime in HC.MIMES_WITH_THUMBNAILS: service_info_updates.append( ( 1, service_id, HC.SERVICE_INFO_NUM_THUMBNAILS ) )
            
            c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
            c.execute( 'DELETE FROM file_transfers WHERE service_id = ? AND hash_id = ? ;', ( service_id, hash_id ) )
            
            if mime in HC.MIMES_WITH_THUMBNAILS: c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL ) )
            
            self._UpdateAutocompleteTagCacheFromFiles( c, service_id, ( hash_id, ), 1 )
            
        
    
    def _AddHydrusSession( self, c, service_key, session_key, expires ):
        
        service_id = self._GetServiceId( c, service_key )
        
        c.execute( 'REPLACE INTO hydrus_sessions ( service_id, session_key, expiry ) VALUES ( ?, ?, ? );', ( service_id, sqlite3.Binary( session_key ), expires ) )
        
    
    def _AddService( self, c, service_key, service_type, name, info ):
        
        if service_type in HC.LOCAL_SERVICES:
            
            if service_type == HC.LOCAL_BOORU:
                
                current_time_struct = time.gmtime()
                
                ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
                
                if 'used_monthly_data' not in info: info[ 'used_monthly_data' ] = 0
                if 'max_monthly_data' not in info: info[ 'max_monthly_data' ] = None
                if 'used_monthly_requests' not in info: info[ 'used_monthly_requests' ] = 0
                if 'current_data_month' not in info: info[ 'current_data_month' ] = ( current_year, current_month )
                if 'port' not in info: info[ 'port' ] = HC.DEFAULT_LOCAL_BOORU_PORT
                if 'upnp' not in info: info[ 'upnp' ] = None
                
            
        
        if service_type in HC.REMOTE_SERVICES:
            
            if 'last_error' not in info: info[ 'last_error' ] = 0
            
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            if 'account' not in info:
                
                account = HC.GetUnknownAccount()
                
                account.MakeStale()
                
                info[ 'account' ] = account
                
                self.pub_after_commit( 'permissions_are_stale' )
                
            
        
        if service_type in HC.TAG_SERVICES:
            
            if 'tag_archive_sync' not in info: info[ 'tag_archive_sync' ] = {}
            
        
        if service_type in HC.REPOSITORIES:
            
            if 'first_timestamp' not in info: info[ 'first_timestamp' ] = None
            if 'next_download_timestamp' not in info: info[ 'next_download_timestamp' ] = 0
            if 'next_processing_timestamp' not in info: info[ 'next_processing_timestamp' ] = 0
            
            info[ 'paused' ] = False
            
        
        c.execute( 'INSERT INTO services ( service_key, service_type, name, info ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, name, info ) )
        
        service_id = c.lastrowid
        
        if service_type in ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ):
            
            file_service_ids = self._GetServiceIds( c, ( HC.FILE_REPOSITORY, HC.LOCAL_FILE, HC.COMBINED_FILE ) )
            
            existing_tag_ids = c.execute( 'SELECT namespace_id, tag_id FROM existing_tags;' ).fetchall()
            
            inserts = ( ( file_service_id, service_id, namespace_id, tag_id, 0, 0 ) for ( file_service_id, ( namespace_id, tag_id ) ) in itertools.product( file_service_ids, existing_tag_ids ) )
            
            c.executemany( 'INSERT OR IGNORE INTO autocomplete_tags_cache ( file_service_id, tag_service_id, namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ?, ?, ? );', inserts )
            
        elif service_type == HC.FILE_REPOSITORY:
            
            tag_service_ids = self._GetServiceIds( c, ( HC.TAG_REPOSITORY, HC.LOCAL_TAG, HC.COMBINED_TAG ) )
            
            existing_tag_ids = c.execute( 'SELECT namespace_id, tag_id FROM existing_tags;' ).fetchall()
            
            inserts = ( ( service_id, tag_service_id, namespace_id, tag_id, 0, 0 ) for ( tag_service_id, ( namespace_id, tag_id ) ) in itertools.product( tag_service_ids, existing_tag_ids ) )
            
            c.executemany( 'INSERT OR IGNORE INTO autocomplete_tags_cache ( file_service_id, tag_service_id, namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ?, ?, ? );', inserts )
            
        
    
    def _AddWebSession( self, c, name, cookies, expires ):
        
        c.execute( 'REPLACE INTO web_sessions ( name, cookies, expiry ) VALUES ( ?, ?, ? );', ( name, cookies, expires ) )
        
    
    def _ArchiveFiles( self, c, hash_ids ):
        
        valid_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_inbox WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ) ]
        
        if len( valid_hash_ids ) > 0:
            
            splayed_hash_ids = HC.SplayListForDB( valid_hash_ids )
            
            c.execute( 'DELETE FROM file_inbox WHERE hash_id IN ' + splayed_hash_ids + ';' )
            
            updates = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id;' ).fetchall()
            
            c.executemany( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in updates ] )
            
        
    
    def _Backup( self, c, path ):
        
        deletee_filenames = dircache.listdir( path )
        
        for deletee_filename in deletee_filenames:

            def make_files_deletable( function_called, path, traceback_gumpf ):
                
                os.chmod( path, stat.S_IWRITE )
                
                function_called( path ) # try again
                
            
            deletee_path = path + os.path.sep + deletee_filename
            
            if os.path.isdir( deletee_path ): shutil.rmtree( deletee_path, onerror = make_files_deletable )
            else: os.remove( deletee_path )
            
        
        shutil.copy( self._db_path, path + os.path.sep + 'client.db' )
        if os.path.exists( self._db_path + '-wal' ): shutil.copy( self._db_path + '-wal', path + os.path.sep + 'client.db-wal' )
        
        shutil.copytree( HC.CLIENT_ARCHIVES_DIR, path + os.path.sep + 'client_archives'  )
        shutil.copytree( HC.CLIENT_FILES_DIR, path + os.path.sep + 'client_files' )
        shutil.copytree( HC.CLIENT_THUMBNAILS_DIR, path + os.path.sep + 'client_thumbnails'  )
        shutil.copytree( HC.CLIENT_UPDATES_DIR, path + os.path.sep + 'client_updates'  )
        
        HC.ShowText( 'Database backup done!' )
        
    
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
        
        self.pub_after_commit( 'notify_new_pending' )
        
    
    def _DeleteHydrusSessionKey( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        c.execute( 'DELETE FROM hydrus_sessions WHERE service_id = ?;', ( service_id, ) )
        
    
    def _DeleteOrphans( self, c ):
        
        HC.pubsub.pub( 'set_splash_text', 'deleting orphan files' )
        
        # careful of the .encode( 'hex' ) business here!
        
        # files
        
        deleted_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_files WHERE service_id = ?;', ( self._local_file_service_id, ) ) }
        
        pending_upload_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_transfers;', ) }
        
        message_attachment_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM message_attachments;' ) }
        
        deletee_hash_ids = ( deleted_hash_ids - pending_upload_hash_ids ) - message_attachment_hash_ids
        
        deletee_hashes = set( self._GetHashes( c, deletee_hash_ids ) )
        
        local_files_hashes = CC.GetAllFileHashes()
        
        for hash in local_files_hashes & deletee_hashes:
            
            try:
                
                path = CC.GetFilePath( hash )
                
                os.chmod( path, stat.S_IWRITE )
                
                os.remove( path )
                
            except: continue
            
        
        # perceptual_hashes and thumbs
        
        perceptual_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM perceptual_hashes;' ) }
        
        hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info;' ) }
        
        perceptual_deletees = perceptual_hash_ids - hash_ids
        
        c.execute( 'DELETE FROM perceptual_hashes WHERE hash_id IN ' + HC.SplayListForDB( perceptual_deletees ) + ';' )
        
        local_thumbnail_hashes = CC.GetAllThumbnailHashes()
        
        hashes = set( self._GetHashes( c, hash_ids ) )
        
        thumbnail_deletees = local_thumbnail_hashes - hashes
        
        for hash in thumbnail_deletees:
            
            path = CC.GetExpectedThumbnailPath( hash, True )
            resized_path = CC.GetExpectedThumbnailPath( hash, False )
            
            if os.path.exists( path ): os.remove( path )
            if os.path.exists( resized_path ): os.remove( resized_path )
            
        
        c.execute( 'REPLACE INTO shutdown_timestamps ( shutdown_type, timestamp ) VALUES ( ?, ? );', ( CC.SHUTDOWN_TIMESTAMP_DELETE_ORPHANS, HC.GetNow() ) )
        
        HC.ShowText( 'Database maintenance: orphaned files successfully deleted.' )
        
    
    def _DeletePending( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service = self._GetService( c, service_id )
        
        if service.GetServiceType() == HC.TAG_REPOSITORY:
            
            pending_rescinded_mappings_ids = HC.BuildKeyToListDict( [ ( ( namespace_id, tag_id ), hash_id ) for ( namespace_id, tag_id, hash_id ) in c.execute( 'SELECT namespace_id, tag_id, hash_id FROM mappings WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ) ] )
            
            pending_rescinded_mappings_ids = [ ( namespace_id, tag_id, hash_ids ) for ( ( namespace_id, tag_id ), hash_ids ) in pending_rescinded_mappings_ids.items() ]
            
            petitioned_rescinded_mappings_ids = HC.BuildKeyToListDict( [ ( ( namespace_id, tag_id ), hash_id ) for ( namespace_id, tag_id, hash_id ) in c.execute( 'SELECT namespace_id, tag_id, hash_id FROM mapping_petitions WHERE service_id = ?;', ( service_id, ) ) ] )
            
            petitioned_rescinded_mappings_ids = [ ( namespace_id, tag_id, hash_ids ) for ( ( namespace_id, tag_id ), hash_ids ) in petitioned_rescinded_mappings_ids.items() ]
            
            self._UpdateMappings( c, service_id, pending_rescinded_mappings_ids = pending_rescinded_mappings_ids, petitioned_rescinded_mappings_ids = petitioned_rescinded_mappings_ids )
            
            c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ?;', ( service_id, ) )
            c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ?;', ( service_id, ) )
            
        elif service.GetServiceType() == HC.FILE_REPOSITORY:
            
            c.execute( 'DELETE FROM file_transfers WHERE service_id = ?;', ( service_id, ) )
            c.execute( 'DELETE FROM file_petitions WHERE service_id = ?;', ( service_id, ) )
            
        
        self.pub_after_commit( 'notify_new_pending' )
        self.pub_after_commit( 'notify_new_siblings' )
        self.pub_after_commit( 'notify_new_parents' )
        
        self.pub_service_updates_after_commit( { service_key : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_DELETE_PENDING ) ] } )
        
    
    def _DeleteYAMLDump( self, c, dump_type, dump_name = None ):
        
        if dump_name is None: c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) )
        else:
            
            if dump_type == YAML_DUMP_ID_SUBSCRIPTION and dump_name in self._subscriptions_cache: del self._subscriptions_cache[ dump_name ]
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.encode( 'hex' )
            
            c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
            
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            service_id = self._GetServiceId( c, HC.LOCAL_BOORU_SERVICE_KEY )
            
            c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_SHARES ) )
            
            HC.pubsub.pub( 'refresh_local_booru_shares' )
            
        
    
    def _FattenAutocompleteCache( self, c ):
        
        tag_services = self._GetServices( c, ( HC.TAG_REPOSITORY, HC.LOCAL_TAG, HC.COMBINED_TAG ) )
        file_services = self._GetServices( c, ( HC.FILE_REPOSITORY, HC.LOCAL_FILE, HC.COMBINED_FILE ) )
        
        for ( tag_service, file_service ) in itertools.product( tag_services, file_services ): self._GetAutocompleteTags( c, tag_service_key = tag_service.GetServiceKey(), file_service_key = file_service.GetServiceKey(), collapse = False )
        
        c.execute( 'REPLACE INTO shutdown_timestamps ( shutdown_type, timestamp ) VALUES ( ?, ? );', ( CC.SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE, HC.GetNow() ) )
        
    
    def _GetAutocompleteTags( self, c, tag_service_key = HC.COMBINED_TAG_SERVICE_KEY, file_service_key = HC.COMBINED_FILE_SERVICE_KEY, tag = '', half_complete_tag = '', include_current = True, include_pending = True, collapse = True ):
        
        tag_service_id = self._GetServiceId( c, tag_service_key )
        file_service_id = self._GetServiceId( c, file_service_key )
        
        if file_service_key == HC.COMBINED_FILE_SERVICE_KEY:
            
            current_tables_phrase = 'mappings WHERE service_id = ' + HC.u( tag_service_id ) + ' AND status = ' + HC.u( HC.CURRENT ) + ' AND '
            pending_tables_phrase = 'mappings WHERE service_id = ' + HC.u( tag_service_id ) + ' AND status = ' + HC.u( HC.PENDING ) + ' AND '
            
        else:
            
            current_tables_phrase = 'mappings, files_info USING ( hash_id ) WHERE mappings.service_id = ' + HC.u( tag_service_id ) + ' AND mappings.status = ' + HC.u( HC.CURRENT ) + ' AND files_info.service_id = ' + HC.u( file_service_id ) + ' AND '
            pending_tables_phrase = 'mappings, files_info USING ( hash_id ) WHERE mappings.service_id = ' + HC.u( tag_service_id ) + ' AND mappings.status = ' + HC.u( HC.PENDING ) + ' AND files_info.service_id = ' + HC.u( file_service_id ) + ' AND '
            
        
        # precache search
        
        there_was_a_namespace = False
        
        if len( half_complete_tag ) > 0:
            
            normal_characters = 'abcdefghijklmnopqrstuvwxyz0123456789'
            
            half_complete_tag_can_be_matched = True
            
            for character in half_complete_tag:
                
                if character not in normal_characters:
                    
                    half_complete_tag_can_be_matched = False
                    
                    break
                    
                
            
            def GetPossibleTagIds():
                
                # the issue is that the tokenizer for fts4 doesn't like weird characters
                # a search for '[s' actually only does 's'
                # so, let's do the old and slower LIKE instead of MATCH in weird cases
                
                if half_complete_tag_can_be_matched: return [ tag_id for ( tag_id, ) in c.execute( 'SELECT docid FROM tags_fts4 WHERE tag MATCH ?;', ( '"' + half_complete_tag + '*"', ) ) ]
                else: return [ tag_id for ( tag_id, ) in c.execute( 'SELECT tag_id FROM tags WHERE tag LIKE ?;', ( '%' + half_complete_tag + '%', ) ) ]
                
            
            if ':' in half_complete_tag:
                
                there_was_a_namespace = True
                
                ( namespace, half_complete_tag ) = half_complete_tag.split( ':', 1 )
                
                if half_complete_tag == '': return CC.AutocompleteMatchesCounted( {} )
                else:
                    
                    result = c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
                    
                    if result is None: return CC.AutocompleteMatchesCounted( {} )
                    else:
                        
                        ( namespace_id, ) = result
                        
                        possible_tag_ids = GetPossibleTagIds()
                        
                        predicates_phrase = 'namespace_id = ' + HC.u( namespace_id ) + ' AND tag_id IN ' + HC.SplayListForDB( possible_tag_ids )
                        
                    
                
            else:
                
                possible_tag_ids = GetPossibleTagIds()
                
                predicates_phrase = 'tag_id IN ' + HC.SplayListForDB( possible_tag_ids )
                
            
        elif len( tag ) > 0:
            
            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
            
            predicates_phrase = 'namespace_id = ' + HC.u( namespace_id ) + ' AND tag_id = ' + HC.u( tag_id )
            
        else:
            
            predicates_phrase = '1 = 1'
            
        
        results = { result for result in c.execute( 'SELECT namespace_id, tag_id FROM existing_tags WHERE ' + predicates_phrase + ';' ) }
        
        if collapse:
            
            # now fetch siblings, add to results set
            
            siblings_manager = HC.app.GetManager( 'tag_siblings' )
            
            if len( half_complete_tag ) > 0: all_associated_sibling_tags = siblings_manager.GetAutocompleteSiblings( half_complete_tag )
            elif len( tag ) > 0: all_associated_sibling_tags = siblings_manager.GetAllSiblings( tag )
            else: all_associated_sibling_tags = siblings_manager.GetAutocompleteSiblings( '' )
            
            sibling_results = [ self._GetNamespaceIdTagId( c, sibling_tag ) for sibling_tag in all_associated_sibling_tags ]
            
            results.update( sibling_results )
            
        
        # fetch what we can from cache
        
        cache_results = []
        
        if len( half_complete_tag ) > 0 or len( tag ) > 0:
            
            for ( namespace_id, tag_ids ) in HC.BuildKeyToListDict( results ).items(): cache_results.extend( c.execute( 'SELECT namespace_id, tag_id, current_count, pending_count FROM autocomplete_tags_cache WHERE tag_service_id = ? AND file_service_id = ? AND namespace_id = ? AND tag_id IN ' + HC.SplayListForDB( tag_ids ) + ';', ( tag_service_id, file_service_id, namespace_id ) ).fetchall() )
            
        else: cache_results = c.execute( 'SELECT namespace_id, tag_id, current_count, pending_count FROM autocomplete_tags_cache WHERE tag_service_id = ? AND file_service_id = ?', ( tag_service_id, file_service_id ) ).fetchall()
        
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
            
        
        ids = set()
        
        current_ids_to_count = collections.Counter()
        pending_ids_to_count = collections.Counter()
        
        for ( namespace_id, tag_id, current_count, pending_count ) in cache_results:
            
            ids.add( ( namespace_id, tag_id ) )
            
            current_ids_to_count[ ( namespace_id, tag_id ) ] += current_count
            pending_ids_to_count[ ( namespace_id, tag_id ) ] += pending_count
            
            if namespace_id != 1 and collapse and not there_was_a_namespace:
                
                current_ids_to_count[ ( 1, tag_id ) ] += current_count
                pending_ids_to_count[ ( 1, tag_id ) ] += pending_count
                
            
        
        ids_to_do = set()
        
        if include_current: ids_to_do.update( ( id for ( id, count ) in current_ids_to_count.items() if count > 0 ) )
        if include_pending: ids_to_do.update( ( id for ( id, count ) in pending_ids_to_count.items() if count > 0 ) )
        
        ids_to_tags = { ( namespace_id, tag_id ) : self._GetNamespaceTag( c, namespace_id, tag_id ) for ( namespace_id, tag_id ) in ids_to_do }
        
        tag_info = [ ( ids_to_tags[ id ], current_ids_to_count[ id ], pending_ids_to_count[ id ] ) for id in ids_to_do ]
        
        tags_to_do = { tag for ( tag, current_count, pending_count ) in tag_info }
        
        tag_censorship_manager = HC.app.GetManager( 'tag_censorship' )
        
        filtered_tags = tag_censorship_manager.FilterTags( tag_service_key, tags_to_do )
        
        predicates = [ HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', tag ), { HC.CURRENT : current_count, HC.PENDING : pending_count } ) for ( tag, current_count, pending_count ) in tag_info if tag in filtered_tags ]
        
        matches = CC.AutocompleteMatchesPredicates( tag_service_key, predicates, collapse = collapse )
        
        return matches
        
    
    def _GetDownloads( self, c ): return { hash for ( hash, ) in c.execute( 'SELECT hash FROM file_transfers, hashes USING ( hash_id ) WHERE service_id = ?;', ( self._local_file_service_id, ) ) }
    
    def _GetFileQueryIds( self, c, search_context ):
        
        system_predicates = search_context.GetSystemPredicates()
        
        file_service_key = search_context.GetFileServiceKey()
        tag_service_key = search_context.GetTagServiceKey()
        
        file_service_id = self._GetServiceId( c, file_service_key )
        tag_service_id = self._GetServiceId( c, tag_service_key )
        
        file_service = self._GetService( c, file_service_id )
        tag_service = self._GetService( c, tag_service_id )
        
        file_service_type = file_service.GetServiceType()
        tag_service_type = tag_service.GetServiceType()
        
        tags_to_include = search_context.GetTagsToInclude()
        tags_to_exclude = search_context.GetTagsToExclude()
        
        namespaces_to_include = search_context.GetNamespacesToInclude()
        namespaces_to_exclude = search_context.GetNamespacesToExclude()
        
        include_current_tags = search_context.IncludeCurrentTags()
        include_pending_tags = search_context.IncludePendingTags()
        
        #
        
        sql_predicates = [ 'service_id = ' + HC.u( file_service_id ) ]
        
        ( hash, min_size, size, max_size, mimes, min_timestamp, max_timestamp, min_width, width, max_width, min_height, height, max_height, min_ratio, ratio, max_ratio, min_num_words, num_words, max_num_words, min_duration, duration, max_duration ) = system_predicates.GetInfo()
        
        if min_size is not None: sql_predicates.append( 'size > ' + HC.u( min_size ) )
        if size is not None: sql_predicates.append( 'size = ' + HC.u( size ) )
        if max_size is not None: sql_predicates.append( 'size < ' + HC.u( max_size ) )
        
        if mimes is not None:
            
            if len( mimes ) == 1:
                
                ( mime, ) = mimes
                
                sql_predicates.append( 'mime = ' + HC.u( mime ) )
                
            else: sql_predicates.append( 'mime IN ' + HC.SplayListForDB( mimes ) )
            
        
        if min_timestamp is not None: sql_predicates.append( 'timestamp >= ' + HC.u( min_timestamp ) )
        if max_timestamp is not None: sql_predicates.append( 'timestamp <= ' + HC.u( max_timestamp ) )
        
        if min_width is not None: sql_predicates.append( 'width > ' + HC.u( min_width ) )
        if width is not None: sql_predicates.append( 'width = ' + HC.u( width ) )
        if max_width is not None: sql_predicates.append( 'width < ' + HC.u( max_width ) )
        
        if min_height is not None: sql_predicates.append( 'height > ' + HC.u( min_height ) )
        if height is not None: sql_predicates.append( 'height = ' + HC.u( height ) )
        if max_height is not None: sql_predicates.append( 'height < ' + HC.u( max_height ) )
        
        if min_ratio is not None:
            
            ( ratio_width, ratio_height ) = min_ratio
            
            sql_predicates.append( '( width * 1.0 ) / height > ' + HC.u( float( ratio_width ) ) + ' / ' + HC.u( ratio_height ) )
            
        if ratio is not None:
            
            ( ratio_width, ratio_height ) = ratio
            
            sql_predicates.append( '( width * 1.0 ) / height = ' + HC.u( float( ratio_width ) ) + ' / ' + HC.u( ratio_height ) )
            
        if max_ratio is not None:
            
            ( ratio_width, ratio_height ) = max_ratio
            
            sql_predicates.append( '( width * 1.0 ) / height < ' + HC.u( float( ratio_width ) ) + ' / ' + HC.u( ratio_height ) )
            
        
        if min_num_words is not None: sql_predicates.append( 'num_words > ' + HC.u( min_num_words ) )
        if num_words is not None:
            
            if num_words == 0: sql_predicates.append( '( num_words IS NULL OR num_words = 0 )' )
            else: sql_predicates.append( 'num_words = ' + HC.u( num_words ) )
            
        if max_num_words is not None:
            if max_num_words == 0: sql_predicates.append( 'num_words < ' + HC.u( max_num_words ) )
            else: sql_predicates.append( '( num_words < ' + HC.u( max_num_words ) + ' OR num_words IS NULL )' )
        
        if min_duration is not None: sql_predicates.append( 'duration > ' + HC.u( min_duration ) )
        if duration is not None:
            
            if duration == 0: sql_predicates.append( '( duration IS NULL OR duration = 0 )' )
            else: sql_predicates.append( 'duration = ' + HC.u( duration ) )
            
        if max_duration is not None:
            
            if max_duration == 0: sql_predicates.append( 'duration < ' + HC.u( max_duration ) )
            else: sql_predicates.append( '( duration < ' + HC.u( max_duration ) + ' OR duration IS NULL )' )
            
        
        if len( tags_to_include ) > 0 or len( namespaces_to_include ) > 0:
            
            query_hash_ids = None
            
            if len( tags_to_include ) > 0: query_hash_ids = HC.IntelligentMassIntersect( ( self._GetHashIdsFromTag( c, file_service_key, tag_service_key, tag, include_current_tags, include_pending_tags ) for tag in tags_to_include ) )
            
            if len( namespaces_to_include ) > 0:
                
                namespace_query_hash_ids = HC.IntelligentMassIntersect( ( self._GetHashIdsFromNamespace( c, file_service_key, tag_service_key, namespace, include_current_tags, include_pending_tags ) for namespace in namespaces_to_include ) )
                
                if query_hash_ids is None: query_hash_ids = namespace_query_hash_ids
                else: query_hash_ids.intersection_update( namespace_query_hash_ids )
                
            
            if len( sql_predicates ) > 1: query_hash_ids.intersection_update( [ id for ( id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE ' + ' AND '.join( sql_predicates ) + ';' ) ] )
            
        else:
            
            if file_service_key != HC.COMBINED_FILE_SERVICE_KEY: query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE ' + ' AND '.join( sql_predicates ) + ';' ) }
            elif tag_service_key != HC.COMBINED_TAG_SERVICE_KEY: query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( tag_service_id, HC.CURRENT, HC.PENDING ) ) }
            else: query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings UNION SELECT hash_id FROM files_info;' ) }
            
        
        #
        
        ( min_num_tags, num_tags, max_num_tags ) = system_predicates.GetNumTagsInfo()
        
        num_tags_zero = False
        num_tags_nonzero = False
        
        tag_predicates = []
        
        if min_num_tags is not None:
            
            if min_num_tags == 0: num_tags_nonzero = True
            else: tag_predicates.append( lambda x: x > min_num_tags )
            
        
        if num_tags is not None:
            
            if num_tags == 0: num_tags_zero = True
            else: tag_predicates.append( lambda x: x == num_tags )
            
        
        if max_num_tags is not None:
            
            if max_num_tags == 1: num_tags_zero = True
            else: tag_predicates.append( lambda x: x < max_num_tags )
            
        
        statuses = []
        
        if include_current_tags: statuses.append( HC.CURRENT )
        if include_pending_tags: statuses.append( HC.PENDING )
        
        if num_tags_zero or num_tags_nonzero or len( tag_predicates ) > 0:
            
            tag_censorship_manager = HC.app.GetManager( 'tag_censorship' )
            
            ( blacklist, tags ) = tag_censorship_manager.GetInfo( tag_service_key )
            
            namespaces = [ tag for tag in tags if ':' in tag ]
            
            if len( namespaces ) == 0: namespace_predicate = ''
            else:
                
                namespace_ids = [ self._GetNamespaceId( c, namespace ) for namespace in namespaces ]
                
                if blacklist: namespace_predicate = ' AND namespace_id NOT IN ' + HC.SplayListForDB( namespace_ids )
                else: namespace_predicate = ' AND namespace_id IN ' + HC.SplayListForDB( namespace_ids )
                
            
        
        if num_tags_zero or num_tags_nonzero:
            
            nonzero_tag_query_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( query_hash_ids ) + ' AND status IN ' + HC.SplayListForDB( statuses ) + namespace_predicate + ';', ( tag_service_id, ) ) }
            
            if num_tags_zero: query_hash_ids.difference_update( nonzero_tag_query_hash_ids )
            elif num_tags_nonzero: query_hash_ids = nonzero_tag_query_hash_ids
            
        
        if len( tag_predicates ) > 0:
            
            query_hash_ids = { id for ( id, count ) in c.execute( 'SELECT hash_id, COUNT( * ) as num_tags FROM mappings WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( query_hash_ids ) + ' AND status IN ' + HC.SplayListForDB( statuses ) + namespace_predicate + ' GROUP BY hash_id;', ( tag_service_id, ) ) if False not in ( pred( count ) for pred in tag_predicates ) }
            
        
        #
        
        if hash is not None:
            
            hash_id = self._GetHashId( c, hash )
            
            query_hash_ids.intersection_update( { hash_id } )
            
        
        #
        
        exclude_query_hash_ids = set()
        
        for tag in tags_to_exclude: exclude_query_hash_ids.update( self._GetHashIdsFromTag( c, file_service_key, tag_service_key, tag, include_current_tags, include_pending_tags ) )
        
        for namespace in namespaces_to_exclude: exclude_query_hash_ids.update( self._GetHashIdsFromNamespace( c, file_service_key, tag_service_key, namespace, include_current_tags, include_pending_tags ) )
        
        if file_service_type == HC.FILE_REPOSITORY and HC.options[ 'exclude_deleted_files' ]: exclude_query_hash_ids.update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM deleted_files WHERE service_id = ?;', ( self._local_file_service_id, ) ) ] )
        
        query_hash_ids.difference_update( exclude_query_hash_ids )
        
        #
        
        ( file_services_to_include_current, file_services_to_include_pending, file_services_to_exclude_current, file_services_to_exclude_pending ) = system_predicates.GetFileServiceInfo()
        
        for service_key in file_services_to_include_current:
            
            service_id = self._GetServiceId( c, service_key )
            
            query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for service_key in file_services_to_include_pending:
            
            service_id = self._GetServiceId( c, service_key )
            
            query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for service_key in file_services_to_exclude_current:
            
            service_id = self._GetServiceId( c, service_key )
            
            query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for service_key in file_services_to_exclude_pending:
            
            service_id = self._GetServiceId( c, service_key )
            
            query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for ( service_key, operator, value ) in system_predicates.GetRatingsPredicates():
            
            service_id = self._GetServiceId( c, service_key )
            
            if value == 'rated': query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ] )
            elif value == 'not rated': query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ] )
            elif value == 'uncertain': query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM ratings_filter WHERE service_id = ?;', ( service_id, ) ) ] )
            else:
                
                if operator == u'\u2248': predicate = HC.u( value * 0.95 ) + ' < rating AND rating < ' + HC.u( value * 1.05 )
                else: predicate = 'rating ' + operator + ' ' + HC.u( value )
                
                query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ? AND ' + predicate + ';', ( service_id, ) ) ] )
                
            
        
        #
        
        must_be_local = system_predicates.MustBeLocal() or system_predicates.MustBeArchive()
        must_not_be_local = system_predicates.MustNotBeLocal()
        must_be_inbox = system_predicates.MustBeInbox()
        must_be_archive = system_predicates.MustBeArchive()
        
        if must_be_local or must_not_be_local:
            
            if file_service_id == self._local_file_service_id:
                
                if must_not_be_local: query_hash_ids = set()
                
            else:
                
                local_hash_ids = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( self._local_file_service_id, ) ) ]
                
                if must_be_local: query_hash_ids.intersection_update( local_hash_ids )
                else: query_hash_ids.difference_update( local_hash_ids )
                
            
        
        if must_be_inbox or must_be_archive:
            
            inbox_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM file_inbox;' ) }
            
            if must_be_inbox: query_hash_ids.intersection_update( inbox_hash_ids )
            elif must_be_archive: query_hash_ids.difference_update( inbox_hash_ids )
            
        
        #
        
        if system_predicates.HasSimilarTo():
            
            ( similar_to_hash, max_hamming ) = system_predicates.GetSimilarTo()
            
            hash_id = self._GetHashId( c, similar_to_hash )
            
            result = c.execute( 'SELECT phash FROM perceptual_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
            if result is None: query_hash_ids = set()
            else:
                
                ( phash, ) = result
                
                similar_hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM perceptual_hashes WHERE hydrus_hamming( phash, ? ) <= ?;', ( sqlite3.Binary( phash ), max_hamming ) ) ]
                
                query_hash_ids.intersection_update( similar_hash_ids )
                
            
        
        return query_hash_ids
        
    
    def _GetFileSystemPredicates( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service = self._GetService( c, service_id )
        
        service_type = service.GetServiceType()
        
        predicates = []
        
        if service_type in ( HC.COMBINED_FILE, HC.COMBINED_TAG ): predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ) ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_HASH ] ] )
        elif service_type in ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ):
            
            service_info = self._GetServiceInfoSpecific( c, service_id, service_type, { HC.SERVICE_INFO_NUM_FILES } )
            
            num_everything = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None ), { HC.CURRENT : num_everything } ) )
            
            predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ) ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_HASH ] ] )
            
        elif service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ):
            
            service_info = self._GetServiceInfoSpecific( c, service_id, service_type, { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_INBOX } )
            
            num_everything = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            if service_type == HC.FILE_REPOSITORY:
                
                if HC.options[ 'exclude_deleted_files' ]:
                    
                    ( num_everything_deleted, ) = c.execute( 'SELECT COUNT( * ) FROM files_info, deleted_files USING ( hash_id ) WHERE files_info.service_id = ? AND deleted_files.service_id = ?;', ( service_id, self._local_file_service_id ) ).fetchone()
                    
                    num_everything -= num_everything_deleted
                    
                
            
            num_inbox = service_info[ HC.SERVICE_INFO_NUM_INBOX ]
            num_archive = num_everything - num_inbox
            
            if service_type == HC.FILE_REPOSITORY:
                
                ( num_local, ) = c.execute( 'SELECT COUNT( * ) FROM files_info AS remote_files_info, files_info USING ( hash_id ) WHERE remote_files_info.service_id = ? AND files_info.service_id = ?;', ( service_id, self._local_file_service_id ) ).fetchone()
                
                num_not_local = num_everything - num_local
                
                num_archive = num_local - num_inbox
                
            
            predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None ), { HC.CURRENT : num_everything } ) )
            
            if num_inbox > 0:
                
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None ), { HC.CURRENT : num_inbox } ) )
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None ), { HC.CURRENT : num_archive } ) )
                
            
            if service_type == HC.FILE_REPOSITORY:
                
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None ), { HC.CURRENT : num_local } ) )
                predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None ), { HC.CURRENT : num_not_local } ) )
                
            
            predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ) ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_SIZE, HC.SYSTEM_PREDICATE_TYPE_AGE, HC.SYSTEM_PREDICATE_TYPE_HASH, HC.SYSTEM_PREDICATE_TYPE_WIDTH, HC.SYSTEM_PREDICATE_TYPE_HEIGHT, HC.SYSTEM_PREDICATE_TYPE_RATIO, HC.SYSTEM_PREDICATE_TYPE_DURATION, HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, HC.SYSTEM_PREDICATE_TYPE_MIME, HC.SYSTEM_PREDICATE_TYPE_RATING, HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE ] ] )
            
        
        return predicates
        
    
    def _GetHashIdsFromNamespace( self, c, file_service_key, tag_service_key, namespace, include_current_tags, include_pending_tags ):
        
        statuses = []
        
        if include_current_tags: statuses.append( HC.CURRENT )
        if include_pending_tags: statuses.append( HC.PENDING )
        
        if len( statuses ) > 0: status_phrase = 'mappings.status IN ' + HC.SplayListForDB( statuses ) + ' AND '
        else: status_phrase = ''
        
        tag_service_id = self._GetServiceId( c, tag_service_key )
        
        file_service_id = self._GetServiceId( c, file_service_key )
        
        namespace_id = self._GetNamespaceId( c, namespace )
        
        if file_service_key == HC.COMBINED_FILE_SERVICE_KEY: hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND ' + status_phrase + 'namespace_id = ?;', ( tag_service_id, namespace_id ) ) }
        else: hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings, files_info USING ( hash_id ) WHERE mappings.service_id = ? AND files_info.service_id = ? AND ' + status_phrase + 'namespace_id = ?;', ( tag_service_id, file_service_id, namespace_id ) ) }
        
        return hash_ids
        
    
    def _GetHashIdsFromTag( self, c, file_service_key, tag_service_key, tag, include_current_tags, include_pending_tags ):
        
        # this does siblings and censorship too!
        
        statuses = []
        
        if include_current_tags: statuses.append( HC.CURRENT )
        if include_pending_tags: statuses.append( HC.PENDING )
        
        if len( statuses ) > 0: status_phrase = 'mappings.status IN ' + HC.SplayListForDB( statuses ) + ' AND '
        else: status_phrase = ''
        
        tag_service_id = self._GetServiceId( c, tag_service_key )
        
        file_service_id = self._GetServiceId( c, file_service_key )
        
        siblings_manager = HC.app.GetManager( 'tag_siblings' )
        
        tags = siblings_manager.GetAllSiblings( tag )
        
        tag_censorship_manager = HC.app.GetManager( 'tag_censorship' )
        
        tags = tag_censorship_manager.FilterTags( tag_service_key, tags )
        
        hash_ids = set()
        
        for tag in tags:
            
            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
            
            if ':' in tag:
                
                if file_service_key == HC.COMBINED_FILE_SERVICE_KEY: hash_ids.update( ( id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND ' + status_phrase + 'namespace_id = ? AND tag_id = ?;', ( tag_service_id, namespace_id, tag_id ) ) ) )
                else: hash_ids.update( ( id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings, files_info USING ( hash_id ) WHERE mappings.service_id = ? AND files_info.service_id = ? AND ' + status_phrase + 'namespace_id = ? AND tag_id = ?;', ( tag_service_id, file_service_id, namespace_id, tag_id ) ) ) )
                
            else:
                
                if file_service_key == HC.COMBINED_FILE_SERVICE_KEY: hash_ids.update( ( id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND ' + status_phrase + 'tag_id = ?;', ( tag_service_id, tag_id ) ) ) )
                else: hash_ids.update( ( id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings, files_info USING ( hash_id ) WHERE mappings.service_id = ? AND files_info.service_id = ? AND ' + status_phrase + 'tag_id = ?;', ( tag_service_id, file_service_id, tag_id ) ) ) )
                
            
        
        return hash_ids
        
    
    def _GetHydrusSessions( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM hydrus_sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        results = c.execute( 'SELECT service_id, session_key, expiry FROM hydrus_sessions;' ).fetchall()
        
        for ( service_id, session_key, expires ) in results:
            
            service = self._GetService( c, service_id )
            
            service_key = service.GetServiceKey()
            
            sessions.append( ( service_key, session_key, expires ) )
            
        
        return sessions
        
    
    def _GetMD5Status( self, c, md5 ):
        
        result = c.execute( 'SELECT hash_id FROM local_hashes WHERE md5 = ?;', ( sqlite3.Binary( md5 ), ) ).fetchone()
        
        if result is not None:
            
            ( hash_id, ) = result
            
            if HC.options[ 'exclude_deleted_files' ]:
                
                result = c.execute( 'SELECT 1 FROM deleted_files WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                
                if result is not None: return ( 'deleted', None )
                
            
            result = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone()
            
            if result is not None:
                
                hash = self._GetHash( c, hash_id )
                
                return ( 'redundant', hash )
                
            
        
        return ( 'new', None )
        
    
    def _GetMediaResults( self, c, service_key, hash_ids ):
        
        service_id = self._GetServiceId( c, service_key )
        
        inbox_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM file_inbox;' ) }
        
        # get first detailed results
        
        if service_key == HC.COMBINED_FILE_SERVICE_KEY:
            
            all_services_results = c.execute( 'SELECT hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';' ).fetchall()
            
            hash_ids_i_have_info_for = set()
            
            results = []
            
            for result in all_services_results:
                
                hash_id = result[0]
                
                if hash_id not in hash_ids_i_have_info_for:
                    
                    hash_ids_i_have_info_for.add( hash_id )
                    
                    results.append( result )
                    
                
            
            results.extend( [ ( hash_id, None, HC.APPLICATION_UNKNOWN, None, None, None, None, None, None ) for hash_id in hash_ids if hash_id not in hash_ids_i_have_info_for ] )
            
        else: results = c.execute( 'SELECT hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words FROM files_info WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) ).fetchall()
        
        # get tagged results
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        hash_ids_to_hashes = self._GetHashIdsToHashes( c, hash_ids )
        
        hash_ids_to_tags = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, ( status, namespace + ':' + tag ) ) ) if namespace != '' else ( hash_id, ( service_id, ( status, tag ) ) ) for ( hash_id, service_id, namespace, tag, status ) in c.execute( 'SELECT hash_id, service_id, namespace, tag, status FROM namespaces, ( tags, mappings USING ( tag_id ) ) USING ( namespace_id ) WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        hash_ids_to_petitioned_tags = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, ( HC.PETITIONED, namespace + ':' + tag ) ) ) if namespace != '' else ( hash_id, ( service_id, ( HC.PETITIONED, tag ) ) ) for ( hash_id, service_id, namespace, tag ) in c.execute( 'SELECT hash_id, service_id, namespace, tag FROM namespaces, ( tags, mapping_petitions USING ( tag_id ) ) USING ( namespace_id ) WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        for ( hash_id, tag_data ) in hash_ids_to_petitioned_tags.items(): hash_ids_to_tags[ hash_id ].extend( tag_data )
        
        hash_ids_to_current_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM files_info WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_deleted_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM deleted_files WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_pending_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM file_transfers WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_petitioned_file_service_ids = HC.BuildKeyToListDict( c.execute( 'SELECT hash_id, service_id FROM file_petitions WHERE hash_id IN ' + splayed_hash_ids + ';' ) )
        
        hash_ids_to_local_ratings = HC.BuildKeyToListDict( [ ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in c.execute( 'SELECT service_id, hash_id, rating FROM local_ratings WHERE hash_id IN ' + splayed_hash_ids + ';' ) ] )
        
        # do current and pending remote ratings here
        
        service_ids_to_service_keys = { service_id : service_key for ( service_id, service_key ) in c.execute( 'SELECT service_id, service_key FROM services;' ) }
        
        # build it
        
        media_results = []
        
        for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in results:
            
            hash = hash_ids_to_hashes[ hash_id ]
            
            #
            
            inbox = hash_id in inbox_hash_ids
            
            #
            
            tags_dict = HC.BuildKeyToListDict( hash_ids_to_tags[ hash_id ] )
            
            service_keys_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
            
            service_keys_to_statuses_to_tags.update( { service_ids_to_service_keys[ service_id ] : HC.BuildKeyToSetDict( tags_info ) for ( service_id, tags_info ) in tags_dict.items() } )
            
            tags_manager = HydrusTags.TagsManager( service_keys_to_statuses_to_tags )
            
            #
            
            current_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_current_file_service_ids[ hash_id ] }
            
            deleted_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_deleted_file_service_ids[ hash_id ] }
            
            pending_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_pending_file_service_ids[ hash_id ] }
            
            petitioned_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_petitioned_file_service_ids[ hash_id ] }
            
            file_service_keys_cdpp = CC.LocationsManager( current_file_service_keys, deleted_file_service_keys, pending_file_service_keys, petitioned_file_service_keys )
            
            #
            
            local_ratings = { service_ids_to_service_keys[ service_id ] : rating for ( service_id, rating ) in hash_ids_to_local_ratings[ hash_id ] }
            
            local_ratings = CC.LocalRatingsManager( local_ratings )
            remote_ratings = {}
            
            #
            
            media_results.append( CC.MediaResult( ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_keys_cdpp, local_ratings, remote_ratings ) ) )
            
        
        return media_results
        
    
    def _GetMediaResultsFromHashes( self, c, service_key, hashes ):
        
        query_hash_ids = set( self._GetHashIds( c, hashes ) )
        
        return self._GetMediaResults( c, service_key, query_hash_ids )
        
    
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
        
    
    def _GetMime( self, c, service_id, hash_id ):
        
        result = c.execute( 'SELECT mime FROM files_info WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None: raise HydrusExceptions.NotFoundException()
        
        ( mime, ) = result
        
        return mime
        
    
    def _GetNews( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        news = c.execute( 'SELECT post, timestamp FROM news WHERE service_id = ?;', ( service_id, ) ).fetchall()
        
        return news
        
    
    def _GetNumsPending( self, c ):
        
        services = self._GetServices( c, ( HC.TAG_REPOSITORY, HC.FILE_REPOSITORY ) )
        
        pendings = {}
        
        for service in services:
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            
            service_id = self._GetServiceId( c, service_key )
            
            if service_type == HC.FILE_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_PENDING_FILES, HC.SERVICE_INFO_NUM_PETITIONED_FILES }
            elif service_type == HC.TAG_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_PENDING_MAPPINGS, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS }
            
            pendings[ service_key ] = self._GetServiceInfoSpecific( c, service_id, service_type, info_types )
            
        
        return pendings
        
    
    def _GetPending( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service = self._GetService( c, service_id )
        
        service_type = service.GetServiceType()
        
        if service_type == HC.TAG_REPOSITORY:
            
            updates = []
            
            # mappings
            
            max_update_weight = 50
            
            content_data = HC.GetEmptyDataDict()
            
            all_hash_ids = set()
            
            current_update_weight = 0
            
            pending_dict = HC.BuildKeyToListDict( [ ( ( namespace_id, tag_id ), hash_id ) for ( namespace_id, tag_id, hash_id ) in c.execute( 'SELECT namespace_id, tag_id, hash_id FROM mappings INDEXED BY mappings_service_id_status_index WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ) ] )
            
            for ( ( namespace_id, tag_id ), hash_ids ) in pending_dict.items():
                
                pending = ( self._GetNamespaceTag( c, namespace_id, tag_id ), hash_ids )
                
                content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_PENDING ].append( pending )
                
                all_hash_ids.update( hash_ids )
                
                current_update_weight += len( hash_ids )
                
                if current_update_weight > max_update_weight:
                    
                    hash_ids_to_hashes = self._GetHashIdsToHashes( c, all_hash_ids )
                    
                    updates.append( HC.ClientToServerUpdate( content_data, hash_ids_to_hashes ) )
                    
                    content_data = HC.GetEmptyDataDict()
                    
                    all_hash_ids = set()
                    
                    current_update_weight = 0
                    
                
            
            petitioned_dict = HC.BuildKeyToListDict( [ ( ( namespace_id, tag_id, reason_id ), hash_id ) for ( namespace_id, tag_id, hash_id, reason_id ) in c.execute( 'SELECT namespace_id, tag_id, hash_id, reason_id FROM mapping_petitions WHERE service_id = ?;', ( service_id, ) ) ] )
            
            for ( ( namespace_id, tag_id, reason_id ), hash_ids ) in petitioned_dict.items():
                
                petitioned = ( self._GetNamespaceTag( c, namespace_id, tag_id ), hash_ids, self._GetReason( c, reason_id ) )
                
                content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_PETITION ].append( petitioned )
                
                all_hash_ids.update( hash_ids )
                
                current_update_weight += len( hash_ids )
                
                if current_update_weight > max_update_weight:
                    
                    hash_ids_to_hashes = self._GetHashIdsToHashes( c, all_hash_ids )
                    
                    updates.append( HC.ClientToServerUpdate( content_data, hash_ids_to_hashes ) )
                    
                    content_data = HC.GetEmptyDataDict()
                    
                    all_hash_ids = set()
                    
                    current_update_weight = 0
                    
                
            
            if len( content_data ) > 0:
                
                hash_ids_to_hashes = self._GetHashIdsToHashes( c, all_hash_ids )
                
                updates.append( HC.ClientToServerUpdate( content_data, hash_ids_to_hashes ) )
                
                content_data = HC.GetEmptyDataDict()
                
                all_hash_ids = set()
                
                current_update_weight = 0
                
            
            # tag siblings
            
            pending = [ ( ( self._GetNamespaceTag( c, old_namespace_id, old_tag_id ), self._GetNamespaceTag( c, new_namespace_id, new_tag_id ) ), self._GetReason( c, reason_id ) ) for ( old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, reason_id ) in c.execute( 'SELECT old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, reason_id FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ).fetchall() ]
            
            content_data[ HC.CONTENT_DATA_TYPE_TAG_SIBLINGS ][ HC.CONTENT_UPDATE_PENDING ] = pending
            
            petitioned = [ ( ( self._GetNamespaceTag( c, old_namespace_id, old_tag_id ), self._GetNamespaceTag( c, new_namespace_id, new_tag_id ) ), self._GetReason( c, reason_id ) ) for ( old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, reason_id ) in c.execute( 'SELECT old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, reason_id FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PETITIONED ) ).fetchall() ]
            
            content_data[ HC.CONTENT_DATA_TYPE_TAG_SIBLINGS ][ HC.CONTENT_UPDATE_PETITION ] = petitioned
            
            # tag parents
            
            pending = [ ( ( self._GetNamespaceTag( c, child_namespace_id, child_tag_id ), self._GetNamespaceTag( c, parent_namespace_id, parent_tag_id ) ), self._GetReason( c, reason_id ) ) for ( child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, reason_id ) in c.execute( 'SELECT child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, reason_id FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ).fetchall() ]
            
            content_data[ HC.CONTENT_DATA_TYPE_TAG_PARENTS ][ HC.CONTENT_UPDATE_PENDING ] = pending
            
            petitioned = [ ( ( self._GetNamespaceTag( c, child_namespace_id, child_tag_id ), self._GetNamespaceTag( c, parent_namespace_id, parent_tag_id ) ), self._GetReason( c, reason_id ) ) for ( child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, reason_id ) in c.execute( 'SELECT child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, reason_id FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PETITIONED ) ).fetchall() ]
            
            content_data[ HC.CONTENT_DATA_TYPE_TAG_PARENTS ][ HC.CONTENT_UPDATE_PETITION ] = petitioned
            
            if len( content_data ) > 0:
                
                hash_ids_to_hashes = self._GetHashIdsToHashes( c, all_hash_ids )
                
                updates.append( HC.ClientToServerUpdate( content_data, hash_ids_to_hashes ) )
                
            
            return updates
            
        elif service_type == HC.FILE_REPOSITORY:
            
            upload_hashes = [ hash for ( hash, ) in c.execute( 'SELECT hash FROM hashes, file_transfers USING ( hash_id ) WHERE service_id = ?;', ( service_id, ) ) ]
            
            content_data = HC.GetEmptyDataDict()
            
            content_data[ HC.CONTENT_DATA_TYPE_FILES ] = {}
            
            petitioned = [ ( hash_ids, reason ) for ( reason, hash_ids ) in HC.BuildKeyToListDict( c.execute( 'SELECT reason, hash_id FROM reasons, file_petitions USING ( reason_id ) WHERE service_id = ?;', ( service_id, ) ) ).items() ]
            
            all_hash_ids = { hash_id for hash_id in itertools.chain.from_iterable( ( hash_ids for ( hash_ids, reason ) in petitioned ) ) }
            
            hash_ids_to_hashes = self._GetHashIdsToHashes( c, all_hash_ids )
            
            content_data[ HC.CONTENT_DATA_TYPE_FILES ][ HC.CONTENT_UPDATE_PETITION ] = petitioned
            
            update = HC.ClientToServerUpdate( content_data, hash_ids_to_hashes )
            
            return ( upload_hashes, update )
            
        
    
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
        
    
    def _GetService( self, c, service_id ):
        
        ( service_key, service_type, name, info ) = c.execute( 'SELECT service_key, service_type, name, info FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return CC.Service( service_key, service_type, name, info )
        
    
    def _GetServices( self, c, limited_types = HC.ALL_SERVICES ):
        
        services = []
        
        for ( service_key, service_type, name, info ) in c.execute( 'SELECT service_key, service_type, name, info FROM services WHERE service_type IN ' + HC.SplayListForDB( limited_types ) + ';' ):
            
            services.append( CC.Service( service_key, service_type, name, info ) )
            
        
        return services
        
    
    def _GetServiceId( self, c, service_key ):
        
        result = c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
        
        if result is None: raise Exception( 'Service id error in database' )
        
        ( service_id, ) = result
        
        return service_id
        
    
    def _GetServiceIds( self, c, service_types ): return [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services WHERE service_type IN ' + HC.SplayListForDB( service_types ) + ';' ) ]
    
    def _GetServiceInfo( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service = self._GetService( c, service_id )
        
        service_type = service.GetServiceType()
        
        if service_type == HC.LOCAL_FILE: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES }
        elif service_type == HC.FILE_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES, HC.SERVICE_INFO_NUM_THUMBNAILS, HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL }
        elif service_type == HC.LOCAL_TAG: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS }
        elif service_type == HC.TAG_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS }
        elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): info_types = { HC.SERVICE_INFO_NUM_FILES }
        elif service_type == HC.LOCAL_BOORU: info_types = { HC.SERVICE_INFO_NUM_SHARES }
        else: info_types = set()
        
        service_info = self._GetServiceInfoSpecific( c, service_id, service_type, info_types )
        
        return service_info
        
    
    def _GetServiceInfoSpecific( self, c, service_id, service_type, info_types ):
        
        results = { info_type : info for ( info_type, info ) in c.execute( 'SELECT info_type, info FROM service_info WHERE service_id = ? AND info_type IN ' + HC.SplayListForDB( info_types ) + ';', ( service_id, ) ) }
        
        if len( results ) != len( info_types ):
            
            info_types_hit = results.keys()
            
            info_types_missed = info_types.difference( info_types_hit )
            
            if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                
                common_tag_info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_NAMESPACES, HC.SERVICE_INFO_NUM_TAGS }
                
                if common_tag_info_types <= info_types_missed:
                    
                    ( num_files, num_namespaces, num_tags ) = c.execute( 'SELECT COUNT( DISTINCT hash_id ), COUNT( DISTINCT namespace_id ), COUNT( DISTINCT tag_id ) FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.CURRENT, HC.PENDING ) ).fetchone()
                    
                    results[ HC.SERVICE_INFO_NUM_FILES ] = num_files
                    results[ HC.SERVICE_INFO_NUM_NAMESPACES ] = num_namespaces
                    results[ HC.SERVICE_INFO_NUM_TAGS ] = num_tags
                    
                    c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_FILES, num_files ) )
                    c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_NAMESPACES, num_namespaces ) )
                    c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_TAGS, num_tags ) )
                    
                    info_types_missed.difference_update( common_tag_info_types )
                    
                
            
            for info_type in info_types_missed:
                
                save_it = True
                
                if service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ):
                    
                    if info_type in ( HC.SERVICE_INFO_NUM_PENDING_FILES, HC.SERVICE_INFO_NUM_PETITIONED_FILES ): save_it = False
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = c.execute( 'SELECT COUNT( * ) FROM files_info WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_TOTAL_SIZE: result = c.execute( 'SELECT SUM( size ) FROM files_info WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_FILES: result = c.execute( 'SELECT COUNT( * ) FROM deleted_files WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_FILES: result = c.execute( 'SELECT COUNT( * ) FROM file_transfers WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_FILES: result = c.execute( 'SELECT COUNT( * ) FROM file_petitions where service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_THUMBNAILS: result = c.execute( 'SELECT COUNT( * ) FROM files_info WHERE service_id = ? AND mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ';', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL:
                        
                        thumbnails_i_have = CC.GetAllThumbnailHashes()
                        
                        hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' AND service_id = ?;', ( service_id, ) ) ]
                        
                        thumbnails_i_should_have = self._GetHashes( c, hash_ids )
                        
                        thumbnails_i_have.intersection_update( thumbnails_i_should_have )
                        
                        result = ( len( thumbnails_i_have ), )
                        
                    elif info_type == HC.SERVICE_INFO_NUM_INBOX: result = c.execute( 'SELECT COUNT( * ) FROM file_inbox, files_info USING ( hash_id ) WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    if info_type in ( HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ): save_it = False
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = c.execute( 'SELECT COUNT( DISTINCT hash_id ) FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.CURRENT, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_NAMESPACES: result = c.execute( 'SELECT COUNT( DISTINCT namespace_id ) FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.CURRENT, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_TAGS: result = c.execute( 'SELECT COUNT( DISTINCT tag_id ) FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.CURRENT, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_MAPPINGS: result = c.execute( 'SELECT COUNT( * ) FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( service_id, HC.CURRENT, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_MAPPINGS: result = c.execute( 'SELECT COUNT( * ) FROM mappings WHERE service_id = ? AND status = ?;', ( service_id, HC.DELETED ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_MAPPINGS: result = c.execute( 'SELECT COUNT( * ) FROM mappings WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS: result = c.execute( 'SELECT COUNT( * ) FROM mapping_petitions WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS: result = c.execute( 'SELECT COUNT( * ) FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS: result = c.execute( 'SELECT COUNT( * ) FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PETITIONED ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS: result = c.execute( 'SELECT COUNT( * ) FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS: result = c.execute( 'SELECT COUNT( * ) FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.PETITIONED ) ).fetchone()
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = c.execute( 'SELECT COUNT( * ) FROM local_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type == HC.LOCAL_BOORU:
                    
                    if info_type == HC.SERVICE_INFO_NUM_SHARES: result = c.execute( 'SELECT COUNT( * ) FROM yaml_dumps WHERE dump_type = ?;', ( YAML_DUMP_ID_LOCAL_BOORU, ) ).fetchone()
                    
                
                if result is None: info = 0
                else: ( info, ) = result
                
                if info is None: info = 0
                
                if save_it: c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, info_type, info ) )
                
                results[ info_type ] = info
                
            
        
        return results
        
    
    def _GetShutdownTimestamps( self, c ):
        
        shutdown_timestamps = collections.defaultdict( lambda: 0 )
        
        shutdown_timestamps.update( c.execute( 'SELECT shutdown_type, timestamp FROM shutdown_timestamps;' ).fetchall() )
        
        return shutdown_timestamps
        
    
    def _GetTagArchiveInfo( self, c ): return { archive_name : hta.GetNamespaces() for ( archive_name, hta ) in self._tag_archives.items() }
    
    def _GetTagArchiveTags( self, c, hashes ):
        
        result = {}
        
        for ( archive_name, hta ) in self._tag_archives.items():
            
            hash_type == hta.GetHashType()
            
            sha256_to_archive_hashes = {}
            
            if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                
                sha256_to_archive_hashes = { hash : hash for hash in hashes }
                
            else:
                
                if hash_type == HydrusTagArchive.HASH_TYPE_MD5: h = 'md5'
                elif hash_type == HydrusTagArchive.HASH_TYPE_SHA1: h = 'sha1'
                elif hash_type == HydrusTagArchive.HASH_TYPE_SHA512: h = 'sha512'
                
                for hash in hashes:
                    
                    hash_id = self._GetHashId( c, hash )
                    
                    ( archive_hash, ) = c.execute( 'SELECT ' + h + ' FROM local_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                    
                    sha256_to_archive_hashes[ hash ] = archive_hash
                    
                
            
            hashes_to_tags = { hash : hta.GetMappings( sha256_to_archive_hashes[ hash ] ) for hash in hashes }
            
            result[ archive_name ] = hashes_to_tags
            
        
        return result
        
    
    def _GetTagCensorship( self, c, service_key = None ):
        
        if service_key is None:
            
            result = []
            
            for ( service_id, blacklist, tags ) in c.execute( 'SELECT service_id, blacklist, tags FROM tag_censorship;' ).fetchall():
                
                service = self._GetService( c, service_id )
                
                service_key = service.GetServiceKey()
                
                result.append( ( service_key, blacklist, tags ) )
                
            
        else:
            
            service_id = self._GetServiceId( c, service_key )
            
            result = c.execute( 'SELECT blacklist, tags FROM tag_censorship WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            if result is None: result = ( True, [] )
            
        
        return result
        
    
    def _GetTagParents( self, c, service_key = None ):
        
        if service_key is None:
            
            service_ids_to_statuses_and_pair_ids = HC.BuildKeyToListDict( ( ( service_id, ( status, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id ) ) for ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status ) in c.execute( 'SELECT service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status FROM tag_parents UNION SELECT service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status FROM tag_parent_petitions;' ) ) )
            
            service_keys_to_statuses_to_pairs = collections.defaultdict( HC.default_dict_set )
            
            for ( service_id, statuses_and_pair_ids ) in service_ids_to_statuses_and_pair_ids.items():
                
                service = self._GetService( c, service_id )
                
                service_key = service.GetServiceKey()
                
                statuses_to_pairs = HC.BuildKeyToSetDict( ( ( status, ( self._GetNamespaceTag( c, child_namespace_id, child_tag_id ), self._GetNamespaceTag( c, parent_namespace_id, parent_tag_id ) ) ) for ( status, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id ) in statuses_and_pair_ids ) )
                
                service_keys_to_statuses_to_pairs[ service_key ] = statuses_to_pairs
                
            
            return service_keys_to_statuses_to_pairs
            
        else:
            
            service_id = self._GetServiceId( c, service_key )
            
            statuses_and_pair_ids = c.execute( 'SELECT child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status FROM tag_parents WHERE service_id = ? UNION SELECT child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status FROM tag_parent_petitions WHERE service_id = ?;', ( service_id, service_id ) ).fetchall()
            
            statuses_to_pairs = HC.BuildKeyToSetDict( ( ( status, ( self._GetNamespaceTag( c, child_namespace_id, child_tag_id ), self._GetNamespaceTag( c, parent_namespace_id, parent_tag_id ) ) ) for ( child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status ) in statuses_and_pair_ids ) )
            
            return statuses_to_pairs
            
        
    
    def _GetTagSiblings( self, c, service_key = None ):
        
        if service_key is None:
            
            service_ids_to_statuses_and_pair_ids = HC.BuildKeyToListDict( ( ( service_id, ( status, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id ) ) for ( service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status ) in c.execute( 'SELECT service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status FROM tag_siblings UNION SELECT service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status FROM tag_sibling_petitions;' ) ) )
            
            service_keys_to_statuses_to_pairs = collections.defaultdict( HC.default_dict_set )
            
            for ( service_id, statuses_and_pair_ids ) in service_ids_to_statuses_and_pair_ids.items():
                
                service = self._GetService( c, service_id )
                
                service_key = service.GetServiceKey()
                
                statuses_to_pairs = HC.BuildKeyToSetDict( ( ( status, ( self._GetNamespaceTag( c, old_namespace_id, old_tag_id ), self._GetNamespaceTag( c, new_namespace_id, new_tag_id ) ) ) for ( status, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id ) in statuses_and_pair_ids ) )
                
                service_keys_to_statuses_to_pairs[ service_key ] = statuses_to_pairs
                
            
            return service_keys_to_statuses_to_pairs
            
        else:
            
            service_id = self._GetServiceId( c, service_key )
            
            statuses_and_pair_ids = c.execute( 'SELECT old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status FROM tag_siblings WHERE service_id = ? UNION SELECT old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status FROM tag_sibling_petitions WHERE service_id = ?;', ( service_id, service_id ) ).fetchall()
            
            statuses_to_pairs = HC.BuildKeyToSetDict( ( ( status, ( self._GetNamespaceTag( c, old_namespace_id, old_tag_id ), self._GetNamespaceTag( c, new_namespace_id, new_tag_id ) ) ) for ( old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status ) in statuses_and_pair_ids ) )
            
            return statuses_to_pairs
            
        
    
    def _GetThumbnailHashesIShouldHave( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE mime IN ' + HC.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' AND service_id = ?;', ( service_id, ) ) ]
        
        hashes = set( self._GetHashes( c, hash_ids ) )
        
        return hashes
        
    
    def _GetURLStatus( self, c, url ):
        
        result = c.execute( 'SELECT hash_id FROM urls WHERE url = ?;', ( url, ) ).fetchone()
        
        if result is not None:
            
            ( hash_id, ) = result
            
            if HC.options[ 'exclude_deleted_files' ]:
                
                result = c.execute( 'SELECT 1 FROM deleted_files WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                
                if result is not None: return ( 'deleted', None )
                
            
            result = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone()
            
            if result is not None:
                
                hash = self._GetHash( c, hash_id )
                
                return ( 'redundant', hash )
                
            
        
        return ( 'new', None )
        
    
    def _GetWebSessions( self, c ):
        
        now = HC.GetNow()
        
        c.execute( 'DELETE FROM web_sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        sessions = c.execute( 'SELECT name, cookies, expiry FROM web_sessions;' ).fetchall()
        
        return sessions
        
    
    def _GetYAMLDump( self, c, dump_type, dump_name = None ):
        
        if dump_name is None:
            
            result = { dump_name : data for ( dump_name, data ) in c.execute( 'SELECT dump_name, dump FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) ) }
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
                
                result = { dump_name.decode( 'hex' ) : data for ( dump_name, data ) in result.items() }
                
            
        else:
            
            if dump_type == YAML_DUMP_ID_SUBSCRIPTION and dump_name in self._subscriptions_cache: return self._subscriptions_cache[ dump_name ]
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.encode( 'hex' )
            
            result = c.execute( 'SELECT dump FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) ).fetchone()
            
            if result is None:
                
                if dump_type == YAML_DUMP_ID_SINGLE:
                    
                    if dump_name == '4chan_pass': result = ( '', '', 0 )
                    elif dump_name == 'pixiv_account': result = ( '', '' )
                    
                
                if result is None: raise Exception( dump_name + ' was not found!' )
                
            else: ( result, ) = result
            
            if dump_type == YAML_DUMP_ID_SUBSCRIPTION: self._subscriptions_cache[ dump_name ] = result
            
        
        return result
        
    
    def _GetYAMLDumpNames( self, c, dump_type ):
        
        names = [ name for ( name, ) in c.execute( 'SELECT dump_name FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) ) ]
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            names = [ name.decode( 'hex' ) for name in names ]
            
        
        return names
        
    
    def _ImportFile( self, c, path, advanced_import_options = {}, service_keys_to_tags = {}, generate_media_result = False, override_deleted = False, url = None ):
        
        result = 'successful'
        
        can_add = True
        
        archive = 'auto_archive' in advanced_import_options
        
        exclude_deleted_files = 'exclude_deleted_files' in advanced_import_options
        
        HydrusImageHandling.ConvertToPngIfBmp( path )
        
        hash = HydrusFileHandling.GetHashFromPath( path )
        
        hash_id = self._GetHashId( c, hash )
        
        if url is not None: c.execute( 'INSERT OR IGNORE INTO urls ( url, hash_id ) VALUES ( ?, ? );', ( url, hash_id ) )
        
        already_in_db = c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone() is not None
        
        if already_in_db:
            
            result = 'redundant'
            
            if archive:
                
                c.execute( 'DELETE FROM file_inbox WHERE hash_id = ?;', ( hash_id, ) )
                
                self.pub_content_updates_after_commit( { HC.LOCAL_FILE_SERVICE_KEY : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, set( ( hash, ) ) ) ] } )
                
            
            can_add = False
            
        else:
            
            if not override_deleted:
                
                if exclude_deleted_files and c.execute( 'SELECT 1 FROM deleted_files WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone() is not None:
                    
                    result = 'deleted'
                    
                    can_add = False
                    
                
            
        
        if can_add:
            
            ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( path )
            
            if width is not None and height is not None:
                
                if 'min_resolution' in advanced_import_options:
                    
                    ( min_x, min_y ) = advanced_import_options[ 'min_resolution' ]
                    
                    if width < min_x or height < min_y: raise Exception( 'Resolution too small' )
                    
                
            
            if 'min_size' in advanced_import_options:
                
                min_size = advanced_import_options[ 'min_size' ]
                
                if size < min_size: raise Exception( 'File too small' )
                
            
            timestamp = HC.GetNow()
            
            dest_path = CC.GetExpectedFilePath( hash, mime )
            
            if not os.path.exists( dest_path ):
                
                shutil.copy( path, dest_path )
                
                os.chmod( dest_path, stat.S_IREAD )
                
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                thumbnail = HydrusFileHandling.GenerateThumbnail( path )
                
                self._AddThumbnails( c, [ ( hash, thumbnail ) ] )
                
            
            self._AddFile( c, self._local_file_service_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words )
            
            content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) )
            
            self.pub_content_updates_after_commit( { HC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
            
            ( md5, sha1, sha512 ) = HydrusFileHandling.GetExtraHashesFromPath( path )
            
            c.execute( 'INSERT OR IGNORE INTO local_hashes ( hash_id, md5, sha1, sha512 ) VALUES ( ?, ?, ?, ? );', ( hash_id, sqlite3.Binary( md5 ), sqlite3.Binary( sha1 ), sqlite3.Binary( sha512 ) ) )
            
            if not archive: self._InboxFiles( c, ( hash_id, ) )
            
        
        if len( service_keys_to_tags ) > 0 and c.execute( 'SELECT 1 FROM files_info WHERE service_id = ? AND hash_id = ?;', ( self._local_file_service_id, hash_id ) ).fetchone() is not None:
            
            service_keys_to_content_updates = collections.defaultdict( list )
            
            for ( service_key, tags ) in service_keys_to_tags.items():
                
                if service_key == HC.LOCAL_TAG_SERVICE_KEY: action = HC.CONTENT_UPDATE_ADD
                else: action = HC.CONTENT_UPDATE_PENDING
                
                hashes = set( ( hash, ) )
                
                service_keys_to_content_updates[ service_key ].extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, action, ( tag, hashes ) ) for tag in tags ) )
                
            
            self._ProcessContentUpdates( c, service_keys_to_content_updates )
            
        
        tag_services = self._GetServices( c, HC.TAG_SERVICES )
        
        for service in tag_services:
            
            service_key = service.GetServiceKey()
            info = service.GetInfo()
            
            tag_archive_sync = info[ 'tag_archive_sync' ]
            
            for ( archive_name, namespaces ) in tag_archive_sync.items():
                
                try: self._SyncToTagArchive( c, hash_id, archive_name, namespaces, service_key )
                except: pass
                
            
        
        if generate_media_result:
            
            if ( can_add or already_in_db ):
                
                ( media_result, ) = self._GetMediaResults( c, HC.LOCAL_FILE_SERVICE_KEY, { hash_id } )
                
                return ( result, media_result )
                
            else: return ( result, None )
            
        else: return ( result, hash )
        
    
    def _InboxFiles( self, c, hash_ids ):
        
        c.executemany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', [ ( hash_id, ) for hash_id in hash_ids ] )
        
        num_added = self._GetRowCount( c )
        
        if num_added > 0:
            
            splayed_hash_ids = HC.SplayListForDB( hash_ids )
            
            updates = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id;' ).fetchall()
            
            c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in updates ] )
            
        
    
    def _InitialiseTagArchiveSync( self, c, archive_name, namespaces, service_key ):
        
        prefix_string = 'initialising sync to tag archive ' + archive_name + ': '
        
        job_key = HC.JobKey( pausable = False, cancellable = False )
        
        message = HC.MessageGauge( HC.MESSAGE_TYPE_GAUGE, prefix_string + 'preparing', job_key )
        
        HC.pubsub.pub( 'message', message )
        
        hash_ids = [ hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM files_info WHERE service_id = ?;', ( self._local_file_service_id, ) ) ]
        
        block_size = 100
        
        next_block = []
        
        for ( i, hash_id ) in enumerate( hash_ids ):
            
            try: self._SyncToTagArchive( c, hash_id, archive_name, namespaces, service_key )
            except: pass
            
            if i % 100 == 0:
                
                message.SetInfo( 'range', len( hash_ids ) )
                message.SetInfo( 'value', i )
                message.SetInfo( 'text', prefix_string + HC.ConvertIntToPrettyString( i ) + '/' + HC.ConvertIntToPrettyString( len( hash_ids ) ) )
                message.SetInfo( 'mode', 'gauge' )
                
            
        
        message.SetInfo( 'text', prefix_string + 'done!' )
        message.SetInfo( 'mode', 'text' )
        
        self.pub_after_commit( 'notify_new_pending' )
        
    
    def _ProcessContentUpdates( self, c, service_keys_to_content_updates, pub_immediate = False ):
        
        notify_new_downloads = False
        notify_new_pending = False
        notify_new_parents = False
        notify_new_siblings = False
        notify_new_thumbnails = False
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            try: service_id = self._GetServiceId( c, service_key )
            except: continue
            
            service = self._GetService( c, service_id )
            
            service_type = service.GetServiceType()
            
            ultimate_mappings_ids = []
            ultimate_deleted_mappings_ids = []
            
            ultimate_pending_mappings_ids = []
            ultimate_pending_rescinded_mappings_ids = []
            
            ultimate_petitioned_mappings_ids = []
            ultimate_petitioned_rescinded_mappings_ids = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if service_type in ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ):
                    
                    if data_type == HC.CONTENT_DATA_TYPE_FILES:
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) = row
                            
                            hash_id = self._GetHashId( c, hash )
                            
                            self._AddFile( c, service_id, hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words )
                            
                            notify_new_thumbnails = True
                            
                        elif action == HC.CONTENT_UPDATE_PENDING:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( c, hashes )
                            
                            c.executemany( 'INSERT OR IGNORE INTO file_transfers ( service_id, hash_id ) VALUES ( ?, ? );', [ ( service_id, hash_id ) for hash_id in hash_ids ] )
                            
                            if service_key == HC.LOCAL_FILE_SERVICE_KEY: notify_new_downloads = True
                            else: notify_new_pending = True
                            
                        elif action == HC.CONTENT_UPDATE_PETITION:
                            
                            ( hashes, reason ) = row
                            
                            hash_ids = self._GetHashIds( c, hashes )
                            
                            reason_id = self._GetReasonId( c, reason )
                            
                            c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
                            
                            c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, hash_id, reason_id ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, reason_id ) for hash_id in hash_ids ] )
                            
                            notify_new_pending = True
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PENDING:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( c, hashes )
                            
                            c.execute( 'DELETE FROM file_transfers WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
                            
                            notify_new_pending = True
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( c, hashes )
                            
                            c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
                            
                            notify_new_pending = True
                            
                        else:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( c, hashes )
                            
                            if action == HC.CONTENT_UPDATE_ARCHIVE: self._ArchiveFiles( c, hash_ids )
                            elif action == HC.CONTENT_UPDATE_INBOX: self._InboxFiles( c, hash_ids )
                            elif action == HC.CONTENT_UPDATE_DELETE: self._DeleteFiles( c, service_id, hash_ids )
                            
                        
                    
                elif service_type in ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ):
                    
                    if data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
                        
                        if action == HC.CONTENT_UPDATE_ADVANCED:
                            
                            c.execute( 'CREATE TABLE temp_operation ( job_id INTEGER PRIMARY KEY AUTOINCREMENT, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER );' )
                            
                            predicates = [ 'service_id = ' + str( service_id ) ]
                            
                            ( sub_action, sub_row ) = row
                            
                            if sub_action == 'copy':
                                
                                ( tag, hashes, service_key_target ) = sub_row
                                
                                service_id_target = self._GetServiceId( c, service_key_target )
                                
                                predicates.append( 'status = ' + str( HC.CURRENT ) )
                                
                            elif sub_action == 'delete':
                                
                                ( tag, hashes ) = sub_row
                                
                                predicates.append( 'status = ' + str( HC.CURRENT ) )
                                
                            elif sub_action == 'delete_deleted':
                                
                                ( tag, hashes ) = sub_row
                                
                                predicates.append( 'status = ' + str( HC.DELETED ) )
                                
                            
                            if tag is not None:
                                
                                ( tag_type, tag ) = tag
                                
                                if tag_type == 'tag':
                                    
                                    ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                                    
                                    predicates.append( 'namespace_id = ' + str( namespace_id ) )
                                    predicates.append( 'tag_id = ' + str( tag_id ) )
                                    
                                elif tag_type == 'namespace':
                                    
                                    namespace_id = self._GetNamespaceId( c, tag )
                                    
                                    predicates.append( 'namespace_id = ' + str( namespace_id ) )
                                    
                                
                            
                            if hashes is not None:
                                
                                hash_ids = self._GetHashIds( c, hashes )
                                
                                predicates.append( 'hash_id IN ' + HC.SplayListForDB( hash_ids ) )
                                
                            
                            c.execute( 'INSERT INTO temp_operation ( namespace_id, tag_id, hash_id ) SELECT namespace_id, tag_id, hash_id FROM mappings WHERE ' + ' AND '.join( predicates ) + ';' )
                            
                            num_to_do = self._GetRowCount( c )
                            
                            i = 0
                            
                            block_size = 1000
                            
                            while i < num_to_do:
                                
                                advanced_mappings_ids = c.execute( 'SELECT namespace_id, tag_id, hash_id FROM temp_operation WHERE job_id BETWEEN ? AND ?;', ( i, i + block_size - 1 ) )
                                
                                advanced_mappings_ids = HC.BuildKeyToListDict( ( ( ( namespace_id, tag_id ), hash_id ) for ( namespace_id, tag_id, hash_id ) in advanced_mappings_ids ) )
                                
                                advanced_mappings_ids = [ ( namespace_id, tag_id, hash_ids ) for ( ( namespace_id, tag_id ), hash_ids ) in advanced_mappings_ids.items() ]
                                
                                if sub_action == 'copy':
                                    
                                    service_target = self._GetService( c, service_id_target )
                                    
                                    if service_target.GetServiceType() == HC.LOCAL_TAG: kwarg = 'mappings_ids'
                                    else: kwarg = 'pending_mappings_ids'
                                    
                                    kwargs = { kwarg : advanced_mappings_ids }
                                    
                                    self._UpdateMappings( c, service_id_target, **kwargs )
                                    
                                elif sub_action == 'delete':
                                    
                                    self._UpdateMappings( c, service_id, deleted_mappings_ids = advanced_mappings_ids )
                                    
                                elif sub_action == 'delete_deleted':
                                    
                                    for ( namespace_id, tag_id, hash_ids ) in advanced_mappings_ids:
                                        
                                        c.execute( 'DELETE FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( service_id, namespace_id, tag_id ) )
                                        
                                    
                                    c.execute( 'DELETE FROM service_info WHERE service_id = ?;', ( service_id, ) )
                                    
                                
                                i += block_size
                                
                            
                            c.execute( 'DROP TABLE temp_operation;' )
                            
                            self.pub_after_commit( 'notify_new_pending' )
                            
                        else:
                            
                            if action == HC.CONTENT_UPDATE_PETITION: ( tag, hashes, reason ) = row
                            else: ( tag, hashes ) = row
                            
                            if tag == '': continue
                            
                            ( namespace_id, tag_id ) = self._GetNamespaceIdTagId( c, tag )
                            
                            hash_ids = self._GetHashIds( c, hashes )
                            
                            if action == HC.CONTENT_UPDATE_ADD: ultimate_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            elif action == HC.CONTENT_UPDATE_DELETE: ultimate_deleted_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            elif action == HC.CONTENT_UPDATE_PENDING: ultimate_pending_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            elif action == HC.CONTENT_UPDATE_RESCIND_PENDING: ultimate_pending_rescinded_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                reason_id = self._GetReasonId( c, reason )
                                
                                ultimate_petitioned_mappings_ids.append( ( namespace_id, tag_id, hash_ids, reason_id ) )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: ultimate_petitioned_rescinded_mappings_ids.append( ( namespace_id, tag_id, hash_ids ) )
                            
                        
                    elif data_type == HC.CONTENT_DATA_TYPE_TAG_SIBLINGS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            if action == HC.CONTENT_UPDATE_ADD: ( deletee_status, new_status ) = ( HC.PENDING, HC.CURRENT )
                            elif action == HC.CONTENT_UPDATE_DELETE: ( deletee_status, new_status ) = ( HC.PETITIONED, HC.DELETED )
                            
                            ( old_tag, new_tag ) = row
                            
                            ( old_namespace_id, old_tag_id ) = self._GetNamespaceIdTagId( c, old_tag )
                            
                            ( new_namespace_id, new_tag_id ) = self._GetNamespaceIdTagId( c, new_tag )
                            
                            c.execute( 'DELETE FROM tag_siblings WHERE service_id = ? AND old_namespace_id = ? AND old_tag_id = ?;', ( service_id, old_namespace_id, old_tag_id ) )
                            c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND old_namespace_id = ? AND old_tag_id = ? AND status = ?;', ( service_id, old_namespace_id, old_tag_id, deletee_status ) )
                            
                            c.execute( 'INSERT OR IGNORE INTO tag_siblings ( service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, new_status ) )
                            
                        elif action in ( HC.CONTENT_UPDATE_PENDING, HC.CONTENT_UPDATE_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_PENDING: new_status = HC.PENDING
                            elif action == HC.CONTENT_UPDATE_PETITION: new_status = HC.PETITIONED
                            
                            ( ( old_tag, new_tag ), reason ) = row
                            
                            ( old_namespace_id, old_tag_id ) = self._GetNamespaceIdTagId( c, old_tag )
                            
                            ( new_namespace_id, new_tag_id ) = self._GetNamespaceIdTagId( c, new_tag )
                            
                            reason_id = self._GetReasonId( c, reason )
                            
                            c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND old_namespace_id = ? AND old_tag_id = ?;', ( service_id, old_namespace_id, old_tag_id ) )
                            
                            c.execute( 'INSERT OR IGNORE INTO tag_sibling_petitions ( service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, reason_id, status ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, reason_id, new_status ) )
                            
                            notify_new_pending = True
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PENDING, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PENDING: deletee_status = HC.PENDING
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: deletee_status = HC.PETITIONED
                            
                            ( old_tag, new_tag ) = row
                            
                            ( old_namespace_id, old_tag_id ) = self._GetNamespaceIdTagId( c, old_tag )
                            
                            c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND old_namespace_id = ? AND old_tag_id = ? AND status = ?;', ( service_id, old_namespace_id, old_tag_id, deletee_status ) )
                            
                            notify_new_pending = True
                            
                        
                        notify_new_siblings = True
                        
                    elif data_type == HC.CONTENT_DATA_TYPE_TAG_PARENTS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            if action == HC.CONTENT_UPDATE_ADD: ( deletee_status, new_status ) = ( HC.PENDING, HC.CURRENT )
                            elif action == HC.CONTENT_UPDATE_DELETE: ( deletee_status, new_status ) = ( HC.PETITIONED, HC.DELETED )
                            
                            ( child_tag, parent_tag ) = row
                            
                            ( child_namespace_id, child_tag_id ) = self._GetNamespaceIdTagId( c, child_tag )
                            
                            ( parent_namespace_id, parent_tag_id ) = self._GetNamespaceIdTagId( c, parent_tag )
                            
                            c.execute( 'DELETE FROM tag_parents WHERE service_id = ? AND child_namespace_id = ? AND child_tag_id = ? AND parent_namespace_id = ? AND parent_tag_id = ?;', ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id ) )
                            c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_namespace_id = ? AND child_tag_id = ? AND parent_namespace_id = ? AND parent_tag_id = ? AND status = ?;', ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, deletee_status ) )
                            
                            c.execute( 'INSERT OR IGNORE INTO tag_parents ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status ) VALUES ( ?, ?, ?, ?, ?, ? );', ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, new_status ) )
                            
                            if action == HC.CONTENT_UPDATE_ADD and service_key == HC.LOCAL_TAG_SERVICE_KEY:
                                
                                existing_hash_ids = [ hash for ( hash, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND status = ?;', ( service_id, child_namespace_id, child_tag_id, HC.CURRENT ) ) ]
                                
                                existing_hashes = self._GetHashes( c, existing_hash_ids )
                                
                                mappings_ids = [ ( parent_namespace_id, parent_tag_id, existing_hash_ids ) ]
                                
                                self._UpdateMappings( c, service_id, mappings_ids = mappings_ids )
                                
                                special_content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( parent_tag, existing_hashes ) )
                                
                                self.pub_content_updates_after_commit( { service_key : [ special_content_update ] } )
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PENDING, HC.CONTENT_UPDATE_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_PENDING: new_status = HC.PENDING
                            elif action == HC.CONTENT_UPDATE_PETITION: new_status = HC.PETITIONED
                            
                            ( ( child_tag, parent_tag ), reason ) = row
                            
                            ( child_namespace_id, child_tag_id ) = self._GetNamespaceIdTagId( c, child_tag )
                            
                            ( parent_namespace_id, parent_tag_id ) = self._GetNamespaceIdTagId( c, parent_tag )
                            
                            reason_id = self._GetReasonId( c, reason )
                            
                            c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_namespace_id = ? AND child_tag_id = ? AND parent_namespace_id = ? AND parent_tag_id = ?;', ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id ) )
                            
                            c.execute( 'INSERT OR IGNORE INTO tag_parent_petitions ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, reason_id, status ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, reason_id, new_status ) )
                            
                            if action == HC.CONTENT_UPDATE_PENDING:
                                
                                existing_hash_ids = [ hash for ( hash, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND status IN ( ?, ? );', ( service_id, child_namespace_id, child_tag_id, HC.CURRENT, HC.PENDING ) ) ]
                                
                                existing_hashes = self._GetHashes( c, existing_hash_ids )
                                
                                mappings_ids = [ ( parent_namespace_id, parent_tag_id, existing_hash_ids ) ]
                                
                                self._UpdateMappings( c, service_id, pending_mappings_ids = mappings_ids )
                                
                                special_content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( parent_tag, existing_hashes ) )
                                
                                self.pub_content_updates_after_commit( { service_key : [ special_content_update ] } )
                                
                            
                            notify_new_pending = True
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PENDING, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PENDING: deletee_status = HC.PENDING
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION: deletee_status = HC.PETITIONED
                            
                            ( child_tag, parent_tag ) = row
                            
                            ( child_namespace_id, child_tag_id ) = self._GetNamespaceIdTagId( c, child_tag )
                            
                            ( parent_namespace_id, parent_tag_id ) = self._GetNamespaceIdTagId( c, parent_tag )
                            
                            c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_namespace_id = ? AND child_tag_id = ? AND parent_namespace_id = ? AND parent_tag_id = ? AND status = ?;', ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, deletee_status ) )
                            
                            notify_new_pending = True
                            
                        
                        notify_new_parents = True
                        
                    
                elif service_type in HC.RATINGS_SERVICES:
                    
                    if action == HC.CONTENT_UPDATE_ADD:
                        
                        ( rating, hashes ) = row
                        
                        hash_ids = self._GetHashIds( c, hashes )
                        
                        splayed_hash_ids = HC.SplayListForDB( hash_ids )
                        
                        if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                            
                            ratings_added = 0
                            
                            c.execute( 'DELETE FROM local_ratings WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                            
                            rowcount = self._GetRowCount( c )
                            
                            if rating is not None:
                                
                                c.execute( 'DELETE FROM ratings_filter WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                                
                                c.executemany( 'INSERT INTO local_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                                
                                ratings_added += self._GetRowCount( c )
                                
                            
                            c.execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                            
                            # and then do a thing here where it looks up remote services links and then pends/rescinds pends appropriately
                            
                        
                    elif action == HC.CONTENT_UPDATE_RATINGS_FILTER:
                        
                        ( min, max, hashes ) = row
                        
                        hash_ids = self._GetHashIds( c, hashes )
                        
                        splayed_hash_ids = HC.SplayListForDB( hash_ids )
                        
                        c.execute( 'DELETE FROM ratings_filter WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                        
                        c.executemany( 'INSERT INTO ratings_filter ( service_id, hash_id, min, max ) VALUES ( ?, ?, ?, ? );', [ ( service_id, hash_id, min, max ) for hash_id in hash_ids ] )
                        
                    
                
            
            if len( ultimate_mappings_ids ) + len( ultimate_deleted_mappings_ids ) + len( ultimate_pending_mappings_ids ) + len( ultimate_pending_rescinded_mappings_ids ) + len( ultimate_petitioned_mappings_ids ) + len( ultimate_petitioned_rescinded_mappings_ids ) > 0:
                
                self._UpdateMappings( c, service_id, mappings_ids = ultimate_mappings_ids, deleted_mappings_ids = ultimate_deleted_mappings_ids, pending_mappings_ids = ultimate_pending_mappings_ids, pending_rescinded_mappings_ids = ultimate_pending_rescinded_mappings_ids, petitioned_mappings_ids = ultimate_petitioned_mappings_ids, petitioned_rescinded_mappings_ids = ultimate_petitioned_rescinded_mappings_ids )
                
                notify_new_pending = True
                
            
        
        if pub_immediate:
            
            HC.pubsub.pub( 'content_updates_data', service_keys_to_content_updates )
            HC.pubsub.pub( 'content_updates_gui', service_keys_to_content_updates )
            
        else:
            
            if notify_new_downloads: self.pub_after_commit( 'notify_new_downloads' )
            if notify_new_pending: self.pub_after_commit( 'notify_new_pending' )
            if notify_new_parents: self.pub_after_commit( 'notify_new_parents' )
            if notify_new_siblings:
                
                self.pub_after_commit( 'notify_new_siblings' )
                self.pub_after_commit( 'notify_new_parents' )
                
            if notify_new_thumbnails: self.pub_after_commit( 'notify_new_thumbnails' )
            
            self.pub_content_updates_after_commit( service_keys_to_content_updates )
            
        
    
    def _ProcessServiceUpdates( self, c, service_keys_to_service_updates ):
        
        do_new_permissions = False
        
        hydrus_requests_made = []
        local_booru_requests_made = []
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            try: service_id = self._GetServiceId( c, service_key )
            except: continue
            
            service = self._GetService( c, service_id )
            
            ( service_key, service_type, name, info ) = service.ToTuple()
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action == HC.SERVICE_UPDATE_ACCOUNT:
                    
                    account = row
                    
                    update = { 'account' : account, 'last_error' : 0 }
                    
                    self._UpdateServiceInfo( c, service_id, update )
                    
                    do_new_permissions = True
                    
                elif action == HC.SERVICE_UPDATE_ERROR:
                    
                    update = { 'last_error' : HC.GetNow() }
                    
                    self._UpdateServiceInfo( c, service_id, update )
                    
                elif action == HC.SERVICE_UPDATE_REQUEST_MADE:
                    
                    num_bytes = row
                    
                    if service_type == HC.LOCAL_BOORU: local_booru_requests_made.append( num_bytes )
                    else: hydrus_requests_made.append( ( service_id, num_bytes ) )
                    
                elif action == HC.SERVICE_UPDATE_NEWS:
                    
                    news_rows = row
                    
                    c.executemany( 'INSERT OR IGNORE INTO news VALUES ( ?, ?, ? );', [ ( service_id, post, timestamp ) for ( post, timestamp ) in news_rows ] )
                    
                    now = HC.GetNow()
                    
                    for ( post, timestamp ) in news_rows:
                        
                        if now - timestamp < 86400 * 7:
                            
                            text = name + ' at ' + time.ctime( timestamp ) + ':' + os.linesep * 2 + post
                            
                            self.pub_after_commit( 'message', HC.Message( HC.MESSAGE_TYPE_TEXT, { 'text' : text } ) )
                            
                        
                    
                elif action == HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP:
                    
                    next_download_timestamp = row
                    
                    if next_download_timestamp > info[ 'next_download_timestamp' ]:
                        
                        if info[ 'first_timestamp' ] is None: update = { 'first_timestamp' : next_download_timestamp, 'next_download_timestamp' : next_download_timestamp }
                        else: update = { 'next_download_timestamp' : next_download_timestamp }
                        
                        self._UpdateServiceInfo( c, service_id, update )
                        
                    
                elif action == HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP:
                    
                    next_processing_timestamp = row
                    
                    if next_processing_timestamp > info[ 'next_processing_timestamp' ]:
                        
                        info_update = { 'next_processing_timestamp' : next_processing_timestamp }
                        
                        self._UpdateServiceInfo( c, service_id, info_update )
                        
                    
                
            
            self.pub_service_updates_after_commit( service_keys_to_service_updates )
            
        
        for ( service_id, nums_bytes ) in HC.BuildKeyToListDict( hydrus_requests_made ).items():
            
            service = self._GetService( c, service_id )
            
            info = service.GetInfo()
            
            account = info[ 'account' ]
            
            for num_bytes in nums_bytes: account.RequestMade( num_bytes )
            
            c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
            
        
        if len( local_booru_requests_made ) > 0:
            
            service_id = self._GetServiceId( c, HC.LOCAL_BOORU_SERVICE_KEY )
            
            service = self._GetService( c, service_id )
            
            info = service.GetInfo()
            
            current_time_struct = time.gmtime()
            
            ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
            
            ( booru_year, booru_month ) = info[ 'current_data_month' ]
            
            if current_year != booru_year or current_month != booru_month:
                
                info[ 'used_monthly_data' ] = 0
                info[ 'used_monthly_requests' ] = 0
                
                info[ 'current_data_month' ] = ( current_year, current_month )
                
            
            info[ 'used_monthly_data' ] += sum( local_booru_requests_made )
            info[ 'used_monthly_requests' ] += len( local_booru_requests_made )
            
            c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
            
        
        if do_new_permissions: self.pub_after_commit( 'notify_new_permissions' )
        
    
    def _RecalcCombinedMappings( self, c ):
        
        service_ids = self._GetServiceIds( c, ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
        
        c.execute( 'DELETE FROM mappings WHERE service_id = ?;', ( self._combined_tag_service_id, ) )
        
        for service_id in service_ids:
            
            c.execute( 'INSERT OR IGNORE INTO mappings SELECT ?, namespace_id, tag_id, hash_id, status FROM mappings WHERE service_id = ? AND status IN ( ?, ? );', ( self._combined_tag_service_id, service_id, HC.CURRENT, HC.PENDING ) )
            
        
        c.execute( 'DELETE FROM autocomplete_tags_cache WHERE tag_service_id = ?;', ( self._combined_tag_service_id, ) )
        
    
    def _ResetService( self, c, service_key ):
        
        service_id = self._GetServiceId( c, service_key )
        
        service = self._GetService( c, service_id )
        
        ( service_key, service_type, name, info ) = service.ToTuple()
        
        c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
        
        if service_type == HC.TAG_REPOSITORY: self._RecalcCombinedMappings( c )
        
        if service_type in HC.REPOSITORIES:
            
            info[ 'next_processing_timestamp' ] = 0
            
            self.pub_after_commit( 'notify_restart_repo_sync_daemon' )
            
        
        self._AddService( c, service_key, service_type, name, info )
        
        self.pub_service_updates_after_commit( { service_key : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_RESET ) ] } )
        self.pub_after_commit( 'notify_new_pending' )
        self.pub_after_commit( 'notify_new_services_data' )
        self.pub_after_commit( 'notify_new_services_gui' )
        HC.ShowText( 'Service ' + name + ' was reset successfully!' )
        
    
    def _SetTagCensorship( self, c, info ):
        
        c.execute( 'DELETE FROM tag_censorship;' )
        
        for ( service_key, blacklist, tags ) in info:
            
            service_id = self._GetServiceId( c, service_key )
            
            c.execute( 'INSERT OR IGNORE INTO tag_censorship ( service_id, blacklist, tags ) VALUES ( ?, ?, ? );', ( service_id, blacklist, tags ) )
            
        
        self.pub_after_commit( 'notify_new_tag_censorship' )
        
    
    def _SetYAMLDump( self, c, dump_type, dump_name, data ):
        
        if dump_type == YAML_DUMP_ID_SUBSCRIPTION: self._subscriptions_cache[ dump_name ] = data
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.encode( 'hex' )
        
        c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
        
        try: c.execute( 'INSERT INTO yaml_dumps ( dump_type, dump_name, dump ) VALUES ( ?, ?, ? );', ( dump_type, dump_name, data ) )
        except:
            
            print( ( dump_type, dump_name, data ) )
            
            raise
            
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            service_id = self._GetServiceId( c, HC.LOCAL_BOORU_SERVICE_KEY )
            
            c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_SHARES ) )
            
            HC.pubsub.pub( 'refresh_local_booru_shares' )
            
        
    
    def _SyncToTagArchive( self, c, hash_id, archive_name, namespaces, service_key ):
        
        hta = self._tag_archives[ archive_name ]
        
        hash_type = hta.GetHashType()
        
        hash = self._GetHash( c, hash_id )
        
        if hash_type == HydrusTagArchive.HASH_TYPE_SHA256: archive_hash = hash
        else:
            
            if hash_type == HydrusTagArchive.HASH_TYPE_MD5: h = 'md5'
            elif hash_type == HydrusTagArchive.HASH_TYPE_SHA1: h = 'sha1'
            elif hash_type == HydrusTagArchive.HASH_TYPE_SHA512: h = 'sha512'
            
            ( archive_hash, ) = c.execute( 'SELECT ' + h + ' FROM local_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
        
        tags = hta.GetMappings( archive_hash )
        
        desired_tags = HydrusTags.FilterNamespaces( tags, namespaces )
        
        if len( desired_tags ) > 0:
            
            if service_key == HC.LOCAL_TAG_SERVICE_KEY: action = HC.CONTENT_UPDATE_ADD
            else: action = HC.CONTENT_UPDATE_PENDING
            
            rows = [ ( tag, ( hash, )  ) for tag in desired_tags ]
            
            content_updates = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, action, row ) for row in rows ]
            
            service_keys_to_content_updates = { service_key : content_updates }
            
            self._ProcessContentUpdates( c, service_keys_to_content_updates, pub_immediate = True )
            
        
    
    def _UpdateAutocompleteTagCacheFromFiles( self, c, file_service_id, hash_ids, direction ):
        
        splayed_hash_ids = HC.SplayListForDB( hash_ids )
        
        current_tags = c.execute( 'SELECT service_id, namespace_id, tag_id, COUNT( * ) FROM mappings WHERE hash_id IN ' + splayed_hash_ids + ' AND status = ? GROUP BY service_id, namespace_id, tag_id;', ( HC.CURRENT, ) ).fetchall()
        pending_tags = c.execute( 'SELECT service_id, namespace_id, tag_id, COUNT( * ) FROM mappings WHERE hash_id IN ' + splayed_hash_ids + ' AND status = ? GROUP BY service_id, namespace_id, tag_id;', ( HC.PENDING, ) ).fetchall()
        
        c.executemany( 'UPDATE autocomplete_tags_cache SET current_count = current_count + ? WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( tag_service_id, namespace_id, tag_id, count ) in current_tags ] )
        c.executemany( 'UPDATE autocomplete_tags_cache SET pending_count = pending_count + ? WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( tag_service_id, namespace_id, tag_id, count ) in pending_tags ] )
        
    
    def _UpdateMappings( self, c, tag_service_id, mappings_ids = [], deleted_mappings_ids = [], pending_mappings_ids = [], pending_rescinded_mappings_ids = [], petitioned_mappings_ids = [], petitioned_rescinded_mappings_ids = [] ):
        
        # this method grew into a monster that merged deleted, pending and current according to a heirarchy of services
        # this cost a lot of CPU time and was extremely difficult to maintain
        # now it attempts a simpler union, not letting delete overwrite a current or pending
        
        other_service_ids = [ service_id for service_id in self._GetServiceIds( c, ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) ) if service_id != tag_service_id ]
        
        splayed_other_service_ids = HC.SplayListForDB( other_service_ids )
        
        def ChangeMappingStatus( namespace_id, tag_id, hash_ids, old_status, new_status ):
            
            # when we commit a tag that is both deleted and pending, we merge two statuses into one!
            # in this case, we have to be careful about the counts (decrement twice, but only increment once), hence why this returns two numbers
            
            pertinent_hash_ids = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( tag_service_id, namespace_id, tag_id, old_status ) ) ]
            
            existing_hash_ids = { id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( tag_service_id, namespace_id, tag_id, new_status ) ) }
            
            deletable_hash_ids = existing_hash_ids.intersection( pertinent_hash_ids )
            
            c.execute( 'DELETE FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( deletable_hash_ids ) + ' AND status = ?;', ( tag_service_id, namespace_id, tag_id, old_status ) )
            
            num_old_deleted = self._GetRowCount( c )
            
            c.execute( 'UPDATE mappings SET status = ? WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( pertinent_hash_ids ) + ' AND status = ?;', ( new_status, tag_service_id, namespace_id, tag_id, old_status ) )
            
            num_old_made_new = self._GetRowCount( c )
            
            if old_status != HC.PENDING and new_status == HC.PENDING:
                
                UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, pertinent_hash_ids, HC.PENDING, 1 )
                
                UpdateCombinedMappings( namespace_id, tag_id, pertinent_hash_ids, 'insert', HC.PENDING )
                
            
            if old_status == HC.PENDING and new_status != HC.PENDING:
                
                UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, pertinent_hash_ids, HC.PENDING, -1 )
                
                UpdateCombinedMappings( namespace_id, tag_id, pertinent_hash_ids, 'delete', HC.PENDING )
                
            
            if old_status != HC.CURRENT and new_status == HC.CURRENT:
                
                UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, pertinent_hash_ids, HC.CURRENT, 1 )
                
                UpdateCombinedMappings( namespace_id, tag_id, pertinent_hash_ids, 'insert', HC.CURRENT )
                
            
            if old_status == HC.CURRENT and new_status != HC.CURRENT:
                
                UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, pertinent_hash_ids, HC.CURRENT, -1 )
                
                UpdateCombinedMappings( namespace_id, tag_id, pertinent_hash_ids, 'delete', HC.CURRENT )
                
            
            return ( num_old_deleted + num_old_made_new, num_old_made_new )
            
        
        def UpdateCombinedMappings( namespace_id, tag_id, hash_ids, action, status ):
            
            if action == 'delete':
                
                existing_other_service_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id IN ' + splayed_other_service_ids + ' AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( namespace_id, tag_id, status ) ) }
                
                pertinent_hash_ids = set( hash_ids ).difference( existing_other_service_hash_ids )
                
                c.execute( 'DELETE FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( pertinent_hash_ids ) + ' AND status = ?;', ( self._combined_tag_service_id, namespace_id, tag_id, status ) )
                
                direction = -1
                
            elif action == 'insert':
                
                existing_combined_hash_ids = { hash_id for ( hash_id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( self._combined_tag_service_id, namespace_id, tag_id, status ) ) }
                
                pertinent_hash_ids = set( hash_ids ).difference( existing_combined_hash_ids )
                
                c.executemany( 'INSERT OR IGNORE INTO mappings VALUES ( ?, ?, ?, ?, ? );', [ ( self._combined_tag_service_id, namespace_id, tag_id, hash_id, status ) for hash_id in pertinent_hash_ids ] )
                
                direction = 1
                
            
            UpdateAutocompleteTagCache( self._combined_tag_service_id, namespace_id, tag_id, pertinent_hash_ids, status, direction )
            
        
        def DeletePending( namespace_id, tag_id, hash_ids ):
            
            c.execute( 'DELETE FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status = ?;', ( tag_service_id, namespace_id, tag_id, HC.PENDING ) )
            
            num_deleted = self._GetRowCount( c )
            
            UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, hash_ids, HC.PENDING, -1 )
            
            UpdateCombinedMappings( namespace_id, tag_id, hash_ids, 'delete', HC.PENDING )
            
            return num_deleted
            
        
        def DeletePetitions( namespace_id, tag_id, hash_ids ):
            
            c.execute( 'DELETE FROM mapping_petitions WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( tag_service_id, namespace_id, tag_id ) )
            
            num_deleted = self._GetRowCount( c )
            
            return num_deleted
            
        
        def InsertMappings( namespace_id, tag_id, hash_ids, status ):
            
            if status in ( HC.CURRENT, HC.DELETED ): existing_hash_ids = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ';', ( tag_service_id, namespace_id, tag_id ) ) ]
            elif status == HC.PENDING: existing_hash_ids = [ id for ( id, ) in c.execute( 'SELECT hash_id FROM mappings WHERE service_id = ? AND namespace_id = ? AND tag_id = ? AND hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' AND status != ?;', ( tag_service_id, namespace_id, tag_id, HC.DELETED ) ) ]
            
            new_hash_ids = set( hash_ids ).difference( existing_hash_ids )
            
            c.executemany( 'INSERT OR IGNORE INTO mappings VALUES ( ?, ?, ?, ?, ? );', [ ( tag_service_id, namespace_id, tag_id, hash_id, status ) for hash_id in new_hash_ids ] )
            
            num_rows_added = self._GetRowCount( c )
            
            if status == HC.CURRENT:
                
                UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, new_hash_ids, HC.CURRENT, 1 )
                
                UpdateCombinedMappings( namespace_id, tag_id, new_hash_ids, 'insert', HC.CURRENT )
                
            elif status == HC.PENDING:
                
                UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, new_hash_ids, HC.PENDING, 1 )
                
                UpdateCombinedMappings( namespace_id, tag_id, new_hash_ids, 'insert', HC.PENDING )
                
            
            return num_rows_added
            
        
        def InsertPetitions( namespace_id, tag_id, hash_ids, reason_id ):
            
            c.executemany( 'INSERT OR IGNORE INTO mapping_petitions VALUES ( ?, ?, ?, ?, ? );', [ ( tag_service_id, namespace_id, tag_id, hash_id, reason_id ) for hash_id in hash_ids ] )
            
            num_rows_added = self._GetRowCount( c )
            
            return num_rows_added
            
        
        def UpdateAutocompleteTagCache( tag_service_id, namespace_id, tag_id, hash_ids, status, direction ):
            
            file_service_info = c.execute( 'SELECT service_id, COUNT( * ) FROM files_info WHERE hash_id IN ' + HC.SplayListForDB( hash_ids ) + ' GROUP BY service_id;' ).fetchall()
            
            file_service_info.append( ( self._combined_file_service_id, len( hash_ids ) ) )
            
            if status == HC.CURRENT: critical_phrase = 'current_count = current_count + ?'
            elif status == HC.PENDING: critical_phrase = 'pending_count = pending_count + ?'
            
            c.executemany( 'UPDATE autocomplete_tags_cache SET ' + critical_phrase + ' WHERE file_service_id = ? AND tag_service_id = ? AND namespace_id = ? AND tag_id = ?;', [ ( count * direction, file_service_id, tag_service_id, namespace_id, tag_id ) for ( file_service_id, count ) in file_service_info ] )
            
        
        change_in_num_mappings = 0
        change_in_num_deleted_mappings = 0
        change_in_num_pending_mappings = 0
        change_in_num_petitioned_mappings = 0
        change_in_num_namespaces = 0
        change_in_num_tags = 0
        change_in_num_files = 0
        
        all_adds = mappings_ids + pending_mappings_ids
        
        namespace_ids_being_added = { namespace_id for ( namespace_id, tag_id, hash_ids ) in all_adds }
        tag_ids_being_added = { tag_id for ( namespace_id, tag_id, hash_ids ) in all_adds }
        
        hash_ids_lists = [ hash_ids for ( namespace_id, tag_id, hash_ids ) in all_adds ]
        hash_ids_being_added = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        all_removes = deleted_mappings_ids + pending_rescinded_mappings_ids
        
        namespace_ids_being_removed = { namespace_id for ( namespace_id, tag_id, hash_ids ) in all_removes }
        tag_ids_being_removed = { tag_id for ( namespace_id, tag_id, hash_ids ) in all_removes }
        
        hash_ids_lists = [ hash_ids for ( namespace_id, tag_id, hash_ids ) in all_removes ]
        hash_ids_being_removed = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        namespace_ids_to_search_for = namespace_ids_being_added.union( namespace_ids_being_removed )
        tag_ids_to_search_for = tag_ids_being_added.union( tag_ids_being_removed )
        hash_ids_to_search_for = hash_ids_being_added.union( hash_ids_being_removed )
        
        pre_existing_namespace_ids = { namespace_id for namespace_id in namespace_ids_to_search_for if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT namespace_id FROM mappings WHERE namespace_id = ? AND service_id = ? AND status IN ( ?, ? ) );', ( namespace_id, tag_service_id, HC.CURRENT, HC.PENDING ) ).fetchone() is not None }
        pre_existing_tag_ids = { tag_id for tag_id in tag_ids_to_search_for if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT tag_id FROM mappings WHERE tag_id = ? AND service_id = ? AND status IN ( ?, ? ) );', ( tag_id, tag_service_id, HC.CURRENT, HC.PENDING ) ).fetchone() is not None }
        pre_existing_hash_ids = { hash_id for hash_id in hash_ids_to_search_for if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT hash_id FROM mappings WHERE hash_id = ? AND service_id = ? AND status IN ( ?, ? ) );', ( hash_id, tag_service_id, HC.CURRENT, HC.PENDING ) ).fetchone() is not None }
        
        num_namespaces_added = len( namespace_ids_being_added.difference( pre_existing_namespace_ids ) )
        num_tags_added = len( tag_ids_being_added.difference( pre_existing_tag_ids ) )
        num_files_added = len( hash_ids_being_added.difference( pre_existing_hash_ids ) )
        
        change_in_num_namespaces += num_namespaces_added
        change_in_num_tags += num_tags_added
        change_in_num_files += num_files_added
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            ( num_deleted_deleted, num_deleted_made_current ) = ChangeMappingStatus( namespace_id, tag_id, hash_ids, HC.DELETED, HC.CURRENT )
            ( num_pending_deleted, num_pending_made_current ) = ChangeMappingStatus( namespace_id, tag_id, hash_ids, HC.PENDING, HC.CURRENT )
            num_raw_adds = InsertMappings( namespace_id, tag_id, hash_ids, HC.CURRENT )
            
            change_in_num_mappings += num_deleted_made_current + num_pending_made_current + num_raw_adds
            change_in_num_deleted_mappings -= num_deleted_deleted
            change_in_num_pending_mappings -= num_pending_deleted
            
        
        for ( namespace_id, tag_id, hash_ids ) in deleted_mappings_ids:
            
            ( num_current_deleted, num_current_made_deleted ) = ChangeMappingStatus( namespace_id, tag_id, hash_ids, HC.CURRENT, HC.DELETED )
            num_raw_adds = InsertMappings( namespace_id, tag_id, hash_ids, HC.DELETED )
            num_deleted_petitions = DeletePetitions( namespace_id, tag_id, hash_ids )
            
            change_in_num_mappings -= num_current_deleted
            change_in_num_deleted_mappings += num_current_made_deleted + num_raw_adds
            change_in_num_petitioned_mappings -= num_deleted_petitions
            
        
        for ( namespace_id, tag_id, hash_ids ) in pending_mappings_ids:
            
            num_raw_adds = InsertMappings( namespace_id, tag_id, hash_ids, HC.PENDING )
            num_deleted_petitions = DeletePetitions( namespace_id, tag_id, hash_ids )
            
            change_in_num_pending_mappings += num_raw_adds
            change_in_num_petitioned_mappings -= num_deleted_petitions
            
        
        for ( namespace_id, tag_id, hash_ids ) in pending_rescinded_mappings_ids:
            
            num_pending_rescinded = DeletePending( namespace_id, tag_id, hash_ids )
            
            change_in_num_pending_mappings -= num_pending_rescinded
            
        
        post_existing_namespace_ids = { namespace_id for namespace_id in namespace_ids_to_search_for if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT namespace_id FROM mappings WHERE namespace_id = ? AND service_id = ? AND status IN ( ?, ? ) );', ( namespace_id, tag_service_id, HC.CURRENT, HC.PENDING ) ).fetchone() is not None }
        post_existing_tag_ids = { tag_id for tag_id in tag_ids_to_search_for if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT tag_id FROM mappings WHERE tag_id = ? AND service_id = ? AND status IN ( ?, ? ) );', ( tag_id, tag_service_id, HC.CURRENT, HC.PENDING ) ).fetchone() is not None }
        post_existing_hash_ids = { hash_id for hash_id in hash_ids_to_search_for if c.execute( 'SELECT 1 WHERE EXISTS ( SELECT hash_id FROM mappings WHERE hash_id = ? AND service_id = ? AND status IN ( ?, ? ) );', ( hash_id, tag_service_id, HC.CURRENT, HC.PENDING ) ).fetchone() is not None }
        
        num_namespaces_removed = len( pre_existing_namespace_ids.intersection( namespace_ids_being_removed ).difference( post_existing_namespace_ids ) )
        num_tags_removed = len( pre_existing_tag_ids.intersection( tag_ids_being_removed ).difference( post_existing_tag_ids ) )
        num_files_removed = len( pre_existing_hash_ids.intersection( hash_ids_being_removed ).difference( post_existing_hash_ids ) )
        
        change_in_num_namespaces -= num_namespaces_removed
        change_in_num_tags -= num_tags_removed
        change_in_num_files -= num_files_removed
        
        for ( namespace_id, tag_id, hash_ids, reason_id ) in petitioned_mappings_ids:
            
            num_petitions_added = InsertPetitions( namespace_id, tag_id, hash_ids, reason_id )
            
            change_in_num_petitioned_mappings += num_petitions_added
            
        
        for ( namespace_id, tag_id, hash_ids ) in petitioned_rescinded_mappings_ids:
            
            num_petitions_removed = DeletePetitions( namespace_id, tag_id, hash_ids )
            
            change_in_num_petitioned_mappings -= num_petitions_removed
            
        
        service_info_updates = []
        
        if change_in_num_mappings != 0: service_info_updates.append( ( change_in_num_mappings, tag_service_id, HC.SERVICE_INFO_NUM_MAPPINGS ) )
        if change_in_num_deleted_mappings != 0: service_info_updates.append( ( change_in_num_deleted_mappings, tag_service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
        if change_in_num_pending_mappings != 0: service_info_updates.append( ( change_in_num_pending_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ) )
        if change_in_num_petitioned_mappings != 0: service_info_updates.append( ( change_in_num_petitioned_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ) )
        if change_in_num_namespaces != 0: service_info_updates.append( ( change_in_num_namespaces, tag_service_id, HC.SERVICE_INFO_NUM_NAMESPACES ) )
        if change_in_num_tags != 0: service_info_updates.append( ( change_in_num_tags, tag_service_id, HC.SERVICE_INFO_NUM_TAGS ) )
        if change_in_num_files != 0: service_info_updates.append( ( change_in_num_files, tag_service_id, HC.SERVICE_INFO_NUM_FILES ) )
        
        if len( service_info_updates ) > 0: c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
    
    def _UpdateServerServices( self, c, admin_service_key, original_services_info, edit_log, service_keys_to_access_keys ):
        
        self.pub_after_commit( 'notify_new_services_data' )
        self.pub_after_commit( 'notify_new_services_gui' )
        
        admin_service_id = self._GetServiceId( c, admin_service_key )
        
        admin_service = self._GetService( c, admin_service_id )
        
        admin_info = admin_service.GetInfo()
        
        host = admin_info[ 'host' ]
        
        #
        
        server_service_keys_to_client_service_info = {}
        
        current_client_services_info = c.execute( 'SELECT service_key, service_type, info FROM services;' ).fetchall()
        
        for ( server_service_key, service_type, server_options ) in original_services_info:
            
            server_port = server_options[ 'port' ]
            
            for ( client_service_key, service_type, client_info ) in current_client_services_info:
                
                if 'host' in client_info and 'port' in client_info:
                    
                    if client_info[ 'host' ] == host and client_info[ 'port' ] == server_port:
                        
                        server_service_keys_to_client_service_info[ server_service_key ] = ( client_service_key, service_type, client_info )
                        
                    
                
            
        
        #
        
        recalc_combined_mappings = False
        
        for ( action, data ) in edit_log:
            
            if action == HC.ADD:
                
                ( service_key, service_type, server_options ) = data
                
                info = {}
                
                info[ 'host' ] = host
                info[ 'port' ] = server_options[ 'port' ]
                info[ 'access_key' ] = service_keys_to_access_keys[ service_key ]
                
                name = HC.service_string_lookup[ service_type ] + ' at ' + host + ':' + HC.u( info[ 'port' ] )
                
                self._AddService( c, service_key, service_type, name, info )
                
            elif action == HC.DELETE:
                
                server_service_key = data
                
                if server_service_key in server_service_keys_to_client_service_info:
                    
                    ( client_service_key, service_type, client_info ) = server_service_keys_to_client_service_info[ server_service_key ]
                    
                    service_id = self._GetServiceId( c, client_service_key )
                    
                    c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
                    
                    service_update = HC.ServiceUpdate( HC.SERVICE_UPDATE_RESET )
                    
                    service_keys_to_service_updates = { client_service_key : [ service_update ] }
                    
                    self.pub_service_updates_after_commit( service_keys_to_service_updates )
                    
                    service_key_hex = server_service_key.encode( 'hex' )
                    
                    all_update_filenames = dircache.listdir( HC.CLIENT_UPDATES_DIR )
                    
                    for filename in all_update_filenames:
                        
                        if filename.startswith( service_key_hex ):
                            
                            os.remove( HC.CLIENT_UPDATES_DIR + os.path.sep + filename )
                            
                        
                    
                    if service_type == HC.TAG_REPOSITORY: recalc_combined_mappings = True
                    
                
            elif action == HC.EDIT:
                
                ( server_service_key, service_type, server_options ) = data
                
                if server_service_key in server_service_keys_to_client_service_info:
                    
                    ( client_service_key, service_type, client_info ) = server_service_keys_to_client_service_info[ server_service_key ]
                    
                    service_id = self._GetServiceId( c, client_service_key )
                    
                    client_info[ 'port' ] = server_options[ 'port' ]
                    
                    c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( client_info, service_id ) )
                    
                
            
        
        if recalc_combined_mappings: self._RecalcCombinedMappings( c )
        
        self.pub_after_commit( 'notify_new_pending' )
        
    
    def _UpdateServices( self, c, edit_log ):
        
        self.pub_after_commit( 'notify_new_services_data' )
        self.pub_after_commit( 'notify_new_services_gui' )
        
        HC.repos_changed = True
        
        recalc_combined_mappings = False
        message = None
        
        for entry in edit_log:
            
            action = entry.GetAction()
            
            if action == HC.ADD:
                
                ( service_key, service_type, name, info ) = entry.GetData()
                
                self._AddService( c, service_key, service_type, name, info )
                
            elif action == HC.DELETE:
                
                service_key = entry.GetIdentifier()
                
                service_id = self._GetServiceId( c, service_key )
                
                service = self._GetService( c, service_id )
                
                if service.GetServiceType() == HC.TAG_REPOSITORY:
                    
                    recalc_combined_mappings = True
                    
                    if message is None:
                        
                        message = HC.Message( HC.MESSAGE_TYPE_TEXT, { 'text' : 'updating services: deleting tag data' } )
                        
                        HC.pubsub.pub( 'message', message )
                        
                    
                
                c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
                
                service_update = HC.ServiceUpdate( HC.SERVICE_UPDATE_RESET )
                
                service_keys_to_service_updates = { service_key : [ service_update ] }
                
                self.pub_service_updates_after_commit( service_keys_to_service_updates )
                
                service_key_hex = service_key.encode( 'hex' )
                
                all_update_filenames = dircache.listdir( HC.CLIENT_UPDATES_DIR )
                
                for filename in all_update_filenames:
                    
                    if filename.startswith( service_key_hex ):
                        
                        os.remove( HC.CLIENT_UPDATES_DIR + os.path.sep + filename )
                        
                    
                
                if service.GetServiceType() == HC.TAG_REPOSITORY: recalc_combined_mappings = True
                
            elif action == HC.EDIT:
                
                ( service_key, service_type, new_name, info_update ) = entry.GetData()
                
                service_id = self._GetServiceId( c, service_key )
                
                c.execute( 'UPDATE services SET name = ? WHERE service_id = ?;', ( new_name, service_id ) )
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    account = HC.GetUnknownAccount()
                    
                    account.MakeStale()
                    
                    info_update[ 'account' ] = account
                    
                    self.pub_after_commit( 'permissions_are_stale' )
                    
                
                if service_type in HC.TAG_SERVICES:
                    
                    ( old_info, ) = c.execute( 'SELECT info FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                    old_tag_archive_sync = old_info[ 'tag_archive_sync' ]
                    new_tag_archive_sync = info_update[ 'tag_archive_sync' ]
                    
                    for archive_name in new_tag_archive_sync:
                        
                        namespaces = set( new_tag_archive_sync[ archive_name ] )
                        
                        if archive_name in old_tag_archive_sync:
                            
                            old_namespaces = old_tag_archive_sync[ archive_name ]
                            
                            namespaces.difference_update( old_namespaces )
                            
                            if len( namespaces ) == 0: continue
                            
                        
                        self._InitialiseTagArchiveSync( c, archive_name, namespaces, service_key )
                        
                    
                
                self._UpdateServiceInfo( c, service_id, info_update )
                
                if service_type == HC.LOCAL_BOORU:
                    
                    self.pub_after_commit( 'restart_booru' )
                    self.pub_after_commit( 'notify_new_upnp_mappings' )
                    
                
            
        
        if recalc_combined_mappings:
            
            message.SetInfo( 'text', 'updating services: recalculating combined tag data' )
            
            self._RecalcCombinedMappings( c )
            
            message.SetInfo( 'text', 'updating services: done!' )
            
        
        self.pub_after_commit( 'notify_new_pending' )
        
    
    def _UpdateServiceInfo( self, c, service_id, update ):
        
        ( info, ) = c.execute( 'SELECT info FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        for ( k, v ) in update.items(): info[ k ] = v
        
        c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
        
    
class DB( ServiceDB ):
    
    def __init__( self ):
        
        self._local_shutdown = False
        self._loop_finished = False
        
        self._db_path = HC.DB_DIR + os.path.sep + 'client.db'
        
        self._jobs = Queue.PriorityQueue()
        self._pubsubs = []
        
        self._subscriptions_cache = {}
        
        self._currently_doing_job = False
        
        self._InitDB()
        
        # clean up if last connection closed badly
        ( db, c ) = self._GetDBCursor()
        
        db.close()
        # ok should be fine
        
        ( db, c ) = self._GetDBCursor()
        
        ( version, ) = c.execute( 'SELECT version FROM version;' ).fetchone()
        
        if version < HC.SOFTWARE_VERSION - 50: raise Exception( 'Your current version of hydrus ' + HC.u( version ) + ' is too old for this version ' + HC.u( HC.SOFTWARE_VERSION ) + ' to update. Please try updating with version ' + HC.u( version + 45 ) + ' or earlier first.' )
        
        while version < HC.SOFTWARE_VERSION:
            
            HC.pubsub.pub( 'set_splash_text', 'updating db to v' + HC.u( version + 1 ) )
            
            time.sleep( 2 )
            
            try: c.execute( 'BEGIN IMMEDIATE' )
            except Exception as e: raise HydrusExceptions.DBAccessException( HC.u( e ) )
            
            try:
                
                self._UpdateDB( c, version )
                
                c.execute( 'COMMIT' )
                
            except:
                
                c.execute( 'ROLLBACK' )
                
                raise Exception( 'Updating the client db to version ' + HC.u( version ) + ' caused this error:' + os.linesep + traceback.format_exc() )
                
            
            ( version, ) = c.execute( 'SELECT version FROM version;' ).fetchone()
            
        
        try: c.execute( 'BEGIN IMMEDIATE' )
        except Exception as e: raise HydrusExceptions.DBAccessException( HC.u( e ) )
        
        try:
            
            # ####### put a temp db update here! ######
            
            # ###### ~~~~~~~~~~~~~~~~~~~~~~~~~~~ ######
            
            c.execute( 'COMMIT' )
            
        except:
            
            HC.ShowText( 'Database commit error:' + os.linesep + traceback.format_exc() )
            
            c.execute( 'ROLLBACK' )
            
            raise
            
        
        self._local_file_service_id = self._GetServiceId( c, HC.LOCAL_FILE_SERVICE_KEY )
        self._local_tag_service_id = self._GetServiceId( c, HC.LOCAL_TAG_SERVICE_KEY )
        self._combined_file_service_id = self._GetServiceId( c, HC.COMBINED_FILE_SERVICE_KEY )
        self._combined_tag_service_id = self._GetServiceId( c, HC.COMBINED_TAG_SERVICE_KEY )
        
        options = self._GetOptions( c )
        
        HC.options = options
        
    
    def _GetDBCursor( self ):
        
        db = sqlite3.connect( self._db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        db.create_function( 'hydrus_hamming', 2, HydrusImageHandling.GetHammingDistance )
        
        c = db.cursor()
        
        c.execute( 'PRAGMA cache_size = 10000;' )
        c.execute( 'PRAGMA foreign_keys = ON;' )
        c.execute( 'PRAGMA recursive_triggers = ON;' )
        
        return ( db, c )
        
    
    def _GetOptions( self, c ):
        
        result = c.execute( 'SELECT options FROM options;' ).fetchone()
        
        if result is None:
            
            options = CC.CLIENT_DEFAULT_OPTIONS
            
            c.execute( 'INSERT INTO options ( options ) VALUES ( ? );', ( options, ) )
            
        else:
            
            ( options, ) = result
            
            for key in CC.CLIENT_DEFAULT_OPTIONS:
                
                if key not in options: options[ key ] = CC.CLIENT_DEFAULT_OPTIONS[ key ]
                
            
        
        return options
        
    
    def _GetRowCount( self, c ):
        
        row_count = c.rowcount
        
        if row_count == -1: return 0
        else: return row_count
        
    
    def _GetSiteId( self, c, name ):
        
        result = c.execute( 'SELECT site_id FROM imageboard_sites WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is None:
            
            c.execute( 'INSERT INTO imageboard_sites ( name ) VALUES ( ? );', ( name, ) )
            
            site_id = c.lastrowid
            
        else: ( site_id, ) = result
        
        return site_id
        
    
    def _InitArchives( self ):
        
        self._tag_archives = {}
        
        for filename in dircache.listdir( HC.CLIENT_ARCHIVES_DIR ):
            
            if filename.endswith( '.db' ):
                
                try:
                    
                    hta = HydrusTagArchive.HydrusTagArchive( HC.CLIENT_ARCHIVES_DIR + os.path.sep + filename )
                    
                    archive_name = filename[:-3]
                    
                    self._tag_archives[ archive_name ] = hta
                    
                except Exception as e:
                    
                    HC.ShowText( 'An archive failed to load on boot.' )
                    HC.ShowException( e )
                    
                
            
        
    
    def _InitDB( self ):
        
        if not os.path.exists( self._db_path ):
            
            HC.is_first_start = True
            
            if not os.path.exists( HC.CLIENT_ARCHIVES_DIR ): os.mkdir( HC.CLIENT_ARCHIVES_DIR )
            if not os.path.exists( HC.CLIENT_FILES_DIR ): os.mkdir( HC.CLIENT_FILES_DIR )
            if not os.path.exists( HC.CLIENT_THUMBNAILS_DIR ): os.mkdir( HC.CLIENT_THUMBNAILS_DIR )
            if not os.path.exists( HC.CLIENT_UPDATES_DIR ): os.mkdir( HC.CLIENT_UPDATES_DIR )
            
            hex_chars = '0123456789abcdef'
            
            for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                
                dir = HC.CLIENT_FILES_DIR + os.path.sep + one + two
                
                if not os.path.exists( dir ): os.mkdir( dir )
                
                dir = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + one + two
                
                if not os.path.exists( dir ): os.mkdir( dir )
                
            
            ( db, c ) = self._GetDBCursor()
            
            c.execute( 'PRAGMA auto_vacuum = 0;' ) # none
            c.execute( 'PRAGMA journal_mode=WAL;' )
            
            try: c.execute( 'BEGIN IMMEDIATE' )
            except Exception as e: raise HydrusExceptions.DBAccessException( HC.u( e ) )
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, service_type INTEGER, name TEXT, info TEXT_YAML );' )
            c.execute( 'CREATE UNIQUE INDEX services_service_key_index ON services ( service_key );' )
            
            #
            
            c.execute( 'CREATE TABLE autocomplete_tags_cache ( file_service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, tag_service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, current_count INTEGER, pending_count INTEGER, PRIMARY KEY ( file_service_id, tag_service_id, namespace_id, tag_id ) );' )
            c.execute( 'CREATE INDEX autocomplete_tags_cache_tag_service_id_namespace_id_tag_id_index ON autocomplete_tags_cache ( tag_service_id, namespace_id, tag_id );' )
            
            c.execute( 'CREATE TABLE contacts ( contact_id INTEGER PRIMARY KEY, contact_key BLOB_BYTES, public_key TEXT, name TEXT, host TEXT, port INTEGER );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_contact_key_index ON contacts ( contact_key );' )
            c.execute( 'CREATE UNIQUE INDEX contacts_name_index ON contacts ( name );' )
            
            c.execute( 'CREATE VIRTUAL TABLE conversation_subjects USING fts4( subject );' )
            
            c.execute( 'CREATE TABLE deleted_files ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            
            c.execute( 'CREATE TABLE existing_tags ( namespace_id INTEGER, tag_id INTEGER, PRIMARY KEY( namespace_id, tag_id ) );' )
            c.execute( 'CREATE INDEX existing_tags_tag_id_index ON existing_tags ( tag_id );' )
            
            c.execute( 'CREATE TABLE file_inbox ( hash_id INTEGER PRIMARY KEY );' )
            
            c.execute( 'CREATE TABLE files_info ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, size INTEGER, mime INTEGER, timestamp INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX files_info_hash_id ON files_info ( hash_id );' )
            
            c.execute( 'CREATE TABLE file_transfers ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX file_transfers_hash_id ON file_transfers ( hash_id );' )
            
            c.execute( 'CREATE TABLE file_petitions ( service_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY( service_id, hash_id, reason_id ), FOREIGN KEY( service_id, hash_id ) REFERENCES files_info ON DELETE CASCADE );' )
            c.execute( 'CREATE INDEX file_petitions_hash_id_index ON file_petitions ( hash_id );' )
            
            c.execute( 'CREATE TABLE hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES );' )
            c.execute( 'CREATE UNIQUE INDEX hashes_hash_index ON hashes ( hash );' )
            
            c.execute( 'CREATE TABLE hydrus_sessions ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, expiry INTEGER );' )
            
            c.execute( 'CREATE TABLE local_hashes ( hash_id INTEGER PRIMARY KEY, md5 BLOB_BYTES, sha1 BLOB_BYTES, sha512 BLOB_BYTES );' )
            c.execute( 'CREATE INDEX local_hashes_md5_index ON local_hashes ( md5 );' )
            c.execute( 'CREATE INDEX local_hashes_sha1_index ON local_hashes ( sha1 );' )
            c.execute( 'CREATE INDEX local_hashes_sha512_index ON local_hashes ( sha512 );' )
            
            c.execute( 'CREATE TABLE local_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, rating REAL, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX local_ratings_hash_id_index ON local_ratings ( hash_id );' )
            c.execute( 'CREATE INDEX local_ratings_rating_index ON local_ratings ( rating );' )
            
            c.execute( 'CREATE TABLE mappings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, status INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id, status ) );' )
            c.execute( 'CREATE INDEX mappings_hash_id_index ON mappings ( hash_id );' )
            c.execute( 'CREATE INDEX mappings_service_id_tag_id_index ON mappings ( service_id, tag_id );' )
            c.execute( 'CREATE INDEX mappings_service_id_hash_id_index ON mappings ( service_id, hash_id );' )
            c.execute( 'CREATE INDEX mappings_service_id_status_index ON mappings ( service_id, status );' )
            
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
            
            c.execute( 'CREATE TABLE perceptual_hashes ( hash_id INTEGER PRIMARY KEY, phash BLOB_BYTES );' )
            
            c.execute( 'CREATE TABLE ratings_filter ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, min REAL, max REAL, PRIMARY KEY( service_id, hash_id ) );' )
            
            c.execute( 'CREATE TABLE reasons ( reason_id INTEGER PRIMARY KEY, reason TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX reasons_reason_index ON reasons ( reason );' )
            
            c.execute( 'CREATE TABLE remote_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, count INTEGER, rating REAL, score REAL, PRIMARY KEY( service_id, hash_id ) );' )
            c.execute( 'CREATE INDEX remote_ratings_hash_id_index ON remote_ratings ( hash_id );' )
            c.execute( 'CREATE INDEX remote_ratings_rating_index ON remote_ratings ( rating );' )
            c.execute( 'CREATE INDEX remote_ratings_score_index ON remote_ratings ( score );' )
            
            c.execute( 'CREATE TABLE service_info ( service_id INTEGER REFERENCES services ON DELETE CASCADE, info_type INTEGER, info INTEGER, PRIMARY KEY ( service_id, info_type ) );' )
            
            c.execute( 'CREATE TABLE shutdown_timestamps ( shutdown_type INTEGER PRIMARY KEY, timestamp INTEGER );' )
            
            c.execute( 'CREATE TABLE statuses ( status_id INTEGER PRIMARY KEY, status TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX statuses_status_index ON statuses ( status );' )
            
            c.execute( 'CREATE TABLE tag_censorship ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, blacklist INTEGER_BOOLEAN, tags TEXT_YAML );' )
            
            c.execute( 'CREATE TABLE tag_parents ( service_id INTEGER REFERENCES services ON DELETE CASCADE, child_namespace_id INTEGER, child_tag_id INTEGER, parent_namespace_id INTEGER, parent_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status ) );' )
            c.execute( 'CREATE INDEX tag_parents_service_id_status_index ON tag_parents ( service_id, status );' )
            c.execute( 'CREATE INDEX tag_parents_status_index ON tag_parents ( status );' )
            
            c.execute( 'CREATE TABLE tag_parent_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, child_namespace_id INTEGER, child_tag_id INTEGER, parent_namespace_id INTEGER, parent_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status ) );' )
            
            c.execute( 'CREATE TABLE tag_siblings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, old_namespace_id INTEGER, old_tag_id INTEGER, new_namespace_id INTEGER, new_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, old_namespace_id, old_tag_id, status ) );' )
            c.execute( 'CREATE INDEX tag_siblings_service_id_status_index ON tag_siblings ( service_id, status );' )
            c.execute( 'CREATE INDEX tag_siblings_status_index ON tag_siblings ( status );' )
            
            c.execute( 'CREATE TABLE tag_sibling_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, old_namespace_id INTEGER, old_tag_id INTEGER, new_namespace_id INTEGER, new_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, old_namespace_id, old_tag_id, status ) );' )
            
            c.execute( 'CREATE TABLE tags ( tag_id INTEGER PRIMARY KEY, tag TEXT );' )
            c.execute( 'CREATE UNIQUE INDEX tags_tag_index ON tags ( tag );' )
            
            c.execute( 'CREATE VIRTUAL TABLE tags_fts4 USING fts4( tag );' )
            
            c.execute( 'CREATE TABLE urls ( url TEXT PRIMARY KEY, hash_id INTEGER );' )
            c.execute( 'CREATE INDEX urls_hash_id ON urls ( hash_id );' )
            
            c.execute( 'CREATE TABLE version ( version INTEGER );' )
            
            c.execute( 'CREATE TABLE web_sessions ( name TEXT PRIMARY KEY, cookies TEXT_YAML, expiry INTEGER );' )
            
            c.execute( 'CREATE TABLE yaml_dumps ( dump_type INTEGER, dump_name TEXT, dump TEXT_YAML, PRIMARY KEY ( dump_type, dump_name ) );' )
            
            # inserts
            
            init_service_info = []
            
            init_service_info.append( ( HC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE, HC.LOCAL_FILE_SERVICE_KEY ) )
            init_service_info.append( ( HC.LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, HC.LOCAL_TAG_SERVICE_KEY ) )
            init_service_info.append( ( HC.COMBINED_FILE_SERVICE_KEY, HC.COMBINED_FILE, HC.COMBINED_FILE_SERVICE_KEY ) )
            init_service_info.append( ( HC.COMBINED_TAG_SERVICE_KEY, HC.COMBINED_TAG, HC.COMBINED_TAG_SERVICE_KEY ) )
            init_service_info.append( ( HC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, HC.LOCAL_BOORU_SERVICE_KEY ) )
            
            for ( service_key, service_type, name ) in init_service_info:
                
                info = {}
                
                self._AddService( c, service_key, service_type, name, info )
                
            
            c.executemany( 'INSERT INTO yaml_dumps VALUES ( ?, ?, ? );', ( ( YAML_DUMP_ID_REMOTE_BOORU, name, booru ) for ( name, booru ) in CC.DEFAULT_BOORUS.items() ) )
            
            c.executemany( 'INSERT INTO yaml_dumps VALUES ( ?, ?, ? );', ( ( YAML_DUMP_ID_IMAGEBOARD, name, imageboards ) for ( name, imageboards ) in CC.DEFAULT_IMAGEBOARDS ) )
            
            c.execute( 'INSERT INTO namespaces ( namespace_id, namespace ) VALUES ( ?, ? );', ( 1, '' ) )
            
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
        
        ( new_width, new_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        c.execute( 'UPDATE options SET options = ?;', ( HC.options, ) )
        
        resize_thumbs = new_width != old_width or new_height != old_height
        
        if resize_thumbs:
            
            message = HC.Message( HC.MESSAGE_TYPE_TEXT, { 'text' : 'deleting old thumbnails: initialising' } )
            
            HC.pubsub.pub( 'message', message )
            
            thumbnail_paths = ( path for path in CC.IterateAllThumbnailPaths() if path.endswith( '_resized' ) )
            
            for ( i, path ) in enumerate( thumbnail_paths ):
                
                os.remove( path )
                
                if i % 100 == 0: message.SetInfo( 'text', 'deleting old thumbnails: done ' + HC.ConvertIntToPrettyString( i ) )
                
            
            self.pub_after_commit( 'thumbnail_resize' )
            
            message.SetInfo( 'text', 'deleting old thumbnails: done' )
            
        
        self.pub_after_commit( 'notify_new_options' )
        
    
    def _SetPassword( self, c, password ):
        
        if password is not None: password = hashlib.sha256( password ).digest()
        
        HC.options[ 'password' ] = password
        
        self._SaveOptions( c )
        
    
    def _UpdateImageboards( self, c, site_edit_log ):
        
        for ( site_action, site_data ) in site_edit_log:
            
            if site_action == HC.ADD:
                
                site_name = site_data
                
                self._GetSiteId( c, site_name )
                
            elif site_action == HC.DELETE:
                
                site_name = site_data
                
                site_id = self._GetSiteId( c, site_name )
                
                c.execute( 'DELETE FROM imageboard_sites WHERE site_id = ?;', ( site_id, ) )
                c.execute( 'DELETE FROM imageboards WHERE site_id = ?;', ( site_id, ) )
                
            elif site_action == HC.EDIT:
                
                ( site_name, edit_log ) = site_data
                
                site_id = self._GetSiteId( c, site_name )
                
                for ( action, data ) in edit_log:
                    
                    if action == HC.ADD:
                        
                        name = data
                        
                        imageboard = CC.Imageboard( name, '', 60, [], {} )
                        
                        c.execute( 'INSERT INTO imageboards ( site_id, name, imageboard ) VALUES ( ?, ?, ? );', ( site_id, name, imageboard ) )
                        
                    elif action == HC.DELETE:
                        
                        name = data
                        
                        c.execute( 'DELETE FROM imageboards WHERE site_id = ? AND name = ?;', ( site_id, name ) )
                        
                    elif action == HC.EDIT:
                        
                        imageboard = data
                        
                        name = imageboard.GetName()
                        
                        c.execute( 'UPDATE imageboards SET imageboard = ? WHERE site_id = ? AND name = ?;', ( imageboard, site_id, name ) )
                        
                    
                
            
        
    
    def _UpdateDB( self, c, version ):
        
        if version == 87:
            
            c.execute( 'CREATE TABLE namespace_blacklists ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, blacklist INTEGER_BOOLEAN, namespaces TEXT_YAML );' )
            
        
        if version == 90:
            
            ( HC.options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            shortcuts = HC.options[ 'shortcuts' ]
            
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'Z' ) ] = 'undo'
            shortcuts[ wx.ACCEL_CTRL ][ ord( 'Y' ) ] = 'redo'
            
            HC.options[ 'shortcuts' ] = shortcuts
            
            c.execute( 'UPDATE options SET options = ?;', ( HC.options, ) )
            
        
        if version == 91:
            
            ( HC.options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            HC.options[ 'num_autocomplete_chars' ] = 2
            
            c.execute( 'UPDATE options SET options = ?;', ( HC.options, ) )
            
        
        if version == 93:
            
            c.execute( 'CREATE TABLE gui_sessions ( name TEXT, info TEXT_YAML );' )
            
        
        if version == 94:
            
            # I changed a variable name in account, so old yaml dumps need to be refreshed
            
            unknown_account = HC.GetUnknownAccount()
            
            c.execute( 'UPDATE accounts SET account = ?;', ( unknown_account, ) )
            
            for ( name, info ) in c.execute( 'SELECT name, info FROM gui_sessions;' ).fetchall():
                
                for ( page_name, c_text, args, kwargs ) in info:
                    
                    if 'do_query' in kwargs: del kwargs[ 'do_query' ]
                    
                
                c.execute( 'UPDATE gui_sessions SET info = ? WHERE name = ?;', ( info, name ) )
                
            
        
        if version == 95:
            
            c.execute( 'COMMIT' )
            
            c.execute( 'PRAGMA foreign_keys = OFF;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
            service_basic_info = c.execute( 'SELECT service_id, service_key, type, name FROM services;' ).fetchall()
            service_address_info = c.execute( 'SELECT service_id, host, port, last_error FROM addresses;' ).fetchall()
            service_account_info = c.execute( 'SELECT service_id, access_key, account FROM accounts;' ).fetchall()
            service_repository_info = c.execute( 'SELECT service_id, first_begin, next_begin FROM repositories;' ).fetchall()
            service_ratings_like_info = c.execute( 'SELECT service_id, like, dislike FROM ratings_like;' ).fetchall()
            service_ratings_numerical_info = c.execute( 'SELECT service_id, lower, upper FROM ratings_numerical;' ).fetchall()
            
            service_address_info = { service_id : ( host, port, last_error ) for ( service_id, host, port, last_error ) in service_address_info }
            service_account_info = { service_id : ( access_key, account ) for ( service_id, access_key, account ) in service_account_info }
            service_repository_info = { service_id : ( first_begin, next_begin ) for ( service_id, first_begin, next_begin ) in service_repository_info }
            service_ratings_like_info = { service_id : ( like, dislike ) for ( service_id, like, dislike ) in service_ratings_like_info }
            service_ratings_numerical_info = { service_id : ( lower, upper ) for ( service_id, lower, upper ) in service_ratings_numerical_info }
            
            c.execute( 'DROP TABLE services;' )
            c.execute( 'DROP TABLE addresses;' )
            c.execute( 'DROP TABLE accounts;' )
            c.execute( 'DROP TABLE repositories;' )
            c.execute( 'DROP TABLE ratings_like;' )
            c.execute( 'DROP TABLE ratings_numerical;' )
            
            c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY, service_key BLOB_BYTES, service_type INTEGER, name TEXT, info TEXT_YAML );' )
            c.execute( 'CREATE UNIQUE INDEX services_service_key_index ON services ( service_key );' )
            
            services = []
            
            for ( service_id, service_key, service_type, name ) in service_basic_info:
                
                info = {}
                
                if service_id in service_address_info:
                    
                    ( host, port, last_error ) = service_address_info[ service_id ]
                    
                    info[ 'host' ] = host
                    info[ 'port' ] = port
                    info[ 'last_error' ] = last_error
                    
                
                if service_id in service_account_info:
                    
                    ( access_key, account ) = service_account_info[ service_id ]
                    
                    info[ 'access_key' ] = access_key
                    info[ 'account' ] = account
                    
                
                if service_id in service_repository_info:
                    
                    ( first_begin, next_begin ) = service_repository_info[ service_id ]
                    
                    info[ 'first_begin' ] = first_begin
                    info[ 'next_begin' ] = next_begin
                    
                
                if service_id in service_ratings_like_info:
                    
                    ( like, dislike ) = service_ratings_like_info[ service_id ]
                    
                    info[ 'like' ] = like
                    info[ 'dislike' ] = dislike
                    
                
                if service_id in service_ratings_numerical_info:
                    
                    ( lower, upper ) = service_ratings_numerical_info[ service_id ]
                    
                    info[ 'lower' ] = lower
                    info[ 'upper' ] = upper
                    
                
                c.execute( 'INSERT INTO services ( service_id, service_key, service_type, name, info ) VALUES ( ?, ?, ?, ?, ? );',  ( service_id, sqlite3.Binary( service_key ), service_type, name, info ) )
                
            
            c.execute( 'COMMIT' )
            
            c.execute( 'PRAGMA foreign_keys = ON;' )
            
            c.execute( 'BEGIN IMMEDIATE' )
            
        
        if version == 95:
            
            for ( service_id, info ) in c.execute( 'SELECT service_id, info FROM services;' ).fetchall():
                
                if 'account' in info:
                    
                    info[ 'account' ].MakeStale()
                    
                    c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
                    
                
            
        
        if version == 101:
            
            c.execute( 'CREATE TABLE yaml_dumps ( dump_type INTEGER, dump_name TEXT, dump TEXT_YAML, PRIMARY KEY ( dump_type, dump_name ) );' )
            
            inserts = []
            
            # singles
            
            data = c.execute( 'SELECT token, pin, timeout FROM fourchan_pass;' ).fetchone()
            
            if data is not None: inserts.append( ( YAML_DUMP_ID_SINGLE, '4chan_pass', data ) )
            
            data = c.execute( 'SELECT pixiv_id, password FROM pixiv_account;' ).fetchone()
            
            if data is not None: inserts.append( ( YAML_DUMP_ID_SINGLE, 'pixiv_account', data ) )
            
            # boorus
            
            data = c.execute( 'SELECT name, booru FROM boorus;' ).fetchall()
            
            inserts.extend( ( ( YAML_DUMP_ID_REMOTE_BOORU, name, booru ) for ( name, booru ) in data ) )
            
            # favourite custom filter actions
            
            data = c.execute( 'SELECT name, actions FROM favourite_custom_filter_actions;' )
            
            inserts.extend( ( ( YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS, name, actions ) for ( name, actions ) in data ) )
            
            # gui sessions
            
            data = c.execute( 'SELECT name, info FROM gui_sessions;' ).fetchall()
            
            inserts.extend( ( ( YAML_DUMP_ID_GUI_SESSION, name, info ) for ( name, info ) in data ) )
            
            # imageboards
            
            all_imageboards = []
            
            all_sites = c.execute( 'SELECT site_id, name FROM imageboard_sites;' ).fetchall()
            
            for ( site_id, name ) in all_sites:
                
                imageboards = [ imageboard for ( imageboard, ) in c.execute( 'SELECT imageboard FROM imageboards WHERE site_id = ? ORDER BY name;', ( site_id, ) ) ]
                
                inserts.append( ( YAML_DUMP_ID_IMAGEBOARD, name, imageboards ) )
                
            
            # import folders
            
            data = c.execute( 'SELECT path, details FROM import_folders;' )
            
            inserts.extend( ( ( YAML_DUMP_ID_IMPORT_FOLDER, path, details ) for ( path, details ) in data ) )
            
            # subs
            
            subs = c.execute( 'SELECT site_download_type, name, info FROM subscriptions;' )            
            
            names = set()
            
            for ( site_download_type, name, old_info ) in subs:
                
                if name in names: name = name + str( site_download_type )
                
                ( query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused ) = old_info
                
                info = {}
                
                info[ 'site_type' ] = site_download_type
                info[ 'query_type' ] = query_type
                info[ 'query' ] = query
                info[ 'frequency_type' ] = frequency_type
                info[ 'frequency' ] = frequency_number
                info[ 'advanced_tag_options' ] = advanced_tag_options
                info[ 'advanced_import_options' ] = advanced_import_options
                info[ 'last_checked' ] = last_checked
                info[ 'url_cache' ] = url_cache
                info[ 'paused' ] = paused
                
                inserts.append( ( YAML_DUMP_ID_SUBSCRIPTION, name, info ) )
                
                names.add( name )
                
            
            #
            
            c.executemany( 'INSERT INTO yaml_dumps VALUES ( ?, ?, ? );', inserts )
            
            #
            
            c.execute( 'DROP TABLE fourchan_pass;' )
            c.execute( 'DROP TABLE pixiv_account;' )
            c.execute( 'DROP TABLE boorus;' )
            c.execute( 'DROP TABLE favourite_custom_filter_actions;' )
            c.execute( 'DROP TABLE gui_sessions;' )
            c.execute( 'DROP TABLE imageboard_sites;' )
            c.execute( 'DROP TABLE imageboards;' )
            c.execute( 'DROP TABLE subscriptions;' )
            
        
        if version == 105:
            
            if not os.path.exists( HC.CLIENT_UPDATES_DIR ): os.mkdir( HC.CLIENT_UPDATES_DIR )
            
            result = c.execute( 'SELECT service_id, info FROM services WHERE service_type IN ' + HC.SplayListForDB( HC.REPOSITORIES ) + ';' ).fetchall()
            
            for ( service_id, info ) in result:
                
                first_begin = info[ 'first_begin' ]
                if first_begin == 0: first_begin = None
                
                next_begin = info[ 'next_begin' ]
                
                info[ 'first_timestamp' ] = first_begin
                info[ 'next_download_timestamp' ] = 0
                info[ 'next_processing_timestamp' ] = next_begin
                
                del info[ 'first_begin' ]
                del info[ 'next_begin' ]
                
                c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
                
            
        
        if version == 106:
            
            c.execute( 'CREATE TABLE tag_censorship ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, blacklist INTEGER_BOOLEAN, tags TEXT_YAML );' )
            
            result = c.execute( 'SELECT service_id, blacklist, namespaces FROM namespace_blacklists;' ).fetchall()
            
            for ( service_id, blacklist, namespaces ) in result:
                
                tags = [ namespace + ':' for namespace in namespaces ]
                
                if ':' in tags: # don't want to change ''!
                    
                    tags.remove( ':' )
                    tags.append( '' )
                    
                
                c.execute( 'INSERT INTO tag_censorship ( service_id, blacklist, tags ) VALUES ( ?, ?, ? );', ( service_id, blacklist, tags ) )
                
            
            c.execute( 'DROP TABLE namespace_blacklists;' )
            
        
        if version == 108:
            
            c.execute( 'CREATE TABLE processed_mappings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, namespace_id INTEGER, tag_id INTEGER, hash_id INTEGER, status INTEGER, PRIMARY KEY( service_id, namespace_id, tag_id, hash_id, status ) );' )
            c.execute( 'CREATE INDEX processed_mappings_hash_id_index ON processed_mappings ( hash_id );' )
            c.execute( 'CREATE INDEX processed_mappings_service_id_tag_id_index ON processed_mappings ( service_id, tag_id );' )
            c.execute( 'CREATE INDEX processed_mappings_service_id_hash_id_index ON processed_mappings ( service_id, hash_id );' )
            c.execute( 'CREATE INDEX processed_mappings_service_id_status_index ON processed_mappings ( service_id, status );' )
            c.execute( 'CREATE INDEX processed_mappings_status_index ON processed_mappings ( status );' )
            
            service_ids = [ service_id for ( service_id, ) in c.execute( 'SELECT service_id FROM services;' ) ]
            
            for ( i, service_id ) in enumerate( service_ids ):
                
                HC.pubsub.pub( 'set_splash_text', 'copying mappings ' + str( i ) + '/' + str( len( service_ids ) ) )
                
                c.execute( 'INSERT INTO processed_mappings SELECT * FROM mappings WHERE service_id = ?;', ( service_id, ) )
                
            
            current_updates = dircache.listdir( HC.CLIENT_UPDATES_DIR )
            
            for filename in current_updates:
                
                path = HC.CLIENT_UPDATES_DIR + os.path.sep + filename
                
                os.rename( path, path + 'old' )
                
            
            current_updates = dircache.listdir( HC.CLIENT_UPDATES_DIR )
            
            for ( i, filename ) in enumerate( current_updates ):
                
                if i % 100 == 0: HC.pubsub.pub( 'set_splash_text', 'renaming updates ' + str( i ) + '/' + str( len( current_updates ) ) )
                
                ( service_key_hex, gumpf ) = filename.split( '_' )
                
                service_key = service_key_hex.decode( 'hex' )
                
                path = HC.CLIENT_UPDATES_DIR + os.path.sep + filename
                
                with open( path, 'rb' ) as f: update_text = f.read()
                
                update = yaml.safe_load( update_text )
                
                ( begin, end ) = update.GetBeginEnd()
                
                new_path = CC.GetUpdatePath( service_key, begin )
                
                if os.path.exists( new_path ): os.remove( path )
                else: os.rename( path, new_path )
                
            
        
        if version == 109:
            
            c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ?;', ( YAML_DUMP_ID_GUI_SESSION, ) )
            
            c.execute( 'DROP TABLE processed_mappings;' )
            
            c.execute( 'DROP INDEX mappings_status_index;' )
            
        
        if version == 110:
            
            all_services = c.execute( 'SELECT service_id, service_type, info FROM services;' ).fetchall()
            
            for ( service_id, service_type, info ) in all_services:
                
                if service_type in HC.REPOSITORIES:
                    
                    info[ 'paused' ] = False
                    
                    c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
                    
                
            
        
        if version == 114:
            
            service_key = HC.LOCAL_BOORU_SERVICE_KEY
            service_type = HC.LOCAL_BOORU
            name  = HC.LOCAL_BOORU_SERVICE_KEY
            info = {}
            
            self._AddService( c, service_key, service_type, name, info )
            
            c.execute( 'CREATE TABLE booru_shares ( service_id INTEGER REFERENCES services ( service_id ) ON DELETE CASCADE, share_key BLOB_BYTES, share TEXT_YAML, expiry INTEGER, used_monthly_data INTEGER, max_monthly_data INTEGER, ip_restriction TEXT, notes TEXT, PRIMARY KEY( service_id, share_key ) );' )
            
        
        if version == 115:
            
            for path in CC.IterateAllFilePaths():
                
                try:
                    
                    filename = os.path.basename( path )
                    
                    ( hash_encoded, ext ) = filename.split( '.', 1 )
                    
                    hash = hash_encoded.decode( 'hex' )
                    
                    if ext == 'webm':
                        
                        thumbnail = HydrusFileHandling.GenerateThumbnail( path )
                        
                        with open( CC.GetExpectedThumbnailPath( hash ), 'wb' ) as f: f.write( thumbnail )
                        
                    
                except: print( traceback.format_exc())
                
            
        
        if version == 116:
            
            c.execute( 'DELETE FROM service_info WHERE info_type = ?;', ( HC.SERVICE_INFO_NUM_THUMBNAILS, ) )
            
        
        if version == 117:
            
            i = 0
            
            for path in CC.IterateAllThumbnailPaths():
                
                if not path.endswith( '_resized' ):
                    
                    filename = os.path.basename( path )
                    
                    hash = filename.decode( 'hex' )
                    
                    try:
                        
                        phash = HydrusImageHandling.GeneratePerceptualHash( path )
                        
                        hash_id = self._GetHashId( c, hash )
                        
                        c.execute( 'INSERT OR REPLACE INTO perceptual_hashes ( hash_id, phash ) VALUES ( ?, ? );', ( hash_id, sqlite3.Binary( phash ) ) )
                        
                        i += 1
                        
                        if i % 100 == 0: HC.pubsub.pub( 'set_splash_text', 'reprocessing thumbs: ' + HC.ConvertIntToPrettyString( i ) )
                        
                    except: print( 'When updating to v118, ' + path + '\'s phash could not be recalculated.' )
                    
                
            
        
        if version == 119:
            
            i = 0
            
            for path in CC.IterateAllFilePaths():
                
                try:
                    
                    filename = os.path.basename( path )
                    
                    ( hash_encoded, ext ) = filename.split( '.' )
                    
                    hash = hash_encoded.decode( 'hex' )
                    
                    hash_id = self._GetHashId( c, hash )
                    
                    if ext not in ( 'flv', 'mp4', 'wmv', 'mkv', 'webm' ): continue
                    
                    ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( path )
                    
                    c.execute( 'UPDATE files_info SET duration = ?, num_frames = ? WHERE hash_id = ?;', ( duration, num_frames, hash_id ) )
                    
                    thumbnail = HydrusFileHandling.GenerateThumbnail( path )
                    
                    thumbnail_path = CC.GetExpectedThumbnailPath( hash )
                    
                    with open( thumbnail_path, 'wb' ) as f: f.write( thumbnail )
                    
                    phash = HydrusImageHandling.GeneratePerceptualHash( thumbnail_path )
                    
                    c.execute( 'INSERT OR REPLACE INTO perceptual_hashes ( hash_id, phash ) VALUES ( ?, ? );', ( hash_id, sqlite3.Binary( phash ) ) )
                    
                    i += 1
                    
                    if i % 100 == 0: HC.pubsub.pub( 'set_splash_text', 'creating video thumbs: ' + HC.ConvertIntToPrettyString( i ) )
                    
                except:
                    print( traceback.format_exc())
                    print( 'When updating to v119, ' + path + '\'s thumbnail or phash could not be calculated.' )
                
            
        
        if version == 121:
            
            c.execute( 'DROP TABLE booru_shares;' )
            
            service_id = self._GetServiceId( c, HC.LOCAL_BOORU_SERVICE_KEY )
            
            ( info, ) = c.execute( 'SELECT info FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            current_time_struct = time.gmtime()
            
            ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
            
            info[ 'used_monthly_requests' ] = 0
            info[ 'current_data_month' ] = ( current_year, current_month )
            
            c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
            
        
        if version == 125:
            
            ( HC.options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            HC.options[ 'default_tag_repository' ] = HC.options[ 'default_tag_repository' ].GetServiceKey()
            
            c.execute( 'UPDATE options SET options = ?;', ( HC.options, ) )
            
            #
            
            results = c.execute( 'SELECT * FROM yaml_dumps WHERE dump_type = ?;', ( YAML_DUMP_ID_SUBSCRIPTION, ) ).fetchall()
            
            for ( dump_type, dump_name, dump ) in results:
                
                advanced_tag_options = dump[ 'advanced_tag_options' ]
                
                new_advanced_tag_options = {}
                
                for ( service_identifier, namespaces ) in advanced_tag_options:
                    
                    new_advanced_tag_options[ service_identifier.GetServiceKey() ] = namespaces
                    
                
                dump[ 'advanced_tag_options' ] = new_advanced_tag_options
                
                c.execute( 'UPDATE yaml_dumps SET dump = ? WHERE dump_type = ? and dump_name = ?;', ( dump, dump_type, dump_name ) )
                
            
        
        if version == 126:
            
            c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ?;', ( YAML_DUMP_ID_GUI_SESSION, ) )
            
        
        if version == 130:
            
            c.execute( 'DROP TABLE tag_service_precedence;' )
            
            #
            
            self._combined_tag_service_id = self._GetServiceId( c, HC.COMBINED_TAG_SERVICE_KEY ) # needed for recalccombinedmappings
            
            service_ids = self._GetServiceIds( c, ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ) )
            
            for service_id in service_ids: c.execute( 'DELETE FROM service_info WHERE service_id = ?;', ( service_id, ) )
            
            self._RecalcCombinedMappings( c )
            
        
        if version == 131:
            
            service_info = c.execute( 'SELECT service_id, info FROM services;' ).fetchall()
            
            for ( service_id, info ) in service_info:
                
                if 'account' in info:
                    
                    info[ 'account' ] = HC.GetUnknownAccount()
                    
                    c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
                    
                
            
        
        if version == 132:
            
            c.execute( 'DELETE FROM service_info WHERE info_type = ?;', ( HC.SERVICE_INFO_NUM_FILES, ) )
            
            #
            
            ( HC.options, ) = c.execute( 'SELECT options FROM options;' ).fetchone()
            
            client_size = HC.options[ 'client_size' ]
            
            client_size[ 'fs_fullscreen' ] = True
            
            client_size[ 'gui_fullscreen' ] = False
            
            del HC.options[ 'fullscreen_borderless' ]
            
            c.execute( 'UPDATE options SET options = ?;', ( HC.options, ) )
            
        
        if version == 135:
            
            if not os.path.exists( HC.CLIENT_ARCHIVES_DIR ): os.mkdir( HC.CLIENT_ARCHIVES_DIR )
            
            #
            
            extra_hashes_data = c.execute( 'SELECT * FROM local_hashes;' ).fetchall()
            
            c.execute( 'DROP TABLE local_hashes;' )
            
            c.execute( 'CREATE TABLE local_hashes ( hash_id INTEGER PRIMARY KEY, md5 BLOB_BYTES, sha1 BLOB_BYTES, sha512 BLOB_BYTES );' )
            c.execute( 'CREATE INDEX local_hashes_md5_index ON local_hashes ( md5 );' )
            c.execute( 'CREATE INDEX local_hashes_sha1_index ON local_hashes ( sha1 );' )
            c.execute( 'CREATE INDEX local_hashes_sha512_index ON local_hashes ( sha512 );' )
            
            for ( i, ( hash_id, md5, sha1 ) ) in enumerate( extra_hashes_data ):
                
                hash = self._GetHash( c, hash_id )
                
                try: path = CC.GetFilePath( hash )
                except: continue
                
                h_sha512 = hashlib.sha512()
                
                with open( path, 'rb' ) as f:
                    
                    for block in HC.ReadFileLikeAsBlocks( f, 65536 ): h_sha512.update( block )
                    
                    sha512 = h_sha512.digest()
                    
                
                c.execute( 'INSERT INTO local_hashes ( hash_id, md5, sha1, sha512 ) VALUES ( ?, ?, ?, ? );', ( hash_id, sqlite3.Binary( md5 ), sqlite3.Binary( sha1 ), sqlite3.Binary( sha512 ) ) )
                
                if i % 100 == 0: HC.pubsub.pub( 'set_splash_text', 'generating sha512 hashes: ' + HC.ConvertIntToPrettyString( i ) )
                
            
            #
            
            tag_service_info = c.execute( 'SELECT service_id, info FROM services WHERE service_type IN ' + HC.SplayListForDB( HC.TAG_SERVICES ) + ';' ).fetchall()
            
            for ( service_id, info ) in tag_service_info:
                
                info[ 'tag_archive_sync' ] = {}
                
                c.execute( 'UPDATE services SET info = ? WHERE service_id = ?;', ( info, service_id ) )
                
            
        
        c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
        HC.is_db_updated = True
        
    
    def _Vacuum( self ):
        
        HC.pubsub.pub( 'set_splash_text', 'vacuuming db' )
        
        ( db, c ) = self._GetDBCursor()
        
        c.execute( 'VACUUM' )
        
        c.execute( 'ANALYZE' )
        
        c.execute( 'REPLACE INTO shutdown_timestamps ( shutdown_type, timestamp ) VALUES ( ?, ? );', ( CC.SHUTDOWN_TIMESTAMP_VACUUM, HC.GetNow() ) )
        
        HC.ShowText( 'Database maintenance: vacuumed successfully.' )
        
    
    def pub_after_commit( self, topic, *args, **kwargs ): self._pubsubs.append( ( topic, args, kwargs ) )
    
    def pub_content_updates_after_commit( self, service_keys_to_content_updates ):
        
        self.pub_after_commit( 'content_updates_data', service_keys_to_content_updates )
        self.pub_after_commit( 'content_updates_gui', service_keys_to_content_updates )
        
    
    def pub_service_updates_after_commit( self, service_keys_to_service_updates ):
        
        self.pub_after_commit( 'service_updates_data', service_keys_to_service_updates )
        self.pub_after_commit( 'service_updates_gui', service_keys_to_service_updates )
        
    
    def LoopIsFinished( self ): return self._loop_finished
    
    def MainLoop( self ):
        
        def ProcessJob( c, job ):
            
            def ProcessRead( action, args, kwargs ):
                
                if action == '4chan_pass': result = self._GetYAMLDump( c, YAML_DUMP_ID_SINGLE, '4chan_pass' )
                elif action == 'tag_archive_info': result = self._GetTagArchiveInfo( c, *args, **kwargs )
                elif action == 'tag_archive_tags': result = self._GetTagArchiveTags( c, *args, **kwargs )
                elif action == 'autocomplete_contacts': result = self._GetAutocompleteContacts( c, *args, **kwargs )
                elif action == 'autocomplete_tags': result = self._GetAutocompleteTags( c, *args, **kwargs )
                elif action == 'contact_names': result = self._GetContactNames( c, *args, **kwargs )
                elif action == 'do_message_query': result = self._DoMessageQuery( c, *args, **kwargs )
                elif action == 'downloads': result = self._GetDownloads( c, *args, **kwargs )
                elif action == 'export_folders': result = self._GetYAMLDump( c, YAML_DUMP_ID_EXPORT_FOLDER )
                elif action == 'favourite_custom_filter_actions': result = self._GetYAMLDump( c, YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS )
                elif action == 'file_query_ids': result = self._GetFileQueryIds( c, *args, **kwargs )
                elif action == 'file_system_predicates': result = self._GetFileSystemPredicates( c, *args, **kwargs )
                elif action == 'gui_sessions': result = self._GetYAMLDump( c, YAML_DUMP_ID_GUI_SESSION )
                elif action == 'hydrus_sessions': result = self._GetHydrusSessions( c, *args, **kwargs )
                elif action == 'identities_and_contacts': result = self._GetIdentitiesAndContacts( c, *args, **kwargs )
                elif action == 'identities': result = self._GetIdentities( c, *args, **kwargs )
                elif action == 'imageboards': result = self._GetYAMLDump( c, YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
                elif action == 'import_folders': result = self._GetYAMLDump( c, YAML_DUMP_ID_IMPORT_FOLDER, *args, **kwargs )
                elif action == 'local_booru_share_keys': result = self._GetYAMLDumpNames( c, YAML_DUMP_ID_LOCAL_BOORU )
                elif action == 'local_booru_share': result = self._GetYAMLDump( c, YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
                elif action == 'local_booru_shares': result = self._GetYAMLDump( c, YAML_DUMP_ID_LOCAL_BOORU )
                elif action == 'md5_status': result = self._GetMD5Status( c, *args, **kwargs )
                elif action == 'media_results': result = self._GetMediaResultsFromHashes( c, *args, **kwargs )
                elif action == 'media_results_from_ids': result = self._GetMediaResults( c, *args, **kwargs )
                elif action == 'message_keys_to_download': result = self._GetMessageKeysToDownload( c, *args, **kwargs )
                elif action == 'message_system_predicates': result = self._GetMessageSystemPredicates( c, *args, **kwargs )
                elif action == 'messages_to_send': result = self._GetMessagesToSend( c, *args, **kwargs )
                elif action == 'news': result = self._GetNews( c, *args, **kwargs )
                elif action == 'nums_pending': result = self._GetNumsPending( c, *args, **kwargs )
                elif action == 'pending': result = self._GetPending( c, *args, **kwargs )
                elif action == 'pixiv_account': result = self._GetYAMLDump( c, YAML_DUMP_ID_SINGLE, 'pixiv_account' )
                elif action == 'ratings_filter': result = self._GetRatingsFilter( c, *args, **kwargs )
                elif action == 'ratings_media_result': result = self._GetRatingsMediaResult( c, *args, **kwargs )
                elif action == 'remote_booru': result = self._GetYAMLDump( c, YAML_DUMP_ID_REMOTE_BOORU, *args, **kwargs )
                elif action == 'remote_boorus': result = self._GetYAMLDump( c, YAML_DUMP_ID_REMOTE_BOORU )
                elif action == 'service_info': result = self._GetServiceInfo( c, *args, **kwargs )
                elif action == 'services': result = self._GetServices( c, *args, **kwargs )
                elif action == 'shutdown_timestamps': result = self._GetShutdownTimestamps( c, *args, **kwargs )
                elif action == 'status_num_inbox': result = self._DoStatusNumInbox( c, *args, **kwargs )
                elif action == 'subscription_names': result = self._GetYAMLDumpNames( c, YAML_DUMP_ID_SUBSCRIPTION )
                elif action == 'subscription': result = self._GetYAMLDump( c, YAML_DUMP_ID_SUBSCRIPTION, *args, **kwargs )
                elif action == 'tag_censorship': result = self._GetTagCensorship( c, *args, **kwargs )
                elif action == 'tag_parents': result = self._GetTagParents( c, *args, **kwargs )
                elif action == 'tag_siblings': result = self._GetTagSiblings( c, *args, **kwargs )
                elif action == 'thumbnail_hashes_i_should_have': result = self._GetThumbnailHashesIShouldHave( c, *args, **kwargs )
                elif action == 'transport_message': result = self._GetTransportMessage( c, *args, **kwargs )
                elif action == 'transport_messages_from_draft': result = self._GetTransportMessagesFromDraft( c, *args, **kwargs )
                elif action == 'url_status': result = self._GetURLStatus( c, *args, **kwargs )
                elif action == 'web_sessions': result = self._GetWebSessions( c, *args, **kwargs )
                else: raise Exception( 'db received an unknown read command: ' + action )
                
                return result
                
            
            def ProcessWrite( action, args, kwargs ):
                
                if action == '4chan_pass': result = self._SetYAMLDump( c, YAML_DUMP_ID_SINGLE, '4chan_pass', *args, **kwargs )
                elif action == 'add_downloads': result = self._AddDownloads( c, *args, **kwargs )
                elif action == 'add_uploads': result = self._AddUploads( c, *args, **kwargs )
                elif action == 'archive_conversation': result = self._ArchiveConversation( c, *args, **kwargs )
                elif action == 'backup': result = self._Backup( c, *args, **kwargs )
                elif action == 'contact_associated': result = self._AssociateContact( c, *args, **kwargs )
                elif action == 'content_updates': result = self._ProcessContentUpdates( c, *args, **kwargs )
                elif action == 'copy_files': result = self._CopyFiles( c, *args, **kwargs )
                elif action == 'delete_conversation': result = self._DeleteConversation( c, *args, **kwargs )
                elif action == 'delete_draft': result = self._DeleteDraft( c, *args, **kwargs )
                elif action == 'delete_export_folder': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_EXPORT_FOLDER, *args, **kwargs )
                elif action == 'delete_favourite_custom_filter_actions': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS, *args, **kwargs )
                elif action == 'delete_gui_session': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_GUI_SESSION, *args, **kwargs )
                elif action == 'delete_hydrus_session_key': result = self._DeleteHydrusSessionKey( c, *args, **kwargs )
                elif action == 'delete_imageboard': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
                elif action == 'delete_import_folder': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_IMPORT_FOLDER, *args, **kwargs )
                elif action == 'delete_local_booru_share': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
                elif action == 'delete_orphans': result = self._DeleteOrphans( c, *args, **kwargs )
                elif action == 'delete_pending': result = self._DeletePending( c, *args, **kwargs )
                elif action == 'delete_remote_booru': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_REMOTE_BOORU, *args, **kwargs )
                elif action == 'delete_subscription': result = self._DeleteYAMLDump( c, YAML_DUMP_ID_SUBSCRIPTION, *args, **kwargs )
                elif action == 'draft_message': result = self._DraftMessage( c, *args, **kwargs )
                elif action == 'export_folder': result = self._SetYAMLDump( c, YAML_DUMP_ID_EXPORT_FOLDER, *args, **kwargs )
                elif action == 'fatten_autocomplete_cache': result = self._FattenAutocompleteCache( c, *args, **kwargs )
                elif action == 'favourite_custom_filter_actions': result = self._SetYAMLDump( c, YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS, *args, **kwargs )
                elif action == 'flush_message_statuses': result = self._FlushMessageStatuses( c, *args, **kwargs )
                elif action == 'generate_tag_ids': result = self._GenerateTagIdsEfficiently( c, *args, **kwargs )
                elif action == 'gui_session': result = self._SetYAMLDump( c, YAML_DUMP_ID_GUI_SESSION, *args, **kwargs )
                elif action == 'hydrus_session': result = self._AddHydrusSession( c, *args, **kwargs )
                elif action == 'imageboard': result = self._SetYAMLDump( c, YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
                elif action == 'import_file': result = self._ImportFile( c, *args, **kwargs )
                elif action == 'import_folder': result = self._SetYAMLDump( c, YAML_DUMP_ID_IMPORT_FOLDER, *args, **kwargs )
                elif action == 'inbox_conversation': result = self._InboxConversation( c, *args, **kwargs )
                elif action == 'local_booru_share': result = self._SetYAMLDump( c, YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
                elif action == 'message': result = self._AddMessage( c, *args, **kwargs )
                elif action == 'message_info_since': result = self._AddMessageInfoSince( c, *args, **kwargs )
                elif action == 'message_statuses': result = self._UpdateMessageStatuses( c, *args, **kwargs )
                elif action == 'pixiv_account': result = self._SetYAMLDump( c, YAML_DUMP_ID_SINGLE, 'pixiv_account', *args, **kwargs )
                elif action == 'remote_booru': result = self._SetYAMLDump( c, YAML_DUMP_ID_REMOTE_BOORU, *args, **kwargs )
                elif action == 'reset_service': result = self._ResetService( c, *args, **kwargs )
                elif action == 'save_options': result = self._SaveOptions( c, *args, **kwargs )
                elif action == 'service_updates': result = self._ProcessServiceUpdates( c, *args, **kwargs )
                elif action == 'set_password': result = self._SetPassword( c, *args, **kwargs )
                elif action == 'subscription': result = self._SetYAMLDump( c, YAML_DUMP_ID_SUBSCRIPTION, *args, **kwargs )
                elif action == 'tag_censorship': result = self._SetTagCensorship( c, *args, **kwargs )
                elif action == 'thumbnails': result = self._AddThumbnails( c, *args, **kwargs )
                elif action == 'update_contacts': result = self._UpdateContacts( c, *args, **kwargs )
                elif action == 'update_server_services': result = self._UpdateServerServices( c, *args, **kwargs )
                elif action == 'update_services': result = self._UpdateServices( c, *args, **kwargs )
                elif action == 'vacuum': result = self._Vacuum()
                elif action == 'web_session': result = self._AddWebSession( c, *args, **kwargs )
                else: raise Exception( 'db received an unknown write command: ' + action )
                
                return result
                
            
            HC.pubsub.pub( 'db_locked_status', 'db locked' )
            
            job_type = job.GetType()
            
            action = job.GetAction()
            
            args = job.GetArgs()
            
            kwargs = job.GetKWArgs()
            
            try:
                
                if job_type == 'read': c.execute( 'BEGIN DEFERRED' )
                elif job_type != 'write_special': c.execute( 'BEGIN IMMEDIATE' )
                
                if job_type in ( 'read', 'read_write' ): result = ProcessRead( action, args, kwargs )
                elif job_type in ( 'write', 'write_special' ): result = ProcessWrite( action, args, kwargs )
                
                if job_type != 'write_special': c.execute( 'COMMIT' )
                
                for ( topic, args, kwargs ) in self._pubsubs: HC.pubsub.pub( topic, *args, **kwargs )
                
                if job.IsSynchronous(): job.PutResult( result )
                
            except Exception as e:
                
                if job_type != 'write_special': c.execute( 'ROLLBACK' )
                
                if type( e ) == MemoryError: HC.ShowText( 'The client is running out of memory! Restart it ASAP!' )
                
                ( etype, value, tb ) = sys.exc_info()
                
                db_traceback = os.linesep.join( traceback.format_exception( etype, value, tb ) )
                
                new_e = HydrusExceptions.DBException( HC.u( e ), 'Unknown Caller, probably GUI.', db_traceback )
                
                if job.IsSynchronous(): job.PutResult( new_e )
                else: HC.ShowException( new_e )
                
            
            HC.pubsub.pub( 'db_locked_status', '' )
            
        
        self._InitArchives()
        
        ( db, c ) = self._GetDBCursor()
        
        while not ( ( self._local_shutdown or HC.shutdown ) and self._jobs.empty() ):
            
            try:
                
                ( priority, job ) = self._jobs.get( timeout = 1 )
                
                self._currently_doing_job = True
                
                self._pubsubs = []
                
                try: ProcessJob( c, job )
                except:
                    
                    self._jobs.put( ( priority, job ) ) # couldn't lock db; put job back on queue
                    
                    time.sleep( 5 )
                    
                
                self._currently_doing_job = False
                
            except: pass # no jobs this second; let's see if we should shutdown
            
        
        c.close()
        db.close()
        
        self._loop_finished = True
        
    
    def Read( self, action, priority, *args, **kwargs ):
        
        if action in ( 'service_info', 'system_predicates' ): job_type = 'read_write'
        else: job_type = 'read'
        
        synchronous = True
        
        job = HC.JobDatabase( action, job_type, synchronous, *args, **kwargs )
        
        if HC.shutdown: raise Exception( 'Application has shutdown!' )
        
        self._jobs.put( ( priority + 1, job ) ) # +1 so all writes of equal priority can clear out first
        
        if synchronous: return job.GetResult()
        
    
    def RestoreBackup( self, path ):
        
        deletee_filenames = dircache.listdir( HC.DB_DIR )
        
        for deletee_filename in deletee_filenames:
            
            def make_files_deletable( function_called, path, traceback_gumpf ):
                
                os.chmod( path, stat.S_IWRITE )
                
                function_called( path ) # try again
                
            
            if deletee_filename.startswith( 'client' ):
                
                deletee_path = HC.DB_DIR + os.path.sep + deletee_filename
                
                if os.path.isdir( deletee_path ): shutil.rmtree( deletee_path, onerror = make_files_deletable )
                else: os.remove( deletee_path )
                
            
        
        shutil.copy( path + os.path.sep + 'client.db', self._db_path )
        if os.path.exists( path + os.path.sep + 'client.db-wal' ): shutil.copy( path + os.path.sep + 'client.db-wal', self._db_path + '-wal' )
        
        shutil.copytree( path + os.path.sep + 'client_archives', HC.CLIENT_ARCHIVES_DIR )
        shutil.copytree( path + os.path.sep + 'client_files', HC.CLIENT_FILES_DIR )
        shutil.copytree( path + os.path.sep + 'client_thumbnails', HC.CLIENT_THUMBNAILS_DIR )
        shutil.copytree( path + os.path.sep + 'client_updates', HC.CLIENT_UPDATES_DIR )
        
    
    def Shutdown( self ): self._local_shutdown = True
    
    def StartDaemons( self ):
        
        HydrusThreading.DAEMONWorker( 'CheckImportFolders', DAEMONCheckImportFolders, ( 'notify_restart_import_folders_daemon', 'notify_new_import_folders' ), period = 180 )
        HydrusThreading.DAEMONWorker( 'CheckExportFolders', DAEMONCheckExportFolders, ( 'notify_restart_export_folders_daemon', 'notify_new_export_folders' ), period = 180 )
        HydrusThreading.DAEMONWorker( 'DownloadFiles', DAEMONDownloadFiles, ( 'notify_new_downloads', 'notify_new_permissions' ) )
        HydrusThreading.DAEMONWorker( 'DownloadThumbnails', DAEMONDownloadThumbnails, ( 'notify_new_permissions', 'notify_new_thumbnails' ) )
        HydrusThreading.DAEMONWorker( 'ResizeThumbnails', DAEMONResizeThumbnails, period = 3600 * 24, init_wait = 600 )
        HydrusThreading.DAEMONWorker( 'SynchroniseAccounts', DAEMONSynchroniseAccounts, ( 'permissions_are_stale', ) )
        HydrusThreading.DAEMONWorker( 'SynchroniseRepositories', DAEMONSynchroniseRepositories, ( 'notify_restart_repo_sync_daemon', 'notify_new_permissions' ) )
        HydrusThreading.DAEMONWorker( 'SynchroniseSubscriptions', DAEMONSynchroniseSubscriptions, ( 'notify_restart_subs_sync_daemon', 'notify_new_subscriptions' ), period = 360, init_wait = 120 )
        HydrusThreading.DAEMONWorker( 'UPnP', DAEMONUPnP, ( 'notify_new_upnp_mappings', ), pre_callable_wait = 10 )
        HydrusThreading.DAEMONQueue( 'FlushRepositoryUpdates', DAEMONFlushServiceUpdates, 'service_updates_delayed', period = 5 )
        
    
    def WaitUntilGoodTimeToUseDBThread( self ):
        
        while True:
            
            if HC.shutdown: raise Exception( 'Client shutting down!' )
            elif self._jobs.empty() and not self._currently_doing_job: return
            else: time.sleep( 0.0001 )
            
        
    
    def Write( self, action, priority, synchronous, *args, **kwargs ):
        
        if action == 'vacuum': job_type = 'write_special'
        else: job_type = 'write'
        
        job = HC.JobDatabase( action, job_type, synchronous, *args, **kwargs )
        
        if HC.shutdown: raise Exception( 'Application has shutdown!' )
        
        self._jobs.put( ( priority, job ) )
        
        if synchronous: return job.GetResult()
        
    
def DAEMONCheckExportFolders():
    
    if not HC.options[ 'pause_export_folders_sync' ]:
        
        export_folders = HC.app.ReadDaemon( 'export_folders' )
        
        for ( folder_path, details ) in export_folders.items():
            
            now = HC.GetNow()
            
            if now > details[ 'last_checked' ] + details[ 'period' ]:
                
                if os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                    
                    existing_filenames = dircache.listdir( folder_path )
                    
                    #
                    
                    predicates = details[ 'predicates' ]
                    
                    search_context = CC.FileSearchContext( HC.LOCAL_FILE_SERVICE_KEY, HC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True, predicates = predicates )
                    
                    query_hash_ids = HC.app.Read( 'file_query_ids', search_context )
                    
                    query_hash_ids = list( query_hash_ids )
                    
                    random.shuffle( query_hash_ids )
                    
                    limit = search_context.GetSystemPredicates().GetLimit()
                    
                    if limit is not None: query_hash_ids = query_hash_ids[ : limit ]
                    
                    media_results = []
                    
                    i = 0
                    
                    base = 256
                    
                    while i < len( query_hash_ids ):
                        
                        if HC.options[ 'pause_export_folders_sync' ]: return
                        
                        if i == 0: ( last_i, i ) = ( 0, base )
                        else: ( last_i, i ) = ( i, i + base )
                        
                        sub_query_hash_ids = query_hash_ids[ last_i : i ]
                        
                        more_media_results = HC.app.Read( 'media_results_from_ids', HC.LOCAL_FILE_SERVICE_KEY, sub_query_hash_ids )
                        
                        media_results.extend( more_media_results )
                        
                    
                    #
                    
                    phrase = details[ 'phrase' ]
                    
                    terms = CC.ParseExportPhrase( phrase )
                    
                    for media_result in media_results:
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        filename = CC.GenerateExportFilename( media_result, terms )
                        
                        ext = HC.mime_ext_lookup[ mime ]
                        
                        path = folder_path + os.path.sep + filename + ext
                        
                        if not os.path.exists( path ):
                            
                            source_path = CC.GetFilePath( hash, mime )
                            
                            shutil.copy( source_path, path )
                            
                        
                    
                    details[ 'last_checked' ] = now
                    
                    HC.app.WriteSynchronous( 'export_folder', folder_path, details )
                    
                
            
        
    
def DAEMONCheckImportFolders():
    
    if not HC.options[ 'pause_import_folders_sync' ]:
        
        import_folders = HC.app.ReadDaemon( 'import_folders' )
        
        for ( folder_path, details ) in import_folders.items():
            
            now = HC.GetNow()
            
            if now > details[ 'last_checked' ] + details[ 'check_period' ]:
                
                if os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                    
                    filenames = dircache.listdir( folder_path )
                    
                    raw_paths = [ folder_path + os.path.sep + filename for filename in filenames ]
                    
                    all_paths = CC.GetAllPaths( raw_paths )
                    
                    if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: 
                        
                        all_paths = [ path for path in all_paths if path not in details[ 'cached_imported_paths' ] ]
                        
                    
                    all_paths = [ path for path in all_paths if path not in details[ 'failed_imported_paths' ] ]
                    
                    successful_hashes = set()
                    
                    for ( i, path ) in enumerate( all_paths ):
                        
                        if HC.options[ 'pause_import_folders_sync' ]: return
                        
                        should_import = True
                        should_action = True
                        
                        temp_path = HC.GetTempPath()
                        
                        try:
                            
                            # make read only perms to make sure it isn't being written/downloaded right now
                            
                            os.chmod( path, stat.S_IREAD )
                            
                            os.chmod( path, stat.S_IWRITE )
                            
                            shutil.copy( path, temp_path )
                            
                            os.chmod( temp_path, stat.S_IWRITE )
                            
                        except:
                            
                            # could not lock, so try again later
                            
                            should_import = False
                            should_action = False
                            
                        
                        if should_import:
                            
                            try:
                                
                                if details[ 'local_tag' ] is not None: service_keys_to_tags = { HC.LOCAL_TAG_SERVICE_KEY : { details[ 'local_tag' ] } }
                                else: service_keys_to_tags = {}
                                
                                ( result, hash ) = HC.app.WriteSynchronous( 'import_file', temp_path, service_keys_to_tags = service_keys_to_tags )
                                
                                if result in ( 'successful', 'redundant' ): successful_hashes.add( hash )
                                elif result == 'deleted':
                                    
                                    details[ 'failed_imported_paths' ].add( path )
                                    
                                
                            except:
                                
                                details[ 'failed_imported_paths' ].add( path )
                                
                                HC.ShowText( 'Import folder failed to import ' + path + ':' + os.linesep * 2 + traceback.format_exc() )
                                
                                should_action = False
                                
                            
                            try: os.remove( temp_path )
                            except: pass # sometimes this fails, I think due to old handles not being cleaned up fast enough. np--it'll be cleaned up later
                            
                        
                        if should_action:
                            
                            if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_DELETE:
                                
                                try: os.remove( path )
                                except: details[ 'failed_imported_paths' ].add( path )
                                
                            elif details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: details[ 'cached_imported_paths' ].add( path )
                            
                        
                    
                    if len( successful_hashes ) > 0:
                        
                        text = HC.u( len( successful_hashes ) ) + ' files imported from ' + folder_path
                        
                        HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_FILES, { 'text' : text, 'hashes' : successful_hashes } ) )
                        
                    
                    details[ 'last_checked' ] = now
                    
                    HC.app.WriteSynchronous( 'import_folder', folder_path, details )
                    
                
            
        
    
def DAEMONDownloadFiles():
    
    hashes = HC.app.ReadDaemon( 'downloads' )
    
    num_downloads = len( hashes )
    
    for hash in hashes:
        
        ( media_result, ) = HC.app.ReadDaemon( 'media_results', HC.COMBINED_FILE_SERVICE_KEY, ( hash, ) )
        
        service_keys = list( media_result.GetLocationsManager().GetCurrent() )
        
        random.shuffle( service_keys )
        
        for service_key in service_keys:
            
            if service_key == HC.LOCAL_FILE_SERVICE_KEY: break
            
            try: file_repository = HC.app.GetManager( 'services' ).GetService( service_key )
            except: continue
            
            HC.pubsub.pub( 'downloads_status', HC.ConvertIntToPrettyString( num_downloads ) + ' file downloads' )
            
            if file_repository.CanDownload(): 
                
                try:
                    
                    request_args = { 'hash' : hash.encode( 'hex' ) }
                    
                    temp_path = file_repository.Request( HC.GET, 'file', request_args = request_args, response_to_path = True )
                    
                    num_downloads -= 1
                    
                    HC.app.WaitUntilGoodTimeToUseGUIThread()
                    
                    HC.pubsub.pub( 'downloads_status', HC.ConvertIntToPrettyString( num_downloads ) + ' file downloads' )
                    
                    HC.app.WriteSynchronous( 'import_file', temp_path )
                    
                    try: os.remove( temp_path )
                    except: pass # sometimes this fails, I think due to old handles not being cleaned up fast enough. np--it'll be cleaned up later
                    
                    break
                    
                except:
                    
                    HC.ShowText( 'Error downloading file:' + os.linesep + traceback.format_exc() )
                    
                
            
            if HC.shutdown: return
            
        
    
    if num_downloads == 0: HC.pubsub.pub( 'downloads_status', 'no file downloads' )
    elif num_downloads > 0: HC.pubsub.pub( 'downloads_status', HC.ConvertIntToPrettyString( num_downloads ) + ' inactive file downloads' )
    
def DAEMONDownloadThumbnails():
    
    services = HC.app.ReadDaemon( 'services', ( HC.FILE_REPOSITORY, ) )
    
    thumbnail_hashes_i_have = CC.GetAllThumbnailHashes()
    
    for service in services:
        
        service_key = service.GetServiceKey()
        
        thumbnail_hashes_i_should_have = HC.app.ReadDaemon( 'thumbnail_hashes_i_should_have', service_key )
        
        thumbnail_hashes_i_need = list( thumbnail_hashes_i_should_have - thumbnail_hashes_i_have )
        
        if len( thumbnail_hashes_i_need ) > 0:
            
            try: file_repository = HC.app.GetManager( 'services' ).GetService( service_key )
            except: continue
            
            if file_repository.CanDownload():
                
                try:
                    
                    num_per_round = 50
                    
                    for i in range( 0, len( thumbnail_hashes_i_need ), num_per_round ):
                        
                        if HC.shutdown: return
                        
                        thumbnails = []
                        
                        for hash in thumbnail_hashes_i_need[ i : i + num_per_round ]:
                            
                            request_args = { 'hash' : hash.encode( 'hex' ) }
                            
                            thumbnail = file_repository.Request( HC.GET, 'thumbnail', request_args = request_args )
                            
                            thumbnails.append( ( hash, thumbnail ) )
                            
                        
                        HC.app.WaitUntilGoodTimeToUseGUIThread()
                        
                        HC.app.WriteSynchronous( 'thumbnails', thumbnails )
                        
                        HC.pubsub.pub( 'add_thumbnail_count', service_key, len( thumbnails ) )
                        
                        thumbnail_hashes_i_have.update( { hash for ( hash, thumbnail ) in thumbnails } )
                        
                        time.sleep( 0.25 )
                        
                    
                except: pass # if bad download, the repo gets dinged an error. no need to do anything here
                
            
        
    
def DAEMONFlushServiceUpdates( list_of_service_keys_to_service_updates ):
    
    service_keys_to_service_updates = HC.MergeKeyToListDicts( list_of_service_keys_to_service_updates )
    
    HC.app.WriteSynchronous( 'service_updates', service_keys_to_service_updates )
    
def DAEMONResizeThumbnails():
    
    if not HC.app.CurrentlyIdle(): return
    
    full_size_thumbnail_paths = { path for path in CC.IterateAllThumbnailPaths() if not path.endswith( '_resized' ) }
    
    resized_thumbnail_paths = { path[:-8] for path in CC.IterateAllThumbnailPaths() if path.endswith( '_resized' ) }
    
    thumbnail_paths_to_render = list( full_size_thumbnail_paths.difference( resized_thumbnail_paths ) )
    
    random.shuffle( thumbnail_paths_to_render )
    
    i = 0
    
    limit = max( 100, len( thumbnail_paths_to_render ) / 10 )
    
    for thumbnail_path in thumbnail_paths_to_render:
        
        try:
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( thumbnail_path, HC.options[ 'thumbnail_dimensions' ] )
            
            thumbnail_resized_path = thumbnail_path + '_resized'
            
            with open( thumbnail_resized_path, 'wb' ) as f: f.write( thumbnail_resized )
            
        except IOError as e: HC.ShowText( 'Thumbnail read error:' + os.linesep + traceback.format_exc() )
        except Exception as e: HC.ShowText( 'Thumbnail rendering error:' + os.linesep + traceback.format_exc() )
        
        if i % 10 == 0: time.sleep( 2 )
        else:
            
            if limit > 10000: time.sleep( 0.05 )
            elif limit > 1000: time.sleep( 0.25 )
            else: time.sleep( 0.5 )
            
        
        i += 1
        
        if i > limit: break
        
        if HC.shutdown: break
        
    
def DAEMONSynchroniseAccounts():
    
    services = HC.app.GetManager( 'services' ).GetServices( HC.RESTRICTED_SERVICES )
    
    do_notify = False
    
    for service in services:
        
        service_key = service.GetServiceKey()
        service_type = service.GetServiceType()
        
        account = service.GetInfo( 'account' )
        credentials = service.GetCredentials()
        
        if service_type in HC.REPOSITORIES:
            
            if HC.options[ 'pause_repo_sync' ]: continue
            
            info = service.GetInfo()
            
            if info[ 'paused' ]: continue
            
        
        if account.IsStale() and credentials.HasAccessKey() and not service.HasRecentError():
            
            try:
                
                response = service.Request( HC.GET, 'account' )
                
                account = response[ 'account' ]
                
                account.MakeFresh()
                
                HC.app.WriteSynchronous( 'service_updates', { service_key : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, account ) ] } )
                
                do_notify = True
                
            except Exception as e:
                
                print( 'Failed to refresh account for ' + service.GetName() + ':' )
                
                print( traceback.format_exc() )
                
            
        
    
    if do_notify: HC.pubsub.pub( 'notify_new_permissions' )
    
def DAEMONSynchroniseMessages():
    
    services = HC.app.GetManager( 'services' ).GetServices( ( HC.MESSAGE_DEPOT, ) )
    
    for service in services:
        
        try:
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            name = service.GetName()
            
            if service.CanCheck():
                
                contact = service.GetContact()
                
                connection = service.GetConnection()
                
                private_key = service.GetPrivateKey()
                
                # is the account associated?
                
                if not contact.HasPublicKey():
                    
                    try:
                        
                        public_key = HydrusEncryption.GetPublicKey( private_key )
                        
                        connection.Post( 'contact', public_key = public_key )
                        
                        HC.app.WriteSynchronous( 'contact_associated', service_key )
                        
                        contact = service.GetContact()
                        
                        HC.ShowText( 'associated public key with account at ' + name )
                        
                    except:
                        
                        continue
                        
                    
                
                # see if there are any new message_keys to download or statuses
                
                last_check = service.GetLastCheck()
                
                ( message_keys, statuses ) = connection.Get( 'message_info_since', since = last_check )
                
                decrypted_statuses = []
                
                for status in statuses:
                    
                    try: decrypted_statuses.append( HydrusMessageHandling.UnpackageDeliveredStatus( status, private_key ) )
                    except: pass
                    
                
                new_last_check = HC.GetNow() - 5
                
                HC.app.WriteSynchronous( 'message_info_since', service_key, message_keys, decrypted_statuses, new_last_check )
                
                if len( message_keys ) > 0: HC.ShowText( 'Checked ' + name + ' up to ' + HC.ConvertTimestampToPrettyTime( new_last_check ) + ', finding ' + HC.u( len( message_keys ) ) + ' new messages' )
                
            
            # try to download any messages that still need downloading
            
            if service.CanDownload():
                
                serverside_message_keys = HC.app.ReadDaemon( 'message_keys_to_download', service_key )
                
                if len( serverside_message_keys ) > 0:
                    
                    connection = service.GetConnection()
                    
                    private_key = service.GetPrivateKey()
                    
                    num_processed = 0
                    
                    for serverside_message_key in serverside_message_keys:
                        
                        try:
                            
                            encrypted_message = connection.Get( 'message', message_key = serverside_message_key.encode( 'hex' ) )
                            
                            message = HydrusMessageHandling.UnpackageDeliveredMessage( encrypted_message, private_key )
                            
                            HC.app.WriteSynchronous( 'message', message, serverside_message_key = serverside_message_key )
                            
                            num_processed += 1
                            
                        except Exception as e:
                            
                            if issubclass( e, httplib.HTTPException ): break # it was an http error; try again later
                            
                        
                    
                    if num_processed > 0:
                        
                        HC.ShowText( 'Downloaded and parsed ' + HC.u( num_processed ) + ' messages from ' + name )
                        
                    
                
            
        except Exception as e:
            
            HC.ShowText( 'Failed to check ' + name + ':' )
            
            HC.ShowException( e )
            
        
    
    HC.app.WriteSynchronous( 'flush_message_statuses' )
    
    # send messages to recipients and update my status to sent/failed
    
    messages_to_send = HC.app.ReadDaemon( 'messages_to_send' )
    
    for ( message_key, contacts_to ) in messages_to_send:
        
        message = HC.app.ReadDaemon( 'transport_message', message_key )
        
        contact_from = message.GetContactFrom()
        
        from_anon = contact_from is None or contact_from.GetName() == 'Anonymous'
        
        if not from_anon:
            
            my_public_key = contact_from.GetPublicKey()
            my_contact_key = contact_from.GetContactKey()
            
            my_message_depot = HC.app.GetManager( 'services' ).GetService( contact_from.GetServiceKey() )
            
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
                
                HC.ShowText( 'Sending a message failed: ' + os.linesep + traceback.format_exc() )
                
                status = 'failed'
                
            
            status_key = hashlib.sha256( contact_key + message_key ).digest()
            
            if not from_anon: service_status_updates.append( ( status_key, HydrusMessageHandling.PackageStatusForDelivery( ( message_key, contact_key, status ), my_public_key ) ) )
            
            local_status_updates.append( ( contact_key, status ) )
            
        
        if not from_anon: from_connection.Post( 'message_statuses', contact_key = my_contact_key, statuses = service_status_updates )
        
        HC.app.WriteSynchronous( 'message_statuses', message_key, local_status_updates )
        
    
    HC.app.ReadDaemon( 'status_num_inbox' )
    
def DAEMONSynchroniseRepositories():
    
    HC.repos_changed = False
    
    if not HC.options[ 'pause_repo_sync' ]:
        
        services = HC.app.GetManager( 'services' ).GetServices( HC.REPOSITORIES )
        
        for service in services:
            
            if HC.shutdown: raise Exception( 'Application shutting down!' )
            
            try:
                
                ( service_key, service_type, name, info ) = service.ToTuple()
                
                if info[ 'paused' ]: continue
                
                if service.CanDownloadUpdate():
                    
                    job_key = HC.JobKey( pausable = True, cancellable = False )
                    
                    message = HC.MessageGauge( HC.MESSAGE_TYPE_GAUGE, 'checking ' + name + ' repository', job_key )
                    
                    HC.pubsub.pub( 'message', message )
                    
                    while service.CanDownloadUpdate():
                        
                        while job_key.IsPaused():
                            
                            message.SetInfo( 'text', 'paused' )
                            
                            time.sleep( 1 )
                            
                            if HC.shutdown: raise Exception( 'application shutting down!' )
                            
                            if message.IsClosed(): return
                            
                        
                        while HC.options[ 'pause_repo_sync' ]:
                            
                            message.SetInfo( 'text', 'repository synchronisation paused' )
                            
                            time.sleep( 5 )
                            
                            if HC.shutdown: raise Exception( 'application shutting down!' )
                            
                            if message.IsClosed(): return
                            
                            if HC.repos_changed:
                                
                                message.Close()
                                
                                HC.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        if HC.shutdown: raise Exception( 'application shutting down!' )
                        
                        now = HC.GetNow()
                        
                        ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = service.GetTimestamps()
                        
                        if first_timestamp is None:
                            
                            range = None
                            value = 0
                            
                            update_index_string = 'initial update'
                            
                        else:
                            
                            range = ( ( now - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                            value = ( ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                            
                            update_index_string = 'update ' + HC.u( value )
                            
                        
                        prefix_string = name + ' ' + update_index_string + ': '
                        
                        message.SetInfo( 'range', range )
                        message.SetInfo( 'value', value )
                        message.SetInfo( 'text', prefix_string + 'downloading' )
                        message.SetInfo( 'mode', 'gauge' )
                        
                        update = service.Request( HC.GET, 'update', { 'begin' : next_download_timestamp } )
                        
                        ( begin, end ) = update.GetBeginEnd()
                        
                        update_path = CC.GetUpdatePath( service_key, begin )
                        
                        with open( update_path, 'wb' ) as f: f.write( yaml.safe_dump( update ) )
                        
                        next_download_timestamp = end + 1
                        
                        service_updates = [ HC.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP, next_download_timestamp ) ]
                        
                        service_keys_to_service_updates = { service_key : service_updates }
                        
                        HC.app.WriteSynchronous( 'service_updates', service_keys_to_service_updates )
                        
                        time.sleep( 0.10 )
                        
                        # this waits for pubsubs to flush, so service updates are processed
                        HC.app.WaitUntilGoodTimeToUseGUIThread()
                        
                    
                    message.Close()
                    
                
                if service.CanProcessUpdate():
                    
                    job_key = HC.JobKey( pausable = True, cancellable = False )
                    
                    message = HC.MessageGauge( HC.MESSAGE_TYPE_GAUGE, 'processing ' + name + ' repository', job_key )
                    
                    HC.pubsub.pub( 'message', message )
                
                    WEIGHT_THRESHOLD = 50
                    
                    while service.CanProcessUpdate():
                        
                        while job_key.IsPaused():
                            
                            message.SetInfo( 'text', 'paused' )
                            
                            time.sleep( 1 )
                            
                            if HC.shutdown: raise Exception( 'application shutting down!' )
                            
                            if message.IsClosed(): return
                            
                        
                        while HC.options[ 'pause_repo_sync' ]:
                            
                            message.SetInfo( 'text', 'repository synchronisation paused' )
                            
                            time.sleep( 5 )
                            
                            if HC.shutdown: raise Exception( 'application shutting down!' )
                            
                            if message.IsClosed(): return
                            
                            if HC.repos_changed:
                                
                                message.Close()
                                
                                HC.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        if HC.shutdown: raise Exception( 'application shutting down!' )
                        
                        now = HC.GetNow()
                        
                        ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = service.GetTimestamps()
                        
                        range = ( ( now - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                        
                        if next_processing_timestamp == 0: value = 0
                        else: value = ( ( next_processing_timestamp - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                        
                        update_index_string = 'update ' + HC.u( value )
                        
                        prefix_string = name + ' ' + update_index_string + ': '
                        
                        message.SetInfo( 'range', range )
                        message.SetInfo( 'value', value )
                        message.SetInfo( 'text', prefix_string + 'processing' )
                        message.SetInfo( 'mode', 'gauge' )
                        
                        update_path = CC.GetUpdatePath( service_key, next_processing_timestamp )
                        
                        with open( update_path, 'rb' ) as f: update_yaml = f.read()
                        
                        update = yaml.safe_load( update_yaml )
                        
                        if service_type == HC.TAG_REPOSITORY:
                            
                            message.SetInfo( 'text', prefix_string + 'generating tags' )
                            
                            HC.app.WriteSynchronous( 'generate_tag_ids', update.GetTags() )
                            
                        
                        i = 0
                        num_content_updates = update.GetNumContentUpdates()
                        content_updates = []
                        current_weight = 0
                        
                        for content_update in update.IterateContentUpdates():
                            
                            content_updates.append( content_update )
                            
                            current_weight += len( content_update.GetHashes() )
                            
                            i += 1
                            
                            if current_weight > WEIGHT_THRESHOLD:
                                
                                while HC.options[ 'pause_repo_sync' ]:
                                    
                                    message.SetInfo( 'text', 'Repository synchronisation paused' )
                                    
                                    time.sleep( 5 )
                                    
                                    if HC.shutdown: raise Exception( 'Application shutting down!' )
                                    
                                    if HC.repos_changed:
                                        
                                        message.Close()
                                        
                                        HC.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                        
                                        return
                                        
                                    
                                
                                message.SetInfo( 'text', prefix_string + 'processing content ' + HC.ConvertIntToPrettyString( i ) + '/' + HC.ConvertIntToPrettyString( num_content_updates ) )
                                
                                HC.app.WaitUntilGoodTimeToUseGUIThread()
                                
                                time.sleep( 0.0001 )
                                
                                before_precise = HC.GetNowPrecise()
                                
                                HC.app.WriteSynchronous( 'content_updates', { service_key : content_updates } )
                                
                                after_precise = HC.GetNowPrecise()
                                
                                if after_precise - before_precise > 1.00: WEIGHT_THRESHOLD /= 1.1
                                elif after_precise - before_precise < 0.75: WEIGHT_THRESHOLD *= 1.1
                                
                                content_updates = []
                                current_weight = 0
                                
                            
                        
                        if len( content_updates ) > 0: HC.app.WriteSynchronous( 'content_updates', { service_key : content_updates } )
                        
                        message.SetInfo( 'text', prefix_string + 'processing service info' )
                        
                        service_updates = [ service_update for service_update in update.IterateServiceUpdates() ]
                        
                        ( begin, end ) = update.GetBeginEnd()
                        
                        next_processing_timestamp = end + 1
                        
                        service_updates.append( HC.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP, next_processing_timestamp ) )
                        
                        service_keys_to_service_updates = { service_key : service_updates }
                        
                        HC.app.WriteSynchronous( 'service_updates', service_keys_to_service_updates )
                        
                        HC.pubsub.pub( 'notify_new_pending' )
                        
                        time.sleep( 0.10 )
                        
                        # this waits for pubsubs to flush, so service updates are processed
                        HC.app.WaitUntilGoodTimeToUseGUIThread()
                        
                    
                    message.Close()
                    
                
            except Exception as e:
                
                print( traceback.format_exc() )
                
                if 'message' in locals(): message.Close()
                
                HC.ShowText( 'Failed to update ' + name + ':' )
                
                HC.ShowException( e )
                
                time.sleep( 3 )
                
            
        
        time.sleep( 5 )
        
    
def DAEMONSynchroniseSubscriptions():
    
    HC.repos_changed = False
    
    if not HC.options[ 'pause_subs_sync' ]:
        
        subscription_names = HC.app.ReadDaemon( 'subscription_names' )
        
        for name in subscription_names:
            
            info = HC.app.ReadDaemon( 'subscription', name )
            
            site_type = info[ 'site_type' ]
            query_type = info[ 'query_type' ]
            query = info[ 'query' ]
            frequency_type = info[ 'frequency_type' ]
            frequency = info[ 'frequency' ]
            advanced_tag_options = info[ 'advanced_tag_options' ]
            advanced_import_options = info[ 'advanced_import_options' ]
            last_checked = info[ 'last_checked' ]
            url_cache = info[ 'url_cache' ]
            paused = info[ 'paused' ]
            
            if paused: continue
            
            now = HC.GetNow()
            
            if last_checked is None: last_checked = 0
            
            if last_checked + ( frequency_type * frequency ) < now:
                
                try:
                    
                    job_key = HC.JobKey( pausable = True, cancellable = False )
                    
                    message = HC.MessageGauge( HC.MESSAGE_TYPE_GAUGE, 'checking ' + name + ' subscription', job_key )
                    
                    HC.pubsub.pub( 'message', message )
                    
                    do_tags = len( advanced_tag_options ) > 0
                    
                    if site_type == HC.SITE_TYPE_BOORU:
                        
                        ( booru_name, booru_query_type ) = query_type
                        
                        try: booru = HC.app.ReadDaemon( 'remote_booru', booru_name )
                        except: raise Exception( 'While attempting to execute a subscription on booru ' + name + ', the client could not find that booru in the db.' )
                        
                        tags = query.split( ' ' )
                        
                        all_args = ( ( booru, tags ), )
                        
                    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY:
                        
                        info = {}
                        
                        info[ 'rating_nudity' ] = 3
                        info[ 'rating_violence' ] = 3
                        info[ 'rating_profanity' ] = 3
                        info[ 'rating_racism' ] = 3
                        info[ 'rating_sex' ] = 3
                        info[ 'rating_spoilers' ] = 3
                        
                        info[ 'rating_yaoi' ] = 1
                        info[ 'rating_yuri' ] = 1
                        info[ 'rating_loli' ] = 1
                        info[ 'rating_shota' ] = 1
                        info[ 'rating_teen' ] = 1
                        info[ 'rating_guro' ] = 1
                        info[ 'rating_furry' ] = 1
                        info[ 'rating_beast' ] = 1
                        info[ 'rating_male' ] = 1
                        info[ 'rating_female' ] = 1
                        info[ 'rating_futa' ] = 1
                        info[ 'rating_other' ] = 1
                        
                        info[ 'filter_media' ] = 'A'
                        info[ 'filter_order' ] = 'date_new'
                        info[ 'filter_type' ] = 0
                        
                        advanced_hentai_foundry_options = info
                        
                        if query_type == 'artist': all_args = ( ( 'artist pictures', query, advanced_hentai_foundry_options ), ( 'artist scraps', query, advanced_hentai_foundry_options ) )
                        else:
                            
                            tags = query.split( ' ' )
                            
                            all_args = ( ( query_type, tags, advanced_hentai_foundry_options ), )
                            
                        
                    elif site_type == HC.SITE_TYPE_PIXIV: all_args = ( ( query_type, query ), )
                    else: all_args = ( ( query, ), )
                    
                    downloaders = [ HydrusDownloading.GetDownloader( site_type, *args ) for args in all_args ]
                    
                    downloaders[0].SetupGallerySearch() # for now this is cookie-based for hf, so only have to do it on one
                    
                    all_url_args = []
                    
                    while True:
                        
                        while job_key.IsPaused():
                            
                            message.SetInfo( 'text', 'paused' )
                            
                            time.sleep( 1 )
                            
                            if HC.shutdown: return
                            
                            if message.IsClosed(): return
                            
                        
                        while HC.options[ 'pause_subs_sync' ]:
                            
                            message.SetInfo( 'text', 'subscriptions paused' )
                            
                            time.sleep( 5 )
                            
                            if HC.shutdown: return
                            
                            if message.IsClosed(): return
                            
                            if HC.subs_changed:
                                
                                message.Close()
                                
                                HC.pubsub.pub( 'notify_restart_subs_sync_daemon' )
                                
                                return
                                
                            
                        
                        if HC.shutdown: return
                        
                        downloaders_to_remove = []
                        
                        for downloader in downloaders:
                            
                            page_of_url_args = downloader.GetAnotherPage()
                            
                            if len( page_of_url_args ) == 0: downloaders_to_remove.append( downloader )
                            else:
                                
                                fresh_url_args = [ url_args for url_args in page_of_url_args if url_args[0] not in url_cache ]
                                
                                # i.e. we have hit the url cache, so no need to fetch any more pages
                                if len( fresh_url_args ) == 0 or len( fresh_url_args ) != len( page_of_url_args ): downloaders_to_remove.append( downloader )
                                
                                all_url_args.extend( fresh_url_args )
                                
                                message.SetInfo( 'text', 'found ' + HC.ConvertIntToPrettyString( len( all_url_args ) ) + ' new files for ' + name )
                                
                            
                        
                        for downloader in downloaders_to_remove: downloaders.remove( downloader )
                        
                        if len( downloaders ) == 0: break
                        
                    
                    message.SetInfo( 'range', len( all_url_args ) )
                    message.SetInfo( 'value', 0 )
                    message.SetInfo( 'mode', 'gauge' )
                    
                    all_url_args.reverse() # to do oldest first, which means we can save incrementally
                    
                    i = 1
                    
                    num_new = 0
                    
                    successful_hashes = set()
                    
                    for url_args in all_url_args:
                        
                        while HC.options[ 'pause_subs_sync' ]:
                            
                            message.SetInfo( 'text', 'subscriptions paused' )
                            
                            time.sleep( 5 )
                            
                            if HC.shutdown: return
                            
                            if HC.subs_changed:
                                
                                message.Close()
                                
                                HC.pubsub.pub( 'notify_restart_subs_sync_daemon' )
                                
                                return
                                
                            
                        
                        if HC.shutdown: return
                        
                        try:
                            
                            url = url_args[0]
                            
                            url_cache.add( url )
                            
                            x_out_of_y = HC.ConvertIntToPrettyString( i ) + '/' + HC.ConvertIntToPrettyString( len( all_url_args ) )
                            
                            message.SetInfo( 'value', i )
                            message.SetInfo( 'text', name + ': ' + x_out_of_y + ' : checking url status' )
                            
                            ( status, hash ) = HC.app.ReadDaemon( 'url_status', url )
                            
                            if status == 'deleted' and 'exclude_deleted_files' not in advanced_import_options: status = 'new'
                            
                            if status == 'redundant':
                                
                                if do_tags:
                                    
                                    try:
                                        
                                        message.SetInfo( 'text', name + ': ' + x_out_of_y + ' : found file in db, fetching tags' )
                                        
                                        tags = downloader.GetTags( *url_args )
                                        
                                        service_keys_to_tags = HydrusDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options )
                                        
                                        service_keys_to_content_updates = HydrusDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags )
                                        
                                        HC.app.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                        
                                    except: pass
                                    
                                
                            elif status == 'new':
                                
                                num_new += 1
                                
                                message.SetInfo( 'text', name + ': ' + x_out_of_y + ' : downloading file' )
                                
                                if do_tags: ( temp_path, tags ) = downloader.GetFileAndTags( *url_args )
                                else:
                                    
                                    temp_path = downloader.GetFile( *url_args )
                                    
                                    tags = []
                                    
                                
                                service_keys_to_tags = HydrusDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options )
                                
                                message.SetInfo( 'text', name + ': ' + x_out_of_y + ' : importing file' )
                                
                                ( status, hash ) = HC.app.WriteSynchronous( 'import_file', temp_path, advanced_import_options = advanced_import_options, service_keys_to_tags = service_keys_to_tags, url = url )
                                
                                try: os.remove( temp_path )
                                except: pass # sometimes this fails, I think due to old handles not being cleaned up fast enough. np--it'll be cleaned up later
                                
                                if status in ( 'successful', 'redundant' ): successful_hashes.add( hash )
                                
                            
                        except Exception as e:
                            
                            HC.ShowText( 'While trying to execute subscription ' + name + ', the url ' + url + ' caused this problem:' )
                            
                            HC.ShowException( e )
                            
                        
                        i += 1
                        
                        if i % 20 == 0:
                            
                            info[ 'site_type' ] = site_type
                            info[ 'query_type' ] = query_type
                            info[ 'query' ] = query
                            info[ 'frequency_type' ] = frequency_type
                            info[ 'frequency' ] = frequency
                            info[ 'advanced_tag_options' ] = advanced_tag_options
                            info[ 'advanced_import_options' ] = advanced_import_options
                            info[ 'last_checked' ] = last_checked
                            info[ 'url_cache' ] = url_cache
                            info[ 'paused' ] = paused
                            
                            HC.app.WriteSynchronous( 'subscription', name, info )
                            
                        
                        HC.app.WaitUntilGoodTimeToUseGUIThread()
                        
                    
                    if len( successful_hashes ) > 0:
                        
                        text = HC.u( len( successful_hashes ) ) + ' files imported from ' + name
                        
                        message.SetInfo( 'text', text )
                        message.SetInfo( 'hashes', successful_hashes )
                        message.SetInfo( 'mode', 'files' )
                        
                        job_key.SetPausable( False )
                        
                    else: message.Close()
                    
                    last_checked = now
                    
                except Exception as e:
                    
                    if 'message' in locals(): message.Close()
                    
                    last_checked = now + HC.UPDATE_DURATION
                    
                    HC.ShowText( 'Problem with ' + name + ':' )
                    
                    HC.ShowException( e )
                    
                    time.sleep( 3 )
                    
                
                info[ 'site_type' ] = site_type
                info[ 'query_type' ] = query_type
                info[ 'query' ] = query
                info[ 'frequency_type' ] = frequency_type
                info[ 'frequency' ] = frequency
                info[ 'advanced_tag_options' ] = advanced_tag_options
                info[ 'advanced_import_options' ] = advanced_import_options
                info[ 'last_checked' ] = last_checked
                info[ 'url_cache' ] = url_cache
                info[ 'paused' ] = paused
                
                HC.app.WriteSynchronous( 'subscription', name, info )
                
            
        
        time.sleep( 3 )
        
    
def DAEMONUPnP():
    
    try:
        
        local_ip = HydrusNATPunch.GetLocalIP()
        
        current_mappings = HydrusNATPunch.GetUPnPMappings()
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
        
    except: return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
    
    services = HC.app.GetManager( 'services' ).GetServices( ( HC.LOCAL_BOORU, ) )
    
    for service in services:
        
        info = service.GetInfo()
        
        internal_port = info[ 'port' ]
        upnp = info[ 'upnp' ]
        
        if ( local_ip, internal_port ) in our_mappings:
            
            current_external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            if upnp is None or current_external_port != upnp: HydrusNATPunch.RemoveUPnPMapping( current_external_port, 'TCP' )
            
        
    
    for service in services:
        
        info = service.GetInfo()
        
        internal_port = info[ 'port' ]
        upnp = info[ 'upnp' ]
        
        if upnp is not None:
            
            if ( local_ip, internal_port ) not in our_mappings:
                
                service_type = service.GetServiceType()
                
                external_port = upnp
                
                protocol = 'TCP'
                
                description = HC.service_string_lookup[ service_type ] + ' at ' + local_ip + ':' + str( internal_port )
                
                duration = 3600
                
                HydrusNATPunch.AddUPnPMapping( local_ip, internal_port, external_port, protocol, description, duration = duration )
                
            
        
    