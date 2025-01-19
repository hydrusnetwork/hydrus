from PIL import Image as PILImage
import warnings

if not hasattr( PILImage, 'DecompressionBombError' ):
    
    # super old versions don't have this, so let's just make a stub, wew
    
    class DBEStub( Warning ):
        
        pass
        
    
    PILImage.DecompressionBombError = DBEStub
    

if not hasattr( PILImage, 'DecompressionBombWarning' ):
    
    # super old versions don't have this, so let's just make a stub, wew
    
    class DBWStub( Warning ):
        
        pass
        
    
    PILImage.DecompressionBombWarning = DBWStub
    

warnings.simplefilter( 'ignore', PILImage.DecompressionBombWarning )
warnings.simplefilter( 'ignore', PILImage.DecompressionBombError )

# PIL moaning about weirdo TIFFs
warnings.filterwarnings( "ignore", "(Possibly )?corrupt EXIF data", UserWarning )
warnings.filterwarnings( "ignore", "Metadata Warning", UserWarning )

# PIL moaning about weirdo PNGs
warnings.filterwarnings( "ignore", "iTXt: chunk data is too large", UserWarning )
