import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.executables import ClientExecutableManager, ClientExecutablePipelines
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

class EditOpenFileIdsAndNamesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, mime: int, ids_and_names: list[ HydrusSerialisable.IdAndName ], executable_manager: ClientExecutableManager.ExecutableManager ):
        
        super().__init__( parent )
        
        self._executable_manager = executable_manager
        
        self._ids_and_names = ClientGUIListBoxes.QueueListBox(
            self,
            4,
            lambda id_and_name: id_and_name.name,
            self._AddIdAndName,
            self._EditIdAndName
        )
        
        #
        
        self._ids_and_names.SetData( ids_and_names )
        
        #
        
        text = f'You can select multiple programs, and these choices will be exposed in the media "open externally" menus; for quicker actions like button clicks or shortcuts, the top-most is the default.'
        
        st = ClientGUICommon.BetterStaticText( self, label = text )
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ids_and_names, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
    
    def _GetRemainingAvailableChoicesTuples( self ):
        
        possible_executable_ids_and_names = self._executable_manager.GetIdsAndNamesOfType( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE )
        
        existing_executable_ids_and_names = set( self.GetValue() )
        
        choice_tuples = [ ( id_and_name.name, id_and_name, 'Select this call.' ) for id_and_name in possible_executable_ids_and_names if id_and_name not in existing_executable_ids_and_names ]
        
        if len( choice_tuples ) == 0:
            
            message = 'You have added all the "open single file" calls that are currently registered with the executable manager! Try going to the "external programs" panel to add more.'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            raise HydrusExceptions.CancelledException( message )
            
        
        return choice_tuples
        
    
    def _AddIdAndName( self ):
        
        choice_tuples = self._GetRemainingAvailableChoicesTuples()
        
        return ClientGUIDialogsQuick.SelectFromListButtons( self, 'select call to add', choice_tuples, allow_insta_one_item_select = False )
        
    
    def _EditIdAndName( self, id_and_name: HydrusSerialisable.IdAndName ) -> HydrusSerialisable.IdAndName:
        
        choice_tuples = self._GetRemainingAvailableChoicesTuples()
        
        return ClientGUIDialogsQuick.SelectFromListButtons( self, 'select call to add', choice_tuples, allow_insta_one_item_select = False )
        
    
    def GetValue( self ):
        
        ids_and_names = self._ids_and_names.GetData()
        
        return ids_and_names
        
    

class OpenExternallyPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, executable_manager_callable: collections.abc.Callable[ [], ClientExecutableManager.ExecutableManager ] ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        self._executable_manager_callable = executable_manager_callable
        
        browser_panel = ClientGUICommon.StaticBox( self, 'URL calls' )
        
        self._launch_url_executable_ids_and_names = ClientGUIListBoxes.QueueListBox(
            self,
            4,
            lambda id_and_name: id_and_name.name,
            self._AddLaunchURLIdAndName,
            self._EditLaunchURLIdAndName
        )
        
        launch_url_executable_ids_and_names = self._new_options.GetLaunchURLExecutableIdsAndNames()
        
        self._launch_url_executable_ids_and_names.SetData( launch_url_executable_ids_and_names )
        
        #
        
        mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' calls' )
        
        self._mime_launch_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( mime_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_OPEN_EXTERNALLY.ID, self._ConvertMimeToDisplayTuple, self._ConvertMimeToSortTuple )
        
        self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._mime_launch_listctrl_panel, 12, model, activation_callback = self._EditMimeLaunch, use_simple_delete = True, can_delete_callback = self._GeneralFileIsNotSelected )
        
        self._mime_launch_listctrl_panel.SetListCtrl( self._mime_launch_listctrl )
        
        self._mime_launch_listctrl_panel.AddButton( 'add', self._AddMimeLaunch )
        self._mime_launch_listctrl_panel.AddButton( 'edit', self._EditMimeLaunch, enabled_only_on_single_selection = True )
        self._mime_launch_listctrl_panel.AddDeleteButton( enabled_check_func = self._GeneralFileIsNotSelected )
        
        mimes_to_launch_file_executable_ids_and_names = self._new_options.GetMimesToLaunchFileExecutableIdsAndNames()
        
        self._mime_launch_listctrl.AddDatas( list( mimes_to_launch_file_executable_ids_and_names.items() ) )
        
        self._mime_launch_listctrl.Sort()
        
        #
        
        text = 'By default, when you ask to open a URL, hydrus will send it to your OS, and that figures out what your "default" web browser is. These OS launch commands can be buggy, though, and sometimes lose #anchor components. If this happens to you, set the specific launch command for your web browser here. You can set several different commands for multiple browsers or profiles, and these choices will be exposed in the deeper url menus; the top-most is the default for quicker actions like shortcuts or left-clicks on hyperlinks.'
        
        st = ClientGUICommon.BetterStaticText( browser_panel, text )
        st.setWordWrap( True )
        
        browser_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        browser_panel.Add( self._launch_url_executable_ids_and_names, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        text = 'Similarly, when you ask to open a file "externally", by default hydrus will send it to your OS to figure out your "default" program. This OS call may fail or direct to a program you do not want for several reasons, so you may set a specific and more reliable call here instead. You can even set multiple.'
        text += '\n' * 2
        text += 'The "all files" entry is a backstop for all files. You can set an entry for "image", to mean all images, or specifically down to each filetype. A specific entry _completely overwrites_ a more general entry.'
        
        st = ClientGUICommon.BetterStaticText( mime_panel, text )
        st.setWordWrap( True )
        
        mime_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        mime_panel.Add( self._mime_launch_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'This page uses the executable calls as set under the "external programs" panel. Go there first if you need to define a new url/file call.'
        label += '\n\n'
        label += 'If you rename calls there, the new labels will not update here until dialog ok. If you delete calls there, they will be removed from here on dialog ok. If you make big edits to your callables, it is best to ok the options dialog to lock them in and come back in here.' 
        
        top_st = ClientGUICommon.BetterStaticText( self, label = label )
        top_st.setWordWrap( True )
        top_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, top_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, browser_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _GetRemainingAvailableLaunchURLChoicesTuples( self ):
        
        executable_manager = self._executable_manager_callable()
        
        possible_executable_ids_and_names = executable_manager.GetIdsAndNamesOfType( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL )
        
        existing_ids_and_names = set( self._launch_url_executable_ids_and_names.GetData() )
        
        choice_tuples = [ ( id_and_name.name, id_and_name, 'Select this call.' ) for id_and_name in possible_executable_ids_and_names if id_and_name not in existing_ids_and_names ]
        
        if len( choice_tuples ) == 0:
            
            message = 'You have added all the "open single file" calls that are currently registered with the executable manager! Try going to the "external programs" panel to add more.'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            raise HydrusExceptions.CancelledException( message )
            
        
        return choice_tuples
        
    
    def _AddLaunchURLIdAndName( self ):
        
        choice_tuples = self._GetRemainingAvailableLaunchURLChoicesTuples()
        
        return ClientGUIDialogsQuick.SelectFromListButtons( self, 'select call to add', choice_tuples, allow_insta_one_item_select = False )
        
    
    def _EditLaunchURLIdAndName( self, id_and_name: HydrusSerialisable.IdAndName ) -> HydrusSerialisable.IdAndName:
        
        choice_tuples = self._GetRemainingAvailableLaunchURLChoicesTuples()
        
        return ClientGUIDialogsQuick.SelectFromListButtons( self, 'select call to add', choice_tuples, allow_insta_one_item_select = False )
        
    
    def _ConvertMimeToDisplayTuple( self, data ):
        
        ( mime, executable_ids_and_names ) = data
        
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        if len( executable_ids_and_names ) == 0:
            
            pretty_executable_ids_and_names = 'empty -- will fall back to default OS launch'
            
        else:
            
            pretty_executable_ids_and_names = ', '.join( [ id_and_name.name for id_and_name in executable_ids_and_names ] )
            
        
        display_tuple = ( pretty_mime, pretty_executable_ids_and_names )
        
        return display_tuple
        
    
    def _ConvertMimeToSortTuple( self, data ):
        
        ( mime, ids_and_names ) = data

        ( pretty_mime, pretty_executable_ids_and_names ) = self._ConvertMimeToDisplayTuple( data )
        
        if mime == HC.GENERAL_FILE:
            
            mime_sort_num = -2
            
        elif mime in HC.GENERAL_CLASSES_OF_FILETYPE:
            
            mime_sort_num = -1
            
        else:
            
            mime_sort_num = 0
            
        
        sort_tuple = ( ( mime_sort_num, pretty_mime ), pretty_executable_ids_and_names )
        
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
                
            
            ids_and_names = []
            
            executable_manager = self._executable_manager_callable()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit calls' ) as dlg:
                
                panel = EditOpenFileIdsAndNamesPanel( dlg, mime_to_use, ids_and_names, executable_manager )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    edited_ids_and_names = panel.GetValue()
                    
                    row = ( mime_to_use, edited_ids_and_names )
                    
                    self._mime_launch_listctrl.AddData( row, select_sort_and_scroll = True )
                    
                
            
        
    
    def _EditMimeLaunch( self ):
        
        row = self._mime_launch_listctrl.GetTopSelectedData()
        
        if row is None:
            
            return
            
        
        ( mime, ids_and_names ) = row
        
        executable_manager = self._executable_manager_callable()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit launch path' ) as dlg:
            
            panel = EditOpenFileIdsAndNamesPanel( dlg, mime, ids_and_names, executable_manager )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_ids_and_names = panel.GetValue()
                
                edited_row = ( mime, edited_ids_and_names )
                
                self._mime_launch_listctrl.ReplaceData( row, edited_row, sort_and_scroll = True )
                
            
        
    
    def _GeneralFileIsNotSelected( self ):
        
        rows = self._mime_launch_listctrl.GetData( only_selected = True )
        
        for ( mime, launch_paths ) in rows:
            
            if mime == HC.GENERAL_FILE:
                
                return False
                
            
        
        return True
        
    
    def UpdateOptions( self ):
        
        executable_manager = self._executable_manager_callable()
        
        launch_url_executable_ids_and_names = self._launch_url_executable_ids_and_names.GetData()
        
        if len( launch_url_executable_ids_and_names ) == 0:
            
            launch_url_executable_ids_and_names = [ executable_manager.GetOSLaunchURLCallable().GetIdAndName() ]
            
        
        launch_url_executable_ids_and_names = executable_manager.WashIdsAndNames( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL, launch_url_executable_ids_and_names )
        
        self._new_options.SetLaunchURLExecutableIdsAndNames( launch_url_executable_ids_and_names )
        
        mimes_to_launch_file_executable_ids_and_names = dict()
        
        for ( mime, ids_and_names ) in self._mime_launch_listctrl.GetData():
            
            if len( ids_and_names ) == 0:
                
                ids_and_names = [ executable_manager.GetOSLaunchFileCallable().GetIdAndName() ]
                
            
            ids_and_names = executable_manager.WashIdsAndNames( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE, ids_and_names )
            
            mimes_to_launch_file_executable_ids_and_names[ mime ] = ids_and_names
            
        
        if HC.GENERAL_FILE not in mimes_to_launch_file_executable_ids_and_names:
            
            mimes_to_launch_file_executable_ids_and_names[ HC.GENERAL_FILE ] = [ executable_manager.GetOSLaunchFileCallable().GetIdAndName() ]
            
        
        self._new_options.SetMimesToLaunchFileExecutableIdsAndNames( mimes_to_launch_file_executable_ids_and_names )
        
    
