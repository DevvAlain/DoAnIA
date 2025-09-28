# IoT 9-Device MQTT Simulator

## 📋 Tổng quan dự án

Dự án giả lập 9 thiết bị IoT sử dụng MQTT protocol, replay traffic từ dataset CSV thực tế. Mỗi thiết bị có IP address riêng và gửi dữ liệu telemetry theo pattern từ dataset.

### 🎯 Mục tiêu

- Giả lập 9 thiết bị IoT với traffic thực từ dataset
- Sử dụng MQTT protocol để giao tiếp
- Replay dữ liệu từ CSV files theo đúng pattern
- Infrastructure Docker để dễ deploy và test

## 🏗️ Kiến trúc dự án

```
Do An IA/
├── simulator_from_csv.py          # Simulator chính
├── feature_extract.py             # Extract features từ CSV
├── requirements.txt               # Dependencies
├── docker-compose.yml            # Docker infrastructure
├── Dockerfile                    # Container config
└── 9 file CSV dataset:
    ├── TemperatureMQTTset.csv     # 192.168.0.151
    ├── LightIntensityMQTTset.csv # 192.168.0.150
    ├── HumidityMQTTset.csv       # 192.168.0.152
    ├── MotionMQTTset.csv         # 192.168.0.154
    ├── CO-GasMQTTset.csv         # 192.168.0.155
    ├── SmokeMQTTset.csv          # 192.168.0.180
    ├── FanSpeedControllerMQTTset.csv # 192.168.0.173
    ├── DoorlockMQTTset.csv       # 192.168.0.176
    └── FansensorMQTTset.csv      # 192.168.0.178
```

## 🔧 Yêu cầu hệ thống

- Docker Desktop
- Docker Compose
- Python 3.11+ (nếu chạy trực tiếp)

## 📁 Quản lý dữ liệu

### CSV Dataset Files

- **Lưu ý**: Các file CSV dataset (~1.5GB) đã được exclude khỏi Git
- **Lý do**: File quá lớn, không phù hợp cho Git repository
- **Cách thêm**: Copy các file CSV vào thư mục dự án trước khi chạy

### Git Setup

```bash
# Clone repository
git clone <your-repo-url>
cd "Do An IA"

# Copy CSV files vào thư mục (nếu chưa có)
# TemperatureMQTTset.csv
# LightIntensityMQTTset.csv
# HumidityMQTTset.csv
# MotionMQTTset.csv
# CO-GasMQTTset.csv
# SmokeMQTTset.csv
# FanSpeedControllerMQTTset.csv
# DoorlockMQTTset.csv
# FansensorMQTTset.csv

# Chạy dự án
docker-compose up -d
```

## 🚀 Hướng dẫn chạy dự án

### Phương pháp 1: Docker (Khuyến nghị)

#### Bước 1: Kiểm tra Docker

```bash
docker --version
docker-compose --version
```

#### Bước 2: Clone/Navigate đến thư mục dự án

```bash
cd "C:\Users\Admin\Desktop\Do An IA"
```

#### Bước 3: Chạy dự án

```bash
# Build và chạy containers
docker-compose up --build -d

# Kiểm tra trạng thái
docker ps
```

#### Bước 4: Kiểm tra logs

```bash
# Xem logs simulator
docker logs mqtt-simulator

# Xem logs realtime
docker logs mqtt-simulator -f
```

#### Bước 5: Truy cập EMQX Dashboard

- URL: http://localhost:18083
- Xem kết nối MQTT và traffic realtime

### Phương pháp 2: Python trực tiếp

#### Bước 1: Cài đặt MQTT Broker

```bash
# Cài EMQX hoặc Mosquitto
# Windows: choco install mosquitto
# Hoặc tải từ: https://www.emqx.io/downloads
```

#### Bước 2: Cài dependencies

```bash
pip install -r requirements.txt
```

#### Bước 3: Chạy simulator

```bash
python simulator_from_csv.py --broker localhost --port 1883
```

## 📊 Monitoring và Test

### 1. Kiểm tra kết nối thiết bị

```bash
# Xem tất cả containers
docker ps

# Xem logs chi tiết
docker logs mqtt-simulator --tail 50
```

### 2. EMQX Dashboard

- **URL**: http://localhost:18083
- **Features**:
  - Xem clients kết nối
  - Monitor MQTT messages
  - Xem topics và subscriptions
  - Real-time traffic analysis

### 3. Test MQTT Client

```bash
# Cài MQTT client (optional)
pip install paho-mqtt

# Subscribe để test
python -c "
import paho.mqtt.client as mqtt
def on_message(client, userdata, message):
    print(f'Topic: {message.topic}, Payload: {message.payload.decode()}')
client = mqtt.Client()
client.on_message = on_message
client.connect('localhost', 1883)
client.subscribe('site/tenantA/home/+/telemetry')
client.loop_forever()
"
```

## 🔍 Chi tiết kỹ thuật

### 9 Thiết bị IoT

| Thiết bị    | IP Address    | CSV File                      | Username        | Topic                                   |
| ----------- | ------------- | ----------------------------- | --------------- | --------------------------------------- |
| Temperature | 192.168.0.151 | TemperatureMQTTset.csv        | sensor_temp     | site/tenantA/home/Temperature/telemetry |
| Light       | 192.168.0.150 | LightIntensityMQTTset.csv     | sensor_light    | site/tenantA/home/Light/telemetry       |
| Humidity    | 192.168.0.152 | HumidityMQTTset.csv           | sensor_hum      | site/tenantA/home/Humidity/telemetry    |
| Motion      | 192.168.0.154 | MotionMQTTset.csv             | sensor_motion   | site/tenantA/home/Motion/telemetry      |
| CO-Gas      | 192.168.0.155 | CO-GasMQTTset.csv             | sensor_co       | site/tenantA/home/CO-Gas/telemetry      |
| Smoke       | 192.168.0.180 | SmokeMQTTset.csv              | sensor_smoke    | site/tenantA/home/Smoke/telemetry       |
| FanSpeed    | 192.168.0.173 | FanSpeedControllerMQTTset.csv | sensor_fanspeed | site/tenantA/home/FanSpeed/telemetry    |
| DoorLock    | 192.168.0.176 | DoorlockMQTTset.csv           | sensor_door     | site/tenantA/home/DoorLock/telemetry    |
| FanSensor   | 192.168.0.178 | FansensorMQTTset.csv          | sensor_fan      | site/tenantA/home/FanSensor/telemetry   |

### Flow hoạt động

1. **Khởi tạo**: 9 threads cho 9 thiết bị
2. **Kết nối**: Mỗi thiết bị kết nối đến EMQX broker
3. **Đọc CSV**: Parse MQTT data từ CSV files
4. **Replay**: Gửi MQTT messages theo pattern từ dataset
5. **Retry**: Tự động retry khi mất kết nối

### Cấu trúc MQTT Message

```json
{
  "topic": "site/tenantA/home/{device_name}/telemetry",
  "payload": {
    "value": "extracted_from_csv_data"
  },
  "qos": 0,
  "retain": false
}
```

## 🛠️ Troubleshooting

### Lỗi thường gặp

#### 1. Connection refused

```bash
# Kiểm tra EMQX có chạy không
docker logs emqx

# Restart containers
docker-compose restart
```

#### 2. Không có data

```bash
# Kiểm tra CSV files
ls -la *.csv

# Kiểm tra logs simulator
docker logs mqtt-simulator
```

#### 3. Port conflicts

```bash
# Kiểm tra port đang sử dụng
netstat -an | findstr 1883
netstat -an | findstr 18083

# Thay đổi port trong docker-compose.yml nếu cần
```

#### 4. Topics/Subscriptions = 0

```bash
# Đây là bình thường! Lý do:
# - Topics = 0: EMQX không tự động tạo topic entries
# - Subscriptions = 0: Không có client subscribe

# Để test messages, chạy:
docker exec mqtt-simulator python -c "
import paho.mqtt.client as mqtt
import time
def on_message(client, userdata, message):
    print(f'Received: {message.topic} -> {message.payload.decode()}')
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.on_message = on_message
client.connect('emqx', 1883)
client.subscribe('site/tenantA/home/+/telemetry')
client.loop_start()
time.sleep(5)
client.loop_stop()
"
```

### Commands hữu ích

```bash
# Dừng dự án
docker-compose down

# Restart dự án
docker-compose restart

# Xem logs tất cả services
docker-compose logs

# Clean up (xóa containers và images)
docker-compose down --rmi all --volumes --remove-orphans
```

## 📈 Kết quả mong đợi

### Khi chạy thành công, bạn sẽ thấy:

1. **9 thiết bị kết nối**:

```
[Temperature] connected to emqx:1883
[Light] connected to emqx:1883
[Humidity] connected to emqx:1883
[Motion] connected to emqx:1883
[CO-Gas] connected to emqx:1883
[Smoke] connected to emqx:1883
[FanSpeed] connected to emqx:1883
[DoorLock] connected to emqx:1883
[FanSensor] connected to emqx:1883
```

2. **EMQX Dashboard** hiển thị:

   - **Connections**: 9 clients kết nối
   - **Incoming Rate**: ~59 messages/sec
   - **Topics/Subscriptions**: 0 (bình thường vì chỉ có publishers)

3. **MQTT Messages** được gửi liên tục theo pattern từ CSV:

   - JSON payload format: `{"value": "extracted_data"}`
   - Real-time data từ CSV files
   - 9 topics hoạt động: `site/tenantA/home/{device}/telemetry`

4. **Test Messages** có thể subscribe để xem:
   - Temperature: "ature125", "ature106", etc.
   - Light: "Intensity0", "Intensity1"
   - Humidity: "ty57", "ty19", etc.
   - Motion: "nt2", "nt0", "nt1"
   - CO-Gas: "280", "334", "15", etc.
   - Smoke: 42.29, 67.21, 41.35, etc.
   - FanSpeed: "eed1", "eed0"
   - DoorLock: "ock0"
   - FanSensor: 42.71, 89.05, 49.6, etc.

## 🎯 Demo cho Mentor

### 1. Khởi động dự án

```bash
docker-compose up -d
```

### 2. Mở EMQX Dashboard

- URL: http://localhost:18083
- Show: Clients, Topics, Messages

### 3. Monitor logs

```bash
docker logs mqtt-simulator -f
```

### 4. Test MQTT client

- Subscribe to topics
- Show real-time data flow

### 5. Dừng dự án

```bash
docker-compose down
```

## 📝 Kết luận

Dự án đã hoàn thành với:

- ✅ 9 thiết bị IoT giả lập
- ✅ MQTT protocol implementation
- ✅ CSV data replay
- ✅ Docker infrastructure
- ✅ Monitoring dashboard
- ✅ Retry logic và error handling

**Dự án sẵn sàng để demo và phát triển thêm!** 🚀
