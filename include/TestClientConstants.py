import ClientConstants as CC
import ClientData
import ClientGUIManagement
import ClientGUIDialogsManage
import ClientCaches
import ClientServices
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest
import HydrusData
import HydrusGlobals

class TestFunctions( unittest.TestCase ):
    
    def test_multipart( self ):
        
        hash = '5a1ba880a043e6207dca5f5407089fb0a0b0a588c8a6cd6a2807d173f59223d9'.decode( 'hex' )
        
        fields = []
        
        fields.append( ( 'sub', CC.FIELD_TEXT, 'subject' ) )
        fields.append( ( 'com', CC.FIELD_COMMENT, u'\u269COP is a fag' ) )
        fields.append( ( 'pass', CC.FIELD_PASSWORD, '123456' ) )
        fields.append( ( 'recaptcha', CC.FIELD_VERIFICATION_RECAPTCHA, 'reticulating splines' ) )
        fields.append( ( 'resto', CC.FIELD_THREAD_ID, '1000000' ) )
        fields.append( ( 'spoiler/on', CC.FIELD_CHECKBOX, True ) )
        fields.append( ( 'upfile', CC.FIELD_FILE, ( hash, HC.IMAGE_GIF, TestConstants.tinest_gif ) ) )
        
        result = ClientGUIManagement.GenerateDumpMultipartFormDataCTAndBody( fields )
        
        expected_result = ('multipart/form-data; boundary=----------AaB03x', '------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="sub"\r\n\r\nsubject\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="com"\r\n\r\n\xe2\x9a\x9cOP is a fag\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="pass"\r\n\r\n123456\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="recaptcha"\r\n\r\nreticulating splines\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="resto"\r\n\r\n1000000\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="spoiler"\r\n\r\non\r\n------------AaB03x\r\nContent-Type: image/gif\r\nContent-Disposition: form-data; name="upfile"; filename="5a1ba880a043e6207dca5f5407089fb0a0b0a588c8a6cd6a2807d173f59223d9.gif"\r\n\r\nGIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;\r\n------------AaB03x--\r\n')
        
        self.assertEqual( result, expected_result )
        
        #
        
        fields = {}
        
        fields[ 'act' ] = 'do_login'
        fields[ 'id' ] = 'token'
        fields[ 'pin' ] = 'pin'
        fields[ 'long_login' ] = 'yes'
        fields[ 'random_unicode' ] = u'\u269C'
        
        result = ClientGUIDialogsManage.GenerateMultipartFormDataCTAndBodyFromDict( fields )
        
        expected_result = ('multipart/form-data; boundary=----------AaB03x', '------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="long_login"\r\n\r\nyes\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="random_unicode"\r\n\r\n\xe2\x9a\x9c\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="id"\r\n\r\ntoken\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="pin"\r\n\r\npin\r\n------------AaB03x\r\nContent-Type: application/octet-stream\r\nContent-Disposition: form-data; name="act"\r\n\r\ndo_login\r\n------------AaB03x--\r\n')
        
        self.assertEqual( result, expected_result )
        
    
class TestManagers( unittest.TestCase ):
    
    def test_services( self ):
        
        def test_service( service, key, service_type, name ):
            
            self.assertEqual( service.GetServiceKey(), key )
            self.assertEqual( service.GetServiceType(), service_type )
            self.assertEqual( service.GetName(), name )
            
        
        repo_key = HydrusData.GenerateKey()
        repo_type = HC.TAG_REPOSITORY
        repo_name = 'test tag repo'
        
        repo = ClientServices.GenerateService( repo_key, repo_type, repo_name )
        
        other_key = HydrusData.GenerateKey()
        
        other = ClientServices.GenerateService( other_key, HC.LOCAL_BOORU, 'booru' )
        
        services = []
        
        services.append( repo )
        services.append( other )
        
        HydrusGlobals.test_controller.SetRead( 'services', services )
        
        services_manager = ClientCaches.ServicesManager( HydrusGlobals.client_controller )
        
        #
        
        service = services_manager.GetService( repo_key )
        
        test_service( service, repo_key, repo_type, repo_name )
        
        service = services_manager.GetService( other_key )
        
        #
        
        services = services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        self.assertEqual( len( services ), 1 )
        
        self.assertEqual( services[0].GetServiceKey(), repo_key )
        
        #
        
        services = []
        
        services.append( repo )
        
        HydrusGlobals.test_controller.SetRead( 'services', services )
        
        services_manager.RefreshServices()
        
        self.assertRaises( Exception, services_manager.GetService, other_key )
        
    
    def test_undo( self ):
        
        hash_1 = HydrusData.GenerateKey()
        hash_2 = HydrusData.GenerateKey()
        hash_3 = HydrusData.GenerateKey()
        
        command_1 = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, { hash_1 } ) ] }
        command_2 = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { hash_2 } ) ] }
        command_3 = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, { hash_1, hash_3 } ) ] }
        
        command_1_inverted = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { hash_1 } ) ] }
        command_2_inverted = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, { hash_2 } ) ] }
        
        undo_manager = ClientCaches.UndoManager( HydrusGlobals.client_controller )
        
        #
        
        undo_manager.AddCommand( 'content_updates', command_1 )
        
        self.assertEqual( ( u'undo archive 1 files', None ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.AddCommand( 'content_updates', command_2 )
        
        self.assertEqual( ( u'undo inbox 1 files', None ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.Undo()
        
        self.assertEqual( ( u'undo archive 1 files', u'redo inbox 1 files' ), undo_manager.GetUndoRedoStrings() )
        
        self.assertEqual( HydrusGlobals.test_controller.GetWrite( 'content_updates' ), [ ( ( command_2_inverted, ), {} ) ] )
        
        undo_manager.Redo()
        
        self.assertEqual( HydrusGlobals.test_controller.GetWrite( 'content_updates' ), [ ( ( command_2, ), {} ) ] )
        
        self.assertEqual( ( u'undo inbox 1 files', None ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.Undo()
        
        self.assertEqual( HydrusGlobals.test_controller.GetWrite( 'content_updates' ), [ ( ( command_2_inverted, ), {} ) ] )
        
        undo_manager.Undo()
        
        self.assertEqual( HydrusGlobals.test_controller.GetWrite( 'content_updates' ), [ ( ( command_1_inverted, ), {} ) ] )
        
        self.assertEqual( ( None, u'redo archive 1 files' ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.AddCommand( 'content_updates', command_3 )
        
        self.assertEqual( ( u'undo archive 2 files', None ), undo_manager.GetUndoRedoStrings() )
        
    
