"""
Traffic Receiver Module
"""

import socket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficReceiver:
    """Receive UDP traffic"""
    
    def __init__(self, listen_ip="127.0.0.1", listen_port=5000):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.listen_ip, self.listen_port))
        
        self.packets_received = 0
        
        logger.info(f"Receiver: {self.listen_ip}:{self.listen_port}")
    
    def receive_packets(self, num_packets, timeout=10):
        """Receive packets"""
        self.sock.settimeout(timeout)
        logger.info(f"Waiting for {num_packets} packets...")
        
        received_data = []
        
        for i in range(num_packets):
            try:
                data, addr = self.sock.recvfrom(2048)
                self.packets_received += 1
                received_data.append(data)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"  Received {i + 1}/{num_packets}")
                    
            except socket.timeout:
                logger.warning(f"Timeout after {self.packets_received} packets")
                break
        
        logger.info(f"✓ Received {self.packets_received} packets")
        return received_data
    
    def close(self):
        self.sock.close()
