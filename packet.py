# import struct

# # Flag definitions
# SYN = 0x01
# ACK = 0x02
# FIN = 0x04
# RST = 0x08
# FIN_ACK = 0x06


# class Packet:
#     HEADER_FORMAT = "!HHIIBHH"  # src_port, dest_port, seq, ack, flags, window, payload_len
#     HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
#     MSS = 5  # Maximum Segment Size

#     def __init__(self, src_port, dest_port, seq_num, ack_num, flags, window_size=0, payload=b''):
#         self.src_port = src_port
#         self.dest_port = dest_port
#         self.seq_num = seq_num
#         self.ack_num = ack_num
#         self.flags = flags
#         self.window_size = window_size
#         self.payload = payload[:self.MSS]  # Enforce MSS
#         self.payload_length = len(self.payload)

#     def to_bytes(self):

#         for name, val in [
#             ("src_port", self.src_port),
#             ("dest_port", self.dest_port),
#             ("seq_num", self.seq_num),
#             ("ack_num", self.ack_num),
#             ("flags", self.flags),
#             ("window_size", self.window_size),
#             ("payload_length", self.payload_length)
#         ]:

#             if not isinstance(val, int):
#                 raise ValueError(
#                     f"{name} must be int, got {val} ({type(val)})")

#         header = struct.pack(
#             self.HEADER_FORMAT,
#             self.src_port,
#             self.dest_port,
#             self.seq_num,
#             self.ack_num,
#             self.flags,
#             self.window_size,
#             self.payload_length
#         )
#         return header + self.payload

#     @classmethod
#     def from_bytes(cls, raw_bytes):
#         header = raw_bytes[:cls.HEADER_SIZE]
#         payload = raw_bytes[cls.HEADER_SIZE:]

#         src_port, dest_port, seq_num, ack_num, flags, window_size, payload_length = struct.unpack(
#             cls.HEADER_FORMAT, header)
#         payload = payload[:payload_length]  # Trim if extra

#         return cls(src_port, dest_port, seq_num, ack_num, flags, window_size, payload)

#     def __str__(self):
#         return f"Packet(seq={self.seq_num}, ack={self.ack_num}, flags={self.flags}, len={self.payload_length})"


# if __name__ == "__main__":
#     pkt = Packet(1234, 5678, 1, 0, SYN | ACK, 512, b"Hello World")
#     data = pkt.to_bytes()
#     parsed = Packet.from_bytes(data)
#     print(parsed)

import struct

# Flag definitions
SYN = 0x01
ACK = 0x02
FIN = 0x04
RST = 0x08
FIN_ACK = 0x06


class Packet:
    HEADER_FORMAT = "!HHIIBHH"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MSS = 5

    ENCRYPTION_KEY = 10

    def __init__(self, src_port, dest_port, seq_num, ack_num, flags, window_size=0, payload=b''):
        self.src_port = src_port
        self.dest_port = dest_port
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.window_size = window_size
        self.payload = payload[:self.MSS]
        self.payload_length = len(self.payload)

    def _encrypt(self, data: bytes) -> bytes:
        """هر بایت از دیتا را با کلید جمع کرده و در مد 256 نگه می‌دارد."""
        return bytes([(b + self.ENCRYPTION_KEY) % 256 for b in data])

    def _decrypt(self, data: bytes) -> bytes:
        """هر بایت از دیتا را از کلید کم کرده و در مد 256 نگه می‌دارد."""
        return bytes([(b - self.ENCRYPTION_KEY) % 256 for b in data])

    def to_bytes(self):
        """بسته را به یک رشته بایت برای ارسال تبدیل می‌کند (با رمزگذاری)."""
        # ... (بخش validation شما بدون تغییر باقی می‌ماند) ...

        header = struct.pack(
            self.HEADER_FORMAT,
            self.src_port,
            self.dest_port,
            self.seq_num,
            self.ack_num,
            self.flags,
            self.window_size,
            self.payload_length
        )

        # --- اصلاح شد: قبل از ارسال، payload را رمزگذاری کن ---
        encrypted_payload = self._encrypt(self.payload)
        return header + encrypted_payload

    @classmethod
    def from_bytes(cls, raw_bytes):
        """یک رشته بایت را به یک آبجکت Packet تبدیل می‌کند (با رمزگشایی)."""
        header = raw_bytes[:cls.HEADER_SIZE]
        encrypted_payload_full = raw_bytes[cls.HEADER_SIZE:]

        src_port, dest_port, seq_num, ack_num, flags, window_size, payload_length = struct.unpack(
            cls.HEADER_FORMAT, header)

        # --- اصلاح شد: payload را پس از دریافت، رمزگشایی کن ---
        encrypted_payload = encrypted_payload_full[:payload_length]
        decrypted_payload = cls._decrypt(cls, encrypted_payload)

        return cls(src_port, dest_port, seq_num, ack_num, flags, window_size, decrypted_payload)

    def __str__(self):
        # نمایش payload به صورت رمزگشایی شده برای خوانایی بهتر در لاگ‌ها
        return f"Packet(seq={self.seq_num}, ack={self.ack_num}, flags={self.flags}, len={self.payload_length}, payload='{self.payload.decode('utf-8', errors='ignore')}')"
