import numpy

import cv2

from hydrus.core.files.images import HydrusImageColours
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageNormalisation

from hydrus.client import ClientGlobals as CG
from hydrus.client.caches import ClientCachesBase

# TODO: rework the cv2 stuff here to PIL or custom methods or whatever!


# to help smooth out jpeg artifacts, we can do a gaussian blur at 100% zoom
# jpeg artifacts are on the scale of 8x8 blocks.
# I tried 0.8 sigma, which is about 3x that radius (2.4px). I generated this visually during debug. it was ok
# I am moving to 0.95 sigma after doing some stats and more visual comparison at 0.7 up to 1.1
# obviously the numbers get closer and closer the higher you go though, so don't trust them alone. we only want to attack jpeg artifacts here
# anything that is like 600x1000 and low quality jpeg just gets blurred a lot!
JPEG_ARTIFACT_BLUR_FOR_PROCESSING = True
JPEG_ARTIFACT_GAUSSIAN_SIGMA_AT_100_ZOOM = 0.95

# saves lots of CPU time for no great change
NORMALISE_SCALE_FOR_LAB_HISTOGRAM_PROCESSING = True
LAB_HISTOGRAM_NORMALISED_RESOLUTION = ( 1024, 1024 )

LAB_HISTOGRAM_NUM_BINS = 256
LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION = 16
LAB_HISTOGRAM_NUM_TILES_DIMENSIONS = ( LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION, LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION )
LAB_HISTOGRAM_NUM_TILES = LAB_HISTOGRAM_NUM_TILES_DIMENSIONS[0] * LAB_HISTOGRAM_NUM_TILES_DIMENSIONS[1]

EDGE_MAP_PERCEPTUAL_RESOLUTION = ( 2048, 2048 )
EDGE_MAP_NORMALISED_RESOLUTION = ( 256, 256 )
EDGE_MAP_NUM_TILES_PER_DIMENSION = 16
EDGE_MAP_NUM_TILES_DIMENSIONS = ( EDGE_MAP_NUM_TILES_PER_DIMENSION, EDGE_MAP_NUM_TILES_PER_DIMENSION )
EDGE_MAP_NUM_TILES = EDGE_MAP_NUM_TILES_DIMENSIONS[0] * EDGE_MAP_NUM_TILES_DIMENSIONS[1]

class EdgeMap( ClientCachesBase.CacheableObject ):
    
    def __init__( self, edge_map_r: numpy.ndarray, edge_map_g: numpy.ndarray, edge_map_b: numpy.ndarray ):
        
        self.edge_map_r = edge_map_r
        self.edge_map_g = edge_map_g
        self.edge_map_b = edge_map_b
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        # this is not a small object mate. maybe we'll scale down a little, let's see the accuracy of this thing
        
        # float32
        return 4 * EDGE_MAP_NORMALISED_RESOLUTION[0] * EDGE_MAP_NORMALISED_RESOLUTION[1] * 3
        
    
    def IsFinishedLoading( self ):
        
        return True
        
    

class LabHistograms( ClientCachesBase.CacheableObject ):
    
    def __init__( self, l_hist: numpy.ndarray, a_hist: numpy.ndarray, b_hist: numpy.ndarray ):
        
        self.l_hist = l_hist
        self.a_hist = a_hist
        self.b_hist = b_hist
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        # float32
        return 4 * LAB_HISTOGRAM_NUM_BINS * 3
        
    
    def IsFinishedLoading( self ):
        
        return True
        
    
    def IsInteresting( self ):
        # a flat colour, or a png with very very flat straight colours, is not going to have much in the L histogram
        return numpy.count_nonzero( self.l_hist ) + numpy.count_nonzero( self.a_hist ) + numpy.count_nonzero( self.b_hist ) > 24
        
    

class VisualData( ClientCachesBase.CacheableObject ):
    
    def __init__( self, resolution, lab_histograms: LabHistograms, alpha_hist: numpy.ndarray | None = None ):
        
        self.resolution = resolution
        self.lab_histograms = lab_histograms
        self.alpha_hist = alpha_hist
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        # float32
        return self.lab_histograms.GetEstimatedMemoryFootprint()
        
    
    def HasAlpha( self ):
        
        return self.alpha_hist is not None
        
    
    def IsFinishedLoading( self ):
        
        return True
        
    
    def IsInteresting( self ):
        
        return self.lab_histograms.IsInteresting()
        
    
    def ResolutionIsTooLow( self ):
        
        return self.resolution[0] < 32 or self.resolution[1] < 32
        
    

class VisualDataTiled( ClientCachesBase.CacheableObject ):
    
    def __init__( self, resolution, had_alpha: bool, histograms: list[ LabHistograms ], edge_map: EdgeMap ):
        
        self.resolution = resolution
        self.had_alpha = had_alpha
        self.histograms = histograms
        self.edge_map = edge_map
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        return sum( ( histogram.GetEstimatedMemoryFootprint() for histogram in self.histograms ) ) + self.edge_map.GetEstimatedMemoryFootprint()
        
    
    def IsFinishedLoading( self ):
        
        return True
        
    
    def ResolutionIsTooLow( self ):
        
        return self.resolution[0] < 32 or self.resolution[1] < 32
        
    

class VisualDataStorage( ClientCachesBase.DataCache ):
    
    my_instance = None
    
    def __init__( self ):
        
        super().__init__( CG.client_controller, 'visual_data', 5 * 1024 * 1024 )
        
    
    @staticmethod
    def instance() -> 'VisualDataStorage':
        
        if VisualDataStorage.my_instance is None:
            
            VisualDataStorage.my_instance = VisualDataStorage()
            
        
        return VisualDataStorage.my_instance
        
    

class VisualDataTiledStorage( ClientCachesBase.DataCache ):
    
    my_instance = None
    
    def __init__( self ):
        
        super().__init__( CG.client_controller, 'visual_data_tiled', 32 * 1024 * 1024 )
        
    
    @staticmethod
    def instance() -> 'VisualDataTiledStorage':
        
        if VisualDataTiledStorage.my_instance is None:
            
            VisualDataTiledStorage.my_instance = VisualDataTiledStorage()
            
        
        return VisualDataTiledStorage.my_instance
        
    

def skewness_numpy( values ):
    
    values_numpy = numpy.asarray( values )
    
    mean = numpy.mean( values_numpy )
    
    std = numpy.std( values_numpy )
    
    if std == 0:
        
        return 0.0  # perfectly uniform array
        
    
    third_moment = numpy.mean( ( values_numpy - mean ) **  3 )
    
    skewness = third_moment / ( std ** 3 )
    
    return float( skewness )
    

# spreading these out in case we want to insert more in future
VISUAL_DUPLICATES_RESULT_NOT = 0
VISUAL_DUPLICATES_RESULT_PROBABLY = 40
VISUAL_DUPLICATES_RESULT_VERY_PROBABLY = 60
VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY = 85
VISUAL_DUPLICATES_RESULT_NEAR_PERFECT = 100

result_str_lookup = {
    VISUAL_DUPLICATES_RESULT_NOT : 'not duplicates',
    VISUAL_DUPLICATES_RESULT_PROBABLY : 'probably visual duplicates',
    VISUAL_DUPLICATES_RESULT_VERY_PROBABLY : 'very probably visual duplicates',
    VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY : 'almost certainly visual duplicates',
    VISUAL_DUPLICATES_RESULT_NEAR_PERFECT : 'near-perfect visual duplicates',
}

def BlurChannelNumPy( numpy_image_channel: numpy.ndarray, sigmaX ):
    
    return cv2.GaussianBlur( numpy_image_channel, ( 0, 0 ), sigmaX = sigmaX )
    

def BlurRGBNumPy( numpy_image: numpy.ndarray, sigmaX ):
    
    return numpy.stack(
        [ BlurChannelNumPy( numpy_image[ ..., i ], sigmaX ) for i in range( 3 ) ],
        axis = -1
    )
    

def FilesAreVisuallySimilarRegional( lab_tile_hist_1: VisualDataTiled, lab_tile_hist_2: VisualDataTiled ):
    
    # alpha is tested at the simple stage, not here
    if lab_tile_hist_1.had_alpha ^ lab_tile_hist_2.had_alpha:
        
        message = 'not visual duplicates\n(one has transparency)'
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, message )
        
    
    if FilesHaveDifferentRatio( lab_tile_hist_1.resolution, lab_tile_hist_2.resolution ):
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates\n(different ratio)' )
        
    
    if lab_tile_hist_1.ResolutionIsTooLow() or lab_tile_hist_2.ResolutionIsTooLow():
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'cannot determine visual duplicates\n(too low resolution)' )
        
    
    #
    
    ( they_are_similar_edge, result_edge, statement_edge ) = FilesAreVisuallySimilarRegionalEdgeMap( lab_tile_hist_1.edge_map, lab_tile_hist_2.edge_map )
    
    if they_are_similar_edge:
        
        ( they_are_similar_lab, result_lab, statement_lab ) = FilesAreVisuallySimilarRegionalLabHistograms( lab_tile_hist_1.histograms, lab_tile_hist_2.histograms )
        
        if result_edge < result_lab:
            
            return ( they_are_similar_edge, result_edge, statement_edge )
            
        else:
            
            return ( they_are_similar_lab, result_lab, statement_lab )
            
        
    else:
        
        return ( they_are_similar_edge, result_edge, statement_edge )
        
    

def FilesAreVisuallySimilarRegionalEdgeMapRaw( edge_map_1: EdgeMap, edge_map_2: EdgeMap ):
    
    # TODO: I think this can all be a lot smarter
    #
    # most importantly, I think we should go regional, tile stuff, for the max score testing
    # we want to determine if we have a crazy skew in all cases. we don't care about one bad pixel, and if we care about multiple bad pixels, we care where they are
    # so, move the largest point difference to its own tile thing and chop it all up and examine the averages or the spread of maxes or the spread of top 1%s or something
    # if we have tiles with a bunch of edge difference, that's an alternate!
    # if we have 70% of tiles with a bit of fuzz, that's jpeg fun
    # 
    # also convertall this to Lab mate
    #
    # we could make our absolute skew pull by using the average of the top decile rather than the absolute peak
    # HOW ABOUT THIS, for top 1% average (655 pixels for 256x256=65536 array):
    # try even higher, top 0.2% or so, to catch eye differences and so on
    # biggest_point_difference = numpy.mean( difference_edge_map_b[ difference_edge_map_b > numpy.percentile( difference_edge_map_b, 99.8 ) ] )
    # (but I forgot to abs it here, but yeah)
    # this is interesting, but may be the wrong tack if we go regional anyway
    #
    # ANY CHANGES HERE NEED A RETUNE
    
    # ####
    
    # each edge map is -255 to +255, hovering around 0
    
    difference_edge_map_r = edge_map_1.edge_map_r - edge_map_2.edge_map_r
    difference_edge_map_g = edge_map_1.edge_map_g - edge_map_2.edge_map_g
    difference_edge_map_b = edge_map_1.edge_map_b - edge_map_2.edge_map_b
    
    largest_point_difference_r = numpy.max( numpy.abs( difference_edge_map_r ) )
    largest_point_difference_g = numpy.max( numpy.abs( difference_edge_map_g ) )
    largest_point_difference_b = numpy.max( numpy.abs( difference_edge_map_b ) )
    
    largest_point_difference = max( largest_point_difference_r, largest_point_difference_g, largest_point_difference_b )
    
    # In some cases, you get something like a sliver of hair or an eye pupil that at a different resolution and jpeg quality loses some of its colour. maybe this is a subsampling thing?
    # This boosts these max-seen point differences up to like 30 or so
    # maybe I shouldn't be testing RGB as much as a weighted Lab
    
    #
    
    # Ok the above 'just get the max diff seen' works well, but I did get a nice 'very probably' false positive pair that had a logo difference in a pale colour
    # to detect a regional shift like this, we will now break our edge map into tiles and computer average distance in each and compute stats on that. any blob in the heat map will stand out
    # basically the same as we do for our histograms
    
    absolute_skew_pulls = []
    
    tile_height = int( EDGE_MAP_NORMALISED_RESOLUTION[0] / EDGE_MAP_NUM_TILES_PER_DIMENSION )
    tile_width = int( EDGE_MAP_NORMALISED_RESOLUTION[1] / EDGE_MAP_NUM_TILES_PER_DIMENSION )
    
    for ( largest_point_difference_for_this, difference_edge_map_for_this ) in [
        ( largest_point_difference_r, difference_edge_map_r ),
        ( largest_point_difference_g, difference_edge_map_g ),
        ( largest_point_difference_b, difference_edge_map_b ),
    ]:
        
        scores = []
        
        for i in range( 0, EDGE_MAP_NORMALISED_RESOLUTION[0], tile_height ):
            
            for j in range( 0, EDGE_MAP_NORMALISED_RESOLUTION[1], tile_width ):
                
                tile = difference_edge_map_for_this[ i : i + tile_height, j : j + tile_width ]
                
                mean_diff = numpy.mean( numpy.abs( tile ) )
                
                scores.append( mean_diff )
                
            
        
        score_skew = skewness_numpy( scores )
        
        # ok so skew alone is normalised and can thus be whack when we have a really tight, low variance distribution
        # so, let's multiply it by the maximum value we saw, and that gives us a nicer thing that scales to relevance with a decent sized distribution
        absolute_skew_pull = score_skew * largest_point_difference_for_this
        
        absolute_skew_pulls.append( absolute_skew_pull )
        
    
    largest_absolute_skew_pull = max( absolute_skew_pulls )
    
    return ( largest_point_difference, largest_absolute_skew_pull )
    

# ok we are doing a hybrid now. a bit of absolute, a bit of tiling
# I still wonder if we might want to do this in Lab. if we do, it should be a part of an automated profiling and testing regime here (about the fifth time I have pledged to work on this 'next time')

# these numbers seem to work well. sometimes there is a heavy re-encode pair at 18, and sometimes there is a subtle alternate pair at 18, but generally speaking these numbers are safely reliable:

EDGE_PERFECT_MAX_POINT_DIFFERENCE = 3
EDGE_VERY_GOOD_MAX_POINT_DIFFERENCE = 11
EDGE_MAX_POINT_DIFFERENCE = 19
EDGE_RUBBISH_MIN_POINT_DIFFERENCE = 45

# 2025-10 OK after tuning, we see:
# bumping up from 15 to 19
# good bit of overlap, with some false positives at 11 or so, oh well

# and here we have some numbers from experimentation. some stand out starkly

# -3->-6 = dupes
# 15-20 = strong encode
# 12-18 = pale watermark
# 34-226 = sweat drop moved
# 200-440 = tears around eyes
# 1400 = yep clear correction
EDGE_TILE_PERFECT_MAX_SKEW = 0
EDGE_TILE_VERY_GOOD_MAX_SKEW = 5
EDGE_TILE_MAX_SKEW = 16.5
EDGE_TILE_RUBBISH_MIN_SKEW = 200

# 2025-10 OK after tuning, we see:
# very rare a false positive lower than 17. sometimes a crazy one at 0.34 when very low quality and it is all fuzz
# lots of false negatives with skew > 22, 40, 50

def FilesAreVisuallySimilarRegionalEdgeMap( edge_map_1: EdgeMap, edge_map_2: EdgeMap ):
    
    ( largest_point_difference, largest_absolute_skew_pull ) = FilesAreVisuallySimilarRegionalEdgeMapRaw( edge_map_1, edge_map_2 )
    
    if largest_absolute_skew_pull > EDGE_TILE_MAX_SKEW:
        
        if largest_absolute_skew_pull > EDGE_TILE_RUBBISH_MIN_SKEW:
            
            return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates\n(alternate)' )
            
        else:
            
            return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'probably not visual duplicates\n(alternate/severe re-encode?)' )
            
        
    
    #
    
    if largest_point_difference < EDGE_PERFECT_MAX_POINT_DIFFERENCE:
        
        return ( True, VISUAL_DUPLICATES_RESULT_NEAR_PERFECT, 'near-perfect visual duplicates' )
        
    elif largest_point_difference < EDGE_VERY_GOOD_MAX_POINT_DIFFERENCE:
        
        return ( True, VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY, 'almost certainly visual duplicates' )
        
    elif largest_point_difference < EDGE_MAX_POINT_DIFFERENCE:
        
        return ( True, VISUAL_DUPLICATES_RESULT_VERY_PROBABLY, 'very probably visual duplicates' )
        
    elif largest_point_difference > EDGE_RUBBISH_MIN_POINT_DIFFERENCE:
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates\n(alternate)')
        
    else:
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'probably not visual duplicates\n(alternate/severe re-encode?)')
        
    

# I tried a bunch of stuff, and it seems like we want to look at multiple variables to catch our different situations
# detecting jpeg artifacts is difficult! they are pretty noisy from certain perspectives, and differentiating that noise from other edits is not simple. however they are _uniform_
# I tried with some correlation coefficient and chi squared stuff, but it wasn't smoothing out the noise nicely. I could fit the numbers to detect original from artist correction, but 70% vs artist correction was false positive

# New attempt with Earth Mover Distance, Wasserstein Distance. this should smooth out little fuzzy jpeg artifacts but notice bigger bumps better
# hesitant, but I think it is a huge success--check out that variance on the true dupes!
# when I compare the correction to 70%, I now get a skew worth something (12.681), so this is correctly measuring the uniform weight of jpeg artifacts and letting us exclude them as noise

# note in this case a 0.0 score is a perfect match, 1.0 is totally different

def FilesAreVisuallySimilarRegionalLabHistogramsRaw( histograms_1: list[ LabHistograms ], histograms_2: list[ LabHistograms ] ):
    
    lab_data = []
    
    for ( i, ( lab_hist_1, lab_hist_2 ) ) in enumerate( zip( histograms_1, histograms_2 ) ):
        
        lab_data.append( GetVisualDataWassersteinDistanceScore( lab_hist_1, lab_hist_2 ) )
        
    
    we_have_no_interesting_tiles = True not in ( interesting_tile for ( interesting_tile, lab_score ) in lab_data )
    we_have_an_interesting_tile_that_matches_perfectly = True in ( interesting_tile and lab_score < 0.0000001 for ( interesting_tile, lab_score ) in lab_data )
    
    scores = [ lab_score for ( interesting_tile, lab_score ) in lab_data ]
    
    max_regional_score = max( scores )
    mean_score = float( numpy.mean( scores ) )
    score_variance = float( numpy.var( scores ) )
    score_skew = skewness_numpy( scores )
    
    # ok so skew alone is normalised and can thus be whack when we have a really tight, low variance distribution
    # so, let's multiply it by the maximum value we saw, and that gives us a nicer thing that scales to relevance with a decent sized distribution
    absolute_skew_pull = score_skew * max_regional_score * 1000
    
    we_have_a_mix_of_perfect_and_non_perfect_matches = we_have_an_interesting_tile_that_matches_perfectly and max_regional_score > 0.0001 and absolute_skew_pull > 8.0
    
    return ( max_regional_score, mean_score, score_variance, score_skew, absolute_skew_pull, we_have_a_mix_of_perfect_and_non_perfect_matches, we_have_an_interesting_tile_that_matches_perfectly, we_have_no_interesting_tiles )
    

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
WD_MAX_ABSOLUTE_SKEW_PULL = 50.0

# and, additionally, after visual score histogram inspection...
WD_VERY_GOOD_MAX_REGIONAL_SCORE = 0.004
WD_VERY_GOOD_MAX_MEAN = 0.0015
WD_VERY_GOOD_MAX_VARIANCE = 0.000001
WD_VERY_GOOD_MAX_SKEW_PULL = 5.0

WD_PERFECT_MAX_REGIONAL_SCORE = 0.001
WD_PERFECT_MAX_MEAN = 0.0001
WD_PERFECT_MAX_VARIANCE = 0.000001
WD_PERFECT_MAX_SKEW_PULL = 1.5

# 2025-10 Tuning Suite Updates!
# REGIONAL_SCORES are great. 0.01 is a very good number
# MEAN is ok, difficult compromise, lots of overlay. 0.003 is ok though
# VARIANCE is no particularly useful tbh. useful for figuring out alts I guess. lots and lots of overlap though
# SKEW PULL is good at detects alts very well. numbers are great

# some future ideas:

# we could adjust our skew detection for how skewed the original file is. jpeg artifacts are focused around borders
    # if a tile has a lot of borders (messy hair) but the rest of the image is simple, we get a relatively high skew despite low mean and such
    # i.e. in this case, jpeg artifacts are not equally distributed across the image
    # so, perhaps a tile histogram could also have some edge/busy-ness detection as well
        # either we reduce the score by the busy-ness (yeah probably this)
        # or we bin the histograms by busy-ness and compare separately (probably convoluted and no better results than a busy-ness weight)

# train an ML to do it lol

# if we did this in HSL, we might be able to detect trivial recolours specifically

def FilesAreVisuallySimilarRegionalLabHistograms( histograms_1: list[ LabHistograms ], histograms_2: list[ LabHistograms ] ):
    
    ( max_regional_score, mean_score, score_variance, score_skew, absolute_skew_pull, we_have_a_mix_of_perfect_and_non_perfect_matches, we_have_an_interesting_tile_that_matches_perfectly, we_have_no_interesting_tiles ) = FilesAreVisuallySimilarRegionalLabHistogramsRaw( histograms_1, histograms_2 )
    
    exceeds_regional_score = max_regional_score > WD_MAX_REGIONAL_SCORE
    exceeds_mean = mean_score > WD_MAX_MEAN
    exceeds_variance = score_variance > WD_MAX_VARIANCE
    exceeds_skew = absolute_skew_pull > WD_MAX_ABSOLUTE_SKEW_PULL
    
    debug_score_statement = f'max {max_regional_score:.6f} ({"ok" if not exceeds_regional_score else "bad"}) / mean {mean_score:.6f} ({"ok" if not exceeds_mean else "bad"})'
    debug_score_statement += '\n'
    debug_score_statement += f'variance {score_variance:.7f} ({"ok" if not exceeds_variance else "bad"}) / skew {score_skew:.3f}/{absolute_skew_pull:.2f} ({"ok" if not exceeds_skew else "bad"})'
    debug_score_statement += '\n'
    debug_score_statement += f'perfect/imperfect: {we_have_an_interesting_tile_that_matches_perfectly} {"ok" if not we_have_a_mix_of_perfect_and_non_perfect_matches else "bad"}'
    
    #print( debug_score_statement )
    
    if exceeds_skew or exceeds_variance or exceeds_mean or exceeds_regional_score or we_have_a_mix_of_perfect_and_non_perfect_matches or we_have_no_interesting_tiles:
        
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
        
        if max_regional_score < WD_PERFECT_MAX_REGIONAL_SCORE and mean_score < WD_PERFECT_MAX_MEAN and score_variance < WD_PERFECT_MAX_VARIANCE and absolute_skew_pull < WD_PERFECT_MAX_SKEW_PULL:
            
            statement = 'near-perfect visual duplicates'
            result = VISUAL_DUPLICATES_RESULT_NEAR_PERFECT
            
        elif max_regional_score < WD_VERY_GOOD_MAX_REGIONAL_SCORE and mean_score < WD_VERY_GOOD_MAX_MEAN and score_variance < WD_VERY_GOOD_MAX_VARIANCE and absolute_skew_pull < WD_VERY_GOOD_MAX_SKEW_PULL:
            
            statement = 'almost certainly visual duplicates'
            result = VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY
            
        else:
            
            statement = 'very probably visual duplicates'
            result = VISUAL_DUPLICATES_RESULT_VERY_PROBABLY
            
        
    
    return ( they_are_similar, result, statement )
    

def FilesAreVisuallySimilarSimple( visual_data_1: VisualData, visual_data_2: VisualData ):
    
    if FilesHaveDifferentRatio( visual_data_1.resolution, visual_data_2.resolution ):
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'not visual duplicates\n(different ratio)' )
        
    
    if visual_data_1.ResolutionIsTooLow() or visual_data_2.ResolutionIsTooLow():
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, 'cannot determine visual duplicates\n(too low resolution)' )
        
    
    if visual_data_1.HasAlpha() and visual_data_2.HasAlpha():
        
        alpha_score = GetHistogramNormalisedWassersteinDistance( visual_data_1.alpha_hist, visual_data_2.alpha_hist )
        
        # tuning suite generally found that dupes had no score exceeding 0.001569
        # we don't want to be crazy strict here, just catch very different alpha masks
        if alpha_score > 0.005:
            
            message = 'not visual duplicates\n(transparency does not match)'
            
            return ( False, VISUAL_DUPLICATES_RESULT_NOT, message )
            
        
    elif visual_data_1.HasAlpha() ^ visual_data_2.HasAlpha():
        
        message = 'not visual duplicates\n(one has transparency)'
        
        return ( False, VISUAL_DUPLICATES_RESULT_NOT, message )
        
    
    # this is useful to rule out easy false positives, but as expected it suffers from lack of fine resolution
    
    ( interesting_tile, lab_score ) = GetVisualDataWassersteinDistanceScore( visual_data_1.lab_histograms, visual_data_2.lab_histograms )
    
    # experimentally, I generally find that most are < 0.0008, but a couple of high-quality-range jpeg pairs are 0.0018
    # so, let's allow this thing to examine deeper on this range of things but otherwise quickly discard (setting it at 0.003)
    # this guy tests if we should look closer, so we never want this guy to false negative!!
    
    # UPDATE 2025-10: After running the tuning suite, I see 0.0092 max score, so I am raising this to 0.01
    # many bad pairs are 0.014, so no worries, we are still achieving something with this fast simple call
    
    if not interesting_tile:
        
        they_are_similar = False
        
        statement = f'too simple to compare'
        result = VISUAL_DUPLICATES_RESULT_NOT
        
    else:
        
        they_are_similar = lab_score < 0.01
        
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
    

def GenerateEdgeMapNumPy( rgb_numpy_image: numpy.ndarray ) -> EdgeMap:
    """
    Receives the full image normalised to the bounding perceptual resolution. Not a tile.
    Comparable images should have the same 'size' of edge coming in here, and thus we can use the same 'perceptual' scale gaussian radii
    """
    
    # maybe we will convert this to be Lab also, I dunno
    
    rgb_numpy_image = rgb_numpy_image.astype( numpy.float32 )
    
    # TODO: Tune the 10.0 gaussian here more. run the tuning suite with multiple values and see if there is a better sweet spot with more numbers
    # were I feeling gigabrain, in part of converting this to Lab, we could blur the chromaticity channels less/more/whatever either as a matter of course or when we have 4:2:0 etc.. explicitly
    # that might be true of the original JPEG_ARTIFACT_GAUSSIAN_SIGMA_AT_100_ZOOM blur, too
    
    # Compute Difference of Gaussians
    # note we already did a JPEG_ARTIFACT_GAUSSIAN_SIGMA_AT_100_ZOOM blur on the 100% zoom. now we want to subtract a blur at subjective zoom
    # I tried several upper range blurs, 10.0 works well visually and with the final stats
    # ultimately this is more of a 'filtered and scaled image' more than a strict tight-band edge-map, but this seems to handle general situations better
    dog = rgb_numpy_image - BlurRGBNumPy( rgb_numpy_image, 10.0 )
    #dog = BlurRGBNumPy( rgb_numpy_image, 2.0 ) - BlurRGBNumPy( rgb_numpy_image, 6.0 )
    
    # this is in a range of -255->255 and hovers around 0
    dog = dog.astype( numpy.float32 )
    
    # ok collapse to something smaller, using mean average
    edge_map = do_cv2_resize( dog, EDGE_MAP_NORMALISED_RESOLUTION )
    
    edge_map_r = edge_map[ :, :, 0 ]
    edge_map_g = edge_map[ :, :, 1 ]
    edge_map_b = edge_map[ :, :, 2 ]
    
    return EdgeMap( edge_map_r, edge_map_g, edge_map_b )
    

def do_cv2_resize( numpy_image: numpy.ndarray, resolution: tuple[ int, int ] ):
    
    # I tried to be clever with 'if downscaling, use area; if upscaling, use lanczos4', but the clash of strategies when the pair does differ seems to make the edge detection go nuts
    # AREA is KISS??
    
    return cv2.resize( numpy_image, resolution, interpolation = cv2.INTER_AREA )
    

def GenerateImageVisualDataNumPy( numpy_image: numpy.ndarray ) -> VisualData:
    
    ( width, height ) = ( numpy_image.shape[1], numpy_image.shape[0] )
    
    resolution = ( width, height )
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( numpy_image )
    
    alpha_hist = None
    
    has_alpha = numpy_image.shape != numpy_image_rgb.shape
    
    if has_alpha:
        
        alpha_channel = HydrusImageColours.GetNumPyAlphaChannel( numpy_image )
        
        if JPEG_ARTIFACT_BLUR_FOR_PROCESSING:
            
            alpha_channel = BlurChannelNumPy( alpha_channel, JPEG_ARTIFACT_GAUSSIAN_SIGMA_AT_100_ZOOM )
            
        
        if NORMALISE_SCALE_FOR_LAB_HISTOGRAM_PROCESSING:
            
            alpha_channel = do_cv2_resize( alpha_channel, LAB_HISTOGRAM_NORMALISED_RESOLUTION )
            
        
        ( alpha_hist, alpha_gubbins ) = numpy.histogram( alpha_channel, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
        
        alpha_hist = alpha_hist.astype( numpy.float32 )
        
    
    #numpy_image_gray = cv2.cvtColor( numpy_image_rgb, cv2.COLOR_RGB2GRAY )
    
    if JPEG_ARTIFACT_BLUR_FOR_PROCESSING:
        
        numpy_image_rgb = BlurRGBNumPy( numpy_image_rgb, JPEG_ARTIFACT_GAUSSIAN_SIGMA_AT_100_ZOOM )
        
    
    # Lab histogram
    
    if NORMALISE_SCALE_FOR_LAB_HISTOGRAM_PROCESSING:
        
        lab_histogram_numpy_image_rgb = do_cv2_resize( numpy_image_rgb, LAB_HISTOGRAM_NORMALISED_RESOLUTION )
        
    else:
        
        lab_histogram_numpy_image_rgb = numpy_image_rgb
        
    
    numpy_image_lab = cv2.cvtColor( lab_histogram_numpy_image_rgb, cv2.COLOR_RGB2Lab )
    
    l = numpy_image_lab[ :, :, 0 ]
    a = numpy_image_lab[ :, :, 1 ]
    b = numpy_image_lab[ :, :, 2 ]
    
    # just a note here, a and b are usually -128 to +128, but opencv normalises to 0-255, so we are good
    
    ( l_hist, l_gubbins ) = numpy.histogram( l, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
    ( a_hist, a_gubbins ) = numpy.histogram( a, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
    
    lab_histograms = LabHistograms( l_hist.astype( numpy.float32 ), a_hist.astype( numpy.float32 ), b_hist.astype( numpy.float32 ) )
    
    return VisualData( resolution, lab_histograms, alpha_hist = alpha_hist )
    

def GenerateImageVisualDataTiledNumPy( numpy_image: numpy.ndarray ) -> VisualDataTiled:
    
    ( width, height ) = ( numpy_image.shape[1], numpy_image.shape[0] )
    
    resolution = ( width, height )
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( numpy_image )
    
    had_alpha = numpy_image.shape != numpy_image_rgb.shape
    
    if JPEG_ARTIFACT_BLUR_FOR_PROCESSING:
        
        numpy_image_rgb = BlurRGBNumPy( numpy_image_rgb, JPEG_ARTIFACT_GAUSSIAN_SIGMA_AT_100_ZOOM )
        
    
    # RGB edge-map
    
    scale_resolution = HydrusImageHandling.GetThumbnailResolution( resolution, EDGE_MAP_PERCEPTUAL_RESOLUTION, HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, 100 )
    
    # We do not want to scale to 2048x2048 or whatever; we want to keep the ratio for the edge stuff because: the Gaussian stuff is circles and we don't want to warp the image dimensions!
    edge_map_numpy_image_rgb = do_cv2_resize( numpy_image_rgb, scale_resolution )
    
    edge_map = GenerateEdgeMapNumPy( edge_map_numpy_image_rgb )
    
    # Lab histograms (tiled)
    
    # ok scale the image up to the nearest multiple of num_tiles
    tile_fitting_width = ( ( width + LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION - 1 ) // LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION ) * LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION
    tile_fitting_height = ( ( height + LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION - 1 ) // LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION ) * LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION
    
    if NORMALISE_SCALE_FOR_LAB_HISTOGRAM_PROCESSING:
        
        lab_size_we_will_scale_to = LAB_HISTOGRAM_NORMALISED_RESOLUTION
        
    else:
        
        lab_size_we_will_scale_to = ( tile_fitting_width, tile_fitting_height )
        
    
    scaled_numpy = do_cv2_resize( numpy_image_rgb, lab_size_we_will_scale_to )
    
    numpy_image_lab = cv2.cvtColor( scaled_numpy, cv2.COLOR_RGB2Lab )
    
    l = numpy_image_lab[ :, :, 0 ]
    a = numpy_image_lab[ :, :, 1 ]
    b = numpy_image_lab[ :, :, 2 ]
    
    histograms = []
    
    ( lab_tile_x, lab_tile_y ) = ( lab_size_we_will_scale_to[0] // LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION, lab_size_we_will_scale_to[1] // LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION )
    
    for x in range( LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION ):
        
        for y in range( LAB_HISTOGRAM_NUM_TILES_PER_DIMENSION ):
            
            l_tile = l[ y * lab_tile_y : ( y + 1 ) * lab_tile_y, x * lab_tile_x : ( x + 1 ) * lab_tile_x ]
            a_tile = a[ y * lab_tile_y : ( y + 1 ) * lab_tile_y, x * lab_tile_x : ( x + 1 ) * lab_tile_x ]
            b_tile = b[ y * lab_tile_y : ( y + 1 ) * lab_tile_y, x * lab_tile_x : ( x + 1 ) * lab_tile_x ]
            
            # just a note here, a and b are usually -128 to +128, but opencv normalises to 0-255, so we are good but the average will usually be ~128
            
            ( l_hist, l_gubbins ) = numpy.histogram( l_tile, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
            ( a_hist, a_gubbins ) = numpy.histogram( a_tile, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
            ( b_hist, b_gubbins ) = numpy.histogram( b_tile, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
            
            histograms.append( LabHistograms( l_hist.astype( numpy.float32 ), a_hist.astype( numpy.float32 ), b_hist.astype( numpy.float32 ) ) )
            
        
    
    return VisualDataTiled( resolution, had_alpha, histograms, edge_map )
    

def GetHistogramNormalisedWassersteinDistance( hist_1: numpy.ndarray, hist_2: numpy.ndarray ) -> float:
    
    # Earth Movement Distance
    # how much do we have to rejigger one hist to be the same as the other?
    
    EMD = numpy.sum( numpy.abs( numpy.cumsum( hist_1 - hist_2 ) ) )
    
    # 0 = no movement, 255 = max movement
    
    return float( EMD / ( len( hist_1 ) - 1 ) )
    

def GetVisualDataWassersteinDistanceScore( lab_hist_1: LabHistograms, lab_hist_2: LabHistograms ):
    
    l_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.l_hist, lab_hist_2.l_hist )
    a_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.a_hist, lab_hist_2.a_hist )
    b_score = GetHistogramNormalisedWassersteinDistance( lab_hist_1.b_hist, lab_hist_2.b_hist )
    
    interesting_tile = lab_hist_1.IsInteresting() or lab_hist_2.IsInteresting()
    
    
    return ( interesting_tile, 0.6 * l_score + 0.2 * a_score + 0.2 * b_score )
    
