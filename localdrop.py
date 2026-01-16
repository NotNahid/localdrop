import customtkinter as ctk
import http.server
import socketserver
import threading
import os
import socket
import requests
from tkinter import filedialog

# CONFIGURATION
PORT = 9000
UPLOAD_DIR = 'Received_Files'

# Create download folder if it doesn't exist
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- 1. THE NETWORK ENGINE (SERVER SIDE) ---
class DropHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get filename from headers
            filename = self.headers.get('Filename', 'unknown_file')
            file_length = int(self.headers['Content-Length'])
            
            # Save the file
            save_path = os.path.join(UPLOAD_DIR, filename)
            with open(save_path, 'wb') as f:
                f.write(self.rfile.read(file_length))
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Success")
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        return # Silence server logs

def start_server(status_label):
    # Find Local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    s.close()

    status_label.configure(text=f"🟢 READY TO RECEIVE\nYour IP: {IP}\nFolder: {UPLOAD_DIR}")
    
    # Start Server safely
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), DropHandler) as httpd:
            httpd.serve_forever()
    except OSError:
        status_label.configure(text=f"🔴 Error: Port {PORT} is busy.")

# --- 2. THE GUI (FRONTEND) ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LocalDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LocalDrop 📡")
        self.geometry("500x450")
        
        # TABS (Send vs Receive)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_send = self.tabview.add("📤 Send File")
        self.tab_receive = self.tabview.add("📥 Receive File")

        # --- RECEIVE TAB SETUP ---
        self.lbl_status = ctk.CTkLabel(self.tab_receive, text="Starting Server...", font=("Arial", 16))
        self.lbl_status.pack(pady=40)
        
        self.btn_open_folder = ctk.CTkButton(self.tab_receive, text="Open Received Folder", command=self.open_folder)
        self.btn_open_folder.pack(pady=10)

        # Start Server in Background Thread
        self.server_thread = threading.Thread(target=start_server, args=(self.lbl_status,), daemon=True)
        self.server_thread.start()

        # --- SEND TAB SETUP ---
        self.entry_ip = ctk.CTkEntry(self.tab_send, placeholder_text="Receiver IP (e.g., 192.168.1.5)")
        self.entry_ip.pack(pady=20, fill="x")

        self.btn_select = ctk.CTkButton(self.tab_send, text="Select File", command=self.select_file)
        self.btn_select.pack(pady=10)

        self.lbl_file = ctk.CTkLabel(self.tab_send, text="No file selected")
        self.lbl_file.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self.tab_send)
        self.progress.set(0)
        self.progress.pack(pady=10, fill="x")

        self.btn_send = ctk.CTkButton(self.tab_send, text="SEND 🚀", command=self.send_file, state="disabled")
        self.btn_send.pack(pady=20)

        self.selected_file_path = None

    def open_folder(self):
        os.startfile(UPLOAD_DIR)

    def select_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.selected_file_path = filename
            self.lbl_file.configure(text=os.path.basename(filename))
            self.btn_send.configure(state="normal", fg_color="green")

    def send_file(self):
        target_ip = self.entry_ip.get()
        if not target_ip or not self.selected_file_path:
            return

        # Disable button while sending
        self.btn_send.configure(state="disabled", text="Sending...")
        
        # Run send logic in thread to not freeze GUI
        threading.Thread(target=self._upload_logic, args=(target_ip,)).start()

    def _upload_logic(self, target_ip):
        url = f"http://{target_ip}:{PORT}"
        filename = os.path.basename(self.selected_file_path)
        
        try:
            with open(self.selected_file_path, 'rb') as f:
                # Simple upload without chunking for now (good for <500MB)
                headers = {'Filename': filename}
                self.progress.set(0.5) # Fake progress for now
                response = requests.post(url, data=f, headers=headers)
                
            if response.status_code == 200:
                self.lbl_file.configure(text="✅ Sent Successfully!", text_color="green")
                self.progress.set(1.0)
            else:
                self.lbl_file.configure(text="❌ Server Error", text_color="red")
        except Exception as e:
            self.lbl_file.configure(text=f"❌ Failed: Cannot connect", text_color="red")
        
        self.btn_send.configure(state="normal", text="SEND 🚀")

if __name__ == "__main__":
    app = LocalDropApp()
    app.mainloop()
