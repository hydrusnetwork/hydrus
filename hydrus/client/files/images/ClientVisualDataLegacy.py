import math
import numpy

from hydrus.core.files.images import HydrusImageNormalisation

# this is just some old gubbins that I tried and am not using any more
# might revisit, so I won't delete yet

LAB_HISTOGRAM_NUM_BINS = 256

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
    

def gaussian_pdf( x, mean, variance ):
    
    coef = 1 / math.sqrt( 2 * math.pi * variance )
    
    return coef * numpy.exp( -0.5 * ( ( x - mean ) ** 2) / variance )
    

def gaussian_cdf(x, mean, std ):
    
    z = ( x - mean ) / ( std * math.sqrt(2) )
    
    return 0.5 * ( 1 + math.erf( z ) )
    

def log_gaussian(x, mean, var):
    
    return -0.5 * numpy.log( 2 * numpy.pi * var ) - 0.5 * ( ( x - mean ) ** 2 ) / var
    

WD_MAX_REGIONAL_SCORE = 0.01

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
    EDIT 2025-06: Edge detection finally worked out and pretty much made this method moot.
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
    

def GenerateImageRGBHistogramsNumPy( numpy_image: numpy.ndarray ):
    
    numpy_image_rgb = HydrusImageNormalisation.StripOutAnyAlphaChannel( numpy_image )
    
    r = numpy_image_rgb[ :, :, 0 ]
    g = numpy_image_rgb[ :, :, 1 ]
    b = numpy_image_rgb[ :, :, 2 ]
    
    # ok the density here tells it to normalise, so images with greater saturation appear similar
    ( r_hist, r_gubbins ) = numpy.histogram( r, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
    ( g_hist, g_gubbins ) = numpy.histogram( g, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
    ( b_hist, b_gubbins ) = numpy.histogram( b, bins = LAB_HISTOGRAM_NUM_BINS, range = ( 0, 255 ), density = True )
    
    return ( r_hist, g_hist, b_hist )
    

def GetEdgeMapSlicedWasstersteinDistanceScore( edge_map_1: numpy.ndarray, edge_map_2: numpy.ndarray ):
    
    # this is a fast alternate of a 2D wasserstein distance
    
    def wasserstein_1d(p, q):
        
        return numpy.sum( numpy.abs( numpy.cumsum( p - q ) ) )
        
    
    row_diff = sum( wasserstein_1d( edge_map_1[i], edge_map_2[i] ) for i in range( edge_map_1.shape[0] ) )
    col_diff = sum( wasserstein_1d( edge_map_1[:, j], edge_map_2[:, j] ) for j in range( edge_map_1.shape[1] ) )
    
    return row_diff + col_diff
    
