import io
import json

from hydrus.core import HydrusConstants as HC
from hydrus.core.files import HydrusUgoiraHandling
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files import HydrusArchiveHandling

from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMediaResult

UGOIRA_DEFAULT_FRAME_DURATION_MS = 125

def GetFrameDurationsMSUgoira( media: ClientMediaResult.MediaResult ): 
    
    client_files_manager = CG.client_controller.client_files_manager
    
    path = client_files_manager.GetFilePath( media.GetHash(), media.GetMime() )
    
    try:
        
        frameData = HydrusUgoiraHandling.GetUgoiraFrameDataJSON( path )
        
        if frameData is not None:
            
            durations_ms = [data['delay'] for data in frameData]
            
            return durations_ms
            
        
    except Exception as e:
        
        pass
        
    
    try:
        
        durations_ms = GetFrameDurationsMSFromNote( media )
        
        if durations_ms is not None:
            
            return durations_ms
            
        
    except Exception as e:
        
        pass
        
    
    num_frames = media.GetNumFrames()
    
    if num_frames == 0 or num_frames is None:
        
        num_frames = 1
        
    
    return [UGOIRA_DEFAULT_FRAME_DURATION_MS] * num_frames
    

def GetFrameDurationsMSFromNote( media: ClientMediaResult.MediaResult ):
    
    if not media.HasNotes():
        
        return None
        
    
    noteManager = media.GetNotesManager()
    
    notes = noteManager.GetNamesToNotes()
    
    if 'ugoira json' in notes:
        
        try:
            
            ugoiraJson = json.loads(notes['ugoira json'])
            
            if isinstance(ugoiraJson, list):
                
                frameData: list[HydrusUgoiraHandling.UgoiraFrame] = ugoiraJson
                
            else:
                
                frameData: list[HydrusUgoiraHandling.UgoiraFrame] = ugoiraJson['frames']
                
            
            frame_durations_ms = [data['delay'] for data in frameData]
            
            if len(frame_durations_ms) > 0 and isinstance(frame_durations_ms[0], int):
                
                return frame_durations_ms 
                
            
        except Exception as e:
            
            pass
            
        
    
    if 'ugoira frame delay array' in notes:
        
        try:
            
            ugoiraJsonArray: list[int] = json.loads(notes['ugoira frame delay array'])
            
            if len(ugoiraJsonArray) > 0 and isinstance(ugoiraJsonArray[0], int):
                
                return ugoiraJsonArray
                
            
        except Exception as e:
            
            pass
            
        
    
    return None
    

def HasFrameTimesNote( media_result: ClientMediaResult.MediaResult ):
    
    if not media_result.HasNotes():
        
        return False
        
    
    names_to_notes = media_result.GetNotesManager().GetNamesToNotes()
    
    return 'ugoira json' in names_to_notes or 'ugoira frame delay array' in names_to_notes
    

class UgoiraRenderer(object):

    def __init__( self, path, num_frames, target_resolution ):

        self._path = path
        self._num_frames = num_frames
        self._target_resolution = target_resolution

        self._next_render_index = 0

        self._frame_data = HydrusUgoiraHandling.GetFramePathsUgoira( path )

        self._zip = HydrusArchiveHandling.GetZipAsPath( path )

    def set_position( self, index ):

        self._next_render_index = index

    def Stop(self):

        pass

    def read_frame(self):

        frame_name = self._frame_data[self._next_render_index]

        with self._zip.joinpath(frame_name).open('rb') as frame_from_zip:

            pil_image = HydrusImageHandling.GeneratePILImage( frame_from_zip )

            numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( pil_image )

        numpy_image = HydrusImageHandling.ResizeNumPyImage( numpy_image, self._target_resolution )

        self._next_render_index = ( self._next_render_index + 1 ) % self._num_frames

        return numpy_image

def ConvertUgoiraToBytesForAPI( media: ClientMediaResult.MediaResult, format: int, quality: int ):
    
    client_files_manager = CG.client_controller.client_files_manager
    
    path = client_files_manager.GetFilePath( media.GetHash(), media.GetMime() )
    
    frame_paths = HydrusUgoiraHandling.GetFramePathsUgoira( path )

    zip = HydrusArchiveHandling.GetZipAsPath( path )
    
    frames = [HydrusImageHandling.GeneratePILImage( zip.joinpath(frame_path_from_zip).open('rb') ) for frame_path_from_zip in frame_paths]
    
    frame_durations_ms = GetFrameDurationsMSUgoira( media )
    
    file = io.BytesIO()
    
    if format == HC.ANIMATION_APNG:

        frames[0].save(
            file,
            'PNG',
            save_all=True,
            append_images=frames[1:],
            duration=frame_durations_ms,
            loop=0,  # loop forever
            #compress_level = quality # seems to have no effect for APNG
        )
        
    elif format == HC.ANIMATION_WEBP:

        frames[0].save(
            file,
            'WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=frame_durations_ms,
            loop=0,  # loop forever
            quality = quality - 100 if quality > 100 else quality,
            lossless = quality > 100
        )
    
    file_bytes = file.getvalue()
    
    file.close()
    
    return file_bytes
