import random
import HydrusData

class VPTreeNode( object ):
    
    def __init__( self, phashes ):
        
        ghd = HydrusData.GetHammingDistance
        
        if len( phashes ) == 1:
            
            ( self._phash, ) = phashes
            self._radius = 0
            
            inner_phashes = []
            outer_phashes = []
            
        else:
            
            # we want to choose a good node.
            # a good node is one that doesn't overlap with other circles much
            
            # get a random sample with big lists, to keep cpu costs down
            if len( phashes ) > 50: phashes_sample = random.sample( phashes, 50 )
            else: phashes_sample = phashes
            
            all_nodes_comparisons = { phash1 : [ ( ghd( phash1, phash2 ), phash2 ) for phash2 in phashes_sample if phash2 != phash1 ] for phash1 in phashes_sample }
            
            for comparisons in all_nodes_comparisons.values(): comparisons.sort()
            
            # the median of the sorted hamming distances makes a decent radius
            
            all_nodes_radii = [ ( comparisons[ len( comparisons ) / 2 ], phash ) for ( phash, comparisons ) in all_nodes_comparisons.items() ]
            
            all_nodes_radii.sort()
            
            # let's make our node the phash with the smallest predicted radius
            
            ( ( predicted_radius, whatever ), self._phash ) = all_nodes_radii[ 0 ]
            
            if len( phashes ) > 50:
                
                my_hammings = [ ( ghd( self._phash, phash ), phash ) for phash in phashes if phash != self._phash ]
                
                my_hammings.sort()
                
            else:
                
                my_hammings = all_nodes_comparisons[ self._phash ]
                
            
            median_index = len( my_hammings ) / 2
            
            ( self._radius, whatever ) = my_hammings[ median_index ]
            
            # lets bump our index up until we actually get outside the radius
            while median_index + 1 < len( my_hammings ) and my_hammings[ median_index + 1 ][0] == self._radius: median_index += 1
            
            # now separate my phashes into inside and outside that radius
            
            inner_phashes = [ phash for ( hamming, phash ) in my_hammings[ : median_index + 1 ] ]
            outer_phashes = [ phash for ( hamming, phash ) in my_hammings[ median_index + 1 : ] ]
            
        
        if len( inner_phashes ) == 0: self._inner_node = VPTreeNodeEmpty()
        else: self._inner_node = VPTreeNode( inner_phashes )
        
        if len( outer_phashes ) == 0: self._outer_node = VPTreeNodeEmpty()
        else: self._outer_node = VPTreeNode( outer_phashes )
        
    
    def __len__( self ): return len( self._inner_node ) + len( self._outer_node ) + 1
    
    def GetMatches( self, phash, max_hamming ):
        
        hamming_distance_to_me = HydrusData.GetHammingDistance( self._phash, phash )
        
        matches = []
        
        if hamming_distance_to_me <= max_hamming: matches.append( self._phash )
        
        if hamming_distance_to_me <= ( self._radius + max_hamming ): matches.extend( self._inner_node.GetMatches( phash, max_hamming ) ) # i.e. result could be in inner
        if hamming_distance_to_me >= ( self._radius - max_hamming ): matches.extend( self._outer_node.GetMatches( phash, max_hamming ) ) # i.e. result could be in outer
        
        return matches
        
    
class VPTreeNodeEmpty( object ):
    
    def __init__( self ): pass
    
    def __len__( self ): return 0
    
    def GetMatches( self, phash, max_hamming ): return []
    