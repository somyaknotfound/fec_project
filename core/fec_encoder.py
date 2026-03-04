"""
FEC Encoder — GF(256) Erasure Coding
=====================================
Builds a systematic encoding matrix using a Cauchy construction so that
every parity packet is a *unique* linear combination of the data packets
over GF(256).  This means up to `n_parity` lost packets can be recovered.

Systematic code layout:
    encoded[0 .. n_data-1]   = original data packets  (unchanged)
    encoded[n_data .. total-1] = parity packets

How encoding works (per byte position):
    parity_j[pos] = SUM_over_i( C[j][i] * data_i[pos] )   in GF(256)

The Cauchy matrix C is chosen such that *every* square sub-matrix formed by
picking any n_data rows out of the full (n_data+n_parity) x n_data matrix
is invertible — which is exactly the property needed for erasure recovery.
"""

from core.galois import gf_mul

class FECEncoder:
    def __init__(self, n_data_packets=4, n_parity_packets=4):
        self.n_data = n_data_packets
        self.n_parity = n_parity_packets
        self.total = n_data_packets + n_parity_packets

        # Build the encoding matrix (only the parity rows).
        # Full matrix = [ I (identity, n_data rows) ]
        #               [ C (Cauchy,   n_parity rows) ]
        # We only need C for encoding since the data rows are identity.
        self.cauchy_matrix = self._build_cauchy_matrix()

    # ------------------------------------------------------------------
    # Matrix construction
    # ------------------------------------------------------------------
    def _build_cauchy_matrix(self):
        """
        Cauchy matrix:  C[j][i] = 1 / (x_j XOR y_i)   in GF(256)
        where x and y are two sets of *distinct* field elements that
        don't overlap.

        We pick:
            y_i = i                     for i in 0 .. n_data-1
            x_j = n_data + j            for j in 0 .. n_parity-1

        Because all values are distinct and x ∩ y = ∅, every square
        sub-matrix of the resulting Cauchy matrix is guaranteed to be
        invertible (a well-known property of Cauchy matrices over finite
        fields).
        """
        from core.galois import gf_inv

        matrix = []
        for j in range(self.n_parity):
            row = []
            for i in range(self.n_data):
                # x_j XOR y_i  — guaranteed non-zero because x_j ≠ y_i
                val = (self.n_data + j) ^ i
                row.append(gf_inv(val))
            matrix.append(row)
        return matrix

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------
    def encode_block(self, data_packets):
        """
        Encode a block of n_data packets.

        Parameters
        ----------
        data_packets : list[bytes]
            Exactly n_data byte-strings.

        Returns
        -------
        list[bytes]
            n_data data packets (unchanged) followed by n_parity parity
            packets.  All packets are padded to the same length.
        """
        assert len(data_packets) == self.n_data, \
            f"Expected {self.n_data} data packets, got {len(data_packets)}"

        # Pad all packets to the same length
        max_len = max(len(p) for p in data_packets)
        padded = [p + b'\x00' * (max_len - len(p)) for p in data_packets]

        # Start result with the original data packets (systematic code)
        result = list(padded)

        # Generate each parity packet
        for j in range(self.n_parity):
            parity = bytearray(max_len)
            for pos in range(max_len):
                val = 0
                for i in range(self.n_data):
                    # parity[pos] += C[j][i] * data_i[pos]  in GF(256)
                    val ^= gf_mul(self.cauchy_matrix[j][i], padded[i][pos])
                parity[pos] = val
            result.append(bytes(parity))

        return result

    # ------------------------------------------------------------------
    # Info helpers
    # ------------------------------------------------------------------
    def get_overhead(self):
        """Return FEC overhead as a percentage."""
        return (self.n_parity / self.n_data) * 100

    def get_encoding_matrix(self):
        """
        Return the full (n_data+n_parity) x n_data encoding matrix.
        Top half = identity (data rows), bottom half = Cauchy (parity rows).
        Used by the decoder to recover lost packets.
        """
        # Identity rows for data packets
        identity = []
        for i in range(self.n_data):
            row = [0] * self.n_data
            row[i] = 1
            identity.append(row)
        return identity + self.cauchy_matrix
