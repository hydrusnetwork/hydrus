import numpy

import cv2
import typing

from hydrus.core.files.images import HydrusImageNormalisation

from hydrus.client import ClientGlobals as CG
from hydrus.client.caches import ClientCachesBase

# TODO: rework the cv2 stuff here to PIL or custom methods or whatever!

HISTOGRAM_IMAGE_SIZE = ( 1024, 1024 )
NUM_BINS = 256
NUM_TILES_DIMENSIONS = ( 16, 16 )
TILE_DIMENSIONS = ( int( HISTOGRAM_IMAGE_SIZE[0] / NUM_TILES_DIMENSIONS[0] ), int( HISTOGRAM_IMAGE_SIZE[1] / NUM_TILES_DIMENSIONS[1] ) )
NUM_TILES = NUM_TILES_DIMENSIONS[0] * NUM_TILES_DIMENSIONS[1]

class LabHistogram( ClientCachesBase.CacheableObject ):
    
    def __init__( self, resolution, l_hist: numpy.array, a_hist: numpy.array, b_hist: numpy.array ):
        
        self.resolution = resolution
        self.l_hist = l_hist
        self.a_hist = a_hist
        self.b_hist = b_hist
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        # I convert to float16, which has no impact on our needed resolution
        return 2 * NUM_BINS * 3
        
    
    def ResolutionIsTooLow( self ):
        
        return self.resolution[0] < 32 or self.resolution[1] < 32
        
    

class LabTilesHistogram( ClientCachesBase.CacheableObject ):
    
    def __init__( self, resolution, histograms: typing.List[ LabHistogram ] ):
        
        self.resolution = resolution
        self.histograms = histograms
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        return sum( ( histogram.GetEstimatedMemoryFootprint() for histogram in self.histograms ) )
        
    
    def ResolutionIsTooLow( self ):
        
        return self.resolution[0] < 32 or self.resolution[1] < 32
        
    

class LabHistogramStorage( ClientCachesBase.DataCache ):
    
    my_instance = None
    
    def __init__( self ):
        
        super().__init__( CG.client_controller, 'lab_histograms', 5 * 1024 * 1024 )
        
    
    @staticmethod
    def instance() -> 'LabHistogramStorage':
        
        if LabHistogramStorage.my_instance is None:
            
            LabHistogramStorage.my_instance = LabHistogramStorage()
            
        
        return LabHistogramStorage.my_instance
        
    

class LabTilesHistogramStorage( ClientCachesBase.DataCache ):
    
    my_instance = None
    
    def __init__( self ):
        
        super().__init__( CG.client_controller, 'lab_tile_histograms', 32 * 1024 * 1024 )
        
    
    @staticmethod
    def instance() -> 'LabTilesHistogramStorage':
        
        if LabTilesHistogramStorage.my_instance is None:
            
            LabTilesHistogramStorage.my_instance = LabTilesHistogramStorage()
            
        
        return LabTilesHistogramStorage.my_instance
        
    

def skewness_numpy( values ):
    
    values_numpy = numpy.asarray( values )
    
    mean = numpy.mean( values_numpy )
    
    std = numpy.std( values_numpy )
    
    if std == 0:
        
        return 0.0  # perfectly uniform array
        
    
    third_moment = numpy.mean( ( values_numpy - mean ) **  3 )
    
    skewness = third_moment / ( std ** 3 )
    
    return float( skewness )
    

# I tried a bunch of stuff, and it seems like we want to look at multiple variables to catch our different situations
# detecting jpeg artifacts is difficult! they are pretty noisy from certain perspectives, and differentiating that noise from other edits is not simple. however they are _uniform_
# I tried with some correlation coefficient and chi squared stuff, but it wasn't smoothing out the noise nicely. I could fit the numbers to detect original from artist correction, but 70% vs artist correction was false positive

# New attempt with Earth Mover Distance, Wasserstein Distance. this should smooth out little fuzzy jpeg artifacts but notice bigger bumps better
# hesitant, but I think it is a huge success--check out that variance on the true dupes!
# when I compare the correction to 70%, I now get a skew worth something (12.681), so this is correctly measuring the uniform weight of jpeg artifacts and letting us exclude them as noise

# note in this case a 0.0 score is a perfect match, 1.0 is totally different

# vs our original normal image:

# scaled down: max 0.008 / mean 0.002299 / variance 0.000001 / skew 0.788
# 60%: max 0.004 / mean 0.001666 / variance 0.000001 / skew 0.316
# 70%: max 0.003 / mean 0.001561 / variance 0.000000 / skew 0.211
# 80%: max 0.002 / mean 0.000845 / variance 0.000000 / skew 0.503

# correction: max 0.032 / mean 0.000155 / variance 0.000004 / skew 14.726
# watermark: max 0.107 / mean 0.001669 / variance 0.000103 / skew 7.110

# dechroma: max 0.022 / mean 0.011325 / variance 0.000027 / skew -0.313
# hue phase: max 0.063 / mean 0.026598 / variance 0.000264 / skew 0.430
# darkness: max 0.059 / mean 0.055800 / variance 0.000002 / skew -2.117
# saturation: max 0.028 / mean 0.009552 / variance 0.000038 / skew 1.107
# colour temp: max 0.087 / mean 0.035031 / variance 0.000473 / skew 0.181

# therefore, I am choosing these decent defaults to start us off:
#WD_MAX_REGIONAL_SCORE = 0.01
#WD_MAX_MEAN = 0.003
#WD_MAX_VARIANCE = 0.000002
#WD_MAX_SKEW = 1.0

# ok after some more IRL testing, we are adjusting to:
WD_MAX_REGIONAL_SCORE = 0.01
WD_MAX_MEAN = 0.003
WD_MAX_VARIANCE = 0.0000035
WD_MAX_SKEW = 2.6

# some future ideas:
# if we discovered that >50% tiles were exact matches and the rest were pretty similar in colour or shape, we might have detected an alternate
# if we did this in HSL, we might be able to detect trivial recolours specifically

def FilesAreVisuallySimilarRegional( lab_tile_hist_1: LabTilesHistogram, lab_tile_hist_2: LabTilesHistogram ):
    
    if FilesHaveDifferentRatio( lab_tile_hist_1.resolution, lab_tile_hist_2.resolution ):
        
        return ( False, 'not visual duplicates (different ratio)' )
        
    
    if lab_tile_hist_1.ResolutionIsTooLow() or lab_tile_hist_2.ResolutionIsTooLow():
        
        return ( False, 'cannot determine visual duplicates (too low resolution)' )
        
    
    scores = [ GetLabHistogramWassersteinDistanceScore( lab_hist_1, lab_hist_2 ) for ( lab_hist_1, lab_hist_2 ) in zip( lab_tile_hist_1.histograms, lab_tile_hist_2.histograms ) ]
    
    max_regional_score = max( scores )
    mean_score = float( numpy.mean( scores ) )
    score_variance = float( numpy.var( scores ) )
    score_skew = skewness_numpy( scores )
    
    exceeds_regional_score = max_regional_score > WD_MAX_REGIONAL_SCORE
    exceeds_mean = mean_score > WD_MAX_MEAN
    exceeds_variance = score_variance > WD_MAX_VARIANCE
    exceeds_skew = max_regional_score > 0.001 and score_skew > WD_MAX_SKEW # for very low differences, skew is whack and not reliable
    
    debug_score_statement = f'max {max_regional_score:.3f} ({not exceeds_regional_score}) / mean {mean_score:.6f} ({not exceeds_mean})\nvariance {score_variance:.6f} ({not exceeds_variance}) / skew {score_skew:.3f} ({not exceeds_skew})'
    
    if exceeds_skew or exceeds_variance or exceeds_mean or exceeds_regional_score:
        
        they_are_similar = False
        
        if exceeds_skew and score_skew > 6.0:
            
            statement = 'not visual duplicates (alternate/watermark?)'
            
        elif score_skew < 1.5 and score_variance < 0.0005:
            
            statement = 'not visual duplicates (recolour?)'
            
        elif mean_score > 0.025:
            
            statement = 'not visual duplicates (alternates?)'
            
        else:
            
            if sum( ( 1 for x in ( exceeds_skew, exceeds_variance, exceeds_mean, exceeds_regional_score ) if x ) ) == 1:
                
                statement = 'probably not visual duplicates'
                
            else:
                
                statement = 'not visual duplicates'
                
            
        
    else:
        
        they_are_similar = True
        
        if max_regional_score < 0.001 and score_variance < 0.000001:
            
            statement = 'near-perfect visual duplicates'
            
        else:
            
            statement = 'visual duplicates'
            
        
    
    statement += f'\n{debug_score_statement}'
    
    return ( they_are_similar, statement )
    

def FilesAreVisuallySimilarSimple( lab_hist_1: LabHistogram, lab_hist_2: LabHistogram ):
    
    if FilesHaveDifferentRatio( lab_hist_1.resolution, lab_hist_2.resolution ):
        
        return ( False, 'not visual duplicates (different ratio)' )
        
    
    if lab_hist_1.ResolutionIsTooLow() or lab_hist_2.ResolutionIsTooLow():
        
        return ( False, 'cannot determine visual duplicates (too low resolution)' )
        
    
    # this is useful to rule out easy false positives, but as expected it suffers from lack of fine resolution
    
    score = GetLabHistogramWassersteinDistanceScore( lab_hist_1, lab_hist_2 )
    
    # experimentally, I generally find that most are < 0.0008, but a couple of high-quality-range jpeg pairs are 0.0018
    # so, let's allow this thing to examine deeper on this range of things but otherwise quickly discard
    # a confident negative result but less confident positive result is the way around we want
    
    they_are_similar = score < 0.003
    
    if they_are_similar:
        
        statement = f'probably visual duplicates\n{score:.3f}'
        
    else:
        
        statement = f'not visual duplicates\n{score:.3f}'
        
    
    return ( they_are_similar, statement )
    

def FilesHaveDifferentRatio( resolution_1, resolution_2 ):
    
    from hydrus.client.search import ClientNumberTest
    
    ( s_w, s_h ) = resolution_1
    ( c_w, c_h ) = resolution_2
    
    s_ratio = s_w / s_h
    c_ratio = c_w / c_h
    
    return not ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT, value = 1 ).Test( s_ratio, c_ratio )
    

def GenerateImageLabHistogramsNumPy( numpy_image: numpy.array ) -> LabHistogram:
    
    resolution = ( numpy_image.shape[1], numpy_image.shape[0] )
    
    scaled_numpy = cv2.resize( numpy_image, HISTOGRAM_IMAGE_SIZE, interpolation = cv2.INTER_AREA )
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( scaled_numpy )
    
    numpy_image_lab = cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2Lab )
    
    l = numpy_image_lab[ :, :, 0 ]
    a = numpy_image_lab[ :, :, 1 ]
    b = numpy_image_lab[ :, :, 2 ]
    
    # just a note here, a and b are usually -128 to +128, but opencv normalises to 0-255, so we are good here
    
    ( l_hist, l_gubbins ) = numpy.histogram( l, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( a_hist, a_gubbins ) = numpy.histogram( a, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    
    return LabHistogram( resolution, l_hist.astype( numpy.float16 ), a_hist.astype( numpy.float16 ), b_hist.astype( numpy.float16 ) )
    

def GenerateImageLabTilesHistogramsNumPy( numpy_image: numpy.array ) -> LabTilesHistogram:
    
    resolution = ( numpy_image.shape[1], numpy_image.shape[0] )
    
    scaled_numpy = cv2.resize( numpy_image, HISTOGRAM_IMAGE_SIZE, interpolation = cv2.INTER_AREA )
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( scaled_numpy )
    
    numpy_image_lab = cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2Lab )
    
    l = numpy_image_lab[ :, :, 0 ]
    a = numpy_image_lab[ :, :, 1 ]
    b = numpy_image_lab[ :, :, 2 ]
    
    histograms = []
    
    ( tile_x, tile_y ) = TILE_DIMENSIONS
    
    for x in range( NUM_TILES_DIMENSIONS[0] ):
        
        for y in range( NUM_TILES_DIMENSIONS[ 1 ] ):
            
            l_tile = l[ y * tile_y : ( y + 1 ) * tile_y, x * tile_x : ( x + 1 ) * tile_x ]
            a_tile = a[ y * tile_y : ( y + 1 ) * tile_y, x * tile_x : ( x + 1 ) * tile_x ]
            b_tile = b[ y * tile_y : ( y + 1 ) * tile_y, x * tile_x : ( x + 1 ) * tile_x ]
            
            # just a note here, a and b are usually -128 to +128, but opencv normalises to 0-255, so we are good here but the average will usually be ~128
            
            ( l_hist, l_gubbins ) = numpy.histogram( l_tile, bins = NUM_BINS, range = ( 0, 255 ), density = True )
            ( a_hist, a_gubbins ) = numpy.histogram( a_tile, bins = NUM_BINS, range = ( 0, 255 ), density = True )
            ( b_hist, b_gubbins ) = numpy.histogram( b_tile, bins = NUM_BINS, range = ( 0, 255 ), density = True )
            
            histograms.append( LabHistogram( resolution, l_hist.astype( numpy.float16 ), a_hist.astype( numpy.float16 ), b_hist.astype( numpy.float16 ) ) )
            
        
    
    return LabTilesHistogram( resolution, histograms )
    

def GenerateImageRGBHistogramsNumPy( numpy_image: numpy.array ):
    
    scaled_numpy = cv2.resize( numpy_image, HISTOGRAM_IMAGE_SIZE, interpolation = cv2.INTER_AREA )
    
    r = scaled_numpy[ :, :, 0 ]
    g = scaled_numpy[ :, :, 1 ]
    b = scaled_numpy[ :, :, 2 ]
    
    # ok the density here tells it to normalise, so images with greater saturation appear similar
    ( r_hist, r_gubbins ) = numpy.histogram( r, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( g_hist, g_gubbins ) = numpy.histogram( g, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    
    return ( r_hist, g_hist, b_hist )
    

def GetHistogramNormalisedWassersteinDistance( hist_1: numpy.array, hist_2: numpy.array ) -> float:
    
    # Earth Movement Distance
    # how much do we have to rejigger one hist to be the same as the other?
    
    hist_1_cdf = numpy.cumsum( hist_1 )
    hist_2_cdf = numpy.cumsum( hist_2 )
    
    EMD = numpy.sum( numpy.abs( hist_1_cdf - hist_2_cdf ) )
    
    # 0 = no movement, 255 = max movement
    
    return float( EMD / ( NUM_BINS - 1 ) )
    

def GetLabHistogramWassersteinDistanceScore( lab_hist_1: LabHistogram, lab_hist_2: LabHistogram ):
    
    l_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.l_hist, lab_hist_2.l_hist )
    a_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.a_hist, lab_hist_2.a_hist )
    b_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.b_hist, lab_hist_2.b_hist )
    
    return 0.6 * l_score + 0.2 * a_score + 0.2 * b_score
    
