# -*- mode: python ; coding: utf-8 -*-

import cloudscraper
import os
import glob
cloudscraper_dir = os.path.dirname( cloudscraper.__file__ )

block_cipher = None


a = Analysis(['hydrus\\hydrus_client.pyw'],
             pathex=['.'],
             binaries=[
               ('hydrus\\sqlite3.dll', '.'),
               ('hydrus\\mpv-2.dll', '.'),
               ('dist\\hydrus_server\\hydrus_server.exe*', '.')
             ],
             datas=[
               ('hydrus\\bin', 'bin'),
               ('hydrus\\help', 'help'),
               ('hydrus\\static', 'static'),
               ('hydrus\\license.txt', '.'),
               ('hydrus\\README.md', '.'),
               ('hydrus\\auto_update_installer.bat', '.'),
               ('hydrus\\help my client will not boot.txt', '.'),
               ('hydrus\\db', 'db'),
               (cloudscraper_dir, 'cloudscraper')
             ],
             hiddenimports=['cloudscraper'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='hydrus_client',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          version='client_file_version_info.txt',
          icon='hydrus\\static\\hydrus.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='hydrus_client')
