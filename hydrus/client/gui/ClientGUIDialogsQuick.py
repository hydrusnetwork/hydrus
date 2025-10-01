import os
import time

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsButtonQuestions
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.panels import ClientGUIScrolledPanelsSelectFromList
from hydrus.client.gui.panels import ClientGUIScrolledPanelsTextEntry

def EnterText( win: QW.QWidget, message: str, default = '', placeholder = None, allow_blank = False, suggestions = None, max_chars = None, password_entry = False, min_char_width = 72 ) -> str:
    
    title = 'Enter Text'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title, frame_key = 'regular_center_dialog' ) as dlg:
        
        panel = ClientGUIScrolledPanelsTextEntry.EditTextPanel( dlg, message, default, placeholder, allow_blank, suggestions, max_chars, password_entry, min_char_width = min_char_width )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            text = panel.GetValue()
            
            return text
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    

def GetDeleteFilesJobs( win: QW.QWidget, media, default_reason, suggested_file_service_key = None ):
    
    title = 'Delete files?'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title, frame_key = 'regular_center_dialog' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditDeleteFilesPanel( dlg, media, default_reason, suggested_file_service_key = suggested_file_service_key )
        
        dlg.SetPanel( panel )
        
        if panel.QuestionIsAlreadyResolved():
            
            ( hashes_physically_deleted, content_update_packages ) = panel.GetValue()
            
            return ( hashes_physically_deleted, content_update_packages )
            
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            ( hashes_physically_deleted, content_update_packages ) = panel.GetValue()
            
            return ( hashes_physically_deleted, content_update_packages )
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    

def run_auto_yes_no_gubbins( dlg: QW.QDialog, time_to_fire, original_title, action_description, end_state ):
    
    def qt_set_title():
        
        time_string = HydrusTime.TimestampToPrettyTimeDelta( time_to_fire, just_now_threshold = 0, just_now_string = 'imminently' )
        
        title = f'{original_title} (will {action_description} {time_string})'
        
        dlg.setWindowTitle( title )
        
    
    def qt_fire_button():
        
        if dlg.isModal():
            
            dlg.done( end_state )
            
        
    
    while not HydrusTime.TimeHasPassed( time_to_fire ):
        
        job = CG.client_controller.CallLaterQtSafe( dlg, 0.0, 'dialog auto yes/no title set', qt_set_title )
        
        if job.IsDead(): # window closed
            
            return
            
        
        time.sleep( 1 )
        
    
    job = CG.client_controller.CallLaterQtSafe( dlg, 0.0, 'dialog auto yes/no fire', qt_fire_button )
    

# TODO: check_for_cancelled aiiiiieeeeeeeeee
def GetYesNo( win: QW.QWidget, message: str, title = 'Are you sure?', yes_label = 'yes', no_label = 'no', auto_yes_time = None, auto_no_time = None, check_for_cancelled = False ):
    
    with ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionYesNoPanel( dlg, message, yes_label = yes_label, no_label = no_label )
        
        dlg.SetPanel( panel )
        
        if auto_yes_time is not None or auto_no_time is not None:
            
            if auto_yes_time is not None:
                
                CG.client_controller.CallToThread( run_auto_yes_no_gubbins, dlg, HydrusTime.GetNow() + auto_yes_time, dlg.windowTitle(), 'auto-yes', QW.QDialog.DialogCode.Accepted )
                
            elif auto_no_time is not None:
                
                CG.client_controller.CallToThread( run_auto_yes_no_gubbins, dlg, HydrusTime.GetNow() + auto_no_time, dlg.windowTitle(), 'auto-no', QW.QDialog.DialogCode.Rejected )
                
            
        
        return dlg.exec() if not check_for_cancelled else ( dlg.exec(), dlg.WasCancelled() )
        
    

def GetYesNoNo( win: QW.QWidget, message: str, title = 'Are you sure?', yes_label = 'yes', no_tuples = None, auto_yes_time = None, disable_yes_initially = False ):
    
    with ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionYesNoNoPanel( dlg, message, yes_label = yes_label, no_tuples = no_tuples, disable_yes_initially = disable_yes_initially )
        
        dlg.SetPanel( panel )
        
        if auto_yes_time is not None:
            
            CG.client_controller.CallToThread( run_auto_yes_no_gubbins, dlg, HydrusTime.GetNow() + auto_yes_time, dlg.windowTitle(), 'auto-yes', QW.QDialog.DialogCode.Accepted )
            
        
        result = dlg.exec()
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            return ( result, None )
            
        else:
            
            return ( result, panel.GetValue() )
            
        
    

def GetYesYesNo( win: QW.QWidget, message: str, title = 'Are you sure?', yes_tuples = None, no_label = 'no' ):
    
    with ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionYesYesNoPanel( dlg, message, yes_tuples = yes_tuples, no_label = no_label )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            return panel.GetValue()
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    

def OpenDocumentation( win: QW.QWidget, documentation_path: str ):
    
    local_path = os.path.join( HC.HELP_DIR, documentation_path )
    remote_url = "/".join( ( HC.REMOTE_HELP.rstrip( '/' ), documentation_path.lstrip( '/' ) ) ) 
    
    local_launch_path = local_path
    
    if "#" in local_path:
        
        local_path = local_path[ : local_path.find( '#' ) ]
        
    
    if os.path.isfile( local_path ):
        
        ClientPaths.LaunchPathInWebBrowser( local_launch_path )
        
    else:
        
        HydrusData.Print( f'Was asked to open "{documentation_path}", which appeared to be "{local_path}" locally, but it did not seem to exist!' )
        
        message = 'You do not have a local help! Are you running from source? Would you like to open the online help or see a guide on how to build your own?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'open online help', 0 ) )
        yes_tuples.append( ( 'open how to build guide', 1 ) )
        
        try:
            
            result = GetYesYesNo( win, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if result == 0:
            
            url = remote_url
            
        else:
            
            url = '/'.join( ( HC.REMOTE_HELP.rstrip( '/' ), HC.DOCUMENTATION_ABOUT_DOCS.lstrip( '/' ) ) )
            
        
        ClientPaths.LaunchURLInWebBrowser( url )
        
    

def PresentClipboardParseError( win: QW.QWidget, content: str, expected_content_description: str, e: Exception ):
    
    MAX_CONTENT_SIZE = 1024
    
    log_message = 'Clipboard Error!\nI was expecting: {}'.format( expected_content_description )
    
    if len( content ) > MAX_CONTENT_SIZE:
        
        log_message += '\nFirst {} of content received (total was {}):\n'.format( HydrusData.ToHumanBytes( MAX_CONTENT_SIZE ), HydrusData.ToHumanBytes( len( content ) ) ) + content[:MAX_CONTENT_SIZE]
        
    else:
        
        log_message += '\nContent received ({}):\n'.format( HydrusData.ToHumanBytes( len( content ) ) ) + content[:MAX_CONTENT_SIZE]
        
    
    HydrusData.DebugPrint( log_message )
    
    HydrusData.PrintException( e, do_wait = False )
    
    message = 'Sorry, I could not understand what was in the clipboard. I was expecting "{}" but received this text:\n\n{}\n\nMore details have been written to the log, but the general error was:\n\n{}'.format( expected_content_description, HydrusText.ElideText( content, 64 ), repr( e ) )
    
    ClientGUIDialogsMessage.ShowCritical( win, 'Clipboard Error!', message )
    

def SelectFromList( win: QW.QWidget, title: str, choice_tuples, value_to_select = None, sort_tuples = True, allow_insta_one_item_select = True ):
    
    if len( choice_tuples ) == 1 and allow_insta_one_item_select:
        
        ( ( text, data ), ) = choice_tuples
        
        return data
        
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsSelectFromList.EditSelectFromListPanel( dlg, choice_tuples, value_to_select = value_to_select, sort_tuples = sort_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    

def SelectFromListButtons( win: QW.QWidget, title: str, choice_tuples, message = '' ):
    
    if len( choice_tuples ) == 1:
        
        ( ( text, data, tooltip ), ) = choice_tuples
        
        return data
        
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title, hide_buttons = True ) as dlg:
        
        panel = ClientGUIScrolledPanelsSelectFromList.EditSelectFromListButtonsPanel( dlg, choice_tuples, message = message )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    

def SelectMultipleFromList( win: QW.QWidget, title: str, choice_tuples ):
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsSelectFromList.EditSelectMultiple( dlg, choice_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    

def SelectServiceKey( service_types = None, service_keys = None, unallowed = None, message = 'select service' ):
    
    if service_types is None:
        
        service_types = HC.ALL_SERVICES
        
    
    if service_keys is None:
        
        services = CG.client_controller.services_manager.GetServices( service_types )
        
        service_keys = [ service.GetServiceKey() for service in services ]
        
    
    service_keys = set( service_keys )
    
    if unallowed is not None:
        
        service_keys.difference_update( unallowed )
        
    
    if len( service_keys ) == 0:
        
        return None
        
    elif len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        return service_key
        
    else:
        
        services = { CG.client_controller.services_manager.GetService( service_key ) for service_key in service_keys }
        
        choice_tuples = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        try:
            
            tlw = CG.client_controller.GetMainTLW()
            
            service_key = SelectFromList( tlw, message, choice_tuples )
            
            return service_key
            
        except HydrusExceptions.CancelledException:
            
            return None
            
        
    
