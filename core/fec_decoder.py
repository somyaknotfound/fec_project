"""
Simple working FEC decoder
"""

class FECDecoder:
    def __init__(self, n_data_packets=4, n_parity_packets=2):
        self.n_data = n_data_packets
        self.n_parity = n_parity_packets
        self.blocks_decoded = 0
        self.blocks_failed = 0
        self.packets_recovered = 0
    
    def decode_block(self, received_packets):
        total = self.n_data + self.n_parity
        received = [p for p in received_packets if p is not None]
        missing_count = total - len(received)
        
        if len(received) < self.n_data:
            self.blocks_failed += 1
            return None, False
        
        # Simple recovery: if we have all data packets, use them
        data_present = all(received_packets[i] is not None for i in range(self.n_data))
        
        if data_present:
            result = received_packets[:self.n_data]
            self.blocks_decoded += 1
            return result, True
        
        # If missing 1 data packet and have 1 parity, can recover via XOR
        if missing_count == 1 and self.n_parity >= 1:
            pkt_size = len(received[0])
            recovered = bytearray(pkt_size)
            
            # XOR all received packets
            for pkt in received:
                for i, byte in enumerate(pkt):
                    recovered[i] ^= byte
            
            # Find missing position and insert
            result = list(received_packets)
            for i in range(total):
                if result[i] is None:
                    result[i] = bytes(recovered)
                    break
            
            self.blocks_decoded += 1
            self.packets_recovered += 1
            return result[:self.n_data], True
        
        self.blocks_failed += 1
        return None, False
    
    def get_statistics(self):
        total = self.blocks_decoded + self.blocks_failed
        rate = (self.blocks_decoded / total * 100) if total > 0 else 0
        return {
            'blocks_decoded': self.blocks_decoded,
            'blocks_failed': self.blocks_failed,
            'total_blocks': total,
            'success_rate': rate,
            'packets_recovered': self.packets_recovered
        }
