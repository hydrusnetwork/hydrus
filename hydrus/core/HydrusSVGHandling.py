import typing

from hydrus.core import HydrusExceptions

def BaseGenerateThumbnailBytesFromSVGPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    raise HydrusExceptions.UnsupportedFileException()
    

def BaseGetSVGResolution( path: str ):
    
    return ( None, None )
    

GenerateThumbnailBytesFromSVGPath = BaseGenerateThumbnailBytesFromSVGPath
GetSVGResolution = BaseGetSVGResolution
