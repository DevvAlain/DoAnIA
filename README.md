# 🏭 IoT MQTT Security Research Platform

Dự án nghiên cứu bảo mật MQTT IoT bao gồm:

- 🔄 **Data Pipeline**: Xử lý và chuẩn hóa dữ liệu MQTT từ CSV
- 📡 **IoT Simulators**: Mô phỏng **19 thiết bị IoT** với payload chuẩn từ canonical dataset
- ⚔️ **Attack Scripts**: 9 kịch bản tấn công MQTT để kiểm tra bảo mật
- 🔬 **Analysis Tools**: Trích xuất đặc trưng và phân tích dữ liệu
- ✨ **Production Ready**: Code đã được optimize với flow chuẩn
- 🗂️ **Unified Data Source**: Tất cả simulator đọc từ canonical_dataset.csv (4.0M records)

## 📁 Cấu trúc dự án

```
Do An IA/
├── 📊 Data Processing Pipeline
│   ├── datasets/                     # 19 dataset CSV từ Edge-IIoT + Gotham + Original
│   ├── build_canonical_dataset.py    # Chuẩn hóa CSV về schema chuẩn
│   ├── canonical_dataset.csv         # Dataset đã chuẩn hóa (4.0M records)
│   ├── features_canonical_dataset.csv # Features đã trích xuất
│   └── feature_extract.py            # Trích xuất đặc trưng cho ML
│
├── 📡 Production Simulation Flow
│   ├── canonical_simulator.py        # Main simulator - 19 devices từ canonical dataset
│   ├── camera_mqtt_simulator.py      # 🎥 Camera IoT simulator (synthetic data)
│   ├── test_camera_simulator.py      # 🧪 Simple camera test
│   ├── camera_mqtt_subscriber.py     # 👂 Camera message listener
│   ├── camera_demo.py                # 🎬 Camera demo runner
│   ├── mqtt_traffic_collector.py     # EMQX → Traffic logging
│   ├── test_subscriber.py            # Test và verify simulator output
│   └── run_complete_flow.py          # End-to-end automation
│
├── 🛡️ Security Detection Pipeline
│   ├── security_detector.py          # Rule-based + Anomaly detection
│   ├── test_attack_flows.py          # Attack compliance testing
│   └── security_alerts.csv           # Real-time security alerts
│
├── ⚔️ Attack Scripts (9 kịch bản)
│   ├── script_flood.py              # Message flooding attack
│   ├── script_wildcard.py           # Wildcard subscription abuse
│   ├── script_bruteforce.py         # Topic brute-force attack
│   ├── script_payload_anomaly.py    # Payload anomaly attack
│   ├── script_retain_qos.py         # Retain/QoS abuse attack
│   ├── script_topic_enumeration.py  # Topic enumeration attack
│   ├── script_duplicate_id.py       # Duplicate client ID attack
│   ├── script_reconnect.py          # Reconnect storm attack
│   ├── script_qos2_abuse.py         # QoS 2 abuse attack
│   └── demo_all_attacks.py          # Demo tất cả attacks
│
├── 🐳 Deployment & Infrastructure
│   ├── docker-compose.yml           # EMQX broker + services
│   ├── Dockerfile                   # Container image cho canonical simulator
│   └── requirements.txt             # Python dependencies
│
└── 📄 Documentation
    ├── README.md                     # Main documentation
    ├── Comprehensive_Research_Documentation.md # Academic documentation
    ├── Huong_dan_demo_IoT_MQTT.docx  # Demo guide (Vietnamese)
    └── IoT_MQTT_Security_Research_Comprehensive.docx # Research report
```

## 🚀 Quick Start - Complete Security Flow

### ✨ NEW: End-to-End Security Pipeline (Recommended)

Chạy complete flow theo architecture diagram trong 1 lệnh:

```bash
# Complete security pipeline: Dataset → Canonical → MQTT → Detection → Alerts
python run_complete_flow.py --duration 180

# Flow sẽ tự động:
# 1. 📊 Prepare canonical dataset
# 2. 🐳 Start EMQX broker
# 3. 📡 Start traffic collection
# 4. 🎯 Start canonical simulator
# 5. ⏱️ Run simulation (180s)
# 6. 🔬 Extract features
# 7. 🛡️ Run security detection
# 8. 📋 Generate security report
```

## Yêu cầu

- Python 3.12+ (recommend)
- Docker Desktop + Docker Compose
- Bộ dataset CSV (19 files): Edge-IIoT, Gotham City, Original 9 devices

### 1. Setup Environment

```bash
# Tạo và kích hoạt virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Manual Step-by-Step Flow (Advanced)

#### 📊 Step 1: Data Processing Pipeline

```bash
# Chuẩn hóa dataset từ CSV
python build_canonical_dataset.py --pattern "*MQTTset.csv" --output canonical_dataset.csv

# Trích xuất đặc trưng
python feature_extract.py canonical_dataset.csv --out features_canonical_dataset.csv
```

#### 🐳 Step 2: Infrastructure Setup

```bash
# Start EMQX broker stack
docker-compose up -d

# Verify broker status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

#### 📡 Step 3: Canonical Simulation Flow (19 Devices)

```bash
# Terminal 1: Start traffic collection
python mqtt_traffic_collector.py --broker localhost --log-file traffic_log.csv

# Terminal 2: Start canonical simulator with 19 devices
python canonical_simulator.py --broker localhost --duration 0

# Terminal 3: Monitor traffic (optional)
python test_subscriber.py --broker localhost --all-zones
```

#### 🎥 Step 3.1: Camera Simulation (Alternative/Additional)

```bash
# Quick camera test
python test_camera_simulator.py

# Full camera demo (interactive)
python camera_demo.py

# Manual camera simulation
# Terminal 1: Start camera subscriber
python camera_mqtt_subscriber.py --broker localhost

# Terminal 2: Start camera simulator (5 cameras for 120 seconds)
python camera_mqtt_simulator.py --cameras 5 --duration 120 --broker localhost
```

#### 🛡️ Step 4: Security Detection

```bash
# Stop traffic generation (Ctrl+C on simulators)

# Extract features from collected traffic
python feature_extract.py traffic_log.csv --out traffic_features.csv

# Run security detection
python security_detector.py --features traffic_features.csv --alerts security_alerts.csv
```

## 📡 IoT Devices & Payload Format

### 🌡️ Supported Devices (19 Total)

Canonical simulator hỗ trợ 19 loại thiết bị IoT từ 3 nguồn dataset:

#### **Original Devices (9)**

| Device          | Topic Pattern                                   | Source Dataset                |
| --------------- | ----------------------------------------------- | ----------------------------- |
| **Temperature** | `site/canonical/temperature/device_*/telemetry` | TemperatureMQTTset.csv        |
| **Humidity**    | `site/canonical/humidity/device_*/telemetry`    | HumidityMQTTset.csv           |
| **CO2**         | `site/canonical/co2/device_*/telemetry`         | CO-GasMQTTset.csv             |
| **Light**       | `site/canonical/light/device_*/telemetry`       | LightIntensityMQTTset.csv     |
| **Motion**      | `site/canonical/motion/device_*/telemetry`      | MotionMQTTset.csv             |
| **Smoke**       | `site/canonical/smoke/device_*/telemetry`       | SmokeMQTTset.csv              |
| **Fan**         | `site/canonical/fan/device_*/telemetry`         | FanSensorMQTTset.csv          |
| **Door**        | `site/canonical/door/device_*/telemetry`        | DoorlockMQTTset.csv           |
| **Vibration**   | `vibration/cooler-iotsim-cooler-motor-1`        | FanSpeedControllerMQTTset.csv |

#### **Edge-IIoT Devices (6)**

| Device             | Topic Pattern                                      | Source Dataset                   |
| ------------------ | -------------------------------------------------- | -------------------------------- |
| **DistanceSensor** | `site/canonical/distancesensor/device_*/telemetry` | Edge-IIoTset_distance_sensor.csv |
| **FlameSensor**    | `site/canonical/flamesensor/device_*/telemetry`    | Edge-IIoTset_flame_sensor.csv    |
| **PhLevelSensor**  | `site/canonical/phlevelsensor/device_*/telemetry`  | Edge-IIoTset_PhLv.csv            |
| **SoilMoisture**   | `site/canonical/soilmoisture/device_*/telemetry`   | Edge-IIoTset_soil_moisture.csv   |
| **SoundSensor**    | `site/canonical/soundsensor/device_*/telemetry`    | Edge-IIoTset_sound_sensors.csv   |
| **WaterLevel**     | `site/canonical/waterlevel/device_*/telemetry`     | Edge-IIoTset_WaterLV.csv         |

#### **Gotham City Devices (4)**

| Device                    | Topic Pattern                                   | Source Dataset                   |
| ------------------------- | ----------------------------------------------- | -------------------------------- |
| **AirQuality**            | `city/air/sensor-iotsim-air-quality-1`          | AirQualityMQTTset.csv            |
| **CoolerMotor**           | `vibration/cooler-iotsim-cooler-motor-1`        | CoolerMotorMQTTset.csv           |
| **HydraulicSystem**       | `hydraulic/rig-iotsim-hydraulic-system-1`       | HydraulicSystemMQTTset.csv       |
| **PredictiveMaintenance** | `maintenance/iotsim-predictive-maintenance-1/*` | PredictiveMaintenanceMQTTset.csv |

#### **Camera Devices (Synthetic Data)**

| Device Type  | Topic Pattern                                   | Features                         |
| ------------ | ----------------------------------------------- | -------------------------------- |
| **Camera**   | `surveillance/{zone}/camera/{camera_id}/status` | 📊 Health, temperature, CPU, RAM |
| **Motion**   | `surveillance/{zone}/camera/{camera_id}/motion` | 🚶 Motion detection, confidence  |
| **Security** | `security/{zone}/camera/{camera_id}/event`      | 🚨 Person/face/vehicle detection |
| **System**   | `system/{zone}/camera/{camera_id}/event`        | 🔧 Config changes, maintenance   |
| **Stream**   | `surveillance/{zone}/camera/{camera_id}/stream` | 📹 FPS, bitrate, quality score   |

**Camera Zones**: `entrance`, `lobby`, `parking`, `warehouse`, `office`, `cafeteria`, `server_room`

### 🎯 Payload Format

#### Canonical Simulator (19 Devices từ Dataset)

Canonical simulator sử dụng payload thực từ packet capture:

```json
{
  "device_type": "Temperature",
  "canonical_source": "dataset_canonical",
  "raw_payload": "24.07 75.32",
  "simulator_timestamp": "2025-10-02T13:04:12"
}
```

#### Camera Simulator (Synthetic Data)

Camera simulator tạo payload synthetic chuyên biệt:

```json
{
  "device_type": "Camera",
  "event_type": "motion_detected",
  "camera_id": "cam_001",
  "zone": "entrance",
  "timestamp": "2025-10-03T10:15:30.123Z",
  "confidence": 0.87,
  "motion_area_percent": 12.5,
  "bounding_boxes": [
    { "x": 450, "y": 200, "width": 120, "height": 180, "confidence": 0.92 }
  ],
  "alert_level": "medium"
}
```

### ⚡ Usage Examples

```bash
# Chạy canonical simulator với 19 devices
python canonical_simulator.py --broker localhost --duration 0

# Chạy với thời gian giới hạn (300 giây)
python canonical_simulator.py --broker localhost --duration 300

# Chạy với tùy chỉnh publish interval
python canonical_simulator.py --broker localhost --publish-interval 5.0

# Subscribe specific patterns
python test_subscriber.py --pattern "site/canonical/temperature/+/telemetry"
python test_subscriber.py --pattern "city/air/+"
python test_subscriber.py --pattern "vibration/+"
```

# Subscribe specific device type

python test_subscriber.py --device-type temperature

````

Các tham số quan trọng:

- `--pattern`: chọn các file CSV cần gộp (có thể đổi thành `*.csv` nếu thư mục chỉ chứa dữ liệu IoT).
- `--protocols`: lọc theo danh sách giao thức IoT cho phép (mặc định đã gồm MQTT/MQTTS và nhiều giao thức IIoT phổ biến).

4. Trích xuất đặc trưng phục vụ phân tích/ML.

   ```bash
   python feature_extract.py canonical_dataset.csv --out features_canonical_dataset.csv
````

File đầu ra giữ lại các trường telemetry quan trọng (`timestamp`, `client_id`, QoS, thời gian giữa hai gói, độ dài payload, nhãn,...).

5. Phát lại dữ liệu lên broker bằng canonical simulator.

   ```bash
   python canonical_simulator.py --broker localhost --port 1883 --duration 0
   ```

   Simulator sẽ publish 19 device types lên các topic pattern khác nhau với payload từ canonical dataset.

## 🐳 Docker Deployment

### EMQX + Simulator Stack

```bash
# Build và khởi động full stack
docker-compose up --build -d

# Kiểm tra containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Theo dõi logs
docker logs -f mqtt-simulator

# EMQX Dashboard: http://localhost:18083 (admin/public)

# Dừng stack
docker-compose down
```

## 🔧 Troubleshooting

### Common Issues

**🚨 Simulator không có 19 devices**

```bash
# Problem: Chỉ thấy 9 devices thay vì 19
# Solution: Check canonical_dataset.csv có đầy đủ 19 device types

python build_canonical_dataset.py datasets/ --output canonical_dataset.csv --force
python canonical_simulator.py --broker localhost  # Sẽ hiện 19 devices
```

**🚨 EMQX Dashboard hiển thị 21 connections thay vì 19**

```bash
# Problem: Dashboard đếm tất cả connections (bao gồm system/admin connections)
# Solution: 19 device connections + 2 system connections = 21 total (bình thường)
# Check EMQX dashboard: http://localhost:18083 (admin/public)
```

**🚨 Connection refused**

```bash
# Đảm bảo MQTT broker đang chạy
mosquitto -p 1883 -v

# Hoặc Docker
docker run -it -p 1883:1883 eclipse-mosquitto:latest
```

**🚨 Attack scripts không hoạt động**

```bash
# Check broker connectivity trước
python test_subscriber.py --broker localhost

# Kiểm tra firewall/antivirus blocking connections
```

**🚨 Dataset processing errors**

```bash
# Đảm bảo datasets/ folder có đầy đủ 19 CSV files
# Edge-IIoT: 6 files, Gotham: 4 files, Original: 9 files
python build_canonical_dataset.py datasets/ --output canonical_dataset.csv --force
```

## Chi tiết xử lý dữ liệu

### Schema chuẩn

| Cột                 | Mô tả                                                |
| ------------------- | ---------------------------------------------------- |
| `timestamp`         | Dấu thời gian ISO-8601 (UTC) cho từng gói tin        |
| `src_ip`/`src_port` | IP/port nguồn                                        |
| `dst_ip`/`dst_port` | IP/port đích (broker 1883/8883)                      |
| `client_id`         | Định danh thiết bị (hợp nhất client_id/device_id)    |
| `topic`             | Topic publish                                        |
| `topicfilter`       | Topic filter khi subscribe (nếu có)                  |
| `qos`               | Mức QoS của MQTT                                     |
| `retain`            | Cờ retain (0/1)                                      |
| `dupflag`           | Cờ duplicate (0/1)                                   |
| `payload_length`    | Kích thước payload (byte hoặc độ dài chuỗi)          |
| `Payload_sample`    | Mẫu payload đã loại control char                     |
| `packet_type`       | Loại gói MQTT (CONNECT, PUBLISH, SUBSCRIBE, ...)     |
| `protocol`          | Tên giao thức chuẩn hóa                              |
| `connack_code`      | Mã phản hồi CONNACK (nếu có)                         |
| `Label`             | Nhãn hành vi (bình thường / kiểu tấn công / unknown) |
| `username`          | Username dùng để xác thực                            |
| `msgid`             | Message ID (QoS1/2)                                  |
| `auth_reason`       | Thông tin bổ sung về lý do auth/khóa                 |

`build_canonical_dataset.py` tự động:

- Ghép các cột đồng nghĩa (`mqtt.clientid`, `device_id`, `mqtt.topic`, ...).
- Chuẩn hóa thời gian sang UTC.
- Giải mã payload hex thành đoạn text dễ đọc.
- Lọc chỉ giữ các giao thức IoT trong danh sách cho phép.
- Đọc file theo từng phần (chunk) để xử lý được dataset dung lượng lớn.

### Trích xuất đặc trưng

`feature_extract.py` nhận đầu vào là CSV theo schema chuẩn. Script sẽ:

- Tách giá trị số từ payload khi có thể.
- Tính thời gian giữa các gói liên tiếp theo từng `client_id`.
- Giữ lại các cờ QoS/retain/dup và sự hiện diện của `msgid`.
- Xuất kết quả thành `features_<input>.csv` (có thể đổi bằng `--out`).

Kiểm tra nhanh file đặc trưng:

```bash
python - <<"PY"
import pandas as pd
print(pd.read_csv("features_canonical_dataset.csv", nrows=5))
PY
```

## Xử lý sự cố thường gặp

- **Thiếu pandas**: chạy `pip install -r requirements.txt` (tool cần pandas >= 2.0).
- **File đầu ra rỗng**: kiểm tra pattern `--pattern` và giao thức có nằm trong danh sách cho phép.
- **Không kết nối được broker**: đảm bảo EMQX hoặc Mosquitto đang chạy đúng host/port.
- **Trùng port Docker**: chỉnh lại port trong `docker-compose.yml` nếu 1883/18083 đã bị dùng.

## Hướng phát triển tiếp

- Dùng `features_canonical_dataset.csv` để phân tích hoặc huấn luyện mô hình.
- Bổ sung alias mới vào `build_canonical_dataset.py` khi nhập thêm bộ dữ liệu khác.
- Tùy biến tần suất publish của simulator bằng `--publish-interval` để phục vụ test tải.

## Lưu ý Git (không push file docs)

- Muốn giữ lại thay đổi docx ở local mà không đẩy lên remote, dùng: `git update-index --skip-worktree "Idea Final.docx" "Huong_dan_demo_IoT_MQTT.docx"`.
- Khi cần push lại hai file này, bỏ cờ skip bằng: `git update-index --no-skip-worktree "Idea Final.docx" "Huong_dan_demo_IoT_MQTT.docx"`.

## ⚔️ MQTT Attack Scenarios

### 🎯 Comprehensive Attack Suite

Bộ 9 kịch bản tấn công MQTT để kiểm tra bảo mật và khả năng chống chịu:

| Attack Script                   | Mô Tả                       | Mục Đích                                 |
| ------------------------------- | --------------------------- | ---------------------------------------- |
| **script_flood.py**             | Message flooding attack     | Test khả năng xử lý high-rate messages   |
| **script_wildcard.py**          | Wildcard subscription abuse | Thu thập thông tin qua wildcard patterns |
| **script_bruteforce.py**        | Topic brute-force attack    | Tìm kiếm topic và quyền truy cập         |
| **script_payload_anomaly.py**   | Payload anomaly attack      | Test xử lý malformed/anomalous payloads  |
| **script_retain_qos.py**        | Retain/QoS abuse attack     | Lạm dụng retain messages và QoS levels   |
| **script_topic_enumeration.py** | Topic enumeration attack    | Khám phá topic structures và hierarchy   |
| **script_duplicate_id.py**      | Duplicate client ID attack  | Tạo conflicts với duplicate client IDs   |
| **script_reconnect.py**         | Reconnect storm attack      | Overwhelm broker với reconnect patterns  |
| **script_qos2_abuse.py**        | QoS 2 abuse attack          | Exploit exactly-once delivery mechanism  |

### 🚀 Attack Execution

#### Single Attack Examples

```bash
# Message flood với 50 workers
python script_flood.py --broker localhost --workers 50 --msg-rate 200

# Payload anomaly với 10 loại payload bất thường
python script_payload_anomaly.py --workers 5 --attack-rate 2.0

# Topic enumeration với wildcard patterns
python script_topic_enumeration.py --workers 2

# Reconnect storm với connection bombs
python script_reconnect.py --workers 10 --bomb-size 100
```

#### Automated Demo

```bash
# Interactive demo menu
python demo_all_attacks.py

# Sequential execution (tất cả attacks tuần tự)
python demo_all_attacks.py --mode sequential --duration 30

# Parallel execution (chọn attacks chạy song song)
python demo_all_attacks.py --mode parallel --attacks 1 3 5 --parallel-duration 60
```

### 📊 Attack Logging & Analysis

- Tất cả attacks ghi log chi tiết vào CSV
- Real-time statistics và monitoring
- Success/failure rates tracking
- Impact analysis capabilities

## Attack simulation scripts

- `script_flood.py`: spawn multiple attacker clients that publish at a fixed rate to stress the broker. Example: `python script_flood.py --broker localhost --workers 50 --msg-rate 200 --log-csv flood.csv`.
- `script_wildcard.py`: connect a listener client and subscribe to broad wildcard filters (including `$SYS/#`) to validate detection of unauthorized eavesdropping. Example: `python script_wildcard.py --broker localhost --topics "#" "$SYS/#" "factory/+/+/#" --log-csv wildcard.csv`.
- `script_bruteforce.py`: iterate through hundreds of topic names (or load from file) to trigger subscribe brute-force rules while logging SUBACK responses. Example: `python script_bruteforce.py --broker localhost --topic-count 500 --rate 20 --rotate-every 100 --log-csv brute.csv`.
