import ClientConstants as CC
import ClientData
import ClientSearch
import HydrusConstants as HC
import HydrusData
import HydrusNetwork
import HydrusSerialisable
import os
import unittest
import wx

class TestServer( unittest.TestCase ):
    
    def _dump_and_load_and_test( self, obj, test_func ):
        
        serialisable_tuple = obj.GetSerialisableTuple()
        
        self.assertIsInstance( serialisable_tuple, tuple )
        
        if isinstance( obj, HydrusSerialisable.SerialisableBaseNamed ):
            
            ( serialisable_type, name, version, serialisable_info ) = serialisable_tuple
            
        elif isinstance( obj, HydrusSerialisable.SerialisableBase ):
            
            ( serialisable_type, version, serialisable_info ) = serialisable_tuple
            
        
        self.assertEqual( serialisable_type, obj.SERIALISABLE_TYPE )
        self.assertEqual( version, obj.SERIALISABLE_VERSION )
        
        dupe_obj = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tuple )
        
        self.assertIsNot( obj, dupe_obj )
        
        test_func( obj, dupe_obj )
        
        #
        
        json_string = obj.DumpToString()
        
        self.assertIsInstance( json_string, str )
        
        dupe_obj = HydrusSerialisable.CreateFromString( json_string )
        
        self.assertIsNot( obj, dupe_obj )
        
        test_func( obj, dupe_obj )
        
        #
        
        network_string = obj.DumpToNetworkString()
        
        self.assertIsInstance( network_string, str )
        
        dupe_obj = HydrusSerialisable.CreateFromNetworkString( network_string )
        
        self.assertIsNot( obj, dupe_obj )
        
        test_func( obj, dupe_obj )
        
    
    def test_basics( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( len( obj.items() ), len( dupe_obj.items() ) )
            
            for ( key, value ) in obj.items():
                
                self.assertEqual( value, dupe_obj[ key ] )
                
            
        
        #
        
        d = HydrusSerialisable.SerialisableDictionary()
        
        d[ 1 ] = 2
        d[ 3 ] = 'test1'
        
        d[ 'test2' ] = 4
        d[ 'test3' ] = 5
        
        d[ 6 ] = HydrusSerialisable.SerialisableDictionary( { i : 'test' + str( i ) for i in range( 20 ) } )
        d[ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'test pred 1' ) ] = 56
        
        d[ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'test pred 2' ) ] = HydrusSerialisable.SerialisableList( [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'test' + str( i ) ) for i in range( 10 ) ] )
        
        self.assertEqual( len( d.keys() ), 7 )
        
        for ( key, value ) in d.items():
            
            self.assertEqual( d[ key ], value )
            
        
        self._dump_and_load_and_test( d, test )
        
        #
        
        db = HydrusSerialisable.SerialisableBytesDictionary()
        
        db[ HydrusData.GenerateKey() ] = HydrusData.GenerateKey()
        db[ HydrusData.GenerateKey() ] = [ HydrusData.GenerateKey() for i in range( 10 ) ]
        db[ 1 ] = HydrusData.GenerateKey()
        db[ 2 ] = [ HydrusData.GenerateKey() for i in range( 10 ) ]
        
        self.assertEqual( len( db.keys() ), 4 )
        
        for ( key, value ) in db.items():
            
            self.assertEqual( db[ key ], value )
            
        
        self._dump_and_load_and_test( db, test )
        
    
    def test_SERIALISABLE_TYPE_SHORTCUTS( self ):
        
        def test( obj, dupe_obj ):
            
            for ( ( modifier, key ), action ) in obj.IterateKeyboardShortcuts():
                
                self.assertEqual( dupe_obj.GetKeyboardAction( modifier, key ), action )
                
            
            for ( ( modifier, mouse_button ), action ) in obj.IterateMouseShortcuts():
                
                self.assertEqual( dupe_obj.GetMouseAction( modifier, mouse_button ), action )
                
            
        
        action_1 = ( HydrusData.GenerateKey(), u'test unicode tag\u2026' )
        action_2 = ( HydrusData.GenerateKey(), 0.5 )
        action_3 = ( None, 'archive' )
        
        shortcuts = ClientData.Shortcuts( 'test' )
        
        shortcuts.SetKeyboardAction( wx.ACCEL_NORMAL, wx.WXK_NUMPAD1, action_1 )
        shortcuts.SetKeyboardAction( wx.ACCEL_SHIFT, wx.WXK_END, action_2 )
        shortcuts.SetKeyboardAction( wx.ACCEL_CTRL, ord( 'R' ), action_3 )
        
        shortcuts.SetMouseAction( wx.ACCEL_NORMAL, wx.MOUSE_BTN_LEFT, action_1 )
        shortcuts.SetMouseAction( wx.ACCEL_SHIFT, wx.MOUSE_BTN_MIDDLE, action_2 )
        shortcuts.SetMouseAction( wx.ACCEL_CTRL, wx.MOUSE_BTN_RIGHT, action_3 )
        shortcuts.SetMouseAction( wx.ACCEL_ALT, wx.MOUSE_WHEEL_VERTICAL, action_3 )
        
        k_a = [ item for item in shortcuts.IterateKeyboardShortcuts() ]
        
        self.assertEqual( len( k_a ), 3 )
        
        for ( ( modifier, key ), action ) in k_a:
            
            self.assertEqual( shortcuts.GetKeyboardAction( modifier, key ), action )
            
        
        m_a = [ item for item in shortcuts.IterateMouseShortcuts() ]
        
        self.assertEqual( len( m_a ), 4 )
        
        for ( ( modifier, mouse_button ), action ) in m_a:
            
            self.assertEqual( shortcuts.GetMouseAction( modifier, mouse_button ), action )
            
        
