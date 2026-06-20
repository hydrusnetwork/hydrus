from qtpy import QtWidgets as QW

from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIMenus

def AppendSlideshowMenu( win: CAC.ApplicationCommandProcessorMixin, menu: QW.QMenu, slideshow_is_running: bool, do_submenu = True, slideshow_duration = None, slideshow_is_shuffling = False, slideshow_is_playing_once_through = False ):
    
    if slideshow_duration == 0.0:
        
        slideshow_duration = None
        
    
    slideshow_menu_label = 'slideshow running' if slideshow_is_running else 'start slideshow'
    
    if do_submenu:
        
        slideshow_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, slideshow_menu, slideshow_menu_label )
        
    else:
        
        slideshow_menu = menu
        
    
    slideshow_durations = CG.client_controller.new_options.GetSlideshowDurations()
    
    if slideshow_is_running:
        
        ClientGUIMenus.AppendMenuItem( slideshow_menu, 'stop' + ( '' if slideshow_duration is None else ( ' (' + HydrusTime.TimeDeltaToPrettyTimeDelta( slideshow_duration ) + ')' ) ), 'Stop the current slideshow.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_SLIDESHOW ) )
        
    else:
        
        if slideshow_duration is not None:
            
            ClientGUIMenus.AppendMenuItem( slideshow_menu, 'resume at ' + HydrusTime.TimeDeltaToPrettyTimeDelta( slideshow_duration ), 'Resume at the previous slideshow period.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_SLIDESHOW ) )
            
        
    
    ClientGUIMenus.AppendSeparator( slideshow_menu )
    
    for slideshow_duration in slideshow_durations:
        
        pretty_duration = HydrusTime.TimeDeltaToPrettyTimeDelta( slideshow_duration )
        
        ClientGUIMenus.AppendMenuItem( slideshow_menu, pretty_duration, f'Start a slideshow that changes media every {pretty_duration}.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_START_SLIDESHOW, slideshow_duration ) )
        
    
    ClientGUIMenus.AppendMenuItem( slideshow_menu, 'very fast', 'Start a very fast slideshow.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_START_SLIDESHOW, 0.08 ) )
    ClientGUIMenus.AppendMenuItem( slideshow_menu, 'custom interval', 'Start a slideshow with a custom interval.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_START_SLIDESHOW ) )
    
    ClientGUIMenus.AppendSeparator( slideshow_menu )
    
    initial_thiswindow_value = slideshow_is_shuffling
    initial_newoptions_value = CG.client_controller.new_options.GetBoolean( 'slideshows_progress_randomly' )
    
    ClientGUIMenus.AppendMenuCheckItem( slideshow_menu, 'shuffle this slideshow', 'Check this to progress randomly through the slideshow.', initial_thiswindow_value, win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_FLIP_THISWINDOW_SLIDESHOW_SHUFFLE ) )
    ClientGUIMenus.AppendMenuCheckItem( slideshow_menu, 'all slideshows shuffle', 'Toggle whether new windows start with random slideshows on.', initial_newoptions_value, win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_FLIP_GLOBAL_SLIDESHOW_SHUFFLE ) )
    
    ClientGUIMenus.AppendSeparator( slideshow_menu )
    
    ClientGUIMenus.AppendMenuCheckItem( slideshow_menu, 'this slideshow plays media once through', 'Override the \'always play media once through\' behaviour for this window only. New windows will still use the global option.', slideshow_is_playing_once_through, win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_FLIP_THISWINDOW_SLIDESHOW_ALWAYS_PLAY_DURATION_MEDIA_ONCE_THROUGH ) )
    ClientGUIMenus.AppendMenuCheckItem( slideshow_menu, 'always play media once through', 'Check this to always play the complete media duration at least once before moving on.', CG.client_controller.new_options.GetBoolean( 'slideshow_always_play_duration_media_once_through' ), win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_FLIP_GLOBAL_SLIDESHOW_ALWAYS_PLAY_DURATION_MEDIA_ONCE_THROUGH ) )
    
