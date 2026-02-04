import json

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUINumberTest
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.search import ClientNumberTest

# TODO: maybe break this into ClientGUITimeWidgets for gui.widgets and then shoot EditCheckerOptions off to something appropriate

def QDateTimeToPrettyString( dt: QC.QDateTime | None, include_milliseconds = False ):
    
    if dt is None:
        
        return 'unknown time'
        
    else:
        
        if include_milliseconds:
            
            phrase = 'yyyy-MM-dd hh:mm:ss.zzz'
            
        else:
            
            phrase = 'yyyy-MM-dd hh:mm:ss'
            
        
        return f'{dt.toString( phrase )} ({HydrusTime.TimestampToPrettyTimeDelta( dt.toSecsSinceEpoch(), force_no_iso = True )})'
        
    

class EditCheckerOptions( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, checker_options ):
        
        super().__init__( parent )
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding these checker options.' ) )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        from hydrus.client import ClientDefaults
        
        defaults_panel = ClientGUICommon.StaticBox( self, 'reasonable defaults' )
        
        defaults_1 = ClientGUICommon.BetterButton( defaults_panel, 'thread', self.SetValue, ClientDefaults.GetDefaultCheckerOptions( 'thread' ) )
        defaults_2 = ClientGUICommon.BetterButton( defaults_panel, 'slow thread', self.SetValue, ClientDefaults.GetDefaultCheckerOptions( 'slow thread' ) )
        defaults_3 = ClientGUICommon.BetterButton( defaults_panel, 'faster tag subscription', self.SetValue, ClientDefaults.GetDefaultCheckerOptions( 'fast tag subscription' ) )
        defaults_4 = ClientGUICommon.BetterButton( defaults_panel, 'medium tag/artist subscription', self.SetValue, ClientDefaults.GetDefaultCheckerOptions( 'artist subscription' ) )
        defaults_5 = ClientGUICommon.BetterButton( defaults_panel, 'slower tag subscription', self.SetValue, ClientDefaults.GetDefaultCheckerOptions( 'slow tag subscription' ) )
        
        #
        
        # add statictext or whatever that will update on any updates above to say 'given velocity of blah and last check at blah, next check in 5 mins'
        # or indeed this could just take the file_seed cache and last check of the caller, if there is one
        # this would be more useful to the user, to know 'right, on ok, it'll refresh in 30 mins'
        # this is actually more complicated--it also needs last check time to calc a fresh file velocity based on new death_file_velocity
        
        #
        
        min_unit_value = 0
        max_unit_value = 1000
        min_time_delta = 60
        
        self._death_file_velocity = VelocityCtrl( self, min_unit_value, max_unit_value, min_time_delta, days = True, hours = True, minutes = True, per_phrase = 'in', unit = 'files' )
        
        self._flat_check_period_checkbox = QW.QCheckBox( self )
        
        #
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            never_faster_than_min = 1
            never_slower_than_min = 1
            
            flat_check_period_min = 1
            
        else:
            
            never_faster_than_min = 30
            never_slower_than_min = 600
            
            flat_check_period_min = 180
            
        
        self._reactive_check_panel = ClientGUICommon.StaticBox( self, 'reactive checking' )
        
        self._intended_files_per_check = QW.QDoubleSpinBox( self._reactive_check_panel )
        self._intended_files_per_check.setDecimals( 2 )
        self._intended_files_per_check.setSingleStep( 0.05 )
        self._intended_files_per_check.setMinimum( 0.25 )
        self._intended_files_per_check.setMaximum( 1000.0 )
        self._intended_files_per_check.setToolTip( ClientGUIFunctions.WrapToolTip( 'How many new files you want the checker to find on each check. If a source is producing about 2 files a day, and this is set to 6, you will probably get a check every three days. You probably want this to be a low number, like 1-4.' ) )
        
        self._never_faster_than = TimeDeltaWidget( self._reactive_check_panel, min = never_faster_than_min, days = True, hours = True, minutes = True, seconds = True )
        self._never_faster_than.setToolTip( ClientGUIFunctions.WrapToolTip( 'Even if the download source produces many new files, the checker will never ask for a check more often than this. This is a safety measure.' ) )
        
        self._never_slower_than = TimeDeltaWidget( self._reactive_check_panel, min = never_slower_than_min, days = True, hours = True, minutes = True, seconds = True )
        self._never_slower_than.setToolTip( ClientGUIFunctions.WrapToolTip( 'Even if the download source slows down significantly, the checker will make sure it checks at least this often anyway, just to catch a future wave in time.' ) )
        
        #
        
        self._static_check_panel = ClientGUICommon.StaticBox( self, 'static checking' )
        
        self._flat_check_period = TimeDeltaWidget( self._static_check_panel, min = flat_check_period_min, days = True, hours = True, minutes = True, seconds = True )
        self._flat_check_period.setToolTip( ClientGUIFunctions.WrapToolTip( 'Always use the same check delay. It is based on the time the last check completed, not the time the last check was due. If you want once a day with no skips, try setting this to 23 hours.' ) )
        
        #
        
        self.SetValue( checker_options )
        
        #
        
        defaults_panel.Add( defaults_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        defaults_panel.Add( defaults_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        defaults_panel.Add( defaults_3, CC.FLAGS_EXPAND_PERPENDICULAR )
        defaults_panel.Add( defaults_4, CC.FLAGS_EXPAND_PERPENDICULAR )
        defaults_panel.Add( defaults_5, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        #
        
        label = 'This checks more or less frequently based on how fast the download source is producing new files.'
        
        st = ClientGUICommon.BetterStaticText( self._reactive_check_panel, label = label )
        
        st.setWordWrap( True )
        
        rows = []
        
        rows.append( ( 'intended new files per check: ', self._intended_files_per_check ) )
        rows.append( ( 'never check faster than once per: ', self._never_faster_than ) )
        rows.append( ( 'never check slower than once per: ', self._never_slower_than ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._reactive_check_panel, rows )
        
        self._reactive_check_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._reactive_check_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'check period: ', self._flat_check_period ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._static_check_panel, rows )
        
        self._static_check_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'stop checking if new files found falls below: ', self._death_file_velocity ) )
        rows.append( ( 'just check at a static, regular interval: ', self._flat_check_period_checkbox ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        label = 'If you do not understand this panel, use the buttons! The defaults are fine for most purposes!'
        
        st = ClientGUICommon.BetterStaticText( self._reactive_check_panel, label = label )
        
        st.setWordWrap( True )
        st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, defaults_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            label = 'As you are in advanced mode, these options have extremely low limits. This is intended only for testing and small scale private network tasks. Do not use very fast check times for real world use on public websites, as it is wasteful and rude, hydrus will be overloaded with high-CPU parsing work, and you may get your IP banned.'
            
            st = ClientGUICommon.BetterStaticText( self, label = label )
            st.setObjectName( 'HydrusWarning' )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._reactive_check_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._static_check_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._flat_check_period_checkbox.clicked.connect( self.EventFlatPeriodCheck )
        
        self._never_faster_than.timeDeltaChanged.connect( self._UpdateTimeDeltas )
        self._never_slower_than.timeDeltaChanged.connect( self._UpdateTimeDeltas )
        
    
    def _ShowHelp( self ):
        
        help_text = 'The intention of this object is to govern how frequently the watcher or subscription checks for new files--and when it should stop completely.'
        help_text += '\n' * 2
        help_text += 'PROTIP: Do not change anything here unless you understand what it means!'
        help_text += '\n' * 2
        help_text += 'In general, checkers can and should be set up to check faster or slower based on how fast new files are coming in. This is polite to the server you are talking to and saves you CPU and bandwidth. The rate of new files is called the \'file velocity\' and is based on how many files appeared in a certain period before the _most recent check time_.'
        help_text += '\n' * 2
        help_text += 'Once the first check is done and an initial file velocity is established, the time to the next check will be based on what you set for the \'intended files per check\'. If the current file velocity is 10 files per 24 hours, and you set the intended files per check to 5 files, the checker will set the next check time to be 12 hours after the previous check time.'
        help_text += '\n' * 2
        help_text += 'After a check is completed, the new file velocity and next check time is calculated, so when files are being posted frequently, it will check more often. When things are slow, it will slow down as well. There are also minimum and maximum check periods to smooth out the bumps.'
        help_text += '\n' * 2
        help_text += 'But if you would rather just check at a fixed rate, check the checkbox and you will get a simpler \'static checking\' panel.'
        help_text += '\n' * 2
        help_text += 'If the \'file velocity\' drops below a certain amount, the checker considers the source of files dead and will stop checking. If it falls into this state but you think there might have since been a rush of new files, hit the watcher or subscription\'s \'check now\' button in an attempt to revive the checker. If there are new files, it will start checking again until they drop off once more.'
        help_text += '\n' * 2
        help_text += 'If you are still not comfortable with how this system works, the \'reasonable defaults\' are good fallbacks. Most of the time, setting some reasonable rules and leaving checkers to do their work is the best way to deal with this stuff, rather than obsessing over the exact perfect values you want for each situation.'
        
        ClientGUIDialogsMessage.ShowInformation( self, help_text )
        
    
    def _UpdateEnabledControls( self ):
        
        if self._flat_check_period_checkbox.isChecked():
            
            self._reactive_check_panel.hide()
            self._static_check_panel.show()
            
        else:
            
            self._reactive_check_panel.show()
            self._static_check_panel.hide()
        
        self._UpdateTimeDeltas()
        
    
    def _UpdateTimeDeltas( self ):
        
        if not self._flat_check_period_checkbox.isChecked():
            
            never_faster_than = self._never_faster_than.GetValue()
            never_slower_than = self._never_slower_than.GetValue()
            
            if never_slower_than < never_faster_than:
                
                self._never_slower_than.SetValue( never_faster_than )
                
            
        
    
    def UserIsOKToOK( self ):
        
        if not self._flat_check_period_checkbox.isChecked():
            
            if self._never_faster_than.GetValue() == self._never_slower_than.GetValue():
                
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                message = 'The "never check faster/slower than" values are the same, which means this checker will always check at a static, regular interval. Is that OK?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return False
                    
                
            
        
        return True
        
    
    def EventFlatPeriodCheck( self ):
        
        self._UpdateEnabledControls()
        
    
    def GetValue( self ):
        
        death_file_velocity = self._death_file_velocity.GetValue()
        
        intended_files_per_check = self._intended_files_per_check.value()
        
        if self._flat_check_period_checkbox.isChecked():
            
            never_faster_than = self._flat_check_period.GetValue()
            never_slower_than = never_faster_than
            
        else:
            
            never_faster_than = self._never_faster_than.GetValue()
            never_slower_than = self._never_slower_than.GetValue()
            
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check, never_faster_than, never_slower_than, death_file_velocity )
        
    
    def SetValue( self, checker_options ):
        
        ( intended_files_per_check, never_faster_than, never_slower_than, death_file_velocity ) = checker_options.ToTuple()
        
        self._intended_files_per_check.setValue( intended_files_per_check )
        self._never_faster_than.SetValue( never_faster_than )
        self._never_slower_than.SetValue( never_slower_than )
        self._death_file_velocity.SetValue( death_file_velocity )
        
        self._flat_check_period.SetValue( never_faster_than )
        
        self._flat_check_period_checkbox.setChecked( never_faster_than == never_slower_than )
        
        self._UpdateEnabledControls()
        
    

class DateTimeWidgetValueRange( object ):
    """
    This guy holds a fixed datetime or a min-max range for n files. It also knows how many files don't have a time set.
    """
    
    def __init__( self ):
        
        self._min_value = None
        self._max_value = None
        self._set_count = 0
        self._null_count = 0
        
        self._step_ms = 0
        
    
    def __eq__( self, other ):
        
        if isinstance( other, DateTimeWidgetValueRange ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._GetCmpTuple().__hash__()
        
    
    def __lt__( self, other ):
        
        if isinstance( other, DateTimeWidgetValueRange ):
            
            return self._GetCmpTuple() < other._GetCmpTuple()
            
        
        return NotImplemented
        
    
    def _GetCmpTuple( self ):
        
        if self._set_count > 0:
            
            min_value = self._min_value.toMSecsSinceEpoch()
            max_value = self._max_value.toMSecsSinceEpoch()
            
        else:
            
            min_value = 0
            max_value = 0
            
        
        return ( min_value, max_value, self._set_count, self._null_count, self._step_ms )
        
    
    def AddValueTimestampMS( self, timestamp_ms: int | None, num_to_add = 1 ):
        
        qt_datetime = None if timestamp_ms is None else QC.QDateTime.fromMSecsSinceEpoch( timestamp_ms, QC.QTimeZone.systemTimeZone() )
        
        self.AddValueQtDateTime( qt_datetime, num_to_add = num_to_add )
        
    
    def AddValueQtDateTime( self, qt_datetime: QC.QDateTime | None, num_to_add = 1 ):
        
        if num_to_add == 0:
            
            return
            
        
        if qt_datetime is None:
            
            self._null_count += num_to_add
            
        else:
            
            self._set_count += num_to_add
            
            if self._min_value is None:
                
                self._min_value = qt_datetime
                self._max_value = qt_datetime
                
            else:
                
                if qt_datetime < self._min_value:
                    
                    self._min_value = qt_datetime
                    
                elif self._max_value < qt_datetime:
                    
                    self._max_value = qt_datetime
                    
                
            
        
    
    def DuplicateWithNewQtDateTime( self, value: QC.QDateTime | None, overwrite_nulls = False ) -> "DateTimeWidgetValueRange":
        
        datetime_value_range = DateTimeWidgetValueRange()
        
        if self._set_count > 0:
            
            datetime_value_range.AddValueQtDateTime( value, num_to_add = self._set_count )
            
        
        if self._null_count > 0:
            
            if overwrite_nulls:
                
                value_to_send = value
                
            else:
                
                value_to_send = None
                
            
            datetime_value_range.AddValueQtDateTime( value_to_send, num_to_add = self._null_count )
            
        
        datetime_value_range.SetStepMS( self._step_ms )
        
        return datetime_value_range
        
    
    def DuplicateWithNewTimestampMS( self, timestamp_ms: int | None, overwrite_nulls = False ) -> "DateTimeWidgetValueRange":
        
        qt_datetime = None if timestamp_ms is None else QC.QDateTime.fromMSecsSinceEpoch( timestamp_ms, QC.QTimeZone.systemTimeZone() )
        
        return self.DuplicateWithNewQtDateTime( qt_datetime, overwrite_nulls = overwrite_nulls )
        
    
    def DuplicateWithOverwrittenNulls( self ) -> "DateTimeWidgetValueRange":
        
        return self.DuplicateWithNewQtDateTime( self.GetBestVisualValue(), overwrite_nulls = True )
        
    
    def GetBestVisualValue( self ) -> QC.QDateTime | None:
        
        if self._set_count > 0:
            
            return self._min_value
            
        else:
            
            return None
            
        
    
    def GetFixedValue( self ) -> QC.QDateTime:
        
        if not self.HasFixedValue():
            
            raise HydrusExceptions.VetoException( 'Sorry, this time value is not fixed! You should not see this, so please let hydev know what happened here.' )
            
        
        return self._min_value
        
    
    def GetNullCount( self ) -> int:
        
        return self._null_count
        
    
    def GetSetCount( self ) -> int:
        
        return self._set_count
        
    
    def GetStepMS( self ) -> int:
        
        return self._step_ms
        
    
    def HasFixedValue( self ):
        
        return self._min_value is not None and self._min_value == self._max_value
        
    
    def IsAllNull( self ):
        
        return self._set_count == 0
        
    
    def IsMultipleFiles( self ):
        
        return self._set_count > 1
        
    
    def SetStepMS( self, value_ms ):
        
        self._step_ms = value_ms
        
    
    def ToString( self ):
        
        total_num_files = self._set_count + self._null_count
        
        if total_num_files == 0:
            
            return 'no time set'
            
        
        s = ''
        
        if self._set_count == 1:
            
            if self._null_count > 1:
                
                s += '1 file set to '
                
            
            s += QDateTimeToPrettyString( self._min_value, include_milliseconds = True )
            
        elif self._set_count > 1:
            
            s += f'{HydrusNumbers.ToHumanInt( self._set_count )} files set'
            
            if self._min_value == self._max_value:
                
                s += f' to {QDateTimeToPrettyString( self._min_value, include_milliseconds = True )}'
                
            else:
                
                s += f' from {QDateTimeToPrettyString( self._min_value, include_milliseconds = True )} to {QDateTimeToPrettyString( self._max_value, include_milliseconds = True )}'
                
            
        
        if self._null_count > 0:
            
            if self._null_count == 1:
                
                none_prefix = '1 file'
                
            else:
                
                none_prefix = f'{HydrusNumbers.ToHumanInt(self._null_count)} files'
                
            
            if s != '':
                
                s += ', '
                
            
            s += f'{none_prefix} without a time set'
            
        
        if self._step_ms != 0:
            
            s += f', with step {HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusTime.SecondiseMSFloat( self._step_ms ) )}'
            
        
        return s
        
    

class DateTimesButton( ClientGUICommon.BetterButton ):
    
    dateTimeChanged = QC.Signal()
    
    def __init__( self, parent, time_allowed = True, milliseconds_allowed = False, none_allowed = False, only_past_dates = False ):
        
        super().__init__( parent, 'initialising', self._EditDateTime )
        
        self._time_allowed = time_allowed
        self._milliseconds_allowed = milliseconds_allowed
        self._none_allowed = none_allowed
        self._only_past_dates = only_past_dates
        
        self._datetime_value_range = DateTimeWidgetValueRange()
        
        self._datetime_value_range.AddValueQtDateTime( QC.QDateTime.currentDateTime() )
        
        self._has_user_changes = False
        
        # XXXX-XX-XX XX:XX:XX = 19 chars, so add a bit of padding
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 23 )
        
        self.setMinimumWidth( min_width )
        
        self._UpdateLabel()
        
    
    def _EditDateTime( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit datetime' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = DateTimesCtrl( self, time_allowed = self._time_allowed, milliseconds_allowed = self._milliseconds_allowed, none_allowed = self._none_allowed, only_past_dates = self._only_past_dates )
            
            control.SetValue( self._datetime_value_range )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                datetime_value_range = control.GetValue()
                
                self.SetValue( datetime_value_range, from_user = True )
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._datetime_value_range.ToString()
        
        self.setText( label )
        
    
    def GetValue( self ):
        
        return self._datetime_value_range
        
    
    def HasChanges( self ):
        
        return self._has_user_changes
        
    
    def SetValue( self, datetime_value_range: DateTimeWidgetValueRange, from_user = False ):
        
        if datetime_value_range.IsAllNull() and not self._none_allowed:
            
            return
            
        
        if self._datetime_value_range != datetime_value_range:
            
            self._datetime_value_range = datetime_value_range
            
            self._UpdateLabel()
            
            self._has_user_changes = from_user
            
            self.dateTimeChanged.emit()
            
        
    

class DateTimesCtrl( QW.QWidget ):
    
    dateTimeChanged = QC.Signal()
    
    def __init__( self, parent, time_allowed = True, seconds_allowed = False, milliseconds_allowed = False, none_allowed = False, only_past_dates = False ):
        
        super().__init__( parent )
        
        self._time_allowed = time_allowed
        self._seconds_allowed = seconds_allowed
        self._milliseconds_allowed = milliseconds_allowed
        self._none_allowed = none_allowed
        self._only_past_dates = only_past_dates
        
        datetime_value_range = DateTimeWidgetValueRange()
        
        datetime_value_range.AddValueQtDateTime( QC.QDateTime.currentDateTime() )
        
        self._original_datetime_value_range = datetime_value_range
        self._current_datetime_value_range = self._original_datetime_value_range
        
        self._we_have_initialised_with_setvalue = False
        
        self._none_time = QW.QCheckBox( self )
        
        self._date = QW.QCalendarWidget( self )
        
        self._time = QW.QTimeEdit( self )
        
        self._step_box = ClientGUICommon.StaticBox( self, 'Cascading Step' )
        
        self._step = TimeDeltaWidget( self._step_box, min = -86399, days = False, hours = True, minutes = True, seconds = True, milliseconds = True, negative_allowed = True )
        tt = 'You can set here that each successive file (in the order of the selection that launched this dialog) be set a little later than the last, forcing a particular sort according to that time type.'
        tt += '\n' * 2
        tt += 'For instance, if you have a manga chapter in order in a search page, but their import times are scattered, set this to 5 milliseconds and their import times will be set to cascade nicely.'
        tt += '\n' * 2
        tt += 'Negative values are allowed!'
        self._step.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._copy_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy timestamp to the clipboard.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste a timestamp. Needs to be a simple string but can handle pretty much anything.' ) )
        
        self._now_button = ClientGUICommon.BetterButton( self, 'now', self._SetNow )
        self._now_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set the time to now.' ) )
        
        #
        
        qt_now = QC.QDateTime.currentDateTime()
        
        self._date.setSelectedDate( qt_now.date() )
        self._time.setTime( qt_now.time() )
        self._step.SetValue( HydrusTime.SecondiseMSFloat( datetime_value_range.GetStepMS() ) )
        
        vbox = QP.VBoxLayout()
        
        self._label = ClientGUICommon.BetterStaticText( self, label = 'initialising' )
        self._label.setWordWrap( True )
        
        QP.AddToLayout( vbox, self._label, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if self._none_allowed:
            
            ClientGUICommon.WrapInText( self._none_time, self, 'No time: ' )
            
            QP.AddToLayout( vbox, self._none_time, CC.FLAGS_CENTER_PERPENDICULAR )
            
        else:
            
            self._none_time.setVisible( False )
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        
        if self._time_allowed:
            
            if self._milliseconds_allowed:
                
                self._time.setDisplayFormat( 'hh:mm:ss.zzz' )
                
            elif self._seconds_allowed:
                
                self._time.setDisplayFormat( 'hh:mm:ss' )
                
            else:
                
                self._time.setDisplayFormat( 'hh:mm' )
                
            
            QP.AddToLayout( hbox, self._time, CC.FLAGS_CENTER_PERPENDICULAR )
            
        else:
            
            self._time.setVisible( False )
            
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._step_box.Add( self._step, CC.FLAGS_ON_RIGHT )
        
        QP.AddToLayout( vbox, self._step_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._now_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._NoneClicked()
        
        self._UpdateLabelAndStep()
        
        self._none_time.clicked.connect( self._NoneClicked )
        
    
    def _Copy( self ):
        
        datetime_value_range = self.GetValue()
        
        best_qt_datetime = datetime_value_range.GetBestVisualValue()
        
        if best_qt_datetime is None:
            
            timestamp = None
            
        else:
            
            timestamp = HydrusTime.SecondiseMSFloat( best_qt_datetime.toMSecsSinceEpoch() )
            
        
        text = json.dumps( timestamp )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _NoneClicked( self ):
        
        editable = not self._none_time.isChecked()
        
        self._date.setEnabled( editable )
        self._time.setEnabled( editable )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        timestamp = None
        timestamp_set = False
        
        if not timestamp_set:
            
            try:
                
                timestamp = json.loads( raw_text )
                
                timestamp_set = True
                
                if isinstance( timestamp, str ):
                    
                    try:
                        
                        timestamp = float( timestamp )
                        
                    except ValueError:
                        
                        raise Exception( 'Does not look like a number!' )
                        
                    
                
            except Exception as e:
                
                pass
                
            
        
        if not timestamp_set:
            
            try:
                
                timestamp = ClientTime.ParseDate( raw_text )
                
                timestamp_set = True
                
            except Exception as e:
                
                pass
                
            
        
        if not timestamp_set:
            
            ClientGUIDialogsMessage.ShowWarning( self, f'Sorry, I did not understand that! I am looking for a simple timestamp integer or parseable datestring, but I got:\n\n{raw_text}' )
            
            return
            
        
        try:
            
            looks_good = timestamp is None or isinstance( timestamp, ( int, float ) )
            
            if not looks_good:
                
                raise Exception( 'Not a timestamp!' )
                
            
            if timestamp is None:
                
                qt_datetime = None
                
            else:
                
                timestamp_ms = HydrusTime.MillisecondiseS( timestamp )
                
                qt_datetime = QC.QDateTime.fromMSecsSinceEpoch( timestamp_ms, QC.QTimeZone.systemTimeZone() )
                
            
            datetime_value_range = self._current_datetime_value_range.DuplicateWithNewQtDateTime( qt_datetime )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'A parseable timestamp string', e )
            
            return
            
        
        self.SetValue( datetime_value_range )
        
    
    def _SetNow( self ):
        
        qt_datetime = QC.QDateTime.currentDateTime()
        
        datetime_value_range = self._current_datetime_value_range.DuplicateWithNewQtDateTime( qt_datetime )
        
        self.SetValue( datetime_value_range )
        
    
    
    def _UpdateLabelAndStep( self ):
        
        if self._original_datetime_value_range.GetSetCount() <= 1:
            
            self._label.hide()
            
        else:
            
            s = 'Originally, ' + self._original_datetime_value_range.ToString()
            
            self._label.setText( s )
            self._label.show()
            
        
        self._step_box.setVisible( self._original_datetime_value_range.IsMultipleFiles() )
        
    
    def GetValue( self ) -> DateTimeWidgetValueRange:
        
        if self._none_time.isChecked():
            
            return self._current_datetime_value_range.DuplicateWithNewQtDateTime( None )
            
        
        qt_date = self._date.selectedDate()
        
        qt_time = self._time.time()
        
        qt_datetime = QC.QDateTime( qt_date, qt_time, QC.QTimeZone.systemTimeZone() )
        
        now = QC.QDateTime.currentDateTime()
        
        if self._only_past_dates and qt_datetime > now:
            
            qt_datetime = now
            
        
        datetime_value_range = self._current_datetime_value_range.DuplicateWithNewQtDateTime( qt_datetime )
        
        datetime_value_range.SetStepMS( int( self._step.GetValue() * 1000 ) )
        
        return datetime_value_range
        
    
    def HasChanges( self ):
        
        return self.GetValue() != self._original_datetime_value_range
        
    
    def SetValue( self, datetime_value_range: DateTimeWidgetValueRange ):
        
        if datetime_value_range.IsAllNull() and not self._none_allowed:
            
            return
            
        
        if not self._we_have_initialised_with_setvalue:
            
            self._original_datetime_value_range = datetime_value_range
            
            self._we_have_initialised_with_setvalue = True
            
        
        self._current_datetime_value_range = datetime_value_range
        
        value_to_set_visually = datetime_value_range.GetBestVisualValue()
        
        if value_to_set_visually is None:
            
            self._none_time.setChecked( True )
            
        else:
            
            self._none_time.setChecked( False )
            
            self._date.setSelectedDate( value_to_set_visually.date() )
            self._time.setTime( value_to_set_visually.time() )
            
        
        self._step.SetValue( HydrusTime.SecondiseMSFloat( datetime_value_range.GetStepMS() ) )
        
        self._NoneClicked()
        
        self._UpdateLabelAndStep()
        
        self.dateTimeChanged.emit()
        
    

class TimeDeltaButton( QW.QPushButton ):
    
    timeDeltaChanged = QC.Signal()
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False ):
        
        super().__init__( parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._monthly_allowed = monthly_allowed
        
        self._value = self._min
        
        self.setText( 'initialising' )
        
        self.clicked.connect( self.EventButton )
        
    
    def _RefreshLabel( self ):
        
        value = self._value
        
        if value is None:
            
            text = 'monthly'
            
        else:
            
            text = HydrusTime.TimeDeltaToPrettyTimeDelta( value )
            
        
        self.setText( text )
        
    
    def EventButton( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit time delta' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = TimeDeltaWidget( panel, min = self._min, days = self._show_days, hours = self._show_hours, minutes = self._show_minutes, seconds = self._show_seconds, monthly_allowed = self._monthly_allowed )
            
            control.SetValue( self._value )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                value = panel.GetValue()
                
                self.SetValue( value )
                
                self.timeDeltaChanged.emit()
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
        self._RefreshLabel()
        
        
    

class TimeDeltaWidget( QW.QWidget ):
    
    timeDeltaChanged = QC.Signal()
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, milliseconds = False, monthly_allowed = False, monthly_label = 'monthly', negative_allowed = False, max_days = 3523 ):
        
        super().__init__( parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._show_milliseconds = milliseconds
        self._monthly_allowed = monthly_allowed
        
        first_expando_guy_set = False
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if self._show_days:
            
            self._days = ClientGUICommon.BetterSpinBox( self, min=0, max=max_days, width = 50 )
            self._days.valueChanged.connect( self.EventChange )
            self._days.installEventFilter( self )
            
            if negative_allowed:
                
                self._days.setMinimum( - self._days.maximum() )
                
            
            if first_expando_guy_set:
                
                flags = CC.FLAGS_CENTER_PERPENDICULAR
                
            else:
                
                flags = CC.FLAGS_EXPAND_BOTH_WAYS
                
                first_expando_guy_set = True
                
            
            QP.AddToLayout( hbox, self._days, flags )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_hours:
            
            self._hours = ClientGUICommon.BetterSpinBox( self, min=0, max=23, width = 45 )
            self._hours.valueChanged.connect( self.EventChange )
            self._hours.installEventFilter( self )
            
            if negative_allowed:
                
                self._hours.setMinimum( - self._hours.maximum() )
                
            
            if first_expando_guy_set:
                
                flags = CC.FLAGS_CENTER_PERPENDICULAR
                
            else:
                
                flags = CC.FLAGS_EXPAND_BOTH_WAYS
                
                first_expando_guy_set = True
                
            
            QP.AddToLayout( hbox, self._hours, flags )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_minutes:
            
            self._minutes = ClientGUICommon.BetterSpinBox( self, min=0, max=59, width = 45 )
            self._minutes.valueChanged.connect( self.EventChange )
            self._minutes.installEventFilter( self )
            
            if negative_allowed:
                
                self._minutes.setMinimum( - self._minutes.maximum() )
                
            
            if first_expando_guy_set:
                
                flags = CC.FLAGS_CENTER_PERPENDICULAR
                
            else:
                
                flags = CC.FLAGS_EXPAND_BOTH_WAYS
                
                first_expando_guy_set = True
                
            
            QP.AddToLayout( hbox, self._minutes, flags )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'minutes'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_seconds:
            
            self._seconds = ClientGUICommon.BetterSpinBox( self, min=0, max=59, width = 45 )
            self._seconds.valueChanged.connect( self.EventChange )
            self._seconds.installEventFilter( self )
            
            if negative_allowed:
                
                self._seconds.setMinimum( - self._seconds.maximum() )
                
            
            if first_expando_guy_set:
                
                flags = CC.FLAGS_CENTER_PERPENDICULAR
                
            else:
                
                flags = CC.FLAGS_EXPAND_BOTH_WAYS
                
                first_expando_guy_set = True
                
            
            QP.AddToLayout( hbox, self._seconds, flags )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'seconds'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_milliseconds:
            
            self._milliseconds = ClientGUICommon.BetterSpinBox( self, min=0, max=999, width = 65 )
            self._milliseconds.valueChanged.connect( self.EventChange )
            self._milliseconds.installEventFilter( self )
            
            if negative_allowed:
                
                self._milliseconds.setMinimum( - self._milliseconds.maximum() )
                
            
            if first_expando_guy_set:
                
                flags = CC.FLAGS_CENTER_PERPENDICULAR
                
            else:
                
                flags = CC.FLAGS_EXPAND_BOTH_WAYS
                
                first_expando_guy_set = True
                
            
            QP.AddToLayout( hbox, self._milliseconds, flags )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'ms'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._monthly_allowed:
            
            self._monthly = QW.QCheckBox( self )
            self._monthly.clicked.connect( self.EventChange )
            
            QP.AddToLayout( hbox, self._monthly, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,monthly_label), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        self.blockSignals( True )
        
        self.SetValue( 0 )
        
        self.blockSignals( False )
        
        self.setLayout( hbox )
        
    
    def _UpdateEnables( self ):
        
        value = self.GetValue()
        
        if self._show_days:
            
            self._days.setEnabled( value is not None )
            
        
        if self._show_hours:
            
            self._hours.setEnabled( value is not None )
            
        
        if self._show_minutes:
            
            self._minutes.setEnabled( value is not None )
            
        
        if self._show_seconds:
            
            self._seconds.setEnabled( value is not None )
            
        
        if self._show_milliseconds:
            
            self._milliseconds.setEnabled( value is not None )
            
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.FocusOut:
                
                if not ClientGUIFunctions.WidgetOrAnyTLWChildHasFocus( self ):
                    
                    value = self.GetValue()
                    
                    if value is not None and value < self._min:
                        
                        self.SetValue( self._min )
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def EventChange( self ):
        
        self._UpdateEnables()
        
        self.timeDeltaChanged.emit()
        
    
    def GetValue( self ) -> float | None:
        
        if self._monthly_allowed and self._monthly.isChecked():
            
            return None
            
        
        value = 0
        
        if self._show_days:
            
            value += self._days.value() * 86400
            
        
        if self._show_hours:
            
            value += self._hours.value() * 3600
            
        
        if self._show_minutes:
            
            value += self._minutes.value() * 60
            
        
        if self._show_seconds:
            
            value += self._seconds.value()
            
        
        if self._show_milliseconds:
            
            value += HydrusTime.SecondiseMSFloat( self._milliseconds.value() )
            
        
        return value
        
    
    def SetValue( self, value: float ):
        
        if self._monthly_allowed:
            
            if value is None:
                
                self._monthly.setChecked( True )
                
            else:
                
                self._monthly.setChecked( False )
                
            
        
        if value is not None:
            
            if value < self._min:
                
                value = self._min
                
            
            if value < 0:
                
                multiplier = -1
                value = abs( value )
                
            else:
                
                multiplier = 1
                
            
            if self._show_days:
                
                self._days.setValue( int( multiplier * ( value // 86400 ) ) )
                
                value %= 86400
                
            
            if self._show_hours:
                
                self._hours.setValue( int( multiplier * ( value // 3600 ) ) )
                
                value %= 3600
                
            
            if self._show_minutes:
                
                self._minutes.setValue( int( multiplier * ( value // 60 ) ) )
                
                value %= 60
                
            
            if self._show_seconds:
                
                self._seconds.setValue( int( multiplier * int( value ) ) )
                
                value %= 1
                
            
            if self._show_milliseconds:
                
                self._milliseconds.setValue( int( multiplier * value * 1000 ) )
                
            
        
        self._UpdateEnables()
        
    

class NoneableTimeDeltaWidget( QW.QWidget ):
    
    timeDeltaChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, default_value: float, message = '', none_phrase = 'no limit', min = 1, days = False, hours = False, minutes = False, seconds = False, milliseconds = False, negative_allowed = False ):
        
        super().__init__( parent )
        
        self._checkbox = QW.QCheckBox( self )
        self._checkbox.stateChanged.connect( self._UpdateWidgetsEnabled )
        self._checkbox.setText( none_phrase )
        
        self._time_delta_widget = TimeDeltaWidget( self, min = min, days = days, hours = hours, minutes = minutes, seconds = seconds, milliseconds = milliseconds, monthly_allowed = False, negative_allowed = negative_allowed )
        
        self.SetValue( default_value )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if len( message ) > 0:
            
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, message + ': '), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._time_delta_widget, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, '  ' ), CC.FLAGS_CENTER_PERPENDICULAR ) # some would say this is crazy
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self._time_delta_widget.timeDeltaChanged.connect( self._HandleValueChanged )
        self._checkbox.stateChanged.connect( self._HandleValueChanged )
        
        
    def _HandleValueChanged( self ):
        
        self.timeDeltaChanged.emit()
        
    
    def _UpdateWidgetsEnabled( self ):
        
        controls_interactable = not self._checkbox.isChecked()
        
        self._time_delta_widget.setEnabled( controls_interactable )
        
    
    def GetValue( self ) -> float | None:
        
        if self._checkbox.isChecked():
            
            return None
            
        else:
            
            return self._time_delta_widget.GetValue()
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
                
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.setChecked( True )
            
            self._time_delta_widget.setEnabled( False )
            
        else:
            
            self._checkbox.setChecked( False )
            
            self._time_delta_widget.setEnabled( True )
            
            self._time_delta_widget.SetValue( value )
            
        
    

class TimestampDataStubCtrl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, timestamp_data_stub = None, show_aggregate_modified_time = False ):
        
        super().__init__( parent )
        
        if timestamp_data_stub is None:
            
            timestamp_data_stub = ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_ARCHIVED )
            
        
        self._show_aggregate_modified_time = show_aggregate_modified_time
        
        #
        
        self._timestamp_type = ClientGUICommon.BetterChoice( self )
        
        for timestamp_type in [ HC.TIMESTAMP_TYPE_ARCHIVED, HC.TIMESTAMP_TYPE_MODIFIED_FILE, HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE, HC.TIMESTAMP_TYPE_IMPORTED, HC.TIMESTAMP_TYPE_DELETED, HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, HC.TIMESTAMP_TYPE_LAST_VIEWED ]:
            
            if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE and not show_aggregate_modified_time:
                
                continue
                
            
            label = HC.timestamp_type_str_lookup[ timestamp_type ]
            
            self._timestamp_type.addItem( label, timestamp_type )
            
        
        #
        
        self._current_file_service = ClientGUICommon.BetterChoice( self )
        
        for service in CG.client_controller.services_manager.GetServices( HC.REAL_FILE_SERVICES ):
            
            self._current_file_service.addItem( service.GetName(), service.GetServiceKey() )
            
        
        #
        
        self._deleted_file_service = ClientGUICommon.BetterChoice( self )
        
        for service in CG.client_controller.services_manager.GetServices( HC.FILE_SERVICES_WITH_DELETE_RECORD ):
            
            self._deleted_file_service.addItem( service.GetName(), service.GetServiceKey() )
            
        
        #
        
        self._canvas_type = ClientGUICommon.BetterChoice( self )
        
        for canvas_type in [ CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW ]:
            
            self._canvas_type.addItem( CC.canvas_type_str_lookup[ canvas_type ], canvas_type )
            
        
        #
        
        self._domain_panel = QW.QWidget( self )
        
        self._domain = QW.QLineEdit( self._domain_panel )
        
        rows = []
        
        rows.append( ( 'domain: ', self._domain ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._domain_panel, rows )
        
        self._domain_panel.setLayout( gridbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._timestamp_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._current_file_service, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._deleted_file_service, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._canvas_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._domain_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._SetValue( timestamp_data_stub )
        
        self._TimestampTypeChanged()
        
        self._timestamp_type.currentIndexChanged.connect( self._TimestampTypeChanged )
        
    
    def _SetValue( self, timestamp_data_stub: ClientTime.TimestampData ):
        
        timestamp_type = timestamp_data_stub.timestamp_type
        
        self._timestamp_type.SetValue( timestamp_type )
        
        location = timestamp_data_stub.location
        
        if timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            if timestamp_type == HC.TIMESTAMP_TYPE_IMPORTED:
                
                self._current_file_service.SetValue( location )
                
            else:
                
                self._deleted_file_service.SetValue( location )
                
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            self._canvas_type.SetValue( location )
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            self._domain.setText( location )
            
        
    
    def _TimestampTypeChanged( self ):
        
        self._current_file_service.setVisible( False )
        self._deleted_file_service.setVisible( False )
        self._canvas_type.setVisible( False )
        self._domain_panel.setVisible( False )
        
        timestamp_type = self._timestamp_type.GetValue()
        
        if timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
            
            if timestamp_type == HC.TIMESTAMP_TYPE_IMPORTED:
                
                self._current_file_service.setVisible( True )
                
            else:
                
                self._deleted_file_service.setVisible( True )
                
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            self._canvas_type.setVisible( True )
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            self._domain_panel.setVisible( True )
            
        
    
    def GetValue( self ) -> ClientTime.TimestampData:
        
        timestamp_type = self._timestamp_type.GetValue()
        
        if timestamp_type in ClientTime.SIMPLE_TIMESTAMP_TYPES:
            
            timestamp_data_stub = ClientTime.TimestampData.STATICSimpleStub( timestamp_type )
            
        else:
            
            if timestamp_type in ClientTime.FILE_SERVICE_TIMESTAMP_TYPES:
                
                if timestamp_type == HC.TIMESTAMP_TYPE_IMPORTED:
                    
                    location = self._current_file_service.GetValue()
                    
                else:
                    
                    location = self._deleted_file_service.GetValue()
                    
                
            elif timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
                
                location = self._canvas_type.GetValue()
                
            elif timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
                
                location = self._domain.text()
                
                if location == '':
                    
                    raise HydrusExceptions.VetoException( 'You have to enter a domain!' )
                    
                
            else:
                
                raise HydrusExceptions.VetoException( 'Unknown timestamp type!' )
                
            
            timestamp_data_stub = ClientTime.TimestampData( timestamp_type = timestamp_type, location = location )
            
        
        return timestamp_data_stub
        
    
    def SetValue( self, timestamp_data_stub: ClientTime.TimestampData ):
        
        self._SetValue( timestamp_data_stub )
        
    

class NumberTestWidgetDuration( ClientGUINumberTest.NumberTestWidget ):
    
    def _GenerateAbsoluteValueWidget( self, max: int ):
        
        widget = TimeDeltaWidget( self, min = 0, minutes = True, seconds = True, milliseconds = True )
        
        widget.timeDeltaChanged.connect( self.valueChanged )
        
        return widget
        
    
    def _GenerateValueWidget( self, max: int ):
        
        widget = TimeDeltaWidget( self, min = 0, days = False, hours = True, minutes = True, seconds = True, milliseconds = True )
        
        widget.timeDeltaChanged.connect( self.valueChanged )
        
        return widget
        
    
    def _GetAbsoluteValue( self ):
        
        return HydrusTime.MillisecondiseS( self._absolute_plus_or_minus.GetValue() )
        
    
    def _SetAbsoluteValue( self, value_ms ):
        
        return self._absolute_plus_or_minus.SetValue( HydrusTime.SecondiseMSFloat( value_ms ) )
        
    
    def _GetSubValue( self ) -> int:
        
        return HydrusTime.MillisecondiseS( self._value.GetValue() )
        
    
    def _SetSubValue( self, value_ms ):
        
        return self._value.SetValue( HydrusTime.SecondiseMSFloat( value_ms ) )
        
    

class NumberTestWidgetTimestamp( ClientGUINumberTest.NumberTestWidget ):
    
    VERTICAL_CHOICE = True
    
    def __init__(
        self,
        parent,
        allowed_operators = None,
        max = 200000,
        unit_string = None,
        appropriate_absolute_plus_or_minus_default = 86400 * 1000,
        appropriate_percentage_plus_or_minus_default = 15,
        swap_in_string_for_value = None
    ):
        
        super().__init__(
            parent,
            allowed_operators = allowed_operators,
            max = max,
            unit_string = unit_string,
            appropriate_absolute_plus_or_minus_default = appropriate_absolute_plus_or_minus_default,
            appropriate_percentage_plus_or_minus_default = appropriate_percentage_plus_or_minus_default,
            swap_in_string_for_value = swap_in_string_for_value
        )
        
    
    def _GenerateAbsoluteValueWidget( self, max: int ):
        
        widget = TimeDeltaWidget( self, min = 0, days = True, hours = True, minutes = True, seconds = True, milliseconds = True )
        
        widget.timeDeltaChanged.connect( self.valueChanged )
        
        return widget
        
    
    def _GenerateChoiceTuples( self, allowed_operators ):
        
        choice_tuples = []
        
        for possible_operator in [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
        ]:
            
            if possible_operator in allowed_operators:
                
                text = ClientNumberTest.number_test_operator_to_timestamp_str_lookup[ possible_operator ]
                
                if possible_operator == ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
                    
                    text += '%'
                    
                
                tooltip = ClientNumberTest.number_test_operator_to_timestamp_desc_lookup[ possible_operator ]
                
                choice_tuples.append( ( text, possible_operator, tooltip ) )
                
            
        
        return choice_tuples
        
    
    def _GenerateValueWidget( self, max: int ):
        
        # this should actually be some calendar guy, but we'll do that when we actually use it m8
        
        widget = TimeDeltaWidget( self, min = 0, days = True, hours = True, minutes = True, seconds = True, milliseconds = True )
        
        widget.timeDeltaChanged.connect( self.valueChanged )
        
        return widget
        
    
    def _GetAbsoluteValue( self ):
        
        return HydrusTime.MillisecondiseS( self._absolute_plus_or_minus.GetValue() )
        
    
    def _SetAbsoluteValue( self, value_ms ):
        
        return self._absolute_plus_or_minus.SetValue( HydrusTime.SecondiseMSFloat( value_ms ) )
        
    
    def _GetSubValue( self ) -> int:
        
        return HydrusTime.MillisecondiseS( self._value.GetValue() )
        
    
    def _SetSubValue( self, value_ms ):
        
        return self._value.SetValue( HydrusTime.SecondiseMSFloat( value_ms ) )
        
    

class VelocityCtrl( QW.QWidget ):
    
    velocityChanged = QC.Signal()
    
    def __init__( self, parent, min_unit_value, max_unit_value, min_time_delta, days = False, hours = False, minutes = False, seconds = False, per_phrase = 'per', unit = None ):
        
        super().__init__( parent )
        
        self._num = ClientGUICommon.BetterSpinBox( self, min=min_unit_value, max=max_unit_value, width = 60 )
        
        self._times = TimeDeltaWidget( self, min = min_time_delta, days = days, hours = hours, minutes = minutes, seconds = seconds )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        
        mid_text = per_phrase
        
        if unit is not None:
            
            mid_text = '{} {}'.format( unit, mid_text )
            
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,mid_text), CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( hbox, self._times, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._num.valueChanged.connect( self.velocityChanged )
        self._times.timeDeltaChanged.connect( self.velocityChanged )
        
    
    def GetValue( self ):
        
        num = self._num.value()
        time_delta = self._times.GetValue()
        
        return ( num, time_delta )
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
                
            
        
    
    def SetValue( self, velocity ):
        
        ( num, time_delta ) = velocity
        
        self._num.setValue( num )
        
        self._times.SetValue( time_delta )
        
    
