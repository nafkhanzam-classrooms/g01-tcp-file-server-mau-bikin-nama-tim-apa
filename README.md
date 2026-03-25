[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
| Joaquin Fairuz Nawfal Ismono               |  5025241106          |      D     |
|  Steven Alvin Christian              | 5025241116           |     D      |

## Pembagian Tugas Anggota Kelompok
1. Joaquin Fairuz Nawfal Ismono: Membuat file `client.py`, `server-poll.py`, `server-select.py`.
2. Steven Alvin Christian: Membuat file `server-sync.py`, `server-thread.py`, dan menambahkan beberapa antarmuka.

## Link Youtube (Unlisted)
Link ditaruh di bawah ini
```

```

## Penjelasan Program

### Protokol Komunikasi
Semua file menggunakan protokol **length-prefixed framing** untuk komunikasi TCP:
- **`send_msg(sock, data)`**: Sebelum mengirim data, fungsi ini membuat header 4 byte menggunakan `struct.pack(">I", len(data))` yang menyimpan panjang data dalam format big-endian unsigned int. Header kemudian digabung dengan data asli dan dikirim sekaligus via `sock.sendall()`. Ini memastikan penerima tahu persis berapa byte yang harus dibaca.
- **`recv_msg(sock)`**: Membaca 4 byte pertama sebagai header, membongkar nilainya dengan `struct.unpack` untuk mendapatkan panjang pesan, lalu membaca data sejumlah byte tersebut dalam loop hingga buffer penuh. Loop diperlukan karena TCP tidak menjamin semua data tiba dalam satu `recv()`.

---

### client.py

```
import socket
import threading
import struct
import os
import sys

C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_RESET = "\033[0m"
C_YELLOW= "\033[1;33m"
C_BOLD = "\033[1m"

CLIENT_FILES_DIR = "client_files"
os.makedirs(CLIENT_FILES_DIR, exist_ok=True)

def send_msg(sock, data):
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    length = struct.unpack(">I", header)[0]
    if not header or len(header) < 4:
        return None
    buf = b""
    while len(buf) < length:
        buf += sock.recv(length - len(buf))
    return buf

def handle_list(sock):
    send_msg(sock, b"/list")

def handle_download(sock, cmd):
    parts = cmd.split()
    if len(parts) == 1:
        print(f"{C_RED}[ERROR]: Please specify a filename. Usage: /download <filename>{C_RESET}")
        return
    if len(parts) > 2:
        print(f"{C_RED}[ERROR]: Too many arguments. Please provide only one filename.{C_RESET}")
        return
    filename = parts[1]
    print(f"{C_YELLOW}[DOWNLOAD]: Starting download for '{filename}'...{C_RESET}")
    send_msg(sock, f"/download {filename}".encode())

def handle_upload(sock, cmd):
    parts = cmd.split()
    if len(parts) == 1:
        print(f"{C_RED}[ERROR]: Please specify a filename. Usage: /upload <filename>{C_RESET}")
        return
    if len(parts) > 2:
        print(f"{C_RED}[ERROR]: Too many arguments. Please upload one file at a time.{C_RESET}")
        return

    filename = parts[1]
    filepath = os.path.join(CLIENT_FILES_DIR, filename)
    
    if os.path.exists(filepath):
        try:
            print(f"{C_YELLOW}[PENDING]: Uploading '{filename}' to server...{C_RESET}")
            with open(filepath, "rb") as f:
                filedata = f.read()
            payload = f"/upload {filename}:".encode() + filedata
            send_msg(sock, payload)
        except Exception as e:
            print(f"{C_RED}[ERROR]: Failed to read file: {e}{C_RESET}")
    else:
        print(f"{C_RED}[ERROR]: File '{filename}' not found in {CLIENT_FILES_DIR}/{C_RESET}")

def print_menu():
    print(f"\n{C_BOLD}{'-'*24} COMMAND LIST {'-'*24}{C_RESET}")
    print("/list\t\t\t: View files available on server")
    print("/upload <filename>\t: Upload a file to server")
    print("/download <filename>\t: Download a file from server")
    print("/exit\t\t\t: Close connection")
    print("<type message>\t\t: Send a text message (Chat)")
    print("-" * 62)

def receive_handler(sock):
    while True:
        data = recv_msg(sock)
        if data is None:
            print(f"\n{C_RED}[INFO]: Disconnected from server.{C_RESET}")
            os._exit(0)

        sys.stdout.write('\r\033[K')
        
        if data.startswith(b"/download "):
            try:
                content = data[10:]
                header, filedata = content.split(b":", 1)
                filename = header.decode('utf-8')
                
                filepath = os.path.join(CLIENT_FILES_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(filedata)
                
                print(f"{C_GREEN}[SUCCESS]: File '{filename}' downloaded to {CLIENT_FILES_DIR}/{C_RESET}")
            except Exception as e:
                print(f"{C_RED}[ERROR]: Failed to save downloaded file: {e}{C_RESET}")
            return
            
        try:
            msg_str = data.decode('utf-8', errors='ignore')
            if any(key in msg_str for key in ["[LIST]", "[INFO]", "[SUCCESS]", "[UPLOAD]", "[DOWNLOAD]"]):
                print(f"{C_GREEN}{msg_str}{C_RESET}")
            elif "[ERROR]" in msg_str:
                print(f"{C_RED}{msg_str}{C_RESET}")
            else:
                print(msg_str)
        except Exception:
            pass

        print("> ", end="")
        sys.stdout.flush()

def main():
    os.system("clear")
    name = input("Enter your username: ").strip() or "Anonymous"

    print(f"\n{C_BOLD}--- Connection Settings ---{C_RESET}")
    target_ip = input("Enter Server IP: ").strip()
    target_port = int(input("Enter Server Port: ").strip())

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"{C_GREEN}[INFO]: Connecting to {target_ip}:{target_port}...{C_RESET}")
        s.connect((target_ip, target_port))
        send_msg(s, f"/name {name}".encode())
        print(f"{C_GREEN}[INFO]: Successfully connected!{C_RESET}")
    except Exception as exception:
        print(f"{C_RED}[ERROR]: Connection failed: {exception}{C_RESET}")
        return

    print_menu()
    
    threading.Thread(target=receive_handler, args=(s,), daemon=True).start()

    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            if cmd == "/exit":
                print(f"{C_RED}[INFO]: Closing connection...{C_RESET}")
                s.close()
                os._exit(0)
            elif cmd == "/list":
                handle_list(s)
            elif cmd.startswith("/download "):
                handle_download(s, cmd)
            elif cmd.startswith("/upload "):
                handle_upload(s, cmd)
            elif cmd.startswith("/"):
                print(f"{C_RED}[ERROR]: Unknown command.{C_RESET}")
            else:
                send_msg(s, cmd.encode())
                
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_RED}[INFO]: Connection interrupted by user.{C_RESET}")
            break

if __name__ == "__main__":
    main()
```

**Alur kerja utama (`main`):**
1. Meminta input username, IP server, dan port dari pengguna.
2. Membuat TCP socket dan memanggil `s.connect()` ke server.
3. Mengirim `/name <username>` ke server sebagai identifikasi awal.
4. Menampilkan menu perintah via `print_menu()`.
5. Menjalankan `receive_handler` di thread terpisah (daemon) agar bisa menerima pesan dari server secara paralel tanpa memblokir input.
6. Masuk ke loop utama `input("> ")` untuk membaca perintah pengguna.

\
**Fungsi-fungsi:**
- **`send_msg(sock, data)`**: Mengirim data dengan length-prefixed framing ke server.
- **`recv_msg(sock)`**: Membaca pesan penuh dari server berdasarkan header panjang.
- **`handle_list(sock)`**: Mengirim perintah `b"/list"` ke server.
- **`handle_download(sock, cmd)`**: Memvalidasi argumen (harus tepat 1 filename), lalu mengirim `/download <filename>` ke server.
- **`handle_upload(sock, cmd)`**: Memvalidasi argumen, membaca file dari folder `client_files/` secara binary, lalu membungkus data dalam format `/upload <filename>:<binary_data>` dan mengirimnya.
- **`receive_handler(sock)`**: Berjalan di thread terpisah. Terus-menerus memanggil `recv_msg()` dan mencetak respons dari server dengan warna sesuai label (`[LIST]`, `[SUCCESS]`, `[ERROR]`, dll), mendownload `<filename>`, dan memanggil `os._exit(0)` jika koneksi terputus.
- **`print_menu()`**: Menampilkan daftar perintah yang tersedia ke terminal.

---

### server-sync.py

```
import socket
import struct
import os

S_IP = "0.0.0.0"
S_PORT = 5000
S_GREEN = "\033[1;32m"
S_RED = "\033[1;31m"
S_CYAN = "\033[1;36m"
S_YELLOW = "\033[1;33m"
S_RESET = "\033[0m"
S_BOLD = "\033[1m"

SERVER_FILES_DIR = "server_files"
os.makedirs(SERVER_FILES_DIR, exist_ok=True)

def send_msg(sock, data):
    if isinstance(data, str): data = data.encode()
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack(">I", header)[0]
    buf = b""
    while len(buf) < length:
        buf += sock.recv(length - len(buf))
    return buf

def process_command(sock, data, addr, client_name="Anonymous"):
    addr_str = f"{S_CYAN}({client_name}-{addr[0]}:{addr[1]}){S_RESET}"
    
    p_label = f"{S_YELLOW}[PROCESS]{S_RESET}"

    # 1. Handle List
    if data == b"/list":
        print(f"{p_label} {addr_str}: Requested file list.")
        files = os.listdir(SERVER_FILES_DIR)
        res = ", ".join(files) if files else "Directory is empty."
        send_msg(sock, f"[LIST]: {res}")

    # 2. Handle Download
    elif data.startswith(b"/download "):
        filename = data[10:].decode('utf-8', errors='ignore')
        filepath = os.path.join(SERVER_FILES_DIR, filename)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            print(f"{p_label} {addr_str}: Sending file: '{filename}'.")
            with open(filepath, "rb") as f:
                filedata = f.read()
            payload = f"/download {filename}:".encode('utf-8') + filedata
            send_msg(sock, payload)
            print(f"{p_label} {addr_str}: {S_GREEN}Download '{filename}' is successful.{S_RESET}")
            send_msg(sock, f"[SUCCESS]: Download '{filename}' is finished.")
        else:
            print(f"{p_label} {addr_str}: {S_RED}Download failed because '{filename}' not found.{S_RESET}")
            send_msg(sock, f"[ERROR]: File '{filename}' not found.")

    # 3. Handle Upload
    elif data.startswith(b"/upload "):
        try:
            content = data[8:]
            header, filedata = content.split(b":", 1)
            filename = header.decode('utf-8')
            
            print(f"{p_label} {addr_str}: Receiving '{filename}'.")
            with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                f.write(filedata)
            
            send_msg(sock, f"[SUCCESS]: File '{filename}' stored on server.")
            print(f"{p_label} {addr_str}: {S_GREEN}Receiving '{filename}' is complete.{S_RESET}")
        except Exception as e:
            print(f"{p_label} {addr_str}: {S_RED}Receiving error {e}.{S_RESET}")
            send_msg(sock, b"[ERROR]: Receiving failed.")

    # 4. Handle Chat
    else:
        msg = data.decode('utf-8', errors='ignore')
        print(f"{S_BOLD}[CHAT]{S_RESET} {addr_str}: {msg}")
        send_msg(sock, f"[{client_name}]: {msg}")

def client_handler(sock, addr):
    print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {addr[0]}:{addr[1]}.")
    client_name = "Anonymous"
    try:
        while True:
            data = recv_msg(sock)
            if not data: break
            if data.startswith(b"/name "):
                client_name = data[6:].decode('utf-8', errors='ignore')
                print(f"{S_CYAN}[INFO]{S_RESET}: {client_name} has joined from {addr[0]}:{addr[1]}.")
                continue
            process_command(sock, data, addr, client_name)
    finally:
        print(f"{S_RED}[DISCONNECTED]{S_RESET}: Connection closed for {addr[0]}:{addr[1]}")
        sock.close()

def main():
    os.system("clear")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        s.bind((S_IP, S_PORT))
        s.listen(1)
        print(f"{S_BOLD}{S_GREEN}[INFO]: Server Sync is running on port {S_PORT}...{S_RESET}")
    except Exception as e:
        print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
        return

    while True:
        c_sock, addr = s.accept()
        client_handler(c_sock, addr)

if __name__ == "__main__":
    main()
```

**Konsep:** Server sinkron: melayani satu client saja.

**Alur kerja utama (`main`):**
1. Membuat server socket, bind ke `0.0.0.0:5000`, dan mulai listen.
2. Loop `s.accept()` menunggu koneksi masuk.
3. Setiap koneksi baru dilayani oleh `client_handler` dan apabila sudah ada yg dilayani, maka dia akan ngelock dan tidak ada client lain yang bisa memerintah server.

\
**Fungsi-fungsi:**
- **`send_msg(sock, data)`**: Mengirim data dengan length-prefixed framing.
- **`recv_msg(sock)`**: Membaca pesan penuh dari client.
- **`process_command(sock, data, addr, client_name)`**: Mem-parsing data yang diterima dan menjalankan aksi yang sesuai:
  - `b"/list"`: Membaca isi folder `./server_files` dengan `os.listdir()`, menggabungkan nama file menjadi satu string, lalu mengirim balik dengan label `[LIST]`.
  - `b"/download <filename>"`: Mengekstrak nama file dari byte ke-10 dan seterusnya, memeriksa keberadaan file di server, lalu mengirim konfirmasi `[SUCCESS]` ke client.
  - `b"/upload <filename>:<data>"`: Memisahkan header nama file dan binary data menggunakan `split(b":", 1)`, lalu menyimpan file ke folder server dengan `open(..., "wb")`.
  - Teks biasa: Meng-echo pesan kembali ke pengirim dengan format `[username]: pesan`.
- **`client_handler(sock, addr)`**: Loop penerimaan pesan untuk satu client. Mendeteksi perintah `/name` untuk menyimpan nama client, lalu meneruskan data ke `process_command`. Memanggil `sock.close()` di blok `finally` saat client disconnect.

---

### server-thread.py

```
import socket
import threading
import struct
import os

S_IP = "0.0.0.0"
S_PORT = 5000
S_GREEN= "\033[1;32m"
S_RED = "\033[1;31m"
S_CYAN = "\033[1;36m"
S_YELLOW = "\033[1;33m"
S_RESET= "\033[0m"
S_BOLD = "\033[1m"

SERVER_FILES_DIR = "server_files"
os.makedirs(SERVER_FILES_DIR, exist_ok=True)

clients_lock = threading.Lock()
clients  = {}

def send_msg(sock, data):
    if isinstance(data, str): data = data.encode()
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack(">I", header)[0]
    buf = b""
    while len(buf) < length:
        chunk = sock.recv(length - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

def broadcast(snapshot, sender_sock, message):
    dead = []
    for sock in snapshot:
        if sock is not sender_sock:
            try:
                send_msg(sock, message)
            except OSError:
                dead.append(sock)
    return dead

def process_command(sock, data, snapshot):
    addr = snapshot[sock]["addr"]
    name= snapshot[sock]["name"]
    addr_str = f"{S_CYAN}({name}-{addr[0]}:{addr[1]}){S_RESET}"
    p_label = f"{S_YELLOW}[PROCESS]{S_RESET}"

    # 1. Handle List
    if data == b"/list":
        print(f"{p_label} {addr_str}: Requested file list.")
        files = os.listdir(SERVER_FILES_DIR)
        res = ", ".join(files) if files else "Directory is empty."
        send_msg(sock, f"[LIST]: {res}")
        return []

    # 2. Handle Download
    elif data.startswith(b"/download "):
        filename = data[10:].decode('utf-8', errors='ignore')
        filepath = os.path.join(SERVER_FILES_DIR, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            print(f"{p_label} {addr_str}: Sending file: '{filename}'.")
            with open(filepath, "rb") as f:
                filedata = f.read()
            payload = f"/download {filename}:".encode('utf-8') + filedata
            send_msg(sock, payload)
            print(f"{p_label} {addr_str}: {S_GREEN}Download '{filename}' is successful.{S_RESET}")
            send_msg(sock, f"[SUCCESS]: Download '{filename}' is finished.")
        else:
            print(f"{p_label} {addr_str}: {S_RED}Download failed, '{filename}' not found.{S_RESET}")
            send_msg(sock, f"[ERROR]: File '{filename}' not found.")
        return []

    # 3. Handle Upload
    elif data.startswith(b"/upload "):
        try:
            content = data[8:]
            file_header, filedata = content.split(b":", 1)
            filename = file_header.decode('utf-8')
            print(f"{p_label} {addr_str}: Receiving '{filename}'.")
            with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                f.write(filedata)
            send_msg(sock, f"[SUCCESS]: File '{filename}' stored on server.")
            print(f"{p_label} {addr_str}: {S_GREEN}Receiving '{filename}' is complete.{S_RESET}")
        except Exception as e:
            print(f"{p_label} {addr_str}: {S_RED}Receiving error: {e}.{S_RESET}")
            send_msg(sock, "[ERROR]: Upload failed.")
        return []

    # 4. Handle Chat
    else:
        msg = data.decode('utf-8', errors='ignore')
        print(f"{S_BOLD}[CHAT]{S_RESET} {addr_str}: {msg}")
        dead = broadcast(snapshot, sock, f"[{name}]: {msg}")
        return dead


class ClientHandler(threading.Thread):
    def __init__(self, sock, addr):
        super().__init__(daemon=True)
        self.sock = sock
        self.addr = addr

    def run(self):
        print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {self.addr[0]}:{self.addr[1]}.")
        with clients_lock:
            clients[self.sock] = {"addr": self.addr, "name": "Anonymous"}

        try:
            while True:
                data = recv_msg(self.sock)
                if not data:
                    break

                if data.startswith(b"/name "):
                    name = data[6:].decode('utf-8', errors='ignore')
                    with clients_lock:
                        clients[self.sock]["name"] = name
                    print(f"{S_CYAN}[INFO]{S_RESET}: {name} has joined from {self.addr[0]}:{self.addr[1]}.")
                    continue

                with clients_lock:
                    snapshot = dict(clients)

                dead = process_command(self.sock, data, snapshot)

                with clients_lock:
                    for d in dead:
                        clients.pop(d, None)
                for d in dead:
                    try:
                        d.close()
                    except OSError:
                        pass

        finally:
            with clients_lock:
                info = clients.pop(self.sock, {})
            name = info.get("name", "Anonymous")
            print(f"{S_RED}[DISCONNECTED]{S_RESET}: {name} from {self.addr[0]}:{self.addr[1]}.")
            try:
                self.sock.close()
            except OSError:
                pass


class Server:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        os.system("clear")
        try:
            self.server.bind((S_IP, S_PORT))
            self.server.listen(5)
            print(f"{S_BOLD}{S_GREEN}[INFO]: Server Thread is running on port {S_PORT}...{S_RESET}")
        except Exception as e:
            print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
            return

        try:
            while True:
                c_sock, addr = self.server.accept()
                ClientHandler(c_sock, addr).start()
        except KeyboardInterrupt:
            print(f"\n{S_RED}[INFO]: Server shutting down.{S_RESET}")
        finally:
            self.server.close()


if __name__ == "__main__":
    Server().run()
```

**Konsep:** Setiap client mendapat thread OS tersendiri via `ClientHandler(threading.Thread)`. Semua thread berbagi satu dict `clients` global, dilindungi oleh `clients_lock = threading.Lock()` untuk menghindari race condition.

**Alur kerja utama (`Server.run`):**
1. `Server.__init__` membuat socket dan mengatur `SO_REUSEADDR`.
2. `Server.run` melakukan bind, listen, lalu loop `self.server.accept()`.
3. Setiap koneksi baru membuat `ClientHandler(c_sock, addr)` dan memanggil `.start()` untuk menjalankannya di thread baru.

\
**Fungsi & Class:**
- **`broadcast(snapshot, sender_sock, message)`**: Iterasi seluruh socket dalam snapshot (salinan dict clients), mengirim pesan ke semua socket **kecuali pengirim**. Mengumpulkan socket yang gagal kirim (koneksi putus) dalam list `dead` dan mengembalikannya.
- **`process_command(sock, data, snapshot)`**: Sama seperti sync, namun untuk chat memanggil `broadcast()` ke semua client lain menggunakan snapshot. Mengembalikan list socket yang dead hasil broadcast.
- **`ClientHandler.run()`**: Inti dari setiap thread client, yang berfungsi:
    - Mendaftarkan socket ke `clients` dict dengan lock.
    - Loop `recv_msg()` tanpa henti.
    - Jika menerima `/name`, update nama di `clients` dengan lock.
  - Untuk perintah lain: ambil **snapshot** `dict(clients)` di bawah lock (agar tidak hold lock saat I/O berlangsung), lalu panggil `process_command` dengan snapshot tersebut.
  - Hapus socket dead dari `clients` dengan lock, lalu tutup socketnya.
  - Blok `finally` memastikan client selalu dihapus dari `clients` dan socket ditutup meskipun terjadi exception.

---

### server-select.py

```
import socket
import select
import struct
import os

S_IP = "0.0.0.0"
S_PORT = 5000
S_GREEN= "\033[1;32m"
S_RED = "\033[1;31m"
S_CYAN = "\033[1;36m"
S_YELLOW = "\033[1;33m"
S_RESET= "\033[0m"
S_BOLD = "\033[1m"

SERVER_FILES_DIR = "server_files"
os.makedirs(SERVER_FILES_DIR, exist_ok=True)

def send_msg(sock, data):
    if isinstance(data, str): data = data.encode()
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack(">I", header)[0]
    buf = b""
    while len(buf) < length:
        chunk = sock.recv(length - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

def broadcast(clients, sender_sock, message):
    dead = []
    for sock in list(clients):
        if sock is not sender_sock:
            try:
                send_msg(sock, message)
            except OSError:
                dead.append(sock)
    return dead

def process_command(sock, data, clients):
    addr = clients[sock]["addr"]
    name = clients[sock]["name"]
    addr_str = f"{S_CYAN}({name}-{addr[0]}:{addr[1]}){S_RESET}"
    p_label = f"{S_YELLOW}[PROCESS]{S_RESET}"

    # 1. Handle List
    if data == b"/list":
        print(f"{p_label} {addr_str}: Requested file list.")
        files = os.listdir(SERVER_FILES_DIR)
        res = ", ".join(files) if files else "Directory is empty."
        send_msg(sock, f"[LIST]: {res}")
        return []

    # 2. Handle Download
    elif data.startswith(b"/download "):
        filename = data[10:].decode('utf-8', errors='ignore')
        filepath = os.path.join(SERVER_FILES_DIR, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            print(f"{p_label} {addr_str}: Sending file: '{filename}'.")
            with open(filepath, "rb") as f:
                filedata = f.read()
            payload = f"/download {filename}:".encode('utf-8') + filedata
            send_msg(sock, payload)
            print(f"{p_label} {addr_str}: {S_GREEN}Download '{filename}' is successful.{S_RESET}")
            send_msg(sock, f"[SUCCESS]: Download '{filename}' is finished.")
        else:
            print(f"{p_label} {addr_str}: {S_RED}Download failed, '{filename}' not found.{S_RESET}")
            send_msg(sock, f"[ERROR]: File '{filename}' not found.")
        return []

    # 3. Handle Upload
    elif data.startswith(b"/upload "):
        try:
            content = data[8:]
            file_header, filedata = content.split(b":", 1)
            filename = file_header.decode('utf-8')
            print(f"{p_label} {addr_str}: Receiving '{filename}'.")
            with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                f.write(filedata)
            send_msg(sock, f"[SUCCESS]: File '{filename}' stored on server.")
            print(f"{p_label} {addr_str}: {S_GREEN}Receiving '{filename}' is complete.{S_RESET}")
        except Exception as e:
            print(f"{p_label} {addr_str}: {S_RED}Receiving error: {e}.{S_RESET}")
            send_msg(sock, "[ERROR]: Upload failed.")
        return []

    # 4. Handle Chat
    else:
        msg = data.decode('utf-8', errors='ignore')
        print(f"{S_BOLD}[CHAT]{S_RESET} {addr_str}: {msg}")
        dead = broadcast(clients, sock, f"[{name}]: {msg}")
        return dead

def remove_client(sock, sockets, clients):
    info = clients.pop(sock, {})
    addr = info.get("addr", ("?", "?"))
    name = info.get("name", "Anonymous")
    print(f"{S_RED}[DISCONNECTED]{S_RESET}: {name} from {addr[0]}:{addr[1]}.")
    if sock in sockets:
        sockets.remove(sock)
    try:
        sock.close()
    except OSError:
        pass

def main():
    os.system("clear")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        s.bind((S_IP, S_PORT))
        s.listen(5)
        print(f"{S_BOLD}{S_GREEN}[INFO]: Server Select is running on port {S_PORT}...{S_RESET}")
    except Exception as e:
        print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
        return

    sockets = [s]
    clients = {}

    while True:
        read_ready, _, _ = select.select(sockets, [], [])

        for sock in read_ready:
            if sock is s:
                c_sock, addr = s.accept()
                sockets.append(c_sock)
                clients[c_sock] = {"addr": addr, "name": "Anonymous"}
                print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {addr[0]}:{addr[1]}.")

            else:
                data = recv_msg(sock)
                if not data:
                    remove_client(sock, sockets, clients)
                    continue

                if data.startswith(b"/name "):
                    name = data[6:].decode('utf-8', errors='ignore')
                    clients[sock]["name"] = name
                    addr = clients[sock]["addr"]
                    print(f"{S_CYAN}[INFO]{S_RESET}: {name} has joined from {addr[0]}:{addr[1]}.")
                    continue

                dead = process_command(sock, data, clients)
                for d in dead:
                    remove_client(d, sockets, clients)

if __name__ == "__main__":
    main()
```

**Konsep:** Single-thread dengan I/O multiplexing menggunakan `select.select()`. Server tidak pernah blocking menunggu satu client: ia memantau semua socket sekaligus dan hanya memproses yang sudah siap dibaca.

**Struktur data:**
- `sockets`: list berisi server socket + semua client socket yang aktif, digunakan sebagai argumen `select.select()`.
- `clients`: dict `{sock: {"addr": ..., "name": ...}}` untuk menyimpan info tiap client.

**Alur kerja utama (`main`):**
1. Membuat server socket, bind, listen.
2. Inisialisasi `sockets = [s]` dan `clients = {}`.
3. Loop utama memanggil `select.select(sockets, [], [])` yang **memblokir** hingga minimal satu socket siap dibaca, lalu mengembalikan list socket yang aktif (`read_ready`).
4. Iterasi `read_ready`:
- Jika socket adalah server socket `s`: panggil `s.accept()`, tambahkan client socket baru ke `sockets` dan `clients`.
- Jika socket adalah client: panggil `recv_msg()`. Jika data kosong (disconnect), panggil `remove_client()`. Jika ada `/name`, update nama. Selainnya, teruskan ke `process_command()`.

\
**Fungsi-fungsi:**
- **`broadcast(clients, sender_sock, message)`**: Mengirim pesan ke semua socket dalam `clients` kecuali pengirim. Mengembalikan list dead socket.
- **`process_command(sock, data, clients)`**: Memproses perintah dan memanggil `broadcast()` untuk chat. Mengembalikan dead sockets.
- **`remove_client(sock, sockets, clients)`**: Menghapus socket dari `sockets` list dan `clients` dict, lalu menutup koneksi.

---

### server-poll.py

```
import socket
import select
import struct
import os

S_IP = "0.0.0.0"
S_PORT = 5000
S_GREEN= "\033[1;32m"
S_RED = "\033[1;31m"
S_CYAN = "\033[1;36m"
S_YELLOW = "\033[1;33m"
S_RESET= "\033[0m"
S_BOLD = "\033[1m"

SERVER_FILES_DIR = "server_files"
os.makedirs(SERVER_FILES_DIR, exist_ok=True)

def send_msg(sock, data):
    if isinstance(data, str): data = data.encode()
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack(">I", header)[0]
    buf = b""
    while len(buf) < length:
        chunk = sock.recv(length - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

def broadcast(clients, sender_sock, message):
    dead = []
    for sock in list(clients):
        if sock is not sender_sock:
            try:
                send_msg(sock, message)
            except OSError:
                dead.append(sock)
    return dead

def process_command(sock, data, clients):
    addr = clients[sock]["addr"]
    name = clients[sock]["name"]
    addr_str = f"{S_CYAN}({name}-{addr[0]}:{addr[1]}){S_RESET}"
    p_label = f"{S_YELLOW}[PROCESS]{S_RESET}"

    # 1. Handle List
    if data == b"/list":
        print(f"{p_label} {addr_str}: Requested file list.")
        files = os.listdir(SERVER_FILES_DIR)
        res = ", ".join(files) if files else "Directory is empty."
        send_msg(sock, f"[LIST]: {res}")
        return []

    # 2. Handle Download
    elif data.startswith(b"/download "):
        filename = data[10:].decode('utf-8', errors='ignore')
        filepath = os.path.join(SERVER_FILES_DIR, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            print(f"{p_label} {addr_str}: Sending file: '{filename}'.")
            with open(filepath, "rb") as f:
                filedata = f.read()
            payload = f"/download {filename}:".encode('utf-8') + filedata
            send_msg(sock, payload)
            print(f"{p_label} {addr_str}: {S_GREEN}Download '{filename}' is successful.{S_RESET}")
            send_msg(sock, f"[SUCCESS]: Download '{filename}' is finished.")
        else:
            print(f"{p_label} {addr_str}: {S_RED}Download failed, '{filename}' not found.{S_RESET}")
            send_msg(sock, f"[ERROR]: File '{filename}' not found.")
        return []

    # 3. Handle Upload
    elif data.startswith(b"/upload "):
        try:
            content = data[8:]
            file_header, filedata = content.split(b":", 1)
            filename = file_header.decode('utf-8')
            print(f"{p_label} {addr_str}: Receiving '{filename}'.")
            with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                f.write(filedata)
            send_msg(sock, f"[SUCCESS]: File '{filename}' stored on server.")
            print(f"{p_label} {addr_str}: {S_GREEN}Receiving '{filename}' is complete.{S_RESET}")
        except Exception as e:
            print(f"{p_label} {addr_str}: {S_RED}Receiving error: {e}.{S_RESET}")
            send_msg(sock, "[ERROR]: Upload failed.")
        return []

    # 4. Handle Chat
    else:
        msg = data.decode('utf-8', errors='ignore')
        print(f"{S_BOLD}[CHAT]{S_RESET} {addr_str}: {msg}")
        dead = broadcast(clients, sock, f"[{name}]: {msg}")
        return dead

def remove_client(sock, poll_obj, fd_map, clients):
    info = clients.pop(sock, {})
    addr = info.get("addr", ("?", "?"))
    name = info.get("name", "Anonymous")
    print(f"{S_RED}[DISCONNECTED]{S_RESET}: {name} from {addr[0]}:{addr[1]}.")
    fd = sock.fileno()
    try:
        poll_obj.unregister(fd)
    except Exception:
        pass
    fd_map.pop(fd, None)
    try:
        sock.close()
    except OSError:
        pass

def main():
    os.system("clear")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        s.bind((S_IP, S_PORT))
        s.listen(5)
        print(f"{S_BOLD}{S_GREEN}[INFO]: Server Poll is running on port {S_PORT}...{S_RESET}")
    except Exception as e:
        print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
        return

    poll_obj = select.poll()
    poll_obj.register(s.fileno(), select.POLLIN)

    fd_map = {s.fileno(): s}
    clients = {}

    while True:
        for fd, event in poll_obj.poll():
            sock = fd_map[fd]

            if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
                if sock is not s:
                    remove_client(sock, poll_obj, fd_map, clients)
                continue

            if event & select.POLLIN:
                if sock is s:
                    c_sock, addr = s.accept()
                    c_fd = c_sock.fileno()
                    fd_map[c_fd] = c_sock
                    poll_obj.register(c_fd, select.POLLIN)
                    clients[c_sock] = {"addr": addr, "name": "Anonymous"}
                    print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {addr[0]}:{addr[1]}.")

                else:
                    data = recv_msg(sock)
                    if not data:
                        remove_client(sock, poll_obj, fd_map, clients)
                        continue

                    if data.startswith(b"/name "):
                        name = data[6:].decode('utf-8', errors='ignore')
                        clients[sock]["name"] = name
                        addr = clients[sock]["addr"]
                        print(f"{S_CYAN}[INFO]{S_RESET}: {name} has joined from {addr[0]}:{addr[1]}.")
                        continue

                    dead = process_command(sock, data, clients)
                    for d in dead:
                        remove_client(d, poll_obj, fd_map, clients)

if __name__ == "__main__":
    main()
```

**Konsep:** Single-thread dengan I/O multiplexing menggunakan `select.poll()` (Linux/Unix only). Prinsipnya sama dengan select, namun `poll()` bekerja dengan **file descriptor (fd)** bukan socket object langsung, dan tidak memiliki batasan jumlah fd seperti `select` pada beberapa sistem.

**Struktur data:**
- `poll_obj`: objek poll yang mengelola daftar fd yang dipantau.
- `fd_map`: dict `{fd: sock}` untuk mencari socket dari fd yang dilaporkan poll.
- `clients`: dict `{sock: {"addr": ..., "name": ...}}`.

**Alur kerja utama (`main`):**
1. Membuat server socket, bind, listen.
2. Membuat `poll_obj = select.poll()` dan mendaftarkan fd server socket dengan `poll_obj.register(s.fileno(), select.POLLIN)`.
3. Inisialisasi `fd_map = {s.fileno(): s}` dan `clients = {}`.
4. Loop utama memanggil `poll_obj.poll()` yang memblokir hingga ada event, lalu mengembalikan list `(fd, event)`.
5. Untuk tiap `(fd, event)`:
- Cari socket via `fd_map[fd]`.
- Jika event mengandung `POLLHUP | POLLERR | POLLNVAL`: client disconnect tidak normal, panggil `remove_client()`.
- Jika event `POLLIN` dan socket adalah server: terima koneksi baru, daftarkan fd baru ke `poll_obj` dan `fd_map`.
- Jika event `POLLIN` dan socket adalah client: `recv_msg()`, proses perintah.

\
**Fungsi-fungsi:**
- **`broadcast(clients, sender_sock, message)`**: Mengirim pesan ke semua client kecuali pengirim.
- **`process_command(sock, data, clients)`**: Memproses perintah, broadcast chat, mengembalikan dead sockets.
- **`remove_client(sock, poll_obj, fd_map, clients)`**: Memanggil `poll_obj.unregister(fd)` untuk berhenti memantau fd tersebut, menghapus dari `fd_map` dan `clients`, lalu menutup socket.

---

## Screenshot Hasil
