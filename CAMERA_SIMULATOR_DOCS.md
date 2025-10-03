# 🎥 Camera MQTT Simulator Documentation

Camera MQTT Simulator tạo dữ liệu synthetic cho hệ thống camera IoT không cần dataset có sẵn.

## 🚀 Quick Start

### 1. Khởi động MQTT Broker

```bash
docker-compose up -d emqx
```

### 2. Test đơn giản

```bash
python test_camera_simulator.py
```

### 3. Chạy Camera Simulator đầy đủ

```bash
# Terminal 1: Start subscriber
python camera_mqtt_subscriber.py --broker localhost

# Terminal 2: Start simulator (5 cameras, 120 seconds)
python camera_mqtt_simulator.py --cameras 5 --duration 120 --broker localhost
```

### 4. Demo tự động

```bash
python camera_demo.py
```

## 📡 MQTT Topics & Payload

### 🎯 Topic Structure

```
surveillance/{zone}/camera/{camera_id}/status    # Camera health & telemetry
surveillance/{zone}/camera/{camera_id}/motion    # Motion detection events
surveillance/{zone}/camera/{camera_id}/stream    # Stream metadata
security/{zone}/camera/{camera_id}/event         # Security events
system/{zone}/camera/{camera_id}/event           # System events
```

### 🏢 Camera Zones

- `entrance` - Lối vào chính
- `lobby` - Sảnh lớn
- `parking` - Bãi đỗ xe
- `warehouse` - Kho hàng
- `office` - Văn phòng
- `cafeteria` - Căng tin
- `server_room` - Phòng server

### 📊 Message Types

#### 1. Camera Status (30s interval)

```json
{
  "device_type": "Camera",
  "camera_id": "cam_001",
  "zone": "entrance",
  "timestamp": "2025-10-03T10:15:30.123Z",
  "status": "online",
  "resolution": "1920x1080",
  "fps": 30,
  "temperature": 45.2,
  "cpu_usage": 32.1,
  "memory_usage": 67.5,
  "recording": true,
  "motion_detection_enabled": true,
  "night_vision_active": false
}
```

#### 2. Motion Detection (random 5-15s)

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
  "motion_vector": {
    "direction": "northeast",
    "speed": "medium"
  },
  "alert_level": "medium"
}
```

#### 3. Security Events (random 20-60s)

```json
{
  "device_type": "Camera",
  "event_type": "person_detected",
  "camera_id": "cam_001",
  "zone": "entrance",
  "timestamp": "2025-10-03T10:15:30.123Z",
  "severity": "warning",
  "confidence": 0.94,
  "details": {
    "person_count": 2,
    "estimated_age": "30±10",
    "estimated_gender": "male",
    "clothing_color": "dark"
  },
  "snapshot_id": "snap_cam_001_1696339530",
  "alert_sent": true
}
```

#### 4. System Events (random 45-120s)

```json
{
  "device_type": "Camera",
  "event_type": "config_changed",
  "camera_id": "cam_001",
  "zone": "entrance",
  "timestamp": "2025-10-03T10:15:30.123Z",
  "source": "system",
  "details": {
    "parameter": "resolution",
    "old_value": "1280x720",
    "new_value": "1920x1080"
  },
  "user_id": "admin_1"
}
```

#### 5. Stream Metadata (10s interval)

```json
{
  "device_type": "Camera",
  "camera_id": "cam_001",
  "zone": "entrance",
  "timestamp": "2025-10-03T10:15:30.123Z",
  "stream_status": "active",
  "current_fps": 29,
  "bitrate_kbps": 4500,
  "encoding": "H.264",
  "quality_score": 0.95,
  "storage_remaining_hours": 72.5
}
```

## 🎛️ Configuration Options

### Camera Simulator Parameters

```bash
python camera_mqtt_simulator.py \
  --broker localhost \
  --port 1883 \
  --cameras 5 \
  --duration 0    # 0 = infinite
```

### Camera Properties (Auto-generated)

- **Camera Models**: HikVision DS-2CD2086G2, Dahua IPC-HFW5241E, Axis M3046-V, Bosch NBE-4502-AL
- **Resolutions**: 1920x1080, 1280x720, 3840x2160, 1600x1200
- **FPS**: 15, 24, 30, 60
- **IP Addresses**: 192.168.1.101-150
- **Features**: Night vision, PTZ, Audio (random assignment)

## 🔥 Event Types

### Motion Detection

- `motion_detected` - Basic motion detection
- Confidence scores: 0.3-0.99
- Motion area percentage: 2-25%
- Bounding boxes with coordinates

### Security Events

- `person_detected` - Human detection
- `face_recognized` - Known face identified
- `face_unknown` - Unknown face detected
- `vehicle_detected` - Vehicle in frame
- `loitering_detected` - Prolonged presence
- `intrusion_alert` - Unauthorized access
- `tampering_detected` - Camera interference
- `audio_anomaly` - Suspicious sounds
- `object_removed` - Missing object
- `object_left_behind` - Abandoned object

### System Events

- `config_changed` - Settings modified
- `firmware_update` - Software updated
- `restart` - System reboot
- `maintenance_mode` - Service mode
- `storage_full` - Disk space warning
- `network_issue` - Connectivity problem
- `temperature_warning` - Overheating
- `auth_failure` - Login attempt failed

## 📈 QoS Levels

- **Status/Stream**: QoS 0/1 (High frequency)
- **Motion/Security**: QoS 2 (Critical events)
- **System**: QoS 1 (Important events)

## 🔧 Integration với Existing Platform

Camera simulator có thể chạy song song với canonical simulator:

```bash
# Terminal 1: Canonical IoT simulator (19 devices)
python canonical_simulator.py --broker localhost --duration 0

# Terminal 2: Camera simulator (5 cameras)
python camera_mqtt_simulator.py --cameras 5 --duration 0 --broker localhost

# Terminal 3: Monitor all traffic
python test_subscriber.py --broker localhost --all-zones
```

## 📋 Log Format

Camera simulator tạo log dễ đọc với emoji:

```
2025-10-03 16:43:31 - INFO - 📊 [STATUS] cam_001@entrance - online | Temp: 45.2°C | CPU: 32.1%
2025-10-03 16:43:35 - INFO - 🚶 [MOTION] cam_002@lobby - 🟡 MEDIUM | Confidence: 0.87 | Area: 12.5%
2025-10-03 16:43:42 - INFO - 🚨 [SECURITY] cam_001@entrance - ⚠️ person_detected | Severity: warning
2025-10-03 16:43:50 - INFO - 🔧 [SYSTEM] cam_003@parking - 🔧 config_changed
```

## 🎯 Use Cases

1. **Security Testing**: Test MQTT security với realistic camera payloads
2. **Performance Testing**: Load testing với multiple camera streams
3. **Analytics Development**: Develop camera analytics trên MQTT data
4. **Integration Testing**: Test camera integration với existing IoT platform
5. **Demo & Training**: Demonstrate camera IoT capabilities

## 🔗 Related Scripts

- `camera_mqtt_simulator.py` - Main camera simulator
- `test_camera_simulator.py` - Simple test script
- `camera_mqtt_subscriber.py` - Message listener/monitor
- `camera_demo.py` - Interactive demo runner
- `camera_quick_demo.py` - Automated quick demo
