import os
import unittest

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientStrings
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.networking import ClientNetworkingURLClass

from hydrus.test import TestGlobals as TG

class TestFileSeedCache( unittest.TestCase ):
    
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
        netloc = 'tokensite.lad'
        
        alphabetise_get_parameters = True
        match_subdomains = False
        keep_matched_subdomains = False
        can_produce_multiple_files = False
        should_be_associated_with_files = True
        keep_fragment = False
        
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
        
        url_class = ClientNetworkingURLClass.URLClass( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, path_components = path_components, parameters = parameters, send_referral_url = send_referral_url, referral_url_converter = referral_url_converter, gallery_index_type = gallery_index_type, gallery_index_identifier = gallery_index_identifier, gallery_index_delta = gallery_index_delta, example_url = example_url )
        
        #
        
        new_url_classes.append( url_class )
        
        dm.SetURLClasses( new_url_classes )
        
        file_seed_cache.RenormaliseURLs()
        
        self.assertEqual( len( file_seed_cache ), len( nums ) )
        
        dm.SetURLClasses( original_url_classes )
        
    
