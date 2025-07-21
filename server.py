from server_socket import ServerSocket


def main():
    server = ServerSocket()
    server.bind(('localhost', 12000))
    server.listen(backlog=1)

    print("[SERVER] Waiting for client...")
    conn = server.accept()
    print("[SERVER] Client connected.")

    # Receive message from client
    while True:
        data = conn.read()
        if data:
            print(f"[SERVER] Received from client: {data}")
            break

    # Send response back to client
    response = b"Hello from server"
    print(f"[SERVER] Sending to client: {response}")
    conn.send(response)

    # Optionally wait to receive client ACK or FIN here

    # Close connection gracefully
    conn.close()
    server.close()


if __name__ == "__main__":
    main()
