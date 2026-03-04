"""
FEC Decoder — GF(256) Erasure Recovery
=======================================
Given a block of (n_data + n_parity) packets where some are missing (None),
recovers the original n_data packets as long as at least n_data packets
were received (i.e., at most n_parity packets were lost).

Recovery algorithm:
    1. Build the full encoding matrix  E  (identity rows + Cauchy rows).
    2. Select only the rows corresponding to *received* packets → sub-matrix S.
    3. Invert S over GF(256)  →  S_inv.
    4. For each byte position, multiply S_inv by the column of received bytes
       to recover all n_data original data bytes at that position.
"""

from core.galois import gf_mul, gf_matrix_invert

class FECDecoder:
    def __init__(self, n_data_packets=4, n_parity_packets=4):
        self.n_data = n_data_packets
        self.n_parity = n_parity_packets
        self.total = n_data_packets + n_parity_packets

        # Build the full encoding matrix (same as encoder uses)
        self.encoding_matrix = self._build_encoding_matrix()

        # Statistics
        self.blocks_decoded = 0
        self.blocks_failed = 0
        self.packets_recovered = 0

    # ------------------------------------------------------------------
    # Encoding matrix (must match the encoder exactly)
    # ------------------------------------------------------------------
    def _build_encoding_matrix(self):
        """Reconstruct the full encoding matrix: identity + Cauchy."""
        from core.galois import gf_inv

        # Identity rows (data packets pass through unchanged)
        matrix = []
        for i in range(self.n_data):
            row = [0] * self.n_data
            row[i] = 1
            matrix.append(row)

        # Cauchy rows (parity packets)
        for j in range(self.n_parity):
            row = []
            for i in range(self.n_data):
                val = (self.n_data + j) ^ i
                row.append(gf_inv(val))
            matrix.append(row)

        return matrix

    # ------------------------------------------------------------------
    # Decoding
    # ------------------------------------------------------------------
    def decode_block(self, received_packets):
        """
        Attempt to decode a block.

        Parameters
        ----------
        received_packets : list[bytes | None]
            Length = n_data + n_parity.  None for lost packets.

        Returns
        -------
        (recovered_data, success) : (list[bytes] | None, bool)
            recovered_data has n_data packets if successful, else None.
        """
        total = self.n_data + self.n_parity

        # Count how many packets we actually received
        received_indices = [i for i in range(total)
                            if received_packets[i] is not None]

        if len(received_indices) < self.n_data:
            # Not enough packets to recover — unrecoverable
            self.blocks_failed += 1
            return None, False

        # Fast path: all data packets present → no math needed
        data_present = all(received_packets[i] is not None
                           for i in range(self.n_data))
        if data_present:
            self.blocks_decoded += 1
            return list(received_packets[:self.n_data]), True

        # ----- Recovery needed -----
        # Pick exactly n_data received packets to form a solvable system
        chosen = received_indices[:self.n_data]

        # Build the sub-matrix from the encoding matrix rows we received
        sub_matrix = [self.encoding_matrix[i][:] for i in chosen]

        # Invert over GF(256)
        try:
            inv_matrix = gf_matrix_invert(sub_matrix)
        except ValueError:
            # Should never happen with a proper Cauchy matrix, but guard
            self.blocks_failed += 1
            return None, False

        # Recover data byte-by-byte
        pkt_len = max(len(p) for p in received_packets if p is not None)
        recovered_data = [bytearray(pkt_len) for _ in range(self.n_data)]

        # Gather received packet bytes
        chosen_packets = [received_packets[i] for i in chosen]

        for pos in range(pkt_len):
            # Column vector of received bytes at this position
            col = [p[pos] if pos < len(p) else 0 for p in chosen_packets]

            # Multiply by inverse matrix to get original data bytes
            for d in range(self.n_data):
                val = 0
                for k in range(self.n_data):
                    val ^= gf_mul(inv_matrix[d][k], col[k])
                recovered_data[d][pos] = val

        # Count how many data packets were actually missing
        missing_data = sum(1 for i in range(self.n_data)
                           if received_packets[i] is None)
        self.packets_recovered += missing_data
        self.blocks_decoded += 1

        return [bytes(pkt) for pkt in recovered_data], True

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def get_statistics(self):
        """Return decoding statistics."""
        total = self.blocks_decoded + self.blocks_failed
        rate = (self.blocks_decoded / total * 100) if total > 0 else 0
        return {
            'blocks_decoded': self.blocks_decoded,
            'blocks_failed': self.blocks_failed,
            'total_blocks': total,
            'success_rate': rate,
            'packets_recovered': self.packets_recovered
        }
