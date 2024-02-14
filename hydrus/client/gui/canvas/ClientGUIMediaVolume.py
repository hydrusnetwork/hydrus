from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIMediaControls

def GetCorrectCurrentMute( canvas_type: int ):
    
    ( global_mute_option_name, global_volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
    
    mute_option_name = global_mute_option_name
    
    if canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
        
        ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_MEDIA_VIEWER ]
        
    elif canvas_type == CC.CANVAS_PREVIEW:
        
        ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_PREVIEW ]
        
    
    return CG.client_controller.new_options.GetBoolean( mute_option_name ) or CG.client_controller.new_options.GetBoolean( global_mute_option_name )
    

def GetCorrectCurrentVolume( canvas_type: int ):
    
    ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
    
    if canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
        
        if CG.client_controller.new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ):
            
            ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_MEDIA_VIEWER ]
            
        
    elif canvas_type == CC.CANVAS_PREVIEW:
        
        if CG.client_controller.new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ):
            
            ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_PREVIEW ]
            
        
    
    return CG.client_controller.new_options.GetInteger( volume_option_name )
    
