"""
FEC Receiver - Receives and decodes FEC-protected data
"""

import socket
import struct
import logging
from collections import defaultdict
from core.fec_decoder import FECDecoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FECReceiver:
    """Receive data with FEC protection"""
    
    def __init__(self, listen_ip="127.0.0.1", listen_port=5000,
                 n_data=4, n_parity=4):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        
        self.decoder = FECDecoder(n_data_packets=n_data,
                                  n_parity_packets=n_parity)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((listen_ip, listen_port))
        
        # Store received packets by block_id
        self.blocks = defaultdict(dict)
        
        self.recovered_data = []
        
        logger.info(f"FEC Receiver: {listen_ip}:{listen_port}")
    
    def receive_blocks(self, num_blocks, timeout=30):
        """Receive and decode FEC blocks"""
        self.sock.settimeout(timeout)
        
        logger.info(f"Waiting for {num_blocks} blocks...")
        
        blocks_decoded = 0
        
        while blocks_decoded < num_blocks:
            try:
                data, addr = self.sock.recvfrom(2048)
                
                # Parse header
                header_size = 8  # 4 + 2 + 2 bytes
                header = data[:header_size]
                payload = data[header_size:]
                
                block_id, packet_idx, total_packets = struct.unpack('!IHH', header)
                
                # Store packet
                self.blocks[block_id][packet_idx] = payload
                
                logger.debug(f"Received block {block_id}, packet {packet_idx}/{total_packets}")
                
                # Try to decode if we have enough packets
                if len(self.blocks[block_id]) >= self.decoder.n_data:
                    if self._try_decode_block(block_id, total_packets):
                        blocks_decoded += 1
                        logger.info(f"Progress: {blocks_decoded}/{num_blocks} blocks decoded")
                
            except socket.timeout:
                logger.warning(f"Timeout - decoded {blocks_decoded}/{num_blocks} blocks")
                break
        
        return self.recovered_data
    
    def _try_decode_block(self, block_id, total_packets):
        """Attempt to decode a block"""
        # Create packet list (None for missing)
        received = [None] * total_packets
        
        for idx, payload in self.blocks[block_id].items():
            received[idx] = payload
        
        # Decode
        recovered, success = self.decoder.decode_block(received)
        
        if success:
            self.recovered_data.extend(recovered)
            # Remove decoded block
            del self.blocks[block_id]
            return True
        
        return False
    
    def get_statistics(self):
        """Get decoder statistics"""
        return self.decoder.get_statistics()
    
    def close(self):
        self.sock.close()
