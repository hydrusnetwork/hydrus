import re
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.search import ClientSearch

class ClientDBURLMap( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_urls: ClientDBMaster.ClientDBMasterURLs ):
        
        self.modules_urls = modules_urls
        
        ClientDBModule.ClientDBModule.__init__( self, 'client urls mapping', cursor )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.url_map' ] = [
            ( [ 'url_id' ], False, 485 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.url_map' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, url_id INTEGER, PRIMARY KEY ( hash_id, url_id ) );', 485 )
        }
        
    
    def AddMapping( self, hash_id: int, url: str ):
        
        url_id = self.modules_urls.GetURLId( url )
        
        self._Execute( 'INSERT OR IGNORE INTO url_map ( hash_id, url_id ) VALUES ( ?, ? );', ( hash_id, url_id ) )
        
    
    def DeleteMapping( self, hash_id: int, url: str ):
        
        url_id = self.modules_urls.GetURLId( url )
        
        self._Execute( 'DELETE FROM url_map WHERE hash_id = ? AND url_id = ?;', ( hash_id, url_id ) )
        
    
    def GetHashIds( self, search_url: str ):
        
        hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM url_map NATURAL JOIN urls WHERE url = ?;', ( search_url, ) ) )
        
        return hash_ids
        
    
    def GetHashIdsFromCountTests( self, number_tests: typing.List[ ClientSearch.NumberTest ], hash_ids: typing.Collection[ int ], hash_ids_table_name: str ):
        
        # we'll have to natural join 'urls' or 'urls-class-map-cache' or whatever when we add a proper filter to this guy
        
        table_join = 'url_map'
        
        if len( hash_ids ) < 50000:
            
            table_join += ' NATURAL JOIN {}'.format( hash_ids_table_name )
            
        
        #
        
        result_hash_ids = set( hash_ids )
        
        specific_number_tests = [ number_test for number_test in number_tests if not ( number_test.IsZero() or number_test.IsAnythingButZero() ) ]
        
        megalambda = ClientSearch.NumberTest.STATICCreateMegaLambda( specific_number_tests )
        
        is_zero = True in ( number_test.IsZero() for number_test in number_tests )
        is_anything_but_zero = True in ( number_test.IsAnythingButZero() for number_test in number_tests )
        wants_zero = True in ( number_test.WantsZero() for number_test in number_tests )
        
        if is_zero or is_anything_but_zero or wants_zero:
            
            select = f'SELECT DISTINCT hash_id FROM {table_join};'
            
            nonzero_url_query_hash_ids = self._STS( self._Execute( select ) )
            
            if is_zero:
                
                result_hash_ids.difference_update( nonzero_url_query_hash_ids )
                
            
            if is_anything_but_zero:
                
                result_hash_ids.intersection_update( nonzero_url_query_hash_ids )
                
            
        
        if len( specific_number_tests ) > 0:
            
            select = f'SELECT hash_id, COUNT( url_id ) FROM {table_join} GROUP BY hash_id;'
            
            good_url_count_hash_ids = { hash_id for ( hash_id, count ) in self._Execute( select ) if megalambda( count ) }
            
            if wants_zero:
                
                zero_hash_ids = result_hash_ids.difference( nonzero_url_query_hash_ids )
                
                good_url_count_hash_ids.update( zero_hash_ids )
                
            
            result_hash_ids.intersection_update( good_url_count_hash_ids )
            
        
        return result_hash_ids
        
    
    def GetHashIdsFromURLRule( self, rule_type, rule, hash_ids = None, hash_ids_table_name = None ):
        
        if rule_type == 'exact_match':
            
            url = rule
            
            table_name = 'url_map NATURAL JOIN urls'
            
            if hash_ids_table_name is not None and hash_ids is not None and len( hash_ids ) < 50000:
                
                table_name += ' NATURAL JOIN {}'.format( hash_ids_table_name )
                
            
            select = 'SELECT hash_id FROM {} WHERE url = ?;'.format( table_name )
            
            result_hash_ids = self._STS( self._Execute( select, ( url, ) ) )
            
            return result_hash_ids
            
        elif rule_type in ( 'url_class', 'url_match' ):
            
            url_class = rule
            
            domain = url_class.GetDomain()
            
            if url_class.MatchesSubdomains():
                
                domain_ids = self.modules_urls.GetURLDomainAndSubdomainIds( domain )
                
            else:
                
                domain_ids = self.modules_urls.GetURLDomainAndSubdomainIds( domain, only_www_subdomains = True )
                
            
            result_hash_ids = set()
            
            with self._MakeTemporaryIntegerTable( domain_ids, 'domain_id' ) as temp_domain_table_name:
                
                if hash_ids_table_name is not None and hash_ids is not None and len( hash_ids ) < 50000:
                    
                    # if we aren't gonk mode with the number of files, temp hashes to url map to urls to domains
                    # next step here is irl profiling and a domain->url_count cache so I can decide whether to do this or not based on url domain count
                    select = 'SELECT hash_id, url FROM {} CROSS JOIN url_map USING ( hash_id ) CROSS JOIN urls USING ( url_id ) CROSS JOIN {} USING ( domain_id );'.format( hash_ids_table_name, temp_domain_table_name )
                    
                else:
                    
                    # domains to urls to url map
                    select = 'SELECT hash_id, url FROM {} CROSS JOIN urls USING ( domain_id ) CROSS JOIN url_map USING ( url_id );'.format( temp_domain_table_name )
                    
                
                for ( hash_id, url ) in self._Execute( select ):
                    
                    # this is actually insufficient, as more detailed url classes may match
                    if hash_id not in result_hash_ids and url_class.Matches( url ):
                        
                        result_hash_ids.add( hash_id )
                        
                    
                
            
            return result_hash_ids
            
        elif rule_type in 'domain':
            
            domain = rule
            
            # if we search for site.com, we also want artist.site.com or www.site.com or cdn2.site.com
            domain_ids = self.modules_urls.GetURLDomainAndSubdomainIds( domain )
            
            result_hash_ids = set()
            
            with self._MakeTemporaryIntegerTable( domain_ids, 'domain_id' ) as temp_domain_table_name:
                
                if hash_ids_table_name is not None and hash_ids is not None and len( hash_ids ) < 50000:
                    
                    # if we aren't gonk mode with the number of files, temp hashes to url map to urls to domains
                    # next step here is irl profiling and a domain->url_count cache so I can decide whether to do this or not based on url domain count
                    select = 'SELECT hash_id FROM {} CROSS JOIN url_map USING ( hash_id ) CROSS JOIN urls USING ( url_id ) CROSS JOIN {} USING ( domain_id )'.format( hash_ids_table_name, temp_domain_table_name )
                    
                else:
                    
                    # domains to urls to url map
                    select = 'SELECT hash_id FROM {} CROSS JOIN urls USING ( domain_id ) CROSS JOIN url_map USING ( url_id );'.format( temp_domain_table_name )
                    
                
                result_hash_ids = self._STS( self._Execute( select ) )
                
            
            return result_hash_ids
            
        else:
            
            regex = rule
            
            if hash_ids_table_name is not None and hash_ids is not None and len( hash_ids ) < 50000:
                
                # if we aren't gonk mode with the number of files, temp hashes to url map to urls
                # next step here is irl profiling and a domain->url_count cache so I can decide whether to do this or not based on _TOTAL_ url count
                select = 'SELECT hash_id, url FROM {} CROSS JOIN url_map USING ( hash_id ) CROSS JOIN urls USING ( url_id );'.format( hash_ids_table_name )
                
            else:
                
                select = 'SELECT hash_id, url FROM url_map NATURAL JOIN urls;'
                
            
            result_hash_ids = set()
            
            for ( hash_id, url ) in self._Execute( select ):
                
                if hash_id not in result_hash_ids and re.search( regex, url ) is not None:
                    
                    result_hash_ids.add( hash_id )
                    
                
            
            return result_hash_ids
            
        
    
    def GetHashIdsToURLs( self, hash_ids_table_name = None ):
        
        hash_ids_to_urls = {}
        
        if hash_ids_table_name is not None:
            
            hash_ids_to_urls = HydrusData.BuildKeyToSetDict( self._Execute( 'SELECT hash_id, url FROM {} CROSS JOIN url_map USING ( hash_id ) CROSS JOIN urls USING ( url_id );'.format( hash_ids_table_name ) ) )
            
        
        return hash_ids_to_urls
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # if content type is a domain, then give urls? bleh
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_FILES:
            
            tables_and_columns.append( ( 'main.url_map', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
