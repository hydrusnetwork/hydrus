import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing import ClientImporting
from hydrus.client.importing.options import ClientImportOptions

class EditCheckerOptions( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, checker_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
        help_button.setToolTip( 'Show help regarding these checker options.' )
        
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
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            never_faster_than_min = 1
            never_slower_than_min = 1
            
            flat_check_period_min = 1
            
        else:
            
            never_faster_than_min = 30
            never_slower_than_min = 600
            
            flat_check_period_min = 180
            
        
        self._reactive_check_panel = ClientGUICommon.StaticBox( self, 'reactive checking' )
        
        self._intended_files_per_check = ClientGUICommon.BetterSpinBox( self._reactive_check_panel, min=1, max=1000 )
        self._intended_files_per_check.setToolTip( 'How many new files you want the checker to find on each check. If a source is producing about 2 files a day, and this is set to 6, you will probably get a check every three days. You probably want this to be a low number, like 1-4.' )
        
        self._never_faster_than = TimeDeltaCtrl( self._reactive_check_panel, min = never_faster_than_min, days = True, hours = True, minutes = True, seconds = True )
        self._never_faster_than.setToolTip( 'Even if the download source produces many new files, the checker will never ask for a check more often than this. This is a safety measure.' )
        
        self._never_slower_than = TimeDeltaCtrl( self._reactive_check_panel, min = never_slower_than_min, days = True, hours = True, minutes = True, seconds = True )
        self._never_slower_than.setToolTip( 'Even if the download source slows down significantly, the checker will make sure it checks at least this often anyway, just to catch a future wave in time.' )
        
        #
        
        self._static_check_panel = ClientGUICommon.StaticBox( self, 'static checking' )
        
        self._flat_check_period = TimeDeltaCtrl( self._static_check_panel, min = flat_check_period_min, days = True, hours = True, minutes = True, seconds = True )
        self._flat_check_period.setToolTip( 'Always use the same check delay. It is based on the time the last check completed, not the time the last check was due. If you want once a day with no skips, try setting this to 23 hours.' )
        
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
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        label = 'If you do not understand this panel, use the buttons! The defaults are fine for most purposes!'
        
        st = ClientGUICommon.BetterStaticText( self._reactive_check_panel, label = label )
        
        st.setWordWrap( True )
        st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, defaults_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            label = 'As you are in advanced mode, these options have extremely low limits. This is intended only for testing and small scale private network tasks. Do not use very fast check times for real world use on public websites, as it is wasteful and rude, hydrus will be overloaded with high-CPU parsing work, and you may get your IP banned.'
            
            st = ClientGUICommon.BetterStaticText( self, label = label )
            st.setObjectName( 'HydrusWarning' )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._reactive_check_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._static_check_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._flat_check_period_checkbox.clicked.connect( self.EventFlatPeriodCheck )
        
    
    def _ShowHelp( self ):
        
        help = 'The intention of this object is to govern how frequently the watcher or subscription checks for new files--and when it should stop completely.'
        help += os.linesep * 2
        help += 'PROTIP: Do not change anything here unless you understand what it means!'
        help += os.linesep * 2
        help += 'In general, checkers can and should be set up to check faster or slower based on how fast new files are coming in. This is polite to the server you are talking to and saves you CPU and bandwidth. The rate of new files is called the \'file velocity\' and is based on how many files appeared in a certain period before the _most recent check time_.'
        help += os.linesep * 2
        help += 'Once the first check is done and an initial file velocity is established, the time to the next check will be based on what you set for the \'intended files per check\'. If the current file velocity is 10 files per 24 hours, and you set the intended files per check to 5 files, the checker will set the next check time to be 12 hours after the previous check time.'
        help += os.linesep * 2
        help += 'After a check is completed, the new file velocity and next check time is calculated, so when files are being posted frequently, it will check more often. When things are slow, it will slow down as well. There are also minimum and maximum check periods to smooth out the bumps.'
        help += os.linesep * 2
        help += 'But if you would rather just check at a fixed rate, check the checkbox and you will get a simpler \'static checking\' panel.'
        help += os.linesep * 2
        help += 'If the \'file velocity\' drops below a certain amount, the checker considers the source of files dead and will stop checking. If it falls into this state but you think there might have since been a rush of new files, hit the watcher or subscription\'s \'check now\' button in an attempt to revive the checker. If there are new files, it will start checking again until they drop off once more.'
        help += os.linesep * 2
        help += 'If you are still not comfortable with how this system works, the \'reasonable defaults\' are good fallbacks. Most of the time, setting some reasonable rules and leaving checkers to do their work is the best way to deal with this stuff, rather than obsessing over the exact perfect values you want for each situation.'
        
        QW.QMessageBox.information( self, 'Information', help )
        
    
    def _UpdateEnabledControls( self ):
        
        if self._flat_check_period_checkbox.isChecked():
            
            self._reactive_check_panel.hide()
            self._static_check_panel.show()
            
        else:
            
            self._reactive_check_panel.show()
            self._static_check_panel.hide()
        
    
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
        
    
class TimeDeltaButton( QW.QPushButton ):

    timeDeltaChanged = QC.Signal()
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False ):
        
        QW.QPushButton.__init__( self, parent )
        
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
            
            text = HydrusData.TimeDeltaToPrettyTimeDelta( value )
            
        
        self.setText( text )
        
    
    def EventButton( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit time delta' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = TimeDeltaCtrl( panel, min = self._min, days = self._show_days, hours = self._show_hours, minutes = self._show_minutes, seconds = self._show_seconds, monthly_allowed = self._monthly_allowed )
            
            control.SetValue( self._value )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                value = panel.GetValue()
                
                self.SetValue( value )
                
                self.timeDeltaChanged.emit()
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
        self._RefreshLabel()
        
        
class TimeDeltaCtrl( QW.QWidget ):
    
    timeDeltaChanged = QC.Signal()
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False, monthly_label = 'monthly' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._monthly_allowed = monthly_allowed
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if self._show_days:
            
            self._days = ClientGUICommon.BetterSpinBox( self, min=0, max=3653, width = 50 )
            self._days.valueChanged.connect( self.EventChange )
            
            QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_hours:
            
            self._hours = ClientGUICommon.BetterSpinBox( self, min=0, max=23, width = 45 )
            self._hours.valueChanged.connect( self.EventChange )
            
            QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_minutes:
            
            self._minutes = ClientGUICommon.BetterSpinBox( self, min=0, max=59, width = 45 )
            self._minutes.valueChanged.connect( self.EventChange )
            
            QP.AddToLayout( hbox, self._minutes, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'minutes'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._show_seconds:
            
            self._seconds = ClientGUICommon.BetterSpinBox( self, min=0, max=59, width = 45 )
            self._seconds.valueChanged.connect( self.EventChange )
            
            QP.AddToLayout( hbox, self._seconds, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'seconds'), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._monthly_allowed:
            
            self._monthly = QW.QCheckBox( self )
            self._monthly.clicked.connect( self.EventChange )
            
            QP.AddToLayout( hbox, self._monthly, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,monthly_label), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        self.setLayout( hbox )
        
    
    def _UpdateEnables( self ):
        
        value = self.GetValue()
        
        if value is None:
            
            if self._show_days:
                
                self._days.setEnabled( False )
                
            
            if self._show_hours:
                
                self._hours.setEnabled( False )
                
            
            if self._show_minutes:
                
                self._minutes.setEnabled( False )
                
            
            if self._show_seconds:
                
                self._seconds.setEnabled( False )
                
            
        else:
            
            if self._show_days:
                
                self._days.setEnabled( True )
                
            
            if self._show_hours:
                
                self._hours.setEnabled( True )
                
            
            if self._show_minutes:
                
                self._minutes.setEnabled( True )
                
            
            if self._show_seconds:
                
                self._seconds.setEnabled( True )
                
            
        
    
    def EventChange( self ):
        
        value = self.GetValue()
        
        if value is not None and value < self._min:
            
            self.SetValue( self._min )
            
        
        self._UpdateEnables()
        
        self.timeDeltaChanged.emit()
        
    
    def GetValue( self ):
        
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
            
        
        return value
        
    
    def SetValue( self, value ):
        
        if self._monthly_allowed:
            
            if value is None:
                
                self._monthly.setChecked( True )
                
            else:
                
                self._monthly.setChecked( False )
                
            
        
        if value is not None:
            
            if value < self._min:
                
                value = self._min
                
            
            if self._show_days:
                
                self._days.setValue( value // 86400 )
                
                value %= 86400
                
            
            if self._show_hours:
                
                self._hours.setValue( value // 3600 )
                
                value %= 3600
                
            
            if self._show_minutes:
                
                self._minutes.setValue( value // 60 )
                
                value %= 60
                
            
            if self._show_seconds:
                
                self._seconds.setValue( value )
                
            
        
        self._UpdateEnables()
        
    
class VelocityCtrl( QW.QWidget ):
    
    velocityChanged = QC.Signal()
    
    def __init__( self, parent, min_unit_value, max_unit_value, min_time_delta, days = False, hours = False, minutes = False, seconds = False, per_phrase = 'per', unit = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._num = ClientGUICommon.BetterSpinBox( self, min=min_unit_value, max=max_unit_value, width = 60 )
        
        self._times = TimeDeltaCtrl( self, min = min_time_delta, days = days, hours = hours, minutes = minutes, seconds = seconds )
        
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
        
    
