# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = collect_data_files("dearpygui")
datas += collect_data_files("mewgenics_parser")
datas += collect_data_files("mewgenics_scorer")
datas += collect_data_files("mewgenics_room_optimizer")
datas += [("packages/mewgenics_room_optimizer_ui/mewgenics_room_optimizer_ui/favicon.ico", ".")]   # puts favicon.ico in the bundle root

hiddenimports = ["dearpygui.dearpygui"]
hiddenimports += collect_submodules("mewgenics_parser")
hiddenimports += collect_submodules("mewgenics_scorer")
hiddenimports += collect_submodules("mewgenics_room_optimizer")
hiddenimports += collect_submodules("mewgenics_room_optimizer_ui")


def find_d3dcompiler():
    candidates = [
        r"C:\Windows\System32\D3DCOMPILER_47.dll",
        r"C:\Windows\SysWOW64\D3DCOMPILER_47.dll",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "D3DCOMPILER_47.dll not found"
    )


a = Analysis(
    ["packages/mewgenics_room_optimizer_ui/mewgenics_room_optimizer_ui/app.py"],
    pathex=[
        "packages/mewgenics_parser",
        "packages/mewgenics_scorer",
        "packages/mewgenics_room_optimizer",
        "packages/mewgenics_room_optimizer_ui",
    ],
    binaries=[
        (find_d3dcompiler(), "."),  # ← copies it into _internal\ root
    ],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="MewgenicsBreedingHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="packages/mewgenics_room_optimizer_ui/mewgenics_room_optimizer_ui/favicon.ico",
)

# vim: set filetype=python
