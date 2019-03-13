from . import ClientConstants as CC
from . import ClientGUIManagement
from . import ClientNetworking
from . import ClientCaches
from . import ClientServices
import collections
from . import HydrusConstants as HC
import os
import unittest
from . import HydrusData
from . import HydrusGlobals as HG

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
        
        HG.test_controller.SetRead( 'services', services )
        
        services_manager = ClientCaches.ServicesManager( HG.client_controller )
        
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
        
        HG.test_controller.SetRead( 'services', services )
        
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
        
        undo_manager = ClientCaches.UndoManager( HG.client_controller )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        undo_manager.AddCommand( 'content_updates', command_1 )
        
        self.assertEqual( ( 'undo archive 1 files', None ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.AddCommand( 'content_updates', command_2 )
        
        self.assertEqual( ( 'undo inbox 1 files', None ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.Undo()
        
        self.assertEqual( ( 'undo archive 1 files', 'redo inbox 1 files' ), undo_manager.GetUndoRedoStrings() )
        
        self.assertEqual( HG.test_controller.GetWrite( 'content_updates' ), [ ( ( command_2_inverted, ), {} ) ] )
        
        undo_manager.Redo()
        
        self.assertEqual( HG.test_controller.GetWrite( 'content_updates' ), [ ( ( command_2, ), {} ) ] )
        
        self.assertEqual( ( 'undo inbox 1 files', None ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.Undo()
        
        self.assertEqual( HG.test_controller.GetWrite( 'content_updates' ), [ ( ( command_2_inverted, ), {} ) ] )
        
        undo_manager.Undo()
        
        self.assertEqual( HG.test_controller.GetWrite( 'content_updates' ), [ ( ( command_1_inverted, ), {} ) ] )
        
        self.assertEqual( ( None, 'redo archive 1 files' ), undo_manager.GetUndoRedoStrings() )
        
        undo_manager.AddCommand( 'content_updates', command_3 )
        
        self.assertEqual( ( 'undo archive 2 files', None ), undo_manager.GetUndoRedoStrings() )
        
    
