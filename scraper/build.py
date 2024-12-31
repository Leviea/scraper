import PyInstaller.__main__
import os
import shutil

def build_exe():
    """Build executable dengan PyInstaller"""
    print("Memulai proses build executable...")
    
    # Hapus folder build dan dist jika ada
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # Konfigurasi PyInstaller
    PyInstaller.__main__.run([
        'scraper.py',  # Script utama
        '--name=WebCrawler',  # Nama executable
        '--onefile',  # Buat single executable
        '--windowed',  # Tanpa console window
        '--icon=icon.png',  # Icon aplikasi
        '--add-data=icon.png;.',  # Include icon.png
        '--hidden-import=PIL._tkinter_finder',  # Import tersembunyi yang diperlukan
        '--add-data=wheels;wheels',  # Include folder wheels
    ])
    
    print("\nBuild selesai! Executable dapat ditemukan di folder 'dist'")

if __name__ == "__main__":
    # Instal PyInstaller jika belum ada
    try:
        import pkg_resources
        pkg_resources.get_distribution('pyinstaller')
    except pkg_resources.DistributionNotFound:
        print("Menginstal PyInstaller...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    build_exe() 