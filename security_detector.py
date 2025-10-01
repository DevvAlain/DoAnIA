#!/usr/bin/env python3
"""
Rule-based Detection & Anomaly Detection cho MQTT Security
Feature Extraction → Detection Rules → Alert/Block
"""

import pandas as pd
import numpy as np
import json
import logging
import argparse
import time
from datetime import datetime, timedelta
import os
from collections import defaultdict, deque
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTSecurityDetector:
    """
    Detection engine cho MQTT security theo flow: 
    Features → Rules → Anomaly Detection → Alert/Block
    """
    
    def __init__(self, features_file=None, output_alerts="security_alerts.csv"):
        self.features_file = features_file
        self.output_alerts = output_alerts
        self.detection_rules = {}
        self.anomaly_models = {}
        self.alert_history = deque(maxlen=1000)
        self.client_stats = defaultdict(lambda: {
            'message_count': 0,
            'topics': set(),
            'first_seen': None,
            'last_seen': None,
            'payload_sizes': [],
            'qos_levels': [],
            'suspicious_score': 0
        })
        
        self._init_detection_rules()
        self._init_alert_log()
        
    def _init_detection_rules(self):
        """Initialize rule-based detection rules"""
        logger.info("🛡️ Initializing MQTT Security Detection Rules...")
        
        self.detection_rules = {
            # Message Flooding Detection
            'flood_detection': {
                'name': 'Message Flood Attack',
                'threshold': 100,  # messages per minute
                'window': 60,  # seconds
                'severity': 'HIGH',
                'action': 'BLOCK'
            },
            
            # Topic Enumeration Detection  
            'topic_enumeration': {
                'name': 'Topic Enumeration Attack',
                'threshold': 20,  # unique topics per minute
                'window': 60,
                'severity': 'MEDIUM', 
                'action': 'ALERT'
            },
            
            # Wildcard Abuse Detection
            'wildcard_abuse': {
                'name': 'Wildcard Subscription Abuse',
                'patterns': ['#', '+/#', '$SYS/#', '*'],
                'severity': 'MEDIUM',
                'action': 'ALERT'
            },
            
            # Payload Anomaly Detection
            'payload_anomaly': {
                'name': 'Payload Anomaly Attack',
                'max_size': 10000,  # bytes
                'min_size': 1,
                'severity': 'MEDIUM',
                'action': 'ALERT'
            },
            
            # QoS Abuse Detection
            'qos_abuse': {
                'name': 'QoS Level Abuse',
                'qos2_threshold': 50,  # QoS 2 messages per hour
                'window': 3600,
                'severity': 'LOW',
                'action': 'MONITOR'
            },
            
            # Reconnection Storm Detection
            'reconnect_storm': {
                'name': 'Reconnection Storm Attack', 
                'threshold': 10,  # reconnects per minute
                'window': 60,
                'severity': 'HIGH',
                'action': 'BLOCK'
            },
            
            # Duplicate Client ID Detection
            'duplicate_client': {
                'name': 'Duplicate Client ID Attack',
                'severity': 'MEDIUM',
                'action': 'ALERT'
            },
            
            # Retain Message Abuse
            'retain_abuse': {
                'name': 'Retain Message Abuse',
                'threshold': 100,  # retain messages per hour
                'window': 3600,
                'severity': 'MEDIUM', 
                'action': 'ALERT'
            },
            
            # System Topic Access
            'system_topic_access': {
                'name': 'Unauthorized System Topic Access',
                'patterns': ['$SYS/', '$share/', '$queue/'],
                'severity': 'HIGH',
                'action': 'BLOCK'
            }
        }
        
        logger.info(f"✅ Loaded {len(self.detection_rules)} detection rules")
        
    def _init_alert_log(self):
        """Initialize alert logging"""
        if not os.path.exists(self.output_alerts):
            with open(self.output_alerts, 'w') as f:
                f.write("timestamp,rule_name,severity,client_id,topic,description,action,blocked\n")
                
        logger.info(f"📝 Alert logging: {self.output_alerts}")
        
    def analyze_features(self, features_file=None):
        """
        Analyze extracted features và run detection
        """
        if features_file:
            self.features_file = features_file
            
        if not self.features_file or not os.path.exists(self.features_file):
            logger.error(f"❌ Features file not found: {self.features_file}")
            return
            
        logger.info(f"🔍 Analyzing features from: {self.features_file}")
        
        # Load features in chunks
        chunk_size = 10000
        total_alerts = 0
        
        for chunk_num, chunk in enumerate(pd.read_csv(self.features_file, chunksize=chunk_size)):
            logger.info(f"📊 Processing chunk {chunk_num + 1}: {len(chunk)} records")
            
            # Run detection rules on chunk
            alerts = self._run_detection_rules(chunk)
            total_alerts += len(alerts)
            
            # Log alerts
            if alerts:
                self._log_alerts(alerts)
                
        logger.info(f"🚨 Detection completed: {total_alerts} alerts generated")
        self._print_detection_summary()
        
    def _run_detection_rules(self, data_chunk):
        """Run tất cả detection rules trên data chunk"""
        alerts = []
        
        for _, record in data_chunk.iterrows():
            try:
                # Update client statistics
                self._update_client_stats(record)
                
                # Run each detection rule
                alerts.extend(self._check_flood_detection(record))
                alerts.extend(self._check_topic_enumeration(record))
                alerts.extend(self._check_wildcard_abuse(record))
                alerts.extend(self._check_payload_anomaly(record))
                alerts.extend(self._check_qos_abuse(record))
                alerts.extend(self._check_system_topic_access(record))
                alerts.extend(self._check_retain_abuse(record))
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing record: {e}")
                continue
                
        return alerts
        
    def _update_client_stats(self, record):
        """Update client statistics for anomaly detection"""
        client_id = record.get('client_id', 'unknown')
        topic = record.get('topic', '')
        timestamp = pd.to_datetime(record.get('timestamp', datetime.now()))
        
        stats = self.client_stats[client_id]
        stats['message_count'] += 1
        stats['topics'].add(topic)
        stats['last_seen'] = timestamp
        
        if stats['first_seen'] is None:
            stats['first_seen'] = timestamp
            
        # Track payload sizes và QoS
        if 'payload_length' in record:
            stats['payload_sizes'].append(record['payload_length'])
            
        if 'qos' in record:
            stats['qos_levels'].append(record['qos'])
            
    def _check_flood_detection(self, record):
        """Detect message flooding attacks"""
        alerts = []
        client_id = record.get('client_id', 'unknown')
        stats = self.client_stats[client_id]
        
        # Simple rate-based detection (in real implementation, would use sliding window)
        if stats['message_count'] > self.detection_rules['flood_detection']['threshold']:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'rule_name': 'Message Flood Attack',
                'severity': 'HIGH',
                'client_id': client_id,
                'topic': record.get('topic', ''),
                'description': f"Client exceeded {self.detection_rules['flood_detection']['threshold']} messages",
                'action': 'BLOCK',
                'blocked': True
            }
            alerts.append(alert)
            
        return alerts
        
    def _check_topic_enumeration(self, record):
        """Detect topic enumeration attacks"""
        alerts = []
        client_id = record.get('client_id', 'unknown')
        stats = self.client_stats[client_id]
        
        # Check for excessive unique topics
        if len(stats['topics']) > self.detection_rules['topic_enumeration']['threshold']:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'rule_name': 'Topic Enumeration Attack',
                'severity': 'MEDIUM',
                'client_id': client_id,
                'topic': record.get('topic', ''),
                'description': f"Client accessed {len(stats['topics'])} unique topics",
                'action': 'ALERT',
                'blocked': False
            }
            alerts.append(alert)
            
        return alerts
        
    def _check_wildcard_abuse(self, record):
        """Detect wildcard subscription abuse"""
        alerts = []
        topic = record.get('topic', '')
        
        for pattern in self.detection_rules['wildcard_abuse']['patterns']:
            if pattern in topic:
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'rule_name': 'Wildcard Subscription Abuse',
                    'severity': 'MEDIUM',
                    'client_id': record.get('client_id', 'unknown'),
                    'topic': topic,
                    'description': f"Wildcard pattern detected: {pattern}",
                    'action': 'ALERT',
                    'blocked': False
                }
                alerts.append(alert)
                break
                
        return alerts
        
    def _check_payload_anomaly(self, record):
        """Detect payload size anomalies"""
        alerts = []
        payload_length = record.get('payload_length', 0)
        rules = self.detection_rules['payload_anomaly']
        
        if payload_length > rules['max_size'] or payload_length < rules['min_size']:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'rule_name': 'Payload Anomaly Attack',
                'severity': 'MEDIUM',
                'client_id': record.get('client_id', 'unknown'),
                'topic': record.get('topic', ''),
                'description': f"Anomalous payload size: {payload_length} bytes",
                'action': 'ALERT',
                'blocked': False
            }
            alerts.append(alert)
            
        return alerts
        
    def _check_qos_abuse(self, record):
        """Detect QoS level abuse"""
        alerts = []
        qos = record.get('qos', 0)
        client_id = record.get('client_id', 'unknown')
        stats = self.client_stats[client_id]
        
        # Count QoS 2 usage
        qos2_count = sum(1 for q in stats['qos_levels'] if q == 2)
        
        if qos2_count > self.detection_rules['qos_abuse']['qos2_threshold']:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'rule_name': 'QoS Level Abuse',
                'severity': 'LOW',
                'client_id': client_id,
                'topic': record.get('topic', ''),
                'description': f"Excessive QoS 2 usage: {qos2_count} messages",
                'action': 'MONITOR',
                'blocked': False
            }
            alerts.append(alert)
            
        return alerts
        
    def _check_system_topic_access(self, record):
        """Detect unauthorized system topic access"""
        alerts = []
        topic = record.get('topic', '')
        
        for pattern in self.detection_rules['system_topic_access']['patterns']:
            if topic.startswith(pattern):
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'rule_name': 'Unauthorized System Topic Access',
                    'severity': 'HIGH',
                    'client_id': record.get('client_id', 'unknown'),
                    'topic': topic,
                    'description': f"Access to system topic: {pattern}",
                    'action': 'BLOCK',
                    'blocked': True
                }
                alerts.append(alert)
                break
                
        return alerts
        
    def _check_retain_abuse(self, record):
        """Detect retain message abuse"""
        alerts = []
        retain = record.get('retain', 0)
        client_id = record.get('client_id', 'unknown')
        
        if retain:
            # Simple counting (in real implementation would use time windows)
            stats = self.client_stats[client_id]
            if not hasattr(stats, 'retain_count'):
                stats['retain_count'] = 0
            stats['retain_count'] += 1
            
            if stats['retain_count'] > self.detection_rules['retain_abuse']['threshold']:
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'rule_name': 'Retain Message Abuse',
                    'severity': 'MEDIUM',
                    'client_id': client_id,
                    'topic': record.get('topic', ''),
                    'description': f"Excessive retain messages: {stats['retain_count']}",
                    'action': 'ALERT',
                    'blocked': False
                }
                alerts.append(alert)
                
        return alerts
        
    def _log_alerts(self, alerts):
        """Log alerts to CSV file"""
        with open(self.output_alerts, 'a') as f:
            for alert in alerts:
                f.write(f"{alert['timestamp']},{alert['rule_name']},{alert['severity']},"
                       f"{alert['client_id']},{alert['topic']},\"{alert['description']}\","
                       f"{alert['action']},{alert['blocked']}\n")
                
        # Add to memory history
        self.alert_history.extend(alerts)
        
        # Print high-severity alerts
        for alert in alerts:
            if alert['severity'] in ['HIGH', 'CRITICAL']:
                logger.warning(f"🚨 {alert['severity']} ALERT: {alert['rule_name']} - {alert['description']}")
                
    def _print_detection_summary(self):
        """Print detection summary"""
        logger.info("=" * 60)
        logger.info("📋 DETECTION SUMMARY")
        logger.info("=" * 60)
        
        # Count by severity
        severity_counts = defaultdict(int)
        action_counts = defaultdict(int)
        
        for alert in self.alert_history:
            severity_counts[alert['severity']] += 1
            action_counts[alert['action']] += 1
            
        logger.info("🚨 Alerts by Severity:")
        for severity, count in severity_counts.items():
            logger.info(f"   {severity}: {count}")
            
        logger.info("🛡️ Actions Taken:")
        for action, count in action_counts.items():
            logger.info(f"   {action}: {count}")
            
        logger.info(f"📊 Total Clients Analyzed: {len(self.client_stats)}")
        logger.info(f"📝 Alerts logged to: {self.output_alerts}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Security Detection Engine")
    parser.add_argument("--features", required=True, help="Features CSV file from feature extraction")
    parser.add_argument("--alerts", default="security_alerts.csv", help="Output alerts CSV file")
    parser.add_argument("--real-time", action="store_true", help="Real-time monitoring mode")
    
    args = parser.parse_args()
    
    try:
        detector = MQTTSecurityDetector(
            features_file=args.features,
            output_alerts=args.alerts
        )
        
        if args.real_time:
            logger.info("🔄 Real-time monitoring mode not implemented yet")
            # TODO: Implement real-time monitoring
        else:
            detector.analyze_features()
            
    except Exception as e:
        logger.error(f"❌ Detection failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())