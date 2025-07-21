from packet import Packet, SYN, ACK, FIN, FIN_ACK, RST
import threading
import time
import socket as so
import threading
import time
import math

got_fin_from_remote = threading.Event()


class Connection:

    def __init__(self, socket, client_addr, seq, ack):

        # -------
        # در تابع __init__ کلاس Connection
        # ...
        self.persist_timer_on = False
        self.last_probe_time = 0
        # ...

        # --- پارامترهای اصلی اتصال ---
        self.socket = socket
        host_ip = so.gethostbyname(client_addr[0])
        self.client_addr = (host_ip, client_addr[1])
        self.lock = threading.Lock()
        self.running = True

        # --- متغیرهای مربوط به شماره سریال‌ها ---
        self.send_base = seq
        self.next_seq = seq
        self.expected_seq = ack
        self.recv_ack = ack

        # --- بافرها ---
        self.buffer = {}      # بافر ارسال: بسته‌های ارسال شده که منتظر ACK هستند
        self.recv_buffer = {}  # بافر دریافت: بسته‌های دریافتی خارج از ترتیب

        # --- منطق داینامیک تایم‌اوت (RTT) ---
        self.estimated_rtt = 1.0
        self.dev_rtt = 0.5
        self.timeout = self.estimated_rtt + 4 * self.dev_rtt
        self.alpha = 0.125
        self.beta = 0.25
        self.is_first_rtt_sample = True

        # --- منطق کنترل جریان و ازدحام ---
        self.max_recv_buffer = 20 * 1024  # برای مثال: ۲۰ کیلوبایت
        self.cwnd = 5                     # پنجره ازدحام (Congestion Window)
        # مقدار اولیه پنجره گیرنده (Receive Window)
        self.rwnd = self.max_recv_buffer

        self.persist_timer_on = False
        self.last_probe_time = 0

        # --- متغیرهای دیگر ---
        self.duplicate_ack_count = {}
        self.fin_sent = False
        self.got_ack_for_fin = threading.Event()

        # --- راه‌اندازی Thread ها ---
        self.receiver_thread = threading.Thread(
            target=self._receiver_loop, daemon=True)
        self.sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True)

        self.retransmit_thread = threading.Thread(
            target=self._retransmit_loop, daemon=True)

        self.receiver_thread.start()
        self.sender_thread.start()
        self.retransmit_thread.start()

        # -----
        self.last_activity_time = time.monotonic()
        self.idle_timeout = 30  # ثانیه (می‌تونی به دلخواه کمتر یا بیشتر کنی)
        self.idle_checker_thread = threading.Thread(
            target=self._check_idle_timeout, daemon=True)
        self.idle_checker_thread.start()
        # -----

    def send(self, data: bytes):
        chunks = [data[i:i + Packet.MSS]
                  for i in range(0, len(data), Packet.MSS)]
        for chunk in chunks:
            while True:
                with self.lock:
                    effective_window = min(self.cwnd * Packet.MSS, self.rwnd)

                    print(
                        f"[FLOW_CONTROL] rwnd={self.rwnd}, effective_window={effective_window}")

                    window_limit = self.send_base + effective_window
                    if self.next_seq + len(chunk) <= window_limit:
                        break
                time.sleep(0.01)

            # print(
            #     f"[SEND] Creating packet: seq={self.next_seq}, ack={self.recv_ack}, chunk_len={len(chunk)}")

            with self.lock:

                bytes_in_buffer = sum(len(d)
                                      for d in self.recv_buffer.values())
                available_space = self.max_recv_buffer - bytes_in_buffer

                pkt = Packet(
                    src_port=self.socket.local_address[1],
                    dest_port=self.client_addr[1],
                    seq_num=self.next_seq,
                    ack_num=self.recv_ack,
                    flags=ACK,
                    payload=chunk,
                    # <--- همیشه اندازه پنجره را ارسال کن
                    window_size=max(0, available_space)

                )

                print(
                    f"[SEND] Buffering: seq={self.next_seq}, ack={self.recv_ack}")
                self.buffer[self.next_seq] = {
                    "packet": pkt,
                    "timestamp": 0,           # not yet sent
                    "sent_once": False,        # hasn't been sent yet
                    "retransmitted": False
                }
                self.next_seq += len(chunk)

    def _sender_loop(self):
        while self.running:
            with self.lock:
                for seq, entry in list(self.buffer.items()):
                    if seq < self.send_base:
                        continue  # already acknowledged
                    if not entry["sent_once"]:
                        # for _ in range(2):
                        self.socket.send_packet(entry["packet"])
                        self.last_activity_time = time.monotonic()

                        # time.sleep(2.5)
                        entry["timestamp"] = time.monotonic()
                        entry["sent_once"] = True
                        print(
                            f"[SENDERLOOP:] Sent for first time: seq={seq}")
            time.sleep(0.1)
# چت دو

    # کد های اصلی
    # def _retransmit_loop(self):
    #     while self.running:
    #         now = time.monotonic()
    #         with self.lock:
    #             items = list(self.buffer.items())

    #         for seq, entry in items:
    #             with self.lock:
    #                 window_limit = self.send_base + self.cwnd * Packet.MSS
    #                 if seq >= window_limit or seq < self.send_base or seq not in self.buffer:
    #                     continue

    #                 ts = entry["timestamp"]
    #                 elapsed = now - ts if ts != 0 else 0  # اگر ts==0، یعنی ارسال نشده، پس کاری نکن

    #                 # فقط اگر قبلاً فرستاده شده و timeout شده
    #                 if ts != 0 and elapsed > self.timeout:
    #                     print(
    #                         f"[RETRANSMIT] Resending, {elapsed:.3f} > {self.timeout}: seq {seq}")
    #                     entry["timestamp"] = time.monotonic()
    #                     entry["retransmitted"] = True  # <-- این خط جدید است

    #                     try:
    #                         self.socket.send_packet(entry["packet"])
    #                         self.last_activity_time = time.monotonic()

    #                     except OSError:
    #                         pass

    #         time.sleep(0.1)

    # # demenai
    # def handle_ack(self, ack_num):
    #     with self.lock:
    #         # --- بخش ۱: مدیریت ACK تکراری یا قدیمی ---
    #         if ack_num <= self.send_base:
    #             if ack_num == self.send_base and self.buffer:
    #                 # ... منطق Fast Retransmit شما (بدون تغییر) ...
    #                 self.duplicate_ack_count[ack_num] = self.duplicate_ack_count.get(
    #                     ack_num, 0) + 1
    #                 print(
    #                     f"[DUP-ACK] {ack_num} : {self.duplicate_ack_count[ack_num]}")
    #                 if self.duplicate_ack_count.get(ack_num, 0) >= 3:
    #                     print(f"[FAST RETRANSMIT] Triggered for seq {ack_num}")
    #                     if ack_num in self.buffer:
    #                         entry = self.buffer[ack_num]
    #                         entry["retransmitted"] = True
    #                         entry["timestamp"] = time.monotonic()
    #                         self.socket.send_packet(entry["packet"])
    #                         self.duplicate_ack_count[ack_num] = 0
    #                         self.last_activity_time = time.monotonic()

    #             return

    #         # --- بخش ۲: مدیریت ACK جدید (منطق کاملاً بازنویسی شده) ---

    #         # ۱. محاسبه RTT برای قدیمی‌ترین بسته تایید نشده
    #         oldest_acked_seq = self.send_base
    #         if oldest_acked_seq in self.buffer:
    #             entry = self.buffer[oldest_acked_seq]
    #             if not entry.get("retransmitted", False):
    #                 sample_rtt = time.monotonic() - entry["timestamp"]

    #                 if self.is_first_rtt_sample:
    #                     self.estimated_rtt = sample_rtt
    #                     self.dev_rtt = sample_rtt / 2
    #                     self.is_first_rtt_sample = False
    #                 else:
    #                     self.dev_rtt = (1 - self.beta) * self.dev_rtt + \
    #                         self.beta * abs(sample_rtt - self.estimated_rtt)
    #                     self.estimated_rtt = (
    #                         1 - self.alpha) * self.estimated_rtt + self.alpha * sample_rtt

    #                 self.timeout = self.estimated_rtt + 4 * self.dev_rtt
    #                 if self.timeout < 0.2:
    #                     self.timeout = 0.2
    #                 print(
    #                     f"[RTT] Sample for seq {oldest_acked_seq}={sample_rtt:.3f}, New Timeout={self.timeout:.3f}")

    #         # ۲. جلو بردن پنجره ارسال
    #         self.send_base = ack_num
    #         self.duplicate_ack_count.clear()

    #         # ۳. حذف تمام بسته‌های تایید شده از بافر
    #         keys_to_delete = [
    #             seq for seq in self.buffer if seq < self.send_base]
    #         for seq in keys_to_delete:
    #             try:
    #                 del self.buffer[seq]
    #             except KeyError:
    #                 pass

    #         print(
    #             f"[ACK] Handled new ACK {ack_num}, new send_base={self.send_base}")

    def _retransmit_loop(self):
        while self.running:
            now = time.monotonic()

            # --- بخش ۱: باز ارسال بسته‌های زمان‌بندی شده (Timeout) ---
            items_to_check = []
            with self.lock:
                items_to_check = list(self.buffer.items())

            for seq, entry in items_to_check:
                # فقط زمانی که نیاز به باز ارسال است، قفل را بگیر
                ts = entry["timestamp"]
                elapsed = now - ts if ts != 0 else 0
                if ts != 0 and elapsed > self.timeout:
                    with self.lock:
                        # دوباره چک کن تا مطمئن شوی بسته هنوز نیاز به باز ارسال دارد
                        if seq in self.buffer and seq >= self.send_base:
                            current_entry = self.buffer[seq]
                            if time.monotonic() - current_entry["timestamp"] > self.timeout:
                                print(
                                    f"[RETRANSMIT] Resending, {elapsed:.3f} > {self.timeout}: seq {seq}")
                                current_entry["timestamp"] = time.monotonic()
                                current_entry["retransmitted"] = True
                                self.last_activity_time = time.monotonic()
                                try:
                                    self.socket.send_packet(
                                        current_entry["packet"])
                                except OSError:
                                    pass

            # --- بخش ۲: کاوش پنجره صفر (Zero-Window Probe) ---
            with self.lock:
                if self.persist_timer_on and self.rwnd == 0:
                    if now - self.last_probe_time > self.timeout:
                        print(
                            "[PROBE] Zero window detected. Sending probe packet...")

                        # محاسبه فضای خالی بافر خودمان برای ارسال در بسته کاوشگر
                        bytes_in_buffer = sum(len(d)
                                              for d in self.recv_buffer.values())
                        available_space = self.max_recv_buffer - bytes_in_buffer

                        probe_pkt = Packet(
                            src_port=self.socket.local_address[1],
                            dest_port=self.client_addr[1],
                            seq_num=self.next_seq,
                            ack_num=self.recv_ack,
                            flags=ACK,
                            # ارسال وضعیت پنجره خودمان
                            window_size=max(0, available_space)
                        )

                        try:
                            self.socket.send_packet(probe_pkt)
                            self.last_activity_time = time.monotonic()
                        except OSError:
                            pass

                        self.last_probe_time = now  # ریست کردن تایمر کاوشگر

            time.sleep(0.1)

    def handle_ack(self, ack_num):
        with self.lock:
            # --- فعال/غیرفعال کردن تایمر کاوشگر بر اساس rwnd ---
            # این منطق به اینجا منتقل شد چون handle_ack فقط توسط فرستنده داده اجرا می‌شود
            if self.rwnd == 0:
                if not self.persist_timer_on:
                    self.last_probe_time = time.monotonic()
                self.persist_timer_on = True
            else:
                self.persist_timer_on = False
            # --------------------------------------------------

            # --- بخش ۱: مدیریت ACK تکراری یا قدیمی ---
            if ack_num <= self.send_base:
                if ack_num == self.send_base and self.buffer:
                    self.duplicate_ack_count[ack_num] = self.duplicate_ack_count.get(
                        ack_num, 0) + 1
                    print(
                        f"[DUP-ACK] {ack_num} : {self.duplicate_ack_count.get(ack_num, 0)}")

                    if self.duplicate_ack_count.get(ack_num, 0) >= 3:
                        print(f"[FAST RETRANSMIT] Triggered for seq {ack_num}")
                        if ack_num in self.buffer:
                            entry = self.buffer[ack_num]
                            entry["retransmitted"] = True
                            entry["timestamp"] = time.monotonic()
                            self.socket.send_packet(entry["packet"])
                            self.last_activity_time = time.monotonic()
                            self.duplicate_ack_count[ack_num] = 0
                            self.cwnd = max(1, self.cwnd // 2)

                return

            # --- بخش ۲: مدیریت ACK جدید ---
            oldest_acked_seq = self.send_base
            if oldest_acked_seq in self.buffer:
                entry = self.buffer[oldest_acked_seq]
                if not entry.get("retransmitted", False):
                    sample_rtt = time.monotonic() - entry["timestamp"]
                    if self.is_first_rtt_sample:
                        self.estimated_rtt = sample_rtt
                        self.dev_rtt = sample_rtt / 2
                        self.is_first_rtt_sample = False
                    else:
                        self.dev_rtt = (1 - self.beta) * self.dev_rtt + \
                            self.beta * abs(sample_rtt - self.estimated_rtt)
                        self.estimated_rtt = (
                            1 - self.alpha) * self.estimated_rtt + self.alpha * sample_rtt

                    self.timeout = self.estimated_rtt + 4 * self.dev_rtt
                    if self.timeout < 0.2:
                        self.timeout = 0.2
                    print(
                        f"[RTT] Sample for seq {oldest_acked_seq}={sample_rtt:.3f}, New Timeout={self.timeout:.3f}")

            self.send_base = ack_num
            self.duplicate_ack_count.clear()

            keys_to_delete = [
                seq for seq in self.buffer if seq < self.send_base]
            for seq in keys_to_delete:
                try:
                    del self.buffer[seq]
                except KeyError:
                    pass

            print(
                f"[ACK] Handled new ACK {ack_num}, new send_base={self.send_base}")

    def _receiver_loop(self):
        while self.running:
            try:
                pkt, addr = self.socket.receive_packet()
                if pkt:
                    self.rwnd = pkt.window_size
                    self.last_activity_time = time.monotonic()

                    if self.rwnd == 0:
                        self.persist_timer_on = True
                        self.last_probe_time = time.monotonic()  # تایمر را از همین الان شروع کن
                    else:
                        self.persist_timer_on = False

                    # print(pkt.ack_num)

            except OSError:
                break  # ✅ سوکت بسته شده

            # print(self.expected_seq)
            if not pkt or addr != self.client_addr:
                continue

                # print(f"[RECEIVER LOOP] Received: {pkt}")
            # if self.expected_seq is None:
            #     self.expected_seq = pkt.seq_num

            # print(self.expected_seq, 125)

            time.sleep(0.5)

            if len(pkt.payload) > 0:
                seq = pkt.seq_num
                with self.lock:

                    print(
                        f"[RECV] Received packet: SEQ={seq}, ACK={pkt.ack_num}, FLAGS={pkt.flags}, LEN={len(pkt.payload)}")

                    if seq < self.expected_seq:
                        print(
                            f"[RECV] Duplicate packet (SEQ={seq}), already delivered. Ignoring.")

                    elif seq == self.expected_seq:
                        # فقط بسته‌ای که دقیقا انتظارش را داریم ذخیره کن
                        self.recv_buffer[seq] = pkt.payload
                        while self.expected_seq in self.recv_buffer:
                            data = self.recv_buffer.pop(self.expected_seq)
                            print("[DELIVER] Accepting in-order data")
                            self.expected_seq += len(data)
                            # self.recv_data.extend(data)

                            print("--- SERVER IS SLOWLY PROCESSING DATA ---")
                            time.sleep(0.5)

                    elif seq in self.recv_buffer:
                        # بسته تکراری، از قبل داریمش
                        print(f"[RECV] Duplicate packet: SEQ={seq}")

                    else:
                        # بسته out-of-order دریافت شده
                        print(
                            f"[RECV] Out-of-order packet: SEQ={seq}, buffering for future")
                        # optionally: می‌تونی این خط رو حذف کنی اگه نخوای buffer out-of-order داشته باشی
                        self.recv_buffer[seq] = pkt.payload

                bytes_in_buffer = sum(len(data)
                                      for data in self.recv_buffer.values())
                available_space = self.max_recv_buffer - bytes_in_buffer
                if available_space < 0:
                    available_space = 0

                # ارسال ACK با مقدار فعلی expected_seq
                ack_pkt = Packet(
                    src_port=self.socket.local_address[1],
                    dest_port=self.client_addr[1],
                    seq_num=self.next_seq,
                    ack_num=self.expected_seq,
                    flags=ACK,
                    window_size=available_space
                )
                self.socket.send_packet(ack_pkt)
                print(
                    f"[RECEIVER LOOP] Sent ACK={self.expected_seq} with Window={available_space}")
                # print(f"time: {time.time()}")

            elif pkt.flags & FIN:
                print("[RECEIVER LOOP] FIN received")
                fin_ack = Packet(
                    src_port=self.socket.local_address[1],
                    dest_port=self.client_addr[1],
                    seq_num=self.next_seq,
                    ack_num=pkt.seq_num + 1,
                    flags=6
                )
                self.socket.send_packet(fin_ack)
                print("[RECEIVER LOOP] Sent FIN|ACK")
                # self.got_fin_from_remote.set()

            elif pkt.flags & ACK:

                print(f"[RECV] Got ACK={pkt.ack_num} from remote")
                print(f"[RECEIVER LOOP] Handling ACK {pkt.ack_num}")
                print(self.fin_sent, self.next_seq)
                if not self.fin_sent and pkt.ack_num == self.next_seq:
                    print("[RECEIVER LOOP] Received ACK for our FIN.")
                    self.got_ack_for_fin.set()

                self.handle_ack(pkt.ack_num)

            elif pkt.flags & RST:
                print(
                    f"[RST] Received RST from {addr}. Connection should be closed.")
                self.close()
                return

    def _check_idle_timeout(self):
        while self.running:
            time.sleep(5)
            if time.monotonic() - self.last_activity_time > self.idle_timeout:
                print(
                    f"[IDLE TIMEOUT] No activity for {self.idle_timeout}s, closing connection.")
                self.close()
                break

    def read(self):
        """Non-blocking: returns assembled in-order data from recv_buffer if available."""
        with self.lock:
            collected = []
            while self.expected_seq in self.recv_buffer:
                data = self.recv_buffer.pop(self.expected_seq - 1)
                collected.append(data)
                self.expected_seq += len(data)

            if collected:
                return b''.join(collected)
            else:
                return None  # Nothing available

    def close(self):
        # time.sleep(0.3)  # کمی تأخیر قبل از بستن، اختیاری
        print("[CLOSE] Sending FIN...")

        fin_pkt = Packet(
            src_port=self.socket.local_address[1],
            dest_port=self.client_addr[1],
            seq_num=self.next_seq,
            ack_num=self.expected_seq,
            flags=FIN
        )
        self.socket.send_packet(fin_pkt)
        self.fin_sent = True
        self.next_seq += 1  # فقط بعد از ارسال FIN افزایش بده

        # ⏳ منتظر دریافت FIN یا FIN+ACK از طرف مقابل
        fin_or_fin_ack_received = got_fin_from_remote.wait(timeout=5)
        if not fin_or_fin_ack_received:
            print("[CLOSE] Warning: FIN or FIN|ACK from remote not received")
        else:
            print("[CLOSE] FIN or FIN|ACK received from remote")

        # 🎯 اگر دریافت شد، ACK نهایی را بفرست
        final_ack = Packet(
            src_port=self.socket.local_address[1],
            dest_port=self.client_addr[1],
            seq_num=self.next_seq,
            ack_num=self.expected_seq,
            flags=ACK
        )
        self.socket.send_packet(final_ack)
        print("[CLOSE] Sent final ACK")

        # 🛑 پایان کامل
        self.running = False  # 🔴 Tell threads to stop first
        time.sleep(0.3)

        # Wait for threads
        self.receiver_thread.join(timeout=1)
        self.sender_thread.join(timeout=1)
        self.retransmit_thread.join(timeout=1)

        # Close the underlying socket
        try:
            self.socket.close()
        except OSError:
            pass

        print("[CLOSE] Connection closed gracefully.")
