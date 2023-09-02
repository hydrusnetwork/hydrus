import typing

from hydrus.core import HydrusExceptions

def BaseGenerateThumbnailBytesFromPDFPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    raise HydrusExceptions.UnsupportedFileException()
    

def BaseGetPDFResolution( path: str ):
    
    return ( None, None )
    

GenerateThumbnailBytesFromPDFPath = BaseGenerateThumbnailBytesFromPDFPath
GetPDFResolution = BaseGetPDFResolution
