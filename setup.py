# setup.py - Fixed Build script for SoulSniper's SOF Seeder (Windows Compatible)
import PyInstaller.__main__
import os
import sys

def create_manifest_file():
    """Create a Windows manifest file for admin elevation"""
    manifest_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="1.0.0.0"
    processorArchitecture="amd64"
    name="SoulSniperSOFSeeder"
    type="win32"
  />
  <description>SoulSniper's SOF Seeder - Hell Let Loose Server Automation</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 -->
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
      <!-- Windows 8.1 -->
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
      <!-- Windows 8 -->
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/>
      <!-- Windows 7 -->
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>
    </application>
  </compatibility>
</assembly>'''
    
    with open('app.manifest', 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    print("✅ Created Windows manifest file")

def create_version_info():
    """Create version info file for the executable"""
    version_info = '''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'SoulSniper Gaming Community'),
          StringStruct(u'FileDescription', u'SoulSniper\\'s SOF Seeder - Automatic Hell Let Loose Server Seeder'),
          StringStruct(u'FileVersion', u'1.0.0.0'),
          StringStruct(u'InternalName', u'SoulSniper_SOF_Seeder'),
          StringStruct(u'LegalCopyright', u'Copyright (C) 2025 SoulSniper Gaming Community'),
          StringStruct(u'OriginalFilename', u'SoulSniper_SOF_Seeder.exe'),
          StringStruct(u'ProductName', u'SoulSniper\\'s SOF Seeder'),
          StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    print("✅ Created version info file")

def build_exe():
    """Build the executable using PyInstaller"""
    
    # Create necessary files
    create_manifest_file()
    create_version_info()
    
    # PyInstaller arguments - REMOVED --strip flag for Windows compatibility
    args = [
        'hll_auto_join.py',                    # Main script
        '--onefile',                           # Single executable
        '--windowed',                          # No console window (for GUI)
        '--name=SoulSniper_SOF_Seeder',       # Executable name
        
        # Include support files
        '--add-data=CreateTasks.xml;.',       # Include PowerShell script
        '--add-data=Uninstall.ps1;.',         # Include uninstall script
        
        # Windows manifest and version info
        '--manifest=app.manifest',            # Windows manifest for compatibility
        '--version-file=version_info.txt',    # Version information
        
        # Include ALL Python dependencies for GUI
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.simpledialog',
        '--hidden-import=tkinter.colorchooser',
        '--hidden-import=tkinter.commondialog',
        '--hidden-import=tkinter.constants',
        '--hidden-import=tkinter.dnd',
        '--hidden-import=tkinter.font',
        '--hidden-import=tkinter.scrolledtext',
        
        # Image handling
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageTk',
        '--hidden-import=PIL._imaging',
        
        # Network and API
        '--hidden-import=requests',
        '--hidden-import=requests.adapters',
        '--hidden-import=requests.auth',
        '--hidden-import=requests.cookies',
        '--hidden-import=requests.models',
        '--hidden-import=requests.sessions',
        '--hidden-import=requests.utils',
        '--hidden-import=urllib3',
        '--hidden-import=urllib3.util',
        '--hidden-import=urllib3.util.retry',
        '--hidden-import=urllib3.exceptions',
        '--hidden-import=certifi',
        '--hidden-import=charset_normalizer',
        '--hidden-import=idna',
        
        # System process handling
        '--hidden-import=psutil',
        '--hidden-import=psutil._common',
        '--hidden-import=psutil._compat',
        '--hidden-import=psutil._psutil_windows',
        
        # Input automation (fallback)
        '--hidden-import=pyautogui',
        '--hidden-import=pyautogui._pyautogui_win',
        '--hidden-import=pymsgbox',
        '--hidden-import=pytweening',
        '--hidden-import=pyscreeze',
        
        # Windows-specific modules for admin elevation and input
        '--hidden-import=ctypes',
        '--hidden-import=ctypes.wintypes',
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        '--hidden-import=win32gui',
        '--hidden-import=win32process',
        '--hidden-import=win32security',
        '--hidden-import=win32service',
        '--hidden-import=win32serviceutil',
        '--hidden-import=pywintypes',
        
        # Standard library modules
        '--hidden-import=threading',
        '--hidden-import=subprocess',
        '--hidden-import=winreg',
        '--hidden-import=json',
        '--hidden-import=pathlib',
        '--hidden-import=time',
        '--hidden-import=re',
        '--hidden-import=os',
        '--hidden-import=sys',
        '--hidden-import=string',
        '--hidden-import=datetime',
        '--hidden-import=logging',
        '--hidden-import=tempfile',
        '--hidden-import=shutil',
        
        # Bundle critical packages completely
        '--collect-all=tkinter',
        '--collect-submodules=tkinter',
        '--collect-data=tkinter',
        '--collect-all=PIL',
        '--collect-all=requests',
        '--collect-all=urllib3',
        '--collect-all=psutil',
        '--collect-all=pyautogui',
        '--collect-all=win32api',
        '--collect-all=win32gui',
        '--collect-all=ctypes',
        
        # Build settings
        '--distpath=dist',                    # Output directory
        '--workpath=build',                   # Temp build directory
        '--clean',                            # Clean before build
        '--noconfirm',                        # Don't ask for confirmation
        
        # Optimization - REMOVED --strip for Windows compatibility
        '--optimize=2',                       # Python optimization level
        # '--strip',                         # REMOVED: Not available on Windows
    ]
    
    # Add optional files if they exist
    if os.path.exists('SoulSniper_Logo.ico'):
        args.extend(['--icon=SoulSniper_Logo.ico', '--add-data=SoulSniper_Logo.ico;.'])
        print("✅ Including icon file")
    
    if os.path.exists('soulsniper_icon.png'):
        args.append('--add-data=soulsniper_icon.png;.')
        print("✅ Including PNG icon")
    
    if os.path.exists('README.txt'):
        args.append('--add-data=README.txt;.')
        print("✅ Including README")
    
    print("🔨 Building SoulSniper's SOF Seeder executable...")
    print("📦 This may take a few minutes...")
    print("🔧 Bundling Windows APIs for admin elevation...")
    print("⚠️  Note: Using Windows-compatible build settings (no strip optimization)")
    
    try:
        PyInstaller.__main__.run(args)
        
        # Verify the executable was created
        exe_path = os.path.join('dist', 'SoulSniper_SOF_Seeder.exe')
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"\n✅ Build completed successfully!")
            print(f"📁 Executable location: {exe_path}")
            print(f"📊 File size: {file_size:.1f} MB")
            print(f"🔑 Admin elevation: Built-in (will request when needed)")
            print(f"🖼️  GUI: Windowed mode (no console)")
            print(f"📦 Dependencies: All bundled")
            print(f"🖥️  Windows: Optimized for Windows compatibility")
            print(f"\n🚀 Ready for distribution and installer creation!")
        else:
            print("\n❌ Build completed but executable not found!")
            return False
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        print("💡 Tip: Make sure all dependencies are installed:")
        print("   pip install pyinstaller pillow requests psutil pyautogui pywin32")
        return False
    
    # Clean up temporary files
    try:
        if os.path.exists('app.manifest'):
            os.remove('app.manifest')
        if os.path.exists('version_info.txt'):
            os.remove('version_info.txt')
        print("🧹 Cleaned up temporary build files")
    except:
        pass
    
    return True

def install_dependencies():
    """Install required dependencies for building"""
    dependencies = [
        'pyinstaller',
        'pillow',  # PIL
        'requests',
        'psutil',
        'pyautogui',
        'pywin32',  # Windows APIs
    ]
    
    print("📦 Installing/updating build dependencies...")
    for dep in dependencies:
        try:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', dep])
            print(f"✅ {dep}")
        except:
            print(f"❌ Failed to install {dep}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--install-deps":
        install_dependencies()
    else:
        success = build_exe()
        if success:
            print("\n🎉 Build process completed successfully!")
            print("📋 Next steps:")
            print("   1. Test the executable: dist/SoulSniper_SOF_Seeder.exe")
            print("   2. Run Inno Setup with your .iss file to create installer")
            print("   3. Distribute the installer to users")
        else:
            print("\n💥 Build failed. Try running with --install-deps first:")
            print("   python setup.py --install-deps")
            sys.exit(1)