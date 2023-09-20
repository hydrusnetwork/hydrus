import typing

from hydrus.core import HydrusExceptions

def BaseGenerateThumbnailNumPyFromPDFPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    raise HydrusExceptions.NoThumbnailFileException()
    

def BaseGetPDFInfo( path: str ):
    
    raise HydrusExceptions.LimitedSupportFileException()
    

GenerateThumbnailNumPyFromPDFPath = BaseGenerateThumbnailNumPyFromPDFPath
GetPDFInfo = BaseGetPDFInfo
