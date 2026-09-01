from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class EditMimeLaunchPathsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, mime: int, launch_paths: list[ str | None ] ):
        
        super().__init__( parent )
        
        self._launch_paths = ClientGUIListBoxes.QueueListBox(
            self,
            4,
            lambda s: s if isinstance( s, str ) else 'default OS call',
            self._AddLaunchPath,
            self._EditLaunchPath
        )
        
        #
        
        self._launch_paths.SetData( launch_paths )
        
        #
        
        text = f'Editing launch paths for {HC.mime_mimetype_string_lookup[ mime ]}. You can set several different commands for multiple programs, and these choices will be exposed in the media "url" menus; for quicker actions like button clicks or shortcuts, the top-most is the default.'
        text += '\n' * 2
        text += 'The command here must include a "%path%" component, normally ideally within those quote marks, which is where hydrus will place the URL when it executes the command. A good example would be:'
        text += '\n' * 2
        
        if HC.PLATFORM_WINDOWS:
            
            text += 'C:\\program files\\my_program\\my_program.exe "%path%"'
            
        elif HC.PLATFORM_MACOS:
            
            text += 'open -a "My App" "%path%"'
            
        else:
            
            text += 'my_program "%path%"'
            
        
        st = ClientGUICommon.BetterStaticText( self, label = text )
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._launch_paths, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
    
    def _AddLaunchPath( self ):
        
        return self._EditLaunchPath( '' )
        
    
    def _EditLaunchPath( self, launch_path: str | None ) -> str | None:
        
        if launch_path is None:
            
            launch_path_for_editing = ''
            
        else:
            
            launch_path_for_editing = launch_path
            
        
        message = 'Edit the launch path. Do not forget the "%path%". Leave blank to select the default OS call.'
        
        try:
            
            edited_launch_path = ClientGUIDialogsQuick.EnterText(
                self,
                message,
                default = launch_path_for_editing,
                allow_blank = True,
                title = 'Enter launch path',
            )
            
            if edited_launch_path == '':
                
                edited_launch_path = None
                
            
            if edited_launch_path is not None and '%path%' not in edited_launch_path:
                
                message = f'Hey, your command "{edited_launch_path}" did not include %path%--it probably is not going to work! Are you sure this is ok?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
            return edited_launch_path
            
        except HydrusExceptions.CancelledException:
            
            raise HydrusExceptions.VetoException()
            
        
    
    def GetValue( self ):
        
        launch_paths = self._launch_paths.GetData()
        
        return launch_paths
        
    

class OpenExternallyPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        browser_panel = ClientGUICommon.StaticBox( self, 'web browser launch path' )
        
        self._web_browser_launch_paths = ClientGUIListBoxes.QueueListBox(
            self,
            4,
            lambda s: s if isinstance( s, str ) else 'default OS call',
            self._AddWebBrowserPath,
            self._EditWebBrowserPath
        )
        
        web_browser_launch_paths = self._new_options.GetWebBrowserLaunchPaths()
        
        self._web_browser_launch_paths.SetData( web_browser_launch_paths )
        
        #
        
        mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' launch paths' )
        
        self._mime_launch_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( mime_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_OPEN_EXTERNALLY.ID, self._ConvertMimeToDisplayTuple, self._ConvertMimeToSortTuple )
        
        self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._mime_launch_listctrl_panel, 12, model, activation_callback = self._EditMimeLaunch )
        
        self._mime_launch_listctrl_panel.SetListCtrl( self._mime_launch_listctrl )
        
        self._mime_launch_listctrl_panel.AddButton( 'add', self._AddMimeLaunch )
        self._mime_launch_listctrl_panel.AddButton( 'edit', self._EditMimeLaunch, enabled_only_on_single_selection = True )
        self._mime_launch_listctrl_panel.AddDeleteButton( enabled_check_func = self._GeneralFileIsNotSelected )
        
        open_externally_launch_paths = self._new_options.GetAllOpenExternallyLaunchPaths()
        
        self._mime_launch_listctrl.AddDatas( list( open_externally_launch_paths.items() ) )
        
        self._mime_launch_listctrl.Sort()
        
        #
        
        text = 'By default, when you ask to open a URL, hydrus will send it to your OS, and that figures out what your "default" web browser is. These OS launch commands can be buggy, though, and sometimes lose #anchor components. If this happens to you, set the specific launch command for your web browser here. You can set several different commands for multiple browsers or profiles, and these choices will be exposed in the deeper url menus; the top-most is the default for quicker actions like shortcuts or left-clicks on hyperlinks.'
        text += '\n' * 2
        text += 'The command here must include a "%url%" component, normally ideally within those quote marks, which is where hydrus will place the URL when it executes the command. A good example would be:'
        text += '\n' * 2
        
        if HC.PLATFORM_WINDOWS:
            
            text += 'C:\\program files\\firefox\\firefox.exe "%url%"'
            
        elif HC.PLATFORM_MACOS:
            
            text += 'open -a /Applications/Firefox.app -g "%url%"'
            
        else:
            
            text += 'firefox "%url%"'
            
        
        st = ClientGUICommon.BetterStaticText( browser_panel, text )
        st.setWordWrap( True )
        
        browser_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        browser_panel.Add( self._web_browser_launch_paths, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        text = 'Similarly, when you ask to open a file "externally", by default hydrus will send it to your OS to figure out your "default" program. This OS call may fail or direct to a program you do not want for several reasons, so you may set a specific and more reliable call here instead. You can even set multiple.'
        text += '\n' * 2
        text += 'The "file" entry is a backstop for all files. You can set an entry for "image", to mean all images, or specifically down to each filetype. A specific entry _completely overwrites_ a more general entry.'
        text += '\n' * 2
        text += 'Again, make sure you include the "%path%" component. Most programs are going to be like \'program_exe "%path%"\', but some may need a profile-selection switch or "-o" open command or similar.'
        
        st = ClientGUICommon.BetterStaticText( mime_panel, text )
        st.setWordWrap( True )
        
        mime_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        mime_panel.Add( self._mime_launch_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, browser_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _AddWebBrowserPath( self ):
        
        return self._EditWebBrowserPath( '' )
        
    
    def _EditWebBrowserPath( self, launch_path: str | None ) -> str | None:
        
        if launch_path is None:
            
            launch_path_for_editing = ''
            
        else:
            
            launch_path_for_editing = launch_path
            
        
        message = 'Edit the launch path. Do not forget the "%url%". Leave blank to select the default OS call.'
        
        try:
            
            edited_launch_path = ClientGUIDialogsQuick.EnterText(
                self,
                message,
                default = launch_path_for_editing,
                allow_blank = True,
                title = 'Enter launch path',
            )
            
            if edited_launch_path == '':
                
                edited_launch_path = None
                
            
            if edited_launch_path is not None and '%url%' not in edited_launch_path:
                
                message = f'Hey, your command "{edited_launch_path}" did not include %url%--it probably is not going to work! Are you sure this is ok?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
            return edited_launch_path
            
        except HydrusExceptions.CancelledException:
            
            raise HydrusExceptions.VetoException()
            
        
    
    def _ConvertMimeToDisplayTuple( self, data ):
        
        ( mime, launch_paths ) = data
        
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        if len( launch_paths ) == 0:
            
            pretty_launch_paths = 'empty -- will be replaced with default launch on dialog ok'
            
        else:
            
            def prettify_launch_path( l_p: str | None ):
                
                if l_p is None:
                    
                    pretty_l_p = 'default: {}'.format( ClientPaths.GetDefaultLaunchPath() )
                    
                else:
                    
                    pretty_l_p = l_p
                    
                
                return pretty_l_p
                
            
            pretty_launch_paths = ', '.join( [ prettify_launch_path( launch_path ) for launch_path in launch_paths ] )
            
        
        display_tuple = ( pretty_mime, pretty_launch_paths )
        
        return display_tuple
        
    
    def _ConvertMimeToSortTuple( self, data ):
        
        ( mime, launch_paths ) = data

        ( pretty_mime, pretty_launch_paths ) = self._ConvertMimeToDisplayTuple( data )
        
        if mime == HC.GENERAL_FILE:
            
            mime_sort_num = -2
            
        elif mime in HC.GENERAL_CLASSES_OF_FILETYPE:
            
            mime_sort_num = -1
            
        else:
            
            mime_sort_num = 0
            
        
        sort_tuple = ( ( mime_sort_num, pretty_mime ), pretty_launch_paths )
        
        return sort_tuple
        
    
    def _AddMimeLaunch( self ):
        
        all_mimes_in_use = { mime for ( mime, launch_paths ) in self._mime_launch_listctrl.GetData() }
        
        all_mimes_we_can_use = list( HC.GENERAL_CLASSES_OF_FILETYPE )
        all_mimes_we_can_use.extend( HC.SEARCHABLE_MIMES )
        
        remaining_mimes_we_can_pick_from = [ mime for mime in all_mimes_we_can_use if mime not in all_mimes_in_use ]
        
        if len( remaining_mimes_we_can_pick_from ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You have managed to add an entry for every possible mime and general mimetype! What are you doing!!!' )
            
            return
            
        else:
            
            try:
                
                choice_tuples = [ ( HC.mime_mimetype_string_lookup[ mime ], mime ) for mime in remaining_mimes_we_can_pick_from ]
                
                mime_to_use = ClientGUIDialogsQuick.SelectFromList( self, 'which filetype?', choice_tuples, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            launch_paths = []
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit launch path' ) as dlg:
                
                panel = EditMimeLaunchPathsPanel( dlg, mime_to_use, launch_paths )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    edited_launch_paths = panel.GetValue()
                    
                    row = ( mime_to_use, edited_launch_paths )
                    
                    self._mime_launch_listctrl.AddData( row, select_sort_and_scroll = True )
                    
                
            
        
    
    def _EditMimeLaunch( self ):
        
        row = self._mime_launch_listctrl.GetTopSelectedData()
        
        if row is None:
            
            return
            
        
        ( mime, launch_paths ) = row
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit launch path' ) as dlg:
            
            panel = EditMimeLaunchPathsPanel( dlg, mime, launch_paths )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_launch_paths = panel.GetValue()
                
                edited_row = ( mime, edited_launch_paths )
                
                self._mime_launch_listctrl.ReplaceData( row, edited_row, sort_and_scroll = True )
                
            
        
    
    def _GeneralFileIsNotSelected( self ):
        
        rows = self._mime_launch_listctrl.GetData( only_selected = True )
        
        for ( mime, launch_paths ) in rows:
            
            if mime == HC.GENERAL_FILE:
                
                return False
                
            
        
        return True
        
    
    def UpdateOptions( self ):
        
        web_browser_launch_paths = self._web_browser_launch_paths.GetData()
        
        if len( web_browser_launch_paths ) == 0:
            
            web_browser_launch_paths = [ None ]
            
        
        self._new_options.SetWebBrowserLaunchPaths( web_browser_launch_paths )
        
        open_externally_launch_paths = dict()
        
        for ( mime, launch_paths ) in self._mime_launch_listctrl.GetData():
            
            if len( launch_paths ) == 0:
                
                launch_paths = [ None ]
                
            
            open_externally_launch_paths[ mime ] = launch_paths
            
        
        if HC.GENERAL_FILE not in open_externally_launch_paths:
            
            open_externally_launch_paths[ HC.GENERAL_FILE ] = [ None ]
            
        
        self._new_options.SetOpenExternallyLaunchPaths( open_externally_launch_paths )
        
    
