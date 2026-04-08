import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusCompression
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientRendering
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUIDialogsFiles
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingURLClass
from hydrus.client.parsing import ClientParsing

def IngestClipboard():
    
    if CG.client_controller.ClipboardHasImage():
        
        try:
            
            qt_image = CG.client_controller.GetClipboardImage()
            
            payload_bytes = ClientSerialisable.LoadFromQtImage( qt_image )
            
            payload_text = HydrusCompression.DecompressBytesToString( payload_bytes )
            
            return [ ( 'clipboard image data', payload_text ) ]
            
        except Exception as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            raise Exception( f'Problem pasting image! Full error written to log; {e}' )
            
        
    elif CG.client_controller.ClipboardHasLocalPaths():
        
        try:
            
            paths = CG.client_controller.GetClipboardLocalPaths()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            raise Exception( f'Problem pasting paths! Full error written to log; {e}' )
            
        
        return IngestPaths( paths )
        
    else:
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
            payload_text = raw_text
            
            return [ ( 'clipboard text data', payload_text ) ]
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            raise Exception( f'Problem pasting text! Full error written to log; {e}' )
            
        
    

def IngestPaths( paths ):
    
    payloads = []
    
    for path in paths:
        
        if HydrusFileHandling.GetIsPNGRealQuick( path ):
            
            try:
                
                payload_bytes = ClientSerialisable.LoadFromPNG( path )
                
                payload_text = HydrusCompression.DecompressBytesToString( payload_bytes )
                
                payloads.append( ( f'PNG "{path}"', payload_text ) )
                
            except Exception as e:
                
                HydrusData.PrintException( e, do_wait = False )
                
                raise Exception( f'Problem loading PNG at path "{path}"! Full error written to log; {e}' )
                
            
        else:
            
            try:
                
                with open( path, 'r', encoding = 'utf-8' ) as f:
                    
                    payload_text = f.read()
                    
                
                payloads.append( ( f'JSON "{path}"', payload_text ) )
                
            except Exception as e:
                
                HydrusData.PrintException( e, do_wait = False )
                
                raise Exception( f'Problem loading assumed JSON at path "{path}"! Full error written to log; {e}' )
                
            
        
    
    return payloads
    

class ReviewDownloaderImport( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        super().__init__( parent )
        
        self._network_engine = network_engine
        
        vbox = QP.VBoxLayout()
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_ADDING_NEW_DOWNLOADERS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the easy downloader import help', 'Open the help page for easily importing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help -->', object_name = 'HydrusIndeterminate' )
        
        self._repo_link = ClientGUICommon.BetterHyperLink( self, 'Many downloaders are available on the user-made downloader repository here.', 'https://github.com/CuddleBear92/Hydrus-Presets-and-Scripts/tree/master/Downloaders' )
        self._repo_link.setWordWrap( True )
        
        self._repo_link.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste paths/bitmaps/JSON from clipboard!' ) )
        
        label = 'To import:'
        label += '\n'
        label += '- drag-and-drop hydrus\'s special downloader-encoded pngs onto Lain'
        label += '\n'
        label += '- or click her to open a file selection dialog and select from there'
        label += '\n'
        label += '- or copy the png bitmap, file path, or raw downloader JSON to your clipboard and hit the paste button'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        st.setWordWrap( True )
        
        lain_path = HydrusStaticDir.GetStaticPath( 'lain.jpg' )
        
        lain_qt_pixmap = ClientRendering.GenerateHydrusBitmap( lain_path, HC.IMAGE_JPEG ).GetQtPixmap()
        
        win = QW.QLabel( self, pixmap = lain_qt_pixmap )
        
        win.setCursor( QG.QCursor( QC.Qt.CursorShape.PointingHandCursor ) )
        
        self._select_from_list = QW.QCheckBox( self )
        self._select_from_list.setToolTip( ClientGUIFunctions.WrapToolTip( 'If the payload includes multiple objects (most do), select what you want to import.' ) )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._select_from_list.setChecked( True )
            
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._repo_link, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, win, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._paste_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._select_from_list, self, 'select objects from list' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        win.installEventFilter( ClientGUIDragDrop.FileDropTarget( win, filenames_callable = self.ImportFromDragDrop ) )
        
        self._lain_event_filter = QP.WidgetEventFilter( win )
        self._lain_event_filter.EVT_LEFT_DOWN( self.EventLainClick )
        
    
    def _ImportPaths( self, paths ):
        
        try:
            
            payloads = IngestPaths( paths )
            
        except Exception as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'problem importing!', f'Sorry, there was a problem importing those paths! Error was: {e}' )
            
            return
            
        
        self._ImportPayloads( payloads )
        
    
    def _ImportPayloads( self, payloads ):
        
        have_shown_load_error = False
        
        gugs = []
        url_classes = []
        parsers = []
        domain_metadatas = []
        login_scripts = []
        
        num_misc_objects = 0
        
        bandwidth_manager = self._network_engine.bandwidth_manager
        domain_manager = self._network_engine.domain_manager
        login_manager = self._network_engine.login_manager
        
        for ( payload_description, payload_text ) in payloads:
            
            try:
                
                obj_list = HydrusSerialisable.CreateFromString( payload_text, raise_error_on_future_version = True )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( payloads ) > 1:
                        
                        message += '\n' * 2
                        message += 'If there are more unloadable objects in this import, they will be skipped silently.'
                        
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Serialisation Object Load Error!', message )
                    
                    have_shown_load_error = True
                    
                
                continue
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'I could not understand what was encoded in {}!'.format( payload_description ) )
                
                continue
                
            
            if isinstance( obj_list, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator, ClientNetworkingURLClass.URLClass, ClientParsing.PageParser, ClientNetworkingDomain.DomainMetadataPackage, ClientNetworkingLogin.LoginScriptDomain ) ):
                
                obj_list = HydrusSerialisable.SerialisableList( [ obj_list ] )
                
            
            if not isinstance( obj_list, HydrusSerialisable.SerialisableList ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Unfortunately, {} did not look like a package of download data! Instead, it looked like: {}'.format( payload_description, obj_list.SERIALISABLE_NAME ) )
                
                continue
                
            
            for obj in obj_list:
                
                if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ):
                    
                    gugs.append( obj )
                    
                elif isinstance( obj, ClientNetworkingURLClass.URLClass ):
                    
                    url_classes.append( obj )
                    
                elif isinstance( obj, ClientParsing.PageParser ):
                    
                    parsers.append( obj )
                    
                elif isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ):
                    
                    domain_metadatas.append( obj )
                    
                elif isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ):
                    
                    login_scripts.append( obj )
                    
                else:
                    
                    num_misc_objects += 1
                    
                
            
        
        if len( gugs ) + len( url_classes ) + len( parsers ) + len( domain_metadatas ) + len( login_scripts ) == 0:
            
            if num_misc_objects > 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'I found '+HydrusNumbers.ToHumanInt(num_misc_objects)+' misc objects in that png, but nothing downloader related.' )
                
            
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
            
            ClientGUIDialogsMessage.ShowInformation( self, f'All {HydrusNumbers.ToHumanInt( total_num_dupes )} downloader objects in that package appeared to already be in the client, so nothing need be added.' )
            
            return
            
        
        # let's start selecting what we want
        
        if self._select_from_list.isChecked():
            
            choice_tuples = []
            choice_tuples.extend( [ ( 'GUG: ' + gug.GetName(), gug, True ) for gug in new_gugs ] )
            choice_tuples.extend( [ ( 'URL Class: ' + url_class.GetName(), url_class, True ) for url_class in new_url_classes ] )
            choice_tuples.extend( [ ( 'Parser: ' + parser.GetName(), parser, True ) for parser in new_parsers ] )
            choice_tuples.extend( [ ( 'Login Script: ' + login_script.GetName(), login_script, True ) for login_script in new_login_scripts ] )
            choice_tuples.extend( [ ( 'Domain Metadata: ' + domain_metadata.GetDomain(), domain_metadata, True ) for domain_metadata in new_domain_metadatas ] )
            
            try:
                
                new_objects = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select objects to add', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            new_gugs = [ obj for obj in new_objects if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ) ]
            new_url_classes = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingURLClass.URLClass ) ]
            new_parsers = [ obj for obj in new_objects if isinstance( obj, ClientParsing.PageParser ) ]
            new_login_scripts = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ) ]
            new_domain_metadatas = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ) ]
            
        
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
                
                message += '\n' * 2
                message += 'There are more than ' + HydrusNumbers.ToHumanInt( TOO_MANY_DM ) + ' domain metadata objects. So I do not give you dozens of preview windows, I will only show you these first ' + HydrusNumbers.ToHumanInt( TOO_MANY_DM ) + '.'
                
            
            new_domain_metadatas_to_show = new_domain_metadatas[:TOO_MANY_DM]
            
            for new_dm in new_domain_metadatas_to_show:
                
                ClientGUIDialogsMessage.ShowInformation( self, new_dm.GetDetailedSafeSummary() )
                
            
        
        all_to_add = list( new_gugs )
        all_to_add.extend( new_url_classes )
        all_to_add.extend( new_parsers )
        all_to_add.extend( new_login_scripts )
        all_to_add.extend( new_domain_metadatas )
        
        message = 'The client is about to add and link these objects:'
        message += '\n' * 2
        message += '\n'.join( ( obj.GetSafeSummary() for obj in all_to_add[:20] ) )
        
        if len( all_to_add ) > 20:
            
            message += '\n'
            message += '(and ' + HydrusNumbers.ToHumanInt( len( all_to_add ) - 20 ) + ' others)'
            
        
        message += '\n' * 2
        message += 'Does that sound good?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        # ok, do it
        
        if len( new_gugs ) > 0:
            
            for gug in new_gugs:
                
                gug.RegenerateGUGKey()
                
            
            domain_manager.AddGUGs( new_gugs )
            
        
        domain_manager.AutoAddURLClassesAndParsers( new_url_classes, dupe_url_classes, new_parsers )
        
        bandwidth_manager.AutoAddDomainMetadatas( new_domain_metadatas )
        domain_manager.AutoAddDomainMetadatas( new_domain_metadatas, approved = ClientNetworkingDomain.VALID_APPROVED )
        login_manager.AutoAddLoginScripts( new_login_scripts )
        
        num_new_gugs = len( new_gugs )
        num_aux = len( new_url_classes ) + len( new_parsers ) + len( new_login_scripts ) + len( new_domain_metadatas )
        
        final_message = 'Successfully added ' + HydrusNumbers.ToHumanInt( num_new_gugs ) + ' new downloaders and ' + HydrusNumbers.ToHumanInt( num_aux ) + ' auxiliary objects.'
        
        if total_num_dupes > 0:
            
            final_message += ' ' + HydrusNumbers.ToHumanInt( total_num_dupes ) + ' duplicate objects were not added (but some additional metadata may have been merged).'
            
        
        ClientGUIDialogsMessage.ShowInformation( self, final_message )
        
        try:
            
            if CG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName() is None:
                
                all_gugs_now = sorted( CG.client_controller.network_engine.domain_manager.GetGUGs(), key = lambda gug: gug.GetName() )
                
                if len( all_gugs_now ) > 0:
                    
                    gug_key_and_name = all_gugs_now[0].GetGUGKeyAndName()
                    
                    CG.client_controller.network_engine.domain_manager.SetDefaultGUGKeyAndName( gug_key_and_name )
                    
                
            
        except Exception as e:
            
            HydrusData.Print( 'Hey, I was trying to set up a GUG (downloader) but the GUG store was messed up. Here is the error:' )
            
            HydrusData.PrintException( e, do_wait = False )
            
        
    
    def _Paste( self ):
        
        try:
            
            payloads = IngestClipboard()
            
        except Exception as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'problem importing!', f'Sorry, there was a problem importing those paths! Error was: {e}' )
            
            return
            
        
        self._ImportPayloads( payloads )
        
    
    def EventLainClick( self, event ):
        
        with ClientGUIDialogsFiles.FileDialog( self, 'Select the pngs to add.', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportPaths( paths )
                
            
        
    
    def ImportFromDragDrop( self, paths ):
        
        self._ImportPaths( paths )
        
    

class ReviewWhatIsThisObject( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        vbox = QP.VBoxLayout()
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste paths/bitmaps/JSON from clipboard!' ) )
        
        question_mark_path = HydrusStaticDir.GetStaticPath( 'question_mark_on_head.jpg' )
        
        question_mark_qt_pixmap = ClientRendering.GenerateHydrusBitmap( question_mark_path, HC.IMAGE_JPEG ).GetQtPixmap()
        
        win = QW.QLabel( self, pixmap = question_mark_qt_pixmap )
        
        win.setCursor( QG.QCursor( QC.Qt.CursorShape.PointingHandCursor ) )
        
        self._description = QW.QTextEdit( self )
        self._json_content = QW.QTextEdit( self )
        
        QP.AddToLayout( vbox, win, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._paste_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._json_content, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        win.installEventFilter( ClientGUIDragDrop.FileDropTarget( win, filenames_callable = self.ImportFromDragDrop ) )
        
        self._image_event_filter = QP.WidgetEventFilter( win )
        self._image_event_filter.EVT_LEFT_DOWN( self.EventImageClick )
        
    
    def _ImportPaths( self, paths ):
        
        try:
            
            payloads = IngestPaths( paths )
            
        except Exception as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'problem importing!', f'Sorry, there was a problem importing those paths! Error was: {e}' )
            
            return
            
        
        self._ImportPayloads( payloads )
        
    
    def _ImportPayloads( self, payloads ):
        
        result_texts = []
        json_texts = []
        
        for ( payload_description, payload_text ) in payloads:
            
            json_texts.append( payload_text )
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( payload_text, raise_error_on_future_version = True )
                
                if not isinstance( obj, HydrusSerialisable.SerialisableBase ):
                    
                    result_text = 'Something crazy happened and a non-serialisable object popped out.'
                    
                else:
                    
                    obj = typing.cast( HydrusSerialisable.SerialisableBase, obj )
                    
                    # TODO: let's make a HydrusSerialisable 'DescribeYourself' or similar and have lists and dicts talk about their contents
                    result_text = f'Object Type: {obj.GetSerialisableDescription()}'
                    result_text += '\n'
                    result_text += f'JSON: {HydrusData.ToHumanBytes( len( payload_text ) )}'
                    
                
                result_texts.append( result_text )
                
            except Exception as e:
                
                result_texts.append( 'Error: {e}' )
                
            
        
        ending_description_text = f'{HydrusNumbers.ToHumanInt(len( result_texts))} items\n\n' + '\n\n'.join( result_texts)
        
        self._description.setText( ending_description_text )
        self._json_content.setText( '\n\n'.join( json_texts ) )
        
    
    def _Paste( self ):
        
        try:
            
            payloads = IngestClipboard()
            
        except Exception as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'problem importing!', f'Sorry, there was a problem importing those paths! Error was: {e}' )
            
            return
            
        
        self._ImportPayloads( payloads )
        
    
    def EventImageClick( self, event ):
        
        with ClientGUIDialogsFiles.FileDialog( self, 'Select the pngs to add.', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportPaths( paths )
                
            
        
    
    def ImportFromDragDrop( self, paths ):
        
        self._ImportPaths( paths )
        
    
