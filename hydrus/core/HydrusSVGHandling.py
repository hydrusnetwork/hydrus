import typing

from hydrus.core import HydrusExceptions

def BaseGenerateThumbnailBytesFromSVGPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    raise HydrusExceptions.NoThumbnailFileException()
    

def BaseGetSVGResolution( path: str ):
    
    raise HydrusExceptions.NoResolutionFileException()
    

GenerateThumbnailBytesFromSVGPath = BaseGenerateThumbnailBytesFromSVGPath
GetSVGResolution = BaseGetSVGResolution
