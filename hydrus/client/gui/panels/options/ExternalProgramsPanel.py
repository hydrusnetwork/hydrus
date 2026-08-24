import shutil

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutableDefaults
from hydrus.client.executables import ClientExecutableManager
from hydrus.client.executables import ClientExecutablePipelines
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.parsing import ClientParsing

class DefaultLaunchFileWidget( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        desc = 'This will try to launch the file using your OS\'s default file handler.'
        desc += '\n\n'
        
        if HC.PLATFORM_WINDOWS:
            
            desc += 'For Windows, this is a hardcoded system call.'
            
        elif HC.PLATFORM_MACOS:
            
            desc += 'For macOS, this is "open %path%".'
            
        elif HC.PLATFORM_HAIKU:
            
            desc += 'For Haiku, this is "open %path%".'
            
        else:
            
            desc += 'For Linux, this is "xdg-open %path%".'
            
        
        st = ClientGUICommon.BetterStaticText( self, label = desc )
        
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self, 60 ) )
        
    
    def CheckValid( self ):
        
        pass
        
    
    def GetValue( self ):
        
        return ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile()
        
    
    def SetPipelineType( self, pipeline_type: int ):
        
        pass
        
    
    def SetValue( self, actual_call: ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile, pipeline_type: int ):
        
        pass
        
    

class DefaultLaunchURLWidget( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        desc = 'This will try to launch the URL using a library that attempts to figure out your OS\'s default URL handler. It may lose the "#anchor" fragment on the end of an URL.'
        
        st = ClientGUICommon.BetterStaticText( self, label = desc )
        
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self, 60 ) )
        
    
    def CheckValid( self ):
        
        pass
        
    
    def GetValue( self ):
        
        return ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL()
        
    
    def SetPipelineType( self, pipeline_type: int ):
        
        pass
        
    
    def SetValue( self, actual_call: ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL, pipeline_type: int ):
        
        pass
        
    

class EditInputParameterProcessingRulePanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, parameter_processing_rule: ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule ):
        
        self._parameter_type = parameter_processing_rule.parameter_type
        
        super().__init__( parent )
        
        self._name = ClientGUICommon.BetterStaticText( self, label = ClientExecutablePipelines.parameter_types_to_strs[ self._parameter_type ] )
        self._replacement_string = QW.QLineEdit( self, text = parameter_processing_rule.replacement_string )
        self._replacement_string.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is the replacement token. The value of this input parameter will be placed wherever this appears in command template\'s parameters.' ) )
        self._string_processing_button = ClientGUIStringControls.StringProcessorWidget( self, parameter_processing_rule.string_processor, self._GetTestData )
        self._enable = QW.QCheckBox( self )
        
        #
        
        self.SetValue( parameter_processing_rule )
        
        #
        
        # to effect a pseudo-table style, we'll force widths
        
        self._name.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._name, 12 ) )
        self._replacement_string.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._replacement_string, 16 ) )
        self._string_processing_button.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._string_processing_button, 36 ) )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._name, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._replacement_string, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._string_processing_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, label = 'use this parameter: ' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._enable, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        #
        
        self._UpdateUI()
        
        self._enable.clicked.connect( self._UpdateUI )
        
        self._enable.clicked.connect( self.valueChanged )
        self._replacement_string.textChanged.connect( self.valueChanged )
        self._string_processing_button.valueChanged.connect( self.valueChanged )
        
    
    def _GetTestData( self ) -> ClientParsing.ParsingTestData:
        
        texts = ClientExecutablePipelines.parameter_types_to_example_values[ self._parameter_type ]
        
        return ClientParsing.ParsingTestData( {}, texts = texts )
        
    
    def _UpdateUI( self ):
        
        enabled = self._enable.isChecked()
        
        self._name.setEnabled( enabled )
        self._replacement_string.setEnabled( enabled )
        self._string_processing_button.setEnabled( enabled )
        
    
    def GetValue( self ) -> ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule | None:
        
        if not self._enable.isChecked():
            
            return None
            
        
        replacement_string = self._replacement_string.text()
        string_processor = self._string_processing_button.GetValue()
        
        actual_call = ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            parameter_type = self._parameter_type,
            replacement_string = replacement_string,
            string_processor = string_processor
        )
        
        return actual_call
        
    
    def SetValue( self, parameter_processing_rule: ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule | None ):
        
        if parameter_processing_rule is None:
            
            self._enable.setChecked( False )
            
            self._UpdateUI()
            
        else:
            
            self._enable.setChecked( True )
            
            self._UpdateUI()
            
            self._replacement_string.setText( parameter_processing_rule.replacement_string )
            self._string_processing_button.SetValue( parameter_processing_rule.string_processor )
            
        
    

class EditProcessCallExecutableAndParametersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, executable_path: str, executable_parameter_templates: list[ str ] ):
        
        super().__init__( parent )
        
        self._executable_path = QW.QLineEdit( self )
        self._executable_parameter_templates = ClientGUIListBoxes.QueueListBox(
            self,
            8,
            str,
            self._AddParameter,
            self._EditParameter
        )
        
        self._example_full_command = QW.QLineEdit( self )
        self._example_full_command.setReadOnly( True )
        
        self._copy_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy the full command to your clipboard.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste a full command from the clipboard.' ) )
        
        #
        
        self._executable_path.setText( executable_path )
        self._executable_parameter_templates.SetData( executable_parameter_templates )
        
        #
        
        rows = []
        
        rows.append( ( 'executable command/path: ', self._executable_path ) )
        rows.append( ( 'parameters: ', self._executable_parameter_templates ) )
        rows.append( ( 'current full template: ', self._example_full_command ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        message = 'Set the command and its parameters. Do not put parameters in the command input section. Put the %path% or %url% style parameter replacement token in the appropriate place in your parameter list. For quick entry, you can paste the whole template and I will try and figure it out.'
        message += '\n\n'
        message += 'Remember to keep it simple. If you need to set up environment variables or use ten different awkward parameters or pipe and grep around, just write a .sh script to do it all and point to that instead.'
        
        st = ClientGUICommon.BetterStaticText( self, label = message )
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        hbox = QP.HBoxLayout()
        
        hbox.addStretch( 0 )
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self._UpdateExample()
        
        self.widget().setLayout( vbox )
        
        self._executable_path.textChanged.connect( self._UpdateExample )
        self._executable_parameter_templates.listBoxChanged.connect( self._UpdateExample )
        
    
    def _AddParameter( self ):
        
        return self._EditParameter( '' )
        
    
    def _Copy( self ):
        
        full_template = self._GetFullTemplate()
        
        CG.client_controller.pub( 'clipboard', 'text', full_template )
        
    
    def _EditParameter( self, parameter: str ) -> str:
        
        message = 'Edit the parameter. This should just be one thing, typically separated by whitespace in a command. In a command like this:'
        message += '\n\n'
        message += 'my_program -o d a=virt profile="My Profile" path'
        message += '\n\n'
        message += 'The parameters would be "-o", "d", "a=virt", "profile="My Profile"", and "path" (or, likely for our purposes here, "%path%"). While you may need quotes within a parameter, you should not, generally speaking, wrap a whole parameter in quotes to avoid whitespace issues--that is handled for you, so do not worry about it; trying to add extra quotes may just break things.'
        message += '\n\n'
        message += 'You can mix a replacement token in amongst other text, or even have multiple tokens in the same parameter. "%parameter1%-%parameter2%" is fine. You cannot use the same token more than once per parameter, but you can use it in multiple parameters!'
        
        try:
            
            result = ClientGUIDialogsQuick.EnterText(
                self,
                message,
                default = parameter,
                placeholder = '-o',
                allow_blank = False,
                allow_whitespace = True,
                title = 'Enter parameter'
            )
            
            return result
            
        except HydrusExceptions.CancelledException:
            
            raise HydrusExceptions.VetoException()
            
        
    
    def _GetFullTemplate( self ):
        
        ( executable_path, executable_parameter_templates ) = self.GetValue()
        
        return executable_path + ' ' + ' '.join( executable_parameter_templates )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', str( e ) )
            
            return
            
        
        try:
            
            raw_text = raw_text.strip()
            
            items = raw_text.split( ' ' )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'A command like "my_progam -d -e -a %path%"', e )
            
            return
            
        
        if len( items ) == 0:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error!', 'Did not parse anything from the clipboard!' )
            
            return
            
        
        executable_path = items[0]
        executable_parameter_templates = items[1:]
        
        message = f'I took your paste and got a command "{executable_path}" and {HydrusNumbers.ToHumanInt(len(executable_parameter_templates))} parameters'
        
        if len( executable_parameter_templates ) > 0:
            
            message += ':'
            message += HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( executable_parameter_templates, do_sort = False, no_trailing_whitespace = True )
            
        else:
            
            message += '.'
            
        
        message += '\n\n'
        message += 'Look good?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._executable_path.setText( executable_path )
            self._executable_parameter_templates.SetData( executable_parameter_templates )
            
            self._UpdateExample()
            
        
    
    def _UpdateExample( self ):
        
        full_command = self._GetFullTemplate()
        
        self._example_full_command.setText( full_command )
        
    
    def UserIsOKToOK( self ):
        
        executable_path = self._executable_path.text()
        
        if executable_path == '':
            
            message = 'Hey, you really need to put an exe name/path in the path box. Are you sure you want to save this?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        if shutil.which( executable_path ) is None:
            
            message = f'Hey, I looked for the executable path "{executable_path}" but did not see it with a "which" call. You sure you are good?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    def GetValue( self ):
        
        executable_path = self._executable_path.text()
        executable_parameter_templates = self._executable_parameter_templates.GetData()
        
        return ( executable_path, executable_parameter_templates )
        
    

class EditProcessCallPanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._we_are_initialised = False
        self._pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE
        
        self._executable_path = ''
        self._executable_parameter_templates = []
        
        self._input_parameter_processing_rules_box = ClientGUICommon.StaticBox( self, 'input parameters' )
        
        self._parameter_types_to_input_parameter_processing_rule_panels: dict[ int, EditInputParameterProcessingRulePanel ] = {}
        
        self._example_command_template = QW.QLineEdit( self )
        self._example_command_template.setToolTip( ClientGUIFunctions.WrapToolTip( 'What will be executed.' ) )
        self._example_command_template.setReadOnly( True )
        
        self._edit_executable_command_and_parameters_button = ClientGUICommon.BetterButton( self, 'edit', self._EditCommandAndParameters )
        
        self._timeout = ClientGUITime.NoneableTimeDeltaWidget( self, 15, min = 1, days = False, hours = False, minutes = True, seconds = True, milliseconds = False, none_phrase = 'this can live for a very long time' )
        self._timeout.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the call takes longer than this, hydrus will stop waiting for any response, assume it is stuck, and try to terminate it. Be generous but not overly so.\n\nIf the call opens a program that you will be interacting with, like an external file viewer, set this to "this can live for a very long time", and hydrus will know to just spawn it and return immediately, without waiting for any response.' ) )
        
        self._hide_terminal = QW.QCheckBox( self )
        self._hide_terminal.setToolTip( ClientGUIFunctions.WrapToolTip( 'Check this unless you are debugging. Note: it will regularly be ignored by certain OS/call situations, so do not panic if unchecking it does not seem to change anything.' ) )
        
        self._text = QW.QCheckBox( self )
        self._text.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the command returns text, check this. If it returns raw bytes (e.g. it does a file conversion and dumps it to stdout), uncheck it.' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'This makes a general process call. Select which input parameter(s) you want to use and make sure you are happy with their replacement tokens (the \'%path%\' stuff, which you can rename if you need to), and then insert those parameters in your command template (e.g. \'my_program "%path%"\'). When this call fires, the given input parameters will be placed into your template and the process launched.'
        label += '\n\n'
        label += 'The "availability" test for this call just does a "which" on the executable path, which may not always target what you need.'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._input_parameter_processing_rules_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        command_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( command_hbox, self._example_command_template, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( command_hbox, self._edit_executable_command_and_parameters_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows.append( ( 'command template: ', command_hbox ) )
        rows.append( ( 'timeout: ', self._timeout ) )
        rows.append( ( 'hide terminal: ', self._hide_terminal ) )
        rows.append( ( 'output is text: ', self._text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._timeout.timeDeltaChanged.connect( self.valueChanged )
        self._hide_terminal.clicked.connect( self.valueChanged )
        self._text.clicked.connect( self.valueChanged )
        
    
    def _EditCommandAndParameters( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit command and parameters' ) as dlg:
            
            panel = EditProcessCallExecutableAndParametersPanel( dlg, self._executable_path, self._executable_parameter_templates )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( self._executable_path, self._executable_parameter_templates ) = panel.GetValue()
                
                self._UpdateExampleCommandTemplate()
                
                self.valueChanged.emit()
                
            
        
    
    def _GetCurrentInputParameterProcessingRules( self ) -> list[ ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule ]:
        
        input_parameter_processing_rules = []
        
        for panel in self._parameter_types_to_input_parameter_processing_rule_panels.values():
            
            value = panel.GetValue()
            
            if value is not None:
                
                input_parameter_processing_rules.append( value )
                
            
        
        return input_parameter_processing_rules
        
    
    def _UpdateExampleCommandTemplate( self ):
        
        self._example_command_template.setText( self._executable_path + ' ' + ' '.join( self._executable_parameter_templates ) )
        
    
    def CheckValid( self ):
        
        if self._executable_path == '':
            
            raise HydrusExceptions.VetoException( 'No executable path is set!' )
            
        
        input_parameter_processing_rules = self._GetCurrentInputParameterProcessingRules()
        
        if len( input_parameter_processing_rules ) == 0:
            
            raise HydrusExceptions.VetoException( 'No input parameters are being used! This is only appropriate if you just want to send a notification signal every time this event happens.' )
            
        
        for input_parameter_processing_rule in input_parameter_processing_rules:
            
            if True not in ( input_parameter_processing_rule.replacement_string in parameter for parameter in self._executable_parameter_templates ):
                
                raise HydrusExceptions.VetoException( f'The replacement string "{input_parameter_processing_rule.replacement_string}" for input parameter "{ClientExecutablePipelines.parameter_types_to_strs[ input_parameter_processing_rule.parameter_type ]}" is not in the command template!' )
                
            
        
    
    def GetValue( self ):
        
        input_parameter_processing_rules = self._GetCurrentInputParameterProcessingRules()
        
        actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
            executable_path = self._executable_path,
            executable_parameter_templates = self._executable_parameter_templates,
            input_parameter_processing_rules = input_parameter_processing_rules,
        )
        
        timeout = self._timeout.GetValue()
        
        if timeout is None:
            
            actual_call.SetTimeout( 15 )
            actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
            
        else:
            
            actual_call.SetTimeout( int( timeout ) )
            actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( False )
            
        
        actual_call.SetHideTerminal( self._hide_terminal.isChecked() )
        actual_call.SetText( self._text.isChecked() )
        
        return actual_call
        
    
    def SetPipelineType( self, pipeline_type: int ):
        
        if pipeline_type == self._pipeline_type and self._we_are_initialised:
            
            return
            
        
        self._pipeline_type = pipeline_type
        
        self._parameter_types_to_input_parameter_processing_rule_panels = {}
        
        self._input_parameter_processing_rules_box.Clear()
        
        for parameter_type in ClientExecutablePipelines.executable_pipeline_types_to_input_params[ self._pipeline_type ]:
            
            parameter_processing_rule = ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule( parameter_type )
            
            input_parameter_processing_rule_panel = EditInputParameterProcessingRulePanel( self._input_parameter_processing_rules_box, parameter_processing_rule )
            input_parameter_processing_rule_panel.valueChanged.connect( self.valueChanged )
            
            input_parameter_processing_rule_panel.SetValue( None )
            
            self._input_parameter_processing_rules_box.Add( input_parameter_processing_rule_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._parameter_types_to_input_parameter_processing_rule_panels[ parameter_type ] = input_parameter_processing_rule_panel
            
        
        self.valueChanged.emit()
        
        self._we_are_initialised = True
        
    
    def SetValue( self, actual_call: ClientExecutableActualCall.ExecutableLocalProcessCall, pipeline_type: int ):
        
        self.blockSignals( True )
        
        self.SetPipelineType( pipeline_type )
        
        self._executable_path = actual_call.GetExecutablePath()
        self._executable_parameter_templates = actual_call.GetExecutableParameterTemplates()
        
        input_parameter_processing_rules = actual_call.GetInputParameterProcessingRules()
        
        for input_parameter_processing_rule in input_parameter_processing_rules:
            
            if input_parameter_processing_rule.parameter_type in self._parameter_types_to_input_parameter_processing_rule_panels:
                
                self._parameter_types_to_input_parameter_processing_rule_panels[ input_parameter_processing_rule.parameter_type ].SetValue( input_parameter_processing_rule )
                
            
        
        self._UpdateExampleCommandTemplate()
        
        if actual_call.GetThisIsAPotentiallyLongLivedExternalGuy():
            
            self._timeout.SetValue( None )
            
        else:
            
            self._timeout.SetValue( actual_call.GetTimeout() )
            
        
        self._hide_terminal.setChecked( actual_call.GetHideTerminal() )
        self._text.setChecked( actual_call.GetText() )
        
        self.blockSignals( False )
        
        self.valueChanged.emit()
        
    

class EditClientExecutableActualCall( ClientGUICommon.StaticBox ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, actual_call: ClientExecutableActualCall.ExecutableActualCall, pipeline_type: int ):
        
        super().__init__( parent, 'external call' )
        
        self._pipeline_type = pipeline_type
        
        self._call_types_choice = ClientGUICommon.BetterChoice( self )
        
        self._call_types_choice.addItem( 'local process call', ClientExecutableActualCall.ExecutableLocalProcessCall )
        
        self._edit_actual_call_window = QW.QWidget( self )
        
        self._call_types_to_windows = {
            ClientExecutableActualCall.ExecutableLocalProcessCall : EditProcessCallPanel( self ),
            ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile : DefaultLaunchFileWidget( self ),
            ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL : DefaultLaunchURLWidget( self ),
        }
        
        #
        
        self.SetValue( actual_call, pipeline_type )
        
        #
        
        st = ClientGUICommon.BetterStaticText( self, label = 'Choose the type of call and then set it up. Availability tests are mostly for other users who might import your call. Do not forget to test it!' )
        st.setWordWrap( True )
        
        self.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._call_types_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for window in self._call_types_to_windows.values():
            
            self.Add( window, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            window.valueChanged.connect( self.valueChanged )
            
        
        self._call_types_choice.currentIndexChanged.connect( self._NotifyCallTypeChanged )
        
    
    def _NotifyCallTypeChanged( self ):
        
        self._UpdateCallTypePanel()
        
        self.valueChanged.emit()
        
    
    def _UpdateCallTypePanel( self ):
        
        call_type_to_show = self._call_types_choice.GetValue()
        
        if call_type_to_show is None:
            
            return
            
        
        for ( call_type, window ) in self._call_types_to_windows.items():
            
            window.blockSignals( True )
            
            window.SetPipelineType( self._pipeline_type )
            
            window.blockSignals( False )
            
            window.setVisible( call_type == call_type_to_show )
            
        
    
    def CheckValid( self ):
        
        call_type = self._call_types_choice.GetValue()
        
        self._call_types_to_windows[ call_type ].CheckValid()
        
    
    def GetValue( self ):
        
        call_type = self._call_types_choice.GetValue()
        
        return self._call_types_to_windows[ call_type ].GetValue()
        
    
    def SetPipelineType( self, pipeline_type: int ):
        
        self._pipeline_type = pipeline_type
        
        self._call_types_choice.blockSignals( True )
        
        self._call_types_choice.clear()
        
        labels_and_call_types: list[ tuple[ str, type ] ] = [
            ( 'local process call', ClientExecutableActualCall.ExecutableLocalProcessCall ),
        ]
        
        if self._pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE:
            
            labels_and_call_types.append(
                ( 'default OS launch file call', ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile )
            )
            
        elif self._pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL:
            
            labels_and_call_types.append(
                ( 'default OS launch URL call', ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL )
            )
            
        
        for ( label, call_type ) in labels_and_call_types:
            
            self._call_types_choice.addItem( label, call_type )
            
        
        self._call_types_choice.blockSignals( False )
        
        self._UpdateCallTypePanel()
        
        self.valueChanged.emit()
        
    
    def SetValue( self, actual_call: ClientExecutableActualCall.ExecutableActualCall, pipeline_type: int ):
        
        self.blockSignals( True )
        
        self.SetPipelineType( pipeline_type )
        
        call_type = type( actual_call )
        
        if call_type not in self._call_types_to_windows:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'unknown call type!', 'Sorry, the given call for this executable is unknown to this client! It cannot show edit UI for it. Cancel out of this dialog mate.' )
            
            return
            
        
        self._call_types_choice.SetValue( call_type )
        
        self._UpdateCallTypePanel()
        
        self._call_types_to_windows[ call_type ].SetValue( actual_call, pipeline_type )
        
        self.blockSignals( False )
        
        self.valueChanged.emit()
        
    

class EditInputParameterTestValuePanel( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, parameter_type: int ):
        
        self._parameter_type = parameter_type
        
        super().__init__( parent )
        
        if self._parameter_type not in PARAM_TYPES_TO_LAST_SEEN_VALUES:
            
            # TODO: Update this to handle multiple items nicely and ditch the [0]
            PARAM_TYPES_TO_LAST_SEEN_VALUES[ self._parameter_type ] = ClientExecutablePipelines.parameter_types_to_example_values[ parameter_type ][0]
            
        
        self._name = ClientGUICommon.BetterStaticText( self, label = ClientExecutablePipelines.parameter_types_to_strs[ self._parameter_type ] )
        self._test_value = QW.QLineEdit( self, text = PARAM_TYPES_TO_LAST_SEEN_VALUES[ self._parameter_type ] )
        
        #
        
        # to effect a pseudo-table style, we'll force widths
        
        self._name.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._name, 12 ) )
        self._test_value.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._test_value, 44 ) )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._name, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._test_value, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self.setLayout( hbox )
        
        self._test_value.textChanged.connect( self.valueChanged )
        
    
    def _GetTestData( self ) -> ClientParsing.ParsingTestData:
        
        texts = ClientExecutablePipelines.parameter_types_to_example_values[ self._parameter_type ]
        
        return ClientParsing.ParsingTestData( {}, texts = texts )
        
    
    def GetValue( self ) -> str:
        
        value = self._test_value.text()
        
        PARAM_TYPES_TO_LAST_SEEN_VALUES[ self._parameter_type ] = value
        
        return value
        
    

PARAM_TYPES_TO_LAST_SEEN_VALUES = {}

class TestCallablePanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, 'testing' )
        
        self._actual_call: ClientExecutableActualCall.ExecutableActualCall = ClientExecutableActualCall.ExecutableLocalProcessCall()
        
        self._test_availability_button = ClientGUICommon.BetterButton( self, 'test availability!', self._TestAvailability )
        
        self._input_param_types_to_edit_panels = {}
        
        self._input_param_types_box = ClientGUICommon.StaticBox( self, 'test input parameters' )
        
        self._actual_command_preview = QW.QLineEdit( self )
        self._actual_command_preview.setReadOnly( True )
        
        self._test_call_button = ClientGUICommon.BetterButton( self, 'test call!', self._TestCall )
        
        # could make this a notebook in future, with the parsed output params as the first window and 'raw' response tucked away for debugging
        self._raw_output_text_box = QW.QPlainTextEdit( self )
        self._raw_output_text_box.setReadOnly( True )
        self._raw_output_text_box.setFont( QG.QFont( 'Monospace' ) )
        
        #
        
        self._currently_running_availability_test = False
        
        st = ClientGUICommon.BetterStaticText( self, label = 'Test your call here. Put in a real path or URL in the provided input parameter box and click "test call!". It will fire for real, so don\'t screw around!\n\nRemember that if your application is inside a sandbox, for instance you installed it via flatpak, it needs to be able to see any paths you give it. Same deal for hydrus seeing an exe.' )
        st.setWordWrap( True )
        
        self.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._test_availability_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._input_param_types_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._actual_command_preview, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._test_call_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._raw_output_text_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _GetInputParams( self ) -> dict[ int, str ]:
        
        return { param_type : input_param_edit_panel.GetValue() for ( param_type, input_param_edit_panel ) in self._input_param_types_to_edit_panels.items() }
        
    
    def _RecreateTestInputPanels( self ):
        
        self._input_param_types_to_edit_panels = {}
        self._input_param_types_box.Clear()
        
        # don't do a sort here; the one we inherit is actually good
        required_input_parameter_types = self._actual_call.GetInputParametersUsed()
        
        for required_input_parameter_type in required_input_parameter_types:
            
            panel = EditInputParameterTestValuePanel( self, required_input_parameter_type )
            
            panel.valueChanged.connect( self._UpdatePreview )
            
            self._input_param_types_to_edit_panels[ required_input_parameter_type ] = panel
            
            self._input_param_types_box.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
    
    def _TestAvailability( self ):
        
        def work_callable():
            
            result = actual_call.TestAvailability()
            
            return result
            
        
        def publish_callable( result ):
            
            if result:
                
                message = 'Availability test worked!'
                
            else:
                
                message = 'Availability test failed!'
                
            
            self._raw_output_text_box.setPlainText( message )
            
        
        def errback_callable( etype, value, tb ):
            
            self._raw_output_text_box.setPlainText( HydrusData.ConvertExceptionTupleToSummary( etype, value, tb ) )
            
        
        def ui_restoration_callable():
            
            self._currently_running_availability_test = False
            
            self._UpdateAvailabilityTestButton()
            
        
        message = f'Testing{HC.UNICODE_ELLIPSIS}'
        
        actual_call = self._actual_call
        
        self._raw_output_text_box.setPlainText( message )
        
        self._currently_running_availability_test = True
        
        self._UpdateAvailabilityTestButton()
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable, ui_restoration_callable = ui_restoration_callable )
        
        job.start()
        
    
    def _TestCall( self ):
        
        def work_callable():
            
            # we might have a special call that returns test data or populates a TestStatus object as it works, and then we can spool stdout/stderr or http response or whatever here
            output_params = actual_call.CallTest( input_params )
            
            return output_params
            
        
        def publish_callable( output_params ):
            
            message = 'Looks good!'
            
            self._raw_output_text_box.setPlainText( message )
            
        
        def errback_callable( etype, value, tb ):
            
            self._raw_output_text_box.setPlainText( HydrusData.ConvertExceptionTupleToSummary( etype, value, tb ) )
            
        
        def ui_restoration_callable():
            
            self._test_call_button.setEnabled( True )
            
        
        message = f'Testing{HC.UNICODE_ELLIPSIS}'
        
        input_params = self._GetInputParams()
        actual_call = self._actual_call
        
        if isinstance( actual_call, ClientExecutableActualCall.ExecutableLocalProcessCall ) and actual_call.GetThisIsAPotentiallyLongLivedExternalGuy():
            
            message += ' (forcing a 15 second timeout for testing purposes)'
            
        
        self._raw_output_text_box.setPlainText( message )
        
        self._test_call_button.setEnabled( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable, ui_restoration_callable = ui_restoration_callable )
        
        job.start()
        
    
    def _UpdateAvailabilityTestButton( self ):
        
        self._test_availability_button.setEnabled( self._actual_call.CanTestAvailability() and not self._currently_running_availability_test )
        
    
    def _UpdatePreview( self ):
        
        input_params = self._GetInputParams()
        
        self._actual_command_preview.setText( self._actual_call.GetCommandPreviewWithInputParams( input_params ) )
        
        self._raw_output_text_box.setPlainText( '' )
        
    
    def SetActualCall( self, actual_call: ClientExecutableActualCall.ExecutableActualCall ):
        
        self._actual_call = actual_call
        
        required_input_parameter_types = self._actual_call.GetInputParametersUsed()
        
        if set( required_input_parameter_types ) != set( self._input_param_types_to_edit_panels.keys() ):
            
            self._RecreateTestInputPanels()
            
        
        self._UpdateAvailabilityTestButton()
        self._UpdatePreview()
        
    

class EditClientExecutableCallablePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, call: ClientExecutableCallables.ClientExecutableCallable ):
        
        super().__init__( parent )
        
        self._pipeline_panel = ClientGUICommon.StaticBox( self, 'pipeline' )
        
        self._name = QW.QLineEdit( self._pipeline_panel )
        self._pipeline_type = ClientGUICommon.BetterChoice( self._pipeline_panel )
        
        for pipeline_type in [
            ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
            ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        ]:
            
            self._pipeline_type.addItem( ClientExecutablePipelines.executable_pipeline_types_to_strs[ pipeline_type ], pipeline_type )
            
        
        self._pipeline_description = ClientGUICommon.BetterStaticText( self._pipeline_panel )
        self._pipeline_description.setWordWrap( True )
        
        self._actual_call_panel = EditClientExecutableActualCall( self, call.GetCall(), call.GetPipelineType() )
        
        self._validity_text = ClientGUICommon.BetterStaticText( self )
        self._validity_text.setWordWrap( True )
        self._validity_text.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._test_panel = TestCallablePanel( self )
        
        #
        
        self.SetValue( call )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'job: ', self._pipeline_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        st = ClientGUICommon.BetterStaticText( self._pipeline_panel, label = 'Set a name for this external call and select the job it will do.' )
        st.setWordWrap( True )
        
        self._pipeline_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pipeline_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pipeline_panel.Add( self._pipeline_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._pipeline_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._actual_call_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._validity_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( hbox )
        
        #
        
        self._pipeline_type.currentIndexChanged.connect( self._UpdatePipelineType )
        self._actual_call_panel.valueChanged.connect( self._UpdateValidity )
        self._actual_call_panel.valueChanged.connect( self._UpdateTestPanel )
        
    
    def _GetValiditySummary( self ):
        
        try:
            
            self._actual_call_panel.CheckValid()
            
        except Exception as e:
            
            return ( False, str( e ) )
            
        
        return ( True, 'Everything looks good!' )
        
    
    def _IsValid( self ):
        
        return self._GetValiditySummary()[0]
        
    
    def _UpdatePipelineType( self ):
        
        pipeline_type = self._pipeline_type.GetValue()
        
        pipeline_type_desc = 'Summary: ' + ClientExecutablePipelines.executable_pipeline_types_to_desc_strs[ pipeline_type ]
        pipeline_type_desc += '\n\n'
        
        input_parameter_types = ClientExecutablePipelines.executable_pipeline_types_to_input_params[ pipeline_type ]
        
        if len( input_parameter_types ) == 0:
            
            pipeline_type_desc += 'Available input parameters: none'
            
        else:
            
            pipeline_type_desc += 'Available input parameters: ' + ', '.join( ( ClientExecutablePipelines.parameter_types_to_strs[ parameter_type ] for parameter_type in input_parameter_types ) )
            
        
        pipeline_type_desc += '\n\n'
        
        output_parameter_types = ClientExecutablePipelines.executable_pipeline_types_to_output_params[ pipeline_type ]
        
        if len( output_parameter_types ) == 0:
            
            pipeline_type_desc += 'Expected output parameters: none'
            
        else:
            
            pipeline_type_desc += 'Expected output parameters: ' + ', '.join( ( ClientExecutablePipelines.parameter_types_to_strs[ parameter_type ] for parameter_type in output_parameter_types ) )
            
        
        self._pipeline_description.setText( pipeline_type_desc )
        
        self._actual_call_panel.SetPipelineType( pipeline_type )
        
        self._UpdateValidity()
        
    
    def _UpdateTestPanel( self ):
        
        actual_call = self._actual_call_panel.GetValue()
        
        self._test_panel.SetActualCall( actual_call )
        
    
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
        actual_call = self._actual_call_panel.GetValue()
        
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
        
        self._actual_call_panel.SetValue( call.GetCall(), call.GetPipelineType() )
        
        self._UpdateValidity()
        self._UpdateTestPanel()
        
    

class ExternalProgramsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._executable_manager: ClientExecutableManager.ExecutableManager = ClientExecutableManager.ExecutableManager()
        
        message = 'THIS SYSTEM IS STILL IN TESTING! ONLY ADVANCED USERS SEE THIS, AND IT IS NOT PLUGGED INTO ANYTHING YET.'
        message += '\n\n'
        message += 'Please test this and let me know how it goes. It will load up the defaults for your system. Pick a call that you should have, and then edit it and put in a sensible file path or URL in the test panel and try it! Let me know if you have any errors or if any of the help text is confusing!'
        message += '\n\n----------\n\n'
        message += 'Here we can teach your client about other programs it can call. Each job has a certain type, such as "open file in external program" or "download URL" or "suggest tags". Depending on the job type, it will have certain call parameters (e.g. a local media file path) that hydrus can pass on to the external program (e.g. a tag profiler). In future, there will also be response parameters (e.g. a list of tags) that hydrus will then ingest.'
        
        st = ClientGUICommon.BetterStaticText( self, message )
        st.setWordWrap( True )
        
        external_calls_panel = ClientGUICommon.StaticBox( self, 'external calls' )
        
        warning_message = 'IF YOU IMPORT A CALL HERE THAT SOMEONE ELSE MADE, MAKE SURE YOU INSPECT IT BEFORE HOOKING IT UP TO ANYTHING.'
        warning_message += '\n\n'
        warning_message += 'USE YOUR BRAIN. DO NOT CALL THINGS BLINDLY.'
        
        warning = ClientGUICommon.BetterStaticText( external_calls_panel, warning_message )
        warning.setWordWrap( True )
        warning.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        warning.setObjectName( 'HydrusWarning' )
        
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
        
        external_calls_panel.Add( warning, CC.FLAGS_EXPAND_PERPENDICULAR )
        external_calls_panel.Add( external_calls_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, external_calls_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self.setLayout( vbox )
        
        def add_defaults():
            
            external_platforms_and_callables = list( ClientExecutableDefaults.GetDefaultOpenExternally() )
            external_platforms_and_callables.extend( ClientExecutableDefaults.GetDefaultOpenURL() )
            
            external_callables = [ call for ( my_platform, call ) in external_platforms_and_callables if my_platform ]
            
            for external_call in external_callables:
                
                self._AddCallableFullyFormed( external_call )
                
            
            self._external_calls.Sort()
            
        
        CG.client_controller.CallAfterQtSafe( self, add_defaults )
        
    
    def _AddCallableBrandNew( self ):
        
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
        
        message = f'Want to see the calls just for your platform ({HC.NICE_PLATFORM_STRING}) or everything?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'just for my platform', no_label = 'no, show me everything' )
        
        filter_by_platform = result == QW.QDialog.DialogCode.Accepted
        
        external_platforms_and_callables = list( ClientExecutableDefaults.GetDefaultOpenExternally() )
        external_platforms_and_callables.extend( ClientExecutableDefaults.GetDefaultOpenURL() )
        
        if filter_by_platform:
            
            external_callables = [ call for ( my_platform, call ) in external_platforms_and_callables if my_platform ]
            
        else:
            
            external_callables = [ call for ( my_platform, call ) in external_platforms_and_callables ]
            
        
        return external_callables
        
    
    def _GetExistingNames( self ) -> set[ str ]:
        
        calls = self._external_calls.GetData()
        
        names = { call.GetName() for call in calls }
        
        return names
        
    
    def UpdateOptions( self ):
        
        # TODO: save this guy on an ok. should it be a manager as held by the controller, or just an options entry? think about it
        # leaning towards its own thing, but w/e
        pass
        
    
