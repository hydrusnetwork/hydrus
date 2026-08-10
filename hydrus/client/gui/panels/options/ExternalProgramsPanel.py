from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutableDefaults
from hydrus.client.executables import ClientExecutableManager
from hydrus.client.executables import ClientExecutablePipelines
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class EditClientExecutableActualCall( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, actual_call: ClientExecutableActualCall.ExecutableActualCall ):
        
        super().__init__( parent )
        
        self._call_types = ClientGUICommon.BetterChoice( self )
        
        # TODO: It'd be cool if I had a DropdownBook tbh. does that exist?
        
        for ( label, call_type ) in [
            ( 'local process call', ClientExecutableActualCall.ExecutableLocalProcessCallTemplate ),
            ( 'windows startfile call', ClientExecutableActualCall.ExecutableLocalProcessWindowsStartFile )
        ]:
            
            self._call_types.addItem( label, call_type )
            
        
        self._edit_actual_call_window = QW.QWidget( self )
        
        self._call_types_to_windows = {}
        
        # TODO: We prob want a test panel for each type!
        # put in the 'which' name etc.., and can actually test it
        # put in fake path or something, and actually call it and get tags back
        
        # edit windows for each of the call types
        
        #
        
        # SetValue
        
        #
        
        # hook each window's valueChanged in to us
        # on type change, switch visible window
        # signal on type change too
        
    
    def _ShowCallTypePanel( self, call_type_to_show: type ):
        
        for ( call_type, window ) in self._call_types_to_windows.items():
            
            window.setVisible( call_type == call_type_to_show )
            
        
    
    def SetValue( self, actual_call: ClientExecutableActualCall.ExecutableActualCall ):
        
        call_type = type( actual_call )
        
        if call_type not in self._call_types_to_windows:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'unknown call type!', 'Sorry, the given call for this executable is unknown to this client! It cannot show edit UI for it. Cancel out of this dialog mate.' )
            
            return
            
        
        self._call_types.SetValue( call_type )
        
        self._ShowCallTypePanel( call_type )
        
        self._call_types_to_windows[ call_type ].SetValue( actual_call )
        
        self.valueChanged.emit()
        
    

class EditClientExecutableCallablePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, call: ClientExecutableCallables.ClientExecutableCallable ):
        
        super().__init__( parent )
        
        self._name = QW.QLineEdit( self )
        self._pipeline_type = ClientGUICommon.BetterChoice( self )
        
        for pipeline_type in [
            ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE
        ]:
            
            self._pipeline_type.addItem( ClientExecutablePipelines.executable_pipeline_types_to_strs[ pipeline_type ], pipeline_type )
            
        
        self._pipeline_description = ClientGUICommon.BetterStaticText( self )
        self._pipeline_description.setWordWrap( True )
        
        self._validity_text = ClientGUICommon.BetterStaticText( self )
        self._validity_text.setWordWrap( True )
        
        self._actual_call = EditClientExecutableActualCall( self, call.GetCall() )
        
        #
        
        self.SetValue( call )
        
        #
        
        vbox = QP.VBoxLayout()
        
        # TODO: lay it all out
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'job: ', self._pipeline_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._pipeline_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._validity_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._actual_call, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._pipeline_type.currentIndexChanged.connect( self._UpdatePipelineType )
        self._actual_call.valueChanged.connect( self._UpdateValidity() )
        
    
    def _GetValiditySummary( self ):
        
        # TODO: Do this
        # if there are expected output params but the call doesn't give them, say them
        # if there are inputs but none are used?? sounds reasonable; maybe we get clever with selectable if and when we have multivariate calls
        
        return ( True, 'Everything looks good!' )
        
    
    def _IsValid( self ):
        
        return self._GetValiditySummary()[0]
        
    
    def _UpdatePipelineType( self ):
        
        pipeline_type = self._pipeline_type.GetValue()
        
        pipeline_type_desc = ClientExecutablePipelines.executable_pipeline_types_to_desc_strs[ pipeline_type ]
        pipeline_type_desc += '\n\n'
        
        input_parameter_types = ClientExecutablePipelines.executable_pipeline_types_to_input_params[ pipeline_type ]
        
        if len( input_parameter_types ) == 0:
            
            pipeline_type_desc += 'Is given no input parameters.'
            
        else:
            
            pipeline_type_desc += 'Available input parameters: ' + ', '.join( ( ClientExecutablePipelines.parameter_types_to_strs[ parameter_type ] for parameter_type in input_parameter_types ) )
            
        
        pipeline_type_desc += '\n\n'
        
        output_parameter_types = ClientExecutablePipelines.executable_pipeline_types_to_output_params[ pipeline_type ]
        
        if len( output_parameter_types ) == 0:
            
            pipeline_type_desc += 'Is not expected to return any output parameters.'
            
        else:
            
            pipeline_type_desc += 'Expected output parameters: ' + ', '.join( ( ClientExecutablePipelines.parameter_types_to_strs[ parameter_type ] for parameter_type in output_parameter_types ) )
            
        
        self._pipeline_description.setText( pipeline_type_desc )
        
        self._UpdateValidity()
        
    
    def _UpdateValidity( self ):
        
        ( is_valid, validity_text ) = self._GetValiditySummary()
        
        self._validity_text.setText( validity_text )
        
        if is_valid:
            
            self._validity_text.setObjectName( 'HydrusValid' )
            
        else:
            
            self._validity_text.setObjectName( 'HydrusWarning' )
            
        
        self._validity_text.style().polish( self._validity_text )
        
    
    def UserIsOKToOK( self ):
        
        if not self._IsValid():
            
            message = 'Hey, it looks like something is not quite right here. Are you sure you want to save this?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    def GetValue( self ):
        
        name = self._name.text()
        pipeline_type = self._pipeline_type.GetValue()
        actual_call = self._actual_call.GetValue()
        
        call = ClientExecutableCallables.ClientExecutableCallable(
            name = name,
            pipeline_type = pipeline_type,
            actual_call = actual_call
        )
        
        return call
        
    
    def SetValue( self, call: ClientExecutableCallables.ClientExecutableCallable ):
        
        self._name.setText( call.GetName() )
        self._pipeline_type.SetValue( call.GetPipelineType() )
        
        self._UpdatePipelineType()
        
        self._actual_call.SetValue( call.GetCall() )
        
        self._UpdateValidity()
        
    

class ExternalProgramsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._executable_manager: ClientExecutableManager.ExecutableManager = ClientExecutableManager.ExecutableManager()
        
        message = 'THIS SYSTEM IS STILL IN TESTING! ONLY ADVANCED USERS SEE THIS, AND IT IS NOT PLUGGED INTO ANYTHING YET.'
        message += '\n\n'
        message += 'Feel free to play with it and let hydev know how you feel. Edit panel is not ready yet, so add/edit do nothing.'
        
        st = ClientGUICommon.BetterStaticText( self, message )
        st.setWordWrap( True )
        
        external_calls_panel = ClientGUICommon.StaticBox( self, 'external calls' )
        
        external_calls_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( external_calls_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EXTERNAL_PROGRAMS.ID, self._ConvertCallableToDisplayTuple, self._ConvertCallableToSortTuple )
        
        self._external_calls = ClientGUIListCtrl.BetterListCtrlTreeView( external_calls_list_panel, 12, model, activation_callback = self._EditCallable, use_simple_delete = True )
        
        external_calls_list_panel.SetListCtrl( self._external_calls )
        
        external_calls_list_panel.AddButton( 'add', self._AddCallableBrandNew )
        external_calls_list_panel.AddButton( 'edit', self._EditCallable, enabled_only_on_single_selection = True )
        external_calls_list_panel.AddDeleteButton()
        external_calls_list_panel.AddSeparator()
        external_calls_list_panel.AddImportExportButtons( ( ClientExecutableCallables.ClientExecutableCallable, ), self._AddCallableFullyFormed )
        external_calls_list_panel.AddDefaultsButton( self._GetDefaultCallables, self._AddCallableFullyFormed )
        
        #
        
        external_calls_panel.Add( external_calls_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, external_calls_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self.setLayout( vbox )
        
    
    def _AddCallableBrandNew( self ):
        
        return
        
        call = ClientExecutableCallables.ClientExecutableCallable( 'new call' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit external program call' ) as dlg:
            
            panel = EditClientExecutableCallablePanel( dlg, call )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_call = panel.GetValue()
                
                self._AddCallableFullyFormed( edited_call )
                
            
        
    
    def _AddCallableFullyFormed( self, call: ClientExecutableCallables.ClientExecutableCallable ):
        
        HydrusSerialisable.SetNonDupeName( call, self._GetExistingNames() )
        
        call.GenerateNewCallableKey()
        
        self._external_calls.AddData( call )
        
    
    def _ConvertCallableToDisplayTuple( self, call: ClientExecutableCallables.ClientExecutableCallable ):
        
        name = call.GetName()
        pipeline_type = call.GetPipelineType()
        desc = call.GetCall().GetCommandDescription()
        
        pretty_pipeline_type = ClientExecutablePipelines.executable_pipeline_types_to_strs[ pipeline_type ]
        
        display_tuple = ( name, pretty_pipeline_type, desc )
        
        return display_tuple
        
    
    _ConvertCallableToSortTuple = _ConvertCallableToDisplayTuple
    
    def _EditCallable( self ):
        
        return
        
        data = self._external_calls.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        call: ClientExecutableCallables.ClientExecutableCallable = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit external program call' ) as dlg:
            
            panel = EditClientExecutableCallablePanel( dlg, call )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                existing_names = self._GetExistingNames()
                existing_names.discard( call.GetName() )
                
                edited_call = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( edited_call, existing_names )
                
                self._external_calls.ReplaceData( call, edited_call, sort_and_scroll = True )
                
            
        
    
    def _GetDefaultCallables( self ) -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
        
        external_callables = list( ClientExecutableDefaults.GetDefaultOpenExternally() )
        external_callables.extend( ClientExecutableDefaults.GetDefaultOpenURL() )
        
        return external_callables
        
    
    def _GetExistingNames( self ) -> set[ str ]:
        
        calls = self._external_calls.GetData()
        
        names = { call.GetName() for call in calls }
        
        return names
        
    
    def UpdateOptions( self ):
        
        # TODO: save this guy on an ok. should it be a manager as held by the controller, or just an options entry? think about it
        # leaning towards its own thing, but w/e
        pass
        
    
