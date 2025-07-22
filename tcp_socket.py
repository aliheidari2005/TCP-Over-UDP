import socket
import random
from packet import Packet, SYN, ACK, FIN, RST
from connection import Connection, got_fin_from_remote
import time
import select
import threading


class TCPSocket:

    def __init__(self):
        self.local_seq = 0
        self.remote_seq = 0
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # ✅ Add this
        self.local_address = None
        self.remote_address = None
        self.is_bound = False
        self.is_connected = False
        self.timeout = 2  # seconds
        self.a = 1

    def bind(self, address):
        print(address)
        self.udp_socket.bind(address)
        self.local_address = address
        self.is_bound = True
        print(f"[BIND] Bound to {address}")

    def send(self, data: bytes):
        packet = Packet(
            src_port=self.local_address[1],
            dest_port=self.remote_address[1],
            seq_num=random.randint(1000, 5000),
            ack_num=0,
            flags=ACK,
            payload=data
        )
        self.send_packet(packet)

    def send_packet(self, packet: Packet):
        if self.remote_address is None:
            raise Exception("Remote address not set for sending")

        data = packet.to_bytes()
        self.udp_socket.sendto(data, self.remote_address)

    def receive_packet(self):
        try:
            data, addr = self.udp_socket.recvfrom(2048)
            packet = Packet.from_bytes(data)

            # if packet:
            #     print(f"{packet.seq_num} client:")

            if self.a == 1 and len(packet.payload) > 0:
                print("delete")
                self.a += 1
                return None, None
            if packet.flags == 6:
                print("[receive_packet] FIN_ACK received")
                got_fin_from_remote.set()
                return None, None
            # print(packet.ack_num)
            # print("152")
            # if packet.payload:
            #     print(packet.payload)
            return packet, addr

        except OSError as e:
            return None, None

    def close(self):
        self.udp_socket.close()
        print("[CLOSE] Socket closed")

    def connect(self, address):
        print(f"[CONNECT] Connecting to {address}")
        self.remote_address = address

        if not self.local_address:
            port = random.randint(30000, 60000)
            self.bind(('localhost', port))

        self_seq = random.randint(1000, 5000)

        # Step 1: Send SYN
        syn_packet = Packet(
            src_port=self.local_address[1],
            dest_port=address[1],
            seq_num=self_seq,
            ack_num=0,
            flags=SYN
        )

        print(f"[Send] SYN from [Client] to [Server] :")
        self.send_packet(syn_packet)

        # Step 2: Wait for SYN-ACK
        for _ in range(5):
            pkt, addr = self.receive_packet()
            if pkt and pkt.flags & SYN and pkt.flags & ACK and pkt.ack_num == self_seq + 1:
                print(f"[CONNECT] Received SYN-ACK from {addr}")

                # Step 3: Send final ACK
                ack_packet = Packet(
                    src_port=self.local_address[1],
                    dest_port=address[1],
                    seq_num=pkt.ack_num,
                    ack_num=pkt.seq_num + 1,
                    flags=ACK
                )

                print("[Send] final Ack from [Client] to [Server]:")
                self.send_packet(ack_packet)

                self.local_seq = self_seq + 1
                self.remote_seq = pkt.seq_num + 1
                self.is_connected = True

                # ✅ Create and assign connection object here
                self.connection = Connection(
                    socket=self,
                    client_addr=address,
                    seq=pkt.ack_num,
                    ack=pkt.seq_num + 1,
                )
                print("[CONNECT] Connection established")
                return

        raise Exception(
            "[CONNECT] Connection failed: No valid SYN-ACK received")
