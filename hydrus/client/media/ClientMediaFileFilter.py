import itertools
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusText
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

FILE_FILTER_ALL = 0
FILE_FILTER_NOT_SELECTED = 1
FILE_FILTER_NONE = 2
FILE_FILTER_INBOX = 3
FILE_FILTER_ARCHIVE = 4
FILE_FILTER_FILE_SERVICE = 5
FILE_FILTER_LOCAL = 6
FILE_FILTER_REMOTE = 7
FILE_FILTER_TAGS = 8
FILE_FILTER_SELECTED = 9
FILE_FILTER_MIME = 10

file_filter_str_lookup = {
    FILE_FILTER_ALL : 'all',
    FILE_FILTER_NOT_SELECTED : 'not selected',
    FILE_FILTER_SELECTED : 'selected',
    FILE_FILTER_NONE : 'none',
    FILE_FILTER_INBOX : 'inbox',
    FILE_FILTER_ARCHIVE : 'archive',
    FILE_FILTER_FILE_SERVICE : 'file service',
    FILE_FILTER_LOCAL : 'local',
    FILE_FILTER_REMOTE : 'not local',
    FILE_FILTER_TAGS : 'tags',
    FILE_FILTER_MIME : 'filetype'
}

quick_inverse_lookups = {}

class FileFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_FILTER
    SERIALISABLE_NAME = 'File Filter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, filter_type = None, filter_data = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.filter_type = filter_type
        self.filter_data = filter_data
        
    
    def __eq__( self, other ):
        
        if isinstance( other, FileFilter ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        if self.filter_data is None:
            
            return self.filter_type.__hash__()
            
        else:
            
            return ( self.filter_type, self.filter_data ).__hash__()
            
        
    
    def _GetSerialisableInfo( self ):
        
        if self.filter_type == FILE_FILTER_FILE_SERVICE:
            
            file_service_key = self.filter_data
            
            serialisable_filter_data = file_service_key.hex()
            
        elif self.filter_type == FILE_FILTER_TAGS:
            
            ( tag_service_key, and_or_or, select_tags ) = self.filter_data
            
            serialisable_filter_data = ( tag_service_key.hex(), and_or_or, select_tags )
            
        else:
            
            serialisable_filter_data = self.filter_data
            
        
        return ( self.filter_type, serialisable_filter_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.filter_type, serialisable_filter_data ) = serialisable_info
        
        if self.filter_type == FILE_FILTER_FILE_SERVICE:
            
            serialisable_file_service_key = serialisable_filter_data
            
            file_service_key = bytes.fromhex( serialisable_file_service_key )
            
            self.filter_data = file_service_key
            
        elif self.filter_type == FILE_FILTER_TAGS:
            
            ( serialisable_tag_service_key, and_or_or, select_tags ) = serialisable_filter_data
            
            tag_service_key = bytes.fromhex( serialisable_tag_service_key )
            
            self.filter_data = ( tag_service_key, and_or_or, select_tags )
            
        else:
            
            self.filter_data = serialisable_filter_data
            
        
    
    def GetMediaListFileCount( self, media_list: ClientMedia.MediaList ):
        
        if self.filter_type == FILE_FILTER_ALL:
            
            return media_list.GetNumFiles()
            
        elif self.filter_type == FILE_FILTER_SELECTED:
            
            selected_media = media_list.GetSelectedMedia()
            
            return sum( ( m.GetNumFiles() for m in selected_media ) )
            
        elif self.filter_type == FILE_FILTER_NOT_SELECTED:
            
            selected_media = media_list.GetSelectedMedia()
            
            return media_list.GetNumFiles() - sum( ( m.GetNumFiles() for m in selected_media ) )
            
        elif self.filter_type == FILE_FILTER_NONE:
            
            return 0
            
        elif self.filter_type == FILE_FILTER_INBOX:
            
            selected_media = media_list.GetSelectedMedia()
            
            return sum( ( m.GetNumInbox() for m in selected_media ) )
            
        elif self.filter_type == FILE_FILTER_ARCHIVE:
            
            selected_media = media_list.GetSelectedMedia()
            
            return media_list.GetNumFiles() - sum( ( m.GetNumInbox() for m in selected_media ) )
            
        else:
            
            flat_media = media_list.GetFlatMedia()
            
            if self.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = self.filter_data
                
                return sum( ( 1 for m in flat_media if file_service_key in m.GetLocationsManager().GetCurrent() ) )
                
            elif self.filter_type == FILE_FILTER_LOCAL:
                
                return sum( ( 1 for m in flat_media if m.GetLocationsManager().IsLocal() ) )
                
            elif self.filter_type == FILE_FILTER_REMOTE:
                
                return sum( ( 1 for m in flat_media if m.GetLocationsManager().IsRemote() ) )
                
            elif self.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = self.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    return sum( ( 1 for m in flat_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ) ) )
                    
                elif and_or_or == 'OR':
                    
                    return sum( ( 1 for m in flat_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ), select_tags ) ) )
                    
                
            
        
        return 0
        
    
    def GetMediaListHashes( self, media_list: ClientMedia.MediaList ):
        
        if self.filter_type == FILE_FILTER_ALL:
            
            return media_list.GetHashes()
            
        elif self.filter_type == FILE_FILTER_SELECTED:
            
            hashes = set()
            
            for m in media_list.GetSelectedMedia():
                
                hashes.update( m.GetHashes() )
                
            
            return hashes
            
        elif self.filter_type == FILE_FILTER_NOT_SELECTED:
            
            hashes = set()
            
            for m in media_list.GetSortedMedia():
                
                if m not in media_list.GetSelectedMedia():
                    
                    hashes.update( m.GetHashes() )
                    
                
            
            return hashes
            
        elif self.filter_type == FILE_FILTER_NONE:
            
            return set()
            
        else:
            
            flat_media = media_list.GetFlatMedia()
            
            if self.filter_type == FILE_FILTER_INBOX:
                
                filtered_media = [ m for m in flat_media if m.HasInbox() ]
                
            elif self.filter_type == FILE_FILTER_ARCHIVE:
                
                filtered_media = [ m for m in flat_media if not m.HasInbox() ]
                
            elif self.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = self.filter_data
                
                filtered_media = [ m for m in flat_media if file_service_key in m.GetLocationsManager().GetCurrent() ]
                
            elif self.filter_type == FILE_FILTER_LOCAL:
                
                filtered_media = [ m for m in flat_media if m.GetLocationsManager().IsLocal() ]
                
            elif self.filter_type == FILE_FILTER_REMOTE:
                
                filtered_media = [ m for m in flat_media if m.GetLocationsManager().IsRemote() ]
                
            elif self.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = self.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    filtered_media = [ m for m in flat_media if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ) ]
                    
                elif and_or_or == 'OR':
                    
                    filtered_media = [ m for m in flat_media if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ), select_tags ) ]
                    
                
            
            hashes = { m.GetHash() for m in filtered_media }
            
            return hashes
            
        
    
    def GetMediaListMedia( self, media_list: ClientMedia.MediaList ):
        
        if self.filter_type == FILE_FILTER_ALL:
            
            return set( media_list.GetSortedMedia() )
            
        elif self.filter_type == FILE_FILTER_SELECTED:
            
            return media_list.GetSelectedMedia()
            
        elif self.filter_type == FILE_FILTER_NOT_SELECTED:
            
            return { m for m in media_list.GetSortedMedia() if m not in media_list.GetSelectedMedia() }
            
        elif self.filter_type == FILE_FILTER_NONE:
            
            return set()
            
        else:
            
            if self.filter_type == FILE_FILTER_INBOX:
                
                filtered_media = { m for m in media_list.GetSortedMedia() if m.HasInbox() }
                
            elif self.filter_type == FILE_FILTER_ARCHIVE:
                
                filtered_media = { m for m in media_list.GetSortedMedia() if not m.HasInbox() }
                
            elif self.filter_type == FILE_FILTER_FILE_SERVICE:
                
                file_service_key = self.filter_data
                
                filtered_media = { m for m in media_list.GetSortedMedia() if file_service_key in m.GetLocationsManager().GetCurrent() }
                
            elif self.filter_type == FILE_FILTER_LOCAL:
                
                filtered_media = { m for m in media_list.GetSortedMedia() if m.GetLocationsManager().IsLocal() }
                
            elif self.filter_type == FILE_FILTER_REMOTE:
                
                filtered_media = { m for m in media_list.GetSortedMedia() if m.GetLocationsManager().IsRemote() }
                
            elif self.filter_type == FILE_FILTER_TAGS:
                
                ( tag_service_key, and_or_or, select_tags ) = self.filter_data
                
                if and_or_or == 'AND':
                    
                    select_tags = set( select_tags )
                    
                    filtered_media = { m for m in media_list.GetSortedMedia() if select_tags.issubset( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ) }
                    
                elif and_or_or == 'OR':
                    
                    filtered_media = { m for m in media_list.GetSortedMedia() if HydrusData.SetsIntersect( m.GetTagsManager().GetCurrentAndPending( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ), select_tags ) }
                    
                
            
            return filtered_media
            
        
    
    def PopulateFilterCounts( self, media_list: ClientMedia.MediaList, filter_counts: dict ):
        
        if self not in filter_counts:
            
            if self.filter_type == FILE_FILTER_NONE:
                
                filter_counts[ self ] = 0
                
                return
                
            
            if self in quick_inverse_lookups:
                
                inverse = quick_inverse_lookups[ self ]
                
                all_filter = FileFilter( FILE_FILTER_ALL )
                
                if all_filter in filter_counts and inverse in filter_counts:
                    
                    filter_counts[ self ] = filter_counts[ all_filter ] - filter_counts[ inverse ]
                    
                    return
                    
                
            
            count = self.GetMediaListFileCount( media_list )
            
            filter_counts[ self ] = count
            
        
    
    def GetCount( self, media_list: ClientMedia.MediaList, filter_counts: dict ):
        
        self.PopulateFilterCounts( media_list, filter_counts )
        
        return filter_counts[ self ]
        
    
    def ToString( self ):
        
        if self.filter_type == FILE_FILTER_FILE_SERVICE:
            
            file_service_key = self.filter_data
            
            s = CG.client_controller.services_manager.GetName( file_service_key )
            
        elif self.filter_type == FILE_FILTER_TAGS:
            
            ( tag_service_key, and_or_or, select_tags ) = self.filter_data
            
            s = and_or_or.join( select_tags )
            
            if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY:
                
                s = '{} on {}'.format( s, CG.client_controller.services_manager.GetName( tag_service_key ) )
                
            
            s = HydrusText.ElideText( s, 64 )
            
        elif self.filter_type == FILE_FILTER_MIME:
            
            mime = self.filter_data
            
            s = HC.mime_string_lookup[ mime ]
            
        else:
            
            s = file_filter_str_lookup[ self.filter_type ]
            
        
        return s
        
    
    def ToStringWithCount( self, media_list: ClientMedia.MediaList, filter_counts: dict ):
        
        s = self.ToString()
        
        self.PopulateFilterCounts( media_list, filter_counts )
        
        my_count = filter_counts[ self ]
        
        s += ' ({})'.format( HydrusData.ToHumanInt( my_count ) )
        
        if self.filter_type == FILE_FILTER_ALL:
            
            inbox_filter = FileFilter( FILE_FILTER_INBOX )
            archive_filter = FileFilter( FILE_FILTER_ARCHIVE )
            
            inbox_filter.PopulateFilterCounts( media_list, filter_counts )
            archive_filter.PopulateFilterCounts( media_list, filter_counts )
            
            inbox_count = filter_counts[ inbox_filter ]
            
            if inbox_count > 0 and inbox_count == my_count:
                
                s += ' (all in inbox)'
                
            else:
                
                archive_count = filter_counts[ archive_filter ]
                
                if archive_count > 0 and archive_count == my_count:
                    
                    s += ' (all in archive)'
                    
                
            
        
        return s
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_FILTER ] = FileFilter

quick_inverse_lookups.update( {
    FileFilter( FILE_FILTER_INBOX ) : FileFilter( FILE_FILTER_ARCHIVE ),
    FileFilter( FILE_FILTER_ARCHIVE ) : FileFilter( FILE_FILTER_INBOX ),
    FileFilter( FILE_FILTER_SELECTED ) : FileFilter( FILE_FILTER_NOT_SELECTED ),
    FileFilter( FILE_FILTER_NOT_SELECTED ) : FileFilter( FILE_FILTER_SELECTED ),
    FileFilter( FILE_FILTER_LOCAL ) : FileFilter( FILE_FILTER_REMOTE ),
    FileFilter( FILE_FILTER_REMOTE ) : FileFilter( FILE_FILTER_LOCAL )
} )

def FilterAndReportDeleteLockFailures( medias: typing.Collection[ ClientMedia.Media ] ):
    
    # TODO: update this system with some texts like 'file was archived' so user can know how to fix the situation
    
    deletee_medias = [ media for media in medias if not media.HasDeleteLocked() ]
    
    if len( deletee_medias ) < len( medias ):
        
        locked_medias = [ media for media in medias if media.HasDeleteLocked() ]
        
        ReportDeleteLockFailures( locked_medias )
        
    
    return deletee_medias
    

def ReportDeleteLockFailures( medias: typing.Collection[ ClientMedia.Media ] ):
    
    job_status = ClientThreading.JobStatus()
    
    message = 'Was unable to delete one or more files because of a delete lock!'
    
    job_status.SetStatusText( message )
    
    hashes = list( itertools.chain.from_iterable( ( media.GetHashes() for media in medias ) ) )
    
    job_status.SetFiles( hashes, 'see them' )
    
    CG.client_controller.pub( 'message', job_status )
    
