from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class ExternalProgramsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        browser_panel = ClientGUICommon.StaticBox( self, 'web browser launch path' )
        
        self._web_browser_path = QW.QLineEdit( browser_panel )
        
        web_browser_path = self._new_options.GetNoneableString( 'web_browser_path' )
        
        if web_browser_path is not None:
            
            self._web_browser_path.setText( web_browser_path )
            
        
        #
        
        mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' launch paths' )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EXTERNAL_PROGRAMS.ID, self._ConvertMimeToDisplayTuple, self._ConvertMimeToSortTuple )
        
        self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( mime_panel, 15, model, activation_callback = self._EditMimeLaunch )
        
        for mime in HC.SEARCHABLE_MIMES:
            
            launch_path = self._new_options.GetMimeLaunch( mime )
            
            row = ( mime, launch_path )
            
            self._mime_launch_listctrl.AddData( row )
            
        
        self._mime_launch_listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'By default, when you ask to open a URL, hydrus will send it to your OS, and that figures out what your "default" web browser is. These OS launch commands can be buggy, though, and sometimes drop #anchor components. If this happens to you, set the specific launch command for your web browser here.'
        text += '\n' * 2
        text += 'The command here must include a "%path%" component, normally ideally within those quote marks, which is where hydrus will place the URL when it executes the command. A good example would be:'
        text += '\n' * 2
        
        if HC.PLATFORM_WINDOWS:
            
            text += 'C:\\program files\\firefox\\firefox.exe "%path%"'
            
        elif HC.PLATFORM_MACOS:
            
            text += 'open -a /Applications/Firefox.app -g "%path%"'
            
        else:
            
            text += 'firefox "%path%"'
            
        
        st = ClientGUICommon.BetterStaticText( browser_panel, text )
        st.setWordWrap( True )
        
        browser_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Manual web browser launch command: ', self._web_browser_path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( mime_panel, rows )
        
        browser_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Similarly, when you ask to open a file "externally", hydrus will send it to your OS, and that figures out your "default" program. This may fail or direct to a program you do not want for several reasons, so you can set a specific override here.'
        text += '\n' * 2
        text += 'Again, make sure you include the "%path%" component. Most programs are going to be like \'program_exe "%path%"\', but some may need a profile switch or "-o" open command or similar.'
        
        st = ClientGUICommon.BetterStaticText( mime_panel, text )
        st.setWordWrap( True )
        
        mime_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        mime_panel.Add( self._mime_launch_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        QP.AddToLayout( vbox, browser_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertMimeToDisplayTuple( self, data ):
        
        ( mime, launch_path ) = data
        
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        if launch_path is None:
            
            pretty_launch_path = 'default: {}'.format( HydrusPaths.GetDefaultLaunchPath() )
            
        else:
            
            pretty_launch_path = launch_path
            
        
        display_tuple = ( pretty_mime, pretty_launch_path )
        
        return display_tuple
        
    
    _ConvertMimeToSortTuple = _ConvertMimeToDisplayTuple
    
    def _EditMimeLaunch( self ):
        
        row = self._mime_launch_listctrl.GetTopSelectedData()
        
        if row is None:
            
            return
            
        
        ( mime, launch_path ) = row
        
        message = 'Enter the new launch path for {}'.format( HC.mime_string_lookup[ mime ] )
        message += '\n' * 2
        message += 'Hydrus will insert the file\'s full path wherever you put %path%, even multiple times!'
        message += '\n' * 2
        message += 'Set as blank to reset to default.'
        
        if launch_path is None:
            
            default = 'program "%path%"'
            
        else:
            
            default = launch_path
            
        
        try:
            
            new_launch_path = ClientGUIDialogsQuick.EnterText( self, message, default = default, allow_blank = True )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if new_launch_path == '':
            
            new_launch_path = None
            
        
        if new_launch_path not in ( launch_path, default ):
            
            if new_launch_path is not None and '%path%' not in new_launch_path:
                
                message = f'Hey, your command "{new_launch_path}" did not include %path%--it probably is not going to work! Are you sure this is ok?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            edited_row = ( mime, new_launch_path )
            
            self._mime_launch_listctrl.ReplaceData( row, edited_row, sort_and_scroll = True )
            
        
    
    def UpdateOptions( self ):
        
        web_browser_path = self._web_browser_path.text()
        
        if web_browser_path == '':
            
            web_browser_path = None
            
        
        self._new_options.SetNoneableString( 'web_browser_path', web_browser_path )
        
        for ( mime, launch_path ) in self._mime_launch_listctrl.GetData():
            
            self._new_options.SetMimeLaunch( mime, launch_path )
            
        
    
