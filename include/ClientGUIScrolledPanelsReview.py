from . import ClientConstants as CC
from . import ClientData
from . import ClientDefaults
from . import ClientDragDrop
from . import ClientExporting
from . import ClientFiles
from . import ClientGUIACDropdown
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIFrames
from . import ClientGUIFunctions
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIPanels
from . import ClientGUIPopupMessages
from . import ClientGUITags
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientNetworking
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import ClientNetworkingLogin
from . import ClientParsing
from . import ClientPaths
from . import ClientRendering
from . import ClientSearch
from . import ClientSerialisable
from . import ClientTags
from . import ClientThreading
import collections
import http.cookiejar
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNATPunch
from . import HydrusPaths
from . import HydrusSerialisable
import os
import stat
import sys
import threading
import time
import traceback
import wx

try:
    
    from . import ClientGUIMatPlotLib
    
    MATPLOTLIB_OK = True
    
except:
    
    MATPLOTLIB_OK = False
    

class AdvancedContentUpdatePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    COPY = 0
    DELETE = 1
    DELETE_DELETED = 2
    DELETE_FOR_DELETED_FILES = 3
    
    ALL_MAPPINGS = 0
    SPECIFIC_MAPPINGS = 1
    SPECIFIC_NAMESPACE = 2
    NAMESPACED = 3
    UNNAMESPACED = 4
    
    def __init__( self, parent, service_key, hashes = None ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._service_key = service_key
        self._hashes = hashes
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
        self._service_name = service.GetName()
        
        self._command_panel = ClientGUICommon.StaticBox( self, 'database commands' )
        
        self._action_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        self._action_dropdown.Bind( wx.EVT_CHOICE, self.EventChoice )
        self._tag_type_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        self._action_text = wx.StaticText( self._command_panel, label = 'initialising' )
        self._service_key_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        
        self._go = ClientGUICommon.BetterButton( self._command_panel, 'Go!', self.Go )
        
        #
        
        self._hta_panel = ClientGUICommon.StaticBox( self, 'hydrus tag archives' )
        
        self._import_from_hta = ClientGUICommon.BetterButton( self._hta_panel, 'one-time mass import or delete using a hydrus tag archive', self.ImportFromHTA )
        self._export_to_hta = ClientGUICommon.BetterButton( self._hta_panel, 'export to hydrus tag archive', self.ExportToHTA )
        
        #
        
        services = [ service for service in HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES ) if service.GetServiceKey() != self._service_key ]
        
        if len( services ) > 0:
            
            self._action_dropdown.Append( 'copy current and pending mappings', self.COPY )
            
        
        if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            self._action_dropdown.Append( 'delete current mappings', self.DELETE )
            self._action_dropdown.Append( 'clear deleted mappings record', self.DELETE_DELETED )
            self._action_dropdown.Append( 'delete current mappings from deleted files', self.DELETE_FOR_DELETED_FILES )
            
        
        self._action_dropdown.Select( 0 )
        
        #
        
        self._tag_type_dropdown.Append( 'all', self.ALL_MAPPINGS )
        self._tag_type_dropdown.Append( 'all namespaced', self.NAMESPACED )
        self._tag_type_dropdown.Append( 'all unnamespaced', self.UNNAMESPACED )
        self._tag_type_dropdown.Append( 'specific tag', self.SPECIFIC_MAPPINGS )
        self._tag_type_dropdown.Append( 'specific namespace', self.SPECIFIC_NAMESPACE )
        
        self._tag_type_dropdown.Select( 0 )
        
        #
        
        for service in services:
            
            self._service_key_dropdown.Append( service.GetName(), service.GetServiceKey() )
            
        
        self._service_key_dropdown.Select( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._action_dropdown, CC.FLAGS_VCENTER )
        hbox.Add( self._tag_type_dropdown, CC.FLAGS_VCENTER )
        hbox.Add( self._action_text, CC.FLAGS_VCENTER )
        hbox.Add( self._service_key_dropdown, CC.FLAGS_VCENTER )
        hbox.Add( self._go, CC.FLAGS_VCENTER )
        
        self._command_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._hta_panel.Add( self._import_from_hta, CC.FLAGS_LONE_BUTTON )
        self._hta_panel.Add( self._export_to_hta, CC.FLAGS_LONE_BUTTON )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        message = 'Regarding '
        
        if self._hashes is None:
            
            message += 'all'
            
        else:
            
            message += HydrusData.ToHumanInt( len( self._hashes ) )
            
        
        message += ' files on ' + self._service_name
        
        title_st = ClientGUICommon.BetterStaticText( self, message )
        
        title_st.SetWrapWidth( 540 )
        
        message = 'These advanced operations are powerful, so think before you click. They can lock up your client for a _long_ time, and are not undoable.'
        message += os.linesep * 2
        message += 'You may need to restart your client to see their effect.' 
        
        st = ClientGUICommon.BetterStaticText( self, message )
        
        st.SetWrapWidth( 540 )
        
        vbox.Add( title_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._command_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._hta_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self.EventChoice( None )
        
    
    def EventChoice( self, event ):
        
        data = self._action_dropdown.GetChoice()
        
        if data in ( self.DELETE, self.DELETE_DELETED, self.DELETE_FOR_DELETED_FILES ):
            
            self._action_text.SetLabelText( 'from ' + self._service_name )
            
            self._service_key_dropdown.Hide()
            
        else:
            
            self._action_text.SetLabelText( 'from ' + self._service_name + ' to')
            
            self._service_key_dropdown.Show()
            
        
        self.Layout()
        
    
    def ExportToHTA( self ):
        
        ClientGUITags.ExportToHTA( self, self._service_key, self._hashes )
        
    
    def Go( self ):
        
        # at some point, rewrite this to cope with multiple tags. setsometag is ready to go on that front
        # this should prob be with a listbox so people can enter their new multiple tags in several separate goes, rather than overwriting every time
        
        action = self._action_dropdown.GetChoice()
        
        tag_type = self._tag_type_dropdown.GetChoice()
        
        if tag_type == self.ALL_MAPPINGS:
            
            tag = None
            
        elif tag_type == self.SPECIFIC_MAPPINGS:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter tag' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    entry = dlg.GetValue()
                    
                    tag = ( 'tag', entry )
                    
                else:
                    
                    return
                    
                
            
        elif tag_type == self.SPECIFIC_NAMESPACE:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter namespace' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    entry = dlg.GetValue()
                    
                    if entry.endswith( ':' ): entry = entry[:-1]
                    
                    tag = ( 'namespace', entry )
                    
                else:
                    
                    return
                    
                
            
        elif tag_type == self.NAMESPACED:
            
            tag = ( 'namespaced', None )
            
        elif tag_type == self.UNNAMESPACED:
            
            tag = ( 'unnamespaced', None )
            
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure?' ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
        if action == self.COPY:
            
            service_key_target = self._service_key_dropdown.GetChoice()
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'copy', ( tag, self._hashes, service_key_target ) ) )
            
        elif action == self.DELETE:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete', ( tag, self._hashes ) ) )
            
        elif action == self.DELETE_DELETED:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', ( tag, self._hashes ) ) )
            
        elif action == self.DELETE_FOR_DELETED_FILES:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_for_deleted_files', ( tag, self._hashes ) ) )
            
        
        service_keys_to_content_updates = { self._service_key : [ content_update ] }
        
        def do_it( job_key ):
            
            try:
                
                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            finally:
                
                job_key.Finish()
                
            
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_title', 'Processing advanced content update' )
        
        HG.client_controller.CallToThread( do_it, job_key )
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'Working\u2026' ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
        job_key.Delete()
        
    
    def ImportFromHTA( self ):
        
        text = 'Select the Hydrus Tag Archive\'s location.'
        
        with wx.FileDialog( self, message = text, style = wx.FD_OPEN ) as dlg_file:
            
            if dlg_file.ShowModal() == wx.ID_OK:
                
                path = dlg_file.GetPath()
                
                ClientGUITags.ImportFromHTA( self, path, self._service_key, self._hashes )
                
            
        
    
class MigrateDatabasePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        self._new_options = self._controller.new_options
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._prefixes_to_locations = HG.client_controller.Read( 'client_files_locations' )
        
        ( self._locations_to_ideal_weights, self._ideal_thumbnails_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        service_info = HG.client_controller.Read( 'service_info', CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        self._all_local_files_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'database_migration.html' ) )
        
        menu_items.append( ( 'normal', 'open the html migration help', 'Open the help page for database migration in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'locations' )
        
        self._current_install_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_db_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_media_paths_st = ClientGUICommon.BetterStaticText( info_panel )
        
        current_media_locations_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( info_panel )
        
        columns = [ ( 'location', -1 ), ( 'portable?', 11 ), ( 'free space', 12 ), ( 'file weight', 10 ), ( 'current usage', 24 ), ( 'ideal usage', 24 ) ]
        
        self._current_media_locations_listctrl = ClientGUIListCtrl.BetterListCtrl( current_media_locations_listctrl_panel, 'db_migration_locations', 8, 36, columns, self._ConvertLocationToListCtrlTuples, style = wx.LC_SINGLE_SEL )
        
        self._current_media_locations_listctrl.Sort()
        
        current_media_locations_listctrl_panel.SetListCtrl( self._current_media_locations_listctrl )
        
        current_media_locations_listctrl_panel.AddButton( 'add new location for files', self._SelectPathToAdd )
        current_media_locations_listctrl_panel.AddButton( 'increase file weight', self._IncreaseWeight, enabled_check_func = self._CanIncreaseWeight )
        current_media_locations_listctrl_panel.AddButton( 'decrease file weight', self._DecreaseWeight, enabled_check_func = self._CanDecreaseWeight )
        
        self._thumbnails_location = wx.TextCtrl( info_panel )
        self._thumbnails_location.Disable()
        
        self._thumbnails_location_set = ClientGUICommon.BetterButton( info_panel, 'set', self._SetThumbnailLocation )
        
        self._thumbnails_location_clear = ClientGUICommon.BetterButton( info_panel, 'clear', self._ClearThumbnailLocation )
        
        self._rebalance_status_st = ClientGUICommon.BetterStaticText( info_panel, style = wx.ALIGN_RIGHT | wx.ST_NO_AUTORESIZE )
        
        self._rebalance_button = ClientGUICommon.BetterButton( info_panel, 'move files now', self._Rebalance )
        
        #
        
        migration_panel = ClientGUICommon.StaticBox( self, 'migrate entire database' )
        
        self._migrate_db_button = ClientGUICommon.BetterButton( migration_panel, 'move entire database and all portable paths', self._MigrateDatabase )
        
        #
        
        t_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        t_hbox.Add( ClientGUICommon.BetterStaticText( info_panel, 'thumbnail location override' ), CC.FLAGS_VCENTER )
        t_hbox.Add( self._thumbnails_location, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        t_hbox.Add( self._thumbnails_location_set, CC.FLAGS_VCENTER )
        t_hbox.Add( self._thumbnails_location_clear, CC.FLAGS_VCENTER )
        
        rebalance_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        rebalance_hbox.Add( self._rebalance_status_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        rebalance_hbox.Add( self._rebalance_button, CC.FLAGS_VCENTER )
        
        info_panel.Add( self._current_install_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._current_db_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._current_media_paths_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( current_media_locations_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        info_panel.Add( t_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( rebalance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        migration_panel.Add( self._migrate_db_button, CC.FLAGS_LONE_BUTTON )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( migration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 100 )
        
        self.SetMinSize( ( min_width, -1 ) )
        
        self._Update()
        
    
    def _AddPath( self, path, starting_weight = 1 ):
        
        if path in self._locations_to_ideal_weights:
            
            wx.MessageBox( 'You already have that location entered!' )
            
            return
            
        
        if path == self._ideal_thumbnails_location_override:
            
            wx.MessageBox( 'That path is already used as the special thumbnail location--please choose another.' )
            
            return
            
        
        self._locations_to_ideal_weights[ path ] = 1
        
        self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
        
        self._Update()
        
    
    def _AdjustWeight( self, amount ):
        
        adjustees = set()
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                current_weight = self._locations_to_ideal_weights[ location ]
                
                new_amount = current_weight + amount
                
                if new_amount > 0:
                    
                    self._locations_to_ideal_weights[ location ] = new_amount
                    
                    self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
                    
                elif new_amount <= 0:
                    
                    self._RemovePath( location )
                    
                
            else:
                
                if amount > 0:
                    
                    if location != self._ideal_thumbnails_location_override:
                        
                        self._AddPath( location, starting_weight = amount )
                        
                    
                
                
            
            self._Update()
            
        
    
    def _CanDecreaseWeight( self ):
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                selection_includes_ideal_locations = True
                
                ideal_weight = self._locations_to_ideal_weights[ location ]
                
                is_big = ideal_weight > 1
                others_can_take_slack = len( self._locations_to_ideal_weights ) > 1
                
                if is_big or others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _CanIncreaseWeight( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                if len( self._locations_to_ideal_weights ) > 1:
                    
                    return True
                    
                
            elif location in locations_to_file_weights:
                
                return True
                
            
        
        return False
        
    
    def _ClearThumbnailLocation( self ):
        
        self._ideal_thumbnails_location_override = None
        
        self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
        
        self._Update()
        
    
    def _ConvertLocationToListCtrlTuples( self, location ):
        
        thumbnail_ratio_estimate = self._GetThumbnailRatioEstimate()
        
        f_space = self._all_local_files_total_size
        t_space = self._all_local_files_total_size * thumbnail_ratio_estimate
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        pretty_location = location
        
        portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
        portable = not os.path.isabs( portable_location )
        
        if portable:
            
            pretty_portable = 'yes'
            
        else:
            
            pretty_portable = 'no'
            
        
        try:
            
            free_space = HydrusPaths.GetFreeSpace( location )
            pretty_free_space = HydrusData.ToHumanBytes( free_space )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'There was a problem finding the free space for "' + location + '"! Perhaps this location does not exist?'
            
            wx.MessageBox( message )
            HydrusData.ShowText( message )
            
            free_space = 0
            pretty_free_space = 'problem finding free space'
            
        
        fp = locations_to_file_weights[ location ] / 256.0
        tp = locations_to_thumb_weights[ location ] / 256.0
        
        p = HydrusData.ConvertFloatToPercentage
        
        current_bytes = fp * f_space + tp * t_space
        
        current_usage = ( fp, tp )
        
        usages = []
        
        if fp > 0:
            
            usages.append( p( fp ) + ' files' )
            
        
        if tp > 0:
            
            usages.append( p( tp ) + ' thumbnails' )
            
        
        if len( usages ) > 0:
            
            if fp == tp:
                
                usages = [ p( fp ) + ' everything' ]
                
            
            pretty_current_usage = HydrusData.ToHumanBytes( current_bytes ) + ' - ' + ','.join( usages )
            
        else:
            
            pretty_current_usage = 'nothing'
            
        
        #
        
        if location in self._locations_to_ideal_weights:
            
            ideal_weight = self._locations_to_ideal_weights[ location ]
            
            pretty_ideal_weight = str( int( ideal_weight ) )
            
        else:
            
            ideal_weight = 0
            
            if location in locations_to_file_weights:
                
                pretty_ideal_weight = '0'
                
            else:
                
                pretty_ideal_weight = 'n/a'
                
            
        
        if location in self._locations_to_ideal_weights:
            
            total_ideal_weight = sum( self._locations_to_ideal_weights.values() )
            
            ideal_fp = self._locations_to_ideal_weights[ location ] / total_ideal_weight
            
        else:
            
            ideal_fp = 0.0
            
        
        if self._ideal_thumbnails_location_override is None:
            
            ideal_tp = ideal_fp
            
        else:
            
            if location == self._ideal_thumbnails_location_override:
                
                ideal_tp = 1.0
                
            else:
                
                ideal_tp = 0.0
                
            
        
        ideal_bytes = ideal_fp * f_space + ideal_tp * t_space
        
        ideal_usage = ( ideal_fp, ideal_tp )
        
        usages = []
        
        if ideal_fp > 0:
            
            usages.append( p( ideal_fp ) + ' files' )
            
        
        if ideal_tp > 0:
            
            usages.append( p( ideal_tp ) + ' thumbnails' )
            
        
        if len( usages ) > 0:
            
            if ideal_fp == ideal_tp:
                
                usages = [ p( ideal_fp ) + ' everything' ]
                
            
            pretty_ideal_usage = HydrusData.ToHumanBytes( ideal_bytes ) + ' - ' + ','.join( usages )
            
        else:
            
            pretty_ideal_usage = 'nothing'
            
        
        display_tuple = ( pretty_location, pretty_portable, pretty_free_space, pretty_ideal_weight, pretty_current_usage, pretty_ideal_usage )
        sort_tuple = ( location, portable, free_space, ideal_weight, current_usage, ideal_usage )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DecreaseWeight( self ):
        
        self._AdjustWeight( -1 )
        
    
    def _GetLocationsToCurrentWeights( self ):
        
        locations_to_file_weights = collections.Counter()
        locations_to_thumb_weights = collections.Counter()
        
        for ( prefix, location ) in list(self._prefixes_to_locations.items()):
            
            if prefix.startswith( 'f' ):
                
                locations_to_file_weights[ location ] += 1
                
            
            if prefix.startswith( 't' ):
                
                locations_to_thumb_weights[ location ] += 1
                
            
        
        return ( locations_to_file_weights, locations_to_thumb_weights )
        
    
    def _GetListCtrlLocations( self ):
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        all_locations = set()
        
        all_locations.update( list(self._locations_to_ideal_weights.keys()) )
        
        if self._ideal_thumbnails_location_override is not None:
            
            all_locations.add( self._ideal_thumbnails_location_override )
            
        
        all_locations.update( list(locations_to_file_weights.keys()) )
        all_locations.update( list(locations_to_thumb_weights.keys()) )
        
        all_locations = list( all_locations )
        
        return all_locations
        
    
    def _GetThumbnailRatioEstimate( self ):
        
        ( t_width, t_height ) = HG.client_controller.options[ 'thumbnail_dimensions' ]
        
        normal_num_pixels = 200 * 200
        normal_ratio = 0.016
        
        current_num_pixels = t_width * t_height
        
        estimate_ratio = ( current_num_pixels / normal_num_pixels ) * normal_ratio
        
        return estimate_ratio
        
    
    def _IncreaseWeight( self ):
        
        self._AdjustWeight( 1 )
        
    
    def _MigrateDatabase( self ):
        
        message = 'This operation will move your database files and any \'portable\' paths. It is a big job that will require a client shutdown and need you to create a new shortcut before you can launch it again.'
        message += os.linesep * 2
        message += 'If you have not read the database migration help or otherwise do not know what is going on here, turn back now!'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_1:
            
            if dlg_1.ShowModal() == wx.ID_YES:
                
                source = self._controller.GetDBDir()
                
                with wx.DirDialog( self, message = 'Choose new database location.' ) as dlg_2:
                    
                    dlg_2.SetPath( source )
                    
                    if dlg_2.ShowModal() == wx.ID_OK:
                        
                        dest = dlg_2.GetPath()
                        
                        if source == dest:
                            
                            wx.MessageBox( 'That is the same location!' )
                            
                            return
                            
                        
                        if len( os.listdir( dest ) ) > 0:
                            
                            message = dest + ' is not empty! Please select an empty destination--if your situation is more complicated, please do this move manually! Feel free to ask hydrus dev for help.'
                            
                            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg_not_empty:
                                
                                if dlg_not_empty.ShowModal() != wx.ID_YES:
                                    
                                    return
                                    
                                
                            
                        
                        message = 'Here is the client\'s best guess at your new launch command. Make sure it looks correct and copy it to your clipboard. Update your program shortcut when the transfer is complete.'
                        message += os.linesep * 2
                        message += 'Hit ok to close the client and start the transfer, cancel to back out.'
                        
                        me = sys.argv[0]
                        
                        shortcut = '"' + me + '" -d="' + dest + '"'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message, default = shortcut ) as dlg_3:
                            
                            if dlg_3.ShowModal() == wx.ID_OK:
                                
                                # careful with this stuff!
                                # the app's mainloop didn't want to exit for me, for a while, because this dialog didn't have time to exit before the thread's dialog laid a new event loop on top
                                # the confused event loops lead to problems at a C++ level in ShowModal not being able to do the Destroy because parent stuff had already died
                                # this works, so leave it alone if you can
                                
                                wx.CallAfter( self.GetParent().Close )
                                
                                portable_locations = []
                                
                                for location in set( self._prefixes_to_locations.values() ):
                                    
                                    if not os.path.exists( location ):
                                        
                                        continue
                                        
                                    
                                    portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
                                    portable = not os.path.isabs( portable_location )
                                    
                                    if portable:
                                        
                                        portable_locations.append( portable_location )
                                        
                                    
                                
                                HG.client_controller.CallToThreadLongRunning( THREADMigrateDatabase, self._controller, source, portable_locations, dest )
                                
                            
                        
                    
                
            
        
    
    def _Rebalance( self ):
        
        message = 'Moving files can be a slow and slightly laggy process, with the UI intermittently hanging, which sometimes makes manually stopping a large ongoing job difficult. Would you like to set a max runtime on this job?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'run for 10 minutes', 600 ) )
        yes_tuples.append( ( 'run for 30 minutes', 1800 ) )
        yes_tuples.append( ( 'run for 1 hour', 3600 ) )
        yes_tuples.append( ( 'run indefinitely', None ) )
        
        with ClientGUIDialogs.DialogYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                value = dlg.GetValue()
                
                if value is None:
                    
                    stop_time = None
                    
                else:
                    
                    stop_time = HydrusData.GetNow() + value
                    
                
                job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
                
            else:
                
                return
                
            
        
        job_key.SetVariable( 'popup_title', 'rebalancing files' )
        
        self._controller.CallToThread( self._controller.client_files_manager.Rebalance, job_key )
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'migrating files' ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
        self._Update()
        
    
    def _RemovePath( self, location ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        removees = set()
        
        if location not in self._locations_to_ideal_weights:
            
            wx.MessageBox( 'Please select a location with weight.' )
            
            return
            
        
        if len( self._locations_to_ideal_weights ) == 1:
            
            wx.MessageBox( 'You cannot empty every single current file location--please add a new place for the files to be moved to and then try again.' )
            
        
        if location in locations_to_file_weights:
            
            message = 'Are you sure you want to remove this location? This will schedule all of the files it is currently responsible for to be moved elsewhere.'
            
        else:
            
            message = 'Are you sure you want to remove this location? The files it would be responsible for will be shared amongst the other file locations.'
            
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                del self._locations_to_ideal_weights[ location ]
                
                self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
                
                self._Update()
                
            
        
    
    def _SelectPathToAdd( self ):
        
        with wx.DirDialog( self, 'Select the location' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                self._AddPath( path )
                
            
        
    
    def _SetThumbnailLocation( self ):
        
        with wx.DirDialog( self ) as dlg:
            
            if self._ideal_thumbnails_location_override is not None:
                
                dlg.SetPath( self._ideal_thumbnails_location_override )
                
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                if path in self._locations_to_ideal_weights:
                    
                    wx.MessageBox( 'That path already exists as a regular file location! Please choose another.' )
                    
                else:
                    
                    self._ideal_thumbnails_location_override = path
                    
                    self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
                    
                    self._Update()
                    
                
            
        
    
    def _Update( self ):
        
        self._prefixes_to_locations = HG.client_controller.Read( 'client_files_locations' )
        
        ( self._locations_to_ideal_weights, self._ideal_thumbnails_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        approx_total_db_size = self._controller.db.GetApproxTotalFileSize()
        
        self._current_db_path_st.SetLabelText( 'database (about ' + HydrusData.ToHumanBytes( approx_total_db_size ) + '): ' + self._controller.GetDBDir() )
        self._current_install_path_st.SetLabelText( 'install: ' + HC.BASE_DIR )
        
        thumbnail_ratio_estimate = self._GetThumbnailRatioEstimate()
        
        approx_total_client_files = self._all_local_files_total_size
        approx_total_thumbnails = self._all_local_files_total_size * thumbnail_ratio_estimate
        
        label = 'media is ' + HydrusData.ToHumanBytes( approx_total_client_files ) + ', thumbnails are estimated at ' + HydrusData.ToHumanBytes( approx_total_thumbnails ) + ':'
        
        self._current_media_paths_st.SetLabelText( label )
        
        locations = self._GetListCtrlLocations()
        
        self._current_media_locations_listctrl.SetData( locations )
        
        #
        
        if self._ideal_thumbnails_location_override is None:
            
            self._thumbnails_location.SetValue( 'none set' )
            
            self._thumbnails_location_set.Enable()
            self._thumbnails_location_clear.Disable()
            
        else:
            
            self._thumbnails_location.SetValue( self._ideal_thumbnails_location_override )
            
            self._thumbnails_location_set.Disable()
            self._thumbnails_location_clear.Enable()
            
        
        #
        
        if self._controller.client_files_manager.RebalanceWorkToDo():
            
            self._rebalance_button.Enable()
            
            self._rebalance_status_st.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._rebalance_status_st.SetLabelText( 'files need to be moved' )
            
        else:
            
            self._rebalance_button.Disable()
            
            self._rebalance_status_st.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._rebalance_status_st.SetLabelText( 'all files are in their ideal locations' )
            
        
    
def THREADMigrateDatabase( controller, source, portable_locations, dest ):
    
    time.sleep( 2 ) # important to have this, so the migrate dialog can close itself and clean its event loop, wew
    
    def wx_code( job_key ):
        
        HG.client_controller.CallLaterWXSafe( controller.gui, 3.0, controller.gui.Exit )
        
        # no parent because this has to outlive the gui, obvs
        
        style_override = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.DIALOG_NO_PARENT
        
        with ClientGUITopLevelWindows.DialogNullipotent( None, 'migrating files', style_override = style_override ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    db = controller.db
    
    job_key = ClientThreading.JobKey( cancel_on_shutdown = False )
    
    job_key.SetVariable( 'popup_title', 'migrating database' )
    
    wx.CallAfter( wx_code, job_key )
    
    try:
        
        job_key.SetVariable( 'popup_text_1', 'waiting for db shutdown' )
        
        while not db.LoopIsFinished():
            
            time.sleep( 1 )
            
        
        job_key.SetVariable( 'popup_text_1', 'doing the move' )
        
        def text_update_hook( text ):
            
            job_key.SetVariable( 'popup_text_1', text )
            
        
        for filename in os.listdir( source ):
            
            if filename.startswith( 'client' ) and filename.endswith( '.db' ):
                
                job_key.SetVariable( 'popup_text_1', 'moving ' + filename )
                
                source_path = os.path.join( source, filename )
                dest_path = os.path.join( dest, filename )
                
                HydrusPaths.MergeFile( source_path, dest_path )
                
            
        
        for portable_location in portable_locations:
            
            source_path = os.path.join( source, portable_location )
            dest_path = os.path.join( dest, portable_location )
            
            HydrusPaths.MergeTree( source_path, dest_path, text_update_hook = text_update_hook )
            
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        
    except:
        
        wx.CallAfter( wx.MessageBox, traceback.format_exc() )
        
        job_key.SetVariable( 'popup_text_1', 'error!' )
        
    finally:
        
        time.sleep( 3 )
        
        job_key.Finish()
        
    
class ReviewAllBandwidthPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._history_time_delta_threshold = ClientGUITime.TimeDeltaButton( self, days = True, hours = True, minutes = True, seconds = True )
        self._history_time_delta_threshold.Bind( ClientGUITime.EVT_TIME_DELTA, self.EventTimeDeltaChanged )
        
        self._history_time_delta_none = wx.CheckBox( self, label = 'show all' )
        self._history_time_delta_none.Bind( wx.EVT_CHECKBOX, self.EventTimeDeltaChanged )
        
        columns = [ ( 'name', -1 ), ( 'type', 14 ), ( 'current usage', 14 ), ( 'past 24 hours', 15 ), ( 'search distance', 17 ), ( 'this month', 12 ), ( 'uses non-default rules', 24 ), ( 'blocked?', 10 ) ]
        
        self._bandwidths = ClientGUIListCtrl.BetterListCtrl( self, 'bandwidth review', 20, 30, columns, self._ConvertNetworkContextsToListCtrlTuples, activation_callback = self.ShowNetworkContext )
        
        self._edit_default_bandwidth_rules_button = ClientGUICommon.BetterButton( self, 'edit default bandwidth rules', self._EditDefaultBandwidthRules )
        
        self._reset_default_bandwidth_rules_button = ClientGUICommon.BetterButton( self, 'reset default bandwidth rules', self._ResetDefaultBandwidthRules )
        
        default_rules_help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowDefaultRulesHelp )
        default_rules_help_button.SetToolTip( 'Show help regarding default bandwidth rules.' )
        
        self._delete_record_button = ClientGUICommon.BetterButton( self, 'delete selected history', self._DeleteNetworkContexts )
        
        #
        
        last_review_bandwidth_search_distance = self._controller.new_options.GetNoneableInteger( 'last_review_bandwidth_search_distance' )
        
        if last_review_bandwidth_search_distance is None:
            
            self._history_time_delta_threshold.SetValue( 86400 * 7 )
            self._history_time_delta_threshold.Disable()
            
            self._history_time_delta_none.SetValue( True )
            
        else:
            
            self._history_time_delta_threshold.SetValue( last_review_bandwidth_search_distance )
            
        
        self._bandwidths.Sort( 0 )
        
        self._update_job = HG.client_controller.CallRepeatingWXSafe( self, 0.5, 5.0, self._Update )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( ClientGUICommon.BetterStaticText( self, 'Show network contexts with usage in the past: ' ), CC.FLAGS_VCENTER )
        hbox.Add( self._history_time_delta_threshold, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._history_time_delta_none, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._edit_default_bandwidth_rules_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._reset_default_bandwidth_rules_button, CC.FLAGS_VCENTER )
        button_hbox.Add( default_rules_help_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._delete_record_button, CC.FLAGS_VCENTER )
        
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._bandwidths, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertNetworkContextsToListCtrlTuples( self, network_context ):
        
        bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( network_context )
        
        has_rules = not self._controller.network_engine.bandwidth_manager.UsesDefaultRules( network_context )
        
        sortable_network_context = ( network_context.context_type, network_context.context_data )
        sortable_context_type = CC.network_context_type_string_lookup[ network_context.context_type ]
        current_usage = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        day_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 86400 )
        day_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 86400 )
        
        day_usage = ( day_usage_data, day_usage_requests )
        
        month_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None )
        month_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
        
        month_usage = ( month_usage_data, month_usage_requests )
        
        if self._history_time_delta_none.GetValue():
            
            search_usage = 0
            pretty_search_usage = ''
            
        else:
            
            search_delta = self._history_time_delta_threshold.GetValue()
            
            search_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, search_delta )
            search_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, search_delta )
            
            search_usage = ( search_usage_data, search_usage_requests )
            
            pretty_search_usage = HydrusData.ToHumanBytes( search_usage_data ) + ' in ' + HydrusData.ToHumanInt( search_usage_requests ) + ' requests'
            
        
        pretty_network_context = network_context.ToString()
        pretty_context_type = CC.network_context_type_string_lookup[ network_context.context_type ]
        
        if current_usage == 0:
            
            pretty_current_usage = ''
            
        else:
            
            pretty_current_usage = HydrusData.ToHumanBytes( current_usage ) + '/s'
            
        
        pretty_day_usage = HydrusData.ToHumanBytes( day_usage_data ) + ' in ' + HydrusData.ToHumanInt( day_usage_requests ) + ' requests'
        pretty_month_usage = HydrusData.ToHumanBytes( month_usage_data ) + ' in ' + HydrusData.ToHumanInt( month_usage_requests ) + ' requests'
        
        if has_rules:
            
            pretty_has_rules = 'yes'
            
        else:
            
            pretty_has_rules = ''
            
        
        ( waiting_estimate, network_context_gumpf ) = self._controller.network_engine.bandwidth_manager.GetWaitingEstimateAndContext( [ network_context ] )
        
        if waiting_estimate > 0:
            
            pretty_blocked = HydrusData.TimeDeltaToPrettyTimeDelta( waiting_estimate )
            
        else:
            
            pretty_blocked = ''
            
        
        display_tuple = ( pretty_network_context, pretty_context_type, pretty_current_usage, pretty_day_usage, pretty_search_usage, pretty_month_usage, pretty_has_rules, pretty_blocked )
        sort_tuple = ( sortable_network_context, sortable_context_type, current_usage, day_usage, search_usage, month_usage, has_rules, waiting_estimate )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteNetworkContexts( self ):
        
        selected_network_contexts = self._bandwidths.GetData( only_selected = True )
        
        if len( selected_network_contexts ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Are you sure? This will delete all bandwidth record for the selected network contexts.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._controller.network_engine.bandwidth_manager.DeleteHistory( selected_network_contexts )
                    
                    self._update_job.Wake()
                    
                
        
    
    def _EditDefaultBandwidthRules( self ):
        
        network_contexts_and_bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetDefaultRules()
        
        choice_tuples = [ ( network_context.ToString() + ' (' + str( len( bandwidth_rules.GetRules() ) ) + ' rules)', ( network_context, bandwidth_rules ) ) for ( network_context, bandwidth_rules ) in network_contexts_and_bandwidth_rules ]
        
        try:
            
            ( network_context, bandwidth_rules ) = ClientGUIDialogsQuick.SelectFromList( self, 'select network context', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit bandwidth rules for ' + network_context.ToString() ) as dlg_2:
            
            summary = network_context.GetSummary()
            
            panel = ClientGUIScrolledPanelsEdit.EditBandwidthRulesPanel( dlg_2, bandwidth_rules, summary )
            
            dlg_2.SetPanel( panel )
            
            if dlg_2.ShowModal() == wx.ID_OK:
                
                bandwidth_rules = panel.GetValue()
                
                self._controller.network_engine.bandwidth_manager.SetRules( network_context, bandwidth_rules )
                
            
        
    
    def _ResetDefaultBandwidthRules( self ):
        
        message = 'Reset your \'default\' and \'global\' bandwidth rules to default?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                ClientDefaults.SetDefaultBandwidthManagerRules( self._controller.network_engine.bandwidth_manager )
                
            
        
    
    def _ShowDefaultRulesHelp( self ):
        
        help = 'Network requests act in multiple contexts. Most use the \'global\' and \'web domain\' network contexts, but a hydrus server request, for instance, will add its own service-specific context, and a subscription will add both itself and its downloader.'
        help += os.linesep * 2
        help += 'If a network context does not have some specific rules set up, it will use its respective default, which may or may not have rules of its own. If you want to set general policy, like "Never download more than 1GB/day from any individual website," or "Limit the entire client to 2MB/s," do it through \'global\' and these defaults.'
        help += os.linesep * 2
        help += 'All contexts\' rules are consulted and have to pass before a request can do work. If you set a 200KB/s limit on a website domain and a 50KB/s limit on global, your download will only ever run at 50KB/s. To make sense, network contexts with broader scope should have more lenient rules.'
        help += os.linesep * 2
        help += 'There are two special \'instance\' contexts, for downloaders and threads. These represent individual queries, either a single gallery search or a single watched thread. It is useful to set rules for these so your searches will gather a fast initial sample of results in the first few minutes--so you can make sure you are happy with them--but otherwise trickle the rest in over time. This keeps your CPU and other bandwidth limits less hammered and helps to avoid accidental downloads of many thousands of small bad files or a few hundred gigantic files all in one go.'
        help += os.linesep * 2
        help += 'Please note that this system bases its calendar dates on UTC/GMT time (it helps servers and clients around the world stay in sync a bit easier). This has no bearing on what, for instance, the \'past 24 hours\' means, but monthly transitions may occur a few hours off whatever your midnight is.'
        help += os.linesep * 2
        help += 'If you do not understand what is going on here, you can safely leave it alone. The default settings make for a _reasonable_ and polite profile that will not accidentally cause you to download way too much in one go or piss off servers by being too aggressive. If you want to throttle your client, the simplest way is to add a simple rule like \'500MB per day\' to the global context.'
        wx.MessageBox( help )
        
    
    def _Update( self ):
        
        if self._history_time_delta_none.GetValue() == True:
            
            history_time_delta_threshold = None
            
        else:
            
            history_time_delta_threshold = self._history_time_delta_threshold.GetValue()
            
        
        network_contexts = self._controller.network_engine.bandwidth_manager.GetNetworkContextsForUser( history_time_delta_threshold )
        
        self._bandwidths.SetData( network_contexts )
        
        timer_duration_s = max( len( network_contexts ), 20 )
        
    
    def EventTimeDeltaChanged( self, event ):
        
        if self._history_time_delta_none.GetValue() == True:
            
            self._history_time_delta_threshold.Disable()
            
            last_review_bandwidth_search_distance = None
            
        else:
            
            self._history_time_delta_threshold.Enable()
            
            last_review_bandwidth_search_distance = self._history_time_delta_threshold.GetValue()
            
        
        self._controller.new_options.SetNoneableInteger( 'last_review_bandwidth_search_distance', last_review_bandwidth_search_distance )
        
        self._update_job.Wake()
        
    
    def ShowNetworkContext( self ):
        
        for network_context in self._bandwidths.GetData( only_selected = True ):
            
            parent = self.GetTopLevelParent().GetParent()
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( parent, 'review bandwidth for ' + network_context.ToString() )
            
            panel = ReviewNetworkContextBandwidthPanel( frame, self._controller, network_context )
            
            frame.SetPanel( panel )
            
        
    
class ReviewDownloaderImport( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_engine = network_engine
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'adding_new_downloaders.html' ) )
        
        menu_items.append( ( 'normal', 'open the easy downloader import help', 'Open the help page for easily importing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        st = ClientGUICommon.BetterStaticText( self, label = 'Drop downloader-encoded pngs onto Lain to import.' )
        
        lain_path = os.path.join( HC.STATIC_DIR, 'lain.jpg' )
        
        lain_bmp = ClientRendering.GenerateHydrusBitmap( lain_path, HC.IMAGE_JPEG ).GetWxBitmap()
        
        win = ClientGUICommon.BufferedWindowIcon( self, lain_bmp )
        
        win.SetCursor( wx.Cursor( wx.CURSOR_HAND ) )
        
        self._select_from_list = wx.CheckBox( self )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._select_from_list.SetValue( True )
            
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( st, CC.FLAGS_CENTER )
        vbox.Add( win, CC.FLAGS_CENTER )
        vbox.Add( ClientGUICommon.WrapInText( self._select_from_list, self, 'select objects from list' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        win.SetDropTarget( ClientDragDrop.FileDropTarget( self, filenames_callable = self.ImportFromDragDrop ) )
        
        win.Bind( wx.EVT_LEFT_DOWN, self.EventLainClick )
        
    
    def _ImportPaths( self, paths ):
        
        gugs = []
        url_classes = []
        parsers = []
        domain_metadatas = []
        login_scripts = []
        
        num_misc_objects = 0
        
        bandwidth_manager = self._network_engine.bandwidth_manager
        domain_manager = self._network_engine.domain_manager
        login_manager = self._network_engine.login_manager
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPng( path )
                
            except Exception as e:
                
                wx.MessageBox( str( e ) )
                
                return
                
            
            try:
                
                obj_list = HydrusSerialisable.CreateFromNetworkBytes( payload )
                
            except:
                
                wx.MessageBox( 'I could not understand what was encoded in the file ' + path + '!' )
                
                continue
                
            
            if isinstance( obj_list, ( ClientNetworkingDomain.GalleryURLGenerator, ClientNetworkingDomain.NestedGalleryURLGenerator, ClientNetworkingDomain.URLClass, ClientParsing.PageParser, ClientNetworkingDomain.DomainMetadataPackage, ClientNetworkingLogin.LoginScriptDomain ) ):
                
                obj_list = HydrusSerialisable.SerialisableList( [ obj_list ] )
                
            
            if not isinstance( obj_list, HydrusSerialisable.SerialisableList ):
                
                wx.MessageBox( 'Unfortunately, ' + path + ' did not look like a package of download data! Instead, it looked like: ' + obj_list.SERIALISABLE_NAME )
                
                continue
                
            
            for obj in obj_list:
                
                if isinstance( obj, ( ClientNetworkingDomain.GalleryURLGenerator, ClientNetworkingDomain.NestedGalleryURLGenerator ) ):
                    
                    gugs.append( obj )
                    
                elif isinstance( obj, ClientNetworkingDomain.URLClass ):
                    
                    url_classes.append( obj )
                    
                elif isinstance( obj, ClientParsing.PageParser ):
                    
                    parsers.append( obj )
                    
                elif isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ):
                    
                    domain_metadatas.append( obj )
                    
                elif isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ):
                    
                    login_scripts.append( obj )
                    
                else:
                    
                    num_misc_objects += 1
                    
                
            
        
        if len( obj_list ) - num_misc_objects == 0:
            
            if num_misc_objects > 0:
                
                wx.MessageBox( 'I found ' + HydrusData.ToHumanInt( num_misc_objects ) + ' misc objects in that png, but nothing downloader related.' )
                
            
            return
            
        
        # url matches first
        
        url_class_names_seen = set()
        
        dupe_url_classes = []
        num_exact_dupe_url_classes = 0
        new_url_classes = []
        
        for url_class in url_classes:
            
            if url_class.GetName() in url_class_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisURLClass( url_class ):
                
                dupe_url_classes.append( url_class )
                num_exact_dupe_url_classes += 1
                
            else:
                
                new_url_classes.append( url_class )
                
                url_class_names_seen.add( url_class.GetName() )
                
            
        
        # now gugs
        
        gug_names_seen = set()
        
        num_exact_dupe_gugs = 0
        new_gugs = []
        
        for gug in gugs:
            
            if gug.GetName() in gug_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisGUG( gug ):
                
                num_exact_dupe_gugs += 1
                
            else:
                
                new_gugs.append( gug )
                
                gug_names_seen.add( gug.GetName() )
                
            
        
        # now parsers
        
        parser_names_seen = set()
        
        num_exact_dupe_parsers = 0
        new_parsers = []
        
        for parser in parsers:
            
            if parser.GetName() in parser_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisParser( parser ):
                
                num_exact_dupe_parsers += 1
                
            else:
                
                new_parsers.append( parser )
                
                parser_names_seen.add( parser.GetName() )
                
            
        
        # now login scripts
        
        login_script_names_seen = set()
        
        num_exact_dupe_login_scripts = 0
        new_login_scripts = []
        
        for login_script in login_scripts:
            
            if login_script.GetName() in login_script_names_seen:
                
                continue
                
            
            if login_manager.AlreadyHaveExactlyThisLoginScript( login_script ):
                
                num_exact_dupe_login_scripts += 1
                
            else:
                
                new_login_scripts.append( login_script )
                
                login_script_names_seen.add( login_script.GetName() )
                
            
        
        # now domain metadata
        
        domains_seen = set()
        
        num_exact_dupe_domain_metadatas = 0
        new_domain_metadatas = []
        
        for domain_metadata in domain_metadatas:
            
            # check if the headers or rules are new, discarding any dupe content
            
            domain = domain_metadata.GetDomain()
            headers_list = None
            bandwidth_rules = None
            
            if domain in domains_seen:
                
                continue
                
            
            nc = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
            
            if domain_metadata.HasHeaders():
                
                headers_list = domain_metadata.GetHeaders()
                
                if domain_manager.AlreadyHaveExactlyTheseHeaders( nc, headers_list ):
                    
                    headers_list = None
                    
                
            
            if domain_metadata.HasBandwidthRules():
                
                bandwidth_rules = domain_metadata.GetBandwidthRules()
                
                if bandwidth_manager.AlreadyHaveExactlyTheseBandwidthRules( nc, bandwidth_rules ):
                    
                    bandwidth_rules = None
                    
                
            
            if headers_list is None and bandwidth_rules is None:
                
                num_exact_dupe_domain_metadatas += 1
                
            else:
                
                new_dm = ClientNetworkingDomain.DomainMetadataPackage( domain = domain, headers_list = headers_list, bandwidth_rules = bandwidth_rules )
                
                new_domain_metadatas.append( new_dm )
                
                domains_seen.add( domain )
                
            
        
        #
        
        total_num_dupes = num_exact_dupe_gugs + num_exact_dupe_url_classes + num_exact_dupe_parsers + num_exact_dupe_domain_metadatas + num_exact_dupe_login_scripts
        
        if len( new_gugs ) + len( new_url_classes ) + len( new_parsers ) + len( new_domain_metadatas ) + len( new_login_scripts ) == 0:
            
            wx.MessageBox( 'All ' + HydrusData.ToHumanInt( total_num_dupes ) + ' downloader objects in that package appeared to already be in the client, so nothing need be added.' )
            
            return
            
        
        # let's start selecting what we want
        
        if self._select_from_list.GetValue() == True:
            
            choice_tuples = []
            choice_tuples.extend( [ ( 'GUG: ' + gug.GetName(), gug, True ) for gug in new_gugs ] )
            choice_tuples.extend( [ ( 'URL Class: ' + url_class.GetName(), url_class, True ) for url_class in new_url_classes ] )
            choice_tuples.extend( [ ( 'Parser: ' + parser.GetName(), parser, True ) for parser in new_parsers ] )
            choice_tuples.extend( [ ( 'Login Script: ' + login_script.GetName(), login_script, True ) for login_script in new_login_scripts ] )
            choice_tuples.extend( [ ( 'Domain Metadata: ' + domain_metadata.GetDomain(), domain_metadata, True ) for domain_metadata in new_domain_metadatas ] )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'select objects to add' ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    new_objects = panel.GetValue()
                    
                    new_gugs = [ obj for obj in new_objects if isinstance( obj, ( ClientNetworkingDomain.GalleryURLGenerator, ClientNetworkingDomain.NestedGalleryURLGenerator ) ) ]
                    new_url_classes = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingDomain.URLClass ) ]
                    new_parsers = [ obj for obj in new_objects if isinstance( obj, ClientParsing.PageParser ) ]
                    new_login_scripts = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ) ]
                    new_domain_metadatas = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ) ]
                    
                else:
                    
                    return
                    
                
            
        
        # final ask
        
        new_gugs.sort( key = lambda o: o.GetName() )
        new_url_classes.sort( key = lambda o: o.GetName() )
        new_parsers.sort( key = lambda o: o.GetName() )
        new_login_scripts.sort( key = lambda o: o.GetName() )
        new_domain_metadatas.sort( key = lambda o: o.GetDomain() )
        
        if len( new_domain_metadatas ) > 0:
            
            message = 'Before the final import confirmation, I will now show the domain metadata in detail. Give it a cursory look just to check it seems good. If not, click no on the final dialog!'
            
            TOO_MANY_DM = 8
            
            if len( new_domain_metadatas ) > TOO_MANY_DM:
                
                message += os.linesep * 2
                message += 'There are more than ' + HydrusData.ToHumanInt( TOO_MANY_DM ) + ' domain metadata objects. So I do not give you dozens of preview windows, I will only show you these first ' + HydrusData.ToHumanInt( TOO_MANY_DM ) + '.'
                
            
            new_domain_metadatas_to_show = new_domain_metadatas[:TOO_MANY_DM]
            
            for new_dm in new_domain_metadatas_to_show:
                
                wx.MessageBox( new_dm.GetDetailedSafeSummary() )
                
            
        
        all_to_add = list( new_gugs )
        all_to_add.extend( new_url_classes )
        all_to_add.extend( new_parsers )
        all_to_add.extend( new_login_scripts )
        all_to_add.extend( new_domain_metadatas )
        
        message = 'The client is about to add and link these objects:'
        message += os.linesep * 2
        message += os.linesep.join( ( obj.GetSafeSummary() for obj in all_to_add[:20] ) )
        
        if len( all_to_add ) > 20:
            
            message += os.linesep
            message += '(and ' + HydrusData.ToHumanInt( len( all_to_add ) - 20 ) + ' others)'
            
        
        message += os.linesep * 2
        message += 'Does that sound good?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
        # ok, do it
        
        if len( new_gugs ) > 0:
            
            domain_manager.AddGUGs( new_gugs )
            
        
        domain_manager.AutoAddURLClassesAndParsers( new_url_classes, dupe_url_classes, new_parsers )
        
        bandwidth_manager.AutoAddDomainMetadatas( new_domain_metadatas )
        domain_manager.AutoAddDomainMetadatas( new_domain_metadatas, approved = True )
        login_manager.AutoAddLoginScripts( new_login_scripts )
        
        num_new_gugs = len( new_gugs )
        num_aux = len( new_url_classes ) + len( new_parsers ) + len( new_login_scripts ) + len( new_domain_metadatas )
        
        final_message = 'Successfully added ' + HydrusData.ToHumanInt( num_new_gugs ) + ' new downloaders and ' + HydrusData.ToHumanInt( num_aux ) + ' auxiliary objects.'
        
        if total_num_dupes > 0:
            
            final_message += ' ' + HydrusData.ToHumanInt( total_num_dupes ) + ' duplicate objects were not added (but some additional metadata may have been merged).'
            
        
        wx.MessageBox( final_message )
        
    
    def EventLainClick( self, event ):
        
        with wx.FileDialog( self, 'Select the pngs to add.', style = wx.FD_OPEN | wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = dlg.GetPaths()
                
                self._ImportPaths( paths )
                
            
        
    
    def ImportFromDragDrop( self, paths ):
        
        self._ImportPaths( paths )
        
    
class ReviewFileMaintenance( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, stats ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._hash_ids = None
        self._job_types_to_counts = {}
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._current_work_panel = wx.Panel( self._notebook )
        
        jobs_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._current_work_panel )
        
        columns = [ ( 'job type', -1 ), ( 'scheduled jobs', 16 ) ]
        
        self._jobs_listctrl = ClientGUIListCtrl.BetterListCtrl( jobs_listctrl_panel, 'file maintenance jobs', 8, 48, columns, self._ConvertJobTypeToListCtrlTuples )
        
        jobs_listctrl_panel.SetListCtrl( self._jobs_listctrl )
        
        jobs_listctrl_panel.AddButton( 'clear', self._DeleteWork, enabled_only_on_selection = True )
        jobs_listctrl_panel.AddButton( 'do work', self._DoWork, enabled_only_on_selection = True )
        jobs_listctrl_panel.AddButton( 'do all work', self._DoAllWork, enabled_check_func = self._WorkToDo )
        jobs_listctrl_panel.AddButton( 'refresh', self._RefreshWorkDue )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( jobs_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._current_work_panel.SetSizer( vbox )
        
        #
        
        self._new_work_panel = wx.Panel( self._notebook )
        
        #
        
        self._search_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'select files by search' )
        
        page_key = HydrusData.GenerateKey()
        
        self._current_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._search_panel, page_key, [] )
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
        
        self._tag_ac_input = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, page_key, file_search_context )
        
        self._run_search_st = ClientGUICommon.BetterStaticText( self._search_panel, label = 'no results yet' )
        
        self._run_search = ClientGUICommon.BetterButton( self._search_panel, 'run this search', self._RunSearch )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._run_search_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._run_search, CC.FLAGS_VCENTER )
        
        self._search_panel.Add( self._current_predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._search_panel.Add( self._tag_ac_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._search_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._button_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'select special files' )
        
        self._select_repo_files = ClientGUICommon.BetterButton( self._button_panel, 'all repository update files', self._SelectRepoUpdateFiles )
        
        self._button_panel.Add( self._select_repo_files, CC.FLAGS_LONE_BUTTON )
        
        #
        
        self._action_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'add job' )
        
        self._selected_files_st = ClientGUICommon.BetterStaticText( self._action_panel, label = 'no files selected yet' )
        
        self._action_selector = ClientGUICommon.BetterChoice( self._action_panel )
        
        for job_type in ClientFiles.ALL_REGEN_JOBS_IN_PREFERRED_ORDER:
            
            self._action_selector.Append( ClientFiles.regen_file_enum_to_str_lookup[ job_type ], job_type )
            
        
        self._add_new_job = ClientGUICommon.BetterButton( self._action_panel, 'add job', self._AddJob )
        
        self._add_new_job.Disable()
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._selected_files_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._action_selector, CC.FLAGS_VCENTER )
        hbox.Add( self._add_new_job, CC.FLAGS_VCENTER )
        
        self._action_panel.Add( hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._button_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._action_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._new_work_panel.SetSizer( vbox )
        
        #
        
        self._notebook.AddPage( self._current_work_panel, 'scheduled work' )
        self._notebook.AddPage( self._new_work_panel, 'add new work' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._RefreshWorkDue()
        
        HG.client_controller.sub( self, '_RefreshWorkDue', 'notify_files_maintenance_done' )
        
    
    def _AddJob( self ):
        
        def wx_done():
            
            if not self:
                
                return
                
            
            wx.MessageBox( 'Jobs added!' )
            
            self._add_new_job.Enable()
            
            self._RefreshWorkDue()
            
        
        def do_it( hash_ids, job_type ):
            
            HG.client_controller.WriteSynchronous( 'file_maintenance_add_jobs', hash_ids, job_type )
            
            wx.CallAfter( wx_done )
            
        
        hash_ids = self._hash_ids
        job_type = self._action_selector.GetChoice()
        
        if len( hash_ids ) > 1000:
            
            message = 'Are you sure you want to schedule "{}" on {} files?'.format( ClientFiles.regen_file_enum_to_str_lookup[ job_type ], HydrusData.ToHumanInt( len( hash_ids ) ) )
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return
                    
                
            
        
        self._add_new_job.Disable()
        
        HG.client_controller.CallToThread( do_it, hash_ids, job_type )
        
    
    def _ConvertJobTypeToListCtrlTuples( self, job_type ):
        
        pretty_job_type = ClientFiles.regen_file_enum_to_str_lookup[ job_type ]
        sort_job_type = pretty_job_type
        
        if job_type in self._job_types_to_counts:
            
            num_to_do = self._job_types_to_counts[ job_type ]
            
        else:
            
            num_to_do = 0
            
        
        pretty_num_to_do = HydrusData.ToHumanInt( num_to_do )
        
        display_tuple = ( pretty_job_type, pretty_num_to_do )
        sort_tuple = ( sort_job_type, num_to_do )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteWork( self ):
        
        def wx_done():
            
            if not self:
                
                return
                
            
            self._RefreshWorkDue()
            
        
        def do_it( job_types ):
            
            for job_type in job_types:
                
                HG.client_controller.WriteSynchronous( 'file_maintenance_cancel_jobs', job_type )
                
            
            wx.CallAfter( wx_done )
            
        
        message = 'Clear all the selected scheduled work?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        HG.client_controller.CallToThread( do_it, job_types )
        
    
    def _DoAllWork( self ):
        
        HG.client_controller.CallToThread( HG.client_controller.files_maintenance_manager.DoMaintenance, maintenance_mode = HC.MAINTENANCE_FORCED )
        
    
    def _DoWork( self ):
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        if len( job_types ) == 0:
            
            return
            
        
        HG.client_controller.CallToThread( HG.client_controller.files_maintenance_manager.DoMaintenance, mandated_job_types = job_types, maintenance_mode = HC.MAINTENANCE_FORCED )
        
    
    def _RefreshWorkDue( self ):
        
        def wx_done( job_types_to_counts ):
            
            if not self:
                
                return
                
            
            self._job_types_to_counts = job_types_to_counts
            
            job_types = list( job_types_to_counts.keys() )
            
            self._jobs_listctrl.SetData( job_types )
            
        
        def do_it():
            
            job_types_to_counts = HG.client_controller.Read( 'file_maintenance_get_job_counts' )
            
            wx.CallAfter( wx_done, job_types_to_counts )
            
        
        HG.client_controller.CallToThread( do_it )
        
    
    def _RunSearch( self ):
        
        def wx_done( hash_ids ):
            
            if not self:
                
                return
                
            
            self._run_search_st.SetLabelText( '{} files found'.format( HydrusData.ToHumanInt( len( hash_ids ) ) ) )
            
            self._run_search.Enable()
            
            self._SetHashIds( hash_ids )
            
        
        def do_it( fsc ):
            
            query_hash_ids = HG.client_controller.Read( 'file_query_ids', fsc )
            
            wx.CallAfter( wx_done, query_hash_ids )
            
        
        self._run_search_st.SetLabelText( 'loading\u2026' )
        
        self._run_search.Disable()
        
        file_search_context = self._tag_ac_input.GetFileSearchContext()
        
        current_predicates = self._current_predicates_box.GetPredicates()
        
        file_search_context.SetPredicates( current_predicates )
        
        HG.client_controller.CallToThread( do_it, file_search_context )
        
    
    def _SelectRepoUpdateFiles( self ):
        
        def wx_done( hash_ids ):
            
            if not self:
                
                return
                
            
            self._select_repo_files.Enable()
            
            self._SetHashIds( hash_ids )
            
        
        def do_it( fsc ):
            
            query_hash_ids = HG.client_controller.Read( 'file_query_ids', fsc )
            
            wx.CallAfter( wx_done, query_hash_ids )
            
        
        self._select_repo_files.Disable()
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_UPDATE_SERVICE_KEY )
        
        HG.client_controller.CallToThread( do_it, file_search_context )
        
    
    def _SetHashIds( self, hash_ids ):
        
        if hash_ids is None:
            
            hash_ids = set()
            
        
        self._hash_ids = hash_ids
        
        self._selected_files_st.SetLabelText( '{} files selected'.format( HydrusData.ToHumanInt( len( hash_ids ) ) ) )
        
        if len( hash_ids ) == 0:
            
            self._add_new_job.Disable()
            
        else:
            
            self._add_new_job.Enable()
            
        
    
    def _WorkToDo( self ):
        
        return len( self._job_types_to_counts ) > 0
        
    
class ReviewHowBonedAmI( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, stats ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        ( num_inbox, num_archive, size_inbox, size_archive, total_viewtime ) = stats
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        num_total = num_archive + num_inbox
        size_total = size_archive + size_inbox
        
        if num_total < 1000:
            
            get_more = ClientGUICommon.BetterStaticText( self, label = 'I hope you enjoy my software. You might like to check out the downloaders! :^)' )
            
            vbox.Add( get_more, CC.FLAGS_CENTER )
            
        elif num_inbox <= num_archive / 100:
            
            hooray = ClientGUICommon.BetterStaticText( self, label = 'CONGRATULATIONS, YOU APPEAR TO BE UNBONED, BUT REMAIN EVER VIGILANT' )
            
            vbox.Add( hooray, CC.FLAGS_CENTER )
            
        else:
            
            boned_path = os.path.join( HC.STATIC_DIR, 'boned.jpg' )
            
            boned_bmp = ClientRendering.GenerateHydrusBitmap( boned_path, HC.IMAGE_JPEG ).GetWxBitmap()
            
            win = ClientGUICommon.BufferedWindowIcon( self, boned_bmp )
            
            vbox.Add( win, CC.FLAGS_CENTER )
            
        
        if num_total == 0:
            
            nothing_label = 'You have yet to board the ride.'
            
            nothing_st = ClientGUICommon.BetterStaticText( self, label = nothing_label )
            
            vbox.Add( nothing_st, CC.FLAGS_CENTER )
            
        else:
            
            num_archive_percent = num_archive / num_total
            size_archive_percent = size_archive / size_total
            
            num_inbox_percent = num_inbox / num_total
            size_inbox_percent = size_inbox / size_total
            
            archive_label = 'Archive: ' + HydrusData.ToHumanInt( num_archive ) + ' files (' + ClientData.ConvertZoomToPercentage( num_archive_percent ) + '), totalling ' + HydrusData.ToHumanBytes( size_archive ) + '(' + ClientData.ConvertZoomToPercentage( size_archive_percent ) + ')'
            
            archive_st = ClientGUICommon.BetterStaticText( self, label = archive_label )
            
            inbox_label = 'Inbox: ' + HydrusData.ToHumanInt( num_inbox ) + ' files (' + ClientData.ConvertZoomToPercentage( num_inbox_percent ) + '), totalling ' + HydrusData.ToHumanBytes( size_inbox ) + '(' + ClientData.ConvertZoomToPercentage( size_inbox_percent ) + ')'
            
            inbox_st = ClientGUICommon.BetterStaticText( self, label = inbox_label )
            
            vbox.Add( archive_st, CC.FLAGS_CENTER )
            vbox.Add( inbox_st, CC.FLAGS_CENTER )
            
            ( media_views, media_viewtime, preview_views, preview_viewtime ) = total_viewtime
            
            media_label = 'Total media views: ' + HydrusData.ToHumanInt( media_views ) + ', totalling ' + HydrusData.TimeDeltaToPrettyTimeDelta( media_viewtime )
            
            media_st = ClientGUICommon.BetterStaticText( self, label = media_label )
            
            preview_label = 'Total preview views: ' + HydrusData.ToHumanInt( preview_views ) + ', totalling ' + HydrusData.TimeDeltaToPrettyTimeDelta( preview_viewtime )
            
            preview_st = ClientGUICommon.BetterStaticText( self, label = preview_label )
            
            vbox.Add( media_st, CC.FLAGS_CENTER )
            vbox.Add( preview_st, CC.FLAGS_CENTER )
            
        
        self.SetSizer( vbox )
        
    
class ReviewNetworkContextBandwidthPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller, network_context ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_context = network_context
        
        self._bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetRules( self._network_context )
        self._bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( self._network_context )
        
        self._last_fetched_rule_rows = set()
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'description' )
        
        description = CC.network_context_type_description_lookup[ self._network_context.context_type ]
        
        self._name = ClientGUICommon.BetterStaticText( info_panel, label = self._network_context.ToString() )
        self._description = ClientGUICommon.BetterStaticText( info_panel, label = description )
        
        #
        
        usage_panel = ClientGUICommon.StaticBox( self, 'usage' )
        
        self._current_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        self._time_delta_usage_bandwidth_type = ClientGUICommon.BetterChoice( usage_panel )
        self._time_delta_usage_time_delta = ClientGUITime.TimeDeltaButton( usage_panel, days = True, hours = True, minutes = True, seconds = True )
        self._time_delta_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        #
        
        rules_panel = ClientGUICommon.StaticBox( self, 'rules' )
        
        self._uses_default_rules_st = ClientGUICommon.BetterStaticText( rules_panel, style = wx.ALIGN_CENTER )
        
        self._rules_rows_panel = wx.Panel( rules_panel )
        
        self._use_default_rules_button = ClientGUICommon.BetterButton( rules_panel, 'use default rules', self._UseDefaultRules )
        self._edit_rules_button = ClientGUICommon.BetterButton( rules_panel, 'edit rules', self._EditRules )
        
        #
        
        self._time_delta_usage_time_delta.SetValue( 86400 )
        
        for bandwidth_type in ( HC.BANDWIDTH_TYPE_DATA, HC.BANDWIDTH_TYPE_REQUESTS ):
            
            self._time_delta_usage_bandwidth_type.Append( HC.bandwidth_type_string_lookup[ bandwidth_type ], bandwidth_type )
            
        
        self._time_delta_usage_bandwidth_type.SelectClientData( HC.BANDWIDTH_TYPE_DATA )
        
        monthly_usage = self._bandwidth_tracker.GetMonthlyDataUsage()
        
        if len( monthly_usage ) > 0:
            
            if MATPLOTLIB_OK:
                
                self._barchart_canvas = ClientGUIMatPlotLib.BarChartBandwidthHistory( usage_panel, monthly_usage )
                
            else:
                
                self._barchart_canvas = ClientGUICommon.BetterStaticText( usage_panel, 'Could not find matplotlib, so cannot display bar chart here.' )
                
            
        else:
            
            self._barchart_canvas = ClientGUICommon.BetterStaticText( usage_panel, 'No usage yet, so no usage history to show.' )
            
        
        #
        
        info_panel.Add( self._name, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._time_delta_usage_bandwidth_type, CC.FLAGS_VCENTER )
        hbox.Add( ClientGUICommon.BetterStaticText( usage_panel, ' in the past ' ), CC.FLAGS_VCENTER )
        hbox.Add( self._time_delta_usage_time_delta, CC.FLAGS_VCENTER )
        hbox.Add( self._time_delta_usage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        usage_panel.Add( self._current_usage_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        usage_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        usage_panel.Add( self._barchart_canvas, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._edit_rules_button, CC.FLAGS_SIZER_VCENTER )
        hbox.Add( self._use_default_rules_button, CC.FLAGS_SIZER_VCENTER )
        
        rules_panel.Add( self._uses_default_rules_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        rules_panel.Add( self._rules_rows_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        rules_panel.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( usage_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( rules_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._rules_job = HG.client_controller.CallRepeatingWXSafe( self, 0.5, 5.0, self._UpdateRules )
        
        self._update_job = HG.client_controller.CallRepeatingWXSafe( self, 0.5, 1.0, self._Update )
        
    
    def _EditRules( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit bandwidth rules for ' + self._network_context.ToString() ) as dlg:
            
            summary = self._network_context.GetSummary()
            
            panel = ClientGUIScrolledPanelsEdit.EditBandwidthRulesPanel( dlg, self._bandwidth_rules, summary )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._bandwidth_rules = panel.GetValue()
                
                self._controller.network_engine.bandwidth_manager.SetRules( self._network_context, self._bandwidth_rules )
                
                self._UpdateRules()
                
            
        
    
    def _Update( self ):
        
        current_usage = self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        pretty_current_usage = 'current usage: ' + HydrusData.ToHumanBytes( current_usage ) + '/s'
        
        self._current_usage_st.SetLabelText( pretty_current_usage )
        
        #
        
        bandwidth_type = self._time_delta_usage_bandwidth_type.GetChoice()
        time_delta = self._time_delta_usage_time_delta.GetValue()
        
        time_delta_usage = self._bandwidth_tracker.GetUsage( bandwidth_type, time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            converter = HydrusData.ToHumanBytes
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            converter = HydrusData.ToHumanInt
            
        
        pretty_time_delta_usage = ': ' + converter( time_delta_usage )
        
        self._time_delta_usage_st.SetLabelText( pretty_time_delta_usage )
        
    
    def _UpdateRules( self ):
        
        changes_made = False
        
        if self._network_context.IsDefault() or self._network_context == ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT:
            
            if self._use_default_rules_button.IsShown():
                
                self._uses_default_rules_st.Hide()
                self._use_default_rules_button.Hide()
                
                changes_made = True
                
            
        else:
            
            if self._controller.network_engine.bandwidth_manager.UsesDefaultRules( self._network_context ):
                
                self._uses_default_rules_st.SetLabelText( 'uses default rules' )
                
                self._edit_rules_button.SetLabel( 'set specific rules' )
                
                if self._use_default_rules_button.IsShown():
                    
                    self._use_default_rules_button.Hide()
                    
                    changes_made = True
                    
                
            else:
                
                self._uses_default_rules_st.SetLabelText( 'has its own rules' )
                
                self._edit_rules_button.SetLabel( 'edit rules' )
                
                if not self._use_default_rules_button.IsShown():
                    
                    self._use_default_rules_button.Show()
                    
                    changes_made = True
                    
                
            
        
        rule_rows = self._bandwidth_rules.GetBandwidthStringsAndGaugeTuples( self._bandwidth_tracker, threshold = 0 )
        
        if rule_rows != self._last_fetched_rule_rows:
            
            self._last_fetched_rule_rows = rule_rows
            
            self._rules_rows_panel.DestroyChildren()
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for ( status, ( v, r ) ) in rule_rows:
                
                tg = ClientGUICommon.TextAndGauge( self._rules_rows_panel )
                
                tg.SetValue( status, v, r )
                
                vbox.Add( tg, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            self._rules_rows_panel.SetSizer( vbox )
            
            changes_made = True
            
        
        if changes_made:
            
            self.Layout()
            
            ClientGUITopLevelWindows.PostSizeChangedEvent( self )
            
        
    
    def _UseDefaultRules( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to revert to using the default rules for this context?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.network_engine.bandwidth_manager.DeleteRules( self._network_context )
                
                self._rules_job.Wake()
                
            
        
    
class ReviewNetworkJobs( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'position', 20 ), ( 'url', -1 ), ( 'status', 40 ), ( 'current speed', 8 ), ( 'progress', 12 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, 'network jobs review', 20, 30, columns, self._ConvertDataToListCtrlTuples )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        # button to stop jobs en-masse
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        #
        
        self._list_ctrl.Sort( 0 )
        
        self._RefreshSnapshot()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, job_row ):
        
        ( network_engine_status, job ) = job_row
        
        position = network_engine_status
        url = job.GetURL()
        ( status, current_speed, num_bytes_read, num_bytes_to_read ) = job.GetStatus()
        progress = ( num_bytes_read, num_bytes_to_read )
        
        pretty_position = ClientNetworking.job_status_str_lookup[ position ]
        pretty_url = url
        pretty_status = status
        pretty_current_speed = HydrusData.ToHumanBytes( current_speed ) + '/s'
        pretty_progress = HydrusData.ConvertValueRangeToBytes( num_bytes_read, num_bytes_to_read )
        
        display_tuple = ( pretty_position, pretty_url, pretty_status, pretty_current_speed, pretty_progress )
        sort_tuple = ( position, url, status, current_speed, progress )
        
        return ( display_tuple, sort_tuple )
        
    
    def _RefreshSnapshot( self ):
        
        job_rows = self._controller.network_engine.GetJobsSnapshot()
        
        self._list_ctrl.SetData( job_rows )
        
    
class ReviewNetworkSessionsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, session_manager ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._session_manager = session_manager
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'network context', -1 ), ( 'cookies', 9 ), ( 'expires', 28 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'review_network_sessions', 32, 34, columns, self._ConvertNetworkContextToListCtrlTuples, delete_key_callback = self._Clear, activation_callback = self._Review )
        
        self._listctrl.Sort()
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'create new', self._Add )
        listctrl_panel.AddButton( 'import cookies.txt (drag and drop also works!)', self._ImportCookiesTXT )
        listctrl_panel.AddButton( 'review', self._Review, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'clear', self._Clear, enabled_only_on_selection = True )
        listctrl_panel.AddSeparator()
        listctrl_panel.AddButton( 'refresh', self._Update )
        
        listctrl_panel.SetDropTarget( ClientDragDrop.FileDropTarget( self, filenames_callable = self._ImportCookiesTXTPaths ) )
        
        self._show_empty = wx.CheckBox( self, label = 'show empty' )
        
        #
        
        self._Update()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._show_empty, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        self._show_empty.Bind( wx.EVT_CHECKBOX, self.EventShowEmpty )
        
    
    def _Add( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'enter new network context' ) as dlg:
            
            network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'example.com' )
            
            panel = ClientGUIScrolledPanelsEdit.EditNetworkContextPanel( dlg, network_context, limited_types = ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_HYDRUS ), allow_default = False )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                network_context = panel.GetValue()
                
                self._AddNetworkContext( network_context )
                
            
        
        self._show_empty.SetValue( True )
        
        self._Update()
        
    
    def _AddNetworkContext( self, network_context ):
        
        # this establishes a bare session
        
        self._session_manager.GetSession( network_context )
        
    
    def _Clear( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Clear these sessions? This will delete them completely.' ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
        for network_context in self._listctrl.GetData( only_selected = True ):
            
            self._session_manager.ClearSession( network_context )
            
        
        self._Update()
        
    
    def _ConvertNetworkContextToListCtrlTuples( self, network_context ):
        
        session = self._session_manager.GetSession( network_context )
        
        pretty_network_context = network_context.ToString()
        
        number_of_cookies = len( session.cookies )
        pretty_number_of_cookies = HydrusData.ToHumanInt( number_of_cookies )
        
        expires_numbers = [ c.expires for c in session.cookies if c.expires is not None ]
        
        if len( expires_numbers ) == 0:
            
            if number_of_cookies > 0:
                
                expiry = 0
                pretty_expiry = 'session'
                
            else:
                
                expiry = -1
                pretty_expiry = ''
                
            
        else:
            
            try:
                
                expiry = max( expires_numbers )
                pretty_expiry = HydrusData.ConvertTimestampToPrettyExpires( expiry )
                
            except:
                
                expiry = -1
                pretty_expiry = 'Unusual expiry numbers'
                
            
        
        display_tuple = ( pretty_network_context, pretty_number_of_cookies, pretty_expiry )
        sort_tuple = ( pretty_network_context, number_of_cookies, expiry )
        
        return ( display_tuple, sort_tuple )
        
    
    # this method is thanks to user prkc on the discord!
    def _ImportCookiesTXT( self ):
        
        with wx.FileDialog( self, 'select cookies.txt', style = wx.FD_OPEN ) as f_dlg:
            
            if f_dlg.ShowModal() == wx.ID_OK:
                
                path = f_dlg.GetPath()
                
                self._ImportCookiesTXTPaths( ( path, ) )
                
            
        
    
    def _ImportCookiesTXTPaths( self, paths ):
        
        num_added = 0
        
        for path in paths:
            
            cj = http.cookiejar.MozillaCookieJar()
            
            try:
                
                cj.load( path, ignore_discard = True, ignore_expires = True )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                wx.MessageBox( 'It looks like that cookies.txt failed to load. Unfortunately, not all formats are supported (for now!).' )
                
                return
                
            
            for cookie in cj:
                
                session = self._session_manager.GetSessionForDomain( cookie.domain )
                
                session.cookies.set_cookie( cookie )
                
                num_added += 1
                
            
        
        wx.MessageBox( 'Added ' + HydrusData.ToHumanInt( num_added ) + ' cookies!' )
        
        self._Update()
        
    
    def _Review( self ):
        
        for network_context in self._listctrl.GetData( only_selected = True ):
            
            parent = self.GetTopLevelParent().GetParent()
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( parent, 'review session for ' + network_context.ToString() )
            
            panel = ReviewNetworkSessionPanel( frame, self._session_manager, network_context )
            
            frame.SetPanel( panel )
            
        
    
    def _Update( self ):
        
        network_contexts = [ network_context for network_context in self._session_manager.GetNetworkContexts() if network_context.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_HYDRUS ) ]
        
        if not self._show_empty.GetValue():
            
            non_empty_network_contexts = []
            
            for network_context in network_contexts:
                
                session = self._session_manager.GetSession( network_context )
                
                if len( session.cookies ) > 0:
                    
                    non_empty_network_contexts.append( network_context )
                    
                
            
            network_contexts = non_empty_network_contexts
            
        
        self._listctrl.SetData( network_contexts )
        
    
    def EventShowEmpty( self, event ):
        
        self._Update()
        
    
class ReviewNetworkSessionPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, session_manager, network_context ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._session_manager = session_manager
        self._network_context = network_context
        
        self._session = self._session_manager.GetSession( self._network_context )
        
        self._description = ClientGUICommon.BetterStaticText( self, network_context.ToString() )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'value', 32 ), ( 'domain', 20 ), ( 'path', 8 ), ( 'expires', 28 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'review_network_session', 8, 18, columns, self._ConvertCookieToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._listctrl.Sort()
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'import cookies.txt (drag and drop also works!)', self._ImportCookiesTXT )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddDeleteButton()
        listctrl_panel.AddSeparator()
        listctrl_panel.AddButton( 'refresh', self._Update )
        
        listctrl_panel.SetDropTarget( ClientDragDrop.FileDropTarget( self, filenames_callable = self._ImportCookiesTXTPaths ) )
        
        #
        
        self._Update()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._description, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit cookie' ) as dlg:
            
            name = 'name'
            value = '123'
            
            if self._network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                domain = '.' + self._network_context.context_data
                
            else:
                
                domain = 'service domain'
                
            
            path = '/'
            expires = HydrusData.GetNow() + 30 * 86400
            
            panel = ClientGUIScrolledPanelsEdit.EditCookiePanel( dlg, name, value, domain, path, expires )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( name, value, domain, path, expires ) = panel.GetValue()
                
                self._SetCookie( name, value, domain, path, expires )
                
            
        
        self._Update()
        
    
    def _ConvertCookieToListCtrlTuples( self, cookie ):
        
        name = cookie.name
        pretty_name = name
        
        value = cookie.value
        pretty_value = value
        
        domain = cookie.domain
        pretty_domain = domain
        
        path = cookie.path
        pretty_path = path
        
        expiry = cookie.expires
        
        if expiry is None:
            
            pretty_expiry = 'session'
            
        else:
            
            pretty_expiry = HydrusData.ConvertTimestampToPrettyExpires( expiry )
            
        
        sort_expiry = ClientGUIListCtrl.SafeNoneInt( expiry )
        
        display_tuple = ( pretty_name, pretty_value, pretty_domain, pretty_path, pretty_expiry )
        sort_tuple = ( name, value, domain, path, sort_expiry )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Delete all selected cookies?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                for cookie in self._listctrl.GetData( only_selected = True ):
                    
                    domain = cookie.domain
                    path = cookie.path
                    name = cookie.name
                    
                    self._session.cookies.clear( domain, path, name )
                    
                
                self._Update()
                
            
        
    
    def _Edit( self ):
        
        for cookie in self._listctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit cookie' ) as dlg:
                
                name = cookie.name
                value = cookie.value
                domain = cookie.domain
                path = cookie.path
                expires = cookie.expires
                
                panel = ClientGUIScrolledPanelsEdit.EditCookiePanel( dlg, name, value, domain, path, expires )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( name, value, domain, path, expires ) = panel.GetValue()
                    
                    self._SetCookie( name, value, domain, path, expires )
                    
                else:
                    
                    break
                    
                
            
        
        self._Update()
        
    
    # these methods are thanks to user prkc on the discord!
    def _ImportCookiesTXT( self ):
        
        with wx.FileDialog( self, 'select cookies.txt', style = wx.FD_OPEN ) as f_dlg:
            
            if f_dlg.ShowModal() == wx.ID_OK:
                
                path = f_dlg.GetPath()
                
                self._ImportCookiesTXTPaths( ( path, ) )
                
            
        
    
    def _ImportCookiesTXTPaths( self, paths ):
        
        num_added = 0
        
        for path in paths:
            
            cj = http.cookiejar.MozillaCookieJar()
            
            try:
                
                cj.load( path, ignore_discard = True, ignore_expires = True )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                wx.MessageBox( 'It looks like that cookies.txt failed to load. Unfortunately, not all formats are supported (for now!).' )
                
                return
                
            
            for cookie in cj:
                
                self._session.cookies.set_cookie( cookie )
                
                num_added += 1
                
            
        
        wx.MessageBox( 'Added ' + HydrusData.ToHumanInt( num_added ) + ' cookies!' )
        
        self._Update()
        
    
    def _SetCookie( self, name, value, domain, path, expires ):
        
        version = 0
        port = None
        port_specified = False
        domain_specified = True
        domain_initial_dot = domain.startswith( '.' )
        path_specified = True
        secure = False
        discard = False
        comment = None
        comment_url = None
        rest = {}
        
        cookie = http.cookiejar.Cookie( version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest )
        
        self._session.cookies.set_cookie( cookie )
        
    
    def _Update( self ):
        
        self._session = self._session_manager.GetSession( self._network_context )
        
        cookies = list( self._session.cookies )
        
        self._listctrl.SetData( cookies )
        
    
class ReviewServicesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        self._local_notebook = ClientGUICommon.BetterNotebook( self._notebook )
        self._remote_notebook = ClientGUICommon.BetterNotebook( self._notebook )
        
        self._notebook.AddPage( self._local_notebook, 'local' )
        self._notebook.AddPage( self._remote_notebook, 'remote' )
        
        self._InitialiseServices()
        
        self.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventPageChanged )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_gui' )
        
    
    def _InitialiseServices( self ):
        
        lb = self._notebook.GetCurrentPage()
        
        if lb.GetPageCount() == 0:
            
            previous_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        else:
            
            page = lb.GetCurrentPage().GetCurrentPage()
            
            previous_service_key = page.GetServiceKey()
            
        
        self._local_notebook.DeleteAllPages()
        self._remote_notebook.DeleteAllPages()
        
        notebook_dict = {}
        
        services = self._controller.services_manager.GetServices( randomised = False )
        
        local_remote_notebook_to_select = None
        service_type_lb = None
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.LOCAL_SERVICES: parent_notebook = self._local_notebook
            else: parent_notebook = self._remote_notebook
            
            if service_type == HC.TAG_REPOSITORY: service_type_name = 'tag repositories'
            elif service_type == HC.FILE_REPOSITORY: service_type_name = 'file repositories'
            elif service_type == HC.MESSAGE_DEPOT: service_type_name = 'message depots'
            elif service_type == HC.SERVER_ADMIN: service_type_name = 'administrative servers'
            elif service_type in HC.LOCAL_FILE_SERVICES: service_type_name = 'files'
            elif service_type == HC.LOCAL_TAG: service_type_name = 'tags'
            elif service_type == HC.LOCAL_RATING_LIKE: service_type_name = 'like/dislike ratings'
            elif service_type == HC.LOCAL_RATING_NUMERICAL: service_type_name = 'numerical ratings'
            elif service_type == HC.LOCAL_BOORU: service_type_name = 'booru'
            elif service_type == HC.CLIENT_API_SERVICE: service_type_name = 'client api'
            elif service_type == HC.IPFS: service_type_name = 'ipfs'
            else: continue
            
            if service_type_name not in notebook_dict:
                
                services_notebook = ClientGUICommon.BetterNotebook( parent_notebook )
                
                notebook_dict[ service_type_name ] = services_notebook
                
                parent_notebook.AddPage( services_notebook, service_type_name, select = False )
                
            
            services_notebook = notebook_dict[ service_type_name ]
            
            page = ClientGUIPanels.ReviewServicePanel( services_notebook, service )
            
            if service.GetServiceKey() == previous_service_key:
                
                self._notebook.SelectPage( parent_notebook )
                parent_notebook.SelectPage( services_notebook )
                
                select = True
                
            else:
                
                select = False
                
            
            name = service.GetName()
            
            services_notebook.AddPage( page, name, select = select )
            
        
    
    def EventPageChanged( self, event ):
        
        ClientGUITopLevelWindows.PostSizeChangedEvent( self )
        
    
    def DoGetBestSize( self ):
        
        # this overrides the py stub in ScrolledPanel, which allows for unusual scroll behaviour driven by whatever this returns
        
        # wx.Notebook isn't expanding on page change and hence increasing min/virtual size and so on to the scrollable panel above, nullifying the neat expand-on-change-page event
        # so, until I write my own or figure out a clever solution, let's just force it
        
        if hasattr( self, '_notebook' ):
            
            current_page = self._notebook.GetCurrentPage()
            
            ( notebook_width, notebook_height ) = self._notebook.GetSize()
            ( page_width, page_height ) = current_page.GetSize()
            
            extra_width = notebook_width - page_width
            extra_height = notebook_height - page_height
            
            ( page_best_width, page_best_height ) = current_page.GetBestSize()
            
            best_size = ( page_best_width + extra_width, page_best_height + extra_height )
            
            return best_size
            
        else:
            
            return ( -1, -1 )
            
        
    
    def RefreshServices( self ):
        
        self._InitialiseServices()
        
    
class ReviewThreads( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', 24 ), ( 'type', 20 ), ( 'current job', -1 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, 'threads review', 20, 30, columns, self._ConvertDataToListCtrlTuples )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        # maybe some buttons to control behaviour here for debug
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        #
        
        self._list_ctrl.Sort( 0 )
        
        self._RefreshSnapshot()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, thread ):
        
        name = thread.GetName()
        thread_type = repr( type( thread ) )
        current_job = repr( thread.GetCurrentJobSummary() )
        
        pretty_name = name
        pretty_thread_type = thread_type
        pretty_current_job = current_job
        
        display_tuple = ( pretty_name, pretty_thread_type, pretty_current_job )
        sort_tuple = ( name, thread_type, current_job )
        
        return ( display_tuple, sort_tuple )
        
    
    def _RefreshSnapshot( self ):
        
        threads = self._controller.GetThreadsSnapshot()
        
        self._list_ctrl.SetData( threads )
        
    
