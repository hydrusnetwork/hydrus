import math
import numpy

import cv2

from hydrus.core.files.images import HydrusImageNormalisation

from hydrus.client import ClientGlobals as CG
from hydrus.client.caches import ClientCachesBase

# TODO: rework the cv2 stuff here to PIL or custom methods or whatever!

NORMALISE_SCALE_FOR_PROCESSING = True
NORMALISED_RESOLUTION = ( 1024, 1024 )

NUM_BINS = 256
NUM_TILES_PER_DIMENSION = 16
NUM_TILES_DIMENSIONS = ( NUM_TILES_PER_DIMENSION, NUM_TILES_PER_DIMENSION )
NUM_TILES = NUM_TILES_PER_DIMENSION * NUM_TILES_PER_DIMENSION

class LabHistogram( ClientCachesBase.CacheableObject ):
    
    def __init__( self, resolution, had_alpha: bool, l_hist: numpy.ndarray, a_hist: numpy.ndarray, b_hist: numpy.ndarray ):
        
        self.resolution = resolution
        self.had_alpha = had_alpha
        self.l_hist = l_hist
        self.a_hist = a_hist
        self.b_hist = b_hist
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        # float32
        return 4 * NUM_BINS * 3
        
    
    def IsInteresting( self ):
        # a flat colour, or a png with very very flat straight colours, is not going to have much in the L histogram
        return numpy.count_nonzero( self.l_hist ) + numpy.count_nonzero( self.a_hist ) + numpy.count_nonzero( self.b_hist ) > 24
        
    
    def ResolutionIsTooLow( self ):
        
        return self.resolution[0] < 32 or self.resolution[1] < 32
        
    

class LabTilesHistogram( ClientCachesBase.CacheableObject ):
    
    def __init__( self, resolution, had_alpha: bool, histograms: list[ LabHistogram ] ):
        
        self.resolution = resolution
        self.had_alpha = had_alpha
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
    

def gaussian_cdf(x, mean, std ):
    
    z = ( x - mean ) / ( std * math.sqrt(2) )
    
    return 0.5 * ( 1 + math.erf( z ) )
    

def aberrant_bump_in_scores_giganto_brain( values ):
    """
    detect a second bump in our score list
    """
    
    '''
    Assuming we are generally talking about 1 curve here in a good situation, let's fit a gaussian to the main guy and then see if the latter section of our histogram still has any grass standing tall
    
    Ok I worked on this and added p-values, but it still wasn't nicely differentiating good from bad! I think the scoring still is the baseline thing we need to hunt here, oh well
    '''
    
    n = len( values )
    
    gmm_result = fit_gmm_1d( values, n_components = 1 )
    mean = gmm_result[ 'means' ][0]
    variance = gmm_result[ 'variances' ][0]
    
    std = variance ** 0.5
    
    # Scott's Rule
    bin_width = 3.5 * std / ( n ** ( 1 / 3 ) )
    num_bins = max( 1, min( round( WD_MAX_REGIONAL_SCORE / bin_width ), 2000 ) )
    
    ( values_histogram, bin_edges ) = numpy.histogram( values, bins = num_bins, range = ( 0, WD_MAX_REGIONAL_SCORE ), density = True )
    
    bin_centers = ( bin_edges[ : -1 ] + bin_edges[ 1 : ] ) / 2
    
    pdf = gaussian_pdf( bin_centers, mean, variance )
    
    model_histogram = pdf * numpy.sum( values_histogram ) * bin_width
    
    residual_histogram = values_histogram - model_histogram
    
    # ok previously we set the num_bins to 50 and just tested against a flat >10? value
    # we are now going bananas and doing P-values
    
    results = []
    
    for ( x, residual ) in zip( bin_centers, residual_histogram ):
        
        if x < mean:
            
            continue  # optional: ignore left tail
            
        
        # what is the probability that tha residual is >0 here?
        p = 1 - gaussian_cdf( x , mean, std )
        
        # if the liklihood is greater than x%, we won't consider that suspicious
        if p > 0.05:
            
            continue
            
        
        # now let's make a normalised 'residual mass' amount that normalises for our dynamic bin width
        
        residual_mass = residual * bin_width
        
        log_score = residual_mass * - math.log( p + 1e-10 )
        
        if log_score > 0:
            
            print( (p, log_score ) )
            
        
        if log_score > 0.07:
            
            print( 'anomaly_detected' )
            
        
    
    return True
    

def aberrant_bump_in_scores( values ):
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
    
    if lab_tile_hist_1.had_alpha or lab_tile_hist_2.had_alpha:
        
        if lab_tile_hist_1.had_alpha and lab_tile_hist_2.had_alpha:
            
            message = 'cannot determine visual duplicates\n(they have transparency)'
            
        else:
            
            message = 'not visual duplicates\n(one has transparency)'
            
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, message )
        
    
    if FilesHaveDifferentRatio( lab_tile_hist_1.resolution, lab_tile_hist_2.resolution ):
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates\n(different ratio)' )
        
    
    if lab_tile_hist_1.ResolutionIsTooLow() or lab_tile_hist_2.ResolutionIsTooLow():
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'cannot determine visual duplicates\n(too low resolution)' )
        
    
    data = []
    
    for ( i, ( lab_hist_1, lab_hist_2 ) ) in enumerate( zip( lab_tile_hist_1.histograms, lab_tile_hist_2.histograms ) ):
        
        data.append( GetLabHistogramWassersteinDistanceScore( lab_hist_1, lab_hist_2 ) )
        
    
    we_have_no_interesting_tiles = True not in ( interesting_tile for ( interesting_tile, lab_score ) in data )
    we_have_an_interesting_tile_that_matches_perfectly = True in ( interesting_tile and lab_score < 0.0000001 for ( interesting_tile, lab_score ) in data )
    
    scores = [ lab_score for ( interesting_tile, lab_score ) in data ]
    
    max_regional_score = max( scores )
    mean_score = float( numpy.mean( scores ) )
    score_variance = float( numpy.var( scores ) )
    score_skew = skewness_numpy( scores )
    
    we_have_a_mix_of_perfect_and_non_perfect_matches = we_have_an_interesting_tile_that_matches_perfectly and max_regional_score > 0.0001
    
    # ok so skew alone is normalised and can thus be whack when we have a really tight, low variance distribution
    # so, let's multiply it by the maximum value we saw, and that gives us a nicer thing that scales to relevance with a decent sized distribution
    absolute_skew_pull = score_skew * max_regional_score * 1000
    
    exceeds_regional_score = max_regional_score > WD_MAX_REGIONAL_SCORE
    exceeds_mean = mean_score > WD_MAX_MEAN
    exceeds_variance = score_variance > WD_MAX_VARIANCE
    exceeds_skew = absolute_skew_pull > WD_MAX_ABSOLUTE_SKEW_PULL
    
    we_saw_an_aberrant_bump = aberrant_bump_in_scores( scores )
    
    debug_score_statement = f'max {max_regional_score:.3f} ({"ok" if not exceeds_regional_score else "bad"}) / mean {mean_score:.6f} ({"ok" if not exceeds_mean else "bad"})'
    debug_score_statement += '\n'
    debug_score_statement += f'variance {score_variance:.7f} ({"ok" if not exceeds_variance else "bad"}) / skew {score_skew:.3f}/{absolute_skew_pull:.2f} ({"ok" if not exceeds_skew else "bad"})'
    debug_score_statement += '\n'
    debug_score_statement += f'bump test: {"ok" if not we_saw_an_aberrant_bump else "bad"} / perfect/imperfect: {we_have_an_interesting_tile_that_matches_perfectly} {"ok" if not we_have_a_mix_of_perfect_and_non_perfect_matches else "bad"}'
    
    #print( debug_score_statement )
    
    if exceeds_skew or exceeds_variance or exceeds_mean or exceeds_regional_score or we_saw_an_aberrant_bump or we_have_a_mix_of_perfect_and_non_perfect_matches or we_have_no_interesting_tiles:
        
        they_are_similar = False
        result = VISUAL_DUPLICATES_RESULT_NOT
        
        if we_have_no_interesting_tiles:
            
            statement = f'too simple to compare'
            
        elif we_have_a_mix_of_perfect_and_non_perfect_matches:
            
            statement = 'probably not visual duplicates\n(small difference?)'
            
        elif exceeds_skew:
            
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
    
    # if I do not scale images to be the same size, this guy falls over!
    # I guess the INTER_AREA or something is doing an implicit gaussian of some sort and my tuned numbers assume that
    
    if lab_hist_1.had_alpha or lab_hist_2.had_alpha:
        
        if lab_hist_1.had_alpha and lab_hist_2.had_alpha:
            
            message = 'cannot determine visual duplicates\n(they have transparency)'
            
        else:
            
            message = 'not visual duplicates\n(one has transparency)'
            
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, message )
        
    
    if FilesHaveDifferentRatio( lab_hist_1.resolution, lab_hist_2.resolution ):
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates\n(different ratio)' )
        
    
    if lab_hist_1.ResolutionIsTooLow() or lab_hist_2.ResolutionIsTooLow():
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'cannot determine visual duplicates\n(too low resolution)' )
        
    
    # this is useful to rule out easy false positives, but as expected it suffers from lack of fine resolution
    
    ( interesting_tile, lab_score ) = GetLabHistogramWassersteinDistanceScore( lab_hist_1, lab_hist_2 )
    
    # experimentally, I generally find that most are < 0.0008, but a couple of high-quality-range jpeg pairs are 0.0018
    # so, let's allow this thing to examine deeper on this range of things but otherwise quickly discard
    # a confident negative result but less confident positive result is the way around we want
    
    they_are_similar = lab_score < 0.003
    
    if not interesting_tile:
        
        statement = f'too simple to compare'
        result = VISUAL_DUPLICATES_RESULT_NOT
        
    elif they_are_similar:
        
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
    

def GenerateEdgeMapNumPy( numpy_image: numpy.ndarray, original_resolution ) -> numpy.ndarray:
    
    '''
    This can work exceptionally well to detect lines, but if we scale images down, we lose data!!!
    So, we feed the image into here as a 100% grayscale.
    Then we have two objectives:
        - filter out jpeg and other scaling fuzz, the size of which is resolution independant
        - recognise similar edges, the size of which which are resolution dependant
    So, our sigma1 is fixed size, but our sigma2 is scaled to a perceptual size.
    
    I tried creating a histogram, but it was not helpful--we have to retain and compare position data! 
    '''
    
    # ok regardless of this tile size, we imagine the full image were zoomed to 2048x2048 size. what's a thin line edge look like at this scale?
    perceptual_scale = ( ( 2048 / original_resolution[0] ) * ( 2048 / original_resolution[1] ) ) ** 0.5
    
    img = numpy_image.astype( numpy.float32 )
    
    # Compute Difference of Gaussians
    blur1 = cv2.GaussianBlur(img, (0, 0), sigmaX = 1.7 )
    blur2 = cv2.GaussianBlur(img, (0, 0), sigmaX = 2.5 / perceptual_scale )
    dog = blur1 - blur2
    
    # generally we rarely see edges stronger than +/-8. sometimes 20-32, but '1' is a useful threshold in testing
    threshold = 1.0
    
    # emphasise yet again what is important, disregard noise
    dog_important = numpy.where( numpy.abs( dog ) > threshold, dog, 0 )
    
    # ok collapse to something smaller, using mean average
    edge_map = cv2.resize( dog_important, ( 32, 32 ), interpolation = cv2.INTER_AREA ).astype( numpy.float32 )
    
    edge_map_normalised_image = ( ( edge_map + 8 ) * 16 ).astype( numpy.uint8 )
    
    return edge_map
    
    # this was another thought--to phash the guy so we'd 'see' the differences
    # no dice, too many false positives because of fuzz
    #return ClientImagePerceptualHashes.GenerateShapePerceptualHashNumPy( edge_map_normalised_image )
    

def GenerateImageLabHistogramsNumPy( numpy_image: numpy.ndarray ) -> LabHistogram:
    
    ( width, height ) = ( numpy_image.shape[1], numpy_image.shape[0] )
    
    resolution = ( width, height )
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( numpy_image )
    
    # TODO: add an alpha histogram or something and an alpha comparison
    had_alpha = numpy_image.shape != numpy_image_rgb.shape
    
    #numpy_image_gray = cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2GRAY )
    
    if NORMALISE_SCALE_FOR_PROCESSING:
        
        numpy_image_rgb = cv2.resize( numpy_image_rgb, NORMALISED_RESOLUTION, interpolation = cv2.INTER_AREA )
        
    
    numpy_image_lab = cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2Lab )
    
    l = numpy_image_lab[ :, :, 0 ]
    a = numpy_image_lab[ :, :, 1 ]
    b = numpy_image_lab[ :, :, 2 ]
    
    # just a note here, a and b are usually -128 to +128, but opencv normalises to 0-255, so we are good here
    
    ( l_hist, l_gubbins ) = numpy.histogram( l, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( a_hist, a_gubbins ) = numpy.histogram( a, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    
    #edge_map = GenerateEdgeMapNumPy( numpy_image_gray, resolution )
    
    return LabHistogram( resolution, had_alpha, l_hist.astype( numpy.float32 ), a_hist.astype( numpy.float32 ), b_hist.astype( numpy.float32 ) )
    

def GenerateImageLabTilesHistogramsNumPy( numpy_image: numpy.ndarray ) -> LabTilesHistogram:
    
    ( width, height ) = ( numpy_image.shape[1], numpy_image.shape[0] )
    
    resolution = ( width, height )
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( numpy_image )
    
    had_alpha = numpy_image.shape != numpy_image_rgb.shape
    
    # ok scale the image up to the nearest multiple of 16
    tile_fitting_width = ( ( width + NUM_TILES_PER_DIMENSION - 1 ) // NUM_TILES_PER_DIMENSION ) * NUM_TILES_PER_DIMENSION
    tile_fitting_height = ( ( height + NUM_TILES_PER_DIMENSION - 1 ) // NUM_TILES_PER_DIMENSION ) * NUM_TILES_PER_DIMENSION
    
    if NORMALISE_SCALE_FOR_PROCESSING:
        
        lab_size_we_will_scale_to = NORMALISED_RESOLUTION
        
    else:
        
        lab_size_we_will_scale_to = ( tile_fitting_width, tile_fitting_height )
        
    
    gray_size_we_will_scale_to = ( tile_fitting_width, tile_fitting_height )
    
    #gray_scaled_numpy = cv2.resize( cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2GRAY ), gray_size_we_will_scale_to, interpolation = cv2.INTER_AREA )
    
    scaled_numpy = cv2.resize( numpy_image_rgb, lab_size_we_will_scale_to, interpolation = cv2.INTER_AREA )
    
    numpy_image_lab = cv2.cvtColor( scaled_numpy, cv2.COLOR_RGB2Lab )
    
    l = numpy_image_lab[ :, :, 0 ]
    a = numpy_image_lab[ :, :, 1 ]
    b = numpy_image_lab[ :, :, 2 ]
    
    histograms = []
    
    ( lab_tile_x, lab_tile_y ) = ( lab_size_we_will_scale_to[0] // NUM_TILES_PER_DIMENSION, lab_size_we_will_scale_to[1] // NUM_TILES_PER_DIMENSION )
    ( gray_tile_x, gray_tile_y ) = ( gray_size_we_will_scale_to[0] // NUM_TILES_PER_DIMENSION, gray_size_we_will_scale_to[1] // NUM_TILES_PER_DIMENSION )
    
    for x in range( NUM_TILES_PER_DIMENSION ):
        
        for y in range( NUM_TILES_PER_DIMENSION ):
            
            l_tile = l[ y * lab_tile_y : ( y + 1 ) * lab_tile_y, x * lab_tile_x : ( x + 1 ) * lab_tile_x ]
            a_tile = a[ y * lab_tile_y : ( y + 1 ) * lab_tile_y, x * lab_tile_x : ( x + 1 ) * lab_tile_x ]
            b_tile = b[ y * lab_tile_y : ( y + 1 ) * lab_tile_y, x * lab_tile_x : ( x + 1 ) * lab_tile_x ]
            
            # just a note here, a and b are usually -128 to +128, but opencv normalises to 0-255, so we are good here but the average will usually be ~128
            
            ( l_hist, l_gubbins ) = numpy.histogram( l_tile, bins = NUM_BINS, range = ( 0, 255 ), density = True )
            ( a_hist, a_gubbins ) = numpy.histogram( a_tile, bins = NUM_BINS, range = ( 0, 255 ), density = True )
            ( b_hist, b_gubbins ) = numpy.histogram( b_tile, bins = NUM_BINS, range = ( 0, 255 ), density = True )
            
            #gray_tile = gray_scaled_numpy[ y * gray_tile_y : ( y + 1 ) * gray_tile_y, x * gray_tile_x : ( x + 1 ) * gray_tile_x ]
            
            #edge_map = GenerateEdgeMapNumPy( gray_tile, resolution )
            
            histograms.append( LabHistogram( resolution, had_alpha, l_hist.astype( numpy.float32 ), a_hist.astype( numpy.float32 ), b_hist.astype( numpy.float32 ) ) )
            
        
    
    return LabTilesHistogram( resolution, had_alpha, histograms )
    

def GenerateImageRGBHistogramsNumPy( numpy_image: numpy.ndarray ):
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( numpy_image )
    
    r = numpy_image_rgb[ :, :, 0 ]
    g = numpy_image_rgb[ :, :, 1 ]
    b = numpy_image_rgb[ :, :, 2 ]
    
    # ok the density here tells it to normalise, so images with greater saturation appear similar
    ( r_hist, r_gubbins ) = numpy.histogram( r, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( g_hist, g_gubbins ) = numpy.histogram( g, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = NUM_BINS, range = ( 0, 255 ), density = True )
    
    return ( r_hist, g_hist, b_hist )
    

def GetHistogramNormalisedWassersteinDistance( hist_1: numpy.ndarray, hist_2: numpy.ndarray ) -> float:
    
    # Earth Movement Distance
    # how much do we have to rejigger one hist to be the same as the other?
    
    EMD = numpy.sum( numpy.abs( numpy.cumsum( hist_1 - hist_2 ) ) )
    
    # 0 = no movement, 255 = max movement
    
    return float( EMD / ( len( hist_1 ) - 1 ) )
    

def GetEdgeMapSlicedWasstersteinDistanceScore( edge_map_1: numpy.ndarray, edge_map_2: numpy.ndarray ):
    
    # this is a fast alternate of a 2D wasserstein distance
    
    def wasserstein_1d(p, q):
        
        return numpy.sum( numpy.abs( numpy.cumsum( p - q ) ) )
        
    
    row_diff = sum( wasserstein_1d( edge_map_1[i], edge_map_2[i] ) for i in range( edge_map_1.shape[0] ) )
    col_diff = sum( wasserstein_1d( edge_map_1[:, j], edge_map_2[:, j] ) for j in range( edge_map_1.shape[1] ) )
    
    return row_diff + col_diff
    

def GetLabHistogramWassersteinDistanceScore( lab_hist_1: LabHistogram, lab_hist_2: LabHistogram ):
    
    l_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.l_hist, lab_hist_2.l_hist )
    a_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.a_hist, lab_hist_2.a_hist )
    b_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.b_hist, lab_hist_2.b_hist )
    
    interesting_tile = lab_hist_1.IsInteresting() or lab_hist_2.IsInteresting()
    
    return ( interesting_tile, 0.6 * l_score + 0.2 * a_score + 0.2 * b_score )
    
