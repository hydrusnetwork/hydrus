# -*- mode: python ; coding: utf-8 -*-

import cloudscraper
import shiboken2
import os
import glob
cloudscraper_dir = os.path.dirname( cloudscraper.__file__ )
shiboken_dir = os.path.join( os.path.dirname( shiboken2.__file__ ), 'files.dir' )

block_cipher = None


a = Analysis(['hydrus\\client.pyw'],
             pathex=['.'],
             binaries=[],
             datas=[
               ('hydrus\\bin', 'bin'),
               ('hydrus\\help', 'help'),
               ('hydrus\\static', 'static'),
               ('dist\\server\\server.exe*', '.'),
               ('hydrus\\license.txt', '.'),
               ('hydrus\\Readme.txt', '.'),
               ('hydrus\\help my client will not boot.txt', '.'),
               ('hydrus\\db', 'db'),
               ('hydrus\\hydrus', 'hydrus'),
               ('hydrus\\sqlite3.dll', '.'),
               ('hydrus\\mpv-1.dll', '.'),
               (cloudscraper_dir, 'cloudscraper'),
               (shiboken_dir, 'shiboken2\\files.dir')
             ],
             hiddenimports=['hydrus\\server.py', 'cloudscraper'],
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
          name='client',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False, 
          icon='hydrus\\static\\hydrus.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='Hydrus Network')
