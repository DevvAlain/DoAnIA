# Mô phỏng MQTT cho 9 thiết bị IoT

Dự án này phát lại telemetry MQTT của chín thiết bị IoT từ các bản ghi CSV lịch sử. Ngoài ra, dự án còn cung cấp pipeline xử lý dữ liệu để quy đổi nhiều định dạng CSV khác nhau về cùng một schema chuẩn, giúp các bước tạo đặc trưng hoặc huấn luyện mô hình có thể tái sử dụng dễ dàng.

## Cấu trúc thư mục

```
Do An IA/
  datasets/                     # Thư mục chứa toàn bộ file CSV thô
    TemperatureMQTTset.csv
    LightIntensityMQTTset.csv
    ...
  build_canonical_dataset.py    # Chuẩn hóa CSV về schema chuẩn
  feature_extract.py            # Sinh đặc trưng phục vụ ML
  simulator_from_csv.py         # Phát lại lưu lượng MQTT cho từng thiết bị
  docker-compose.yml            # Stack EMQX + simulator (tùy chọn)
  Dockerfile                    # Docker image cho simulator
  requirements.txt              # Danh sách phụ thuộc Python
```

> **Lưu ý**: hãy đặt mọi file dataset (*.csv) vào thư mục `datasets/` trước khi chạy các lệnh bên dưới.

## Yêu cầu

- Python 3.11 trở lên (chạy local)
- Pip (hoặc công cụ quản lý package tương đương)
- Tùy chọn: Docker Desktop + Docker Compose (chạy bằng container)
- Bộ dataset CSV thô (TemperatureMQTTset.csv, LightIntensityMQTTset.csv, ...)

## Quy trình nhanh (chạy Python local)

1. Tạo môi trường ảo (khuyến nghị).

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows PowerShell
   # source .venv/bin/activate  # WSL/Linux/macOS
   ```

2. Cài đặt phụ thuộc.

   ```bash
   pip install -r requirements.txt
   ```

3. Gộp dữ liệu về schema chuẩn (mặc định đọc các CSV trong `datasets/`).

   ```bash
   python build_canonical_dataset.py --pattern "*MQTTset.csv" --output canonical_dataset.csv --chunksize 50000 --force
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
   python simulator_from_csv.py --broker localhost --port 1883 --publish-interval 0.2
   ```

   Simulator sẽ publish lên các topic `site/tenantA/home/<device>/telemetry` với payload lấy từ dataset CSV.

## Quy trình bằng Docker (EMQX + simulator)

1. Build và khởi động stack (Dockerfile đã copy thư mục `datasets/` vào image).

   ```bash
   docker-compose up --build -d
   ```

   Lệnh trên sẽ:
   - Build image `doania-simulator` (Python 3.11 + dependencies + folder datasets)
   - Khởi động EMQX (broker) và container simulator

2. Kiểm tra trạng thái container.

   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```

   Bạn sẽ thấy `emqx` mở cổng 1883/18083 và `mqtt-simulator` đang chạy.

3. Theo dõi log realtime.

   ```bash
   docker logs -f mqtt-simulator
   # Hoặc chỉ xem 10 dòng cuối
   docker logs --tail 10 mqtt-simulator
   ```

   Khi hoạt động ổn định, log sẽ báo tất cả 9 thiết bị kết nối tới EMQX.

4. Truy cập EMQX Dashboard.
   - URL: http://localhost:18083
   - Đăng nhập mặc định (nếu chưa đổi): `admin` / `public`
   - Theo dõi connections, throughput, subscriptions

5. Dừng và dọn dẹp.

   ```bash
   docker-compose down
   ```

   Thêm `--volumes` nếu muốn xóa luôn dữ liệu/volume tạm.

## Chi tiết xử lý dữ liệu

### Schema chuẩn

| Cột              | Mô tả                                             |
|------------------|---------------------------------------------------|
| `timestamp`      | Dấu thời gian ISO-8601 (UTC) cho từng gói tin      |
| `src_ip`/`src_port` | IP/port nguồn                                   |
| `dst_ip`/`dst_port` | IP/port đích (broker 1883/8883)                 |
| `client_id`      | Định danh thiết bị (hợp nhất client_id/device_id) |
| `topic`          | Topic publish                                     |
| `topicfilter`    | Topic filter khi subscribe (nếu có)               |
| `qos`            | Mức QoS của MQTT                                  |
| `retain`         | Cờ retain (0/1)                                   |
| `dupflag`        | Cờ duplicate (0/1)                                |
| `payload_length` | Kích thước payload (byte hoặc độ dài chuỗi)       |
| `Payload_sample` | Mẫu payload đã loại control char                  |
| `packet_type`    | Loại gói MQTT (CONNECT, PUBLISH, SUBSCRIBE, ...)  |
| `protocol`       | Tên giao thức chuẩn hóa                           |
| `connack_code`   | Mã phản hồi CONNACK (nếu có)                      |
| `Label`          | Nhãn hành vi (bình thường / kiểu tấn công / unknown) |
| `username`       | Username dùng để xác thực                         |
| `msgid`          | Message ID (QoS1/2)                               |
| `auth_reason`    | Thông tin bổ sung về lý do auth/khóa              |

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
## Attack simulation scripts

- `script_flood.py`: spawn multiple attacker clients that publish at a fixed rate to stress the broker. Example: `python script_flood.py --broker localhost --clients 50 --msg-rate 200 --topic-template "factory/{client}/telemetry" --log-csv flood.csv`.
- `script_wildcard.py`: connect a listener client and subscribe to broad wildcard filters (including `$SYS/#`) to validate detection of unauthorized eavesdropping. Example: `python script_wildcard.py --broker localhost --topics "#" "$SYS/#" "factory/+/+/#" --log-csv wildcard.csv`.
- `script_bruteforce.py`: iterate through hundreds of topic names (or load from file) to trigger subscribe brute-force rules while logging SUBACK responses. Example: `python script_bruteforce.py --broker localhost --topic-count 500 --rate 20 --rotate-every 100 --log-csv brute.csv`.
