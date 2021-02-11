import os
import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags

from hydrus.client.db import ClientDBMaster

class ClientDBCacheLocalTags( HydrusDBModule.HydrusDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_tags: ClientDBMaster.ClientDBMasterTags ):
        
        self.modules_tags = modules_tags
        
        self._tag_ids_to_tags_cache = {}
        
        HydrusDBModule.HydrusDBModule.__init__( self, 'client tags local cache', cursor )
        
    
    def _GetIndexGenerationTuples( self ):
        
        index_generation_tuples = []
        
        return index_generation_tuples
        

    def _PopulateTagIdsToTagsCache( self, tag_ids ):
        
        if len( self._tag_ids_to_tags_cache ) > 100000:
            
            if not isinstance( tag_ids, set ):
                
                tag_ids = set( tag_ids )
                
            
            self._tag_ids_to_tags_cache = { tag_id : tag for ( tag_id, tag ) in self._tag_ids_to_tags_cache.items() if tag_id in tag_ids }
            
        
        uncached_tag_ids = { tag_id for tag_id in tag_ids if tag_id not in self._tag_ids_to_tags_cache }
        
        if len( uncached_tag_ids ) > 0:
            
            if len( uncached_tag_ids ) == 1:
                
                ( uncached_tag_id, ) = uncached_tag_ids
                
                # this makes 0 or 1 rows, so do fetchall rather than fetchone
                local_uncached_tag_ids_to_tags = { tag_id : tag for ( tag_id, tag ) in self._c.execute( 'SELECT tag_id, tag FROM local_tags_cache WHERE tag_id = ?;', ( uncached_tag_id, ) ) }
                
            else:
                
                with HydrusDB.TemporaryIntegerTable( self._c, uncached_tag_ids, 'tag_id' ) as temp_table_name:
                    
                    # temp tag_ids to actual tags
                    local_uncached_tag_ids_to_tags = { tag_id : tag for ( tag_id, tag ) in self._c.execute( 'SELECT tag_id, tag FROM {} CROSS JOIN local_tags_cache USING ( tag_id );'.format( temp_table_name ) ) }
                    
                
            
            self._tag_ids_to_tags_cache.update( local_uncached_tag_ids_to_tags )
            
            uncached_tag_ids = { tag_id for tag_id in uncached_tag_ids if tag_id not in self._tag_ids_to_tags_cache }
            
        
        if len( uncached_tag_ids ) > 0:
            
            tag_ids_to_tags = self.modules_tags.GetTagIdsToTags( tag_ids = uncached_tag_ids )
            
            self._tag_ids_to_tags_cache.update( tag_ids_to_tags )
            
        
    
    def CreateTables( self ):
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_caches.local_tags_cache ( tag_id INTEGER PRIMARY KEY, tag TEXT UNIQUE );' )
        
    
    def AddTagIdsToCache( self, tag_ids ):
        
        tag_ids_to_tags = self.modules_tags.GetTagIdsToTags( tag_ids = tag_ids )
        
        self._c.executemany( 'INSERT OR IGNORE INTO local_tags_cache ( tag_id, tag ) VALUES ( ?, ? );', tag_ids_to_tags.items() )
        
    
    def ClearCache( self ):
        
        self._c.execute( 'DROP TABLE IF EXISTS local_tags_cache;' )
        
        self.CreateTables()
        
    
    def DropTagIdsFromCache( self, tag_ids ):
        
        self._c.executemany( 'DELETE FROM local_tags_cache WHERE tag_id = ?;', ( ( tag_id, ) for tag_id in tag_ids ) )
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        expected_table_names = [
            'external_caches.local_tags_cache'
        ]
        
        return expected_table_names
        
    
    def GetTag( self, tag_id ) -> str:
        
        self._PopulateTagIdsToTagsCache( ( tag_id, ) )
        
        return self._tag_ids_to_tags_cache[ tag_id ]
        
    
    def GetTagId( self, tag ) -> int:
        
        clean_tag = HydrusTags.CleanTag( tag )
        
        try:
            
            HydrusTags.CheckTagNotEmpty( clean_tag )
            
        except HydrusExceptions.TagSizeException:
            
            raise HydrusExceptions.TagSizeException( '"{}" tag seems not valid--when cleaned, it ends up with zero size!'.format( tag ) )
            
        
        result = self._c.execute( 'SELECT tag_id FROM tags WHERE tag = ?;', ( tag, ) ).fetchone()
        
        if result is None:
            
            return self.modules_tags.GetTagId( tag )
            
        else:
            
            ( tag_id, ) = result
            
        
        return tag_id
        
    
    def GetTagIdsToTags( self, tag_ids = None, tags = None ) -> typing.Dict[ int, str ]:
        
        if tag_ids is not None:
            
            self._PopulateTagIdsToTagsCache( tag_ids )
            
            tag_ids_to_tags = { tag_id : self._tag_ids_to_tags_cache[ tag_id ] for tag_id in tag_ids }
            
        elif tags is not None:
            
            tag_ids_to_tags = { self.GetTagId( tag ) : tag for tag in tags }
            
        
        return tag_ids_to_tags
        
    
    def UpdateTagInCache( self, tag_id, tag ):
        
        self._c.execute( 'UPDATE local_tags_cache SET tag = ? WHERE tag_id = ?;', ( tag, tag_id ) )
        
        if tag_id in self._tag_ids_to_tags_cache:
            
            del self._tag_ids_to_tags_cache[ tag_id ]
            
        
    
