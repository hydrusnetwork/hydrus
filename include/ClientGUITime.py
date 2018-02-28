import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusData
import os
import wx

class EditCheckerOptions( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, checker_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowHelp )
        help_button.SetToolTip( 'Show help regarding these checker options.' )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        # add statictext or whatever that will update on any updates above to say 'given velocity of blah and last check at blah, next check in 5 mins'
        # or indeed this could just take the seed cache and last check of the caller, if there is one
        # this would be more useful to the user, to know 'right, on ok, it'll refresh in 30 mins'
        
        self._intended_files_per_check = wx.SpinCtrl( self, min = 1, max = 1000 )
        
        self._never_faster_than = TimeDeltaCtrl( self, min = 30, days = True, hours = True, minutes = True, seconds = True )
        
        self._never_slower_than = TimeDeltaCtrl( self, min = 600, days = True, hours = True, minutes = True )
        
        self._death_file_velocity = VelocityCtrl( self, min_time_delta = 60, days = True, hours = True, minutes = True, per_phrase = 'in', unit = 'files' )
        
        #
        
        ( intended_files_per_check, never_faster_than, never_slower_than, death_file_velocity ) = checker_options.ToTuple()
        
        self._intended_files_per_check.SetValue( intended_files_per_check )
        self._never_faster_than.SetValue( never_faster_than )
        self._never_slower_than.SetValue( never_slower_than )
        self._death_file_velocity.SetValue( death_file_velocity )
        
        #
        
        rows = []
        
        rows.append( ( 'intended new files per check: ', self._intended_files_per_check ) )
        rows.append( ( 'stop checking if new files found falls below: ', self._death_file_velocity ) )
        rows.append( ( 'never check faster than once per: ', self._never_faster_than ) )
        rows.append( ( 'never check slower than once per: ', self._never_slower_than ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def _ShowHelp( self ):
        
        help = 'PROTIP: Do not change anything here unless you understand what it means!'
        help += os.linesep * 2
        help += 'After its initialisation check, the checker times future checks so that it will probably find the same specified number of new files each time. When files are being posted frequently, it will check more often. When things are slow, it will slow down as well.'
        help += os.linesep * 2
        help += 'For instance, if it were set to try for 5 new files with every check, and at the last check it knew that the last 24 hours had produced 10 new files, it would check again 12 hours later. When that check was done and any new files found, it would then recalculate and repeat the process.'
        help += os.linesep * 2
        help += 'If the \'file velocity\' drops below a certain amount, the checker considers the source of files dead and will stop checking. If it falls into this state but you think there might have been a rush of new files, hit the \'check now\' button in an attempt to revive the checker. If there are new files, it will start checking again until they drop off once more.'
        
        wx.MessageBox( help )
        
    
    def GetValue( self ):
        
        intended_files_per_check = self._intended_files_per_check.GetValue()
        never_faster_than = self._never_faster_than.GetValue()
        never_slower_than = self._never_slower_than.GetValue()
        death_file_velocity = self._death_file_velocity.GetValue()
        
        return ClientData.CheckerOptions( intended_files_per_check, never_faster_than, never_slower_than, death_file_velocity )
        
    
( TimeDeltaEvent, EVT_TIME_DELTA ) = wx.lib.newevent.NewCommandEvent()

class TimeDeltaButton( wx.Button ):
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False ):
        
        wx.Button.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._monthly_allowed = monthly_allowed
        
        self._value = self._min
        
        self.SetLabelText( 'initialising' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def _RefreshLabel( self ):
        
        value = self._value
        
        if value is None:
            
            text = 'monthly'
            
        else:
            
            text = HydrusData.ConvertTimeDeltaToPrettyString( value )
            
        
        self.SetLabelText( text )
        
    
    def EventButton( self, event ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit time delta' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = TimeDeltaCtrl( panel, min = self._min, days = self._show_days, hours = self._show_hours, minutes = self._show_minutes, seconds = self._show_seconds, monthly_allowed = self._monthly_allowed )
            
            control.SetValue( self._value )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                value = panel.GetValue()
                
                self.SetValue( value )
                
                new_event = TimeDeltaEvent( 0 )
                
                wx.QueueEvent( self.GetEventHandler(), new_event )
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
        self._RefreshLabel()
        
        self.GetParent().Layout()
        
    
class TimeDeltaCtrl( wx.Panel ):
    
    def __init__( self, parent, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False, monthly_label = 'monthly' ):
        
        wx.Panel.__init__( self, parent )
        
        self._min = min
        self._show_days = days
        self._show_hours = hours
        self._show_minutes = minutes
        self._show_seconds = seconds
        self._monthly_allowed = monthly_allowed
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if self._show_days:
            
            self._days = wx.SpinCtrl( self, min = 0, max = 3653, size = ( 50, -1 ) )
            self._days.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.Add( self._days, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, 'days' ), CC.FLAGS_VCENTER )
            
        
        if self._show_hours:
            
            self._hours = wx.SpinCtrl( self, min = 0, max = 23, size = ( 45, -1 ) )
            self._hours.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.Add( self._hours, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, 'hours' ), CC.FLAGS_VCENTER )
            
        
        if self._show_minutes:
            
            self._minutes = wx.SpinCtrl( self, min = 0, max = 59, size = ( 45, -1 ) )
            self._minutes.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.Add( self._minutes, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, 'minutes' ), CC.FLAGS_VCENTER )
            
        
        if self._show_seconds:
            
            self._seconds = wx.SpinCtrl( self, min = 0, max = 59, size = ( 45, -1 ) )
            self._seconds.Bind( wx.EVT_SPINCTRL, self.EventChange )
            
            hbox.Add( self._seconds, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, 'seconds' ), CC.FLAGS_VCENTER )
            
        
        if self._monthly_allowed:
            
            self._monthly = wx.CheckBox( self )
            self._monthly.Bind( wx.EVT_CHECKBOX, self.EventChange )
            
            hbox.Add( self._monthly, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, monthly_label ), CC.FLAGS_VCENTER )
            
        
        self.SetSizer( hbox )
        
    
    def _UpdateEnables( self ):
        
        value = self.GetValue()
        
        if value is None:
            
            if self._show_days:
                
                self._days.Disable()
                
            
            if self._show_hours:
                
                self._hours.Disable()
                
            
            if self._show_minutes:
                
                self._minutes.Disable()
                
            
            if self._show_seconds:
                
                self._seconds.Disable()
                
            
        else:
            
            if self._show_days:
                
                self._days.Enable()
                
            
            if self._show_hours:
                
                self._hours.Enable()
                
            
            if self._show_minutes:
                
                self._minutes.Enable()
                
            
            if self._show_seconds:
                
                self._seconds.Enable()
                
            
        
    
    def EventChange( self, event ):
        
        value = self.GetValue()
        
        if value is not None and value < self._min:
            
            self.SetValue( self._min )
            
        
        self._UpdateEnables()
        
        new_event = TimeDeltaEvent( 0 )
        
        wx.QueueEvent( self.GetEventHandler(), new_event )
        
    
    def GetValue( self ):
        
        if self._monthly_allowed and self._monthly.GetValue():
            
            return None
            
        
        value = 0
        
        if self._show_days:
            
            value += self._days.GetValue() * 86400
            
        
        if self._show_hours:
            
            value += self._hours.GetValue() * 3600
            
        
        if self._show_minutes:
            
            value += self._minutes.GetValue() * 60
            
        
        if self._show_seconds:
            
            value += self._seconds.GetValue()
            
        
        return value
        
    
    def SetValue( self, value ):
        
        if self._monthly_allowed:
            
            if value is None:
                
                self._monthly.SetValue( True )
                
            else:
                
                self._monthly.SetValue( False )
                
            
        
        if value is not None:
            
            if value < self._min:
                
                value = self._min
                
            
            if self._show_days:
                
                self._days.SetValue( value / 86400 )
                
                value %= 86400
                
            
            if self._show_hours:
                
                self._hours.SetValue( value / 3600 )
                
                value %= 3600
                
            
            if self._show_minutes:
                
                self._minutes.SetValue( value / 60 )
                
                value %= 60
                
            
            if self._show_seconds:
                
                self._seconds.SetValue( value )
                
            
        
        self._UpdateEnables()
        
    
class VelocityCtrl( wx.Panel ):
    
    def __init__( self, parent, min_time_delta = 60, days = False, hours = False, minutes = False, seconds = False, per_phrase = 'per', unit = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._num = wx.SpinCtrl( self, min = 0, max = 1000, size = ( 60, -1 ) )
        
        self._times = TimeDeltaCtrl( self, min = min_time_delta, days = days, hours = hours, minutes = minutes, seconds = seconds )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._num, CC.FLAGS_VCENTER )
        
        mid_text = per_phrase
        
        if unit is not None:
            
            mid_text = unit + ' ' + mid_text
            
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, mid_text ), CC.FLAGS_VCENTER )
        
        hbox.Add( self._times, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def GetValue( self ):
        
        num = self._num.GetValue()
        time_delta = self._times.GetValue()
        
        return ( num, time_delta )
        
    
    def SetToolTip( self, text ):
        
        wx.Panel.SetToolTip( self, text )
        
        for c in self.GetChildren():
            
            c.SetToolTip( text )
            
        
    
    def SetValue( self, velocity ):
        
        ( num, time_delta ) = velocity
        
        self._num.SetValue( num )
        
        self._times.SetValue( time_delta )
        
    
