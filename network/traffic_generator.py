"""
Traffic Generator Module
"""

import socket
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficGenerator:
    """Generate UDP traffic"""
    
    def __init__(self, dest_ip="127.0.0.1", dest_port=5000):
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packets_sent = 0
        
        logger.info(f"Traffic generator: {self.dest_ip}:{self.dest_port}")
    
    def send_packets(self, num_packets, packet_size=1024, delay=0.1):
        """Send a series of packets"""
        logger.info(f"Sending {num_packets} packets...")
        
        for i in range(num_packets):
            payload = f"PKT{i:04d}".encode() + b'X' * (packet_size - 7)
            self.sock.sendto(payload, (self.dest_ip, self.dest_port))
            self.packets_sent += 1
            
            if (i + 1) % 10 == 0:
                logger.info(f"  Sent {i + 1}/{num_packets}")
            
            time.sleep(delay)
        
        logger.info(f"✓ Complete: {self.packets_sent} packets sent")
    
    def close(self):
        self.sock.close()
