import os
import sys
import socket
import threading
import json
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import unquote, quote
from pathlib import Path

# ====== Kivy Setup ======
os.environ['KIVY_NO_CONSOLELOG'] = '1'
from kivy.config import Config
Config.set('graphics', 'width', '420')
Config.set('graphics', 'height', '760')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle

# ====== CONFIG ======
PORT = 45454
PIN = "123456"
DEVICE_NAME = socket.gethostname()

def get_save_dir():
    if platform == 'android':
        try:
            from android.storage import primary_external_storage_path
            base = primary_external_storage_path()
            d = os.path.join(base, 'Download', 'FastDrop')
        except:
            d = os.path.join(str(Path.home()), 'FastDrop')
    else:
        d = os.path.join(str(Path.home()), 'Downloads', 'FastDrop')
    os.makedirs(d, exist_ok=True)
    return d

# ====== Helpers ======
def get_local_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except: pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ':' not in ip and not ip.startswith('127.'):
                ips.add(ip)
    except: pass
    return sorted(ips)

def human_size(n):
    if n <= 0: return "0 B"
    for u in ['B','KB','MB','GB','TB']:
        if abs(n) < 1024.0:
            return f"{n:.0f} {u}" if u == 'B' else f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} PB"

def unique_path(directory, filename):
    safe = "".join(c for c in filename if c not in '\\/:*?"<>|')
    if not safe:
        safe = 'file.bin'
    base, ext = os.path.splitext(safe)
    out = os.path.join(directory, safe)
    i = 1
    while os.path.exists(out):
        out = os.path.join(directory, f"{base} ({i}){ext}")
        i += 1
    return out

# ====== Web UI HTML ======
WEB_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>FastDrop</title>
<style>
  :root { --bg:#0b0d12; --card:#161920; --orange:#ff6a00; --orange2:#ff8c42; --text:#e6e6e6; --muted:#8b92a8; --green:#00ff88; --red:#ff4444; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body { margin:0; font-family:Segoe UI, Roboto, system-ui, sans-serif; background:var(--bg); color:var(--text); padding-bottom:20px; }
  header { background:linear-gradient(90deg, #ff4d00, var(--orange)); padding:16px; display:flex; align-items:center; justify-content:center; gap:10px; box-shadow:0 4px 20px rgba(255,106,0,.25); position:sticky; top:0; z-index:10; }
  header h1 { margin:0; font-size:20px; letter-spacing:1px; font-weight:700; }
  .dot { width:10px; height:10px; background:var(--green); border-radius:50%; box-shadow:0 0 8px var(--green); animation:pulse 2s infinite; }
  @keyframes pulse { 0%{opacity:1} 50%{opacity:.5} 100%{opacity:1} }
  .wrap { max-width:760px; margin:0 auto; padding:16px; }
  .card { background:var(--card); border-radius:16px; padding:18px; margin-bottom:16px; border:1px solid #222; box-shadow:0 8px 24px rgba(0,0,0,.35); }
  h2 { margin:0 0 14px; font-size:14px; color:var(--orange2); text-transform:uppercase; letter-spacing:.5px; }
  .info { color:var(--muted); font-size:13px; line-height:1.7; }
  .info strong { color:var(--text); }
  input[type=text], input[type=password] { width:100%; padding:12px; border-radius:10px; border:1px solid #333; background:#0f1115; color:#fff; font-size:14px; margin-bottom:10px; }
  .btn { width:100%; padding:14px; border:none; border-radius:10px; background:var(--orange); color:#fff; font-weight:700; font-size:15px; cursor:pointer; text-align:center; display:inline-block; text-decoration:none; }
  .btn:hover, .btn:active { filter:brightness(1.15); }
  .btn-secondary { background:#2a2d35; color:var(--text); }
  .btn-small { width:auto; padding:8px 14px; font-size:13px; }
  .dropzone { border:2px dashed #444; border-radius:12px; padding:32px 16px; text-align:center; color:var(--muted); cursor:pointer; }
  .dropzone.dragover { border-color:var(--orange); background:#1f150d; color:#fff; }
  .file { display:flex; align-items:center; padding:10px 12px; background:#0f1115; border-radius:8px; margin-bottom:6px; font-size:14px; border:1px solid #1c1f26; gap:8px; }
  .file-name { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .file-meta { color:var(--muted); font-size:12px; white-space:nowrap; }
  .file-actions a, .file-actions button { color:var(--orange2); text-decoration:none; font-size:16px; background:none; border:none; cursor:pointer; padding:4px 6px; border-radius:6px; }
  .file-actions a:hover, .file-actions button:hover { background:#222; }
  .danger { color:var(--red) !important; }
  .empty { text-align:center; color:var(--muted); padding:14px; }
  .bar { height:10px; background:#0f1115; border-radius:8px; overflow:hidden; margin-top:10px; border:1px solid #222; }
  .bar > div { height:100%; width:0%; background:linear-gradient(90deg,var(--orange),var(--orange2)); transition:width .15s; }
  .status { font-size:13px; color:var(--muted); margin-top:8px; min-height:20px; }
  .ip-tag { display:inline-block; background:#222; padding:4px 10px; border-radius:6px; font-family:monospace; color:var(--orange2); margin:2px; border:1px solid #333; font-size:12px; }
  .badge { background:var(--green); color:#000; font-size:11px; padding:2px 8px; border-radius:4px; font-weight:700; }
  .device { display:flex; justify-content:space-between; align-items:center; padding:10px; background:#0f1115; border-radius:8px; margin-bottom:6px; border:1px solid #1c1f26; }
</style>
</head>
<body>
<header>
  <div class="dot"></div>
  <h1>⚡ FastDrop</h1>
</header>
<div class="wrap">

  <div class="card">
    <h2>📶 Connection</h2>
    <div class="info">
      <strong>Device:</strong> __DEVICE__<br>
      <strong>PIN:</strong> __PIN__<br>
      <strong>Save folder:</strong> __SAVE__<br>
      <strong>Open on other device:</strong><br>
      __IPS__
    </div>
  </div>

  <div class="card">
    <h2>📤 Send Files to This Device</h2>
    <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
      📎 Tap or drag files here
    </div>
    <input type="file" id="fileInput" multiple style="display:none" onchange="handleFiles(this.files)">
    <input type="text" id="pinInput" placeholder="PIN" value="__PIN__">
    <div class="bar"><div id="pb"></div></div>
    <div class="status" id="status">Ready</div>
  </div>

  <div class="card">
    <h2>📥 Files (<span id="fileCount">0</span>)</h2>
    <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px">
      <a href="/download-all" class="btn btn-secondary btn-small">⬇ Download All ZIP</a>
      <button class="btn btn-secondary btn-small" onclick="refreshFiles()">🔄 Refresh</button>
    </div>
    <div id="filesList">
      <div class="empty">Loading...</div>
    </div>
  </div>

</div>

<script>
const dropzone = document.getElementById('dropzone');
const status = document.getElementById('status');
const pb = document.getElementById('pb');

['dragenter','dragover','dragleave','drop'].forEach(e=>{
  dropzone.addEventListener(e, ev=>{ ev.preventDefault(); ev.stopPropagation(); });
});
['dragenter','dragover'].forEach(e=> dropzone.addEventListener(e, ()=> dropzone.classList.add('dragover')));
['dragleave','drop'].forEach(e=> dropzone.addEventListener(e, ()=> dropzone.classList.remove('dragover')));
dropzone.addEventListener('drop', e=> handleFiles(e.dataTransfer.files));

async function handleFiles(fileList) {
  if (!fileList.length) return;
  const pin = document.getElementById('pinInput').value;

  for (let i=0; i<fileList.length; i++) {
    const file = fileList[i];
    status.textContent = `Uploading (${i+1}/${fileList.length}) ${file.name}`;
    pb.style.width = '0%';
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/upload');
      xhr.setRequestHeader('x-pin', pin);
      xhr.setRequestHeader('x-file-name', encodeURIComponent(file.name));
      xhr.upload.onprogress = e => {
        if (e.lengthComputable) pb.style.width = (e.loaded/e.total*100).toFixed(1)+'%';
      };
      xhr.onload = () => xhr.status === 200 ? resolve() : reject(xhr.responseText || 'Error');
      xhr.onerror = () => reject('Network error');
      xhr.send(file);
    }).catch(err => { status.textContent = '❌ ' + err; throw err; });
  }
  status.textContent = '✅ Done!';
  pb.style.width = '100%';
  setTimeout(refreshFiles, 500);
}

function humanSize(n) {
  if (n <= 0) return '0 B';
  const u = ['B','KB','MB','GB','TB'];
  let i = 0;
  while (n >= 1024 && i < u.length-1) { n /= 1024; i++; }
  return (i === 0 ? n.toFixed(0) : n.toFixed(1)) + ' ' + u[i];
}

async function refreshFiles() {
  try {
    const r = await fetch('/files');
    const files = await r.json();
    document.getElementById('fileCount').textContent = files.length;
    const list = document.getElementById('filesList');
    if (!files.length) {
      list.innerHTML = '<div class="empty">No files yet</div>';
      return;
    }
    list.innerHTML = files.map(f => `
      <div class="file">
        <span class="file-name">${f.name}</span>
        <span class="file-meta">${humanSize(f.size)}</span>
        <div class="file-actions">
          <a href="/download/${encodeURIComponent(f.name)}" title="Download">⬇</a>
          <a href="/delete/${encodeURIComponent(f.name)}" class="danger" onclick="return confirm('Delete?')" title="Delete">🗑</a>
        </div>
      </div>
    `).join('');
  } catch(e) {
    document.getElementById('filesList').innerHTML = '<div class="empty">Error loading</div>';
  }
}
refreshFiles();
setInterval(refreshFiles, 5000);
</script>
</body>
</html>
"""

# ====== HTTP Server (Receiver + Web UI) ======
class FileHandler(BaseHTTPRequestHandler):
    save_dir = ""
    pin = ""
    on_receive = None
    on_progress = None

    def log_message(self, format, *args): pass

    def _send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code, text, ctype='text/plain'):
        body = text.encode('utf-8') if isinstance(text, str) else text
        self.send_response(code)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_GET(self):
        # ROOT - Serve Web UI
        if self.path == '/' or self.path == '/index.html':
            ips = get_local_ips()
            ip_html = ''.join(f'<span class="ip-tag">http://{ip}:{PORT}</span> ' for ip in ips)
            html = (WEB_PAGE
                    .replace('__DEVICE__', DEVICE_NAME)
                    .replace('__PIN__', self.pin or '')
                    .replace('__SAVE__', self.save_dir)
                    .replace('__IPS__', ip_html or 'No network'))
            self._send_text(200, html, 'text/html')
            return

        # Ping
        if self.path == '/ping':
            self._send_json(200, {
                'ok': True,
                'name': DEVICE_NAME,
                'pinRequired': bool(self.pin)
            })
            return

        # File list
        if self.path == '/files':
            files = []
            try:
                for name in sorted(os.listdir(self.save_dir)):
                    full = os.path.join(self.save_dir, name)
                    if os.path.isfile(full):
                        files.append({
                            'name': name,
                            'size': os.path.getsize(full)
                        })
            except: pass
            self._send_json(200, files)
            return

        # Download single file
        if self.path.startswith('/download/'):
            fname = unquote(self.path[10:])
            full = os.path.join(self.save_dir, fname)
            if os.path.isfile(full):
                fsize = os.path.getsize(full)
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', str(fsize))
                self.end_headers()
                with open(full, 'rb') as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk: break
                        try:
                            self.wfile.write(chunk)
                        except:
                            break
                return
            self._send_text(404, 'Not found')
            return

        # Download all as ZIP
        if self.path == '/download-all':
            import zipfile
            import io
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
                for name in os.listdir(self.save_dir):
                    full = os.path.join(self.save_dir, name)
                    if os.path.isfile(full):
                        zf.write(full, name)
            data = mem.getvalue()
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', f'attachment; filename="FastDrop_{stamp}.zip"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # Delete
        if self.path.startswith('/delete/'):
            fname = unquote(self.path[8:])
            full = os.path.join(self.save_dir, fname)
            try:
                if os.path.isfile(full):
                    os.remove(full)
            except: pass
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return

        self._send_text(404, 'Not Found')

    def do_POST(self):
        if self.path == '/upload':
            pin = self.headers.get('x-pin', '')
            if self.pin and pin != self.pin:
                self._send_text(403, 'Invalid PIN')
                return

            fname = unquote(self.headers.get('x-file-name', 'file.bin'))
            try:
                total = int(self.headers.get('Content-Length', 0))
            except:
                total = 0
            out = unique_path(self.save_dir, fname)

            received = 0
            try:
                with open(out, 'wb') as f:
                    while received < total:
                        chunk_size = min(1024 * 1024, total - received)
                        chunk = self.rfile.read(chunk_size)
                        if not chunk: break
                        f.write(chunk)
                        received += len(chunk)
                        if self.on_progress:
                            try: self.on_progress(fname, received, total)
                            except: pass

                if self.on_receive:
                    try: self.on_receive(os.path.basename(out), received)
                    except: pass

                self._send_json(200, {'ok': True, 'saved': os.path.basename(out)})
            except Exception as e:
                self._send_text(500, f'Error: {e}')
            return

        self._send_text(404, 'Not Found')

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class ReceiverServer:
    def __init__(self):
        self.server = None
        self.thread = None
        self.running = False

    def start(self, port, pin, save_dir, on_receive=None, on_progress=None):
        FileHandler.save_dir = save_dir
        FileHandler.pin = pin
        FileHandler.on_receive = on_receive
        FileHandler.on_progress = on_progress

        self.server = ThreadingHTTPServer(('0.0.0.0', port), FileHandler)
        self.running = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.server:
            try: self.server.shutdown()
            except: pass
            try: self.server.server_close()
            except: pass
            self.server = None

# ====== Discovery ======
class DeviceDiscovery:
    def __init__(self):
        self.devices = {}
        self.zc = None

    def start(self, port):
        try:
            from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener

            class L(ServiceListener):
                def __init__(self2):
                    pass
                def add_service(self2, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info and info.addresses:
                        ip = socket.inet_ntoa(info.addresses[0])
                        if ip not in get_local_ips():
                            self.devices[name] = {
                                'name': name.replace('._fastdrop._tcp.local.', ''),
                                'ip': ip,
                                'port': info.port
                            }
                def remove_service(self2, zc, type_, name):
                    self.devices.pop(name, None)
                def update_service(self2, zc, type_, name): pass

            self.zc = Zeroconf()
            ips = get_local_ips()
            if ips:
                info = ServiceInfo(
                    "_fastdrop._tcp.local.",
                    f"{DEVICE_NAME}._fastdrop._tcp.local.",
                    addresses=[socket.inet_aton(ips[0])],
                    port=port,
                    properties={'name': DEVICE_NAME},
                    server=f"{DEVICE_NAME.replace(' ', '-')}.local.",
                )
                try: self.zc.register_service(info)
                except: pass
            ServiceBrowser(self.zc, "_fastdrop._tcp.local.", L())
        except Exception as e:
            print(f"Discovery error: {e}")

    def stop(self):
        if self.zc:
            try: self.zc.close()
            except: pass

    def get_devices(self):
        return list(self.devices.values())

# ====== Manual scan fallback ======
def scan_network(base_ip, port, timeout=0.3):
    found = []
    found_lock = threading.Lock()
    prefix = '.'.join(base_ip.split('.')[:3]) + '.'
    local_ips = set(get_local_ips())

    def check(ip):
        try:
            s = socket.socket()
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            try:
                import urllib.request
                r = urllib.request.urlopen(f"http://{ip}:{port}/ping", timeout=1)
                data = json.loads(r.read())
                if data.get('ok'):
                    with found_lock:
                        found.append({
                            'name': data.get('name', ip),
                            'ip': ip,
                            'port': port
                        })
            except: pass
        except: pass

    threads = []
    for i in range(1, 255):
        ip = prefix + str(i)
        if ip in local_ips: continue
        t = threading.Thread(target=check, args=(ip,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=1)

    return found

# ====== Kivy UI ======
class StyledButton(Button):
    def __init__(self, bg_color=(1, 0.42, 0, 1), **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = bg_color
        self.color = (1, 1, 1, 1)
        self.bold = True
        self.size_hint_y = None
        self.height = dp(48)
        self.font_size = dp(14)

class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = kwargs.get('color', (0.9, 0.9, 0.9, 1))
        self.size_hint_y = kwargs.get('size_hint_y', None)
        if self.size_hint_y is None and 'height' not in kwargs:
            self.height = dp(30)
        self.font_size = dp(13)
        self.halign = 'left'
        self.valign = 'middle'
        self.bind(size=self.setter('text_size'))

class CardBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(12)
        self.spacing = dp(8)
        self.size_hint_y = None
        with self.canvas.before:
            Color(0.086, 0.098, 0.125, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *a):
        self.bg.pos = self.pos
        self.bg.size = self.size

class FastDropApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.receiver = ReceiverServer()
        self.discovery = DeviceDiscovery()
        self.save_dir = ""
        self.ips = []
        self.receiver_running = False
        self.discovered_devices = []
        self.selected_files = []
        self.title = "FastDrop"

    def build(self):
        self.save_dir = get_save_dir()
        self.ips = get_local_ips()

        if platform == 'android':
            self._request_android_permissions()

        root = BoxLayout(orientation='vertical')

        with root.canvas.before:
            Color(0.043, 0.051, 0.07, 1)
            self.root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *a: setattr(self.root_bg, 'pos', root.pos),
                  size=lambda *a: setattr(self.root_bg, 'size', root.size))

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(16), dp(8)])
        with header.canvas.before:
            Color(1, 0.42, 0, 1)
            self.hdr_bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda *a: setattr(self.hdr_bg, 'pos', header.pos),
                    size=lambda *a: setattr(self.hdr_bg, 'size', header.size))
        header.add_widget(Label(text='⚡ FastDrop', font_size=dp(20), bold=True))
        root.add_widget(header)

        self.tabs = TabbedPanel(do_default_tab=False, tab_width=dp(95))

        tab1 = TabbedPanelItem(text='📥 Receive')
        tab1.add_widget(self._build_receive_tab())
        self.tabs.add_widget(tab1)

        tab2 = TabbedPanelItem(text='📤 Send')
        tab2.add_widget(self._build_send_tab())
        self.tabs.add_widget(tab2)

        tab3 = TabbedPanelItem(text='📁 Files')
        tab3.add_widget(self._build_files_tab())
        self.tabs.add_widget(tab3)

        tab4 = TabbedPanelItem(text='🔍 Devices')
        tab4.add_widget(self._build_devices_tab())
        self.tabs.add_widget(tab4)

        root.add_widget(self.tabs)

        # Auto-start receiver
        Clock.schedule_once(lambda dt: self.toggle_receiver(None), 1)
        return root

    def _request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET,
            ])
        except: pass

    def _build_receive_tab(self):
        scroll = ScrollView()
        layout = GridLayout(cols=1, spacing=dp(10), padding=dp(12), size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        card = CardBox()
        card.add_widget(StyledLabel(text='[b]📶 Connection Info[/b]', markup=True,
                                     color=(1, 0.55, 0.26, 1)))
        ip_text = ', '.join(self.ips) if self.ips else 'No network'
        self.ip_label = StyledLabel(text=f'IP: {ip_text}', height=dp(24))
        card.add_widget(self.ip_label)

        self.pin_input = TextInput(text=PIN, hint_text='PIN', multiline=False,
                                    size_hint_y=None, height=dp(44),
                                    background_color=(0.06, 0.07, 0.08, 1),
                                    foreground_color=(1,1,1,1))
        card.add_widget(self.pin_input)

        self.port_input = TextInput(text=str(PORT), hint_text='Port', multiline=False,
                                     size_hint_y=None, height=dp(44),
                                     background_color=(0.06, 0.07, 0.08, 1),
                                     foreground_color=(1,1,1,1))
        card.add_widget(self.port_input)

        self.receiver_btn = StyledButton(text='▶ Start Receiver')
        self.receiver_btn.bind(on_press=self.toggle_receiver)
        card.add_widget(self.receiver_btn)

        self.receiver_status = StyledLabel(text='Status: Stopped',
                                            color=(0.55, 0.57, 0.66, 1))
        card.add_widget(self.receiver_status)

        self.url_label = StyledLabel(text='', color=(1, 0.55, 0.26, 1), height=dp(50))
        card.add_widget(self.url_label)

        card.bind(minimum_height=card.setter('height'))
        layout.add_widget(card)

        card2 = CardBox()
        card2.add_widget(StyledLabel(text='[b]📊 Transfer Progress[/b]', markup=True,
                                      color=(1, 0.55, 0.26, 1)))
        self.recv_progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(20))
        card2.add_widget(self.recv_progress)
        self.recv_progress_label = StyledLabel(text='Waiting...',
                                                color=(0.55, 0.57, 0.66, 1))
        card2.add_widget(self.recv_progress_label)
        card2.bind(minimum_height=card2.setter('height'))
        layout.add_widget(card2)

        card3 = CardBox()
        card3.add_widget(StyledLabel(text='[b]📋 Log[/b]', markup=True,
                                      color=(1, 0.55, 0.26, 1)))
        self.recv_log = StyledLabel(text='Ready', height=dp(220),
                                     color=(0.55, 0.57, 0.66, 1))
        card3.add_widget(self.recv_log)
        card3.bind(minimum_height=card3.setter('height'))
        layout.add_widget(card3)

        scroll.add_widget(layout)
        return scroll

    def _build_send_tab(self):
        scroll = ScrollView()
        layout = GridLayout(cols=1, spacing=dp(10), padding=dp(12), size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        card = CardBox()
        card.add_widget(StyledLabel(text='[b]📤 Send Files[/b]', markup=True,
                                     color=(1, 0.55, 0.26, 1)))

        self.target_ip = TextInput(hint_text='Receiver IP (e.g. 192.168.0.105)',
                                    multiline=False, size_hint_y=None, height=dp(44),
                                    background_color=(0.06, 0.07, 0.08, 1),
                                    foreground_color=(1,1,1,1))
        card.add_widget(self.target_ip)

        self.target_port = TextInput(text=str(PORT), hint_text='Port',
                                      multiline=False, size_hint_y=None, height=dp(44),
                                      background_color=(0.06, 0.07, 0.08, 1),
                                      foreground_color=(1,1,1,1))
        card.add_widget(self.target_port)

        self.target_pin = TextInput(text=PIN, hint_text='PIN',
                                     multiline=False, size_hint_y=None, height=dp(44),
                                     background_color=(0.06, 0.07, 0.08, 1),
                                     foreground_color=(1,1,1,1))
        card.add_widget(self.target_pin)

        pick_btn = StyledButton(text='📎 Pick Files', bg_color=(0.17, 0.18, 0.21, 1))
        pick_btn.bind(on_press=self.pick_files)
        card.add_widget(pick_btn)

        self.selected_label = StyledLabel(text='No files selected',
                                           color=(0.55, 0.57, 0.66, 1))
        card.add_widget(self.selected_label)

        send_btn = StyledButton(text='🚀 Send')
        send_btn.bind(on_press=self.send_files)
        card.add_widget(send_btn)

        card.bind(minimum_height=card.setter('height'))
        layout.add_widget(card)

        card2 = CardBox()
        card2.add_widget(StyledLabel(text='[b]📊 Send Progress[/b]', markup=True,
                                      color=(1, 0.55, 0.26, 1)))
        self.send_progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(20))
        card2.add_widget(self.send_progress)
        self.send_progress_label = StyledLabel(text='Ready',
                                                color=(0.55, 0.57, 0.66, 1))
        card2.add_widget(self.send_progress_label)
        card2.bind(minimum_height=card2.setter('height'))
        layout.add_widget(card2)

        scroll.add_widget(layout)
        return scroll

    def _build_files_tab(self):
        scroll = ScrollView()
        self.files_layout = GridLayout(cols=1, spacing=dp(6), padding=dp(12),
                                        size_hint_y=None)
        self.files_layout.bind(minimum_height=self.files_layout.setter('height'))

        refresh_btn = StyledButton(text='🔄 Refresh', bg_color=(0.17, 0.18, 0.21, 1))
        refresh_btn.bind(on_press=lambda b: self.refresh_files())
        self.files_layout.add_widget(refresh_btn)

        self.files_list_box = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.files_list_box.bind(minimum_height=self.files_list_box.setter('height'))
        self.files_layout.add_widget(self.files_list_box)

        scroll.add_widget(self.files_layout)
        Clock.schedule_once(lambda dt: self.refresh_files(), 1)
        return scroll

    def _build_devices_tab(self):
        scroll = ScrollView()
        layout = GridLayout(cols=1, spacing=dp(10), padding=dp(12), size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        card = CardBox()
        card.add_widget(StyledLabel(text='[b]🔍 Device Discovery[/b]', markup=True,
                                     color=(1, 0.55, 0.26, 1)))

        scan_btn = StyledButton(text='🔄 Scan Network')
        scan_btn.bind(on_press=self.scan_devices)
        card.add_widget(scan_btn)

        self.scan_status = StyledLabel(text='Tap "Scan Network" to find devices',
                                        color=(0.55, 0.57, 0.66, 1))
        card.add_widget(self.scan_status)

        card.bind(minimum_height=card.setter('height'))
        layout.add_widget(card)

        self.devices_list_box = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.devices_list_box.bind(minimum_height=self.devices_list_box.setter('height'))
        layout.add_widget(self.devices_list_box)

        scroll.add_widget(layout)
        return scroll

    # ====== Actions ======
    def toggle_receiver(self, btn):
        if self.receiver_running:
            self.receiver.stop()
            self.discovery.stop()
            self.receiver_running = False
            self.receiver_btn.text = '▶ Start Receiver'
            self.receiver_btn.background_color = (1, 0.42, 0, 1)
            self.receiver_status.text = 'Status: Stopped'
            self.url_label.text = ''
            self._log('Receiver stopped')
            return

        try:
            port = int(self.port_input.text or PORT)
        except:
            port = PORT
        pin = self.pin_input.text.strip()

        try:
            self.receiver.start(
                port=port, pin=pin, save_dir=self.save_dir,
                on_receive=self._on_file_received,
                on_progress=self._on_recv_progress
            )
            self.discovery.start(port)
            self.receiver_running = True
            self.receiver_btn.text = '⏹ Stop Receiver'
            self.receiver_btn.background_color = (0.8, 0.2, 0.2, 1)
            ip_str = ', '.join(self.ips)
            self.receiver_status.text = f'✅ Running on port {port}'
            urls = '\n'.join(f'http://{ip}:{port}' for ip in self.ips)
            self.url_label.text = urls
            self._log(f'Receiver started on {ip_str}:{port}')
        except Exception as e:
            self.receiver_status.text = f'❌ Error: {e}'
            self._log(f'Error: {e}')

    def _on_file_received(self, name, size):
        Clock.schedule_once(lambda dt: self._log(f'✅ Received: {name} ({human_size(size)})'))
        Clock.schedule_once(lambda dt: self.refresh_files())
        Clock.schedule_once(lambda dt: setattr(self.recv_progress, 'value', 100))
        Clock.schedule_once(lambda dt: setattr(self.recv_progress_label, 'text', f'Done: {name}'))

    def _on_recv_progress(self, fname, received, total):
        if total > 0:
            pct = (received / total) * 100
            Clock.schedule_once(lambda dt: setattr(self.recv_progress, 'value', pct))
            Clock.schedule_once(lambda dt: setattr(
                self.recv_progress_label, 'text',
                f'Receiving: {fname} ({human_size(received)}/{human_size(total)})'
            ))

    def _log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        current = self.recv_log.text if self.recv_log.text != 'Ready' else ''
        lines = current.split('\n') if current else []
        lines.insert(0, f'[{now}] {msg}')
        if len(lines) > 25:
            lines = lines[:25]
        self.recv_log.text = '\n'.join(lines)

    def pick_files(self, btn):
        if platform == 'android':
            self._android_pick_files()
        else:
            self._desktop_pick_files()

    def _desktop_pick_files(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            files = filedialog.askopenfilenames(title="Select files to send")
            root.destroy()
            if files:
                self.selected_files = list(files)
                names = [os.path.basename(f) for f in self.selected_files]
                preview = ', '.join(names[:3])
                more = f' +{len(names)-3} more' if len(names) > 3 else ''
                self.selected_label.text = f'{len(names)} file(s): {preview}{more}'
        except Exception as e:
            self.selected_label.text = f'Error: {e}'

    def _android_pick_files(self):
        try:
            from plyer import filechooser
            selection = filechooser.open_file(multiple=True)
            if selection:
                self.selected_files = selection
                self.selected_label.text = f'{len(selection)} file(s) selected'
        except Exception as e:
            self.selected_label.text = f'Picker error: {e}'

    def send_files(self, btn):
        if not self.selected_files:
            self.send_progress_label.text = '❌ No files selected'
            return

        host = self.target_ip.text.strip()
        try:
            port = int(self.target_port.text or PORT)
        except:
            port = PORT
        pin = self.target_pin.text.strip()

        if not host:
            self.send_progress_label.text = '❌ Enter receiver IP'
            return

        self.send_progress_label.text = 'Connecting...'
        self.send_progress.value = 0

        files_to_send = list(self.selected_files)

        def do_send():
            try:
                import http.client
                total_files = len(files_to_send)

                for i, fpath in enumerate(files_to_send):
                    if not os.path.isfile(fpath):
                        continue

                    fname = os.path.basename(fpath)
                    fsize = os.path.getsize(fpath)
                    idx = i + 1

                    Clock.schedule_once(lambda dt, n=fname, x=idx:
                        setattr(self.send_progress_label, 'text',
                                f'Sending ({x}/{total_files}) {n}'))

                    conn = http.client.HTTPConnection(host, port, timeout=600)
                    conn.putrequest('POST', '/upload')
                    conn.putheader('x-pin', pin)
                    conn.putheader('x-file-name', quote(fname))
                    conn.putheader('Content-Length', str(fsize))
                    conn.putheader('Content-Type', 'application/octet-stream')
                    conn.endheaders()

                    sent = 0
                    with open(fpath, 'rb') as f:
                        while True:
                            chunk = f.read(1024 * 1024)
                            if not chunk: break
                            conn.send(chunk)
                            sent += len(chunk)
                            pct = (sent / fsize) * 100 if fsize > 0 else 100
                            Clock.schedule_once(lambda dt, p=pct:
                                setattr(self.send_progress, 'value', p))
                            Clock.schedule_once(lambda dt, n=fname, s=sent, t=fsize:
                                setattr(self.send_progress_label, 'text',
                                        f'{n}: {human_size(s)}/{human_size(t)}'))

                    resp = conn.getresponse()
                    resp.read()
                    conn.close()

                    if resp.status != 200:
                        raise Exception(f'Server returned {resp.status}')

                Clock.schedule_once(lambda dt:
                    setattr(self.send_progress_label, 'text', '✅ All files sent!'))
                Clock.schedule_once(lambda dt:
                    setattr(self.send_progress, 'value', 100))
            except Exception as e:
                err = str(e)
                Clock.schedule_once(lambda dt:
                    setattr(self.send_progress_label, 'text', f'❌ {err}'))

        threading.Thread(target=do_send, daemon=True).start()

    def refresh_files(self, *args):
        self.files_list_box.clear_widgets()
        try:
            files = sorted(os.listdir(self.save_dir))
            actual_files = [f for f in files if os.path.isfile(os.path.join(self.save_dir, f))]

            if not actual_files:
                self.files_list_box.add_widget(
                    StyledLabel(text='No files yet', color=(0.55, 0.57, 0.66, 1)))
                return

            for name in actual_files:
                full = os.path.join(self.save_dir, name)
                size = human_size(os.path.getsize(full))
                row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6),
                                padding=[dp(8), 0])

                with row.canvas.before:
                    Color(0.06, 0.07, 0.08, 1)
                    r = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(8)])
                row.bind(pos=lambda inst, val, r=r: setattr(r, 'pos', val),
                         size=lambda inst, val, r=r: setattr(r, 'size', val))

                lbl = Label(text=name, font_size=dp(12),
                           halign='left', valign='middle',
                           color=(0.9, 0.9, 0.9, 1), shorten=True)
                lbl.bind(size=lbl.setter('text_size'))
                row.add_widget(lbl)

                sz = Label(text=size, font_size=dp(11), size_hint_x=0.3,
                          color=(0.55, 0.57, 0.66, 1))
                row.add_widget(sz)

                del_btn = Button(text='🗑', size_hint_x=0.15,
                                 background_normal='',
                                 background_color=(0.8, 0.2, 0.2, 1),
                                 font_size=dp(14))
                del_btn.bind(on_press=lambda b, n=name: self.delete_file(n))
                row.add_widget(del_btn)

                self.files_list_box.add_widget(row)
        except Exception as e:
            self.files_list_box.add_widget(
                StyledLabel(text=f'Error: {e}', color=(1, 0.3, 0.3, 1)))

    def delete_file(self, name):
        try:
            os.remove(os.path.join(self.save_dir, name))
            self.refresh_files()
        except Exception as e:
            print(f"Delete error: {e}")

    def scan_devices(self, btn):
        self.scan_status.text = '⏳ Scanning network...'
        self.devices_list_box.clear_widgets()

        try:
            port = int(self.port_input.text or PORT)
        except:
            port = PORT

        def do_scan():
            devices = list(self.discovery.get_devices())

            if self.ips:
                manual = scan_network(self.ips[0], port)
                seen_ips = {d['ip'] for d in devices}
                for m in manual:
                    if m['ip'] not in seen_ips:
                        devices.append(m)

            self.discovered_devices = devices
            Clock.schedule_once(lambda dt: self._show_devices())

        threading.Thread(target=do_scan, daemon=True).start()

    def _show_devices(self):
        self.devices_list_box.clear_widgets()

        if not self.discovered_devices:
            self.scan_status.text = 'No devices found'
            self.devices_list_box.add_widget(StyledLabel(
                text='No devices on this network.\nMake sure other device is running FastDrop\nand on same Wi-Fi.',
                height=dp(70), color=(0.55, 0.57, 0.66, 1)))
            return

        self.scan_status.text = f'Found {len(self.discovered_devices)} device(s)'

        for dev in self.discovered_devices:
            card = CardBox()
            card.add_widget(StyledLabel(
                text=f'📱 {dev["name"]}',
                color=(1, 0.55, 0.26, 1), height=dp(28)))
            card.add_widget(StyledLabel(
                text=f'{dev["ip"]}:{dev["port"]}',
                color=(0.55, 0.57, 0.66, 1), height=dp(22)))

            connect_btn = StyledButton(text='🔗 Use as Target',
                                        bg_color=(0.17, 0.18, 0.21, 1))
            connect_btn.bind(on_press=lambda b, d=dev: self._connect_device(d))
            card.add_widget(connect_btn)

            card.bind(minimum_height=card.setter('height'))
            self.devices_list_box.add_widget(card)

    def _connect_device(self, dev):
        self.target_ip.text = dev['ip']
        self.target_port.text = str(dev['port'])
        # Switch to Send tab (index 1)
        for tab in self.tabs.tab_list:
            if 'Send' in tab.text:
                self.tabs.switch_to(tab)
                break

    def on_stop(self):
        self.receiver.stop()
        self.discovery.stop()

if __name__ == '__main__':
    FastDropApp().run()