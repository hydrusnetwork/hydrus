from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtInit
from hydrus.client.gui.panels import ClientGUIScrolledPanelsReview

def render_availability_line( name: str, is_ok: bool, is_module_not_found: bool, error_trace: str ):
    
    if is_ok:
        
        return f'{name}: yes'
        
    elif is_module_not_found:
        
        return f'{name}: not available'
        
    else:
        
        HydrusData.ShowText( f'Module {name} failed to import because of the following:' )
        HydrusData.ShowText( error_trace )
        
        if name == 'mpv' and 'sio_flush' in error_trace:
            
            HydrusData.ShowText( 'Hey I noticed you have "sio_flush" in your mpv error text. We have been able to fix this for other users by moving them to running from source. This is not super difficult to set up, and there are several other benefits, so please check the "running from source" guide in the help!' )
            
        
        return f'{name}: no - error'
        
    

def ShowAboutWindow( win: QW.QWidget ):
    
    import cv2
    import os
    import PIL
    import sqlite3
    import ssl
    import sys
    import typing
    
    from hydrus.core import HydrusCompression
    from hydrus.core import HydrusEncryption
    from hydrus.core import HydrusMemory
    from hydrus.core import HydrusPSUtil
    from hydrus.core import HydrusTemp
    from hydrus.core import HydrusText
    from hydrus.core import HydrusTime
    from hydrus.core.files import HydrusFileHandling
    from hydrus.core.files import HydrusOLEHandling
    from hydrus.core.files import HydrusFFMPEG
    from hydrus.core.files.images import HydrusImageHandling
    
    from hydrus.client import ClientPDFHandling
    from hydrus.client import ClientTime
    from hydrus.client.gui import ClientGUICharts
    from hydrus.client.gui.canvas import ClientGUIMPV
    from hydrus.client.parsing import ClientParsing

    name = 'hydrus client'
    version = 'v{}, using network version {}'.format( HC.SOFTWARE_VERSION, HC.NETWORK_VERSION )
    
    library_version_lines = []
    
    library_version_lines.append( 'running on {} {} {}'.format( HC.NICE_ARCHITECTURE_STRING, HC.NICE_PLATFORM_STRING, HC.NICE_RUNNING_AS_STRING ) )
    
    # 2.7.12 (v2.7.12:d33e0cf91556, Jun 27 2016, 15:24:40) [MSC v.1500 64 bit (AMD64)]
    v = sys.version
    
    if ' ' in v:
        
        v = v.split( ' ' )[0]
        
    
    library_version_lines.append( 'python: {}'.format( v ) )
    library_version_lines.append( 'FFMPEG: {}'.format( HydrusFFMPEG.GetFFMPEGVersion() ) )
    
    if ClientGUIMPV.MPV_IS_AVAILABLE:
        
        library_version_lines.append( 'mpv api version: {}'.format( ClientGUIMPV.GetClientAPIVersionString() ) )
        
    else:
        
        library_version_lines.append( render_availability_line( 'mpv', ClientGUIMPV.MPV_IS_AVAILABLE, ClientGUIMPV.MPV_MODULE_NOT_FOUND, ClientGUIMPV.MPV_IMPORT_ERROR ) )
        
        if HC.RUNNING_FROM_FROZEN_BUILD and HC.PLATFORM_MACOS:
            
            HydrusData.ShowText( 'The macOS App does not come with MPV support on its own, but if your system has the dev library, libmpv1 or libmpv2, it will try to import it. It seems your system does not have this, or it failed to import. The specific error follows:' )
            
        
    
    library_version_lines.append( 'OpenCV: {}'.format( cv2.__version__ ) )
    library_version_lines.append( 'openssl: {}'.format( ssl.OPENSSL_VERSION ) )
    
    import numpy
    
    library_version_lines.append( 'numpy: {}'.format( numpy.__version__ ) )
    library_version_lines.append( 'Pillow: {}'.format( PIL.__version__ ) )
    
    qt_string = 'Qt: Unknown'
    
    if QtInit.WE_ARE_QT5:
        
        if QtInit.WE_ARE_PYSIDE:
            
            # noinspection PyUnresolvedReferences
            import PySide2
            
            qt_string = 'Qt: PySide2 {}'.format( PySide2.__version__ )
            
        elif QtInit.WE_ARE_PYQT:
            
            # noinspection PyUnresolvedReferences
            from PyQt5.Qt import PYQT_VERSION_STR # pylint: disable=E0401,E0611
            
            qt_string = 'Qt: PyQt5 {}'.format( PYQT_VERSION_STR )
            
        
    elif QtInit.WE_ARE_QT6:
        
        if QtInit.WE_ARE_PYSIDE:
            
            import PySide6
            
            qt_string = 'Qt: PySide6 {}'.format( PySide6.__version__ )
            
        elif QtInit.WE_ARE_PYQT:
            
            # noinspection PyUnresolvedReferences
            from PyQt6.QtCore import PYQT_VERSION_STR
            
            qt_string = 'Qt: PyQt6 {}'.format( PYQT_VERSION_STR )
            
        
    
    try:
        
        actual_platform_name = QG.QGuiApplication.platformName()
        running_platform_name = typing.cast( QW.QApplication, QW.QApplication.instance() ).platformName()
        
        if actual_platform_name != running_platform_name:
            
            qt_string += f' (actual {actual_platform_name}, set-to {running_platform_name})'
            
        else:
            
            qt_string += f' ({actual_platform_name})'
            
        
    except:
        
        qt_string += f' (unknown platform)'
        
    
    library_version_lines.append( qt_string )
    
    library_version_lines.append( 'sqlite: {}'.format( sqlite3.sqlite_version ) )
    
    library_version_lines.append( '' )
    
    boot_time_ms = CG.client_controller.GetBootTimestampMS()
    
    library_version_lines.append( f'boot time: {HydrusTime.TimestampToPrettyTimeDelta( boot_time_ms // 1000 )} ({HydrusTime.TimestampMSToPrettyTime( boot_time_ms )})' )
    
    library_version_lines.append( '' )
    
    library_version_lines.append( 'install dir: {}'.format( HC.BASE_DIR ) )
    library_version_lines.append( 'db dir: {}'.format( CG.client_controller.db_dir ) )
    library_version_lines.append( 'temp dir: {}'.format( HydrusTemp.GetCurrentTempDir() ) )
    
    import locale
    
    l_string = locale.getlocale()[0]
    qtl_string = QC.QLocale().name()
    
    library_version_lines.append( 'locale: {}/{}'.format( l_string, qtl_string ) )
    
    library_version_lines.append( '' )
    
    library_version_lines.append( 'db cache size per file: {}MB'.format( HG.db_cache_size ) )
    library_version_lines.append( 'db journal mode: {}'.format( HG.db_journal_mode ) )
    library_version_lines.append( 'db synchronous mode: {}'.format( HG.db_synchronous ) )
    library_version_lines.append( 'db transaction commit period: {}'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HG.db_cache_size ) ) )
    library_version_lines.append( 'db using memory for temp?: {}'.format( HG.no_db_temp_files ) )
    
    description_versions = 'This is the media management application of the hydrus software suite.' + '\n' * 2 + '\n'.join( library_version_lines )
    
    #
    
    if not HydrusImageHandling.JXL_OK:
        
        message = 'Hey, you do not seem to have Jpeg-XL support for our image library Pillow. The error follows:'
        
        if HC.PLATFORM_MACOS:
            
            message += '\n\nAlso, since you are on macOS, you should know that a common reason for Jpeg-XL not loading is that it is not bundled with their python package on macOS. Your error below probably talks about a missing .dylib or .so file. If you run from source, you can resolve this by opening a terminal and running "brew install jpeg-xl", and then restarting hydrus.'
            
        
        HydrusData.ShowText( message )
        HydrusData.ShowText( HydrusImageHandling.JXL_ERROR_TEXT )
        
    
    availability_lines = []
    
    availability_lines.append( render_availability_line( 'QtCharts', ClientGUICharts.QT_CHARTS_OK, ClientGUICharts.QT_CHARTS_MODULE_NOT_FOUND, ClientGUICharts.QT_CHARTS_IMPORT_ERROR ) )
    
    if QtInit.WE_ARE_QT5:
        
        availability_lines.append( 'QtPdf not available on Qt5' )
        
    else:
        
        availability_lines.append( render_availability_line( 'QtPdf', ClientPDFHandling.PDF_OK, ClientPDFHandling.PDF_MODULE_NOT_FOUND, ClientPDFHandling.PDF_IMPORT_ERROR ) )
        
    
    CBOR_AVAILABLE = False
    
    try:
        
        import cbor2
        CBOR_AVAILABLE = True
        
    except:
        
        pass
        
    
    availability_lines.append( render_availability_line( 'cbor2', CBOR_AVAILABLE, not CBOR_AVAILABLE, '' ) )
    availability_lines.append( render_availability_line( 'chardet', HydrusText.CHARDET_OK, not HydrusText.CHARDET_OK, '' ) )
    availability_lines.append( render_availability_line( 'cryptography', HydrusEncryption.CRYPTO_OK, not HydrusEncryption.CRYPTO_OK, '' ) )
    availability_lines.append( render_availability_line( 'dateparser', ClientTime.DATEPARSER_OK, ClientTime.DATEPARSER_MODULE_NOT_FOUND, ClientTime.DATEPARSER_IMPORT_ERROR ) )
    availability_lines.append( render_availability_line( 'dateutil', ClientTime.DATEUTIL_OK, ClientTime.DATEUTIL_MODULE_NOT_FOUND, ClientTime.DATEUTIL_IMPORT_ERROR ) )
    availability_lines.append( render_availability_line( 'html5lib', ClientParsing.HTML5LIB_IS_OK, not ClientParsing.HTML5LIB_IS_OK, '' ) )
    availability_lines.append( render_availability_line( 'lxml', ClientParsing.LXML_IS_OK, not ClientParsing.LXML_IS_OK, '' ) )
    availability_lines.append( render_availability_line( 'lz4', HydrusCompression.LZ4_OK, not HydrusCompression.LZ4_OK, '' ) )
    availability_lines.append( render_availability_line( 'olefile', HydrusOLEHandling.OLEFILE_OK, not HydrusOLEHandling.OLEFILE_OK, '' ) )
    
    #
    
    heif_line = render_availability_line( 'Pillow HEIF', HydrusImageHandling.HEIF_OK, not HydrusImageHandling.HEIF_OK, '' )
    
    if HydrusImageHandling.HEIF_OK:
        
        if HydrusImageHandling.HEIF_PLUGIN_OK:
            
            extra = 'via plugin'
            
        else:
            
            extra = 'native'
            
        
        heif_line = f'{heif_line} ({extra})'
        
    
    availability_lines.append( heif_line )
    
    #
    
    avif_line = render_availability_line( 'Pillow AVIF', HydrusImageHandling.AVIF_OK, not HydrusImageHandling.AVIF_OK, '' )
    
    if HydrusImageHandling.AVIF_OK:
        
        if HydrusImageHandling.AVIF_BACKUP_PLUGIN_OK:
            
            extra = 'via backup plugin'
            
        elif HydrusImageHandling.AVIF_PLUGIN_OK:
            
            extra = 'via plugin'
            
        else:
            
            extra = 'native'
            
        
        avif_line = f'{avif_line} ({extra})'
        
    
    availability_lines.append( avif_line )
    
    #
    
    jxl_line = render_availability_line( 'Pillow JpegXL', HydrusImageHandling.JXL_OK, not HydrusImageHandling.JXL_OK, '' )
    
    if HydrusImageHandling.JXL_OK:
        
        if HydrusImageHandling.JXL_PLUGIN_OK:
            
            extra = 'via plugin'
            
        else:
            
            extra = 'native'
            
        
        jxl_line = f'{jxl_line} ({extra})'
        
    
    availability_lines.append( jxl_line )
    
    #
    
    availability_lines.append( render_availability_line( 'psutil', HydrusPSUtil.PSUTIL_OK, HydrusPSUtil.PSUTIL_MODULE_NOT_FOUND, HydrusPSUtil.PSUTIL_IMPORT_ERROR ) )
    availability_lines.append( render_availability_line( 'pympler', HydrusMemory.PYMPLER_OK, not HydrusMemory.PYMPLER_OK, '' ) )
    availability_lines.append( render_availability_line( 'pyopenssl', HydrusEncryption.OPENSSL_OK, not HydrusEncryption.OPENSSL_OK, '' ) )
    availability_lines.append( render_availability_line( 'show-in-file-manager', ClientPaths.SHOW_IN_FILE_MANAGER_OK, not ClientPaths.SHOW_IN_FILE_MANAGER_OK, '' ) )
    availability_lines.append( render_availability_line( 'speedcopy (experimental test)', HydrusFileHandling.SPEEDCOPY_OK, not HydrusFileHandling.SPEEDCOPY_OK, '' ) )
    
    description_availability = '\n'.join( availability_lines )
    
    #
    
    if os.path.exists( HC.LICENSE_PATH ):
        
        with open( HC.LICENSE_PATH, 'r', encoding = 'utf-8' ) as f:
            
            hydrus_license = f.read()
            
        
    else:
        
        hydrus_license = 'no licence file found!'
        
    
    developers = [ 'Anonymous' ]
    
    site = 'https://hydrusnetwork.github.io/hydrus/'
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, 'about hydrus' )
    
    panel = ClientGUIScrolledPanelsReview.AboutPanel( frame, name, version, description_versions, description_availability, hydrus_license, developers, site )
    
    frame.SetPanel( panel )
    
