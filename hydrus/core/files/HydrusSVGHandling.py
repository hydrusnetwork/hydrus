from hydrus.core import HydrusExceptions

def BaseGenerateThumbnailNumPyFromSVGPath( path: str, target_resolution: tuple[int, int] ) -> bytes:
    
    raise HydrusExceptions.NoThumbnailFileException()
    

def BaseGetSVGResolution( path: str ):
    
    raise HydrusExceptions.NoResolutionFileException()
    

GenerateThumbnailNumPyFromSVGPath = BaseGenerateThumbnailNumPyFromSVGPath
GetSVGResolution = BaseGetSVGResolution
