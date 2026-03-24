import base64
import os
import select
import socket

HOST = "127.0.0.1"
PORT = 5000
BUFFER_SIZE = 4096
SERVER_FILES_DIR = "server_files"


def send_line(sock, line):
    sock.sendall((line + "\n").encode())


def broadcast(clients, line):
    broken = []
    for client in clients:
        try:
            send_line(client, line)
        except OSError:
            broken.append(client)
    return broken


def close_client(client, input_sockets, clients, buffers):
    if client in input_sockets:
        input_sockets.remove(client)
    if client in clients:
        del clients[client]
    if client in buffers:
        del buffers[client]
    try:
        client.close()
    except OSError:
        pass


os.makedirs(SERVER_FILES_DIR, exist_ok=True)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

input_sockets = [server_socket]
clients = {}
buffers = {}

print(f"Server listening on {HOST}:{PORT}")

while True:
    read_ready, _, _ = select.select(input_sockets, [], [])

    for sock in read_ready:
        if sock == server_socket:
            client_sock, client_addr = server_socket.accept()
            input_sockets.append(client_sock)
            clients[client_sock] = client_addr
            buffers[client_sock] = ""
            print("Connected:", client_addr)
            send_line(client_sock, "SYSTEM|Connected to server")
            continue

        try:
            data = sock.recv(BUFFER_SIZE)
        except ConnectionResetError:
            data = b""

        if not data:
            addr = clients.get(sock)
            if addr:
                print("Disconnected:", addr)
            close_client(sock, input_sockets, clients, buffers)
            continue

        buffers[sock] += data.decode(errors="replace")

        while "\n" in buffers[sock]:
            line, buffers[sock] = buffers[sock].split("\n", 1)
            line = line.strip()
            if not line:
                continue

            addr = clients.get(sock, ("unknown", 0))
            sender = f"{addr[0]}:{addr[1]}"

            if line == "LIST":
                files = sorted(
                    name
                    for name in os.listdir(SERVER_FILES_DIR)
                    if os.path.isfile(os.path.join(SERVER_FILES_DIR, name))
                )
                send_line(sock, f"LIST|{','.join(files)}")

            elif line.startswith("DOWNLOAD|"):
                filename = os.path.basename(line.split("|", 1)[1].strip())
                if not filename:
                    send_line(sock, "ERROR|Filename is required")
                    continue

                file_path = os.path.join(SERVER_FILES_DIR, filename)
                if not os.path.isfile(file_path):
                    send_line(sock, f"ERROR|File not found: {filename}")
                    continue

                with open(file_path, "rb") as f:
                    content = f.read()

                encoded = base64.b64encode(content).decode()
                send_line(sock, f"DOWNLOAD|{filename}|{encoded}")

            elif line.startswith("UPLOAD|"):
                parts = line.split("|", 2)
                if len(parts) != 3:
                    send_line(sock, "ERROR|Invalid upload format")
                    continue

                filename = os.path.basename(parts[1].strip())
                content_b64 = parts[2]
                if not filename:
                    send_line(sock, "ERROR|Filename is required")
                    continue

                try:
                    content = base64.b64decode(content_b64.encode(), validate=True)
                except Exception:
                    send_line(sock, "ERROR|Invalid file content")
                    continue

                file_path = os.path.join(SERVER_FILES_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(content)

                send_line(sock, f"UPLOAD_OK|{filename}|{len(content)}")

            elif line.startswith("CHAT|"):
                message = line.split("|", 1)[1].strip()
                if not message:
                    send_line(sock, "ERROR|Message cannot be empty")
                    continue

                payload = f"CHAT|{sender}|{message}"
                dead_clients = broadcast(list(clients.keys()), payload)
                for dead in dead_clients:
                    close_client(dead, input_sockets, clients, buffers)

            else:
                send_line(sock, "ERROR|Unknown command")