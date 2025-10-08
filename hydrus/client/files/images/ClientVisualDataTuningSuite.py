import itertools
import numpy
import os
import random

from PIL import Image as PILImage
from PIL import ImageDraw as PILDraw

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusPaths
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientGlobals as CG
from hydrus.client.duplicates import ClientDuplicatesComparisonStatements
from hydrus.client.files.images import ClientVisualData

pil_subsampling_lookup = {
    444 : '4:4:4',
    422 : '4:2:2',
    420 : '4:2:0'
}

def save_file( pil_image, out_dir, base_filename, suffix, original = False ):
    
    if original:
        
        quality = 97
        subsampling = 444
        
    else:
        
        quality = random.randint( 72, 90 )
        subsampling = random.choice( ( 444, 444, 444, 444, 422, 420, 420 ) )
        
    
    dest_filename = f'{base_filename}_{quality}_{subsampling}_{suffix}.jpg'
    
    dest_path = os.path.join( out_dir, dest_filename )
    
    pil_image.save( dest_path, 'JPEG', quality = quality, subsampling = pil_subsampling_lookup[ subsampling ] )
    
    # got to load so we can get subsampling and quality differences!!
    numpy_image = HydrusImageHandling.GenerateNumPyImage( dest_path, HC.IMAGE_JPEG, force_pil = True )
    
    visual_data = ClientVisualData.GenerateImageVisualDataNumPy( numpy_image )
    
    visual_data_tiled = ClientVisualData.GenerateImageVisualDataTiledNumPy( numpy_image )
    
    return ( base_filename, dest_path, suffix, quality, subsampling, visual_data, visual_data_tiled )
    

NUM_TO_DO = 5

def PercentileValue( some_numbers, percentile ):
    
    return float( sorted( some_numbers )[ int( len( some_numbers ) * percentile ) ] )
    

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
        
        good_paths.add( save_file( pil_image, out_dir, base_filename, 'original', original = True ) )
        
        for i in range( NUM_TO_DO ):
            
            good_paths.add( save_file( pil_image, out_dir, base_filename, 'resave' ) )
            
            #
            
            scale = random.randint( 90, 95 ) / 100
            
            pil_image_smaller = pil_image.resize( ( int( width * scale ), int( height * scale ) ), PILImage.Resampling.LANCZOS )
            
            good_paths.add( save_file( pil_image_smaller, out_dir, base_filename, 'bit_smaller' ) )
            
            #
            
            scale = random.randint( 80, 90 ) / 100
            
            pil_image_smaller = pil_image.resize( ( int( width * scale ), int( height * scale ) ), PILImage.Resampling.LANCZOS )
            
            good_paths.add( save_file( pil_image_smaller, out_dir, base_filename, 'even_smaller' ) )
            
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
            
        
        #
        
        good_paths_sorted = sorted( good_paths, key = lambda big_tuple: ( big_tuple[2], big_tuple[3], big_tuple[4] ) )
        
        all_good_pairs = list( itertools.combinations( good_paths_sorted, 2 ) )
        
        all_bad_paths = list( correction_paths )
        all_bad_paths.extend( watermark_paths )
        all_bad_paths.extend( recolour_paths )
        
        all_bad_pairs = list( itertools.product( all_bad_paths, good_paths_sorted ) )
        
        #
        
        def render_simple_image_to_report_string( base_filename, suffix_1, visual_data_1: ClientVisualData.VisualData, quality_1, subsampling_1, suffix_2, visual_data_2: ClientVisualData.VisualData, quality_2, subsampling_2 ):
            
            components = []
            
            if visual_data_1.resolution == visual_data_2.resolution:
                
                components.append( f'{visual_data_1.resolution[0]}x{visual_data_1.resolution[1]}' )
                
            else:
                
                components.append( f'{visual_data_1.resolution[0]}x{visual_data_1.resolution[1]} vs {visual_data_2.resolution[0]}x{visual_data_2.resolution[1]}' )
                
            
            if quality_1 == quality_2:
                
                components.append( f'{quality_1}' )
                
            else:
                
                components.append( f'{quality_1} vs {quality_2}' )
                
            
            if subsampling_1 == subsampling_2:
                
                components.append( f'{subsampling_1}' )
                
            else:
                
                components.append( f'{subsampling_1} vs {subsampling_2}' )
                
            
            return f'{base_filename} ({suffix_1} vs {suffix_2}): ' + ', '.join( components )
            
        
        #
        
        report = 'Good pairs:\n\n'
        
        #
        
        simple_score_spam = []
        simple_false_negatives = []
        
        lab_scores = []
        lab_scores_444 = []
        lab_scores_444_420 = []
        
        for (
                ( base_filename_1, path_1, suffix_1, quality_1, subsampling_1, visual_data_1, visual_data_tiled_1 ),
                ( base_filename_2, path_2, suffix_2, quality_2, subsampling_2, visual_data_2, visual_data_tiled_2 )
        ) in all_good_pairs:
            
            pair_str = render_simple_image_to_report_string( base_filename_1, suffix_1, visual_data_1, quality_1, subsampling_1, suffix_2, visual_data_2, quality_2, subsampling_2 )
            
            ( interesting_tile, lab_score ) = ClientVisualData.GetVisualDataWassersteinDistanceScore( visual_data_1.lab_histograms, visual_data_2.lab_histograms )
            
            lab_scores.append( lab_score )
            
            if { subsampling_1, subsampling_2 } == { 420, 444 }:
                
                lab_scores_444_420.append( lab_score )
                
            elif subsampling_1 == subsampling_2 and subsampling_1 == 444:
                
                lab_scores_444.append( lab_score )
                
            
            ( simple_seems_good, simple_result, simple_score_statement ) = ClientVisualData.FilesAreVisuallySimilarSimple( visual_data_1, visual_data_2 )
            
            if not simple_seems_good:
                
                simple_false_negatives.append( f'Got a FALSE NEGATIVE simple test on: {pair_str}: {lab_score}' )
                
            
        
        report += 'Simple Scores:\n\n'
        report += 'We never want to see a false negative here!\n\n'
        report += f'Mean simple score: {float( numpy.mean( lab_scores ) )}\n'
        report += f'95th percentile simple score: {PercentileValue( lab_scores, 0.95 )}\n'
        report += f'Max simple score: {max( lab_scores )} (We want to set the threshold to be over this)\n\n'
        
        if len( lab_scores_444_420 ) > 0:
            
            report += f'Mean simple score 444 vs 420: {float( numpy.mean( lab_scores_444_420 ) )}\n'
            report += f'Max simple score 444 vs 420: {max( lab_scores_444_420 )}\n\n'
            
        
        if len( lab_scores_444 ) > 0:
            
            report += f'Mean simple score 444: {float( numpy.mean( lab_scores_444 ) )}\n'
            report += f'Max simple score 444: {max( lab_scores_444 )}\n\n'
            
        
        report += '\n'.join( simple_score_spam ) + '\n\n'
        report += '\n'.join( simple_false_negatives ) + '\n\n'
        
        #
        
        regional_score_spam = []
        regional_false_negatives = []
        
        datas_edge_map = []
        
        datas_histogram = []
        datas_histogram_444 = []
        datas_histogram_444_420 = []
        
        for (
                ( base_filename_1, path_1, suffix_1, quality_1, subsampling_1, visual_data_1, visual_data_tiled_1 ),
                ( base_filename_2, path_2, suffix_2, quality_2, subsampling_2, visual_data_2, visual_data_tiled_2 )
        ) in all_good_pairs:
            
            pair_str = render_simple_image_to_report_string( base_filename_1, suffix_1, visual_data_1, quality_1, subsampling_1, suffix_2, visual_data_2, quality_2, subsampling_2 )
            
            (
                max_regional_score,
                mean_score,
                score_variance,
                score_skew,
                absolute_skew_pull,
                we_have_a_mix_of_perfect_and_non_perfect_matches,
                we_have_an_interesting_tile_that_matches_perfectly,
                we_have_no_interesting_tiles
            ) = ClientVisualData.FilesAreVisuallySimilarRegionalLabHistogramsRaw(
                visual_data_tiled_1.histograms,
                visual_data_tiled_2.histograms
            )
            
            ( largest_point_difference, largest_absolute_skew_pull ) = ClientVisualData.FilesAreVisuallySimilarRegionalEdgeMapRaw(
                visual_data_tiled_1.edge_map,
                visual_data_tiled_2.edge_map
            )
            
            data = {
                'max_regional_score' : max_regional_score,
                'mean_score' : mean_score,
                'score_variance' : score_variance,
                'score_skew' : score_skew,
                'absolute_skew_pull' : absolute_skew_pull,
                'largest_point_difference' : largest_point_difference,
                'largest_absolute_skew_pull' : largest_absolute_skew_pull
            }
            
            datas_edge_map.append( data )
            
            ( edge_map_seems_good, edge_map_result, edge_map_score_statement ) = ClientVisualData.FilesAreVisuallySimilarRegionalEdgeMap( visual_data_tiled_1.edge_map, visual_data_tiled_2.edge_map )
            
            if edge_map_seems_good:
                
                ( regional_seems_good, regional_result, regional_score_statement ) = ClientVisualData.FilesAreVisuallySimilarRegionalLabHistograms( visual_data_tiled_1.histograms, visual_data_tiled_2.histograms )
                
                datas_histogram.append( data )
                
                if { subsampling_1, subsampling_2 } == { 420, 444 }:
                    
                    datas_histogram_444_420.append( data )
                    
                elif subsampling_1 == subsampling_2 and subsampling_1 == 444:
                    
                    datas_histogram_444.append( data )
                    
                
                if not regional_seems_good:
                    
                    regional_false_negatives.append( f'Got a FALSE NEGATIVE REGIONAL test on: {pair_str} {sorted( data.items() )}' )
                    
                
            else:
                
                regional_false_negatives.append( f'Got a FALSE NEGATIVE EDGE MAP test on: {pair_str} {sorted( data.items() )}' )
                
            
        
        report += 'Regional Scores:\n\n'
        report += 'A false negative here is not great but ok.\n\n'
        
        report += f'Mean largest point difference: {float( numpy.mean( [ data[ "largest_point_difference" ] for data in datas_edge_map ] ) )}\n'
        report += f'95th percentile largest point difference: {PercentileValue( [ data[ "largest_point_difference" ] for data in datas_edge_map ], 0.95 )}\n'
        report += f'Max largest point difference: {float( max( [ data[ "largest_point_difference" ] for data in datas_edge_map ] ) )}\n\n'
        
        report += f'Mean largest absolute skew pull: {float( numpy.mean( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ] ) )}\n'
        report += f'95th percentile absolute skew pull: {PercentileValue( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ], 0.95 )}\n'
        report += f'Max largest absolute skew pull: {float( max( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ] ) )}\n\n\n'
        
        if len( datas_histogram ) > 0:
            
            report += f'Mean max regional score: {float( numpy.mean( [ data[ "max_regional_score" ] for data in datas_histogram ] ) )}\n'
            report += f'95th percentile max regional score: {PercentileValue( [ data[ "max_regional_score" ] for data in datas_histogram ], 0.95 )}\n'
            report += f'Max max regional score: {float( max( [ data[ "max_regional_score" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Mean mean score: {float( numpy.mean( [ data[ "mean_score" ] for data in datas_histogram ] ) )}\n'
            report += f'95th percentile mean score: {PercentileValue( [ data[ "mean_score" ] for data in datas_histogram ], 0.95 )}\n'
            report += f'Max mean score: {float( max( [ data[ "mean_score" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Mean score variance: {float( numpy.mean( [ data[ "score_variance" ] for data in datas_histogram ] ) )}\n'
            report += f'95th percentile score variance: {PercentileValue( [ data[ "score_variance" ] for data in datas_histogram ], 0.95 )}\n'
            report += f'Max score variance: {float( max( [ data[ "score_variance" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Mean score skew: {float( numpy.mean( [ data[ "score_skew" ] for data in datas_histogram ] ) )}\n'
            report += f'95th percentile score skew: {PercentileValue( [ data[ "score_skew" ] for data in datas_histogram ], 0.95 )}\n'
            report += f'Max score skew: {float( max( [ data[ "score_skew" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Mean absolute skew pull: {float( numpy.mean( [ data[ "absolute_skew_pull" ] for data in datas_histogram ] ) )}\n'
            report += f'95th percentile absolute skew pull: {PercentileValue( [ data[ "absolute_skew_pull" ] for data in datas_histogram ], 0.95 )}\n'
            report += f'Max absolute skew pull: {float( max( [ data[ "absolute_skew_pull" ] for data in datas_histogram ] ) )}\n\n'
            
        
        if len( datas_histogram_444_420 ) > 0:
            
            report += f'Mean max regional score 444 vs 420: {float( numpy.mean( [ data[ "max_regional_score" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max max regional score 444 vs 420: {float( max( [ data[ "max_regional_score" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean mean score 444 vs 420: {float( numpy.mean( [ data[ "mean_score" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max mean score 444 vs 420: {float( max( [ data[ "mean_score" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean score variance 444 vs 420: {float( numpy.mean( [ data[ "score_variance" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max score variance 444 vs 420: {float( max( [ data[ "score_variance" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean score skew 444 vs 420: {float( numpy.mean( [ data[ "score_skew" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max score skew 444 vs 420: {float( max( [ data[ "score_skew" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean absolute skew pull 444 vs 420: {float( numpy.mean( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max absolute skew pull 444 vs 420: {float( max( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            
        
        if len( datas_histogram_444 ) > 0:
            
            report += f'Mean max regional score 444: {float( numpy.mean( [ data[ "max_regional_score" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max max regional score 444: {float( max( [ data[ "max_regional_score" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean mean score 444: {float( numpy.mean( [ data[ "mean_score" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max mean score 444: {float( max( [ data[ "mean_score" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean score variance 444: {float( numpy.mean( [ data[ "score_variance" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max score variance 444: {float( max( [ data[ "score_variance" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean score skew 444: {float( numpy.mean( [ data[ "score_skew" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max score skew 444: {float( max( [ data[ "score_skew" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean absolute skew pull 444: {float( numpy.mean( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max absolute skew pull 444: {float( max( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444 ] ) )}\n\n'
            
        
        report += '\n'.join( regional_score_spam ) + '\n\n'
        report += '\n'.join( regional_false_negatives ) + '\n\n'
        
        #
        
        report += 'Bad pairs:\n\n'
        
        #
        
        simple_score_spam = []
        simple_false_positives = []
        
        lab_scores = []
        lab_scores_444 = []
        lab_scores_444_420 = []
        
        for (
                ( base_filename_1, path_1, suffix_1, quality_1, subsampling_1, visual_data_1, visual_data_tiled_1 ),
                ( base_filename_2, path_2, suffix_2, quality_2, subsampling_2, visual_data_2, visual_data_tiled_2 )
        ) in all_bad_pairs:
            
            pair_str = render_simple_image_to_report_string( base_filename_1, suffix_1, visual_data_1, quality_1, subsampling_1, suffix_2, visual_data_2, quality_2, subsampling_2 )
            
            ( interesting_tile, lab_score ) = ClientVisualData.GetVisualDataWassersteinDistanceScore( visual_data_1.lab_histograms, visual_data_2.lab_histograms )
            
            lab_scores.append( lab_score )
            
            if { subsampling_1, subsampling_2 } == { 420, 444 }:
                
                lab_scores_444_420.append( lab_score )
                
            elif subsampling_1 == subsampling_2 and subsampling_1 == 444:
                
                lab_scores_444.append( lab_score )
                
            
            ( simple_seems_good, simple_result, simple_score_statement ) = ClientVisualData.FilesAreVisuallySimilarSimple( visual_data_1, visual_data_2 )
            
            if simple_seems_good:
                
                simple_false_positives.append( f'Got a false positive simple test on: {pair_str}: {lab_score}' )
                
            
        
        report += 'Simple Scores:\n\n'
        report += 'A false positive here is ok. Pairs with extremely low simple scores are worthy of more investigation.\n\n'
        report += f'Min simple score: {min( lab_scores )}\n'
        report += f'Mean simple score: {float( numpy.mean( lab_scores ) )}\n'
        report += f'95th percentile simple score: {PercentileValue( lab_scores, 0.95 )}\n'
        report += f'Max simple score: {max( lab_scores )}\n\n'
        
        if len( lab_scores_444_420 ) > 0:
            
            report += f'Mean simple score 444 vs 420: {float( numpy.mean( lab_scores_444_420 ) )}\n'
            report += f'Max simple score 444 vs 420: {max( lab_scores_444_420 )}\n\n'
            
        
        if len( lab_scores_444 ) > 0:
            
            report += f'Mean simple score 444: {float( numpy.mean( lab_scores_444 ) )}\n'
            report += f'Max simple score 444: {max( lab_scores_444 )}\n\n'
            
        
        report += '\n'.join( simple_score_spam ) + '\n\n'
        report += '\n'.join( simple_false_positives ) + '\n\n'
        
        #
        
        regional_score_spam = []
        regional_false_positives = []
        
        datas_edge_map = []
        
        datas_histogram = []
        datas_histogram_444 = []
        datas_histogram_444_420 = []
        
        for (
                ( base_filename_1, path_1, suffix_1, quality_1, subsampling_1, visual_data_1, visual_data_tiled_1 ),
                ( base_filename_2, path_2, suffix_2, quality_2, subsampling_2, visual_data_2, visual_data_tiled_2 )
        ) in all_bad_pairs:
            
            pair_str = render_simple_image_to_report_string( base_filename_1, suffix_1, visual_data_1, quality_1, subsampling_1, suffix_2, visual_data_2, quality_2, subsampling_2 )
            
            (
                max_regional_score,
                mean_score,
                score_variance,
                score_skew,
                absolute_skew_pull,
                we_have_a_mix_of_perfect_and_non_perfect_matches,
                we_have_an_interesting_tile_that_matches_perfectly,
                we_have_no_interesting_tiles
            ) = ClientVisualData.FilesAreVisuallySimilarRegionalLabHistogramsRaw(
                visual_data_tiled_1.histograms,
                visual_data_tiled_2.histograms
            )
            
            ( largest_point_difference, largest_absolute_skew_pull ) = ClientVisualData.FilesAreVisuallySimilarRegionalEdgeMapRaw(
                visual_data_tiled_1.edge_map,
                visual_data_tiled_2.edge_map
            )
            
            data = {
                'max_regional_score' : max_regional_score,
                'mean_score' : mean_score,
                'score_variance' : score_variance,
                'score_skew' : score_skew,
                'absolute_skew_pull' : absolute_skew_pull,
                'largest_point_difference' : largest_point_difference,
                'largest_absolute_skew_pull' : largest_absolute_skew_pull
            }
            
            datas_edge_map.append( data )
            
            ( edge_map_seems_good, edge_map_result, edge_map_score_statement ) = ClientVisualData.FilesAreVisuallySimilarRegionalEdgeMap( visual_data_tiled_1.edge_map, visual_data_tiled_2.edge_map )
            
            if edge_map_seems_good:
                
                datas_histogram.append( data )
                
                if { subsampling_1, subsampling_2 } == { 420, 444 }:
                    
                    datas_histogram_444_420.append( data )
                    
                elif subsampling_1 == subsampling_2 and subsampling_1 == 444:
                    
                    datas_histogram_444.append( data )
                    
                
                ( regional_seems_good, regional_result, regional_score_statement ) = ClientVisualData.FilesAreVisuallySimilarRegionalLabHistograms( visual_data_tiled_1.histograms, visual_data_tiled_2.histograms )
                
                if regional_seems_good:
                    
                    regional_false_negatives.append( f'Got a FALSE POSITIVE!!!!! REGIONAL test on: {pair_str} {sorted( data.items() )}' )
                    
                
            
        
        report += 'Regional Scores:\n\n'
        report += 'A false positive here is a disaster.\n\n'
        
        report += f'Min largest point difference: {float( min( [ data[ "largest_point_difference" ] for data in datas_edge_map ] ) )}\n'
        report += f'5th percentile largest point difference: {PercentileValue( [ data[ "largest_point_difference" ] for data in datas_edge_map ], 0.05 )}\n'
        report += f'Mean largest point difference: {float( numpy.mean( [ data[ "largest_point_difference" ] for data in datas_edge_map ] ) )}\n'
        report += f'Max largest point difference: {float( max( [ data[ "largest_point_difference" ] for data in datas_edge_map ] ) )}\n\n'
        
        report += f'Min largest absolute skew pull: {float( min( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ] ) )}\n'
        report += f'5th percentile absolute skew pull: {PercentileValue( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ], 0.05 )}\n'
        report += f'Mean largest absolute skew pull: {float( numpy.mean( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ] ) )}\n'
        report += f'Max largest absolute skew pull: {float( max( [ data[ "largest_absolute_skew_pull" ] for data in datas_edge_map ] ) )}\n\n\n'
        
        if len( datas_histogram ) > 0:
            
            report += f'Min max regional score: {float( min( [ data[ "max_regional_score" ] for data in datas_histogram ] ) )}\n'
            report += f'5th percentile max regional score: {PercentileValue( [ data[ "max_regional_score" ] for data in datas_histogram ], 0.05 )}\n'
            report += f'Mean max regional score: {float( numpy.mean( [ data[ "max_regional_score" ] for data in datas_histogram ] ) )}\n'
            report += f'Max max regional score: {float( max( [ data[ "max_regional_score" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Min mean score: {float( min( [ data[ "mean_score" ] for data in datas_histogram ] ) )}\n'
            report += f'5th percentile mean score: {PercentileValue( [ data[ "mean_score" ] for data in datas_histogram ], 0.05 )}\n'
            report += f'Mean mean score: {float( numpy.mean( [ data[ "mean_score" ] for data in datas_histogram ] ) )}\n'
            report += f'Max mean score: {float( max( [ data[ "mean_score" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Min score variance: {float( min( [ data[ "score_variance" ] for data in datas_histogram ] ) )}\n'
            report += f'5th percentile score variance: {PercentileValue( [ data[ "score_variance" ] for data in datas_histogram ], 0.05 )}\n'
            report += f'Mean score variance: {float( numpy.mean( [ data[ "score_variance" ] for data in datas_histogram ] ) )}\n'
            report += f'Max score variance: {float( max( [ data[ "score_variance" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Min score skew: {float( min( [ data[ "score_skew" ] for data in datas_histogram ] ) )}\n'
            report += f'5th percentile score skew: {PercentileValue( [ data[ "score_skew" ] for data in datas_histogram ], 0.05 )}\n'
            report += f'Mean score skew: {float( numpy.mean( [ data[ "score_skew" ] for data in datas_histogram ] ) )}\n'
            report += f'Max score skew: {float( max( [ data[ "score_skew" ] for data in datas_histogram ] ) )}\n\n'
            
            report += f'Min absolute skew pull: {float( min( [ data[ "absolute_skew_pull" ] for data in datas_histogram ] ) )}\n'
            report += f'5th percentile absolute skew pull: {PercentileValue( [ data[ "absolute_skew_pull" ] for data in datas_histogram ], 0.05 )}\n'
            report += f'Mean absolute skew pull: {float( numpy.mean( [ data[ "absolute_skew_pull" ] for data in datas_histogram ] ) )}\n'
            report += f'Max absolute skew pull: {float( max( [ data[ "absolute_skew_pull" ] for data in datas_histogram ] ) )}\n\n'
            
        
        if len( datas_histogram_444_420 ) > 0:
            
            report += f'Mean max regional score 444 vs 420: {float( numpy.mean( [ data[ "max_regional_score" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max max regional score 444 vs 420: {float( max( [ data[ "max_regional_score" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean mean score 444 vs 420: {float( numpy.mean( [ data[ "mean_score" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max mean score 444 vs 420: {float( max( [ data[ "mean_score" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean score variance 444 vs 420: {float( numpy.mean( [ data[ "score_variance" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max score variance 444 vs 420: {float( max( [ data[ "score_variance" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean score skew 444 vs 420: {float( numpy.mean( [ data[ "score_skew" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max score skew 444 vs 420: {float( max( [ data[ "score_skew" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
            report += f'Mean absolute skew pull 444 vs 420: {float( numpy.mean( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444_420 ] ) )}\n'
            report += f'Max absolute skew pull 444 vs 420: {float( max( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444_420 ] ) )}\n\n'
            
        
        if len( datas_histogram_444 ) > 0:
            
            report += f'Mean max regional score 444: {float( numpy.mean( [ data[ "max_regional_score" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max max regional score 444: {float( max( [ data[ "max_regional_score" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean mean score 444: {float( numpy.mean( [ data[ "mean_score" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max mean score 444: {float( max( [ data[ "mean_score" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean score variance 444: {float( numpy.mean( [ data[ "score_variance" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max score variance 444: {float( max( [ data[ "score_variance" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean score skew 444: {float( numpy.mean( [ data[ "score_skew" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max score skew 444: {float( max( [ data[ "score_skew" ] for data in datas_histogram_444 ] ) )}\n\n'
            
            report += f'Mean absolute skew pull 444: {float( numpy.mean( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444 ] ) )}\n'
            report += f'Max absolute skew pull 444: {float( max( [ data[ "absolute_skew_pull" ] for data in datas_histogram_444 ] ) )}\n\n'
            
        
        report += '\n'.join( regional_score_spam ) + '\n\n'
        report += '\n'.join( regional_false_positives ) + '\n\n'
        
        #
        
        reports.append( report )
        
    
    db_dir = CG.client_controller.GetDBDir()
    
    log_path = os.path.join( db_dir, 'visual_tuning.log' )
    
    with open( log_path, 'w', encoding = 'utf-8' ) as f:
        
        f.write( '\n\n'.join( reports ) )
        
    
    
    # run the good files against each other and the bad files. nice fat sample. record the different variables
    # in the first stage, report ranges of the variables for each class of True/False match 'all watermarks had skew >blah'
    # break the 444/442/440 differences out so we can see if there is a common subsampling coefficient we can insert
    # I guess ideally in a future run the differences across subsampling will be normalised and we'd see no difference in future runs
    # save this to a log file in the dir
    
    # future:
    # in a future stage, we may wish to attempt a 'logistic regression' and have weighted coefficients on these, or a sample of them for which it is appropriate, to create a more powerful weighted score
    # might be nice to break the Lab channels into this reporting too, somehow. atm I make a wasserstein score on a 0.6, 0.2, 0.2 weighting or something. we should examine that!
    
    pass
    
