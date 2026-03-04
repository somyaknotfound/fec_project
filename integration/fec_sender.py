"""
FEC Sender - Integrates FEC encoding with UDP transmission
"""

import socket
import struct
import logging
from core.fec_encoder import FECEncoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FECSender:
    """Send data with FEC protection"""
    
    def __init__(self, dest_ip="127.0.0.1", dest_port=5000, 
                 n_data=4, n_parity=4):
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        
        self.encoder = FECEncoder(n_data_packets=n_data, 
                                  n_parity_packets=n_parity)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.packet_buffer = []
        self.block_counter = 0
        
        logger.info(f"FEC Sender: {dest_ip}:{dest_port}")
        logger.info(f"Code: ({n_data}, {n_parity})")
    
    def send_data(self, data_payload):
        """
        Send data with FEC protection.
        Buffers packets until we have enough for a block.
        """
        self.packet_buffer.append(data_payload)
        
        # When buffer is full, encode and send
        if len(self.packet_buffer) >= self.encoder.n_data:
            self._send_fec_block()
    
    def _send_fec_block(self):
        """Encode and send a complete FEC block"""
        # Get packets for this block
        data_packets = self.packet_buffer[:self.encoder.n_data]
        self.packet_buffer = self.packet_buffer[self.encoder.n_data:]
        
        # Encode
        encoded_packets = self.encoder.encode_block(data_packets)
        
        logger.info(f"Sending block {self.block_counter} ({len(encoded_packets)} packets)")
        
        # Send each packet with metadata
        for idx, packet_data in enumerate(encoded_packets):
            # Create header: block_id (4B) | packet_idx (2B) | total (2B)
            header = struct.pack('!IHH', self.block_counter, idx, 
                               len(encoded_packets))
            
            full_packet = header + packet_data
            self.sock.sendto(full_packet, (self.dest_ip, self.dest_port))
        
        self.block_counter += 1
    
    def flush(self):
        """Send any remaining buffered packets"""
        if self.packet_buffer:
            # Pad buffer to complete block
            while len(self.packet_buffer) < self.encoder.n_data:
                self.packet_buffer.append(b'\x00' * 1024)
            self._send_fec_block()
    
    def close(self):
        self.flush()
        self.sock.close()
