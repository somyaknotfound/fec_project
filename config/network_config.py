"""
Network configuration.
"""

class NetworkConfig:
    """Network configuration parameters"""
    
    SENDER_IP = "127.0.0.1"
    RECEIVER_IP = "127.0.0.1"
    TEST_PORT = 5000
    
    DEFAULT_PACKET_SIZE = 1024
    DEFAULT_TRAFFIC_RATE = 1.0
    
    PACKET_TIMEOUT = 5.0
    RECEIVE_TIMEOUT = 10.0
