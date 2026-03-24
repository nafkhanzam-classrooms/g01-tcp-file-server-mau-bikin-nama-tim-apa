import base64
import logging
import os
import socket
import threading

logging.basicConfig(level=logging.INFO)

HOST = 'localhost'
PORT = 5000

BUFFER_SIZE = 4096

sock = None
running = True


def send_line(sock_obj, line):
    sock_obj.sendall((line + "\n").encode())


def receiver_loop(sock_obj):
    global running
    buffer = ""

    while running:
        try:
            data = sock_obj.recv(BUFFER_SIZE)
        except OSError:
            break

        if not data:
            logging.info("Server disconnected")
            running = False
            break

        buffer += data.decode(errors="replace")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            if line.startswith("CHAT|"):
                parts = line.split("|", 2)
                if len(parts) != 3:
                    logging.info(f"Invalid chat response: {line}")
                    continue
                sender = parts[1]
                message = parts[2]
                logging.info(f"[{sender}] {message}")

            elif line.startswith("LIST|"):
                files_text = line.split("|", 1)[1]
                files = [f for f in files_text.split(",") if f]
                if files:
                    logging.info("Server files:")
                    for name in files:
                        logging.info(f"- {name}")
                else:
                    logging.info("Server files: (empty)")

            elif line.startswith("UPLOAD_OK|"):
                parts = line.split("|", 2)
                if len(parts) != 3:
                    logging.info(f"Invalid upload response: {line}")
                    continue
                filename = parts[1]
                size = parts[2]
                logging.info(f"Upload success: {filename} ({size} bytes)")

            elif line.startswith("DOWNLOAD|"):
                parts = line.split("|", 2)
                if len(parts) != 3:
                    logging.info(f"Invalid download response: {line}")
                    continue
                filename = parts[1] or "downloaded_file"
                content_b64 = parts[2]
                try:
                    content = base64.b64decode(content_b64.encode(), validate=True)
                except Exception:
                    logging.info(f"Failed to decode downloaded file: {filename}")
                    continue

                save_name = f"downloaded_{filename}"
                with open(save_name, "wb") as f:
                    f.write(content)
                logging.info(f"Downloaded file saved as: {save_name}")

            elif line.startswith("SYSTEM|"):
                logging.info(line.split("|", 1)[1])

            elif line.startswith("ERROR|"):
                logging.info(f"Server error: {line.split('|', 1)[1]}")

            else:
                logging.info(f"Server response: {line}")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = (HOST, PORT)
    logging.info(f"connecting to {server_address}")
    sock.connect(server_address)

    receiver_thread = threading.Thread(target=receiver_loop, args=(sock,), daemon=True)
    receiver_thread.start()

    while running:
        message = input(
            "Message or command (/list, /upload <file>, /download <file>, exit): "
        ).strip()

        if message.lower() == 'exit':
            logging.info("Client stopped by user")
            running = False
            break

        if not message:
            logging.info("Message cannot be empty")
            continue

        if message == "/list":
            send_line(sock, "LIST")
            continue

        if message.startswith("/upload "):
            filename = message[len("/upload "):].strip()
            if not filename:
                logging.info("Usage: /upload <filename>")
                continue
            if not os.path.isfile(filename):
                logging.info(f"File not found: {filename}")
                continue

            with open(filename, "rb") as f:
                content = f.read()

            send_line(
                sock,
                "UPLOAD|"
                + os.path.basename(filename)
                + "|"
                + base64.b64encode(content).decode(),
            )
            continue

        if message.startswith("/download "):
            filename = message[len("/download "):].strip()
            if not filename:
                logging.info("Usage: /download <filename>")
                continue

            send_line(sock, f"DOWNLOAD|{filename}")
            continue

        send_line(sock, f"CHAT|{message}")

except Exception as e:
    logging.error(f"Error: {e}")

finally:
    running = False
    if sock:
        sock.close()
        logging.info("Socket closed")