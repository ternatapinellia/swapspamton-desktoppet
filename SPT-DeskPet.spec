# -*- mode: python ; coding: utf-8 -*-

spt_sfx = [
    ('spt_sfx/voice_spam.wav', 'spt_sfx'),
    ('spt_sfx/voice_spamlaugh.wav', 'spt_sfx'),
    ('spt_sfx/voice_spamlaugh_long.wav', 'spt_sfx'),
]

a = Analysis(
    ['index.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('pet1.png', '.'),
        ('pet2.png', '.'),
        ('bubble.png', '.'),
        ('panel.png', '.'),
        ('panel2.png', '.'),
        ('message.ico', '.'),
        ('dialogues.py', '.'),
('GAMES', 'GAMES'),
    ] + spt_sfx,
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtMultimedia',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SPT-DeskPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['message.ico'],
)