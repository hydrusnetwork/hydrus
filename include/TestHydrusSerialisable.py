import ClientConstants as CC
import ClientData
import ClientDownloading
import ClientImporting
import ClientSearch
import HydrusConstants as HC
import HydrusData
import HydrusNetwork
import HydrusSerialisable
import os
import unittest
import wx

class TestSerialisables( unittest.TestCase ):
    
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
            
        
    
    def test_SERIALISABLE_TYPE_SUBSCRIPTION( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj.GetName(), dupe_obj.GetName() )
            
            self.assertEqual( obj._gallery_identifier, dupe_obj._gallery_identifier )
            self.assertEqual( obj._gallery_stream_identifiers, dupe_obj._gallery_stream_identifiers )
            self.assertEqual( obj._query, dupe_obj._query )
            self.assertEqual( obj._period, dupe_obj._period )
            self.assertEqual( obj._get_tags_if_url_known_and_file_redundant, dupe_obj._get_tags_if_url_known_and_file_redundant )
            self.assertEqual( obj._initial_file_limit, dupe_obj._initial_file_limit )
            self.assertEqual( obj._periodic_file_limit, dupe_obj._periodic_file_limit )
            self.assertEqual( obj._paused, dupe_obj._paused )
            
            self.assertEqual( obj._import_file_options.GetSerialisableTuple(), dupe_obj._import_file_options.GetSerialisableTuple() )
            self.assertEqual( obj._import_tag_options.GetSerialisableTuple(), dupe_obj._import_tag_options.GetSerialisableTuple() )
            
            self.assertEqual( obj._last_checked, dupe_obj._last_checked )
            self.assertEqual( obj._last_error, dupe_obj._last_error )
            self.assertEqual( obj._check_now, dupe_obj._check_now )
            
            self.assertEqual( obj._seed_cache.GetSerialisableTuple(), dupe_obj._seed_cache.GetSerialisableTuple() )
            
        
        sub = ClientImporting.Subscription( 'test sub' )
        
        self._dump_and_load_and_test( sub, test )
        
        gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU, 'gelbooru' )
        gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( gallery_identifier )
        query = 'test query'
        period = 86400 * 7
        get_tags_if_url_known_and_file_redundant = True
        initial_file_limit = 100
        periodic_file_limit = 50
        paused = False
        
        import_file_options = ClientData.ImportFileOptions( automatic_archive = False, exclude_deleted = True, min_size = 8 * 1024, min_resolution = [ 25, 25 ] )
        import_tag_options = ClientData.ImportTagOptions( service_keys_to_namespaces = { HydrusData.GenerateKey() : { 'series', '' } }, service_keys_to_explicit_tags = { HydrusData.GenerateKey() : { 'test explicit tag', 'and another' } } )
        
        last_checked = HydrusData.GetNow() - 3600
        last_error = HydrusData.GetNow() - 86400 * 20
        check_now = False
        seed_cache = ClientImporting.SeedCache()
        
        seed_cache.AddSeed( 'http://exampleurl.com/image/123456' )
        
        sub.SetTuple( gallery_identifier, gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options, last_checked, last_error, check_now, seed_cache )
        
        self.assertEqual( sub.GetGalleryIdentifier(), gallery_identifier )
        self.assertEqual( sub.GetImportTagOptions(), import_tag_options )
        self.assertEqual( sub.GetQuery(), query )
        self.assertEqual( sub.GetSeedCache(), seed_cache )
        
        self.assertEqual( sub._paused, False )
        sub.PauseResume()
        self.assertEqual( sub._paused, True )
        sub.PauseResume()
        self.assertEqual( sub._paused, False )
        
        self._dump_and_load_and_test( sub, test )
        
    
