import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, Menu
from tkinter.ttk import Notebook
import requests
from bs4 import BeautifulSoup
import threading
import queue
import time
import json
import os
from datetime import datetime
import webbrowser
import random
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.qparser import QueryParser
import sys
from PIL import Image, ImageTk
import subprocess
import pkg_resources

def get_resource_path(relative_path):
    """Mendapatkan path absolut untuk resource file, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def check_and_install_dependencies():
    """Fungsi untuk mengecek dan menginstal dependensi yang diperlukan"""
    required_packages = {
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'whoosh': 'whoosh',
        'pillow': 'PIL',  # Menggunakan 'pillow' bukan 'PIL'
        'sv-ttk': 'sv_ttk'  # Optional theme package
    }
    
    missing_packages = []
    
    # Cek package yang belum terinstal
    for package, import_name in required_packages.items():
        try:
            pkg_resources.get_distribution(package)
        except pkg_resources.DistributionNotFound:
            missing_packages.append(package)
    
    # Instal package yang belum ada
    if missing_packages:
        print(f"Menginstal dependensi yang diperlukan: {', '.join(missing_packages)}")
        try:
            # Gunakan get_resource_path untuk folder wheels
            wheels_dir = get_resource_path("wheels")
            if os.path.exists(wheels_dir):
                # Instalasi dari file wheel lokal
                for package in missing_packages:
                    try:
                        # Cari file wheel yang sesuai
                        wheel_files = [f for f in os.listdir(wheels_dir) 
                                     if f.startswith(package.replace('-', '_')) and f.endswith('.whl')]
                        
                        if wheel_files:
                            wheel_path = os.path.join(wheels_dir, wheel_files[0])
                            subprocess.check_call([sys.executable, "-m", "pip", "install", wheel_path])
                            print(f"Berhasil menginstal {package} dari wheel lokal")
                        else:
                            # Jika tidak ada wheel, coba instal dari internet
                            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                            print(f"Berhasil menginstal {package} dari internet")
                    except subprocess.CalledProcessError as e:
                        print(f"Gagal menginstal {package}: {str(e)}")
                        return False
            else:
                os.makedirs(wheels_dir, exist_ok=True)
                print(f"Folder wheels telah dibuat di: {wheels_dir}")
                # Jika tidak ada folder wheels, buat folder dan beri instruksi
                os.makedirs(wheels_dir, exist_ok=True)
                print(f"""
Untuk instalasi offline:
1. Buat folder 'wheels' di lokasi yang sama dengan script ini
2. Download file wheel (.whl) untuk package berikut:
   {', '.join(missing_packages)}
3. Letakkan file wheel di folder 'wheels'
4. Jalankan script ini kembali

Folder wheels telah dibuat di: {wheels_dir}
                """)
                return False
            
            print("Semua dependensi berhasil diinstal!")
            return True
            
        except Exception as e:
            print(f"Error saat menginstal dependensi: {str(e)}")
            return False
    return True

class WebCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Crawler")
        self.root.geometry("800x600")
        
        # Set icon aplikasi
        try:
            # Gunakan get_resource_path untuk icon.png
            icon_path = get_resource_path("icon.png")
            if os.path.exists(icon_path):
                icon = ImageTk.PhotoImage(Image.open(icon_path))
                self.root.iconphoto(True, icon)
            else:
                self.create_default_icon()
                icon = ImageTk.PhotoImage(Image.open(icon_path))
                self.root.iconphoto(True, icon)
        except Exception as e:
            print(f"Error saat mengatur ikon: {str(e)}")
        
        # Set default dark mode dan style
        self.style = ttk.Style()
        self.is_dark_mode = tk.BooleanVar(value=True)  # Default dark mode
        
        # Setup tema dasar
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
            self.has_sv_ttk = True
        except ImportError:
            self.has_sv_ttk = False
            # Fallback ke tema default
            self.style.theme_use('default')
        
        self.setup_theme()
        
        self.queue = queue.Queue()
        self.scraped_data = []
        
        # Pengaturan bahasa
        self.languages = {
            
            'English': {
                'title': 'Web Crawler',
                'url_label': 'Start URL:',
                'depth_label': 'Max Depth:',
                'mode_frame': 'Operation Mode',
                'crawl_mode': 'Crawling',
                'scrape_mode': 'Scraping',
                'both_mode': 'Both',
                'start_button': 'Start',
                'stop_button': 'Stop',
                'save_button': 'Save Results',
                'result_frame': 'Crawling Results',
                'ready_status': 'Ready to crawl...',
                'error_url': 'Please enter URL!',
                'error_selector': 'Please enter CSS Selector for scraping!',
                'error_depth': 'Depth must be a positive number!',
                'stopping_status': 'Stopping crawler...',
                'finished_status': 'Crawling finished!',
                'stopped_status': 'Crawling stopped!'
            },
            
            'Indonesia': {
                'title': 'Web Crawler',
                'url_label': 'URL Awal:',
                'depth_label': 'Kedalaman Maksimal:',
                'mode_frame': 'Mode Operasi',
                'crawl_mode': 'Crawling',
                'scrape_mode': 'Scraping',
                'both_mode': 'Keduanya',
                'start_button': 'Mulai',
                'stop_button': 'Berhenti',
                'save_button': 'Simpan Hasil',
                'result_frame': 'Hasil Crawling',
                'ready_status': 'Siap untuk crawling...',
                'error_url': 'Mohon masukkan URL!',
                'error_selector': 'Mohon masukkan CSS Selector untuk scraping!',
                'error_depth': 'Kedalaman harus berupa angka positif!',
                'stopping_status': 'Menghentikan crawling...',
                'finished_status': 'Crawling selesai!',
                'stopped_status': 'Crawling dihentikan!'
            }
        }
        
        self.current_language = tk.StringVar(value='Indonesia')
        
        # Pengaturan default
        self.crawler_settings = {
            'timeout': 30,
            'max_retries': 3,
            'user_agent': 'Mozilla/5.0',
            'respect_robots': True,
            'delay': 1,  # delay antar request dalam detik
            'delay_min': 2,  # delay minimum dalam detik
            'delay_max': 5,  # delay maksimum dalam detik
            'rotate_user_agent': True,
            'respect_robots_txt': True
        }
        
        self.scraper_settings = {
            'extract_images': False,
            'extract_links': False,
            'min_text_length': 0,
            'exclude_selectors': '',
            'save_html': False
        }
        
        # Tambahkan daftar User-Agent
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        # Tambahkan pengaturan indexing
        self.index_settings = {
            'index_dir': 'search_index',
            'auto_index': True,
            'index_content': True,
            'index_title': True
        }
        
        # Setup schema untuk indexing
        self.schema = Schema(
            url=ID(stored=True),
            title=TEXT(stored=True),
            content=TEXT(stored=True),
            date=DATETIME(stored=True)
        )
        
        # Buat direktori index jika belum ada
        if not os.path.exists(self.index_settings['index_dir']):
            os.makedirs(self.index_settings['index_dir'])
            index.create_in(self.index_settings['index_dir'], self.schema)
        
        self.setup_menu()
        self.setup_gui()
        
    def setup_theme(self):
        # Definisi warna untuk tema
        self.themes = {
            'light': {
                'bg': '#ffffff',
                'fg': '#000000',
                'select_bg': '#0078d7',
                'select_fg': '#ffffff',
                'button': '#f0f0f0',
                'input_bg': '#ffffff',
                'frame_bg': '#f5f5f5',
                'accent': '#0078d7',
                'text_bg': '#ffffff',
                'text_fg': '#000000'
            },
            'dark': {
                'bg': '#1e1e1e',
                'fg': '#ffffff',
                'select_bg': '#404040',
                'select_fg': '#ffffff',
                'button': '#333333',
                'input_bg': '#2d2d2d',
                'frame_bg': '#252525',
                'accent': '#0078d7',
                'text_bg': '#2d2d2d',
                'text_fg': '#ffffff'
            }
        }
        
        theme = 'dark' if self.is_dark_mode.get() else 'light'
        colors = self.themes[theme]
        
        if not self.has_sv_ttk:
            # Configure styles untuk semua widget jika tidak menggunakan sv_ttk
            self.style.configure('.', background=colors['bg'], foreground=colors['fg'])
            self.style.configure('TFrame', background=colors['bg'])
            self.style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
            self.style.configure('TButton', 
                                background=colors['button'],
                                foreground=colors['fg'])
            
            self.style.configure('TEntry',
                                fieldbackground=colors['input_bg'],
                                foreground=colors['fg'])
            
            self.style.configure('TLabelframe',
                                background=colors['frame_bg'],
                                foreground=colors['fg'])
            
            self.style.configure('TLabelframe.Label',
                                background=colors['frame_bg'],
                                foreground=colors['fg'])
            
            self.style.configure('TNotebook',
                                background=colors['bg'])
            
            self.style.configure('TNotebook.Tab',
                                background=colors['button'],
                                foreground=colors['fg'],
                                padding=[10, 2])
        
        # Configure scrolledtext colors
        self.root.option_add('*Text*Background', colors['text_bg'])
        self.root.option_add('*Text*Foreground', colors['text_fg'])
        
        # Update root background
        self.root.configure(bg=colors['bg'])
        
        def update_theme(*args):
            theme = 'dark' if self.is_dark_mode.get() else 'light'
            colors = self.themes[theme]
            
            if not self.has_sv_ttk:
                # Update all styles
                self.style.configure('.', background=colors['bg'], foreground=colors['fg'])
                self.style.configure('TFrame', background=colors['bg'])
                self.style.configure('TLabel', background=colors['bg'], foreground=colors['fg'])
                self.style.configure('TButton',
                                    background=colors['button'],
                                    foreground=colors['fg'])
                self.style.configure('TEntry',
                                    fieldbackground=colors['input_bg'],
                                    foreground=colors['fg'])
                self.style.configure('TLabelframe',
                                    background=colors['frame_bg'],
                                    foreground=colors['fg'])
                self.style.configure('TLabelframe.Label',
                                    background=colors['frame_bg'],
                                    foreground=colors['fg'])
                self.style.configure('TNotebook',
                                    background=colors['bg'])
                self.style.configure('TNotebook.Tab',
                                    background=colors['button'],
                                    foreground=colors['fg'])
            
            # Update root and text widgets
            self.root.configure(bg=colors['bg'])
            self.root.option_add('*Text*Background', colors['text_bg'])
            self.root.option_add('*Text*Foreground', colors['text_fg'])
            
            if hasattr(self, 'result_text'):
                self.result_text.configure(
                    bg=colors['text_bg'],
                    fg=colors['text_fg'],
                    insertbackground=colors['fg']
                )
        
        # Bind theme update ke variable
        self.is_dark_mode.trace('w', update_theme)
        self._update_theme = update_theme

    def setup_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu File
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Buka File", command=self.open_saved_file)
        file_menu.add_separator()
        file_menu.add_command(label="Keluar", command=self.root.quit)
        
        # Menu View
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_checkbutton(label="Dark Mode", variable=self.is_dark_mode)
        
        # Menu Settings
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Advanced", command=self.show_advanced_settings)
        
        # Menu Language
        language_menu = Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="Language", menu=language_menu)
        for lang in self.languages.keys():
            language_menu.add_radiobutton(
                label=lang,
                variable=self.current_language,
                value=lang,
                command=self.update_language
            )
        
        # Menu Help
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Tutorial", command=self.show_tutorial)
        help_menu.add_command(label="About", command=self.show_about)

    def update_language(self):
        lang = self.languages[self.current_language.get()]
        
        # Update judul window
        self.root.title(lang['title'])
        
        # Update label-label
        self.url_label.config(text=lang['url_label'])
        self.depth_label.config(text=lang['depth_label'])
        self.mode_frame.config(text=lang['mode_frame'])
        
        # Update radio buttons
        self.crawl_radio.config(text=lang['crawl_mode'])
        self.scrape_radio.config(text=lang['scrape_mode'])
        self.both_radio.config(text=lang['both_mode'])
        
        # Update tombol-tombol
        self.start_button.config(text=lang['start_button'])
        self.stop_button.config(text=lang['stop_button'])
        self.save_button.config(text=lang['save_button'])
        
        # Update frame hasil
        self.result_frame.config(text=lang['result_frame'])
        
        # Update status
        if self.progress_var.get() == "Siap untuk crawling...":
            self.progress_var.set(lang['ready_status'])
        elif self.progress_var.get() == "Menghentikan crawling...":
            self.progress_var.set(lang['stopping_status'])
        elif self.progress_var.get() == "Crawling selesai!":
            self.progress_var.set(lang['finished_status'])
        elif self.progress_var.get() == "Crawling dihentikan!":
            self.progress_var.set(lang['stopped_status'])

    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Input")
        input_frame.pack(fill="x", pady=(0, 10))
        
        # URL input
        url_frame = ttk.Frame(input_frame)
        url_frame.pack(fill="x", padx=5, pady=5)
        
        self.url_label = ttk.Label(url_frame, text=self.languages[self.current_language.get()]['url_label'])
        self.url_label.pack(side="left")
        
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Control section
        control_frame = ttk.Frame(input_frame)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Depth input
        depth_frame = ttk.Frame(control_frame)
        depth_frame.pack(side="left", padx=(0, 20))
        
        self.depth_label = ttk.Label(depth_frame, text=self.languages[self.current_language.get()]['depth_label'])
        self.depth_label.pack(side="left")
        
        self.depth_var = tk.StringVar(value="2")
        self.depth_entry = ttk.Entry(depth_frame, textvariable=self.depth_var, width=5)
        self.depth_entry.pack(side="left", padx=(5, 0))
        
        # Mode selection
        self.mode_frame = ttk.LabelFrame(control_frame, text=self.languages[self.current_language.get()]['mode_frame'])
        self.mode_frame.pack(side="left", fill="x", expand=True)
        
        self.mode_var = tk.StringVar(value="both")
        modes = [
            ("crawl", self.languages[self.current_language.get()]['crawl_mode']),
            ("scrape", self.languages[self.current_language.get()]['scrape_mode']),
            ("both", self.languages[self.current_language.get()]['both_mode'])
        ]
        
        for value, text in modes:
            ttk.Radiobutton(self.mode_frame, text=text, value=value, 
                           variable=self.mode_var, command=self.on_mode_change).pack(side="left", padx=5)
        
        # CSS Selector
        selector_frame = ttk.Frame(input_frame)
        selector_frame.pack(fill="x", padx=5, pady=5)
        
        self.selector_label = ttk.Label(selector_frame, text="CSS Selector:")
        self.selector_label.pack(side="left")
        
        self.selector_entry = ttk.Entry(selector_frame)
        self.selector_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.selector_entry.insert(0, "p, h1, h2, h3")  # Default selector
        
        # Advanced Options Frame
        advanced_frame = ttk.LabelFrame(main_frame, text="Advanced Options")
        advanced_frame.pack(fill="x", pady=(0, 10))
        
        # Left side - Indexing options
        index_frame = ttk.Frame(advanced_frame)
        index_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Index mode
        index_mode_frame = ttk.Frame(index_frame)
        index_mode_frame.pack(fill="x")
        
        ttk.Label(index_mode_frame, text="Index Mode:").pack(side="left")
        self.index_mode_var = tk.StringVar(value="auto")
        ttk.Radiobutton(index_mode_frame, text="Auto", 
                        variable=self.index_mode_var, 
                        value="auto",
                        command=self.update_index_mode).pack(side="left", padx=5)
        ttk.Radiobutton(index_mode_frame, text="Manual", 
                        variable=self.index_mode_var, 
                        value="manual",
                        command=self.update_index_mode).pack(side="left", padx=5)
        
        self.index_button = ttk.Button(index_mode_frame, 
                                      text="Index Now", 
                                      command=self.manual_index,
                                      state="disabled")
        self.index_button.pack(side="left", padx=5)
        
        # Right side - Crawler options
        crawler_frame = ttk.Frame(advanced_frame)
        crawler_frame.pack(side="right", fill="x", expand=True, padx=5, pady=5)
        
        # Anti-detection options
        anti_detect_frame = ttk.Frame(crawler_frame)
        anti_detect_frame.pack(fill="x")
        
        # Robots.txt options
        ttk.Label(anti_detect_frame, text="Robots.txt:").pack(side="left")
        self.respect_robots_var = tk.BooleanVar(value=False)  # Default: bypass
        ttk.Radiobutton(anti_detect_frame, text="Respect", 
                        variable=self.respect_robots_var,
                        value=True).pack(side="left", padx=5)
        ttk.Radiobutton(anti_detect_frame, text="Bypass", 
                        variable=self.respect_robots_var,
                        value=False).pack(side="left", padx=5)
        
        # Delay options
        delay_frame = ttk.Frame(crawler_frame)
        delay_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Label(delay_frame, text="Delay (sec):").pack(side="left")
        self.delay_min_var = tk.StringVar(value="2")
        ttk.Entry(delay_frame, textvariable=self.delay_min_var, width=4).pack(side="left", padx=2)
        ttk.Label(delay_frame, text="-").pack(side="left")
        self.delay_max_var = tk.StringVar(value="5")
        ttk.Entry(delay_frame, textvariable=self.delay_max_var, width=4).pack(side="left", padx=2)
        
        # Search Frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)
        
        ttk.Button(search_frame, text="Search", 
                   command=self.search_index).pack(side="right", padx=(5, 0))
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, 
                                      text=self.languages[self.current_language.get()]['start_button'],
                                      command=self.start_crawling)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(button_frame,
                                     text=self.languages[self.current_language.get()]['stop_button'],
                                     command=self.stop_crawling,
                                     state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        self.save_button = ttk.Button(button_frame,
                                     text=self.languages[self.current_language.get()]['save_button'],
                                     command=self.save_results,
                                     state="disabled")
        self.save_button.pack(side="left", padx=5)
        
        # Results area
        result_frame = ttk.LabelFrame(main_frame, text=self.languages[self.current_language.get()]['result_frame'])
        result_frame.pack(fill="both", expand=True)
        
        self.result_text = scrolledtext.ScrolledText(result_frame)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status bar
        self.progress_var = tk.StringVar(value=self.languages[self.current_language.get()]['ready_status'])
        self.progress_label = ttk.Label(main_frame, textvariable=self.progress_var)
        self.progress_label.pack(pady=(5, 0))
        
        # Initial mode check
        self.on_mode_change()

    def start_crawling(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Mohon masukkan URL!")
            return
            
        # Menambahkan http:// secara otomatis jika tidak ada protokol
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
            
        # Validasi mode scraping
        if self.mode_var.get() in ["scrape", "both"]:
            if not self.selector_entry.get().strip():
                messagebox.showerror("Error", "Mohon masukkan CSS Selector untuk scraping!")
                return
        
        try:
            max_depth = int(self.depth_var.get())
            if max_depth < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Kedalaman harus berupa angka positif!")
            return
            
        self.crawling_active = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.result_text.delete(1.0, tk.END)
        
        # Memulai crawling dalam thread terpisah
        self.crawler_thread = threading.Thread(
            target=self.crawl,
            args=(url, max_depth)
        )
        self.crawler_thread.start()
        
        # Memulai pemeriksaan queue
        self.root.after(100, self.check_queue)
        
    def stop_crawling(self):
        self.crawling_active = False
        self.progress_var.set(self.languages[self.current_language.get()]['stopping_status'])
        self.stop_button.config(state="disabled")
        
    def crawl(self, start_url, max_depth):
        """Fungsi crawling dengan anti-detection"""
        try:
            # Random delay
            delay = random.uniform(float(self.delay_min_var.get()), 
                                 float(self.delay_max_var.get()))
            time.sleep(delay)
            
            # Get dengan random headers
            headers = self.get_random_headers()
            
            # Coba beberapa kali jika gagal
            retries = 3
            for attempt in range(retries):
                try:
                    response = requests.get(start_url, 
                                         headers=headers,
                                         timeout=30,
                                         verify=False)
                    
                    # Cek jika diblokir
                    if response.status_code == 403:
                        self.queue.put(("error", f"Terdeteksi sebagai bot di {start_url}, mencoba lagi...\n"))
                        time.sleep(delay * 2)  # Tunggu lebih lama
                        continue
                    
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Ambil title untuk indexing
                    title = soup.title.string if soup.title else ""
                    
                    # Index konten jika mode auto
                    if self.index_mode_var.get() == "auto":
                        content = " ".join([elem.get_text(strip=True) 
                                          for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
                        self.index_content(start_url, title, content)
                    
                    # Mengirim hasil ke queue
                    self.queue.put(("update", f"\nMengunjungi: {start_url}\n"))
                    
                    # Melakukan scraping jika mode sesuai
                    if self.mode_var.get() in ["scrape", "both"]:
                        selectors = self.selector_entry.get().strip().split(',')
                        scraped_content = []
                        
                        for selector in selectors:
                            elements = soup.select(selector.strip())
                            for element in elements:
                                text = element.get_text(strip=True)
                                if text:
                                    scraped_content.append({
                                        'url': start_url,
                                        'selector': selector.strip(),
                                        'content': text
                                    })
                        
                        if scraped_content:
                            self.scraped_data.extend(scraped_content)
                            self.queue.put(("update", f"Berhasil scraping {len(scraped_content)} elemen dari {start_url}\n"))
                    
                    # Lanjutkan crawling jika mode sesuai dan belum mencapai max_depth
                    if self.mode_var.get() in ["crawl", "both"] and max_depth > 0:
                        links = soup.find_all('a')
                        for link in links:
                            if not self.crawling_active:
                                return
                            
                            href = link.get('href')
                            if href:
                                try:
                                    # Perbaikan penanganan URL relatif
                                    if not href.startswith(('http://', 'https://')):
                                        href = urljoin(start_url, href)
                                    
                                    if href.startswith(('http://', 'https://')):
                                        self.crawl(href, max_depth - 1)
                                except Exception as e:
                                    self.queue.put(("error", f"Error parsing URL {href}: {str(e)}\n"))
                    
                    # Berhasil memproses URL ini
                    break
                    
                except requests.exceptions.ConnectionError as e:
                    if attempt == retries - 1:  # Jika ini percobaan terakhir
                        self.queue.put(("error", f"Koneksi gagal ke {start_url} setelah {retries} percobaan\n"))
                except Exception as e:
                    if attempt == retries - 1:  # Jika ini percobaan terakhir
                        self.queue.put(("error", f"Error pada {start_url}: {str(e)}\n"))
                
        except Exception as e:
            self.queue.put(("error", f"Error tidak terduga pada {start_url}: {str(e)}\n"))
        
        if not self.crawling_active:
            self.queue.put(("finished", None))

    def save_results(self):
        if not self.scraped_data:
            messagebox.showwarning("Peringatan", "Tidak ada data yang bisa disimpan!")
            return
            
        # Membuat nama file default dengan timestamp
        default_filename = f"crawling_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Dialog untuk memilih lokasi dan nama file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_filename,
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        try:
            # Menyimpan hasil dalam format JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_items': len(self.scraped_data),
                    'data': self.scraped_data
                }, f, ensure_ascii=False, indent=2)
                
            messagebox.showinfo("Sukses", f"Data berhasil disimpan ke:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file:\n{str(e)}")

    def check_queue(self):
        try:
            while True:
                msg_type, msg = self.queue.get_nowait()
                
                if msg_type == "update":
                    self.result_text.insert(tk.END, msg)
                    self.result_text.see(tk.END)
                elif msg_type == "error":
                    self.result_text.insert(tk.END, f"ERROR: {msg}\n", "error")
                    self.result_text.see(tk.END)
                elif msg_type == "finished":
                    self.crawling_active = False
                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    self.save_button.config(state="normal" if self.scraped_data else "disabled")
                    self.progress_var.set(self.languages[self.current_language.get()]['finished_status'])
                    return
                    
                self.queue.task_done()
                
        except queue.Empty:
            if self.crawling_active:
                self.root.after(100, self.check_queue)
            else:
                self.start_button.config(state="normal")
                self.stop_button.config(state="disabled")
                self.save_button.config(state="normal" if self.scraped_data else "disabled")
                self.progress_var.set(self.languages[self.current_language.get()]['stopped_status'])

    def show_advanced_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Pengaturan Lanjutan")
        settings_window.geometry("400x300")
        
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab crawler
        crawler_frame = ttk.Frame(notebook)
        notebook.add(crawler_frame, text="Crawler")
        
        # Tambahkan pengaturan lanjutan crawler
        row = 0
        for key, value in self.crawler_settings.items():
            ttk.Label(crawler_frame, text=key.replace('_', ' ').title() + ':').grid(
                row=row, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(crawler_frame)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, padx=5, pady=2)
            row += 1
            
        # Tab scraper
        scraper_frame = ttk.Frame(notebook)
        notebook.add(scraper_frame, text="Scraper")
        
        # Tambahkan pengaturan lanjutan scraper
        row = 0
        for key, value in self.scraper_settings.items():
            ttk.Label(scraper_frame, text=key.replace('_', ' ').title() + ':').grid(
                row=row, column=0, padx=5, pady=2, sticky="w")
            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                ttk.Checkbutton(scraper_frame, variable=var).grid(
                    row=row, column=1, padx=5, pady=2)
            else:
                entry = ttk.Entry(scraper_frame)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=5, pady=2)
            row += 1

    def open_saved_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Buat window baru untuk menampilkan hasil
                viewer = tk.Toplevel(self.root)
                viewer.title(f"Viewer - {os.path.basename(file_path)}")
                viewer.geometry("600x400")
                
                text_area = scrolledtext.ScrolledText(viewer, wrap=tk.WORD)
                text_area.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Tampilkan data dalam format yang mudah dibaca
                text_area.insert(tk.END, json.dumps(data, indent=2, ensure_ascii=False))
                text_area.config(state="disabled")  # Read-only
                
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membuka file:\n{str(e)}")

    def open_results_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            try:
                if os.path.exists(folder_path):
                    webbrowser.open(folder_path)
                else:
                    messagebox.showerror("Error", "Folder tidak ditemukan!")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membuka folder:\n{str(e)}")

    def on_mode_change(self):
        # Enable/disable selector entry berdasarkan mode yang dipilih
        if self.mode_var.get() in ["scrape", "both"]:
            self.selector_entry.config(state="normal")
        else:
            self.selector_entry.config(state="disabled")

    def index_content(self, url, title, content):
        """Index konten yang di-crawl"""
        try:
            ix = index.open_dir(self.index_settings['index_dir'])
            writer = ix.writer()
            
            writer.add_document(
                url=url,
                title=title if title else "",
                content=content,
                date=datetime.now()
            )
            
            writer.commit()
        except Exception as e:
            self.queue.put(("error", f"Error saat indexing {url}: {str(e)}\n"))

    def search_index(self):
        """Cari konten dalam index"""
        search_text = self.search_entry.get().strip()
        if not search_text:
            messagebox.showwarning("Peringatan", "Masukkan kata kunci pencarian!")
            return
        
        try:
            ix = index.open_dir(self.index_settings['index_dir'])
            
            # Cari di title dan content
            parser = QueryParser("content", ix.schema)
            query = parser.parse(search_text)
            
            with ix.searcher() as searcher:
                results = searcher.search(query, limit=50)
                
                # Tampilkan hasil dalam window baru
                search_window = tk.Toplevel(self.root)
                search_window.title(f"Search Results: {search_text}")
                search_window.geometry("600x400")
                
                result_text = scrolledtext.ScrolledText(search_window, wrap=tk.WORD)
                result_text.pack(fill="both", expand=True, padx=5, pady=5)
                
                if len(results) == 0:
                    result_text.insert(tk.END, "Tidak ditemukan hasil yang sesuai.")
                else:
                    for hit in results:
                        result_text.insert(tk.END, f"URL: {hit['url']}\n")
                        result_text.insert(tk.END, f"Title: {hit['title']}\n")
                        result_text.insert(tk.END, f"Date: {hit['date']}\n")
                        result_text.insert(tk.END, f"Content: {hit.highlights('content')}\n")
                        result_text.insert(tk.END, "-" * 50 + "\n\n")
                
                result_text.config(state="disabled")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error saat mencari: {str(e)}")

    def update_index_mode(self):
        """Update state tombol index berdasarkan mode yang dipilih"""
        if self.index_mode_var.get() == "manual":
            self.index_button.config(state="normal")
        else:
            self.index_button.config(state="disabled")

    def manual_index(self):
        """Melakukan indexing manual untuk data yang sudah di-crawl"""
        if not self.scraped_data:
            messagebox.showwarning("Peringatan", "Tidak ada data untuk di-index!")
            return
        
        try:
            ix = index.open_dir(self.index_settings['index_dir'])
            writer = ix.writer()
            
            indexed_count = 0
            for item in self.scraped_data:
                url = item['url']
                content = item['content']
                
                # Coba dapatkan title dari cache jika ada
                title = ""
                try:
                    response = requests.get(url, timeout=5, verify=False)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title = soup.title.string if soup.title else ""
                except:
                    pass
                
                writer.add_document(
                    url=url,
                    title=title,
                    content=content,
                    date=datetime.now()
                )
                indexed_count += 1
            
            writer.commit()
            messagebox.showinfo("Sukses", f"Berhasil mengindex {indexed_count} item!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saat indexing: {str(e)}")

    def show_tutorial(self):
        """Menampilkan window tutorial"""
        tutorial_window = tk.Toplevel(self.root)
        tutorial_window.title("Tutorial")
        tutorial_window.geometry("800x600")
        
        # Buat notebook untuk tab tutorial
        notebook = ttk.Notebook(tutorial_window)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab Dasar
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Pengaturan Dasar")
        
        basic_text = scrolledtext.ScrolledText(basic_frame, wrap=tk.WORD)
        basic_text.pack(fill="both", expand=True, padx=5, pady=5)
        basic_text.insert(tk.END, """
Pengaturan Dasar:

1. URL Input
   - Masukkan URL website target
   - URL akan otomatis ditambahkan 'http://' jika belum ada
   - Contoh: www.example.com

2. Kedalaman Crawling
   - Tentukan berapa level crawler akan mengikuti link
   - Nilai minimal adalah 1
   - Semakin dalam, semakin banyak halaman yang di-crawl

3. Mode Operasi
   - Crawling: Hanya mengumpulkan URL
   - Scraping: Hanya mengambil konten dari URL awal
   - Both: Melakukan crawling dan scraping sekaligus
    """)
        basic_text.config(state="disabled")
        
        # Tab Lanjutan
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Pengaturan Lanjutan")
        
        advanced_text = scrolledtext.ScrolledText(advanced_frame, wrap=tk.WORD)
        advanced_text.pack(fill="both", expand=True, padx=5, pady=5)
        advanced_text.insert(tk.END, """
Pengaturan Lanjutan:

1. Indexing
   - Auto: Indexing otomatis saat crawling
   - Manual: Indexing setelah crawling selesai
   - Gunakan "Index Now" untuk indexing manual
   - Berguna untuk pencarian konten

2. Robots.txt
   - Respect: Mengikuti aturan robots.txt website
   - Bypass: Mengabaikan robots.txt
   - Gunakan bypass dengan bijak dan bertanggung jawab

3. CSS Selector
   - Masukkan selector untuk elemen yang ingin di-scrape
   - Default: "p, h1, h2, h3"
   - Contoh lain: ".content", "#main-text", "article p"
   - Gunakan developer tools browser untuk identifikasi selector
    """)
        advanced_text.config(state="disabled")
        
        # Tab Tips
        tips_frame = ttk.Frame(notebook)
        notebook.add(tips_frame, text="Tips & Trik")
        
        tips_text = scrolledtext.ScrolledText(tips_frame, wrap=tk.WORD)
        tips_text.pack(fill="both", expand=True, padx=5, pady=5)
        tips_text.insert(tk.END, """
Tips & Trik:

1. Crawling Efektif
   - Mulai dengan kedalaman rendah (1-2) untuk tes
   - Gunakan mode "Crawling" untuk pemetaan awal
   - Aktifkan delay untuk menghindari pemblokiran
   - Monitor penggunaan memori

2. Scraping Optimal
   - Periksa struktur HTML website target
   - Gunakan selector yang spesifik
   - Test selector di browser terlebih dahulu
   - Simpan hasil secara berkala

3. Performa
   - Gunakan indexing manual untuk crawling besar
   - Atur delay sesuai kebijakan website
   - Batasi kedalaman crawling
   - Gunakan mode yang sesuai kebutuhan

4. Pencarian
   - Index konten untuk pencarian full-text
   - Gunakan kata kunci yang spesifik
   - Manfaatkan fitur highlight hasil
    """)
        tips_text.config(state="disabled")
        
        # Tab Peringatan
        warning_frame = ttk.Frame(notebook)
        notebook.add(warning_frame, text="Peringatan")
        
        warning_text = scrolledtext.ScrolledText(warning_frame, wrap=tk.WORD)
        warning_text.pack(fill="both", expand=True, padx=5, pady=5)
        warning_text.insert(tk.END, """
Peringatan Penting:

1. Penggunaan yang Bertanggung Jawab
   - Hormati Terms of Service website target
   - Perhatikan batas rate limiting
   - Jangan overload server target
   - Gunakan delay yang wajar

2. Keamanan
   - Verifikasi URL sebelum crawling
   - Hati-hati dengan konten berbahaya
   - Backup data penting
   - Monitor aktivitas crawling

3. Legal
   - Periksa kebijakan website target
   - Bypass robots.txt hanya jika diizinkan
   - Patuhi hukum dan regulasi yang berlaku
   - Hormati hak cipta
    """)
        warning_text.config(state="disabled")

    def show_about(self):
        """Menampilkan informasi tentang aplikasi"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("400x300")
        
        about_frame = ttk.Frame(about_window, padding="20")
        about_frame.pack(fill="both", expand=True)
        
        ttk.Label(about_frame, text="Web Crawler & Scraper", 
                  font=("Helvetica", 14, "bold")).pack(pady=10)
        
        ttk.Label(about_frame, text="Version 1.0", 
                  font=("Helvetica", 10)).pack()
        
        ttk.Label(about_frame, text="\nAplikasi web crawler dan scraper dengan GUI\n" +
                  "dilengkapi fitur indexing dan pencarian.\n\n" +
                  "Dibuat dengan Python menggunakan:\n" +
                  "- Tkinter untuk GUI\n" +
                  "- BeautifulSoup4 untuk parsing HTML\n" +
                  "- Whoosh untuk indexing dan pencarian\n",
                  justify="center").pack(pady=10)
        
        ttk.Label(about_frame, text="© 2024 Your Name\n" +
                  "Licensed under MIT License",
                  font=("Helvetica", 8)).pack(side="bottom", pady=10)

    def get_random_headers(self):
        """Generate random headers untuk bypass detection"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        return headers

    def create_default_icon(self):
        """Membuat icon default jika icon.png tidak ada"""
        try:
            # Buat gambar 32x32 pixel
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            
            # Buat desain ikon sederhana (contoh: lingkaran biru)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, 28, 28], fill='#0078d7')  # Lingkaran biru
            
            # Simpan sebagai icon.png
            img.save("icon.png")
        except Exception as e:
            print(f"Error saat membuat ikon default: {str(e)}")

if __name__ == "__main__":
    if check_and_install_dependencies():
        root = tk.Tk()
        app = WebCrawlerGUI(root)
        root.mainloop()
    else:
        print("Gagal menginstal dependensi yang diperlukan. Program tidak dapat dijalankan.")
        sys.exit(1)

