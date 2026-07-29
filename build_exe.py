import PyInstaller.__main__
import sys
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
ENTRY_POINT = str(BASE_DIR / 'main.py')

# Define PyInstaller arguments
args = [
    ENTRY_POINT,               # Entry point
    '--name=Captain',          # Name of the executable
    '--onedir',                # One folder bundle (faster startup, easier config)
    '--windowed',              # Hide the console window
    '--noconfirm',             # Overwrite existing build
    '--icon=icon.ico',         # Custom Application Icon
]

# Hidden imports (libraries that use dynamic importing)
hidden_imports = [
    'google.genai',
    'comtypes',
    'sounddevice',
    'webview',
    'psutil',
    'cv2',
    'pywinauto',
    'youtube_transcript_api',
    'pptx',
    'mss',
    'pyautogui',
    'duckduckgo_search',
    'firebase_admin',
    'geopy',
    'dotenv',
    'win10toast',
    'pycaw',
    'PyQt6',
    'core.orb'
]

# Exclude massive unused ML frameworks that break the build
excludes = [
    'tensorflow',
    'torch',
    'tensorboard',
    'keras',
    'matplotlib',
    'PyQt5',          # Prevents multiple Qt binding collisions
    'jax',            # Fixes numpy 2.x crash
    'jaxlib',
    'ml_dtypes'
]

for imp in hidden_imports:
    args.extend(['--hidden-import', imp])

for exc in excludes:
    args.extend(['--exclude-module', exc])

data_folders = [
    ('core', 'core'),
    ('actions', 'actions'),
    ('plugins', 'plugins'),
    ('utils', 'utils'),
    ('frontend/dist', 'frontend/dist'),
]

for src, dst in data_folders:
    src_path = BASE_DIR / src
    if src_path.exists():
        args.extend(['--add-data', f'{src};{dst}'])
    else:
        print(f"Warning: Data folder {src} not found, skipping.")

print("Starting PyInstaller build...")
print(f"Arguments: {' '.join(args)}")

try:
    PyInstaller.__main__.run(args)
    print("\n[OK] Build complete! You can find the executable in the 'dist/Captain' folder.")
    
    # --- AUTOMATIC POST-BUILD COPY ---
    import shutil
    import glob
    print("-------------------------------------------------------------------------")
    is_release = '--release' in sys.argv
    
    if is_release:
        print("[+] RELEASE BUILD: Skipping personal data copy. Safe to share with others!")
    else:
        print("[+] LOCAL BUILD: Automating post-build steps (Copying personal data)...")
        print("    (Tip: Run 'python build_exe.py --release' if building for friends to avoid sharing personal data)")
        
        dest_dir = BASE_DIR / 'dist' / 'Captain'
        
        # 1. Copy config folder
        config_src = BASE_DIR / 'config'
        config_dst = dest_dir / 'config'
        if config_src.exists():
            if config_dst.exists():
                shutil.rmtree(config_dst)
            shutil.copytree(config_src, config_dst)
            print("  -> Copied 'config' folder")
            
        # 2. Copy memory folder (to retain long term memory across builds)
        memory_src = BASE_DIR / 'memory'
        memory_dst = dest_dir / 'memory'
        if memory_src.exists():
            if not memory_dst.exists():
                shutil.copytree(memory_src, memory_dst)
                print("  -> Copied 'memory' folder (First time setup)")
            else:
                print("  -> Skipped 'memory' folder (Existing memory kept safe!)")

        # 3. Copy .env file
        env_src = BASE_DIR / '.env'
        if env_src.exists():
            shutil.copy2(env_src, dest_dir / '.env')
            print("  -> Copied '.env' file")
            
        # 4. Copy Firebase JSON keys
        for fb_key in glob.glob(str(BASE_DIR / "*firebase*adminsdk*.json")):
            shutil.copy2(fb_key, dest_dir)
            print(f"  -> Copied Firebase key: {Path(fb_key).name}")
            
        print("-------------------------------------------------------------------------")
        print("[SUCCESS] All files copied! The .exe is ready to run with full memory and configuration restored.")
    
except Exception as e:
    print(f"\n[ERROR] Build failed: {e}")
