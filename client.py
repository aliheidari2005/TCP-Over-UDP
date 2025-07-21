from tcp_socket import TCPSocket
from connection import Connection


def main():
    client = TCPSocket()
    client.connect(('localhost', 12000))
    print("[CLIENT] Connection established")

    # Wrap in Connection object (like accept() does)
    conn = Connection(
        socket=client,
        client_addr=client.remote_address,
        seq=client.local_seq,
        ack=client.remote_seq
    )

    # Send message to server
    message = b"Hello from client"
    print(f"[CLIENT] Sending to server: {message}")
    conn.send(message)

    # Wait for response
    while True:
        response = conn.read()
        if response:
            print(f"[CLIENT] Received from server: {response}")
            break

    conn.close()


if __name__ == "__main__":
    main()
