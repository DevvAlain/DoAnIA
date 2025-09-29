# 🏭 IoT MQTT Security Research Platform

Dự án nghiên cứu bảo mật MQTT IoT bao gồm:

- 🔄 **Data Pipeline**: Xử lý và chuẩn hóa dữ liệu MQTT từ CSV
- 📡 **IoT Simulators**: Mô phỏng 9 thiết bị IoT với payload chuẩn
- ⚔️ **Attack Scripts**: 9 kịch bản tấn công MQTT để kiểm tra bảo mật
- 🔬 **Analysis Tools**: Trích xuất đặc trưng và phân tích dữ liệu

## 📁 Cấu trúc dự án

```
Do An IA/
├── 📊 Data Processing
│   ├── datasets/                     # Dataset CSV thô từ 9 thiết bị IoT
│   ├── build_canonical_dataset.py    # Chuẩn hóa CSV về schema chuẩn
│   ├── feature_extract.py            # Trích xuất đặc trưng cho ML
│   └── canonical_dataset.csv         # Dataset đã chuẩn hóa
│
├── 📡 IoT Simulators
│   ├── unified_simulator.py         # ✨ Unified simulator (enhanced + legacy modes)
│   └── test_subscriber.py           # Test và verify simulator output
│
├── ⚔️ Attack Scripts
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
└── 🐳 Deployment
    ├── docker-compose.yml           # EMQX broker + simulator stack
    ├── Dockerfile                   # Container image cho simulator
    └── requirements.txt             # Python dependencies
```

> **Lưu ý**: hãy đặt mọi file dataset (\*.csv) vào thư mục `datasets/` trước khi chạy các lệnh bên dưới.

## Yêu cầu

- Python 3.11 trở lên (chạy local)
- Pip (hoặc công cụ quản lý package tương đương)
- Tùy chọn: Docker Desktop + Docker Compose (chạy bằng container)
- Bộ dataset CSV thô (TemperatureMQTTset.csv, LightIntensityMQTTset.csv, ...)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MQTT Broker (Mosquitto/EMQX) hoặc Docker

### 1. Setup Environment

```bash
# Tạo và kích hoạt virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Data Processing Pipeline

```bash
# Chuẩn hóa dataset từ CSV
python build_canonical_dataset.py --pattern "*MQTTset.csv" --output canonical_dataset.csv

# Trích xuất đặc trưng
python feature_extract.py canonical_dataset.csv --out features_canonical_dataset.csv
```

### 3. IoT Simulation

#### 🔥 Enhanced Mode (Khuyến nghị)

```bash
# Tạo dữ liệu IoT với payload chuẩn (mặc định)
python unified_simulator.py --broker localhost --devices Temperature Humidity CO2

# Test output trong terminal khác
python test_subscriber.py --all-zones
```

#### 🔄 Legacy Mode

```bash
# Replay từ CSV data (backward compatibility)
python unified_simulator.py --legacy --broker localhost --publish-interval 0.2
```

### 4. Security Testing

#### Single Attack

```bash
# Chạy một loại tấn công
python script_flood.py --broker localhost --workers 10 --msg-rate 100

# Topic enumeration
python script_topic_enumeration.py --broker localhost --workers 2
```

#### All Attacks Demo

```bash
# Demo tất cả kịch bản tấn công
python demo_all_attacks.py --broker localhost --duration 30
```

## 📡 IoT Devices & Payload Format

### 🌡️ Supported Devices

Enhanced simulator hỗ trợ 9 loại thiết bị IoT với payload format chuẩn:

| Device          | Topic Pattern                                          | Payload Format                                     |
| --------------- | ------------------------------------------------------ | -------------------------------------------------- |
| **Temperature** | `site/tenantA/zone1/temperature/{device_id}/telemetry` | `{"timestamp": 169xxx, "value": 24.6, "unit":"C"}` |
| **Humidity**    | `site/tenantA/zone1/humidity/{device_id}/telemetry`    | `{"value": 55.2, "unit":"%"}`                      |
| **CO₂/Gas**     | `site/tenantA/zone2/co2/{device_id}/telemetry`         | `{"value": 420, "unit":"ppm"}`                     |
| **Vibration**   | `site/tenantA/zone3/vibration/{device_id}/telemetry`   | `{"rms":0.032, "freq":120}`                        |
| **Smoke**       | `site/tenantA/zone1/smoke/{device_id}/telemetry`       | `{"value": 0.04, "alarm": false}`                  |
| **Air Quality** | `site/tenantA/zone4/airquality/{device_id}/telemetry`  | `{"pm2_5": 12.4, "pm10": 25.1}`                    |
| **Light**       | `site/tenantA/zone2/light/{device_id}/telemetry`       | `{"lux": 300}`                                     |
| **Sound**       | `site/tenantA/zone2/sound/{device_id}/telemetry`       | `{"db": 45}`                                       |
| **Water Level** | `site/tenantA/zone5/waterlevel/{device_id}/telemetry`  | `{"level": 1.24, "unit":"m"}`                      |

### 🎯 Topic Structure

```
site/tenantA/zone{N}/{device_type}/device_{XXX}/telemetry
```

Example: `site/tenantA/zone1/temperature/device_001/telemetry`

### ⚡ Usage Examples

```bash
# Enhanced mode - chỉ chạy Temperature và Humidity
python unified_simulator.py --devices Temperature Humidity

# Enhanced mode - tùy chỉnh publish interval
python unified_simulator.py --publish-interval 5.0

# Legacy mode - replay specific devices từ CSV
python unified_simulator.py --legacy --devices Temperature Light

# Subscribe specific zone
python test_subscriber.py --zone 1

# Subscribe specific device type
python test_subscriber.py --device-type temperature
```

Các tham số quan trọng:

- `--pattern`: chọn các file CSV cần gộp (có thể đổi thành `*.csv` nếu thư mục chỉ chứa dữ liệu IoT).
- `--protocols`: lọc theo danh sách giao thức IoT cho phép (mặc định đã gồm MQTT/MQTTS và nhiều giao thức IIoT phổ biến).

4. Trích xuất đặc trưng phục vụ phân tích/ML.

   ```bash
   python feature_extract.py canonical_dataset.csv --out features_canonical_dataset.csv
   ```

   File đầu ra giữ lại các trường telemetry quan trọng (`timestamp`, `client_id`, QoS, thời gian giữa hai gói, độ dài payload, nhãn,...).

5. Phát lại dữ liệu lên broker bằng script (tự tìm CSV trong `datasets/`).

   ```bash
   python unified_simulator.py --legacy --broker localhost --port 1883 --publish-interval 0.2
   ```

   Simulator sẽ publish lên các topic `site/tenantA/home/<device>/telemetry` với payload lấy từ dataset CSV.

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

**🚨 Simulator payload format sai**

```bash
# Problem: {"value": "ature-6"} instead of {"value": 24.6, "unit": "C"}
# Solution: Sử dụng enhanced mode (default) thay vì legacy mode

python unified_simulator.py --devices Temperature Humidity  # Enhanced mode
python test_subscriber.py --all-zones  # Verify output
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
# Đảm bảo datasets/ folder tồn tại và có CSV files
# Chỉnh sửa pattern nếu cần
python build_canonical_dataset.py --pattern "*.csv" --force
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
