import unittest

from unittest import mock

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

from hydrus.client.networking import ClientNetworkingDomainSettings

class TestDomainSettings( unittest.TestCase ):
    
    def test_normal( self ):
        
        domain_settings = ClientNetworkingDomainSettings.DomainSettings()
        
        self.assertRaises( HydrusExceptions.DataMissing, domain_settings.GetSettingOrRaise, ClientNetworkingDomainSettings.DOMAIN_SETTING_MAX_ACTIVE_NETWORK_JOBS )
        self.assertRaises( NotImplementedError, domain_settings.GetSettingOrRaise, 'hello' )
        
        domain_settings.SetSetting( ClientNetworkingDomainSettings.DOMAIN_SETTING_MAX_ACTIVE_NETWORK_JOBS, 3 )
        
        self.assertEqual( domain_settings.GetSettingOrRaise( ClientNetworkingDomainSettings.DOMAIN_SETTING_MAX_ACTIVE_NETWORK_JOBS ), 3 )
        
        #
        
        domain_settings.SetSetting( ClientNetworkingDomainSettings.DOMAIN_SETTING_NETWORK_INFRASTRUCTURE_PROBLEMS_HALT_VELOCITY, [ 2, None ] )
        
        self.assertEqual( domain_settings.Duplicate().GetSettingOrRaise( ClientNetworkingDomainSettings.DOMAIN_SETTING_NETWORK_INFRASTRUCTURE_PROBLEMS_HALT_VELOCITY ), [ 2, None ] )
        
    

class TestDomainStatus( unittest.TestCase ):
    
    def test_normal( self ):
        
        domain_status = ClientNetworkingDomainSettings.DomainStatus()
        
        time_delta_s = 0.5
        time_delta_ms = int( time_delta_s * 1000 )
        now_ms = 100000
        older_than_limit_ms = now_ms - int( time_delta_ms * 1.2 )
        within_limit_ms = now_ms - int( time_delta_ms * 0.6 )
        much_later_ms = now_ms + 100000
        
        self.assertTrue( domain_status.IsStub() )
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = now_ms ):
            
            domain_status.CleanseOldRecords( time_delta_s )
            
        
        self.assertTrue( domain_status.IsStub() )
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = older_than_limit_ms ):
            
            domain_status.RegisterDomainEvent( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE )
            
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = now_ms ):
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s ), 0 )
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_SERVERSIDE_BANDWIDTH, time_delta_s ), 0 )
            
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = within_limit_ms ):
            
            domain_status.RegisterDomainEvent( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE )
            
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = now_ms ):
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s ), 1 )
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_SERVERSIDE_BANDWIDTH, time_delta_s ), 0 )
            
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = within_limit_ms + 5 ):
            
            domain_status.RegisterDomainEvent( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE )
            
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = now_ms ):
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s ), 2 )
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s * 2 ), 3 )
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s * 0.25 ), 0 )
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_SERVERSIDE_BANDWIDTH, time_delta_s ), 0 )
            
            domain_status.CleanseOldRecords( time_delta_s )
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s * 2 ), 2 )
            
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = much_later_ms ):
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_SERVERSIDE_BANDWIDTH, time_delta_s ), 0 )
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s ), 0 )
            
            domain_status.CleanseOldRecords( time_delta_s )
            
            self.assertEqual( domain_status.NumberOfEvents( ClientNetworkingDomainSettings.DOMAIN_EVENT_NETWORK_INFRASTRUCTURE, time_delta_s ), 0 )
            
            self.assertTrue( domain_status.IsStub() )
            
        
    
