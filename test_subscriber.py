import paho.mqtt.client as mqtt
import json
import argparse
from datetime import datetime

class MQTTSubscriber:
    def __init__(self, broker, port, topics):
        self.broker = broker
        self.port = port
        self.topics = topics if isinstance(topics, list) else [topics]
        self.client = mqtt.Client(client_id="test_subscriber_001")
        self.message_count = 0
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to {self.broker}:{self.port}")
            print(f"📡 Subscribing to {len(self.topics)} topics...")
            
            for topic in self.topics:
                result, mid = client.subscribe(topic, qos=0)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    print(f"   ✓ Subscribed to: {topic}")
                else:
                    print(f"   ❌ Failed to subscribe to: {topic}")
            print("-" * 80)
        else:
            print(f"❌ Connection failed with code: {rc}")
    
    def on_message(self, client, userdata, msg):
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        topic = msg.topic
        
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            payload_str = json.dumps(payload, indent=2) if len(str(payload)) > 100 else str(payload)
        except:
            payload_str = msg.payload.decode('utf-8', errors='ignore')
        
        print(f"[{timestamp}] #{self.message_count}")
        print(f"📍 Topic: {topic}")
        print(f"📦 Payload: {payload_str}")
        print(f"📏 Size: {len(msg.payload)} bytes")
        print("-" * 80)
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"⚠️  Unexpected disconnection: {rc}")
        else:
            print("👋 Disconnected gracefully")
    
    def start(self):
        print(f"🚀 Starting MQTT Subscriber...")
        print(f"🎯 Broker: {self.broker}:{self.port}")
        print(f"📋 Topics: {', '.join(self.topics)}")
        print("=" * 80)
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping subscriber... (received {self.message_count} messages)")
            self.client.disconnect()
        except Exception as e:
            print(f"❌ Connection error: {e}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Subscriber for Testing")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    
    parser.add_argument("--topics", nargs="+", help="Specific topics to subscribe to")
    parser.add_argument("--all-zones", action="store_true", help="Subscribe to all zone topics")
    parser.add_argument("--zone", type=int, help="Subscribe to specific zone (1-5)")
    parser.add_argument("--device-type", help="Subscribe to specific device type")
    
    args = parser.parse_args()
    
    if args.topics:
        topics = args.topics
    elif args.all_zones:
        topics = ["site/tenantA/+/+/+/telemetry", "site/+/+/+/+/+/telemetry"]
    elif args.zone:
        topics = [f"site/tenantA/zone{args.zone}/+/+/telemetry"]
    elif args.device_type:
        topics = [f"site/tenantA/+/{args.device_type}/+/telemetry"]
    else:
        topics = [
            "site/tenantA/zone1/temperature/+/telemetry",
            "site/tenantA/zone1/humidity/+/telemetry", 
            "site/tenantA/zone2/co2/+/telemetry",
            "site/tenantA/zone3/vibration/+/telemetry",
            "site/tenantA/zone1/smoke/+/telemetry",
            "site/tenantA/zone4/airquality/+/telemetry",
            "site/tenantA/zone2/light/+/telemetry",
            "site/tenantA/zone2/sound/+/telemetry",
            "site/tenantA/zone5/waterlevel/+/telemetry"
        ]
    
    subscriber = MQTTSubscriber(args.broker, args.port, topics)
    subscriber.start()

if __name__ == "__main__":
    main()
