import os
import random
import time
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworking

from hydrus.server import ServerDB

from hydrus.test import TestController

class TestServerDB( unittest.TestCase ):
    
    def _read( self, action, *args, **kwargs ): return TestServerDB._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestServerDB._db.Write( action, True, *args, **kwargs )
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ServerDB.DB( HG.test_controller, TestController.DB_DIR, 'server' )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._db.Shutdown()
        
        while not cls._db.LoopIsFinished():
            
            time.sleep( 0.1 )
            
        
        del cls._db
        
    
    def _test_account_creation( self ):
        
        result = sorted( self._read( 'account_types', self._tag_service_key, self._tag_service_account ), key = lambda at: at.GetTitle() )
        
        ( self._tag_service_admin_account_type, self._null_account_type ) = result
        
        self.assertEqual( self._tag_service_admin_account_type.GetTitle(), 'administrator' )
        self.assertEqual( self._null_account_type.GetTitle(), 'null account' )
        
        #
        
        self._regular_user_account_type = HydrusNetwork.AccountType.GenerateNewAccountType( 'regular user', { HC.CONTENT_TYPE_MAPPINGS : HC.PERMISSION_ACTION_CREATE, HC.CONTENT_TYPE_TAG_PARENTS : HC.PERMISSION_ACTION_PETITION, HC.CONTENT_TYPE_TAG_SIBLINGS : HC.PERMISSION_ACTION_PETITION }, HydrusNetworking.BandwidthRules() )
        self._deletee_user_account_type = HydrusNetwork.AccountType.GenerateNewAccountType( 'deletee user', {}, HydrusNetworking.BandwidthRules() )
        
        new_account_types = [ self._tag_service_admin_account_type, self._null_account_type, self._regular_user_account_type, self._deletee_user_account_type ]
        
        #
        
        self._write( 'account_types', self._tag_service_key, self._tag_service_account, new_account_types, {} )
        
        edited_account_types = self._read( 'account_types', self._tag_service_key, self._tag_service_account )
        
        self.assertEqual(
            { at.GetAccountTypeKey() for at in edited_account_types },
            { at.GetAccountTypeKey() for at in ( self._tag_service_admin_account_type, self._null_account_type, self._regular_user_account_type, self._deletee_user_account_type ) }
        )
        
        #
        
        r_keys = self._read( 'registration_keys', self._tag_service_key, self._tag_service_account, 5, self._deletee_user_account_type.GetAccountTypeKey(), HydrusData.GetNow() + 86400 * 365 )
        
        access_keys = [ self._read( 'access_key', self._tag_service_key, r_key ) for r_key in r_keys ]
        
        account_keys = [ self._read( 'account_key_from_access_key', self._tag_service_key, access_key ) for access_key in access_keys ] 
        
        accounts = [ self._read( 'account', self._tag_service_key, account_key ) for account_key in account_keys ] 
        
        for account in accounts:
            
            self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._deletee_user_account_type.GetAccountTypeKey() )
            
        
        #
        
        deletee_account_type_keys_to_replacement_account_type_keys = { self._deletee_user_account_type.GetAccountTypeKey() : self._regular_user_account_type.GetAccountTypeKey() }
        
        new_account_types = [ self._tag_service_admin_account_type, self._null_account_type, self._regular_user_account_type ]
        
        self._write( 'account_types', self._tag_service_key, self._tag_service_account, new_account_types, deletee_account_type_keys_to_replacement_account_type_keys )
        
        accounts = [ self._read( 'account', self._tag_service_key, account_key ) for account_key in account_keys ] 
        
        self._tag_service_regular_account = accounts[0]
        
        for account in accounts:
            
            self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._regular_user_account_type.GetAccountTypeKey() )
            
        
        #
        
        r_keys = self._read( 'registration_keys', self._tag_service_key, self._tag_service_account, 5, self._regular_user_account_type.GetAccountTypeKey(), HydrusData.GetNow() + 86400 * 365 )
        
        self.assertEqual( len( r_keys ), 5 )
        
        for r_key in r_keys: self.assertEqual( len( r_key ), 32 )
        
        r_key = r_keys[0]
        
        access_key = self._read( 'access_key', self._tag_service_key, r_key )
        access_key_2 = self._read( 'access_key', self._tag_service_key, r_key )
        
        self.assertNotEqual( access_key, access_key_2 )
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            # this access key has been replaced
            self._read( 'account_key_from_access_key', self._tag_service_key, access_key )
            
        
        account_key = self._read( 'account_key_from_access_key', self._tag_service_key, access_key_2 )
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            # this registration token has been deleted
            self._read( 'access_key', self._tag_service_key, r_key )
            
        
    
    def _test_account_fetching_from_content( self ):
        
        tag = 'character:samus aran'
        hash = HydrusData.GenerateKey()
        
        mappings_content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, ( hash, ) ) )
        mapping_content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) )
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, mappings_content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        # can extend this to generate and fetch an actual update given a timespan
        
        #
        
        result = self._read( 'account_key_from_content', self._tag_service_key, mapping_content )
        
        self.assertEqual( result, self._tag_service_regular_account.GetAccountKey() )
        
    
    def _test_account_modification( self ):
        
        regular_account_key = self._tag_service_regular_account.GetAccountKey()
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._regular_user_account_type.GetAccountTypeKey() )
        
        self._write( 'modify_account_account_type', self._tag_service_key, self._tag_service_account, regular_account_key, self._tag_service_admin_account_type.GetAccountTypeKey() )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._tag_service_admin_account_type.GetAccountTypeKey() )
        
        self._write( 'modify_account_account_type', self._tag_service_key, self._tag_service_account, regular_account_key, self._regular_user_account_type.GetAccountTypeKey() )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._regular_user_account_type.GetAccountTypeKey() )
        
        #
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsBanned() )
        
        ban_reason = 'oh no no no'
        
        self._write( 'modify_account_ban', self._tag_service_key, self._tag_service_account, regular_account_key, ban_reason, None )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertTrue( account.IsBanned() )
        
        ( reason, created, expires ) = account.GetBannedInfo()
        
        self.assertEqual( reason, ban_reason )
        self.assertTrue( HydrusData.GetNow() - 5 < created < HydrusData.GetNow() + 5 )
        self.assertEqual( expires, None )
        
        ban_reason = 'just having a giggle m8'
        ban_expires = HydrusData.GetNow() + 86400
        
        self._write( 'modify_account_ban', self._tag_service_key, self._tag_service_account, regular_account_key, ban_reason, ban_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertTrue( account.IsBanned() )
        
        ( reason, created, expires ) = account.GetBannedInfo()
        
        self.assertEqual( reason, ban_reason )
        self.assertTrue( HydrusData.GetNow() - 5 < created < HydrusData.GetNow() + 5 )
        self.assertEqual( expires, ban_expires )
        
        self._write( 'modify_account_unban', self._tag_service_key, self._tag_service_account, regular_account_key )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsBanned() )
        
        #
        
        set_expires = HydrusData.GetNow() - 5
        
        self._write( 'modify_account_expires', self._tag_service_key, self._tag_service_account, regular_account_key, set_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertTrue( account.IsExpired() )
        
        self.assertEqual( set_expires, account.GetExpires() )
        
        set_expires = HydrusData.GetNow() + 86400
        
        self._write( 'modify_account_expires', self._tag_service_key, self._tag_service_account, regular_account_key, set_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsExpired() )
        
        self.assertEqual( set_expires, account.GetExpires() )
        
        set_expires = None
        
        self._write( 'modify_account_expires', self._tag_service_key, self._tag_service_account, regular_account_key, set_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsExpired() )
        
        self.assertEqual( set_expires, account.GetExpires() )
        
        #
        
        set_message = 'hello'
        
        self._write( 'modify_account_set_message', self._tag_service_key, self._tag_service_account, regular_account_key, set_message )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        ( message, created ) = account.GetMessageAndTimestamp()
        
        self.assertEqual( message, set_message )
        
        set_message = ''
        
        self._write( 'modify_account_set_message', self._tag_service_key, self._tag_service_account, regular_account_key, set_message )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        ( message, created ) = account.GetMessageAndTimestamp()
        
        self.assertEqual( message, set_message )
        
    
    def _test_content_creation_and_service_info_counts_files( self ):
        
        # files
        
        hashes = [ HydrusData.GenerateKey() for i in range( 20 ) ]
        
        service_info = self._read( 'service_info', self._file_service_key )
        
        expected_num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        expected_num_hashes = service_info[ HC.SERVICE_INFO_NUM_FILE_HASHES ]
        expected_num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
        expected_num_petitioned_files = service_info[ HC.SERVICE_INFO_NUM_PETITIONED_FILES ]
        expected_num_actionable_delete_petitions = service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_FILE_DELETE_PETITIONS ]
        
        def do_num_test():
            
            service_info = self._read( 'service_info', self._file_service_key )
            
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_FILES ], expected_num_files )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_FILE_HASHES ], expected_num_hashes )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ], expected_num_deleted_files )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_PETITIONED_FILES ], expected_num_petitioned_files )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_FILE_DELETE_PETITIONS ], expected_num_actionable_delete_petitions )
            
        
        # add with admin
        
        for ( i, hash ) in enumerate( hashes ):
            
            file_dict = {
                'hash' : hash,
                'ip' : '127.0.0.1',
                'height' : 200,
                'width' : 200,
                'mime' : 2,
                'size' : 5270,
                'path' : os.path.join( HC.STATIC_DIR, 'hydrus.png' ),
                'thumbnail' : b'abcd'
            }
            
            self._write( 'file', self._file_service, self._file_service_account, file_dict, HydrusData.GetNow() )
            
            expected_num_files += 1
            expected_num_hashes += 1
            
            do_num_test()
            
        
        # delete with admin
        
        NUM_TO_DELETE = 5
        
        deletee_hashes = random.sample( hashes, NUM_TO_DELETE )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, deletee_hashes )
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'files are bad' )
        
        self._write( 'update', self._file_service_key, self._file_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_files -= NUM_TO_DELETE
        expected_num_deleted_files += NUM_TO_DELETE
        
        do_num_test()
        
        # can't do this until I have a regular account set up earlier in this big test
        # petition with regular
        # approve and deny some with admin
        
    
    def _test_content_creation_and_service_info_counts_mappings( self ):
        
        service_info = self._read( 'service_info', self._tag_service_key )
        
        expected_num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
        expected_num_hashes = service_info[ HC.SERVICE_INFO_NUM_FILE_HASHES ]
        expected_num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
        expected_num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
        expected_num_petitioned_mappings = service_info[ HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ]
        expected_num_actionable_delete_petitions = service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_MAPPING_DELETE_PETITIONS ]
        
        def do_num_test():
            
            service_info = self._read( 'service_info', self._tag_service_key )
            
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_TAGS ], expected_num_tags )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_FILE_HASHES ], expected_num_hashes )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ], expected_num_mappings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ], expected_num_deleted_mappings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ], expected_num_petitioned_mappings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_MAPPING_DELETE_PETITIONS ], expected_num_actionable_delete_petitions )
            
        
        tag_1 = 'character:samus aran'
        tag_2 = 'typo'
        
        tag_1_hashes = [ HydrusData.GenerateKey() for i in range( 100 ) ]
        tag_2_hashes = tag_1_hashes[50:] + [ HydrusData.GenerateKey() for i in range( 50 ) ]
        
        # add with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_1, tag_1_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_2, tag_2_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tags += 2
        expected_num_hashes += len( set( tag_1_hashes ).union( tag_2_hashes ) )
        expected_num_mappings += len( tag_1_hashes ) + len( tag_2_hashes )
        
        do_num_test()
        
        # delete with admin
        
        tag_1_deletee_hashes = random.sample( tag_1_hashes, 15 )
        tag_2_deletee_hashes = random.sample( tag_2_hashes, 25 )
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_1, tag_1_deletee_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'admin delete' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_2, tag_2_deletee_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'admin delete' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_mappings -= len( tag_1_deletee_hashes ) + len( tag_2_deletee_hashes )
        expected_num_deleted_mappings += len( tag_1_deletee_hashes ) + len( tag_2_deletee_hashes )
        
        do_num_test()
        
        # petition with regular
        
        tag_1_petition_hashes = random.sample( set( tag_1_hashes ).difference( tag_1_deletee_hashes ), 15 )
        tag_2_petition_hashes = random.sample( set( tag_2_hashes ).difference( tag_2_deletee_hashes ), 25 )
        tag_2a_petition_hashes = random.sample( set( tag_2_hashes ).difference( tag_2_deletee_hashes ).difference( tag_2_petition_hashes ), 10 )
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_1, tag_1_petition_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'these are bad' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_2, tag_2_petition_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'these are bad' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_2, tag_2a_petition_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'bad for a stupid reason' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_petitioned_mappings += len( tag_1_petition_hashes ) + len( tag_2_petition_hashes ) + len( tag_2a_petition_hashes )
        expected_num_actionable_delete_petitions += 3
        
        do_num_test()
        
        # approve and deny some with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_1, tag_1_petition_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'these are bad' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_2, tag_2_petition_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'these are bad' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag_2, tag_2a_petition_hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PETITION, content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_mappings -= len( tag_1_petition_hashes ) + len( tag_2_petition_hashes )
        expected_num_deleted_mappings += len( tag_1_petition_hashes ) + len( tag_2_petition_hashes )
        expected_num_petitioned_mappings -= len( tag_1_petition_hashes ) + len( tag_2_petition_hashes ) + len( tag_2a_petition_hashes )
        expected_num_actionable_delete_petitions -= 3
        
        do_num_test()
        
    
    def _test_content_creation_and_service_info_counts_tag_parents( self ):
        
        service_info = self._read( 'service_info', self._tag_service_key )
        
        expected_num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
        expected_num_tag_parents = service_info[ HC.SERVICE_INFO_NUM_TAG_PARENTS ]
        expected_num_deleted_tag_parents = service_info[ HC.SERVICE_INFO_NUM_DELETED_TAG_PARENTS ]
        expected_num_pending_tag_parents = service_info[ HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS ]
        expected_num_actionable_add_petitions = service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_PARENT_ADD_PETITIONS ]
        expected_num_petitioned_tag_parents = service_info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ]
        expected_num_actionable_delete_petitions = service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_PARENT_DELETE_PETITIONS ]
        
        def do_num_test():
            
            service_info = self._read( 'service_info', self._tag_service_key )
            
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_TAGS ], expected_num_tags )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_TAG_PARENTS ], expected_num_tag_parents )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_DELETED_TAG_PARENTS ], expected_num_deleted_tag_parents )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS ], expected_num_pending_tag_parents )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_PARENT_ADD_PETITIONS ], expected_num_actionable_add_petitions )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ], expected_num_petitioned_tag_parents )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_PARENT_DELETE_PETITIONS ], expected_num_actionable_delete_petitions )
            
        
        child_tag_1 = 'child_tag_1'
        parent_tag_1 = 'parent_tag_1'
        
        child_tag_2 = 'child_tag_2'
        parent_tag_2 = 'parent_tag_2'
        
        child_tag_2a = 'child_tag_2a'
        parent_tag_2a = 'parent_tag_2a'
        
        child_tag_3 = 'child_tag_3'
        parent_tag_3 = 'parent_tag_3'
        replacement_parent_tag_3 = 'replacement_parent_tag_3'
        
        child_tag_4 = 'child_tag_4'
        parent_tag_4 = 'parent_tag_4'
        replacement_parent_tag_4 = 'replacement_parent_tag_4'
        
        # get some into the db as existing tags, since count adjustment logic can change
        
        hashes = [ HydrusData.GenerateKey() for i in range( 5 ) ]
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( child_tag_2, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( parent_tag_2, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( child_tag_4, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( parent_tag_4, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( replacement_parent_tag_4, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        service_info = self._read( 'service_info', self._tag_service_key )
        
        expected_num_tags += 5
        
        do_num_test()
        
        # add with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_1, parent_tag_1 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'admin add' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_3, parent_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'admin add' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_4, parent_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'admin add' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tags += 4
        expected_num_tag_parents += 3
        
        do_num_test()
        
        # delete with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_1, parent_tag_1 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'admin delete' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tag_parents -= 1
        expected_num_deleted_tag_parents += 1
        
        do_num_test()
        
        # pend with regular
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_2, parent_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'this is great' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_2a, parent_tag_2a ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'this is great' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_pending_tag_parents += 2
        expected_num_actionable_add_petitions += 1
        
        do_num_test()
        
        # approve and deny some with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_2, parent_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'this is great' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_2a, parent_tag_2a ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PEND, content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        # note no increase in num tags. _2 already known, _2a denied
        expected_num_tag_parents += 1
        expected_num_pending_tag_parents -= 2
        expected_num_actionable_add_petitions -= 1
        
        do_num_test()
        
        # petition with regular
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_2, parent_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'this is bad 2' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_3, parent_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_4, parent_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'replacing 4' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_3, replacement_parent_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_4, replacement_parent_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'replacing 4' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_petitioned_tag_parents += 3
        expected_num_pending_tag_parents += 2
        expected_num_actionable_delete_petitions += 3
        
        do_num_test()
        
        # approve and deny some with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_2, parent_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'this is bad 2' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_3, parent_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_4, parent_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PETITION, content, reason = 'replacing 4' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_3, replacement_parent_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag_4, replacement_parent_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PEND, content, reason = 'replacing 4' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tags += 1
        expected_num_tag_parents -= 1
        expected_num_deleted_tag_parents += 2
        expected_num_petitioned_tag_parents -= 3
        expected_num_pending_tag_parents -= 2
        expected_num_actionable_delete_petitions -= 3
        
        do_num_test()
        
    
    def _test_content_creation_and_service_info_counts_tag_siblings( self ):
        
        service_info = self._read( 'service_info', self._tag_service_key )
        
        expected_num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
        expected_num_tag_siblings = service_info[ HC.SERVICE_INFO_NUM_TAG_SIBLINGS ]
        expected_num_deleted_tag_siblings = service_info[ HC.SERVICE_INFO_NUM_DELETED_TAG_SIBLINGS ]
        expected_num_pending_tag_siblings = service_info[ HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS ]
        expected_num_actionable_add_petitions = service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_SIBLING_ADD_PETITIONS ]
        expected_num_petitioned_tag_siblings = service_info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS ]
        expected_num_actionable_delete_petitions = service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_SIBLING_DELETE_PETITIONS ]
        
        def do_num_test():
            
            service_info = self._read( 'service_info', self._tag_service_key )
            
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_TAGS ], expected_num_tags )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_TAG_SIBLINGS ], expected_num_tag_siblings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_DELETED_TAG_SIBLINGS ], expected_num_deleted_tag_siblings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS ], expected_num_pending_tag_siblings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_SIBLING_ADD_PETITIONS ], expected_num_actionable_add_petitions )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS ], expected_num_petitioned_tag_siblings )
            self.assertEqual( service_info[ HC.SERVICE_INFO_NUM_ACTIONABLE_SIBLING_DELETE_PETITIONS ], expected_num_actionable_delete_petitions )
            
        
        bad_tag_1 = 'bad_tag_1'
        good_tag_1 = 'good_tag_1'
        
        bad_tag_2 = 'bad_tag_2'
        good_tag_2 = 'good_tag_2'
        
        bad_tag_2a = 'bad_tag_2a'
        good_tag_2a = 'good_tag_2a'
        
        bad_tag_3 = 'bad_tag_3'
        good_tag_3 = 'good_tag_3'
        replacement_good_tag_3 = 'replacement_good_tag_3'
        
        bad_tag_4 = 'bad_tag_4'
        good_tag_4 = 'good_tag_4'
        replacement_good_tag_4 = 'replacement_good_tag_4'
        
        # get some into the db as existing tags, since count adjustment logic can change
        
        hashes = [ HydrusData.GenerateKey() for i in range( 5 ) ]
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( bad_tag_2, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( good_tag_2, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( bad_tag_4, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( good_tag_4, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( replacement_good_tag_4, hashes ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        service_info = self._read( 'service_info', self._tag_service_key )
        
        expected_num_tags += 5
        
        do_num_test()
        
        # add with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_1, good_tag_1 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'admin add' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_3, good_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'admin add' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_4, good_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'admin add' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tags += 4
        expected_num_tag_siblings += 3
        
        do_num_test()
        
        # delete with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_1, good_tag_1 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'admin delete' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tag_siblings -= 1
        expected_num_deleted_tag_siblings += 1
        
        do_num_test()
        
        # pend with regular
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_2, good_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'this is great' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_2a, good_tag_2a ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'this is great' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_pending_tag_siblings += 2
        expected_num_actionable_add_petitions += 1
        
        do_num_test()
        
        # approve and deny some with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_2, good_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'this is great' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_2a, good_tag_2a ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PEND, content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        # note no increase in num tags. _2 already known, _2a denied
        expected_num_tag_siblings += 1
        expected_num_pending_tag_siblings -= 2
        expected_num_actionable_add_petitions -= 1
        
        do_num_test()
        
        # petition with regular
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_2, good_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'this is bad 2' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_3, good_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_4, good_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'replacing 4' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_3, replacement_good_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_4, replacement_good_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'replacing 4' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_petitioned_tag_siblings += 3
        expected_num_pending_tag_siblings += 2
        expected_num_actionable_delete_petitions += 3
        
        do_num_test()
        
        # approve and deny some with admin
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_2, good_tag_2 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'this is bad 2' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_3, good_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_4, good_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PETITION, content, reason = 'replacing 4' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_3, replacement_good_tag_3 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason = 'replacing 3' )
        
        content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag_4, replacement_good_tag_4 ) )
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_DENY_PEND, content, reason = 'replacing 4' )
        
        self._write( 'update', self._tag_service_key, self._tag_service_account, client_to_server_update, HydrusData.GetNow() )
        
        expected_num_tags += 1
        expected_num_tag_siblings -= 1
        expected_num_deleted_tag_siblings += 2
        expected_num_petitioned_tag_siblings -= 3
        expected_num_pending_tag_siblings -= 2
        expected_num_actionable_delete_petitions -= 3
        
        do_num_test()
        
    
    def _test_init_server_admin( self ):
        
        result = self._read( 'access_key', HC.SERVER_ADMIN_KEY, b'init' )
        
        self.assertEqual( type( result ), bytes )
        self.assertEqual( len( result ), 32 )
        
        self._admin_access_key = result
        
        #
        
        result = self._read( 'account_key_from_access_key', HC.SERVER_ADMIN_KEY, self._admin_access_key )
        
        self.assertEqual( type( result ), bytes )
        self.assertEqual( len( result ), 32 )
        
        self._admin_account_key = result
        
        #
        
        result = self._read( 'account', HC.SERVER_ADMIN_KEY, self._admin_account_key )
        
        self.assertEqual( type( result ), HydrusNetwork.Account )
        self.assertEqual( result.GetAccountKey(), self._admin_account_key )
        
        self._admin_account = result
        
    
    def _test_service_creation( self ):
        
        self._tag_service_key = HydrusData.GenerateKey()
        self._file_service_key = HydrusData.GenerateKey()
        
        current_services = self._read( 'services' )
        
        self._tag_service = HydrusNetwork.GenerateService( self._tag_service_key, HC.TAG_REPOSITORY, 'tag repo', 100 )
        self._file_service = HydrusNetwork.GenerateService( self._file_service_key, HC.FILE_REPOSITORY, 'file repo', 101 )
        
        new_services = list( current_services )
        new_services.append( self._tag_service )
        new_services.append( self._file_service )
        
        service_keys_to_access_keys = self._write( 'services', self._admin_account, new_services )
        
        self.assertEqual( set( service_keys_to_access_keys.keys() ), { self._tag_service_key, self._file_service_key } )
        
        self._tag_service_access_key = service_keys_to_access_keys[ self._tag_service_key ]
        self._file_service_access_key = service_keys_to_access_keys[ self._file_service_key ]
        
        self._tag_service_account_key = self._read( 'account_key_from_access_key', self._tag_service_key, self._tag_service_access_key )
        self._file_service_account_key = self._read( 'account_key_from_access_key', self._file_service_key, self._file_service_access_key )
        
        self._tag_service_account = self._read( 'account', self._tag_service_key, self._tag_service_account_key )
        self._file_service_account = self._read( 'account', self._file_service_key, self._file_service_account_key )
        
        self.assertEqual( self._tag_service_account.GetAccountKey(), self._tag_service_account_key )
        self.assertEqual( self._file_service_account.GetAccountKey(), self._file_service_account_key )
        
    
    def test_server( self ):
        
        self._test_init_server_admin()
        
        self._test_service_creation()
        
        self._test_account_creation()
        
        self._test_account_modification()
        
        self._test_content_creation_and_service_info_counts_files()
        self._test_content_creation_and_service_info_counts_mappings()
        self._test_content_creation_and_service_info_counts_tag_parents()
        self._test_content_creation_and_service_info_counts_tag_siblings()
        
        self._test_account_fetching_from_content()
        

