from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class FilesAndTrashPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        self._prefix_hash_when_copying = QW.QCheckBox( self )
        self._prefix_hash_when_copying.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you often paste hashes into boorus, check this to automatically prefix with the type, like "md5:2496dabcbd69e3c56a5d8caabb7acde5".' ) )
        
        self._delete_to_recycle_bin = QW.QCheckBox( self )
        
        self._ms_to_wait_between_physical_file_deletes = ClientGUITime.TimeDeltaWidget( self, min = 0.02, days = False, hours = False, minutes = False, seconds = True, milliseconds = True )
        tt = 'Deleting a file from a hard disk can be resource expensive, so when files leave the trash, the actual physical file delete happens later, in the background. The operation is spread out so as not to give you lag spikes.'
        self._ms_to_wait_between_physical_file_deletes.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._confirm_trash = QW.QCheckBox( self )
        self._confirm_archive = QW.QCheckBox( self )
        
        self._confirm_multiple_local_file_services_copy = QW.QCheckBox( self )
        self._confirm_multiple_local_file_services_move = QW.QCheckBox( self )
        
        self._only_show_delete_from_all_local_domains_when_filtering = QW.QCheckBox( self )
        tt = 'When you finish archive/delete filtering, if the files you chose to delete are in multiple local file domains, you are usually given the option of where you want to delete them from. If you always want to delete them from all locations and do not want the more complicated confirmation dialog, check this.'
        self._only_show_delete_from_all_local_domains_when_filtering.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._archive_delete_commit_panel_delays_multiple_delete_choices = QW.QCheckBox( self )
        tt = 'When you finish archive/delete filtering, if you have multiple choices for deletion domain, the final confirmation panel will not enable its buttons for a second or so, just to catch you from spamming enter through it too quickly. Disable this if you find it more annoying than helpful.'
        self._archive_delete_commit_panel_delays_multiple_delete_choices.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._remove_filtered_files = QW.QCheckBox( self )
        self._remove_filtered_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will remove all archived/deleted files from the source thumbnail page when you commit your archive/delete filter run.' ) )
        
        self._remove_filtered_files_even_when_skipped = QW.QCheckBox( self )
        self._remove_trashed_files = QW.QCheckBox( self )
        self._remove_local_domain_moved_files = QW.QCheckBox( self )
        
        # TODO: replace these with a new(?) noneabletimedelta and noneablebytesguy
        self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, 72, none_phrase = 'no age limit', min = 0, max = 8640 )
        self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, 2048, none_phrase = 'no size limit', min = 0, max = 20480 )
        
        self._do_not_do_chmod_mode = QW.QCheckBox( self )
        self._do_not_do_chmod_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'CAREFUL. When hydrus copies files around, it preserves or sets permission bits. If you are on ACL-backed storage, e.g. via NFSv4 with ACL set, chmod is going to raise errors and/or audit logspam. You can try stopping all chmod here--hydrus will use differing copy calls that only copy the file contents and try to preserve access/modified times.' ) )
        
        delete_lock_panel = ClientGUICommon.StaticBox( self, 'delete lock' )
        
        self._delete_lock_for_archived_files = QW.QCheckBox( delete_lock_panel )
        self._delete_lock_for_archived_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will stop the client from physically deleting anything you have archived. You can still trash such files, but they cannot go further. It is a last-ditch catch to rescue accidentally deleted good files.' ) )
        
        self._delete_lock_reinbox_deletees_after_archive_delete = QW.QCheckBox( delete_lock_panel )
        self._delete_lock_reinbox_deletees_after_archive_delete.setToolTip( ClientGUIFunctions.WrapToolTip( 'Be careful with this!\n\nIf the delete lock is on, and you do an archive/delete filter, this will ensure that all deletee files are inboxed before being deleted.' ) )
        
        self._delete_lock_reinbox_deletees_after_duplicate_filter = QW.QCheckBox( delete_lock_panel )
        self._delete_lock_reinbox_deletees_after_duplicate_filter.setToolTip( ClientGUIFunctions.WrapToolTip( 'Be careful with this!\n\nIf the delete lock is on, and you do a duplicate filter, this will ensure that all file delese you manually trigger and all file deletees that come from merge options are inboxed before being deleted.' ) )
        
        self._delete_lock_reinbox_deletees_in_auto_resolution = QW.QCheckBox( delete_lock_panel )
        self._delete_lock_reinbox_deletees_in_auto_resolution.setToolTip( ClientGUIFunctions.WrapToolTip( 'Be careful with this!\n\nIf the delete lock is on, any auto-resolution rule action, semi-automatic or automatic, will ensure that all deletee files from merge options are inboxed before being deleted.' ) )
        
        advanced_file_deletion_panel = ClientGUICommon.StaticBox( self, 'advanced file deletion and custom reasons' )
        
        self._use_advanced_file_deletion_dialog = QW.QCheckBox( advanced_file_deletion_panel )
        self._use_advanced_file_deletion_dialog.setToolTip( ClientGUIFunctions.WrapToolTip( 'If this is set, the client will present a more complicated file deletion confirmation dialog that will permit you to set your own deletion reason and perform \'clean\' deletes that leave no deletion record (making later re-import easier).' ) )
        
        self._remember_last_advanced_file_deletion_special_action = QW.QCheckBox( advanced_file_deletion_panel )
        self._remember_last_advanced_file_deletion_special_action.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will try to remember and restore the last action you set, whether that was trash, physical delete, or physical delete and clear history.') )
        
        self._remember_last_advanced_file_deletion_reason = QW.QCheckBox( advanced_file_deletion_panel )
        self._remember_last_advanced_file_deletion_reason.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will remember and restore the last reason you set for a delete.' ) )
        
        self._advanced_file_deletion_reasons = ClientGUIListBoxes.QueueListBox( advanced_file_deletion_panel, 5, str, add_callable = self._AddAFDR, edit_callable = self._EditAFDR )
        
        #
        
        self._prefix_hash_when_copying.setChecked( self._new_options.GetBoolean( 'prefix_hash_when_copying' ) )
        
        self._delete_to_recycle_bin.setChecked( HC.options[ 'delete_to_recycle_bin' ] )
        
        self._ms_to_wait_between_physical_file_deletes.SetValue( HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'ms_to_wait_between_physical_file_deletes' ) ) )
        
        self._confirm_trash.setChecked( HC.options[ 'confirm_trash' ] )
        tt = 'If there is only one place to delete the file from, you will get no delete dialog--it will just be deleted immediately. Applies the same way to undelete.'
        self._confirm_trash.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._confirm_archive.setChecked( HC.options[ 'confirm_archive' ] )
        
        self._confirm_multiple_local_file_services_copy.setChecked( self._new_options.GetBoolean( 'confirm_multiple_local_file_services_copy' ) )
        self._confirm_multiple_local_file_services_move.setChecked( self._new_options.GetBoolean( 'confirm_multiple_local_file_services_move' ) )
        
        self._only_show_delete_from_all_local_domains_when_filtering.setChecked( self._new_options.GetBoolean( 'only_show_delete_from_all_local_domains_when_filtering' ) )
        self._archive_delete_commit_panel_delays_multiple_delete_choices.setChecked( self._new_options.GetBoolean( 'archive_delete_commit_panel_delays_multiple_delete_choices' ) )
        
        self._remove_filtered_files.setChecked( HC.options[ 'remove_filtered_files' ] )
        self._remove_filtered_files_even_when_skipped.setChecked( self._new_options.GetBoolean( 'remove_filtered_files_even_when_skipped' ) )
        self._remove_trashed_files.setChecked( HC.options[ 'remove_trashed_files' ] )
        self._remove_local_domain_moved_files.setChecked( self._new_options.GetBoolean( 'remove_local_domain_moved_files' ) )
        self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
        self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
        
        self._do_not_do_chmod_mode.setChecked( self._new_options.GetBoolean( 'do_not_do_chmod_mode' ) )
        
        self._delete_lock_for_archived_files.setChecked( self._new_options.GetBoolean( 'delete_lock_for_archived_files' ) )
        self._delete_lock_reinbox_deletees_after_archive_delete.setChecked( self._new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_archive_delete' ) )
        self._delete_lock_reinbox_deletees_after_duplicate_filter.setChecked( self._new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter' ) )
        self._delete_lock_reinbox_deletees_in_auto_resolution.setChecked( self._new_options.GetBoolean( 'delete_lock_reinbox_deletees_in_auto_resolution' ) )
        
        self._use_advanced_file_deletion_dialog.setChecked( self._new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ) )
        
        self._remember_last_advanced_file_deletion_special_action.setChecked( CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ) )
        self._remember_last_advanced_file_deletion_reason.setChecked( CG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ) )
        
        self._advanced_file_deletion_reasons.AddDatas( self._new_options.GetStringList( 'advanced_file_deletion_reasons' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_CENTER )
        
        rows = []
        
        rows.append( ( 'When copying file hashes, prefix with booru-friendly hash type: ', self._prefix_hash_when_copying ) )
        rows.append( ( 'Confirm sending files to trash: ', self._confirm_trash ) )
        rows.append( ( 'Confirm sending more than one file to archive or inbox: ', self._confirm_archive ) )
        rows.append( ( 'Confirm when copying files across local file domains: ', self._confirm_multiple_local_file_services_copy ) )
        rows.append( ( 'Confirm when moving files across local file domains: ', self._confirm_multiple_local_file_services_move ) )
        rows.append( ( 'When physically deleting files or folders, send them to the OS\'s recycle bin: ', self._delete_to_recycle_bin ) )
        rows.append( ( 'When maintenance physically deletes files, wait this long between each delete: ', self._ms_to_wait_between_physical_file_deletes ) )
        rows.append( ( 'When finishing archive/delete filtering, always delete from all possible domains: ', self._only_show_delete_from_all_local_domains_when_filtering ) )
        rows.append( ( 'When finishing archive/delete filtering, delay activation of multiple deletion choice buttons: ', self._archive_delete_commit_panel_delays_multiple_delete_choices ) )
        rows.append( ( 'Remove files from view when they are archive/delete filtered: ', self._remove_filtered_files ) )
        rows.append( ( '--even skipped files: ', self._remove_filtered_files_even_when_skipped ) )
        rows.append( ( 'Remove files from view when they are sent to the trash: ', self._remove_trashed_files ) )
        rows.append( ( 'Remove files from view when they are moved to another local file domain: ', self._remove_local_domain_moved_files ) )
        rows.append( ( 'Number of hours a file can be in the trash before being deleted: ', self._trash_max_age ) )
        rows.append( ( 'Maximum size of trash (MB): ', self._trash_max_size ) )
        rows.append( ( 'ADVANCED: Do not do chmod when copying files', self._do_not_do_chmod_mode ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Do not permit archived files to be deleted from the trash: ', self._delete_lock_for_archived_files ) )
        rows.append( ( 'After archive/delete filter, ensure deletees are inboxed before delete: ', self._delete_lock_reinbox_deletees_after_archive_delete ) )
        rows.append( ( 'After duplicate filter, ensure deletees are inboxed before delete: ', self._delete_lock_reinbox_deletees_after_duplicate_filter ) )
        rows.append( ( 'In duplicates auto-resolution, ensure deletees are inboxed before delete: ', self._delete_lock_reinbox_deletees_in_auto_resolution ) )
        
        gridbox = ClientGUICommon.WrapInGrid( delete_lock_panel, rows )
        
        delete_lock_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, delete_lock_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Use the advanced file deletion dialog: ', self._use_advanced_file_deletion_dialog ) )
        rows.append( ( 'Remember the last action: ', self._remember_last_advanced_file_deletion_special_action ) )
        rows.append( ( 'Remember the last reason: ', self._remember_last_advanced_file_deletion_reason ) )
        
        gridbox = ClientGUICommon.WrapInGrid( advanced_file_deletion_panel, rows )
        
        advanced_file_deletion_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        advanced_file_deletion_panel.Add( self._advanced_file_deletion_reasons, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        QP.AddToLayout( vbox, advanced_file_deletion_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._delete_lock_for_archived_files.clicked.connect( self._UpdateLockControls )
        
        self._remove_filtered_files.clicked.connect( self._UpdateRemoveFiltered )
        
        self._use_advanced_file_deletion_dialog.clicked.connect( self._UpdateAdvancedControls )
        
        self._UpdateLockControls()
        self._UpdateRemoveFiltered()
        self._UpdateAdvancedControls()
        
    
    def _AddAFDR( self ):
        
        reason = 'I do not like the file.'
        
        return self._EditAFDR( reason )
        
    
    def _EditAFDR( self, reason ):
        
        try:
            
            reason = ClientGUIDialogsQuick.EnterText( self, 'Enter the reason', default = reason )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return reason
        
    
    def _UpdateAdvancedControls( self ):
        
        advanced_enabled = self._use_advanced_file_deletion_dialog.isChecked()
        
        self._remember_last_advanced_file_deletion_special_action.setEnabled( advanced_enabled )
        self._remember_last_advanced_file_deletion_reason.setEnabled( advanced_enabled )
        self._advanced_file_deletion_reasons.setEnabled( advanced_enabled )
        
    
    def _UpdateRemoveFiltered( self ):
        
        self._remove_filtered_files_even_when_skipped.setEnabled( self._remove_filtered_files.isChecked() )
        
    
    def _UpdateLockControls( self ):
        
        self._delete_lock_reinbox_deletees_after_archive_delete.setEnabled( self._delete_lock_for_archived_files.isChecked() )
        self._delete_lock_reinbox_deletees_after_duplicate_filter.setEnabled( self._delete_lock_for_archived_files.isChecked() )
        self._delete_lock_reinbox_deletees_in_auto_resolution.setEnabled( self._delete_lock_for_archived_files.isChecked() )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'prefix_hash_when_copying', self._prefix_hash_when_copying.isChecked() )
        
        HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.isChecked()
        HC.options[ 'confirm_trash' ] = self._confirm_trash.isChecked()
        HC.options[ 'confirm_archive' ] = self._confirm_archive.isChecked()
        HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.isChecked()
        self._new_options.SetBoolean( 'remove_filtered_files_even_when_skipped', self._remove_filtered_files_even_when_skipped.isChecked() )
        HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.isChecked()
        self._new_options.SetBoolean( 'remove_local_domain_moved_files', self._remove_local_domain_moved_files.isChecked() )
        HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
        HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
        
        self._new_options.SetBoolean( 'do_not_do_chmod_mode', self._do_not_do_chmod_mode.isChecked() )
        
        self._new_options.SetBoolean( 'only_show_delete_from_all_local_domains_when_filtering', self._only_show_delete_from_all_local_domains_when_filtering.isChecked() )
        self._new_options.SetBoolean( 'archive_delete_commit_panel_delays_multiple_delete_choices', self._archive_delete_commit_panel_delays_multiple_delete_choices.isChecked() )
        
        self._new_options.SetInteger( 'ms_to_wait_between_physical_file_deletes', HydrusTime.MillisecondiseS( self._ms_to_wait_between_physical_file_deletes.GetValue() ) )
        
        self._new_options.SetBoolean( 'confirm_multiple_local_file_services_copy', self._confirm_multiple_local_file_services_copy.isChecked() )
        self._new_options.SetBoolean( 'confirm_multiple_local_file_services_move', self._confirm_multiple_local_file_services_move.isChecked() )
        
        self._new_options.SetBoolean( 'delete_lock_for_archived_files', self._delete_lock_for_archived_files.isChecked() )
        self._new_options.SetBoolean( 'delete_lock_reinbox_deletees_after_archive_delete', self._delete_lock_reinbox_deletees_after_archive_delete.isChecked() )
        self._new_options.SetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter', self._delete_lock_reinbox_deletees_after_duplicate_filter.isChecked() )
        self._new_options.SetBoolean( 'delete_lock_reinbox_deletees_in_auto_resolution', self._delete_lock_reinbox_deletees_in_auto_resolution.isChecked() )
        
        self._new_options.SetBoolean( 'use_advanced_file_deletion_dialog', self._use_advanced_file_deletion_dialog.isChecked() )
        
        self._new_options.SetStringList( 'advanced_file_deletion_reasons', self._advanced_file_deletion_reasons.GetData() )
        
        CG.client_controller.new_options.SetBoolean( 'remember_last_advanced_file_deletion_special_action', self._remember_last_advanced_file_deletion_special_action.isChecked() )
        CG.client_controller.new_options.SetBoolean( 'remember_last_advanced_file_deletion_reason', self._remember_last_advanced_file_deletion_reason.isChecked() )
        
    
