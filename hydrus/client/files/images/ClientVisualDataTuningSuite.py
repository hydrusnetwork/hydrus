import os
import random

from PIL import Image as PILImage
from PIL import ImageDraw as PILDraw

from hydrus.core import HydrusPaths
from hydrus.core.files.images import HydrusImageHandling

pil_subsampling_lookup = {
    444 : '4:4:4',
    422 : '4:2:2',
    420 : '4:2:0'
}

def save_file( pil_image, out_dir, base_filename, suffix ):
    
    quality = random.randint( 60, 90 )
    subsampling = random.choice( ( 444, 422, 420 ) )
    
    dest_filename = f'{base_filename}_{quality}_{subsampling}_{suffix}.jpg'
    
    dest_path = os.path.join( out_dir, dest_filename )
    
    pil_image.save( dest_path, 'JPEG', quality = quality, subsampling = pil_subsampling_lookup[ subsampling ] )
    
    return ( dest_path, quality, subsampling )
    

def RunTuningSuite( test_dir: str ):
    
    out_dir = os.path.join( test_dir, 'out' )
    
    # clear out last test
    if os.path.exists( out_dir ):
        
        HydrusPaths.DeletePath( out_dir )
        
    
    reports = []
    
    source_filenames = os.listdir( test_dir )
    
    HydrusPaths.MakeSureDirectoryExists( out_dir )
    
    for source_filename in source_filenames:
        
        source_path = os.path.join( test_dir, source_filename )
        
        pil_image = HydrusImageHandling.GeneratePILImage( source_path )
        
        ( width, height ) = pil_image.size
        
        good_paths = set()
        
        correction_paths = set()
        watermark_paths = set()
        recolour_paths = set()
        
        ( base_filename, jpeg_gumpf ) = source_filename.rsplit( '.', 1 )
        
        for i in range( 10 ):
            
            good_paths.add( save_file( pil_image, out_dir, base_filename, 'original' ) )
            
            #
            
            scale = random.randint( 50, 85 ) / 100
            
            pil_image_smaller = pil_image.resize( ( int( width * scale ), int( height * scale ) ), PILImage.Resampling.LANCZOS )
            
            good_paths.add( save_file( pil_image_smaller, out_dir, base_filename, 'smaller' ) )
            #
            
            # ok let's draw a soft grey line over our image to be a correction
            
            pil_image_rgba = pil_image.convert( 'RGBA' )
            
            canvas = PILImage.new( 'RGBA', pil_image_rgba.size, ( 255, 255, 255, 0 ) )
            
            draw = PILDraw.Draw( canvas )
            
            x1 = random.randint( int( width / 4 ), int( width / 2 ) )
            y1 = random.randint( int( height / 4 ), int( height / 2 ) )
            x2 = x1 + random.randint( int( width / 16 ), int( width / 12 ) )
            y2 = y1 + random.randint( int( height / 16 ), int( height / 12 ) )
            
            line_width = int( width / 200 )
            
            draw.line( ( x1, y1, x2, y2 ), fill = ( 128, 128, 128, 128 ), width = line_width )
            
            pil_image_rgba = PILImage.alpha_composite( pil_image_rgba, canvas )
            
            del draw
            
            pil_image_correction = pil_image_rgba.convert( 'RGB' )
            
            correction_paths.add( save_file( pil_image_correction, out_dir, base_filename, 'correction' ) )
            
            #
            
            # and now a box to be our watermark
            
            pil_image_rgba = pil_image.convert( 'RGBA' )
            
            canvas = PILImage.new( 'RGBA', pil_image_rgba.size, ( 255, 255, 255, 0 ) )
            
            draw = PILDraw.Draw( canvas )
            
            x1 = random.randint( int( width / 4 ), int( width / 2 ) )
            y1 = random.randint( int( height / 4 ), int( height / 2 ) )
            x2 = x1 + random.randint( int( width / 20 ), int( width / 10 ) )
            y2 = y1 + random.randint( int( height / 20 ), int( height / 10 ) )
            
            line_width = int( width / 50 )
            
            draw.rectangle( ( x1, y1, x2, y2 ), outline = ( 128, 128, 128, 64 ), width = line_width )
            
            pil_image_rgba = PILImage.alpha_composite( pil_image_rgba, canvas )
            
            del draw
            
            pil_image_watermark = pil_image_rgba.convert( 'RGB' )
            
            watermark_paths.add( save_file( pil_image_watermark, out_dir, base_filename, 'watermark' ) )
            
            #
            
            ( r, g, b ) = pil_image.split()
            
            recoloured_pil_image = PILImage.merge( 'RGB', ( b, g, r ) )
            
            recolour_paths.add( save_file( recoloured_pil_image, out_dir, base_filename, 'recolour' ) )
            
        
    
    # run the good files against each other and the bad files. nice fat sample. record the different variables
    # in the first stage, report ranges of the variables for each class of True/False match 'all watermarks had skew >blah'
    # break the 444/442/440 differences out so we can see if there is a common subsampling coefficient we can insert
    # I guess ideally in a future run the differences across subsampling will be normalised and we'd see no difference in future runs
    # save this to a log file in the dir
    
    # future:
    # in a future stage, we may wish to attempt a 'logistic regression' and have weighted coefficients on these, or a sample of them for which it is appropriate, to create a more powerful weighted score
    # might be nice to break the Lab channels into this reporting too, somehow. atm I make a wasserstein score on a 0.6, 0.2, 0.2 weighting or something. we should examine that!
    
    pass
    
