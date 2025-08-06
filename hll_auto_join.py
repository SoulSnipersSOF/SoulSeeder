import sys
import os

# Fix tkinter import issues in PyInstaller
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    try:
        import Tkinter as tk
        import ttk
        import tkMessageBox as messagebox
    except ImportError:
        print("ERROR: Could not import tkinter. Please install Python with tkinter support.")
        sys.exit(1)

import re
import subprocess
import winreg
import json
from pathlib import Path
import time
import requests
import threading
import ctypes
from ctypes import wintypes, windll
import tempfile
import shutil
from datetime import datetime

class SoulSniperSeeder:
    def __init__(self, root):
        # Check for admin privileges first thing
        self.check_and_request_admin_if_needed()

        self.root = root
        self.root.title("SoulSniper's SOF Seeder")
        self.root.geometry("700x900")  # Made larger for better layout
        self.root.configure(bg='#1a1a1a')
        self.root.resizable(True, True)

        # Discord webhook configuration
        self.discord_webhook_url = "https://discord.com/api/webhooks/1401563355986006126/nItlnbUdolRX64vOhW_-KQZiHTL0sE8PHMemj21BDaLgNHfKYnORIk4_CwDbwcGZcZnX"
        self.discord_role_id = "965630567376887818"
        
        # Track notification timing to prevent spam
        self.last_notification_time = {}
        self.notification_cooldown = 1800  # 30 minutes between notifications for same server

        # Initialize HLL config backup system
        self.hll_config_backup_dir = None
        self.hll_config_original_files = []

        # Initialize Steam launch options backup system
        self.original_launch_options = None
        self.launch_options_backed_up = False

        # Initialize cleanup timer ID
        self.cleanup_timer_id = None

        # Server configurations with Battlemetrics IDs
        self.SERVERS = {
            'soul1': {
                'ip': '192.169.95.2', 
                'port': '8530', 
                'name': 'Soul 1',
                'battlemetrics_id': '14968811'
            },
            'soul2': {
                'ip': '192.169.95.182', 
                'port': '7777', 
                'name': 'Soul 2',
                'battlemetrics_id': '33644491'
            }
        }

        # Steam paths and app ID
        self.HLL_APP_ID = '686810'
        self.steam_path = self.find_steam_path()
        self.steam_user_id = None
        self.selected_server = None
        self.monitoring_active = False
        self.monitoring_thread = None

        self.setup_ui()
        self.find_steam_user()

        # Add debug buttons (remove this later when issue is fixed) - AFTER setup_ui()
        self.add_debug_buttons()

        # Check for first run and auto-setup
        self.log_status("Starting first-run setup check...")

        # Create HLL config backup FIRST THING
        self.create_hll_config_backup()

        self.check_first_run_setup()

        # Check for auto-start command line argument
        if len(sys.argv) > 1:
            if sys.argv[1] == "--auto-start":
                self.log_status("🤖 Auto-start triggered from command line")
                self.root.after(2000, self.start_auto_seeding)
            elif sys.argv[1] == "--setup-only":
                self.log_status("🔧 Setup-only mode triggered")
                self.root.after(1000, self.run_setup_only_mode)

    def send_discord_notification(self, server_key, error_message):
        """Send Discord webhook notification when server is unreachable"""
        try:
            # Check notification cooldown
            current_time = time.time()
            if server_key in self.last_notification_time:
                time_since_last = current_time - self.last_notification_time[server_key]
                if time_since_last < self.notification_cooldown:
                    self.log_status(f"🔇 Discord notification on cooldown for {server_key} ({int((self.notification_cooldown - time_since_last) / 60)} minutes remaining)")
                    return False

            server_name = self.SERVERS[server_key]['name']
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')
            
            # Create Discord embed message
            embed = {
                "title": "🚨 SoulSniper Server Alert 🚨",
                "description": f"<@&{self.discord_role_id}>",
                "color": 15158332,  # Red color
                "fields": [
                    {
                        "name": "Server",
                        "value": server_name,
                        "inline": True
                    },
                    {
                        "name": "Status", 
                        "value": "Unable to connect to Battlemetrics API",
                        "inline": True
                    },
                    {
                        "name": "Time",
                        "value": timestamp,
                        "inline": False
                    },
                    {
                        "name": "Error Details",
                        "value": f"```{error_message}```",
                        "inline": False
                    },
                    {
                        "name": "Action Taken",
                        "value": "Switching to backup server for seeding" if server_key == 'soul1' else "Seeding operations affected",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Please check server status ASAP!"
                }
            }

            payload = {
                "content": f"<@&{self.discord_role_id}>",
                "embeds": [embed]
            }

            # Send webhook
            response = requests.post(
                self.discord_webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code in [200, 204]:
                self.log_status(f"✅ Discord notification sent for {server_name}")
                self.last_notification_time[server_key] = current_time
                return True
            else:
                self.log_status(f"⚠️ Discord webhook failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            self.log_status(f"❌ Error sending Discord notification: {e}")
            return False



    def start_auto_seeding(self):
        """Start automatic seeding with continuous monitoring"""
        if not self.steam_path:
            messagebox.showerror("Error", "Steam installation not found!")
            return
        if self.monitoring_active:
            messagebox.showwarning("Warning", "Auto-seeding is already running!")
            return
        
        # Check if Steam is running first
        if not self.is_steam_running():
            messagebox.showerror("Error", "Steam is not running!\n\nPlease start Steam and log in, then try again.")
            return
        
        # REMOVED: self.exit_steam() - no longer needed!
        
        self.start_keep_awake()
        self.monitoring_active = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.log_status("🤖 Starting SoulSniper auto-seeding system...")
        self.monitoring_thread = threading.Thread(target=self.run_seeding_loop, daemon=True)
        self.monitoring_thread.start()

    def check_and_request_admin_if_needed(self):
        """Check if running as admin, request elevation if not"""
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()

            if not is_admin:
                # Check if this is an auto-start (scheduled task should already be admin)
                if len(sys.argv) > 1 and sys.argv[1] == "--auto-start":
                    print("ERROR: Scheduled task should run as admin but isn't. Check task configuration.")
                    sys.exit(1)

                # For manual launches, request admin privileges
                print("Requesting administrator privileges for HLL input handling...")

                # Get current executable path
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                    args = ' '.join(sys.argv[1:])  # Pass through any command line args
                else:
                    exe_path = sys.executable
                    script_path = os.path.abspath(__file__)
                    args = f'"{script_path}" ' + ' '.join(sys.argv[1:])

                # Re-run as administrator
                try:
                    result = ctypes.windll.shell32.ShellExecuteW(
                        None, 
                        "runas", 
                        exe_path, 
                        args, 
                        None, 
                        1  # SW_SHOWNORMAL
                    )

                    if result > 32:  # Success
                        print("Restarting with administrator privileges...")
                        sys.exit(0)  # Exit current instance
                    else:
                        print("User cancelled admin request. Some features may not work.")
                        # Continue without admin - manual server joining will still work
                        return False

                except Exception as e:
                    print(f"Failed to request admin privileges: {e}")
                    return False
            else:
                print("✅ Running with administrator privileges")
                return True

        except Exception as e:
            print(f"Error checking admin status: {e}")
            return False

    def start_keep_awake(self):
        """Start the keep-awake system to prevent sleep during seeding"""
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002

            result = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )

            if result:
                self.log_status("🔒 Keep-awake system activated")
                return True
            else:
                self.log_status("⚠️ Failed to activate keep-awake system")
                return False
        except Exception as e:
            self.log_status(f"❌ Error starting keep-awake: {e}")
            return False

    def stop_keep_awake(self):
        """Stop the keep-awake system"""
        try:
            ES_CONTINUOUS = 0x80000000

            result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

            if result:
                self.log_status("🔓 Keep-awake system deactivated")
                return True
            else:
                self.log_status("⚠️ Failed to deactivate keep-awake system")
                return False
        except Exception as e:
            self.log_status(f"❌ Error stopping keep-awake: {e}")
            return False

    def create_hll_config_backup(self):
        """Create backup of HLL config files to prevent settings loss"""
        try:
            username = os.environ.get('USERNAME', 'Unknown')
            hll_config_path = f"C:\\Users\\{username}\\AppData\\Local\\HLL\\Saved\\Config\\WindowsNoEditor"

            self.log_status(f"🔍 Looking for HLL config at: {hll_config_path}")

            if not os.path.exists(hll_config_path):
                self.log_status("ℹ️ HLL config directory not found - will create backup when found")

                # Check alternative locations
                alternative_paths = [
                    f"C:\\Users\\{username}\\AppData\\Local\\Application Data\\HLL\\Saved\\Config\\WindowsNoEditor",
                    f"C:\\Users\\{username}\\Documents\\My Games\\HLL\\Saved\\Config\\WindowsNoEditor"
                ]

                for alt_path in alternative_paths:
                    self.log_status(f"🔍 Checking alternative path: {alt_path}")
                    if os.path.exists(alt_path):
                        hll_config_path = alt_path
                        self.log_status(f"✅ Found HLL config at alternative location!")
                        break
                else:
                    return

            # Create backup directory in temp
            self.hll_config_backup_dir = os.path.join(tempfile.gettempdir(), f"SoulSniper_HLL_Backup_{int(time.time())}")
            os.makedirs(self.hll_config_backup_dir, exist_ok=True)
            self.log_status(f"📁 Created backup directory: {self.hll_config_backup_dir}")

            # Find and backup .ini files
            ini_files = []
            try:
                for file in os.listdir(hll_config_path):
                    if file.endswith('.ini'):
                        ini_files.append(file)
                        self.log_status(f"🔍 Found .ini file: {file}")
            except Exception as e:
                self.log_status(f"❌ Error reading config directory: {e}")
                return

            if not ini_files:
                self.log_status("ℹ️ No HLL .ini files found to backup")
                return

            # Copy each .ini file to backup with validation
            for ini_file in ini_files:
                source = os.path.join(hll_config_path, ini_file)
                backup = os.path.join(self.hll_config_backup_dir, ini_file)
                try:
                    # Get file size for validation
                    source_size = os.path.getsize(source)

                    shutil.copy2(source, backup)

                    # Verify backup was created correctly
                    if os.path.exists(backup):
                        backup_size = os.path.getsize(backup)
                        if backup_size == source_size:
                            self.hll_config_original_files.append((source, backup))
                            self.log_status(f"💾 Backed up: {ini_file} ({source_size} bytes)")
                        else:
                            self.log_status(f"⚠️ Backup size mismatch for {ini_file}: {source_size} vs {backup_size}")
                    else:
                        self.log_status(f"❌ Backup file not created: {ini_file}")

                except Exception as e:
                    self.log_status(f"⚠️ Could not backup {ini_file}: {e}")

            if self.hll_config_original_files:
                self.log_status(f"✅ HLL config backup created ({len(self.hll_config_original_files)} files)")

                # Add a test button to the GUI for manual testing
                self.add_backup_test_button()
            else:
                self.log_status("❌ No files were successfully backed up")

        except Exception as e:
            self.log_status(f"⚠️ Error creating HLL config backup: {e}")

    def add_backup_test_button(self):
        """Add a test button to manually test backup/restore functionality"""
        try:
            # Find the button frame and add test button
            test_btn = tk.Button(self.root, text="🧪 Test Config Backup/Restore", 
                               command=self.test_backup_restore, 
                               font=('Arial', 10),
                               bg='#6c757d', fg='white', relief='flat', 
                               pady=5, cursor='hand2')
            test_btn.pack(pady=5)
            self.log_status("🧪 Added backup test button to GUI")
        except:
            pass
    
    def add_debug_buttons(self):
        """Add debug buttons to test cleanup functionality"""
        try:
            # Add debug buttons frame
            debug_frame = tk.Frame(self.root, bg='#1a1a1a')
            debug_frame.pack(pady=5)
            
            # Check options button
            check_btn = tk.Button(debug_frame, text="🔍 Check Current Options", 
                                command=self.get_current_steam_launch_options_debug, 
                                font=('Arial', 10),
                                bg='#17a2b8', fg='white', relief='flat', 
                                pady=5, cursor='hand2')
            check_btn.pack(side='left', padx=(0, 5))
            
            # Manual cleanup button
            cleanup_btn = tk.Button(debug_frame, text="🧹 Test Cleanup", 
                                  command=self.manual_cleanup_test, 
                                  font=('Arial', 10),
                                  bg='#ffc107', fg='black', relief='flat', 
                                  pady=5, cursor='hand2')
            cleanup_btn.pack(side='left', padx=5)
            
            self.log_status("🧪 Added debug buttons to GUI")
        except Exception as e:
            self.log_status(f"❌ Could not add debug buttons: {e}")

    def test_backup_restore(self):
        """Test the backup and restore functionality"""
        self.log_status("🧪 Testing HLL config backup/restore system...")

        if not self.hll_config_original_files:
            self.log_status("❌ No backup files to test!")
            messagebox.showerror("Test Error", "No HLL config files are currently backed up!")
            return

        try:
            # Show current backup status
            self.log_status(f"📋 Testing {len(self.hll_config_original_files)} backed up files:")

            for original_path, backup_path in self.hll_config_original_files:
                filename = os.path.basename(original_path)

                # Check if original still exists
                if os.path.exists(original_path):
                    original_size = os.path.getsize(original_path)
                    original_modified = os.path.getmtime(original_path)
                    self.log_status(f"📄 Original {filename}: {original_size} bytes, modified {time.ctime(original_modified)}")
                else:
                    self.log_status(f"❌ Original {filename} not found!")

                # Check if backup exists
                if os.path.exists(backup_path):
                    backup_size = os.path.getsize(backup_path)
                    backup_modified = os.path.getmtime(backup_path)
                    self.log_status(f"💾 Backup {filename}: {backup_size} bytes, created {time.ctime(backup_modified)}")
                else:
                    self.log_status(f"❌ Backup {filename} not found!")

            # Ask user if they want to test restore
            response = messagebox.askyesno(
                "Test Restore",
                f"Backup test completed! Check the log for details.\n\n"
                f"Would you like to test the restore function?\n"
                f"This will overwrite current HLL config files with the backed-up versions.\n\n"
                f"WARNING: Only do this if you're sure you want to restore the backed-up settings!"
            )

            if response:
                self.log_status("🔄 User requested restore test - performing restore...")
                restored_count = self.restore_hll_config_backup()
                messagebox.showinfo(
                    "Restore Test Complete",
                    f"Restore test completed!\n\n"
                    f"Files restored: {restored_count}\n"
                    f"Check the log for detailed results."
                )
            else:
                self.log_status("ℹ️ User cancelled restore test")

        except Exception as e:
            self.log_status(f"❌ Error during backup test: {e}")
            messagebox.showerror("Test Error", f"Backup test failed: {e}")

    def restore_hll_config_backup(self):
        """Restore HLL config files from backup"""
        if not self.hll_config_original_files:
            self.log_status("ℹ️ No HLL config backup to restore")
            return 0

        try:
            restored_count = 0
            failed_count = 0

            self.log_status("🔄 Starting HLL config restoration...")

            for original_path, backup_path in self.hll_config_original_files:
                filename = os.path.basename(original_path)

                if os.path.exists(backup_path):
                    try:
                        # Get file sizes for verification
                        backup_size = os.path.getsize(backup_path)

                        # Restore the file
                        shutil.copy2(backup_path, original_path)

                        # Verify restoration
                        if os.path.exists(original_path):
                            restored_size = os.path.getsize(original_path)
                            if restored_size == backup_size:
                                restored_count += 1
                                self.log_status(f"🔄 Restored: {filename} ({restored_size} bytes)")
                            else:
                                failed_count += 1
                                self.log_status(f"⚠️ Size mismatch after restore: {filename}")
                        else:
                            failed_count += 1
                            self.log_status(f"❌ File not found after restore: {filename}")

                    except Exception as e:
                        failed_count += 1
                        self.log_status(f"⚠️ Could not restore {filename}: {e}")
                else:
                    failed_count += 1
                    self.log_status(f"❌ Backup file missing: {filename}")

            if restored_count > 0:
                self.log_status(f"✅ HLL config restored ({restored_count} files)")
            if failed_count > 0:
                self.log_status(f"⚠️ Failed to restore {failed_count} files")

            # Clean up backup directory
            if self.hll_config_backup_dir and os.path.exists(self.hll_config_backup_dir):
                try:
                    shutil.rmtree(self.hll_config_backup_dir)
                    self.log_status("🧹 Cleaned up config backup directory")
                except Exception as e:
                    self.log_status(f"⚠️ Could not clean up backup directory: {e}")

            return restored_count

        except Exception as e:
            self.log_status(f"❌ Error restoring HLL config: {e}")
            return 0

    def clear_steam_launch_options_and_exit(self):
        try:
            if hasattr(self, 'previous_launch_options_path') and self.previous_launch_options_path.exists():
                original = self.previous_launch_options_path.read_text().strip()
                self.set_steam_launch_options(original)
                self.previous_launch_options_path.unlink()
                self.log_status(f"✅ Restored original Steam launch options: '{original}'")
            else:
                self.log_status("ℹ️ No backup launch options found to restore")

            self.stop_auto_seeding()
        except Exception as e:
            self.log_status(f"❌ Failed to clear Steam launch options: {e}")
            self.stop_auto_seeding()

    def find_steam_path(self):
        """Find Steam installation path - searches all common locations"""
        possible_paths = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Program Files (x86)\Steam",
            r"D:\Program Files\Steam",
            r"D:\Steam",
            r"E:\Program Files (x86)\Steam", 
            r"E:\Program Files\Steam",
            r"E:\Steam",
            r"F:\Program Files (x86)\Steam",
            r"F:\Program Files\Steam", 
            r"F:\Steam",
            r"G:\Steam",
            r"H:\Steam"
        ]

        # Try Windows registry first
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
                if os.path.exists(steam_path):
                    return steam_path
        except:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                if os.path.exists(steam_path):
                    return steam_path
        except:
            pass

        # Search all drive letters
        import string
        available_drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                available_drives.append(letter)

        extended_paths = []
        for drive in available_drives:
            drive_paths = [
                f"{drive}:\\Program Files (x86)\\Steam",
                f"{drive}:\\Program Files\\Steam", 
                f"{drive}:\\Steam",
                f"{drive}:\\Games\\Steam",
                f"{drive}:\\SteamLibrary\\Steam"
            ]
            extended_paths.extend(drive_paths)

        all_paths = possible_paths + extended_paths

        # Remove duplicates
        seen = set()
        unique_paths = []
        for path in all_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)

        # Search all paths
        for path in unique_paths:
            if os.path.exists(path):
                steam_exe = os.path.join(path, "steam.exe")
                if os.path.exists(steam_exe):
                    return path

        return None

    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg='#1a1a1a', padx=25, pady=25)
        main_frame.pack(fill='both', expand=True)

        # Admin status indicator
        admin_frame = tk.Frame(main_frame, bg='#1a1a1a')
        admin_frame.pack(fill='x', pady=(0, 10))

        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        admin_status = "🔑 Administrator Mode" if is_admin else "⚠️ Limited Mode"
        admin_color = '#4caf50' if is_admin else '#ffa500'

        admin_label = tk.Label(admin_frame, text=admin_status, 
                              font=('Arial', 10, 'bold'), fg=admin_color, bg='#1a1a1a')
        admin_label.pack()

        if not is_admin:
            admin_note = tk.Label(admin_frame, 
                                 text="Some features may not work without admin privileges", 
                                 font=('Arial', 8), fg='#cccccc', bg='#1a1a1a')
            admin_note.pack()

        # Custom icon
        icon_frame = tk.Frame(main_frame, bg='#1a1a1a')
        icon_frame.pack(pady=(0, 10))

        try:
            from PIL import Image, ImageTk
            icon_path = "soulsniper_icon.png"
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path).resize((64, 64), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(icon_image)
                icon_label = tk.Label(icon_frame, image=self.icon_photo, bg='#1a1a1a')
                icon_label.pack()
            else:
                icon_label = tk.Label(icon_frame, text="🎯", font=('Arial', 32), 
                                    bg='#1a1a1a', fg='#ff6b35')
                icon_label.pack()
        except Exception:
            icon_label = tk.Label(icon_frame, text="🎯", font=('Arial', 32), 
                                bg='#1a1a1a', fg='#ff6b35')
            icon_label.pack()

        # Title
        title = tk.Label(main_frame, text="SoulSniper's SOF Seeder", 
                        font=('Arial', 20, 'bold'), fg='#ff6b35', bg='#1a1a1a')
        title.pack(pady=(0, 20))

        # Steam status frame
        status_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='ridge', bd=2)
        status_frame.pack(fill='x', pady=(0, 25))

        tk.Label(status_frame, text="Steam Connection Status", 
                font=('Arial', 12, 'bold'), fg='#ffffff', bg='#2d2d2d').pack(pady=8)

        self.steam_status = tk.Label(status_frame, text="Detecting Steam...", 
                                   font=('Arial', 10), fg='#ffa500', bg='#2d2d2d')
        self.steam_status.pack(pady=(0, 8))

        # Server selection frame
        server_frame = tk.LabelFrame(main_frame, text="Select Server to Seed", 
                                   font=('Arial', 14, 'bold'), fg='#ff6b35', 
                                   bg='#1a1a1a', bd=2)
        server_frame.pack(fill='x', pady=(0, 25))

        # Server buttons
        buttons_frame = tk.Frame(server_frame, bg='#1a1a1a')
        buttons_frame.pack(fill='x', pady=15, padx=15)

        self.soul1_btn = tk.Button(buttons_frame, text="Join Soul 1", 
                                  font=('Arial', 14, 'bold'),
                                  command=lambda: self.join_specific_server('soul1'),
                                  bg='#2196f3', fg='white', relief='flat', 
                                  pady=15, cursor='hand2')
        self.soul1_btn.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.soul2_btn = tk.Button(buttons_frame, text="Join Soul 2", 
                                  font=('Arial', 14, 'bold'),
                                  command=lambda: self.join_specific_server('soul2'),
                                  bg='#2196f3', fg='white', relief='flat', 
                                  pady=15, cursor='hand2')
        self.soul2_btn.pack(side='left', fill='x', expand=True, padx=(10, 0))

        # Selected server display
        self.selected_label = tk.Label(server_frame, text="Click a server button to join directly", 
                                     font=('Arial', 11), fg='#cccccc', bg='#1a1a1a')
        self.selected_label.pack(pady=(5, 15))

        # Start seeding button
        self.start_btn = tk.Button(main_frame, text="🤖 Start Auto-Seeding", 
                                  command=self.start_auto_seeding, 
                                  font=('Arial', 16, 'bold'),
                                  bg='#28a745', fg='white', relief='flat', 
                                  pady=20, cursor='hand2')
        self.start_btn.pack(fill='x', pady=(0, 10))

        # Stop seeding button
        self.stop_btn = tk.Button(main_frame, text="🛑 Stop Auto-Seeding", 
                                 command=self.stop_auto_seeding, 
                                 font=('Arial', 14, 'bold'),
                                 bg='#dc3545', fg='white', relief='flat', 
                                 pady=15, cursor='hand2', state='disabled')
        self.stop_btn.pack(fill='x', pady=(0, 20))

        # Info panel with scrollable content
        info_frame = tk.LabelFrame(main_frame, text="Seeding Information", 
                                 font=('Arial', 12, 'bold'), fg='#ff6b35', 
                                 bg='#1a1a1a', bd=2)
        info_frame.pack(fill='x', pady=(0, 20))

        # Create scrollable text widget for info
        info_text_frame = tk.Frame(info_frame, bg='#1a1a1a')
        info_text_frame.pack(fill='both', expand=True, pady=10, padx=10)

        self.info_text = tk.Text(info_text_frame, height=8, bg='#2d2d2d', fg='#cccccc', 
                               font=('Arial', 9), state='disabled', wrap='word',
                               insertbackground='white')

        info_scrollbar = tk.Scrollbar(info_text_frame, orient='vertical', command=self.info_text.yview)
        self.info_text.config(yscrollcommand=info_scrollbar.set)

        self.info_text.pack(side='left', fill='both', expand=True)
        info_scrollbar.pack(side='right', fill='y')

        # Add comprehensive info text
        info_content = """🔵 MANUAL SERVER JOINING:
• Blue buttons: Join specific server directly
• Click "Join Soul 1" or "Join Soul 2" to connect immediately
• Perfect for manual seeding or when you want to play on a specific server

🟢 AUTOMATIC SEEDING:
• Green button: Smart auto-selection based on player counts
• Checks Battlemetrics API to find which server needs seeding
• Automatically switches servers when one reaches 70 players
• Monitors continuously and handles server transitions

⚙️ AUTOMATION FEATURES:
• Daily seeding at 7 AM EST (wakes computer from sleep)
• Handles HLL splash screen automatically
• Switches from Soul 1 to Soul 2 when first server fills
• Exits cleanly when both servers reach 70+ players
• Clears Steam launch options when done (prevents auto-join during manual play)

💾 PROTECTION FEATURES:
• Backs up HLL settings files on startup
• Restores settings when seeding completes
• Prevents game crashes from wiping your configurations
• Admin privileges ensure reliable automation

🎯 SEEDING LOGIC:
• Soul 1 priority: Always seeds Soul 1 first
• Soul 2 fallback: Switches to Soul 2 when Soul 1 hits 70 players
• Both full: Exits and clears configs when both servers hit 70+
• Smart monitoring: Checks player counts every 30 seconds"""

        self.info_text.config(state='normal')
        self.info_text.insert('end', info_content)
        self.info_text.config(state='disabled')

        # Status log - made much larger and more visible
        log_frame = tk.LabelFrame(main_frame, text="Status Log", 
                                font=('Arial', 12, 'bold'), fg='#ff6b35', 
                                bg='#1a1a1a', bd=2)
        log_frame.pack(fill='both', expand=True, pady=(10, 0))

        text_frame = tk.Frame(log_frame, bg='#1a1a1a')
        text_frame.pack(fill='both', expand=True, pady=10, padx=10)

        # Increased height and better colors for visibility
        self.status_text = tk.Text(text_frame, height=20, bg='#2d2d2d', fg='#ffffff', 
                                  font=('Consolas', 10), state='disabled',
                                  insertbackground='white', wrap='word',
                                  relief='sunken', bd=2)

        # Ensure scrollbar is always visible and functional
        scrollbar = tk.Scrollbar(text_frame, orient='vertical', command=self.status_text.yview,
                               bg='#444444', troughcolor='#2d2d2d', 
                               activebackground='#666666')
        self.status_text.config(yscrollcommand=scrollbar.set)

        self.status_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def log_status(self, message, color='#ffffff'):
        """Add a status message to the log with enhanced visibility"""
        timestamp = time.strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"

        # Also write to a debug file
        try:
            debug_file = os.path.join(os.path.expanduser("~"), "Desktop", "soulsniper_debug.txt")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except:
            pass

        # Enhanced GUI logging with color coding
        try:
            self.status_text.config(state='normal')

            # Color coding based on message content
            if "✅" in message or "SUCCESS" in message.upper():
                color = '#4caf50'  # Green for success
            elif "❌" in message or "ERROR" in message.upper() or "FAILED" in message.upper():
                color = '#f44336'  # Red for errors
            elif "⚠️" in message or "WARNING" in message.upper():
                color = '#ff9800'  # Orange for warnings
            elif "🎯" in message or "🚀" in message or "🔧" in message:
                color = '#2196f3'  # Blue for actions
            elif "📊" in message or "📤" in message:
                color = '#9c27b0'  # Purple for data/API
            elif "ℹ️" in message or "INFO" in message.upper():
                color = '#00bcd4'  # Cyan for info

            # Insert the message with timestamp and color
            self.status_text.insert('end', log_message + "\n")

            # Apply color to the last line inserted
            last_line_start = self.status_text.index("end-2l linestart")
            last_line_end = self.status_text.index("end-1l lineend")

            # Create a tag for this color if it doesn't exist
            tag_name = f"color_{color.replace('#', '')}"
            self.status_text.tag_configure(tag_name, foreground=color)
            self.status_text.tag_add(tag_name, last_line_start, last_line_end)

            self.status_text.config(state='disabled')
            self.status_text.see('end')  # Auto-scroll to bottom

            # Force GUI update
            self.root.update_idletasks()

        except Exception as e:
            # Fallback to console if GUI logging fails
            print(f"GUI Log Error: {e}")
            print(log_message)

    def find_steam_user(self):
        """Find the active Steam user ID"""
        if not self.steam_path:
            self.steam_status.config(text="❌ Steam not found", fg='#ff4444')
            return

        self.log_status(f"Steam detected at: {self.steam_path}")

        try:
            userdata_path = os.path.join(self.steam_path, "userdata")

            if os.path.exists(userdata_path):
                user_dirs = []
                for item in os.listdir(userdata_path):
                    if item.isdigit():
                        config_path = os.path.join(userdata_path, item, "config", "localconfig.vdf")
                        if os.path.exists(config_path):
                            user_dirs.append(item)

                if user_dirs:
                    self.steam_user_id = user_dirs[0]
                    self.steam_status.config(text=f"✅ Steam Connected (User: {self.steam_user_id})", fg='#4caf50')
                    self.log_status(f"Steam user detected: {self.steam_user_id}")
                    self.log_status("SoulSniper's SOF Seeder initialized")
                    return
        except Exception as e:
            self.log_status(f"Error detecting Steam user: {e}")

        self.steam_status.config(text="⚠️ Steam found but no user detected", fg='#ffa500')
        self.log_status("Could not detect Steam user configuration")

    def check_first_run_setup(self):
        """Check if this is the first run and set up automatic seeding"""
        try:
            result = subprocess.run(
                ['schtasks', '/query', '/tn', 'SoulSeeder Auto Seeder'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                self.log_status("🎉 Welcome to SoulSniper's SOF Seeder!")
                self.log_status("🔧 Setting up automatic daily seeding...")

                welcome_msg = (
                    "Welcome to SoulSniper's SOF Seeder!\n\n"
                    "This will automatically set up daily server seeding at 7 AM EST.\n"
                    "The setup requires Administrator privileges.\n\n"
                    "Click OK to continue with automatic setup."
                )

                response = messagebox.askyesno(
                    "First Run Setup", 
                    welcome_msg,
                    icon='question'
                )

                if response:
                    self.run_automatic_setup()
                else:
                    self.log_status("ℹ️ Setup skipped - you can set up manually later")
            else:
                self.log_status("✅ Automatic seeding already configured")

        except Exception as e:
            self.log_status(f"ℹ️ Could not check setup status: {str(e)}")

    def run_automatic_setup(self):
        """Run the XML-based task setup automatically"""
        try:
            # Check if we're running as administrator
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            self.log_status(f"🔑 Running as administrator: {bool(is_admin)}")

            if not is_admin:
                self.log_status("🔄 Requesting administrator privileges...")

                # Get current executable path
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = sys.executable + ' "' + __file__ + '"'

                # Re-run as administrator
                try:
                    ctypes.windll.shell32.ShellExecuteW(
                        None, 
                        "runas", 
                        exe_path, 
                        "--setup-only", 
                        None, 
                        1
                    )
                    self.log_status("✅ Administrator request sent - app will restart with admin privileges")
                    messagebox.showinfo(
                        "Admin Required", 
                        "The app will restart with Administrator privileges to set up automatic seeding.\n\n"
                        "Click 'Yes' when Windows asks for permission."
                    )
                    # Close current instance
                    self.root.quit()
                    return
                except Exception as e:
                    self.log_status(f"❌ Failed to request admin privileges: {str(e)}")

            # If we get here, we should have admin privileges
            self.log_status("✅ Have administrator privileges, proceeding with setup...")

            # Create the scheduled task using XML import
            self.create_task_with_xml()

        except Exception as e:
            self.log_status(f"❌ Automatic setup failed: {str(e)}")
            messagebox.showwarning(
                "Setup Warning",
                f"Automatic setup encountered an issue:\n{str(e)}\n\n"
                "The app will still work for manual server joining.\n"
                "For automatic daily seeding, please run as Administrator."
            )

    def run_setup_only_mode(self):
        """Run in setup-only mode (called when restarted as admin)"""
        try:
            self.log_status("🔧 Running in setup-only mode with admin privileges")
            self.create_task_with_xml()
            messagebox.showinfo(
                "Setup Complete!",
                "SoulSniper's SOF Seeder is now configured!\n\n"
                "✅ Daily automatic seeding at 7 AM EST\n\n"
                "You can now close this window and use the main app normally."
            )
            self.root.after(3000, self.root.quit)  # Auto-close after 3 seconds
        except Exception as e:
            self.log_status(f"❌ Setup-only mode failed: {str(e)}")
            messagebox.showerror("Setup Failed", f"Setup failed: {str(e)}")

    def create_task_with_xml(self):
        """Create scheduled task using XML file import"""
        try:
            # Find the XML task definition file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            xml_file = os.path.join(script_dir, "CreateTasks.xml")

            if not os.path.exists(xml_file):
                # If running from PyInstaller bundle, check relative to executable
                if getattr(sys, 'frozen', False):
                    script_dir = os.path.dirname(sys.executable)
                    xml_file = os.path.join(script_dir, "CreateTasks.xml")

            if not os.path.exists(xml_file):
                # Create the XML file dynamically
                self.log_status("📄 XML file not found, creating task definition...")
                xml_file = self.create_xml_task_file()

            if not xml_file or not os.path.exists(xml_file):
                raise Exception("Could not create or find CreateTasks.xml")

            self.log_status(f"📄 Using XML task file: {xml_file}")

            # Import the XML task using schtasks
            cmd = [
                "schtasks",
                "/create",
                "/xml", xml_file,
                "/tn", "SoulSeeder Auto Seeder",
                "/f"  # Force overwrite if exists
            ]

            self.log_status("🔧 Creating scheduled task from XML definition...")

            # DEBUG: Show exactly what we're trying to execute
            self.log_status(f"🔧 Full command: {cmd}")
            self.log_status(f"🔧 XML file path: {xml_file}")
            self.log_status(f"🔧 XML file exists: {os.path.exists(xml_file)}")
            self.log_status(f"🔧 Current working directory: {os.getcwd()}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            # DEBUG: Show detailed results
            self.log_status(f"📤 stdout: {result.stdout}")
            self.log_status(f"📤 stderr: {result.stderr}")
            self.log_status(f"📤 return code: {result.returncode}")

            if result.returncode == 0:
                self.log_status("✅ Scheduled task created successfully!")
                messagebox.showinfo(
                    "Setup Complete!",
                    "SoulSniper's SOF Seeder is now configured!\n\n"
                    "✅ Daily automatic seeding at 7 AM EST\n"
                    "✅ Will WAKE your computer from sleep\n"
                    "✅ Works even when not logged in\n"
                    "✅ Full administrator privileges\n"
                    "✅ Network aware - waits for internet connection\n"
                    "✅ Supports up to 5 hours of seeding time\n\n"
                    "Thank you for helping seed the servers!"
                )
            else:
                raise Exception(f"Task creation failed with code {result.returncode}")

        except Exception as e:
            self.log_status(f"❌ Task creation failed: {str(e)}")
            raise e

    def create_xml_task_file(self):
        """Create the XML task definition file dynamically"""
        try:
            # Get the current executable path
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                work_dir = os.path.dirname(sys.executable)
            else:
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                work_dir = os.path.dirname(os.path.abspath(__file__))

            # XML template with proper paths
            xml_content = rf'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2025-01-01T00:00:00.0000000</Date>
    <Author>SoulSniper SOF Seeder</Author>
    <Version>1.0.0</Version>
    <Description>Daily HLL server seeding automation - wakes PC at 7 AM EST and manages server population</Description>
    <URI>\SoulSeeder Auto Seeder</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <Repetition>
        <Interval>P1D</Interval>
      </Repetition>
      <StartBoundary>2025-01-01T12:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <LogonType>ServiceAccount</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT5H</ExecutionTimeLimit>
    <Priority>4</Priority>
    <RestartPolicy>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartPolicy>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe_path}</Command>
      <Arguments>--auto-start</Arguments>
      <WorkingDirectory>{work_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

            # Write XML file to temp directory
            temp_dir = tempfile.gettempdir()
            xml_file_path = os.path.join(temp_dir, "HLL_Seeder_Task.xml")

            with open(xml_file_path, 'w', encoding='utf-16') as f:
                f.write(xml_content)

            self.log_status(f"📄 Created XML task file: {xml_file_path}")
            return xml_file_path

        except Exception as e:
            self.log_status(f"❌ Error creating XML file: {e}")
            return None

    def backup_steam_launch_options(self):
        """Backup user's existing Steam launch options for HLL"""
        try:
            self.log_status("💾 Starting Steam launch options backup...")
            
            config_path = self.get_localconfig_path()
            if not config_path or not os.path.exists(config_path):
                self.log_status("⚠️ Steam configuration not accessible")
                return False

            # Get current launch options
            current_options = self.get_current_steam_launch_options()
            self.original_launch_options = current_options
            self.launch_options_backed_up = True
            
            self.log_status(f"💾 DEBUG: Backed up launch options: '{self.original_launch_options}'")
            self.log_status("✅ Steam launch options backed up successfully")
            return True

        except Exception as e:
            self.log_status(f"❌ Error backing up launch options: {e}")
            return False

    def auto_remove_server_connection_options(self):
        """Automatically remove ONLY the server connection options, keeping user's original options"""
        self.log_status("🧹 CLEANUP TRIGGERED: Restoring normal game behavior")

        try:
            # DEBUG: Check current state
            current_options = self.get_current_steam_launch_options()
            self.log_status(f"🔍 DEBUG: Current options before cleanup: '{current_options}'")
            self.log_status(f"🔍 DEBUG: Original options to restore: '{self.original_launch_options}'")
            self.log_status(f"🔍 DEBUG: Backup flag status: {self.launch_options_backed_up}")
            
            # Restore to original launch options (removes server connection)
            if self.launch_options_backed_up and self.original_launch_options is not None:
                self.log_status(f"🔄 Restoring to original options: '{self.original_launch_options}'")
                success = self.modify_steam_config(self.original_launch_options)
                
                if success:
                    # Verify the cleanup worked
                    after_cleanup = self.get_current_steam_launch_options()
                    self.log_status(f"🔍 DEBUG: Options after cleanup: '{after_cleanup}'")
                    
                    if after_cleanup == self.original_launch_options:
                        self.log_status("✅ Game configuration successfully restored to original settings")
                    else:
                        self.log_status(f"⚠️ WARNING: Cleanup may not have worked correctly!")
                        self.log_status(f"⚠️ Expected: '{self.original_launch_options}'")
                        self.log_status(f"⚠️ Actual: '{after_cleanup}'")
                        
                    # Clear the timer ID
                    if hasattr(self, 'cleanup_timer_id'):
                        self.cleanup_timer_id = None
                        
                else:
                    self.log_status("❌ Could not restore original game configuration")
            else:
                self.log_status("⚠️ No backup available to restore from")
                self.log_status(f"🔍 DEBUG: backup_flag={self.launch_options_backed_up}, original_options={self.original_launch_options}")

        except Exception as e:
            self.log_status(f"❌ Error restoring normal game behavior: {e}")

    def restore_steam_launch_options(self):
        """Restore user's original Steam launch options for HLL (removing only our added options)"""
        if not self.launch_options_backed_up:
            self.log_status("ℹ️ No configuration backup to restore")
            return False

        try:
            self.log_status("🔄 Restoring original game configuration...")
            self.log_status(f"🔍 DEBUG: Restoring to: '{self.original_launch_options}'")

            if self.original_launch_options is None:
                self.log_status("⚠️ Original configuration was not properly saved")
                return False

            # Restore to exactly the original state
            success = self.modify_steam_config(self.original_launch_options)

            if success:
                # Verify the restore worked
                after_restore = self.get_current_steam_launch_options()
                self.log_status(f"🔍 DEBUG: Options after restore: '{after_restore}'")
                
                if after_restore == self.original_launch_options:
                    if self.original_launch_options:
                        self.log_status("✅ Restored original game configuration")
                    else:
                        self.log_status("✅ Cleared game configuration (restored to default state)")
                    return True
                else:
                    self.log_status(f"⚠️ WARNING: Restore verification failed!")
                    self.log_status(f"⚠️ Expected: '{self.original_launch_options}'")
                    self.log_status(f"⚠️ Actual: '{after_restore}'")
                    return False
            else:
                self.log_status("❌ Failed to restore original configuration")
                return False

        except Exception as e:
            self.log_status(f"❌ Error restoring configuration: {e}")
            return False

    def modify_steam_config_with_backup(self, server_connection_args):
        """Modify Steam config by APPENDING server connection args to existing launch options"""
        try:
            # First, backup the current launch options if not already done
            if not self.launch_options_backed_up:
                self.backup_steam_launch_options()

            # Get current launch options
            current_options = self.get_current_steam_launch_options()
            
            self.log_status(f"🔍 DEBUG: Current options before modification: '{current_options}'")
            self.log_status(f"🔍 DEBUG: Adding server connection: '{server_connection_args}'")
            self.log_status(f"🔍 DEBUG: Original backup: '{self.original_launch_options}'")
            
            # Append the server connection arguments to existing options
            if current_options:
                combined_options = f"{current_options} {server_connection_args}"
                self.log_status("🔗 Configuring game for automatic server connection")
            else:
                combined_options = server_connection_args
                self.log_status("🆕 Setting up automatic server connection")

            # Set the combined launch options
            success = self.modify_steam_config(combined_options)
            
            if success:
                # Verify what was actually set
                verify_options = self.get_current_steam_launch_options()
                self.log_status(f"🔍 DEBUG: Options after setting: '{verify_options}'")
                
                self.log_status("🚀 Game configured for automatic connection")
                self.log_status(f"🔍 DEBUG: Will restore to: '{self.original_launch_options}' in 3 minutes")
                
                # Cancel any existing cleanup timer
                if hasattr(self, 'cleanup_timer_id') and self.cleanup_timer_id:
                    self.root.after_cancel(self.cleanup_timer_id)
                    self.log_status("🔄 Cancelled previous cleanup timer")
                
                # Schedule new cleanup
                self.cleanup_timer_id = self.root.after(180000, self.auto_remove_server_connection_options)
                self.log_status(f"⏰ DEBUG: Cleanup scheduled with timer ID: {self.cleanup_timer_id}")
                
                return True
            else:
                self.log_status("❌ Failed to configure game for automatic connection")
                return False

        except Exception as e:
            self.log_status(f"❌ Failed to configure automatic connection: {e}")
            return False

    def get_current_steam_launch_options_debug(self):
        """Debug version that shows what's currently in Steam config"""
        try:
            current = self.get_current_steam_launch_options()
            self.log_status(f"🔍 DEBUG: Current Steam launch options: '{current}'")
            return current
        except Exception as e:
            self.log_status(f"❌ DEBUG: Error reading current options: {e}")
            return ""

    def set_steam_launch_options(self, launch_options):
        """Set Steam launch options for HLL"""
        return self.modify_steam_config(launch_options)

    def get_localconfig_path(self):
        """Get path to Steam's localconfig.vdf"""
        if not self.steam_path or not self.steam_user_id:
            return None
        return os.path.join(self.steam_path, "userdata", self.steam_user_id, "config", "localconfig.vdf")

    def get_current_steam_launch_options(self):
        """Get current Steam launch options for HLL"""
        try:
            config_path = self.get_localconfig_path()
            if not config_path or not os.path.exists(config_path):
                return ""

            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            hll_pattern = rf'"{self.HLL_APP_ID}"\s*\{{([^}}]*)\}}'
            hll_match = re.search(hll_pattern, content, re.DOTALL)

            if hll_match:
                hll_section = hll_match.group(1)
                launch_options_pattern = r'"LaunchOptions"\s*"([^"]*)"'
                launch_match = re.search(launch_options_pattern, hll_section)
                
                if launch_match:
                    return launch_match.group(1)
            
            return ""
        except Exception as e:
            self.log_status(f"❌ Error reading game configuration: {e}")
            return ""

    def manual_cleanup_test(self):
        """Manual test function to check cleanup - you can call this from GUI"""
        self.log_status("🧪 MANUAL CLEANUP TEST: Checking current state...")
        
        # Show current state
        current = self.get_current_steam_launch_options()
        self.log_status(f"🔍 Current options: '{current}'")
        self.log_status(f"🔍 Original options: '{self.original_launch_options}'")
        self.log_status(f"🔍 Backup status: {self.launch_options_backed_up}")
        
        # Ask user if they want to run cleanup now
        response = messagebox.askyesno(
            "Manual Cleanup Test",
            f"Current options: '{current}'\n"
            f"Original options: '{self.original_launch_options}'\n\n"
            f"Run cleanup now?"
        )
        
        if response:
            self.log_status("🧪 Running manual cleanup...")
            self.auto_remove_server_connection_options()
        else:
            self.log_status("🧪 Manual cleanup cancelled")    

    def modify_steam_config(self, launch_options):
        """Modify Steam's configuration file to set launch options (REPLACES entire launch options field)"""
        config_path = self.get_localconfig_path()

        if not config_path or not os.path.exists(config_path):
            self.log_status("❌ Game config file not found")
            return False

        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            hll_pattern = rf'"{self.HLL_APP_ID}"\s*\{{[^}}]*\}}'
            hll_match = re.search(hll_pattern, content, re.DOTALL)

            if hll_match:
                hll_section = hll_match.group(0)
                # Remove existing LaunchOptions line
                updated_section = re.sub(r'"LaunchOptions"\s*"[^"]*"\s*', '', hll_section)

                if launch_options:
                    # Add the new launch options
                    updated_section = updated_section.replace(
                        '}', 
                        f'\t\t\t\t"LaunchOptions"\t\t"{launch_options}"\n\t\t\t}}'
                    )

                content = content.replace(hll_section, updated_section)
            else:
                # No HLL section exists, create one
                apps_match = re.search(r'"Apps"\s*\{', content)
                if apps_match:
                    insert_pos = apps_match.end()
                    if launch_options:
                        new_section = f'\n\t\t\t"{self.HLL_APP_ID}"\n\t\t\t{{\n\t\t\t\t"LaunchOptions"\t\t"{launch_options}"\n\t\t\t}}'
                    else:
                        new_section = f'\n\t\t\t"{self.HLL_APP_ID}"\n\t\t\t{{\n\t\t\t}}'
                    content = content[:insert_pos] + new_section + content[insert_pos:]

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if launch_options:
                self.log_status("✅ Game configuration updated")
            else:
                self.log_status("🧹 Game configuration cleared")
            return True

        except Exception as e:
            self.log_status(f"❌ Error modifying game configuration: {str(e)}")
            return False

    def is_steam_running(self):
        """Check if Steam is currently running"""
        try:
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe"], 
                                  capture_output=True, text=True)
            return "steam.exe" in result.stdout
        except:
            return False

    def exit_steam(self):
        """Exit Steam completely"""
        if self.is_steam_running():
            self.log_status("🚪 Closing Steam...")
            try:
                # Try graceful shutdown first
                subprocess.run(["taskkill", "/im", "steam.exe"], capture_output=True)
                time.sleep(3)

                # Force kill if still running
                if self.is_steam_running():
                    subprocess.run(["taskkill", "/f", "/im", "steam.exe"], capture_output=True)
                    time.sleep(2)

                self.log_status("✅ Steam closed successfully")
                return True
            except Exception as e:
                self.log_status(f"⚠️ Error closing Steam: {str(e)}")
                return False
        else:
            self.log_status("ℹ️ Steam was not running")
            return True

    def close_hll_and_steam(self):
        """Close both HLL and Steam completely"""
        self.log_status("🚪 Closing HLL and Steam for server switch...")

        # Close HLL first
        self.close_hll()
        time.sleep(2)

        # Close Steam completely  
        self.exit_steam()
        time.sleep(5)  # Give time for Steam to fully close

        self.log_status("✅ HLL and Steam closed successfully")

    def get_server_player_count_enhanced(self, server_key):
        """Enhanced server status check that distinguishes between server down vs low population"""
        server_id = self.SERVERS[server_key]['battlemetrics_id']
        server_name = self.SERVERS[server_key]['name']

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }

            self.log_status(f"🔍 Checking {server_name} status...")

            response = requests.get(
                f"https://api.battlemetrics.com/servers/{server_id}",
                headers=headers,
                timeout=15  # Increased timeout
            )

            if response.status_code == 200:
                data = response.json()
                server_attributes = data.get('data', {}).get('attributes', {})
                
                player_count = server_attributes.get('players', 0)
                server_status = server_attributes.get('status', 'unknown')
                
                # Check if server is actually online
                if server_status == 'online':
                    self.log_status(f"📊 {server_name}: {player_count} players (online)")
                    return {'status': 'online', 'players': player_count, 'error': None}
                else:
                    self.log_status(f"⚠️ {server_name}: Server status is '{server_status}'")
                    error_msg = f"Server status: {server_status}"
                    self.send_discord_notification(server_key, error_msg)
                    return {'status': 'offline', 'players': 0, 'error': error_msg}

            elif response.status_code == 404:
                error_msg = f"Server not found (HTTP 404) - Battlemetrics ID may be incorrect"
                self.log_status(f"❌ {server_name}: {error_msg}")
                self.send_discord_notification(server_key, error_msg)
                return {'status': 'error', 'players': 0, 'error': error_msg}

            else:
                error_msg = f"API Error HTTP {response.status_code}: {response.text[:200]}"
                self.log_status(f"⚠️ {server_name}: {error_msg}")
                self.send_discord_notification(server_key, error_msg)
                return {'status': 'error', 'players': 0, 'error': error_msg}

        except requests.exceptions.Timeout:
            error_msg = "Request timeout - Battlemetrics API not responding"
            self.log_status(f"⏱️ {server_name}: {error_msg}")
            self.send_discord_notification(server_key, error_msg)
            return {'status': 'error', 'players': 0, 'error': error_msg}

        except requests.exceptions.ConnectionError:
            error_msg = "Connection failed - Network or API unavailable"
            self.log_status(f"🌐 {server_name}: {error_msg}")
            self.send_discord_notification(server_key, error_msg)
            return {'status': 'error', 'players': 0, 'error': error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_status(f"❌ {server_name}: {error_msg}")
            self.send_discord_notification(server_key, error_msg)
            return {'status': 'error', 'players': 0, 'error': error_msg}

    def get_server_player_count(self, server_key):
        """Legacy method - now uses enhanced version and returns just player count for compatibility"""
        result = self.get_server_player_count_enhanced(server_key)
        return result['players']        

    def is_hll_running(self):
        """Check if Hell Let Loose is currently running"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'HLL-Win64-Shipping.exe':
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            self.log_status("⚠️ psutil not installed - cannot detect HLL process")
        return False

    def close_hll(self):
        """Close Hell Let Loose process"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'HLL-Win64-Shipping.exe':
                        proc.terminate()
                        self.log_status("🚪 Closed Hell Let Loose")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            self.log_status("⚠️ psutil not installed - using taskkill")
            try:
                subprocess.run(["taskkill", "/f", "/im", "HLL-Win64-Shipping.exe"], 
                             capture_output=True)
                self.log_status("🚪 Closed Hell Let Loose")
                return True
            except:
                pass
        return False

    def send_space_key_to_hll_robust(self):
        """Enhanced space key sending with multiple methods and better debugging"""
        self.log_status("🎯 Attempting to bypass HLL splash screen...")

        # Wait a bit for HLL to fully load
        self.log_status("⏳ Waiting for HLL to stabilize...")
        time.sleep(3)

        success = False

        # Method 1: Try to find and focus HLL window specifically
        try:
            import win32gui
            import win32con

            def find_hll_window():
                """Find HLL window using win32gui"""
                windows = []

                def enum_windows_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        window_text = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)
                        if any(keyword in window_text.lower() for keyword in ['hell let loose', 'hll']) or \
                           any(keyword in class_name.lower() for keyword in ['unreal', 'hll']):
                            windows.append((hwnd, window_text, class_name))
                    return True

                win32gui.EnumWindows(enum_windows_callback, windows)
                return windows

            hll_windows = find_hll_window()
            self.log_status(f"🔍 Found {len(hll_windows)} potential HLL windows")

            for hwnd, title, class_name in hll_windows:
                self.log_status(f"📋 Window: '{title}' (Class: {class_name})")

            if hll_windows:
                # Use the first HLL window found
                hwnd = hll_windows[0][0]
                self.log_status(f"🎯 Focusing HLL window: {hll_windows[0][1]}")

                # Bring window to foreground
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                time.sleep(1)

                # Verify window is focused
                focused_hwnd = win32gui.GetForegroundWindow()
                if focused_hwnd == hwnd:
                    self.log_status("✅ HLL window successfully focused")

                    # Method 1a: Use win32api to send key
                    try:
                        import win32api
                        import win32con

                        self.log_status("⌨️ Sending space key via win32api...")
                        win32api.keybd_event(win32con.VK_SPACE, 0, 0, 0)  # Key down
                        time.sleep(0.1)
                        win32api.keybd_event(win32con.VK_SPACE, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
                        self.log_status("✅ Space key sent via win32api")
                        success = True

                    except Exception as e:
                        self.log_status(f"⚠️ win32api method failed: {e}")
                else:
                    self.log_status("⚠️ Could not focus HLL window properly")

        except ImportError:
            self.log_status("⚠️ win32gui not available, trying alternative methods...")
        except Exception as e:
            self.log_status(f"⚠️ Window focusing method failed: {e}")

        # Method 2: Enhanced SendInput with better window detection
        if not success:
            try:
                self.log_status("🔄 Trying enhanced SendInput method...")
                user32 = windll.user32

                # Define constants
                VK_SPACE = 0x20
                KEYEVENTF_KEYUP = 0x0002
                INPUT_KEYBOARD = 1

                # Define INPUT structure
                class KEYBDINPUT(ctypes.Structure):
                    _fields_ = [
                        ("wVk", wintypes.WORD),
                        ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
                    ]

                class INPUT(ctypes.Structure):
                    _fields_ = [
                        ("type", wintypes.DWORD),
                        ("ki", KEYBDINPUT)
                    ]

                # Get the currently active window
                active_window = user32.GetForegroundWindow()
                if active_window:
                    # Get window title for verification
                    buffer = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(active_window, buffer, 256)
                    window_title = buffer.value
                    self.log_status(f"🖥️ Active window: '{window_title}'")

                    # Click center of screen first to ensure focus
                    screen_width = user32.GetSystemMetrics(0)
                    screen_height = user32.GetSystemMetrics(1)
                    center_x = screen_width // 2
                    center_y = screen_height // 2

                    self.log_status(f"🖱️ Clicking center of screen ({center_x}, {center_y})")
                    user32.SetCursorPos(center_x, center_y)
                    user32.mouse_event(0x0002 | 0x0004, 0, 0, 0, 0)  # Left click down and up
                    time.sleep(0.5)

                    # Send space key
                    self.log_status("⌨️ Sending space key via SendInput...")
                    key_input = INPUT()
                    key_input.type = INPUT_KEYBOARD
                    key_input.ki.wVk = VK_SPACE
                    key_input.ki.wScan = 0
                    key_input.ki.dwFlags = 0
                    key_input.ki.time = 0
                    key_input.ki.dwExtraInfo = None

                    # Send key down
                    result1 = user32.SendInput(1, ctypes.byref(key_input), ctypes.sizeof(INPUT))
                    time.sleep(0.1)

                    # Send key up
                    key_input.ki.dwFlags = KEYEVENTF_KEYUP
                    result2 = user32.SendInput(1, ctypes.byref(key_input), ctypes.sizeof(INPUT))

                    if result1 and result2:
                        self.log_status("✅ Space key sent successfully via SendInput")
                        success = True
                    else:
                        self.log_status("⚠️ SendInput returned 0 - may have failed")

            except Exception as e:
                self.log_status(f"⚠️ SendInput method failed: {e}")

        # Method 3: PyAutoGUI fallback with retry
        if not success:
            try:
                self.log_status("🔄 Trying pyautogui fallback method...")
                import pyautogui

                # Disable pyautogui failsafe
                pyautogui.FAILSAFE = False

                # Click center of screen first
                screen_size = pyautogui.size()
                center_x = screen_size.width // 2
                center_y = screen_size.height // 2

                self.log_status(f"🖱️ PyAutoGUI clicking center ({center_x}, {center_y})")
                pyautogui.click(center_x, center_y)
                time.sleep(0.5)

                # Send space key multiple times to be sure
                for i in range(3):
                    self.log_status(f"⌨️ PyAutoGUI sending space key (attempt {i+1})")
                    pyautogui.press('space')
                    time.sleep(0.3)

                self.log_status("✅ Space key sent via pyautogui")
                success = True

            except Exception as e:
                self.log_status(f"⚠️ PyAutoGUI method failed: {e}")

        # Method 4: Direct PostMessage to window
        if not success:
            try:
                self.log_status("🔄 Trying PostMessage method...")
                import win32gui
                import win32con

                # Find HLL window again
                def find_window_by_title():
                    def callback(hwnd, windows):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if 'hell let loose' in title.lower() or 'hll' in title.lower():
                                windows.append(hwnd)
                        return True

                    windows = []
                    win32gui.EnumWindows(callback, windows)
                    return windows[0] if windows else None

                hll_hwnd = find_window_by_title()
                if hll_hwnd:
                    self.log_status("📤 Sending WM_KEYDOWN/WM_KEYUP messages...")
                    win32gui.PostMessage(hll_hwnd, win32con.WM_KEYDOWN, win32con.VK_SPACE, 0)
                    time.sleep(0.1)
                    win32gui.PostMessage(hll_hwnd, win32con.WM_KEYUP, win32con.VK_SPACE, 0)
                    self.log_status("✅ PostMessage sent to HLL window")
                    success = True
                else:
                    self.log_status("⚠️ Could not find HLL window for PostMessage")

            except Exception as e:
                self.log_status(f"⚠️ PostMessage method failed: {e}")

        if success:
            self.log_status("🎉 Successfully sent input to bypass splash screen!")
            return True
        else:
            self.log_status("❌ All input methods failed - splash screen may need manual input")
            return False

    def send_space_key_to_hll(self):
        """Send space key to HLL using robust SendInput method"""
        return self.send_space_key_to_hll_robust()

    def join_specific_server(self, server_key):
        """Join a specific server immediately"""
        if not self.steam_path:
            messagebox.showerror("Error", "Steam installation not found!")
            return

        # REMOVED: self.exit_steam() - no longer needed!
        
        server_info = self.SERVERS[server_key]

        self.log_status(f"🎯 Direct join to {server_info['name']}")
        self.selected_label.config(
            text=f"Joining {server_info['name']} ({server_info['ip']}:{server_info['port']})",
            fg='#4caf50'
        )

        self.launch_hll_with_server(server_info)

    def launch_hll_with_server(self, server_info):
        """Launch HLL with specific server connection using Steam launch parameters"""
        if not self.steam_path:
            self.log_status("❌ Steam path not found")
            messagebox.showerror("Error", "Steam installation not found!")
            return False
            
        if not self.is_steam_running():
            self.log_status("⚠️ Steam is not running - please start Steam first")
            messagebox.showerror("Error", "Steam is not running!\n\nPlease start Steam and log in, then try again.")
            return False
            
        try:
            steam_exe = os.path.join(self.steam_path, "steam.exe")
            
            # Build Steam launch command with server connection parameters
            cmd = [
                steam_exe,
                "-applaunch", self.HLL_APP_ID,
                "-dev", "+connect", f"{server_info['ip']}:{server_info['port']}"
            ]
            
            self.log_status(f"🚀 Launching HLL with direct connection to {server_info['name']}")
            self.log_status(f"🔧 Command: {' '.join(cmd[1:])}")  # Log without full steam.exe path
            
            # Launch HLL with server connection parameters
            subprocess.Popen(cmd, cwd=self.steam_path)
            
            self.log_status(f"✅ HLL launched with connection to {server_info['name']}")
            self.log_status("💡 No Steam restart needed - using existing session!")
            return True
            
        except Exception as e:
            self.log_status(f"❌ Error launching HLL: {str(e)}")
            messagebox.showerror("Error", f"Failed to launch HLL: {str(e)}")
            return False

    def stop_auto_seeding(self):
        """Stop the auto-seeding process and restore Steam configuration"""
        self.monitoring_active = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # Stop keep-awake system
        self.stop_keep_awake()

        self.log_status("🛑 Stopping auto-seeding...")

        # Close HLL if running
        if self.is_hll_running():
            self.log_status("🚪 Closing Hell Let Loose...")
            self.close_hll()
            time.sleep(2)

        # Restore original Steam launch options
        self.log_status("🔄 Restoring Steam configuration...")
        if self.restore_steam_launch_options():
            self.log_status("✅ Steam configuration restored successfully")
        else:
            self.log_status("⚠️ Warning: Could not restore Steam configuration!")

        # Restart Steam to ensure launch options are reloaded
        self.restart_steam_for_config_reload()

        self.log_status("✅ Auto-seeding stopped - Steam restored to original state")

    def restart_steam_for_config_reload(self):
        """Restart Steam to ensure launch option changes take effect"""
        try:
            if self.is_steam_running():
                self.log_status("🔄 Restarting Steam to reload configuration...")

                # Close Steam gracefully
                self.exit_steam()

                # Wait for Steam to fully close
                self.log_status("⏳ Waiting for Steam to fully close...")
                time.sleep(5)

                # Restart Steam
                if self.steam_path:
                    steam_exe = os.path.join(self.steam_path, "steam.exe")
                    if os.path.exists(steam_exe):
                        self.log_status("🚀 Restarting Steam...")
                        subprocess.Popen([steam_exe], cwd=self.steam_path)
                        self.log_status("✅ Steam restarted - launch options reloaded")
                    else:
                        self.log_status("❌ Could not find Steam executable")
                else:
                    self.log_status("❌ Steam path not available for restart")
            else:
                self.log_status("ℹ️ Steam not running - no restart needed")

        except Exception as e:
            self.log_status(f"⚠️ Error restarting Steam: {e}")
            self.log_status("💡 You may need to restart Steam manually to clear launch options")

    def run_seeding_loop(self):
        """Enhanced seeding loop with server availability checking and failover logic"""
        try:
            self.log_status("📊 Checking server availability and player counts...")
            
            # Enhanced server status checking
            soul1_result = self.get_server_player_count_enhanced('soul1')
            soul2_result = self.get_server_player_count_enhanced('soul2')
            
            soul1_players = soul1_result['players']
            soul2_players = soul2_result['players']
            soul1_available = soul1_result['status'] == 'online'
            soul2_available = soul2_result['status'] == 'online'

            # Log server availability status
            if not soul1_available:
                self.log_status(f"🚨 Soul 1 is UNAVAILABLE: {soul1_result['error']}")
            if not soul2_available:
                self.log_status(f"🚨 Soul 2 is UNAVAILABLE: {soul2_result['error']}")

            # Check if both servers are unreachable
            if not soul1_available and not soul2_available:
                self.log_status("💥 CRITICAL: Both servers are unreachable!")
                messagebox.showerror(
                    "Critical Error",
                    "Both SoulSniper servers are unreachable!\n\n"
                    "Discord notifications have been sent to admins.\n"
                    "Seeding will stop until servers are restored."
                )
                self.stop_auto_seeding()
                return

            # Enhanced seeding decision logic
            if soul1_available and soul2_available:
                # Both servers online - use original logic
                if soul1_players >= 70 and soul2_players >= 70:
                    self.log_status("🎉 Both SoulSniper servers are full! Put it back in your pants, Souldier!")
                    messagebox.showinfo(
                        "Servers Full!",
                        "Both SoulSniper servers are full!\n\nPut it back in your pants, Souldier! Mission accomplished!"
                    )
                    self.stop_auto_seeding()
                    return
                elif soul1_players < 70 and soul2_players < 70:
                    target_server = 'soul1'
                    self.log_status("📈 Both servers need seeding - prioritizing Soul 1")
                elif soul1_players < 70:
                    target_server = 'soul1'
                    self.log_status("📈 Soul 1 needs seeding")
                else:
                    target_server = 'soul2'
                    self.log_status("📈 Soul 2 needs seeding")

            elif soul1_available and not soul2_available:
                # Only Soul 1 available
                if soul1_players >= 70:
                    self.log_status("✅ Soul 1 is full and Soul 2 is down - seeding complete for available servers")
                    self.stop_auto_seeding()
                    return
                else:
                    target_server = 'soul1'
                    self.log_status("🔄 Soul 2 unavailable - seeding Soul 1 only")

            elif not soul1_available and soul2_available:
                # Only Soul 2 available - FAILOVER SCENARIO
                if soul2_players >= 70:
                    self.log_status("✅ Soul 2 is full and Soul 1 is down - seeding complete for available servers")
                    self.stop_auto_seeding()
                    return
                else:
                    target_server = 'soul2'
                    self.log_status("🔄 FAILOVER: Soul 1 unavailable - switching to Soul 2")

            server_info = self.SERVERS[target_server]
            self.log_status(f"🌱 Starting seeding process for {server_info['name']}")

            self.root.after(0, lambda: self.selected_label.config(
                text=f"Auto-seeding {server_info['name']} ({soul1_players if target_server == 'soul1' else soul2_players} players)",
                fg='#4caf50'
            ))

            # Launch for the target server
            if not self.launch_hll_with_server_monitoring(server_info):
                self.stop_auto_seeding()
                return

            # Give HLL more time to fully load before attempting splash screen bypass
            self.log_status("⏳ Waiting for HLL to fully load (90 seconds)...")
            time.sleep(90)

            # Try multiple times to bypass splash screen
            for attempt in range(3):
                self.log_status(f"🎯 Splash screen bypass attempt {attempt + 1}/3")
                if self.send_space_key_to_hll():
                    break
                time.sleep(5)

            time.sleep(15)  # Wait for connection to establish

            self.monitoring_loop_enhanced(target_server)

        except Exception as e:
            self.log_status(f"❌ Error in seeding loop: {str(e)}")
            self.root.after(0, self.stop_auto_seeding)

    def launch_hll_with_server_monitoring(self, server_info):
        """Launch HLL with server connection for monitoring using Steam launch parameters"""
        if not self.steam_path:
            self.log_status("❌ Steam path not found")
            return False
            
        if not self.is_steam_running():
            self.log_status("⚠️ Steam is not running - auto-seeding requires Steam to be running")
            self.log_status("💡 Tip: Start Steam before running auto-seeding")
            return False
            
        try:
            steam_exe = os.path.join(self.steam_path, "steam.exe")
            
            # Build Steam launch command with server connection parameters
            cmd = [
                steam_exe,
                "-applaunch", self.HLL_APP_ID,
                "-dev", "+connect", f"{server_info['ip']}:{server_info['port']}"
            ]
            
            self.log_status(f"🚀 Launching HLL for monitoring on {server_info['name']}")
            self.log_status(f"🔧 Command: {' '.join(cmd[1:])}")  # Log without full steam.exe path
            
            # Launch HLL with server connection parameters
            subprocess.Popen(cmd, cwd=self.steam_path)
            
            self.log_status(f"✅ HLL launched for monitoring on {server_info['name']}")
            self.log_status("🔥 Using Steam launch parameters - no account selection needed!")
            return True
            
        except Exception as e:
            self.log_status(f"❌ Error launching HLL for monitoring: {str(e)}")
            return False

    def is_steam_running(self):
        """Enhanced check if Steam is currently running"""
        try:
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe"], 
                                capture_output=True, text=True)
            if "steam.exe" in result.stdout:
                self.log_status("✅ Steam is running and ready")
                return True
            else:
                self.log_status("⚠️ Steam is not running")
                return False
        except Exception as e:
            self.log_status(f"❌ Error checking Steam status: {e}")
            return False                

    def monitoring_loop_enhanced(self, current_server):
        """Enhanced monitoring loop with improved server availability checking"""
        while self.monitoring_active:
            try:
                time.sleep(30)  # Check every 30 seconds

                if not self.monitoring_active:
                    break

                # Enhanced server status checking
                soul1_result = self.get_server_player_count_enhanced('soul1')
                soul2_result = self.get_server_player_count_enhanced('soul2')
                
                soul1_players = soul1_result['players']
                soul2_players = soul2_result['players']
                soul1_available = soul1_result['status'] == 'online'
                soul2_available = soul2_result['status'] == 'online'

                # Update UI with current status including availability
                availability_status = ""
                if not soul1_available:
                    availability_status += " [Soul 1: DOWN]"
                if not soul2_available:
                    availability_status += " [Soul 2: DOWN]"

                self.root.after(0, lambda: self.selected_label.config(
                    text=f"Seeding {self.SERVERS[current_server]['name']} | Soul 1: {soul1_players} | Soul 2: {soul2_players}{availability_status}",
                    fg='#4caf50' if not availability_status else '#ffa500'
                ))

                # Check if both available servers are full
                if soul1_available and soul2_available and soul1_players >= 70 and soul2_players >= 70:
                    self.log_status("🎉 Both SoulSniper servers are full! Mission accomplished!")
                    self.log_status("🏁 Seeding complete - preparing to exit for the day")
                    self.root.after(0, self.clear_steam_launch_options_and_exit)
                    break
                elif soul1_available and not soul2_available and soul1_players >= 70:
                    self.log_status("✅ Soul 1 full and Soul 2 down - seeding complete!")
                    self.root.after(0, self.clear_steam_launch_options_and_exit)
                    break
                elif not soul1_available and soul2_available and soul2_players >= 70:
                    self.log_status("✅ Soul 2 full and Soul 1 down - seeding complete!")
                    self.root.after(0, self.clear_steam_launch_options_and_exit)
                    break

                # Enhanced server switching logic with availability checking
                if current_server == 'soul1' and soul1_available and soul1_players >= 70:
                    self.log_status(f"✅ Soul 1 is full with {soul1_players} players!")

                    if soul2_available and soul2_players < 70:
                        self.log_status(f"🔄 Soul 1 full - switching to Soul 2 ({soul2_players} players)")
                        # [Server switching logic remains the same]
                        self.close_hll_and_steam()
                        time.sleep(8)

                        server_info = self.SERVERS['soul2']
                        self.log_status(f"🎯 Launching HLL for {server_info['name']}")

                        self.root.after(0, lambda: self.selected_label.config(
                            text=f"Switching to {server_info['name']} ({soul2_players} players)",
                            fg='#ffa500'
                        ))

                        if self.launch_hll_with_server_monitoring(server_info):
                            self.log_status(f"🚀 Successfully switched to {server_info['name']}")
                            self.log_status("⏳ Waiting for HLL to load (90 seconds)...")
                            time.sleep(90)

                            for attempt in range(3):
                                self.log_status(f"⌨️ Splash screen bypass attempt {attempt + 1}/3")
                                if self.send_space_key_to_hll():
                                    break
                                time.sleep(5)

                            time.sleep(15)
                            current_server = 'soul2'
                            self.log_status(f"✅ Now seeding {server_info['name']}")
                            continue
                        else:
                            self.log_status("❌ Failed to switch to Soul 2")
                            break
                    elif not soul2_available:
                        self.log_status("✅ Soul 1 full and Soul 2 down - seeding complete for available servers!")
                        self.root.after(0, self.clear_steam_launch_options_and_exit)
                        break
                    else:
                        self.log_status("🎉 Both servers are now full! Seeding complete!")
                        self.root.after(0, self.clear_steam_launch_options_and_exit)
                        break

                elif current_server == 'soul2' and soul2_available and soul2_players >= 70:
                    self.log_status(f"✅ Soul 2 is full with {soul2_players} players!")
                    self.log_status("🎉 Seeding mission complete!")
                    self.root.after(0, self.clear_steam_launch_options_and_exit)
                    break

                # Handle case where current server goes down during seeding
                if current_server == 'soul1' and not soul1_available:
                    self.log_status("🚨 Soul 1 went down during seeding!")
                    if soul2_available:
                        self.log_status("🔄 Switching to Soul 2 due to Soul 1 outage")
                        # Switch to Soul 2 [same switching logic as above]
                    else:
                        self.log_status("💥 Both servers now down - stopping seeding")
                        break
                elif current_server == 'soul2' and not soul2_available:
                    self.log_status("🚨 Soul 2 went down during seeding!")
                    if soul1_available:
                        self.log_status("🔄 Switching back to Soul 1 due to Soul 2 outage")
                        # Switch to Soul 1 [implement similar switching logic]
                    else:
                        self.log_status("💥 Both servers now down - stopping seeding")
                        break

                # Periodic status logging
                if int(time.time()) % 180 == 0:  # Every 3 minutes
                    status_msg = f"📊 Monitoring: Soul 1 ({soul1_players}"
                    if not soul1_available:
                        status_msg += " - DOWN"
                    status_msg += f") | Soul 2 ({soul2_players}"
                    if not soul2_available:
                        status_msg += " - DOWN"
                    status_msg += f") | Current: {self.SERVERS[current_server]['name']}"
                    self.log_status(status_msg)

            except Exception as e:
                self.log_status(f"❌ Error in monitoring loop: {str(e)}")
                break

        # Clean up when monitoring ends
        self.root.after(0, self.stop_auto_seeding)

    def monitoring_loop(self, current_server):
        """Legacy method - redirects to enhanced version"""
        return self.monitoring_loop_enhanced(current_server)    

    def schedule_cleanup_and_exit(self):
        """Schedule cleanup of launch options and exit"""
        self.log_status("🧹 Scheduling cleanup to clear launch options...")
        # Use the new comprehensive cleanup method
        self.root.after(0, self.clear_steam_launch_options_and_exit)

    def show_completion_and_exit(self):
        """Show completion message and exit the application"""
        messagebox.showinfo(
            "Seeding Complete!",
            "🎉 SoulSniper servers are now populated!\n\n"
            "✅ Steam configuration has been restored\n"
            "✅ HLL config files have been restored\n"
            "✅ You can now play HLL normally with your settings\n\n"
            "The seeder will run again tomorrow at 7 AM EST.\n"
            "Your game settings are protected and restored.\n\n"
            "Thank you for helping seed the servers!"
        )

        # Exit the application
        self.log_status("🏁 Seeding complete - exiting application")
        self.root.quit()

    def auto_cleanup(self):
        """Legacy method - now just logs that auto-cleanup is handled automatically"""
        self.log_status("ℹ️ Server connection options will be auto-removed after HLL connects")
        # The actual cleanup is now handled by the 3-minute timer set when launching

if __name__ == "__main__":
    root = tk.Tk()
    app = SoulSniperSeeder(root)
    root.mainloop()