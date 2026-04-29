from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

class MediaSingle( ClientMedia.Media ):
    
    def __init__( self, media_result: ClientMediaResult.MediaResult ):
        
        super().__init__()
        
        self._media_result = media_result
        
    
    def Duplicate( self ):
        
        return MediaSingle( self._media_result.Duplicate() )
        
    
    def GetDisplayMedia( self ) -> "MediaSingle | None":
        
        return self
        
    
    def GetDisplayMediaResult( self ) -> ClientMediaResult.MediaResult | None:
        
        return self._media_result
        
    
    def GetDurationMS( self ):
        
        return self._media_result.GetDurationMS()
        
    
    def GetEarliestHashId( self ):
        
        return self._media_result.GetFileInfoManager().hash_id
        
    
    def GetFileInfoManager( self ):
        
        return self._media_result.GetFileInfoManager()
        
    
    def GetFileViewingStatsManager( self ):
        
        return self._media_result.GetFileViewingStatsManager()
        
    
    def GetFlatMedia( self ):
        
        return [ self ]
        
    
    def GetFramerate( self ):
        
        return self._media_result.GetFileInfoManager().GetFramerate()
        
    
    def GetHash( self ):
        
        return self._media_result.GetHash()
        
    
    def GetHashId( self ):
        
        return self._media_result.GetHashId()
        
    
    def GetHashes( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None, ordered = False ):
        
        if self.MatchesDiscriminant( is_in_file_service_key = is_in_file_service_key, discriminant = discriminant, is_not_in_file_service_key = is_not_in_file_service_key ):
            
            if ordered:
                
                return [ self._media_result.GetHash() ]
                
            else:
                
                return { self._media_result.GetHash() }
                
            
        else:
            
            if ordered:
                
                return []
                
            else:
                
                return set()
                
            
        
    
    def GetLocationsManager( self ):
        
        return self._media_result.GetLocationsManager()
        
    
    def GetMediaResult( self ):
        
        return self._media_result
        
    
    def GetMime( self ):
        
        return self._media_result.GetMime()
        
    
    def GetNotesManager( self ) -> ClientMediaManagers.NotesManager:
        
        return self._media_result.GetNotesManager()
        
    
    def GetNumFiles( self ): return 1
    
    def GetNumFrames( self ): return self._media_result.GetNumFrames()
    
    def GetNumInbox( self ):
        
        if self.HasInbox(): return 1
        else: return 0
        
    
    def GetNumWords( self ): return self._media_result.GetNumWords()
    
    def GetRatingsManager( self ): return self._media_result.GetRatingsManager()
    
    def GetResolution( self ):
        
        return self._media_result.GetResolution()
        
    
    def GetSize( self ):
        
        size = self._media_result.GetSize()
        
        if size is None: return 0
        else: return size
        
    
    def GetTagsManager( self ):
        
        return self._media_result.GetTagsManager()
        
    
    def GetTimesManager( self ):
        
        return self._media_result.GetTimesManager()
        
    
    def GetTitleString( self ):
        
        new_options = CG.client_controller.new_options
        
        tag_summary_generator = new_options.GetTagSummaryGenerator( 'media_viewer_top' )
        
        tags = self.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        
        if len( tags ) == 0:
            
            return ''
            
        
        summary = tag_summary_generator.GenerateSummary( tags )
        
        return summary
        
    
    def HasAnyOfTheseHashes( self, hashes ):
        
        return self._media_result.GetHash() in hashes
        
    
    def HasArchive( self ):
        
        return not self._media_result.GetInbox()
        
    
    def HasAudio( self ):
        
        return self._media_result.HasAudio()
        
    
    def IsPhysicalDeleteLocked( self ):
        
        return self._media_result.IsPhysicalDeleteLocked()
        
    
    def HasDuration( self ):
        
        return self._media_result.HasDuration()
        
    
    def HasSimulatedDuration( self ) -> bool:
        
        return self._media_result.HasSimulatedDuration()
        
    
    def HasStaticImages( self ):
        
        return self.IsStaticImage()
        
    
    def HasInbox( self ):
        
        return self._media_result.GetInbox()
        
    
    def HasNotes( self ):
        
        return self._media_result.HasNotes()
        
    
    def HasUsefulResolution( self ):
        
        return self._media_result.HasUsefulResolution()
        
    
    def IsCollection( self ):
        
        return False
        
    
    def IsSizeDefinite( self ):
        
        return self._media_result.GetSize() is not None
        
    
    def IsStaticImage( self ):
        
        return self._media_result.IsStaticImage()
        
    
    def MatchesDiscriminant( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None ):
        
        if discriminant is not None:
            
            inbox = self._media_result.GetInbox()
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if discriminant == CC.DISCRIMINANT_INBOX:
                
                p = inbox
                
            elif discriminant == CC.DISCRIMINANT_ARCHIVE:
                
                p = not inbox
                
            elif discriminant == CC.DISCRIMINANT_LOCAL:
                
                p = locations_manager.IsLocal()
                
            elif discriminant == CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH:
                
                p = locations_manager.IsLocal() and not locations_manager.IsTrashed()
                
            elif discriminant == CC.DISCRIMINANT_NOT_LOCAL:
                
                p = not locations_manager.IsLocal()
                
            elif discriminant == CC.DISCRIMINANT_DOWNLOADING:
                
                p = locations_manager.IsDownloading()
                
            
            if not p:
                
                return False
                
            
        
        if is_in_file_service_key is not None:
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if is_in_file_service_key not in locations_manager.GetCurrent():
                
                return False
                
            
        
        if is_not_in_file_service_key is not None:
            
            locations_manager = self._media_result.GetLocationsManager()
            
            if is_not_in_file_service_key in locations_manager.GetCurrent():
                
                return False
                
            
        
        return True
        
    
