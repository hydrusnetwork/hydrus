from hydrus.core import HydrusExceptions

def BaseGenerateThumbnailNumPyFromPDFPath( path: str, target_resolution: tuple[int, int] ) -> bytes:
    
    raise HydrusExceptions.NoThumbnailFileException()
    

def BaseGetPDFInfo( path: str ):
    
    raise HydrusExceptions.LimitedSupportFileException()
    

GenerateThumbnailNumPyFromPDFPath = BaseGenerateThumbnailNumPyFromPDFPath
GetPDFInfo = BaseGetPDFInfo
