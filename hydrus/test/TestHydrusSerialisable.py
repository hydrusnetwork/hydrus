import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientDefaults
from hydrus.client import ClientDuplicates
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.importing import ClientImportSubscriptions
from hydrus.client.importing import ClientImportSubscriptionQuery
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

from hydrus.test import TestController as TC

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
        
        network_bytes = obj.DumpToNetworkBytes()
        
        self.assertIsInstance( network_bytes, bytes )
        
        dupe_obj = HydrusSerialisable.CreateFromNetworkBytes( network_bytes )
        
        self.assertIsNot( obj, dupe_obj )
        
        test_func( obj, dupe_obj )
        
    
    def test_basics( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( len( list(obj.items()) ), len( list(dupe_obj.items()) ) )
            
            for ( key, value ) in list(obj.items()):
                
                self.assertEqual( value, dupe_obj[ key ] )
                
            
        
        #
        
        d = HydrusSerialisable.SerialisableDictionary()
        
        d[ 1 ] = 2
        d[ 3 ] = 'test1'
        
        d[ 'test2' ] = 4
        d[ 'test3' ] = 5
        
        d[ 6 ] = HydrusSerialisable.SerialisableDictionary( { i : 'test' + str( i ) for i in range( 20 ) } )
        d[ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'test pred 1' ) ] = 56
        
        d[ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'test pred 2' ) ] = HydrusSerialisable.SerialisableList( [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'test' + str( i ) ) for i in range( 10 ) ] )
        
        self.assertEqual( len( list(d.keys()) ), 7 )
        
        for ( key, value ) in list(d.items()):
            
            self.assertEqual( d[ key ], value )
            
        
        self._dump_and_load_and_test( d, test )
        
        #
        
        db = HydrusSerialisable.SerialisableBytesDictionary()
        
        db[ HydrusData.GenerateKey() ] = HydrusData.GenerateKey()
        db[ HydrusData.GenerateKey() ] = [ HydrusData.GenerateKey() for i in range( 10 ) ]
        db[ 1 ] = HydrusData.GenerateKey()
        db[ 2 ] = [ HydrusData.GenerateKey() for i in range( 10 ) ]
        
        self.assertEqual( len( list(db.keys()) ), 4 )
        
        for ( key, value ) in list(db.items()):
            
            self.assertEqual( db[ key ], value )
            
        
        self._dump_and_load_and_test( db, test )
        
    
    def test_SERIALISABLE_TYPE_APPLICATION_COMMAND( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj.GetCommandType(), dupe_obj.GetCommandType() )
            
            self.assertSequenceEqual( tuple( obj._data ), tuple( dupe_obj._data ) )
            
        
        acs = []
        
        acs.append( ( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE ), 'archive file' ) )
        acs.append( ( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MEDIA_SEEK_DELTA, simple_data = ( -1, 2500 ) ), 'seek media (back 2.5 seconds)' ) )
        acs.append( ( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MEDIA_SEEK_DELTA, simple_data = ( 1, 800 ) ), 'seek media (forwards 800 milliseconds)' ) )
        acs.append( ( CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( HydrusData.GenerateKey(), HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) ), 'flip on/off mappings "test" for unknown service!' ) )
        acs.append( ( CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) ), 'flip on/off mappings "test" for my tags' ) )
        acs.append( ( CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( HydrusData.GenerateKey(), HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_SET, 0.4 ) ), 'set ratings uncertain rating, "0.4" for unknown service!' ) )
        
        for ( ac, s ) in acs:
            
            self._dump_and_load_and_test( ac, test )
            
            self.assertEqual( ac.ToString(), s )
            
        
    
    def test_SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj.ToTuple(), dupe_obj.ToTuple() )
            
        
        duplicate_action_options_delete_and_move = ClientDuplicates.DuplicateActionOptions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE, HydrusTags.TagFilter() ) ], [ ( TC.LOCAL_RATING_LIKE_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ), ( TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_MOVE ) ] )
        duplicate_action_options_copy = ClientDuplicates.DuplicateActionOptions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_COPY, HydrusTags.TagFilter() ) ], [ ( TC.LOCAL_RATING_LIKE_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_COPY ), ( TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_COPY ) ] )
        duplicate_action_options_merge = ClientDuplicates.DuplicateActionOptions( [ ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE, HydrusTags.TagFilter() ) ], [ ( TC.LOCAL_RATING_LIKE_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ), ( TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ) ] )
        
        inbox = True
        size = 40960
        mime = HC.IMAGE_JPEG
        width = 640
        height = 480
        duration = None
        num_frames = None
        has_audio = False
        num_words = None
        
        local_locations_manager = ClientMediaManagers.LocationsManager( { CC.LOCAL_FILE_SERVICE_KEY : 123, CC.COMBINED_LOCAL_FILE_SERVICE_KEY : 123 }, dict(), set(), set(), inbox )
        trash_locations_manager = ClientMediaManagers.LocationsManager( { CC.TRASH_SERVICE_KEY : 123, CC.COMBINED_LOCAL_FILE_SERVICE_KEY : 12 }, dict(), set(), set(), inbox )
        deleted_locations_manager = ClientMediaManagers.LocationsManager( dict(), { CC.LOCAL_FILE_SERVICE_KEY : 120, CC.COMBINED_LOCAL_FILE_SERVICE_KEY : 123 }, set(), set(), inbox )
        
        # duplicate to generate proper dicts
        
        one_tags_manager = ClientMediaManagers.TagsManager( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'one' } } }, { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'one' } } } ).Duplicate()
        two_tags_manager = ClientMediaManagers.TagsManager( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'two' } } }, { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'two' } } } ).Duplicate()
        substantial_tags_manager = ClientMediaManagers.TagsManager( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'test tag', 'series:namespaced test tag' } } }, { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'test tag', 'series:namespaced test tag' } } } ).Duplicate()
        empty_tags_manager = ClientMediaManagers.TagsManager( {}, {} ).Duplicate()
        
        one_ratings_manager = ClientMediaManagers.RatingsManager( { TC.LOCAL_RATING_LIKE_SERVICE_KEY : 1.0, TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY : 0.8 } )
        two_ratings_manager = ClientMediaManagers.RatingsManager( { TC.LOCAL_RATING_LIKE_SERVICE_KEY : 0.0, TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY : 0.6 } )
        substantial_ratings_manager = ClientMediaManagers.RatingsManager( { TC.LOCAL_RATING_LIKE_SERVICE_KEY : 1.0, TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY : 0.8 } )
        empty_ratings_manager = ClientMediaManagers.RatingsManager( {} )
        
        notes_manager = ClientMediaManagers.NotesManager( {} )
        
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager()
        
        #
        
        local_hash_has_values = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 1, local_hash_has_values, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, substantial_tags_manager, local_locations_manager, substantial_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        local_media_has_values = ClientMedia.MediaSingleton( media_result )
        
        #
        
        other_local_hash_has_values = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 2, other_local_hash_has_values, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, substantial_tags_manager, local_locations_manager, substantial_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        other_local_media_has_values = ClientMedia.MediaSingleton( media_result )
        
        #
        
        local_hash_empty = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 3, local_hash_empty, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, empty_tags_manager, local_locations_manager, empty_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        local_media_empty = ClientMedia.MediaSingleton( media_result )
        
        #
        
        trashed_hash_empty = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 4, trashed_hash_empty, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, empty_tags_manager, trash_locations_manager, empty_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        trashed_media_empty = ClientMedia.MediaSingleton( media_result )
        
        #
        
        deleted_hash_empty = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 5, deleted_hash_empty, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, empty_tags_manager, deleted_locations_manager, empty_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        deleted_media_empty = ClientMedia.MediaSingleton( media_result )
        
        #
        
        one_hash = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 6, one_hash, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, one_tags_manager, local_locations_manager, one_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        one_media = ClientMedia.MediaSingleton( media_result )
        
        #
        
        two_hash = HydrusData.GenerateKey()
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 7, two_hash, size, mime, width, height, duration, num_frames, has_audio, num_words )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, two_tags_manager, local_locations_manager, two_ratings_manager, notes_manager, file_viewing_stats_manager )
        
        two_media = ClientMedia.MediaSingleton( media_result )
        
        #
        
        self._dump_and_load_and_test( duplicate_action_options_delete_and_move, test )
        self._dump_and_load_and_test( duplicate_action_options_copy, test )
        self._dump_and_load_and_test( duplicate_action_options_merge, test )
        
        #
        
        def assertSCUEqual( one, two ):
            
            self.assertEqual( TC.ConvertServiceKeysToContentUpdatesToComparable( one ), TC.ConvertServiceKeysToContentUpdatesToComparable( two ) )
            
        
        file_deletion_reason = 'test delete'
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, local_media_empty, delete_second = True, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { local_hash_empty }, reason = file_deletion_reason ) ]
        
        assertSCUEqual( result, scu )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, trashed_media_empty, delete_second = True, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { trashed_hash_empty }, reason = file_deletion_reason ) ]
        
        assertSCUEqual( result, scu )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, deleted_media_empty, delete_second = True, file_deletion_reason = file_deletion_reason )
        
        self.assertEqual( result, {} )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_has_values, other_local_media_has_values, delete_second = True, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test tag', { other_local_hash_has_values } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'series:namespaced test tag', { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        scu[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { other_local_hash_has_values }, reason = file_deletion_reason ) ]
        
        assertSCUEqual( result, scu )
        
        #
        
        result = duplicate_action_options_delete_and_move.ProcessPairIntoContentUpdates( local_media_empty, other_local_media_has_values, delete_second = True, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test tag', { other_local_hash_has_values } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'series:namespaced test tag', { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { other_local_hash_has_values } ) ) ]
        scu[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { other_local_hash_has_values }, reason = file_deletion_reason ) ]
        
        assertSCUEqual( result, scu )
        
        #
        #
        
        result = duplicate_action_options_copy.ProcessPairIntoContentUpdates( local_media_has_values, local_media_empty, file_deletion_reason = file_deletion_reason )
        
        self.assertEqual( result, {} )
        
        #
        
        result = duplicate_action_options_copy.ProcessPairIntoContentUpdates( local_media_empty, other_local_media_has_values, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ) ]
        
        assertSCUEqual( result, scu )
        
        #
        #
        
        result = duplicate_action_options_merge.ProcessPairIntoContentUpdates( local_media_has_values, local_media_empty, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ) ]
        
        assertSCUEqual( result, scu )
        
        #
        
        result = duplicate_action_options_merge.ProcessPairIntoContentUpdates( local_media_empty, other_local_media_has_values, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test tag', { local_hash_empty } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:namespaced test tag', { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { local_hash_empty } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { local_hash_empty } ) ) ]
        
        assertSCUEqual( result, scu )
        
        #
        
        result = duplicate_action_options_merge.ProcessPairIntoContentUpdates( one_media, two_media, file_deletion_reason = file_deletion_reason )
        
        scu = {}
        
        scu[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'one', { two_hash } ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'two', { one_hash } ) ) ]
        scu[ TC.LOCAL_RATING_LIKE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { two_hash } ) ) ]
        scu[ TC.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.8, { two_hash } ) ) ]
        
        assertSCUEqual( result, scu )
        
    
    def test_SERIALISABLE_TYPE_SHORTCUT( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( dupe_obj.__hash__(), ( dupe_obj.shortcut_type, dupe_obj.shortcut_key, dupe_obj.shortcut_press_type, tuple( dupe_obj.modifiers ) ).__hash__() )
            
            self.assertEqual( obj, dupe_obj )
            
        
        shortcuts = []
        
        shortcuts.append( ( ClientGUIShortcuts.Shortcut(), 'f7' ) )
        
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), 'space' ) )
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'a' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+a' ) )
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'A' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+a' ) )
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT, ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+alt+home' ) )
        
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), 'left-click' ) )
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), 'ctrl+middle-click' ) )
        shortcuts.append( ( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT, ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), 'alt+shift+scroll down' ) )
        
        for ( shortcut, s ) in shortcuts:
            
            self._dump_and_load_and_test( shortcut, test )
            
            if HC.PLATFORM_MACOS:
                
                s = s.replace( 'ctrl', 'command' )
                
            
            self.assertEqual( shortcut.ToString(), s )
            
        
    
    def test_SERIALISABLE_TYPE_SHORTCUT_SET( self ):
        
        def test( obj, dupe_obj ):
            
            for ( shortcut, command ) in obj:
                
                self.assertEqual( dupe_obj.GetCommand( shortcut ), command )
                
            
        
        default_shortcuts = ClientDefaults.GetDefaultShortcuts()
        
        for shortcuts in default_shortcuts:
            
            self._dump_and_load_and_test( shortcuts, test )
            
        
        command_1 = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE )
        command_2 = CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( HydrusData.GenerateKey(), HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) )
        command_3 = CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_FLIP, 'test' ) )
        
        k_shortcut_1 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        k_shortcut_2 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'a' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        k_shortcut_3 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'A' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        k_shortcut_4 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT, ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        
        m_shortcut_1 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        m_shortcut_2 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        m_shortcut_3 = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT, ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] )
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( 'test' )
        
        shortcut_set.SetCommand( k_shortcut_1, command_1 )
        shortcut_set.SetCommand( k_shortcut_2, command_2 )
        shortcut_set.SetCommand( k_shortcut_3, command_2 )
        shortcut_set.SetCommand( k_shortcut_4, command_3 )
        
        shortcut_set.SetCommand( m_shortcut_1, command_1 )
        shortcut_set.SetCommand( m_shortcut_2, command_2 )
        shortcut_set.SetCommand( m_shortcut_3, command_3 )
        
        self._dump_and_load_and_test( shortcut_set, test )
        
        self.assertEqual( tuple( shortcut_set.GetCommand( k_shortcut_1 )._data ), tuple( command_1._data ) )
        
        shortcut_set.SetCommand( k_shortcut_1, command_3 )
        
        self.assertEqual( tuple( shortcut_set.GetCommand( k_shortcut_1 )._data ), tuple( command_3._data ) )
        
    
    def test_SERIALISABLE_TYPE_SUBSCRIPTION( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj.GetName(), dupe_obj.GetName() )
            
            self.assertEqual( obj._gug_key_and_name, dupe_obj._gug_key_and_name )
            self.assertEqual( len( obj._query_headers ), len( dupe_obj._query_headers ) )
            self.assertEqual( obj._initial_file_limit, dupe_obj._initial_file_limit )
            self.assertEqual( obj._periodic_file_limit, dupe_obj._periodic_file_limit )
            self.assertEqual( obj._paused, dupe_obj._paused )
            
            self.assertEqual( obj._file_import_options.GetSerialisableTuple(), dupe_obj._file_import_options.GetSerialisableTuple() )
            self.assertEqual( obj._tag_import_options.GetSerialisableTuple(), dupe_obj._tag_import_options.GetSerialisableTuple() )
            
            self.assertEqual( obj._no_work_until, dupe_obj._no_work_until )
            
        
        sub = ClientImportSubscriptions.Subscription( 'test sub' )
        
        self._dump_and_load_and_test( sub, test )
        
        gug_key_and_name = ( HydrusData.GenerateKey(), 'muh test gug' )
        
        query_headers = []
        
        q = ClientImportSubscriptionQuery.SubscriptionQueryHeader()
        q.SetQueryText( 'test query' )
        query_headers.append( q )
        
        q = ClientImportSubscriptionQuery.SubscriptionQueryHeader()
        q.SetQueryText( 'test query 2' )
        query_headers.append( q )
        
        checker_options = ClientImportOptions.CheckerOptions()
        initial_file_limit = 100
        periodic_file_limit = 50
        paused = False
        
        file_import_options = FileImportOptions.FileImportOptions()
        
        service_tag_import_options = TagImportOptions.ServiceTagImportOptions( get_tags = False, additional_tags = { 'test additional tag', 'and another' } )
        
        tag_import_options = TagImportOptions.TagImportOptions( service_keys_to_service_tag_import_options = { HydrusData.GenerateKey() : service_tag_import_options } )
        
        no_work_until = HydrusData.GetNow() - 86400 * 20
        
        sub.SetTuple( gug_key_and_name, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until )
        
        sub.SetQueryHeaders( query_headers )
        
        self.assertEqual( sub.GetGUGKeyAndName(), gug_key_and_name )
        self.assertEqual( sub.GetTagImportOptions(), tag_import_options )
        self.assertEqual( sub.GetQueryHeaders(), query_headers )
        
        self.assertEqual( sub._paused, False )
        sub.PauseResume()
        self.assertEqual( sub._paused, True )
        sub.PauseResume()
        self.assertEqual( sub._paused, False )
        
        self._dump_and_load_and_test( sub, test )
        
    
    def test_SERIALISABLE_TYPE_TAG_FILTER( self ):
        
        def test( obj, dupe_obj ):
            
            self.assertEqual( obj._tag_slices_to_rules, dupe_obj._tag_slices_to_rules )
            
        
        tags = set()
        
        tags.add( 'title:test title' )
        tags.add( 'series:neon genesis evangelion' )
        tags.add( 'series:kill la kill' )
        tags.add( 'smile' )
        tags.add( 'blue eyes' )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile', 'blue eyes', 'title:test title', 'series:neon genesis evangelion', 'series:kill la kill' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), set() )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'series:neon genesis evangelion', 'series:kill la kill' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:kill la kill', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'series:kill la kill' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'smile', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile', 'blue eyes' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile', 'blue eyes', 'series:neon genesis evangelion', 'series:kill la kill' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:kill la kill', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile', 'blue eyes', 'series:kill la kill' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'series:', HC.FILTER_BLACKLIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile', 'blue eyes', 'title:test title' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'series:', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'series:neon genesis evangelion', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'smile', 'blue eyes', 'title:test title', 'series:neon genesis evangelion' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'title:test title', 'series:neon genesis evangelion', 'series:kill la kill' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'blue eyes', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( tags ), { 'title:test title', 'series:neon genesis evangelion', 'series:kill la kill', 'blue eyes' } )
        
        # blacklist namespace test
        
        blacklist_tags = { 'nintendo', 'studio:nintendo' }
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'nintendo', HC.FILTER_BLACKLIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( blacklist_tags ), { 'studio:nintendo' } )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'nintendo', HC.FILTER_BLACKLIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( blacklist_tags, apply_unnamespaced_rules_to_namespaced_tags = True ), set() )
        
        #
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( 'nintendo', HC.FILTER_BLACKLIST )
        tag_filter.SetRule( 'studio:nintendo', HC.FILTER_WHITELIST )
        
        self._dump_and_load_and_test( tag_filter, test )
        
        self.assertEqual( tag_filter.Filter( blacklist_tags, apply_unnamespaced_rules_to_namespaced_tags = True ), { 'studio:nintendo' } )
        
    
