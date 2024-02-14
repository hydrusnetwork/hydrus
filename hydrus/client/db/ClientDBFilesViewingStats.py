import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client import ClientTime
from hydrus.client.db import ClientDBModule

class ClientDBFilesViewingStats( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor
    ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client files viewing stats', cursor )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.file_viewing_stats' ] = [
            ( [ 'last_viewed_timestamp_ms' ], False, 559 ),
            ( [ 'views' ], False, 400 ),
            ( [ 'viewtime' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        # TODO: Migrate last_viewed_timestamp over to the FilesTimestamps module and think about collapsing it to just the media viewer, with an option to fold preview views in if you want
        return {
            'main.file_viewing_stats' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, canvas_type INTEGER, last_viewed_timestamp_ms INTEGER, views INTEGER, viewtime INTEGER, PRIMARY KEY ( hash_id, canvas_type ) );', 400 )
        }
        
    
    def AddViews( self, hash_id, canvas_type, view_timestamp_ms, views_delta, viewtime_delta ):
        
        self._Execute( 'INSERT OR IGNORE INTO file_viewing_stats ( hash_id, canvas_type, last_viewed_timestamp_ms, views, viewtime ) VALUES ( ?, ?, ?, ?, ? );', ( hash_id, canvas_type, 0, 0, 0 ) )
        
        self._Execute( 'UPDATE file_viewing_stats SET last_viewed_timestamp_ms = ?, views = views + ?, viewtime = viewtime + ? WHERE hash_id = ? AND canvas_type = ?;', ( view_timestamp_ms, views_delta, viewtime_delta, hash_id, canvas_type ) )
        
    
    def ClearAllStats( self ):
        
        self._Execute( 'DELETE FROM file_viewing_stats;' )
        
    
    def ClearViews( self, hash_ids ):
        
        self._ExecuteMany( 'DELETE FROM file_viewing_stats WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def CullFileViewingStatistics( self ):
        
        media_min = CG.client_controller.new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time' )
        media_max = CG.client_controller.new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time' )
        preview_min = CG.client_controller.new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time' )
        preview_max = CG.client_controller.new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time' )
        
        if media_min is not None and media_max is not None and media_min > media_max:
            
            raise Exception( 'Media min was greater than media max! Abandoning cull now!' )
            
        
        if preview_min is not None and preview_max is not None and preview_min > preview_max:
            
            raise Exception( 'Preview min was greater than preview max! Abandoning cull now!' )
            
        
        if media_min is not None:
            
            self._Execute( 'UPDATE file_viewing_stats SET views = CAST( viewtime / ? AS INTEGER ) WHERE views * ? > viewtime AND canvas_type = ?;', ( media_min, media_min, CC.CANVAS_MEDIA_VIEWER ) )
            
        
        if media_max is not None:
            
            self._Execute( 'UPDATE file_viewing_stats SET viewtime = views * ? WHERE viewtime > views * ? AND canvas_type = ?;', ( media_max, media_max, CC.CANVAS_MEDIA_VIEWER ) )
            
        
        if preview_min is not None:
            
            self._Execute( 'UPDATE file_viewing_stats SET views = CAST( viewtime / ? AS INTEGER ) WHERE views * ? > viewtime AND canvas_type = ?;', ( preview_min, preview_min, CC.CANVAS_PREVIEW ) )
            
        
        if preview_max is not None:
            
            self._Execute( 'UPDATE file_viewing_stats SET viewtime = views * ? WHERE viewtime > views * ? AND canvas_type = ?;', ( preview_max, preview_max, CC.CANVAS_PREVIEW ) )
            
        
    
    def GetHashIdsFromFileViewingStatistics( self, view_type, viewing_locations, operator, viewing_value ) -> typing.Set[ int ]:
        
        # only works for positive values like '> 5'. won't work for '= 0' or '< 1' since those are absent from the table
        
        include_media = 'media' in viewing_locations
        include_preview = 'preview' in viewing_locations
        
        canvas_type_predicate = '1=1'
        group_by_phrase = ''
        having_phrase = ''
        
        if view_type == 'views':
            
            content_phrase = 'views'
            
        elif view_type == 'viewtime':
            
            content_phrase = 'viewtime'
            
        else:
            
            return set()
            
        
        if include_media and include_preview:
            
            group_by_phrase = ' GROUP BY hash_id'
            
            if view_type == 'views':
                
                content_phrase = 'SUM( views )'
                
            elif view_type == 'viewtime':
                
                content_phrase = 'SUM( viewtime )'
                
            
        elif include_media:
            
            canvas_type_predicate = 'canvas_type = {}'.format( CC.CANVAS_MEDIA_VIEWER )
            
        elif include_preview:
            
            canvas_type_predicate = 'canvas_type = {}'.format( CC.CANVAS_PREVIEW )
            
        else:
            
            return set()
            
        
        if operator == HC.UNICODE_APPROX_EQUAL:
            
            lower_bound = int( 0.8 * viewing_value )
            upper_bound = int( 1.2 * viewing_value )
            
            test_phrase = '{} BETWEEN {} AND {}'.format( content_phrase, str( lower_bound ), str( upper_bound ) )
            
        else:
            
            test_phrase = '{} {} {}'.format( content_phrase, operator, str( viewing_value ) )
            
        
        if include_media and include_preview:
            
            select_statement = 'SELECT hash_id FROM file_viewing_stats {} HAVING {};'.format( group_by_phrase, test_phrase )
            
        else:
            
            select_statement = 'SELECT hash_id FROM file_viewing_stats WHERE {} AND {}{};'.format( test_phrase, canvas_type_predicate, group_by_phrase )
            
        
        hash_ids = self._STS( self._Execute( select_statement ) )
        
        return hash_ids
        
    
    def GetHashIdsFromLastViewed( self, min_last_viewed_timestamp_ms = None, max_last_viewed_timestamp_ms = None, job_status: typing.Optional[ ClientThreading.JobStatus ] = None ) -> typing.Set[ int ]:
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        last_viewed_timestamp_predicates = []
        
        if min_last_viewed_timestamp_ms is not None: last_viewed_timestamp_predicates.append( 'last_viewed_timestamp_ms >= ' + str( min_last_viewed_timestamp_ms ) )
        if max_last_viewed_timestamp_ms is not None: last_viewed_timestamp_predicates.append( 'last_viewed_timestamp_ms <= ' + str( max_last_viewed_timestamp_ms ) )
        
        if len( last_viewed_timestamp_predicates ) == 0:
            
            return set()
            
        
        pred_string = ' AND '.join( last_viewed_timestamp_predicates )
        
        return self._STS( self._ExecuteCancellable( 'SELECT hash_id FROM file_viewing_stats WHERE canvas_type = ? AND {};'.format( pred_string ), ( CC.CANVAS_MEDIA_VIEWER, ), cancelled_hook ) )
        
    
    def GetHashIdsToFileViewingStatsRows( self, hash_ids_table_name ):
        
        query = 'SELECT hash_id, canvas_type, last_viewed_timestamp_ms, views, viewtime FROM {} CROSS JOIN file_viewing_stats USING ( hash_id );'.format( hash_ids_table_name )
        
        return HydrusData.BuildKeyToListDict( ( ( hash_id, ( canvas_type, last_viewed_timestamp_ms, views, viewtime ) ) for ( hash_id, canvas_type, last_viewed_timestamp_ms, views, viewtime ) in self._Execute( query ) ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_viewing_stats', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
    def GetTimestampMS( self, hash_id: int, timestamp_data: ClientTime.TimestampData ) -> typing.Optional[ int ]:
        
        if timestamp_data.location is None:
            
            return
            
        
        result = self._Execute( 'SELECT last_viewed_timestamp_ms FROM file_viewing_stats WHERE canvas_type = ? AND hash_id = ?;', ( timestamp_data.location, hash_id ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( timestamp_ms, ) = result
            
            return timestamp_ms
            
        
    
    def SetTime( self, hash_ids: typing.Collection[ int ], timestamp_data: ClientTime.TimestampData ):
        
        if timestamp_data.location is None:
            
            return
            
        
        if timestamp_data.timestamp_ms is None:
            
            return
            
        
        self._ExecuteMany( 'UPDATE file_viewing_stats SET last_viewed_timestamp_ms = ? WHERE canvas_type = ? and hash_id = ?;', ( ( timestamp_data.timestamp_ms, timestamp_data.location, hash_id ) for hash_id in hash_ids ) )
        
    
