#!/usr/bin/env python3
"""
Demo script để chạy tất cả các kịch bản tấn công MQTT
Chạy từng loại tấn công trong thời gian ngắn để demonstration
"""

import argparse
import subprocess
import time
import threading
import os
from datetime import datetime

class MQTTAttackDemo:
    def __init__(self, broker="localhost", port=1883, duration=30):
        self.broker = broker
        self.port = port
        self.duration = duration
        self.log_dir = f"attack_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Tạo thư mục log
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Danh sách các script tấn công
        self.attacks = [
            {
                "name": "Payload Anomaly Attack",
                "script": "script_payload_anomaly.py",
                "args": ["--workers", "3", "--attack-rate", "1.0"],
                "description": "Gửi các payload bất thường và malformed"
            },
            {
                "name": "Retain/QoS Abuse Attack", 
                "script": "script_retain_qos.py",
                "args": ["--workers", "2", "--retain-rate", "2.0", "--qos2-rate", "1.0"],
                "description": "Lạm dụng retain messages và QoS levels"
            },
            {
                "name": "Topic Enumeration Attack",
                "script": "script_topic_enumeration.py", 
                "args": ["--workers", "2"],
                "description": "Khám phá và liệt kê các topic có sẵn"
            },
            {
                "name": "Duplicate ID Attack",
                "script": "script_duplicate_id.py",
                "args": ["--workers", "4", "--max-rapid-connections", "50"],
                "description": "Tạo xung đột với duplicate client IDs"
            },
            {
                "name": "Reconnect Storm Attack",
                "script": "script_reconnect.py",
                "args": ["--workers", "5", "--max-reconnects-per-worker", "100", "--bomb-size", "20"],
                "description": "Tạo storm reconnection để quá tải broker"
            },
            {
                "name": "QoS2 Abuse Attack",
                "script": "script_qos2_abuse.py",
                "args": ["--workers", "3", "--message-rate", "2.0", "--max-messages-per-worker", "200"],
                "description": "Lạm dụng QoS 2 exactly-once delivery"
            }
        ]

    def run_attack(self, attack_info, attack_id):
        """Chạy một loại tấn công"""
        script_name = attack_info["script"]
        attack_name = attack_info["name"]
        description = attack_info["description"]
        
        print(f"\n{'='*60}")
        print(f"🚀 Bắt đầu: {attack_name}")
        print(f"📝 Mô tả: {description}")
        print(f"⏱️  Thời gian: {self.duration} giây")
        print(f"{'='*60}")
        
        # Tạo log file cho attack này
        log_file = os.path.join(self.log_dir, f"attack_{attack_id}_{script_name.replace('.py', '.csv')}")
        
        # Xây dựng command
        cmd = [
            "python", script_name,
            "--broker", self.broker,
            "--port", str(self.port),
            "--log-csv", log_file
        ] + attack_info["args"]
        
        print(f"🔧 Lệnh: {' '.join(cmd)}")
        print(f"📊 Log file: {log_file}")
        
        # Chạy attack trong subprocess
        try:
            process = subprocess.Popen(cmd, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True,
                                     bufsize=1,
                                     universal_newlines=True)
            
            # Cho phép attack chạy trong thời gian quy định
            time.sleep(self.duration)
            
            # Dừng attack
            process.terminate()
            
            # Đợi process kết thúc hoặc kill nếu cần
            try:
                stdout, stderr = process.communicate(timeout=10)
                print(f"✅ {attack_name} hoàn thành")
                if stdout:
                    print(f"📤 Output: {stdout[-200:]}")  # In 200 ký tự cuối
                if stderr:
                    print(f"⚠️  Errors: {stderr[-200:]}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"🛑 {attack_name} bị buộc dừng")
                
        except Exception as e:
            print(f"❌ Lỗi khi chạy {attack_name}: {e}")
        
        print(f"🏁 Kết thúc: {attack_name}")
        time.sleep(2)  # Pause giữa các attacks

    def run_all_attacks_sequential(self):
        """Chạy tất cả attacks tuần tự"""
        print(f"\n🎯 BẮT ĐẦU DEMO TẤT CẢ CÁC KỊCH BẢN TẤN CÔNG MQTT")
        print(f"🎯 Target: {self.broker}:{self.port}")
        print(f"🎯 Thời gian mỗi attack: {self.duration} giây")
        print(f"🎯 Tổng số attacks: {len(self.attacks)}")
        print(f"🎯 Log directory: {self.log_dir}")
        
        start_time = time.time()
        
        for i, attack in enumerate(self.attacks, 1):
            print(f"\n📍 Attack {i}/{len(self.attacks)}")
            self.run_attack(attack, i)
        
        total_time = time.time() - start_time
        print(f"\n🎉 HOÀN THÀNH TẤT CẢ ATTACKS!")
        print(f"⏱️  Tổng thời gian: {total_time:.1f} giây")
        print(f"📁 Kiểm tra logs tại: {self.log_dir}")

    def run_selected_attacks_parallel(self, selected_indices, parallel_duration=60):
        """Chạy một số attacks song song"""
        selected_attacks = [self.attacks[i-1] for i in selected_indices if 1 <= i <= len(self.attacks)]
        
        if not selected_attacks:
            print("❌ Không có attack nào được chọn!")
            return
        
        print(f"\n🎯 CHẠY SONG SONG {len(selected_attacks)} ATTACKS")
        print(f"🎯 Target: {self.broker}:{self.port}")
        print(f"🎯 Thời gian: {parallel_duration} giây")
        
        threads = []
        
        # Bắt đầu tất cả attacks song song
        for i, attack in enumerate(selected_attacks, 1):
            thread = threading.Thread(target=self.run_attack, args=(attack, i))
            thread.daemon = True
            threads.append(thread)
            thread.start()
            time.sleep(2)  # Stagger start times
        
        print(f"🚀 Đã khởi động {len(threads)} attacks song song")
        print(f"⏳ Đang chạy trong {parallel_duration} giây...")
        
        # Đợi hoàn thành
        time.sleep(parallel_duration)
        
        print(f"🏁 Kết thúc demo song song")

    def show_attack_menu(self):
        """Hiển thị menu chọn attacks"""
        print(f"\n📋 DANH SÁCH CÁC KỊCH BẢN TẤN CÔNG:")
        for i, attack in enumerate(self.attacks, 1):
            print(f"{i:2d}. {attack['name']}")
            print(f"     📄 {attack['description']}")
            print(f"     🔧 Script: {attack['script']}")
            print()

def main():
    parser = argparse.ArgumentParser(description="Demo MQTT Attack Scripts Suite")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--duration", type=int, default=30, help="Duration per attack (seconds)")
    
    parser.add_argument("--mode", choices=["sequential", "parallel", "menu"], default="menu",
                       help="Demo mode: sequential, parallel, or interactive menu")
    
    parser.add_argument("--attacks", type=int, nargs="+", 
                       help="Attack numbers to run (for parallel mode)")
    
    parser.add_argument("--parallel-duration", type=int, default=60,
                       help="Duration for parallel attack demo (seconds)")
    
    args = parser.parse_args()
    
    demo = MQTTAttackDemo(broker=args.broker, port=args.port, duration=args.duration)
    
    if args.mode == "sequential":
        demo.run_all_attacks_sequential()
        
    elif args.mode == "parallel":
        if args.attacks:
            demo.run_selected_attacks_parallel(args.attacks, args.parallel_duration)
        else:
            print("❌ Cần chỉ định --attacks cho parallel mode")
            demo.show_attack_menu()
            
    else:  # menu mode
        demo.show_attack_menu()
        
        print("🎮 CHỌN CHỨC NĂNG:")
        print("1. Chạy tất cả attacks tuần tự")
        print("2. Chạy attacks được chọn song song") 
        print("3. Thoát")
        
        try:
            choice = input("\n👆 Nhập lựa chọn (1-3): ").strip()
            
            if choice == "1":
                demo.run_all_attacks_sequential()
                
            elif choice == "2":
                attack_nums = input("👆 Nhập số thứ tự attacks (VD: 1 3 5): ").strip()
                try:
                    selected = [int(x) for x in attack_nums.split()]
                    duration = int(input(f"👆 Thời gian chạy song song (giây, mặc định {args.parallel_duration}): ") or args.parallel_duration)
                    demo.run_selected_attacks_parallel(selected, duration)
                except ValueError:
                    print("❌ Định dạng không hợp lệ!")
                    
            elif choice == "3":
                print("👋 Tạm biệt!")
                
            else:
                print("❌ Lựa chọn không hợp lệ!")
                
        except KeyboardInterrupt:
            print("\n🛑 Demo bị dừng bởi người dùng")

if __name__ == "__main__":
    main()