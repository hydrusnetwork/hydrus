def CalculateMediaHeightForControlsBar( container_height: int, controls_bar_height: int, reserve_space: bool, controls_bar_hidden: bool ) -> int:
    
    if reserve_space and not controls_bar_hidden:
        
        return max( 1, container_height - controls_bar_height )
        
    
    return container_height
