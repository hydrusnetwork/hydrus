from qtpy import QtWidgets as QW

from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIMenus

def AppendSlideshowMenu( win: CAC.ApplicationCommandProcessorMixin, menu: QW.QMenu, slideshow_is_running: bool, do_submenu = True ):
    
    slideshow_menu_label = 'slideshow running' if slideshow_is_running else 'start slideshow'
    
    if do_submenu:
        
        slideshow_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, slideshow_menu, slideshow_menu_label )
        
    else:
        
        slideshow_menu = menu
        
    
    if slideshow_is_running:
        
        ClientGUIMenus.AppendMenuItem( slideshow_menu, 'stop', 'Stop the current slideshow.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_SLIDESHOW ) )
        
        ClientGUIMenus.AppendSeparator( slideshow_menu )
        
    
    slideshow_durations = CG.client_controller.new_options.GetSlideshowDurations()
    
    for slideshow_duration in slideshow_durations:
        
        pretty_duration = HydrusTime.TimeDeltaToPrettyTimeDelta( slideshow_duration )
        
        ClientGUIMenus.AppendMenuItem( slideshow_menu, pretty_duration, f'Start a slideshow that changes media every {pretty_duration}.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_START_SLIDESHOW, slideshow_duration ) )
        
    
    ClientGUIMenus.AppendMenuItem( slideshow_menu, 'very fast', 'Start a very fast slideshow.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_START_SLIDESHOW, 0.08 ) )
    ClientGUIMenus.AppendMenuItem( slideshow_menu, 'custom interval', 'Start a slideshow with a custom interval.', win.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_START_SLIDESHOW ) )
    
    ClientGUIMenus.AppendSeparator( slideshow_menu )
    
    initial_value = CG.client_controller.new_options.GetBoolean( 'slideshows_progress_randomly' )
    
    ClientGUIMenus.AppendMenuCheckItem( slideshow_menu, 'slideshows move randomly', 'Check this to progress randomly through the slideshow.', initial_value, CG.client_controller.new_options.FlipBoolean, 'slideshows_progress_randomly' )
    
