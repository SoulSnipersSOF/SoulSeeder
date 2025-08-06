import sys
import os
import subprocess
import time
import tkinter as tk

class SteamLaunchParamsTest:
    def __init__(self, root):
        self.root = root
        self.root.title("Steam Launch Parameters Test")
        self.root.geometry("500x300")
        self.root.configure(bg='#1a1a1a')
        
        # Configuration
        self.steam_path = self.find_steam_path()
        self.soul1_connection = "-dev +connect 192.169.95.2:8530"
        
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title = tk.Label(self.root, text="Steam Launch Parameters Test", 
                        font=('Arial', 14, 'bold'), fg='#ff6b35', bg='#1a1a1a')
        title.pack(pady=20)
        
        # Info
        info = tk.Label(self.root, text="Tests: steam.exe -applaunch 686810 -dev +connect 192.169.95.2:8530", 
                       font=('Arial', 9), fg='#cccccc', bg='#1a1a1a')
        info.pack(pady=5)
        
        # Status
        self.status_label = tk.Label(self.root, text="Ready to test", 
                                   font=('Arial', 12), fg='#ffffff', bg='#1a1a1a')
        self.status_label.pack(pady=10)
        
        # Test button
        self.test_btn = tk.Button(self.root, text="🚀 Test Steam Launch Parameters", 
                                 command=self.test_launch_params, 
                                 font=('Arial', 12, 'bold'),
                                 bg='#28a745', fg='white', relief='flat', 
                                 pady=15, cursor='hand2')
        self.test_btn.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(self.root, 
                               text="REQUIREMENTS:\n"
                                    "• Steam must be running and logged in\n"
                                    "• Will launch HLL directly with server connection\n"
                                    "• Press SPACEBAR when HLL loads", 
                               font=('Arial', 10), fg='#ffa500', bg='#1a1a1a',
                               justify='left')
        instructions.pack(pady=10)
        
        # Log area
        self.log_text = tk.Text(self.root, height=8, bg='#2d2d2d', fg='#ffffff', 
                               font=('Consolas', 9), state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=20, pady=10)
        
    def log(self, message):
        """Simple logging"""
        timestamp = time.strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        self.log_text.config(state='normal')
        self.log_text.insert('end', log_message + "\n")
        self.log_text.config(state='disabled')
        self.log_text.see('end')
        self.root.update()
        
    def find_steam_path(self):
        """Find Steam installation"""
        paths = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam"
        ]
        
        for path in paths:
            if os.path.exists(os.path.join(path, "steam.exe")):
                return path
        return None
        
    def is_steam_running(self):
        """Check if Steam is running"""
        try:
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe"], 
                                  capture_output=True, text=True)
            return "steam.exe" in result.stdout
        except:
            return False
            
    def test_launch_params(self):
        """Test launching HLL with Steam command line parameters"""
        self.log("🧪 Testing Steam launch parameters...")
        
        if not self.steam_path:
            self.log("❌ Steam installation not found!")
            self.status_label.config(text="Steam not found", fg='#ff4444')
            return
            
        if not self.is_steam_running():
            self.log("⚠️ Steam is not running! Please start Steam and log in first.")
            self.status_label.config(text="Steam not running", fg='#ffa500')
            return
            
        try:
            steam_exe = os.path.join(self.steam_path, "steam.exe")
            
            # Build the command
            cmd = [
                steam_exe,
                "-applaunch", "686810",  # HLL App ID
                "-dev", "+connect", "192.169.95.2:8530"  # Soul 1 connection
            ]
            
            self.log("🚀 Launching with command:")
            self.log(f"   {' '.join(cmd)}")
            self.log("")
            self.log("🎯 KEY TEST: Will HLL connect directly to Soul 1?")
            self.log("📋 Manual steps:")
            self.log("   1. Wait for HLL to load")
            self.log("   2. Press SPACEBAR to bypass splash screen")
            self.log("   3. Check if it connects to Soul 1 (192.169.95.2:8530)")
            
            # Launch with parameters
            subprocess.Popen(cmd, cwd=self.steam_path)
            
            self.status_label.config(text="HLL launched with parameters - test in progress!", fg='#4caf50')
            self.log("✅ Command executed - monitoring results...")
            
        except Exception as e:
            self.log(f"❌ Failed to launch: {e}")
            self.status_label.config(text="Launch failed", fg='#ff4444')

if __name__ == "__main__":
    root = tk.Tk()
    app = SteamLaunchParamsTest(root)
    root.mainloop()