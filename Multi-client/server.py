import socket
import threading

connections = {}


def handle_client(addr, server_socket):
    print(f"[HANDSHAKE] Starting handshake with {addr}")

    # مرحله 2: دریافت SYN از کلاینت
    data, _ = server_socket.recvfrom(1024)
    if data.decode() != "SYN":
        return

    print(f"[HANDSHAKE] Received SYN from {addr}")
    server_socket.sendto("SYN-ACK".encode(), addr)

    # مرحله 3: دریافت ACK نهایی
    data, _ = server_socket.recvfrom(1024)
    if data.decode() == "ACK":
        print(f"[HANDSHAKE] Connection established with {addr}")
        connections[addr] = True

    # حالا پیام‌ها را دریافت کن
    while True:
        try:
            data, _ = server_socket.recvfrom(1024)
            if data.decode() == "exit":
                print(f"[DISCONNECT] {addr} disconnected.")
                break
            print(f"[{addr}] {data.decode()}")
        except:
            break


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("0.0.0.0", 9999))
    print("[SERVER] UDP socket bound on port 9999...")

    while True:
        data, addr = server_socket.recvfrom(1024)
        if addr not in connections:
            threading.Thread(target=handle_client, args=(
                addr, server_socket)).start()


if __name__ == "__main__":
    main()
