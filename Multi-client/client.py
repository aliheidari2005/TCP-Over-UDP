import socket
import time


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = ("127.0.0.1", 9999)

    # مرحله 1: ارسال SYN
    print("[CLIENT] Sending SYN")
    client_socket.sendto("SYN".encode(), server_addr)

    # مرحله 2: دریافت SYN-ACK
    data, _ = client_socket.recvfrom(1024)
    print(f"[CLIENT] Received {data.decode()}")

    # مرحله 3: ارسال ACK
    print("[CLIENT] Sending ACK")
    client_socket.sendto("ACK".encode(), server_addr)

    # حالا می‌توانیم پیام بفرستیم
    while True:
        msg = input("Enter message (or 'exit'): ")
        client_socket.sendto(msg.encode(), server_addr)
        if msg == "exit":
            break


if __name__ == "__main__":
    main()
