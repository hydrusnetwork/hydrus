import math
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
    
    def __init__( self, resolution, l_hist: numpy.ndarray, a_hist: numpy.ndarray, b_hist: numpy.ndarray ):
        
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
    

# I tried detecting bimodality coefficient with this, but it didn't work for the sort of bump we were looking for
def kurtosis_numpy( values ):
    
    values = numpy.asarray( values )
    
    mean = numpy.mean( values )
    
    variance = numpy.var( values )
    
    if variance == 0:
        
        return 0
        
    
    m4 = numpy.mean( ( values - mean ) ** 4)
    
    kurt = m4 / ( variance ** 2 )
    
    return kurt
    

def log_gaussian(x, mean, var):
    
    return -0.5 * numpy.log( 2 * numpy.pi * var ) - 0.5 * ( ( x - mean ) ** 2 ) / var
    

# gaussian mixture modelling--how well does this distribution fit with n modes?
# it does its job well, but it is a liklihood based model that basically goes for maximising surface area
# so when it says 'yeah, this most looks bimodal, the means are here and here', it'll generally preference the bumps in the main blob and skip the tiny blob we are really looking for
def fit_gmm_1d( data, n_components=2, n_iter=100, tol=1e-6 ):
    
    data = numpy.asarray( data ).flatten()
    
    n = len( data )
    
    # Init: random means, uniform weights, global variance
    rng = numpy.random.default_rng()
    means = rng.choice( data, size=n_components, replace=False)
    variances = numpy.full( n_components, numpy.var(  data ) )
    weights = numpy.full( n_components, 1 / n_components )
    
    log_likelihoods = []
    
    for _ in range( n_iter ):
        
        # E-step: compute responsibilities
        log_probs = numpy.array( [
            numpy.log( weights[k] ) + log_gaussian( data, means[k], variances[k] )
            for k in range( n_components )
        ] )
        
        log_sum = numpy.logaddexp.reduce( log_probs, axis=0 )
        responsibilities = numpy.exp( log_probs - log_sum )
        
        # M-step: update parameters
        Nk = responsibilities.sum( axis=1 )
        weights = Nk / n
        means = numpy.sum( responsibilities * data, axis=1 ) / Nk
        variances = numpy.sum( responsibilities * ( data - means[:, numpy.newaxis] )**2, axis=1 ) / Nk

        # Log-likelihood
        ll = numpy.sum( log_sum )
        log_likelihoods.append( ll )
        if len( log_likelihoods ) > 1 and abs( log_likelihoods[-1] - log_likelihoods[-2] ) < tol:
            
            break
            
        
    
    # BIC = -2 * LL + p * log(n)
    # bayesian information criterion
    p = n_components * 3 - 1  # means, variances, weights (sum to 1)
    bic = -2 * log_likelihoods[-1] + p * numpy.log(n)
    
    return {
        'weights': weights,
        'means': means,
        'variances': variances,
        'log_likelihood': log_likelihoods[-1],
        'bic': bic
    }
    

def gaussian_pdf( x, mean, variance ):
    
    coef = 1 / math.sqrt( 2 * math.pi * variance )
    
    return coef * numpy.exp( -0.5 * ( ( x - mean ) ** 2) / variance )
    

def aberrant_bump_detected_giganto_brain( values ):
    """
    detect a second bump in our score list
    """
    
    '''
    Assuming we are generally talking about 1 curve here in a good situation, let's fit a gaussian to the main guy and then see if the latter section of our histogram still has any grass standing tall
    
    Ok this worked kiiiind of ok, but it catches a bunch of false positives of later bumps. some bumps are ok, some are not! ultimately not easy to differentiate
    '''
    
    gmm_result = fit_gmm_1d( values, n_components = 1 )
    mean = gmm_result[ 'means' ][0]
    variance = gmm_result[ 'variances' ][0]
    
    ( values_histogram, bin_edges ) = numpy.histogram( values, bins = 50, range = ( 0, WD_MAX_REGIONAL_SCORE ), density = True )
    
    bin_centers = ( bin_edges[ : -1 ] + bin_edges[ 1 : ] ) / 2
    
    pdf = gaussian_pdf( bin_centers, mean, variance )
    
    bin_width = ( bin_edges[1] - bin_edges[0] )
    
    model_histogram = pdf * numpy.sum( values_histogram ) * bin_width
    
    residual_histogram = values_histogram - model_histogram
    
    # what's >0 was above what is expected by the model
    
    tail_start_position = round( ( mean + ( variance ** 0.5 ) * 2 ) / bin_width )
    
    tail = residual_histogram[ tail_start_position : ]
    
    return numpy.any( tail > 10 )
    

def aberrant_bump_detected( values ):
    """
    detect a second bump in our score list
    """
    
    '''
    ok here is what we want to detect:
    
    array([176.47058824,  58.82352941, 137.25490196, 215.68627451,
       333.33333333, 294.11764706, 588.23529412, 549.01960784,
       588.23529412, 607.84313725, 352.94117647, 333.33333333,
       156.8627451 , 156.8627451 ,  58.82352941, 156.8627451 ,
        58.82352941,  78.43137255,  58.82352941,  19.60784314,
         0.        ,   0.        ,   0.        ,   0.        ,
         0.        ,   0.        ,   0.        ,   0.        ,
         0.        ,   0.        ,   0.        ,   0.        ,
         0.        ,   0.        ,   0.        ,   0.        ,
         0.        ,   0.        ,   0.        ,   0.        ,
         0.        ,  19.60784314,   0.        ,   0.        ,
         0.        ,   0.        ,   0.        ,   0.        ,
         0.        ,   0.        ])
    
    basically, a nice big bump and then a small bump--that's our weird change
    skew does not catch this reliably since the large bump is so large
    
    I tried some algorithms to detect bimodality and such, but really I think the simple solution is just to say 'if there are a bunch of zeroes and then data, that's an odd little bump mate'
    EDIT: After thinking about this more, maybe we need to massage the data coming in more. since we now know that tiles are not equal when it comes to jpeg artifact differences
        perhaps we should be thinking about getting higher quality scores before trying harder to hunt for odd bumps--some of our bumps are currently good! 
    '''
    
    values_histogram = numpy.histogram( values, bins = 50, range = ( 0, WD_MAX_REGIONAL_SCORE ), density = True )[0]
    
    NUM_ZEROES_THRESHOLD = 6
    
    have_hit_main_bump = False
    current_num_zeroes = 0
    
    for i in range( len( values_histogram ) ):
        
        value = values_histogram[ i ]
        
        if not have_hit_main_bump:
            
            if value > 0:
                
                have_hit_main_bump = True
                
            
        else:
            
            if value == 0:
                
                current_num_zeroes += 1
                
            else:
                
                # ok, we hit the main bump, did some zeroes, and now hit new data!!
                if current_num_zeroes >= NUM_ZEROES_THRESHOLD:
                    
                    return True
                    
                
                current_num_zeroes = 0
                
            
        
    
    return False
    

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
WD_MAX_ABSOLUTE_SKEW_PULL = 50

# and, additionally, after visual score histogram inspection...
WD_VERY_GOOD_MAX_REGIONAL_SCORE = 0.004
WD_VERY_GOOD_MAX_MEAN = 0.0015
WD_VERY_GOOD_MAX_VARIANCE = 0.000001

WD_PERFECT_MAX_REGIONAL_SCORE = 0.001
WD_PERFECT_MAX_MEAN = 0.0001
WD_PERFECT_MAX_VARIANCE = 0.000001


# some future ideas:

# set up a really nice test suite with lots of good example pairs and perform some sort of multi-factor analysis on these output weights
    # then, instead of doing separate bools, have coefficients (or more complicated weights) that we multiply the inputs by to make a total weight and test against one threshold value
    # this would be far more precise than bool gubbins, but we'd have to do research and do it right

# we could adjust our skew detection for how skewed the original file is. jpeg artifacts are focused around borders
    # if a tile has a lot of borders (messy hair) but the rest of the image is simple, we get a relatively high skew despite low mean and such
    # i.e. in this case, jpeg artifacts are not equally distributed across the image
    # so, perhaps a tile histogram could also have some edge/busy-ness detection as well
        # either we reduce the score by the busy-ness (yeah probably this)
        # or we bin the histograms by busy-ness and compare separately (probably convoluted and no better results than a busy-ness weight)

# train an ML to do it lol

# if we did this in HSL, we might be able to detect trivial recolours specifically

VISUAL_DUPLICATES_RESULT_NOT = 0
VISUAL_DUPLICATES_RESULT_PROBABLY = 1
VISUAL_DUPLICATES_RESULT_VERY_PROBABLY = 2
VISUAL_DUPLICATES_RESULT_DEFINITELY = 3
VISUAL_DUPLICATES_RESULT_PERFECTLY = 4

def FilesAreVisuallySimilarRegional( lab_tile_hist_1: LabTilesHistogram, lab_tile_hist_2: LabTilesHistogram ):
    
    if FilesHaveDifferentRatio( lab_tile_hist_1.resolution, lab_tile_hist_2.resolution ):
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates (different ratio)' )
        
    
    if lab_tile_hist_1.ResolutionIsTooLow() or lab_tile_hist_2.ResolutionIsTooLow():
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'cannot determine visual duplicates (too low resolution)' )
        
    
    scores = [ GetLabHistogramWassersteinDistanceScore( lab_hist_1, lab_hist_2 ) for ( lab_hist_1, lab_hist_2 ) in zip( lab_tile_hist_1.histograms, lab_tile_hist_2.histograms ) ]
    
    max_regional_score = max( scores )
    mean_score = float( numpy.mean( scores ) )
    score_variance = float( numpy.var( scores ) )
    score_skew = skewness_numpy( scores )
    
    # ok so skew alone is normalised and can thus be whack when we have a really tight, low variance distribution
    # so, let's multiply it by the maximum value we saw, and that gives us a nicer thing that scales to relevance with a decent sized distribution
    absolute_skew_pull = score_skew * max_regional_score * 1000
    
    exceeds_regional_score = max_regional_score > WD_MAX_REGIONAL_SCORE
    exceeds_mean = mean_score > WD_MAX_MEAN
    exceeds_variance = score_variance > WD_MAX_VARIANCE
    exceeds_skew = absolute_skew_pull > WD_MAX_ABSOLUTE_SKEW_PULL
    
    we_saw_an_aberrant_bump = aberrant_bump_detected( scores )
    
    debug_score_statement = f'max {max_regional_score:.3f} ({not exceeds_regional_score}) / mean {mean_score:.6f} ({not exceeds_mean})\nvariance {score_variance:.7f} ({not exceeds_variance}) / skew {score_skew:.3f}/{absolute_skew_pull:.2f} ({not exceeds_skew})\naberrant bump: {not aberrant_bump_detected}'
    
    if exceeds_skew or exceeds_variance or exceeds_mean or exceeds_regional_score or we_saw_an_aberrant_bump:
        
        they_are_similar = False
        result = VISUAL_DUPLICATES_RESULT_NOT
        
        if exceeds_skew:
            
            statement = 'not visual duplicates\n(alternate/watermark?)'
            
        elif not exceeds_variance:
            
            statement = 'probably not visual duplicates\n(alternate/severe re-encode?)'
            
        else:
            
            statement = 'probably not visual duplicates'
            
        
    else:
        
        they_are_similar = True
        
        if max_regional_score < WD_PERFECT_MAX_REGIONAL_SCORE and mean_score < WD_PERFECT_MAX_MEAN and score_variance < WD_PERFECT_MAX_VARIANCE:
            
            statement = 'near-perfect visual duplicates'
            result = VISUAL_DUPLICATES_RESULT_PERFECTLY
            
        elif max_regional_score < WD_VERY_GOOD_MAX_REGIONAL_SCORE and mean_score < WD_VERY_GOOD_MAX_MEAN and score_variance < WD_VERY_GOOD_MAX_VARIANCE:
            
            statement = 'definitely visual duplicates'
            result = VISUAL_DUPLICATES_RESULT_DEFINITELY
            
        else:
            
            statement = 'very probably visual duplicates'
            result = VISUAL_DUPLICATES_RESULT_VERY_PROBABLY
            
        
    
    return ( they_are_similar, result, statement )
    

def FilesAreVisuallySimilarSimple( lab_hist_1: LabHistogram, lab_hist_2: LabHistogram ):
    
    if FilesHaveDifferentRatio( lab_hist_1.resolution, lab_hist_2.resolution ):
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates (different ratio)' )
        
    
    if lab_hist_1.ResolutionIsTooLow() or lab_hist_2.ResolutionIsTooLow():
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'cannot determine visual duplicates (too low resolution)' )
        
    
    # this is useful to rule out easy false positives, but as expected it suffers from lack of fine resolution
    
    score = GetLabHistogramWassersteinDistanceScore( lab_hist_1, lab_hist_2 )
    
    # experimentally, I generally find that most are < 0.0008, but a couple of high-quality-range jpeg pairs are 0.0018
    # so, let's allow this thing to examine deeper on this range of things but otherwise quickly discard
    # a confident negative result but less confident positive result is the way around we want
    
    they_are_similar = score < 0.003
    
    if they_are_similar:
        
        statement = f'probably visual duplicates'
        result = VISUAL_DUPLICATES_RESULT_PROBABLY
        
    else:
        
        statement = f'not visual duplicates'
        result = VISUAL_DUPLICATES_RESULT_NOT
        
    
    return ( they_are_similar, result, statement )
    

def FilesHaveDifferentRatio( resolution_1, resolution_2 ):
    
    from hydrus.client.search import ClientNumberTest
    
    ( s_w, s_h ) = resolution_1
    ( c_w, c_h ) = resolution_2
    
    s_ratio = s_w / s_h
    c_ratio = c_w / c_h
    
    return not ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT, value = 1 ).Test( s_ratio, c_ratio )
    

def GenerateImageLabHistogramsNumPy( numpy_image: numpy.ndarray ) -> LabHistogram:
    
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
    

def GenerateImageLabTilesHistogramsNumPy( numpy_image: numpy.ndarray ) -> LabTilesHistogram:
    
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
    

def GenerateImageRGBHistogramsNumPy( numpy_image: numpy.ndarray ):
    
    scaled_numpy = cv2.resize( numpy_image, HISTOGRAM_IMAGE_SIZE, interpolation = cv2.INTER_AREA )
    
    r = scaled_numpy[ :, :, 0 ]
    g = scaled_numpy[ :, :, 1 ]
    b = scaled_numpy[ :, :, 2 ]
    
    # ok the density here tells it to normalise, so images with greater saturation appear similar
    ( r_hist, r_gubbins ) = numpy.histogram( r, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( g_hist, g_gubbins ) = numpy.histogram( g, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    
    return ( r_hist, g_hist, b_hist )
    

def GetHistogramNormalisedWassersteinDistance( hist_1: numpy.ndarray, hist_2: numpy.ndarray ) -> float:
    
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
    
