import sqlite3

from hydrus.core import HydrusConstants as HC

from hydrus.client.db import ClientDBContentUpdates
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesDuplicates
from hydrus.client.db import ClientDBModule

class ClientDBFilesDuplicatesSetter( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_files_duplicates: ClientDBFilesDuplicates.ClientDBFilesDuplicates,
        modules_content_updates: ClientDBContentUpdates.ClientDBContentUpdates
        ):
        
        super().__init__( 'client file duplicates setter', cursor )
        
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_files_duplicates = modules_files_duplicates
        self.modules_content_updates = modules_content_updates
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def SetDuplicatePairStatus( self, pair_infos ):
        
        # TODO: This guy should now take a list of DuplicatePairDecisionDuplicatesAction!!! get rid of this tuple!
        
        for ( duplicate_type, hash_a, hash_b, content_update_packages ) in pair_infos:
            
            for content_update_package in content_update_packages:
                
                self.modules_content_updates.ProcessContentUpdatePackage( content_update_package )
                
            
            hash_id_a = self.modules_hashes_local_cache.GetHashId( hash_a )
            hash_id_b = self.modules_hashes_local_cache.GetHashId( hash_b )
            
            media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
            
            smaller_media_id = min( media_id_a, media_id_b )
            larger_media_id = max( media_id_a, media_id_b )
            
            # this shouldn't be strictly needed, but lets do it here anyway to catch unforeseen problems
            # it is ok to remove this even if we are just about to add it back in--this clears out invalid pairs and increases priority with distance 0
            
            self.modules_files_duplicates.DeletePotentialDuplicates( [ ( smaller_media_id, larger_media_id ) ] )
            
            if hash_id_a == hash_id_b:
                
                continue
                
            
            if duplicate_type in ( HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE ):
                
                if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                    
                    alternates_group_id_a = self.modules_files_duplicates.GetAlternatesGroupId( media_id_a )
                    alternates_group_id_b = self.modules_files_duplicates.GetAlternatesGroupId( media_id_b )
                    
                    self.modules_files_duplicates.SetFalsePositive( alternates_group_id_a, alternates_group_id_b )
                    
                elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                    
                    if media_id_a == media_id_b:
                        
                        king_hash_id = self.modules_files_duplicates.GetKingHashId( media_id_a )
                        
                        hash_id_to_remove = hash_id_b if king_hash_id == hash_id_a else hash_id_a
                        
                        self.modules_files_duplicates.RemoveMediaIdMember( hash_id_to_remove )
                        
                        media_id_a = self.modules_files_duplicates.GetMediaId( hash_id_a )
                        media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
                        
                    
                    self.modules_files_duplicates.SetAlternates( media_id_a, media_id_b )
                    
                
            elif duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ):
                
                king_hash_id_a = self.modules_files_duplicates.GetKingHashId( media_id_a )
                king_hash_id_b = self.modules_files_duplicates.GetKingHashId( media_id_b )
                
                if duplicate_type == HC.DUPLICATE_BETTER:
                    
                    if media_id_a == media_id_b:
                        
                        if hash_id_b == king_hash_id_b:
                            
                            # user manually set that a > King A, hence we are setting a new king within a group
                            
                            self.modules_files_duplicates.SetKing( hash_id_a, media_id_a )
                            
                        
                    else:
                        
                        if hash_id_b != king_hash_id_b:
                            
                            # user manually set that a member of A is better than a non-King of B. remove b from B and merge it into A
                            
                            self.modules_files_duplicates.RemoveMediaIdMember( hash_id_b )
                            
                            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
                            
                            # b is now the King of its new group
                            
                        
                        # a member of A is better than King B, hence B can merge into A
                        
                        self.modules_files_duplicates.SetDuplicates( media_id_a, media_id_b )
                        
                    
                elif duplicate_type == HC.DUPLICATE_SAME_QUALITY:
                    
                    if media_id_a != media_id_b:
                        
                        a_is_king = hash_id_a == king_hash_id_a
                        b_is_king = hash_id_b == king_hash_id_b
                        
                        if not ( a_is_king or b_is_king ):
                            
                            # if neither file is the king, remove B from B and merge it into A
                            
                            self.modules_files_duplicates.RemoveMediaIdMember( hash_id_b )
                            
                            media_id_b = self.modules_files_duplicates.GetMediaId( hash_id_b )
                            
                            superior_media_id = media_id_a
                            mergee_media_id = media_id_b
                            
                        elif not a_is_king:
                            
                            # if one of our files is not the king, merge into that group, as the king of that is better than all of the other
                            
                            superior_media_id = media_id_a
                            mergee_media_id = media_id_b
                            
                        elif not b_is_king:
                            
                            superior_media_id = media_id_b
                            mergee_media_id = media_id_a
                            
                        else:
                            
                            # if both are king, merge into A
                            
                            superior_media_id = media_id_a
                            mergee_media_id = media_id_b
                            
                        
                        self.modules_files_duplicates.SetDuplicates( superior_media_id, mergee_media_id )
                        
                    
                
            elif duplicate_type == HC.DUPLICATE_POTENTIAL:
                
                potential_duplicate_media_ids_and_distances = [ ( media_id_b, 0 ) ]
                
                self.modules_files_duplicates.AddPotentialDuplicates( media_id_a, potential_duplicate_media_ids_and_distances )
                
            
        
    
