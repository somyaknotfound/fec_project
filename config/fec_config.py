"""
Forward Error Correction configuration.
"""

class FECConfig:
    """FEC encoding/decoding parameters"""
    
    # Reed-Solomon Parameters - FIXED
    N_DATA_PACKETS = 4          # Number of data packets per block
    N_PARITY_PACKETS = 4        # Increased to 4 for better protection
    
    @property
    def code_rate(self):
        return self.N_DATA_PACKETS / (self.N_DATA_PACKETS + self.N_PARITY_PACKETS)
    
    @property
    def total_packets(self):
        return self.N_DATA_PACKETS + self.N_PARITY_PACKETS
    
    MAX_PAYLOAD_SIZE = 1024
    HEADER_SIZE = 16
    MAX_DECODE_ATTEMPTS = 3
    BLOCK_TIMEOUT = 5.0
    ENABLE_INTERLEAVING = False
    USE_SYSTEMATIC_CODE = True
