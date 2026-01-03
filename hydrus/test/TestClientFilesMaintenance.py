import unittest

from hydrus.client.metadata import ClientTikTok


class _DummyNotesManager:
    
    def __init__( self, names_to_notes ):
        
        self._names_to_notes = dict( names_to_notes )
        
    
    def GetNamesToNotes( self ):
        
        return dict( self._names_to_notes )


class TestClientFilesMaintenanceTikTokTags( unittest.TestCase ):
    
    def test_tiktok_tags_from_urls( self ):
        
        urls = [
            'https://www.tiktok.com/@ExampleUser/video/12345?is_from_webapp=1',
            'https://m.tiktok.com/@some_user',
            'https://vm.tiktok.com/ZSAbc/'
        ]
        
        tags = ClientTikTok.GetTikTokTagsFromURLs( urls )
        
        self.assertEqual( tags, { 'site:tiktok', 'creator:exampleuser', 'creator:some_user' } )
        
    
    def test_non_tiktok_urls_are_ignored( self ):
        
        urls = [ 'https://example.com/@user/video/1' ]
        
        tags = ClientTikTok.GetTikTokTagsFromURLs( urls )
        
        self.assertEqual( tags, set() )
        
    
    def test_tiktok_description_note_lookup( self ):
        
        notes_manager = _DummyNotesManager(
            {
                'Description' : 'hello #One',
                'other' : '#two'
            }
        )
        
        description_text = ClientTikTok.GetTikTokDescriptionTextFromNotes( notes_manager )
        
        self.assertEqual( description_text, 'hello #One' )
        
    
    def test_tiktok_description_note_fallback_single_note( self ):
        
        notes_manager = _DummyNotesManager( { 'misc' : 'hi #tag' } )
        
        description_text = ClientTikTok.GetTikTokDescriptionTextFromNotes( notes_manager )
        
        self.assertEqual( description_text, 'hi #tag' )
        
    
    def test_tiktok_hashtag_tags_from_text( self ):
        
        text = 'hello #One and #two_2 then #3rd.'
        
        tags = ClientTikTok.GetTikTokHashtagTagsFromText( text )
        
        self.assertEqual( tags, { 'tiktok:one', 'tiktok:two_2', 'tiktok:3rd' } )
        
    
    def test_tiktok_tags_from_parsed_metadata( self ):
        
        urls = [ 'https://www.tiktok.com/@ExampleUser/video/12345' ]
        names_and_notes = [ ( 'description', 'hello #Tag' ) ]
        
        tags = ClientTikTok.GetTikTokTagsFromParsedMetadata( urls, names_and_notes )
        
        self.assertEqual( tags, { 'site:tiktok', 'creator:exampleuser', 'tiktok:tag' } )
        
    
    def test_non_tiktok_parsed_metadata_is_ignored( self ):
        
        urls = [ 'https://example.com/@user/video/1' ]
        names_and_notes = [ ( 'description', 'hello #Tag' ) ]
        
        tags = ClientTikTok.GetTikTokTagsFromParsedMetadata( urls, names_and_notes )
        
        self.assertEqual( tags, set() )
        
    
    def test_tiktok_parsed_metadata_with_existing_site_tag( self ):
        
        urls = []
        names_and_notes = [ ( 'description', 'hello #Tag' ) ]
        
        tags = ClientTikTok.GetTikTokTagsFromParsedMetadata(
            urls,
            names_and_notes,
            existing_tags = { 'site:tiktok' }
        )
        
        self.assertEqual( tags, { 'tiktok:tag' } )
        
