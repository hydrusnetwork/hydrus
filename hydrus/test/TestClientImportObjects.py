import os
import random
import unittest

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientStrings
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.networking import ClientNetworkingURLClass

from hydrus.test import TestGlobals as TG

class TestFileSeedCache( unittest.TestCase ):
    
    def test_compaction_0_simple( self ):
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        last_fifty = []
        
        for i in range( 100 ):
            
            url = f'https://example.com/post/{i}'
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = 100000
            
            file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW )
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
            if i >= 50:
                
                last_fifty.append( file_seed )
                
            
        
        self.assertFalse( file_seed_cache.CanCompact( 50, 80000 ) )
        self.assertFalse( file_seed_cache.CanCompact( 150, 120000 ) )
        self.assertTrue( file_seed_cache.CanCompact( 50, 120000 ) )
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 100 )
        
        file_seed_cache.Compact( 50, 120000 )
        
        self.assertEqual( len( file_seed_cache ), len( last_fifty ) )
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 50 )
        
        for file_seed in last_fifty:
            
            self.assertTrue( file_seed_cache.HasFileSeed( file_seed ) )
            
        
    
    def test_compaction_1_parents( self ):
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        last_fifty_with_children = []
        
        for i in range( 100 ):
            
            url = f'https://example.com/post/{i}'
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = 100000
            
            num_children = random.randint( 2, 8 )
            
            file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_CHILD_FILES, note = f'Found {num_children} new URLs in {num_children} posts.' )
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
            if i >= 50:
                
                last_fifty_with_children.append( file_seed )
                
            
            # children:
            
            for j in range( num_children ):
                
                url = f'https://manga.example.com/post/{i}/{j}'
                
                file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
                
                file_seed.source_time = 100000
                
                file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW )
                
                file_seed_cache.AddFileSeeds( ( file_seed, ) )
                
                if i >= 50:
                    
                    last_fifty_with_children.append( file_seed )
                    
                
            
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 100 )
        
        self.assertFalse( file_seed_cache.CanCompact( 50, 80000 ) )
        self.assertFalse( file_seed_cache.CanCompact( 150, 120000 ) )
        self.assertTrue( file_seed_cache.CanCompact( 50, 120000 ) )
        
        file_seed_cache.Compact( 50, 120000 )
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 50 )
        
        self.assertEqual( len( file_seed_cache ), len( last_fifty_with_children ) )
        
        for file_seed in last_fifty_with_children:
            
            self.assertTrue( file_seed_cache.HasFileSeed( file_seed ) )
            
        
    
    def test_compaction_2_parents_bad_note( self ):
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        last_fifty_with_children = []
        
        for i in range( 100 ):
            
            url = f'https://example.com/post/{i}'
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = 100000
            
            file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_CHILD_FILES, note = 'Hello old note will not parse.' )
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
            if i >= 50:
                
                last_fifty_with_children.append( file_seed )
                
            
            # children:
            
            for j in range( random.randint( 2, 8 ) ):
                
                url = f'https://manga.example.com/post/{i}/{j}'
                
                file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
                
                file_seed.source_time = 100000
                
                file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW )
                
                file_seed_cache.AddFileSeeds( ( file_seed, ) )
                
                if i >= 50:
                    
                    last_fifty_with_children.append( file_seed )
                    
                
            
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 100 )
        
        self.assertFalse( file_seed_cache.CanCompact( 50, 80000 ) )
        self.assertFalse( file_seed_cache.CanCompact( 150, 120000 ) )
        self.assertTrue( file_seed_cache.CanCompact( 50, 120000 ) )
        
        file_seed_cache.Compact( 50, 120000 )
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 50 )
        
        self.assertEqual( len( file_seed_cache ), len( last_fifty_with_children ) )
        
        for file_seed in last_fifty_with_children:
            
            self.assertTrue( file_seed_cache.HasFileSeed( file_seed ) )
            
        
    
    def test_compaction_3_nested_parents_hooray( self ):
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        last_fifty_with_children = []
        
        for i in range( 100 ):
            
            url = f'https://example.com/post/{i}'
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = 100000
            
            file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_CHILD_FILES, note = f'Found 1 new URLs in 1 posts.' )
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
            if i >= 50:
                
                last_fifty_with_children.append( file_seed )
                
            
            url = f'https://example.com/post/{i}/directory'
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = 100000
            
            num_children = random.randint( 2, 8 )
            
            file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_CHILD_FILES, note = f'Found {num_children} new URLs in {num_children} posts.' )
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
            if i >= 50:
                
                last_fifty_with_children.append( file_seed )
                
            
            # children:
            
            for j in range( num_children ):
                
                url = f'https://manga.example.com/post/{i}/{j}'
                
                file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
                
                file_seed.source_time = 100000
                
                file_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW )
                
                file_seed_cache.AddFileSeeds( ( file_seed, ) )
                
                if i >= 50:
                    
                    last_fifty_with_children.append( file_seed )
                    
                
            
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 100 )
        
        self.assertFalse( file_seed_cache.CanCompact( 50, 80000 ) )
        self.assertFalse( file_seed_cache.CanCompact( 150, 120000 ) )
        self.assertTrue( file_seed_cache.CanCompact( 50, 120000 ) )
        
        file_seed_cache.Compact( 50, 120000 )
        
        self.assertEqual( file_seed_cache.GetApproxNumMasterFileSeeds(), 50 )
        
        self.assertEqual( len( file_seed_cache ), len( last_fifty_with_children ) )
        
        for file_seed in last_fifty_with_children:
            
            self.assertTrue( file_seed_cache.HasFileSeed( file_seed ) )
            
        
    
    def test_renormalise( self ):
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        nums = [ 123, 456, 123456 ]
        num_dupes = 3
        
        # some fake tokenised URL dupes
        for num in nums:
            
            for i in range( num_dupes ):
                
                url = f'https://tokensite.lad/post/{num}?token={os.urandom( 16 ).hex()}'
                
                file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
                
                file_seed_cache.AddFileSeeds( ( file_seed, ) )
                
            
        
        self.assertEqual( len( file_seed_cache ), len( nums ) * num_dupes )
        
        dm = TG.test_controller.network_engine.domain_manager
        
        original_url_classes = dm.GetURLClasses()
        
        new_url_classes = list( original_url_classes )
        
        #
        
        name = 'tokensite post'
        url_type = HC.URL_TYPE_POST
        preferred_scheme = 'https'
        
        url_domain_mask = ClientNetworkingURLClass.URLDomainMask( raw_domains = [ 'tokensite.lad' ] )
        
        path_components = []
        
        path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ), None ) )
        path_components.append( ( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_ANY, match_value = '123456', example_string = '123456' ), None ) )
        
        parameters = []
        
        p = ClientNetworkingURLClass.URLClassParameterFixedName( name = 'token', value_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_ANY, match_value = 'blah', example_string = 'blah' ) )
        p.SetIsEphemeral( True )
        
        parameters.append( p )
        
        send_referral_url = ClientNetworkingURLClass.SEND_REFERRAL_URL_ONLY_IF_PROVIDED
        referral_url_converter = None
        gallery_index_type = None
        gallery_index_identifier = None
        gallery_index_delta = 1
        example_url = 'https://tokensite.lad/post/123456?token=abcdabcdabcdabcdabcdabcdabcdabcd}'
        
        url_class = ClientNetworkingURLClass.URLClass( name, url_type = url_type, preferred_scheme = preferred_scheme, url_domain_mask = url_domain_mask, path_components = path_components, parameters = parameters, send_referral_url = send_referral_url, referral_url_converter = referral_url_converter, gallery_index_type = gallery_index_type, gallery_index_identifier = gallery_index_identifier, gallery_index_delta = gallery_index_delta, example_url = example_url )
        
        #
        
        new_url_classes.append( url_class )
        
        dm.SetURLClasses( new_url_classes )
        
        file_seed_cache.RenormaliseURLs()
        
        self.assertEqual( len( file_seed_cache ), len( nums ) )
        
        dm.SetURLClasses( original_url_classes )
        
    
