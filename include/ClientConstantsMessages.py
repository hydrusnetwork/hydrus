import collections
import hashlib
import httplib
import ClientConstants as CC
import HydrusConstants as HC
import HydrusImageHandling
import HydrusMessageHandling
import os
import random
import sqlite3
import threading
import time
import traceback
import yaml
import wx
import zlib
import HydrusData
import HydrusGlobals
'''
class Conversation( object ):
    
    def __init__( self, identity, conversation_key, subject, messages, drafts, search_context ):
        
        self._identity = identity
        self._conversation_key = conversation_key
        self._subject = subject
        self._messages = messages
        self._drafts = drafts
        self._search_context = search_context
        
        HydrusGlobals.client_controller.sub( self, 'DeleteDraft', 'delete_draft_data' )
        HydrusGlobals.client_controller.sub( self, 'DeleteMessage', 'delete_message' )
        HydrusGlobals.client_controller.sub( self, 'DraftSaved', 'draft_saved' )
        HydrusGlobals.client_controller.sub( self, 'ArchiveConversation', 'archive_conversation_data' )
        HydrusGlobals.client_controller.sub( self, 'InboxConversation', 'inbox_conversation_data' )
        HydrusGlobals.client_controller.sub( self, 'UpdateMessageStatuses', 'message_statuses_data' )
        
    
    def AddDraft( self, draft ): self._drafts.append( draft )
    
    def AddMessage( self, message ): self._messages.append( message )
    
    def ArchiveConversation( self, conversation_key ):
        
        if conversation_key == self._conversation_key:
            
            self._inbox = False
            
            for message in self._messages: message.Archive()
            
        
    
    def DeleteDraft( self, draft_key ):
        
        self._drafts = [ draft for draft in self._drafts if draft.GetDraftKey() != draft_key ]
        
        if len( self._messages ) + len( self._drafts ) == 0:
            
            HydrusGlobals.client_controller.pub( 'delete_conversation_data', self._conversation_key )
            HydrusGlobals.client_controller.pub( 'delete_conversation_gui', self._conversation_key )
            
        
    
    def DraftSaved( self, draft_key, draft_message ):
        
        for ( index, draft ) in enumerate( self._drafts ):
            
            if draft.GetDraftKey() == draft_key:
                
                self._drafts[ index ] = draft_message
                
                return
                
            
        
    
    def DeleteMessage( self, message_key ):
        
        self._messages = [ message for message in self._messages if message.GetMessageKey() != message_key ]
        
        if len( self._messages ) + len( self._drafts ) == 0:
            
            HydrusGlobals.client_controller.pub( 'delete_conversation_data', self._conversation_key )
            HydrusGlobals.client_controller.pub( 'delete_conversation_gui', self._conversation_key )
            
        
    
    def GetConversationKey( self ): return self._conversation_key
    
    def GetListCtrlTuple( self ):
        
        if len( self._messages ) > 0:
            
            first_message = self._messages[0]
            last_message = self._messages[-1]
            
            first_timestamp = first_message.GetTimestamp()
            last_timestamp = last_message.GetTimestamp()
            
            from_name = first_message.GetContactFrom().GetName()
            
        else:
            
            first_timestamp = None
            last_timestamp = None
            
            from_name = self._drafts[0].GetContactFrom().GetName()
            
        
        participants = self.GetParticipants()
        
        num_messages_unread = len( [ message for message in self._messages if ( self._identity, 'sent' ) in message.GetDestinations() ] )
        
        inbox = True in ( message.IsInbox() for message in self._messages )
        
        return ( self._conversation_key, inbox, self._subject, from_name, participants, len( self._messages ), num_messages_unread, first_timestamp, last_timestamp )
        
    
    def GetMessages( self ): return ( self._messages, self._drafts )
    
    def GetMessageKeysWithDestination( self, destination ): return [ message.GetMessageKey() for message in self._messages if message.HasDestination( destination ) ]
    
    def GetParticipants( self ):
        
        if len( self._messages ) == 0: return []
        else:
            
            first_message = self._messages[ 0 ]
            
            return first_message.GetParticipants()
            
        
    
    def GetStartedBy( self ):
        
        if len( self._messages ) > 0: return self._messages[ 0 ].GetContactFrom()
        elif len( self._drafts ) > 0: return self._drafts[ 0 ].GetContactFrom()
        else: return None
        
    
    def GetSubject( self ): return self._subject
    
    def GetUpdated( self ):
        
        if len( self._messages ) > 0:
            
            last_message = self._messages[-1]
            last_timestamp = last_message.GetTimestamp()
            
        else: last_timestamp = None
        
        return last_timestamp
        
    
    def HasMessageKey( self, message_key ): return True in ( message_key == message.GetMessageKey() for message in self._messages )
    
    def HasRead( self ): return True in ( message.IsRead( self._identity ) for message in self._messages )
    
    def HasUnread( self ): return True in ( message.IsUnread( self._identity ) for message in self._messages )
    
    def InboxConversation( self, conversation_key ):
        
        if conversation_key == self._conversation_key:
            
            self._inbox = True
            
            for message in self._messages: message.Inbox()
            
        
    
    def IsInbox( self ): return True in ( message.IsInbox() for message in self._messages )
    
    def UpdateMessageStatuses( self, message_key, status_updates ):
        
        for message in self._messages:
            
            if message_key == message.GetMessageKey():
                
                message.UpdateMessageStatuses( status_updates )
                
                break
                
            
        
    
class Contact( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Contact'
    
    def __init__( self, public_key, name, host, port ):
        
        HydrusData.HydrusYAMLBase.__init__( self )
        
        self._public_key = public_key
        self._name = name
        self._host = host
        self._port = port
        
    
    def __hash__( self ): return self._name.__hash__()
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def Encrypt( self, message ): return HydrusMessageHandling.PackageMessageForDelivery( message, self._public_key )
    
    def GetAddress( self ): return ( self._host, self._port )
    
    def GetConnection( self ): return None # this used to be connectiontoservice
    
    def GetContactKey( self ):
        
        if self._public_key is None: return None
        else: return hashlib.sha256( self._public_key ).digest()
        
    
    def GetInfo( self ): return ( self._public_key, self._name, self._host, self._port )
    
    def GetName( self ): return self._name
    
    def GetPublicKey( self ): return self._public_key
    
    def HasPublicKey( self ): return self._public_key is not None
    
class DraftMessage( object ):
    
    def __init__( self, draft_key, conversation_key, subject, contact_from, contacts_names_to, recipients_visible, body, attachment_hashes, is_new = False ):
        
        self._draft_key = draft_key
        self._conversation_key = conversation_key
        self._subject = subject
        self._contact_from = contact_from
        self._contacts_names_to = contacts_names_to
        self._recipients_visible = recipients_visible
        self._body = body
        self._attachment_hashes = attachment_hashes
        self._is_new = is_new
        
    
    def __hash__( self ): return self._draft_key.__hash__()
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def GetContactFrom( self ): return self._contact_from
    
    def GetDraftKey( self ): return self._draft_key
    
    def GetInfo( self ): return ( self._draft_key, self._conversation_key, self._subject, self._contact_from, self._contacts_names_to, self._recipients_visible, self._body, self._attachment_hashes )
    
    def IsNew( self ): return self._is_new
    
    def IsReply( self ): return self._conversation_key != self._draft_key
    
    def Saved( self ): self._is_new = False
    
class Message( object ):
    
    def __init__( self, message_key, contact_from, destinations, timestamp, body, attachment_hashes, inbox ):
        
        self._message_key = message_key
        self._contact_from = contact_from
        self._destinations = destinations
        self._timestamp = timestamp
        self._body = body
        self._attachment_hashes = attachment_hashes
        self._inbox = inbox
        
    
    def __hash__( self ): return self._message_key.__hash__()
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def Archive( self ): self._inbox = False
    
    def GetBody( self ): return self._body
    def GetContactFrom( self ): return self._contact_from
    def GetContactsTo( self ): return [ contact_to for ( contact_to, status ) in self._destinations ]
    def GetDestinations( self ): return self._destinations
    def GetMessageKey( self ): return self._message_key
    def GetParticipants( self ): return [ self._contact_from ] + self.GetContactsTo()
    def GetTimestamp( self ): return self._timestamp
    
    def HasDestination( self, destination ): return destination in self._destinations
    
    def Inbox( self ): self._inbox = True
    
    def IsInbox( self ): return self._inbox
    def IsRead( self, identity ): return ( identity, 'read' ) in self._destinations
    def IsUnread( self, identity ): return ( identity, 'sent' ) in self._destinations
    
    def Read( self, identity ): self.UpdateMessageStatuses( [ ( identity.GetContactKey(), 'read' ) ] )
    
    def UpdateMessageStatuses( self, updates ):
        
        contact_keys_to_contacts = { contact.GetContactKey() : contact for ( contact, status ) in self._destinations }
        
        dest_dict = dict( self._destinations )
        
        for ( contact_key, status ) in updates:
            
            if contact_key in contact_keys_to_contacts:
                
                dest_dict[ contact_keys_to_contacts[ contact_key ] ] = status
                
            
        
        self._destinations = dest_dict.items()
        
    
    def Unread( self, identity ): self.UpdateMessageStatuses( [ ( identity.GetContactKey(), 'sent' ) ] )
    
class MessageSearchContext( object ):
    
    def __init__( self, identity, raw_predicates = None ):
        
        if raw_predicates is None: raw_predicates = []
        
        self._identity = identity
        
        raw_system_predicates = [ predicate for predicate in raw_predicates if predicate.startswith( 'system:' ) ]
        
        self._system_predicates = MessageSystemPredicates( raw_system_predicates )
        
        raw_search_terms = [ predicate for predicate in raw_predicates if not predicate.startswith( 'system:' ) ]
        
        self._search_terms_to_include = [ search_term for search_term in raw_search_terms if not search_term.startswith( '-' ) ]
        self._search_terms_to_exclude = [ search_term[1:] for search_term in raw_search_terms if search_term.startswith( '-' ) ]
        
    
    def GetIdentity( self ): return self._identity
    def GetSystemPredicates( self ): return self._system_predicates
    def GetTermsToExclude( self ): return self._search_terms_to_exclude
    def GetTermsToInclude( self ): return self._search_terms_to_include

class MessageSystemPredicates( object ):
    
    STATUS = 0
    CONTACT_STARTED = 1
    CONTACT_FROM = 2
    CONTACT_TO = 3
    TIMESTAMP = 4
    NUM_ATTACHMENTS = 5
    
    def __init__( self, system_predicates ):
        
        self._predicates = {}
        
        self._predicates[ self.NUM_ATTACHMENTS ] = []
        
        self._status = None
        
        self._contact_from = None
        self._contact_to = None
        self._contact_started = None
        self._min_timestamp = None
        self._max_timestamp = None
        
        self._inbox = 'system:inbox' in system_predicates
        
        self._archive = 'system:archive' in system_predicates
        
        self._draft = 'system:draft' in system_predicates
        
        isin = lambda a, b: a in b
        startswith = lambda a, b: a.startswith( b )
        lessthan = lambda a, b: a < b
        greaterthan = lambda a, b: a > b
        equals = lambda a, b: a == b
        about_equals = lambda a, b: a < b * 1.15 and a > b * 0.85
        
        for predicate in system_predicates:
            
            if predicate.startswith( 'system:status' ):
                
                try:
                    
                    status = predicate[14:]
                    
                    self._status = status
                    
                except: raise Exception( 'I could not parse the status predicate.' )
                
            
            if predicate.startswith( 'system:started_by' ):
                
                try:
                    
                    started_by = predicate[18:]
                    
                    self._contact_started = started_by
                    
                except: raise Exception( 'I could not parse the started by predicate.' )
                
            
            if predicate.startswith( 'system:from' ):
                
                try:
                    
                    contact_from = predicate[12:]
                    
                    self._contact_from = contact_from
                    
                except: raise Exception( 'I could not parse the contact from predicate.' )
                
            
            if predicate.startswith( 'system:to' ):
                
                try:
                    
                    contact_to = predicate[10:]
                    
                    self._contact_to = contact_to
                    
                except: raise Exception( 'I could not parse the contact to predicate.' )
                
            
            if predicate.startswith( 'system:age' ):
                
                try:
                    
                    condition = predicate[10]
                    
                    if condition not in ( '<', '>', u'\u2248' ): raise Exception()
                    
                    age = predicate[11:]
                    
                    years = 0
                    months = 0
                    days = 0
                    
                    if 'y' in age:
                        
                        ( years, age ) = age.split( 'y' )
                        
                        years = int( years )
                        
                    
                    if 'm' in age:
                        
                        ( months, age ) = age.split( 'm' )
                        
                        months = int( months )
                        
                    
                    if 'd' in age:
                        
                        ( days, age ) = age.split( 'd' )
                        
                        days = int( days )
                        
                    
                    timestamp = HydrusData.GetNow() - ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 86400 )
                    
                    # this is backwards because we are talking about age, not timestamp
                    
                    if condition == '<': self._max_timestamp = timestamp
                    elif condition == '>': self._min_timestamp = timestamp
                    elif condition == u'\u2248':
                        self._min_timestamp = int( timestamp * 0.85 )
                        self._max_timestamp = int( timestamp * 1.15 )
                    
                except: raise Exception( 'I could not parse the age predicate.' )
                
            
            if predicate.startswith( 'system:numattachments' ):
                
                try:
                    
                    condition = predicate[21]
                    
                    if condition not in ( '>', '<', '=', u'\u2248' ): raise Exception()
                    
                    num_attachments = int( predicate[22:] )
                    
                    if num_attachments >= 0:
                        
                        if condition == '<': self._predicates[ self.NUM_ATTACHMENTS ].append( ( lessthan, num_attachments ) )
                        elif condition == '>': self._predicates[ self.NUM_ATTACHMENTS ].append( ( greaterthan, num_attachments ) )
                        elif condition == '=': self._predicates[ self.NUM_ATTACHMENTS ].append( ( equals, num_attachments ) )
                        elif condition == u'\u2248': self._predicates[ self.NUM_ATTACHMENTS ].append( ( about_equals, num_attachments ) )
                        
                    
                except: raise Exception( 'I could not parse the num attachments predicate.' )
                
            
        
    
    def GetInfo( self ): return ( self._inbox, self._archive, self._draft, self._status, self._contact_from, self._contact_to, self._contact_started, self._min_timestamp, self._max_timestamp )
    
    # maybe reconfigure this!
    # instead of Ok, I could do some real good searching and ANDing with the above predicates
    # especially since this is for getting the message_ids, not the whole convo, which will have the rich data
    
    def Ok( self, num_attachments ):
        
        if False in ( function( num_attachments, arg ) for ( function, arg ) in self._predicates[ self.NUM_ATTACHMENTS ] ): return False
        
        return True
        
    '''