import ClientCaches
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientImporting
import ClientMedia
import ClientRatings
import ClientSearch
import HydrusConstants as HC
import HydrusData
import HydrusNetwork
import HydrusSerialisable
import TestConstants as TC
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
        
    
    def test_SERIALISABLE_TYPE_APPLICATION_COMMAND( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj.GetCommandType(), dupe_obj.GetCommandType() )
            
            self.assertEqual( obj.GetData(), dupe_obj.GetData() )
            
        
        acs = []
        
        acs.append( ( ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_file' ), 'archive_file' ) )
        acs.append( ( ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( HydrusData.GenerateKey(), HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) ), 'flip on/off mappings "test" for unknown service!' ) )
        acs.append( ( ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) ), 'flip on/off mappings "test" for local tags' ) )
        acs.append( ( ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( HydrusData.GenerateKey(), HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_SET, 0.4 ) ), 'set ratings "0.4" for unknown service!' ) )
        
        for ( ac, s ) in acs:
            
            self._dump_and_load_and_test( ac, test )
            
            self.assertEqual( ac.ToString(), s )
            
        
    
    def test_SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj.ToTuple(), dupe_obj.ToTuple() )
            
        
        duplicate_action_options_delete_and_move = ClientData.DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ), ( TC.LOCAL_RATING_LIKE_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ), ( TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ) ], True )
        duplicate_action_options_copy = ClientData.DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_COPY ), ( TC.LOCAL_RATING_LIKE_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_COPY ), ( TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_COPY ) ], False )
        duplicate_action_options_merge = ClientData.DuplicateActionOptions( [ ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ), ( TC.LOCAL_RATING_LIKE_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ), ( TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ) ], False )
        
        inbox = True
        size = 40960
        mime = HC.IMAGE_JPEG
        width = 640
        height = 480
        duration = None
        num_frames = None
        num_words = None
        
        local_locations_manager = ClientMedia.LocationsManager( { CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY }, set(), set(), set() )
        trash_locations_manager = ClientMedia.LocationsManager( { CC.TRASH_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY }, set(), set(), set() )
        deleted_locations_manager = ClientMedia.LocationsManager( set(), { CC.COMBINED_LOCAL_FILE_SERVICE_KEY }, set(), set() )
        
        # duplicate to generate proper dicts
        
        one_tags_manager = ClientMedia.TagsManager( { CC.LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'one' } } } ).Duplicate()
        two_tags_manager = ClientMedia.TagsManager( { CC.LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'two' } } } ).Duplicate()
        substantial_tags_manager = ClientMedia.TagsManager( { CC.LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'test tag', 'series:namespaced test tag' } } } ).Duplicate()
        empty_tags_manager = ClientMedia.TagsManager( {} ).Duplicate()
        
        one_ratings_manager = ClientRatings.RatingsManager( { TC.LOCAL_RATING_LIKE_SERVICE_KEY : 1.0, TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY : 0.8 } )
        two_ratings_manager = ClientRatings.RatingsManager( { TC.LOCAL_RATING_LIKE_SERVICE_KEY : 0.0, TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY : 0.6 } )
        substantial_ratings_manager = ClientRatings.RatingsManager( { TC.LOCAL_RATING_LIKE_SERVICE_KEY : 1.0, TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY : 0.8 } )
        empty_ratings_manager = ClientRatings.RatingsManager( {} )
        
        local_hash_has_values = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( local_hash_has_values, inbox, size, mime, width, height, duration, num_frames, num_words, substantial_tags_manager, local_locations_manager, substantial_ratings_manager ) )
        
        local_media_has_values = ClientMedia.MediaSingleton( media_result )
        
        other_local_hash_has_values = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( other_local_hash_has_values, inbox, size, mime, width, height, duration, num_frames, num_words, substantial_tags_manager, local_locations_manager, substantial_ratings_manager ) )
        
        other_local_media_has_values = ClientMedia.MediaSingleton( media_result )
        
        local_hash_empty = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( local_hash_empty, inbox, size, mime, width, height, duration, num_frames, num_words, empty_tags_manager, local_locations_manager, empty_ratings_manager ) )
        
        local_media_empty = ClientMedia.MediaSingleton( media_result )
        
        trashed_hash_empty = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( trashed_hash_empty, inbox, size, mime, width, height, duration, num_frames, num_words, empty_tags_manager, trash_locations_manager, empty_ratings_manager ) )
        
        trashed_media_empty = ClientMedia.MediaSingleton( media_result )
        
        deleted_hash_empty = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( deleted_hash_empty, inbox, size, mime, width, height, duration, num_frames, num_words, empty_tags_manager, deleted_locations_manager, empty_ratings_manager ) )
        
        deleted_media_empty = ClientMedia.MediaSingleton( media_result )
        
        one_hash = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( one_hash, inbox, size, mime, width, height, duration, num_frames, num_words, one_tags_manager, local_locations_manager, one_ratings_manager ) )
        
        one_media = ClientMedia.MediaSingleton( media_result )
        
        two_hash = HydrusData.GenerateKey()
        
        media_result = ClientMedia.MediaResult( ( two_hash, inbox, size, mime, width, height, duration, num_frames, num_words, two_tags_manager, local_locations_manager, two_ratings_manager ) )
        
        two_media = ClientMedia.MediaSingleton( media_result )
        
        #
        
        self._dump_and_load_and_test( duplicate_action_options_delete_and_move, test )
        self._dump_and_load_and_test( duplicate_action_options_copy, test )
        self._dump_and_load_and_test( duplicate_action_options_merge, test )
        
        #
        
        def assertSCUEqual( one, two ):
            
            self.assertEqual( TC.ConvertServiceKeysToContentUpdatesToComparable( one ), TC.ConvertServiceKeysToContentUpdatesToComparable( two ) )
            
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, local_media_empty )
        
        scu = {}
        
        scu[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { local_hash_empty } ) ]
        
        assertSCUEqual( result[0], scu )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, trashed_media_empty )
        
        scu = {}
        
        scu[ CC.TRASH_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { trashed_hash_empty } ) ]
        
        assertSCUEqual( result[0], scu )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, deleted_media_empty )
        
        self.assertEqual( result, [] )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, other_local_media_has_values )
        
        scu = {}
        
        scu[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test tag', { other_local_hash_has_values } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'series:namespaced test tag', { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        
        assertSCUEqual( result[0], scu )
        
        scu = {}
        
        scu[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { other_local_hash_has_values } ) ]
        
        assertSCUEqual( result[1], scu )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_empty, other_local_media_has_values )
        
        scu = {}
        
        scu[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test tag', { other_local_hash_has_values } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'series:namespaced test tag', { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        
        assertSCUEqual( result[0], scu )
        
        scu = {}
        
        scu[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { other_local_hash_has_values } ) ]
        
        assertSCUEqual( result[1], scu )
        
        #
        #
        
        result = duplicate_action_options_copy.ProcessPairIntoContentUpdates( local_media_has_values, local_media_empty )
        
        self.assertEqual( result, [] )
        
        #
        
        result = duplicate_action_options_copy.ProcessPairIntoContentUpdates( local_media_empty, other_local_media_has_values )
        
        scu = {}
        
        scu[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ) ]
        
        assertSCUEqual( result[0], scu )
        
        #
        #
        
        result = duplicate_action_options_merge.ProcessPairIntoContentUpdates( local_media_has_values, local_media_empty )
        
        scu = {}
        
        scu[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ) ]
        
        assertSCUEqual( result[0], scu )
        
        #
        
        result = duplicate_action_options_merge.ProcessPairIntoContentUpdates( local_media_empty, other_local_media_has_values )
        
        scu = {}
        
        scu[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ) ]
        
        assertSCUEqual( result[0], scu )
        
        #
        
        result = duplicate_action_options_merge.ProcessPairIntoContentUpdates( one_media, two_media )
        
        scu = {}
        
        scu[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'one', { two_hash } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'two', { one_hash } ) ) ]
        
        assertSCUEqual( result[0], scu )
        
    
    def test_SERIALISABLE_TYPE_SHORTCUT( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( dupe_obj.__hash__(), ( dupe_obj._shortcut_type, dupe_obj._shortcut_key, tuple( dupe_obj._modifiers ) ).__hash__() )
            
            self.assertEqual( obj, dupe_obj )
            
        
        shortcuts = []
        
        shortcuts.append( ( ClientData.Shortcut(), 'f7' ) )
        
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SPACE, [] ), 'space' ) )
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'a' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+a' ) )
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'A' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+a' ) )
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_HOME, [ CC.SHORTCUT_MODIFIER_ALT, CC.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+alt+home' ) )
        
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] ), 'left-click' ) )
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_MIDDLE, [ CC.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+middle-click' ) )
        shortcuts.append( ( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_DOWN, [ CC.SHORTCUT_MODIFIER_ALT, CC.SHORTCUT_MODIFIER_SHIFT ] ), 'alt+shift+scroll down' ) )
        
        for ( shortcut, s ) in shortcuts:
            
            self._dump_and_load_and_test( shortcut, test )
            
            self.assertEqual( shortcut.ToString(), s )
            
        
    
    def test_SERIALISABLE_TYPE_SHORTCUTS( self ):
        
        def test( obj, dupe_obj ):
            
            for ( shortcut, command ) in obj:
                
                self.assertEqual( dupe_obj.GetCommand( shortcut ).GetData(), command.GetData() )
                
            
        
        default_shortcuts = ClientDefaults.GetDefaultShortcuts()
        
        for shortcuts in default_shortcuts:
            
            self._dump_and_load_and_test( shortcuts, test )
            
        
        command_1 = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_file' )
        command_2 = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( HydrusData.GenerateKey(), HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) )
        command_3 = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) )
        
        k_shortcut_1 = ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SPACE, [] )
        k_shortcut_2 = ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'a' ), [ CC.SHORTCUT_MODIFIER_CTRL ] )
        k_shortcut_3 = ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'A' ), [ CC.SHORTCUT_MODIFIER_CTRL ] )
        k_shortcut_4 = ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_HOME, [ CC.SHORTCUT_MODIFIER_ALT, CC.SHORTCUT_MODIFIER_CTRL ] )
        
        m_shortcut_1 = ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] )
        m_shortcut_2 = ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_MIDDLE, [ CC.SHORTCUT_MODIFIER_CTRL ] )
        m_shortcut_3 = ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_DOWN, [ CC.SHORTCUT_MODIFIER_ALT, CC.SHORTCUT_MODIFIER_SHIFT ] )
        
        shortcuts = ClientData.Shortcuts( 'test' )
        
        shortcuts.SetCommand( k_shortcut_1, command_1 )
        shortcuts.SetCommand( k_shortcut_2, command_2 )
        shortcuts.SetCommand( k_shortcut_3, command_2 )
        shortcuts.SetCommand( k_shortcut_4, command_3 )
        
        shortcuts.SetCommand( m_shortcut_1, command_1 )
        shortcuts.SetCommand( m_shortcut_2, command_2 )
        shortcuts.SetCommand( m_shortcut_3, command_3 )
        
        self._dump_and_load_and_test( shortcuts, test )
        
        self.assertEqual( shortcuts.GetCommand( k_shortcut_1 ).GetData(), command_1.GetData() )
        
        shortcuts.SetCommand( k_shortcut_1, command_3 )
        
        self.assertEqual( shortcuts.GetCommand( k_shortcut_1 ).GetData(), command_3.GetData() )
        
    
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
        
    
