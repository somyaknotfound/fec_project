"""
Galois Field GF(256) Arithmetic
===============================
Used for Reed-Solomon-style erasure coding. All operations (add, multiply, 
divide, inverse) are done in GF(2^8) with the irreducible polynomial 
x^8 + x^4 + x^3 + x^2 + 1  (0x11D, same as used in AES and QR codes).

Key concepts:
  - Addition in GF(256) = XOR  (no carry)
  - Multiplication uses log/exp tables for speed
  - Every non-zero element has a multiplicative inverse

This module is self-contained — no external libraries required.
"""

# ---------------------------------------------------------------------------
# Primitive polynomial: x^8 + x^4 + x^3 + x^2 + 1 = 0x11D
# Generator (primitive element): alpha = 2
# ---------------------------------------------------------------------------
PRIM_POLY = 0x11D

# Pre-compute log and exp (anti-log) tables for fast multiply/divide
# exp_table[i] = alpha^i  mod PRIM_POLY
# log_table[v] = i  such that alpha^i = v   (log_table[0] is undefined)
_exp_table = [0] * 512   # double-sized to avoid modular indexing
_log_table = [0] * 256

def _init_tables():
    """Build log/exp lookup tables once at import time."""
    x = 1
    for i in range(255):
        _exp_table[i] = x
        _log_table[x] = i
        x <<= 1                       # multiply by alpha (=2)
        if x & 0x100:                  # if x >= 256
            x ^= PRIM_POLY            # reduce modulo primitive polynomial
    # Extend exp table so we can index up to 510 without modular arithmetic
    for i in range(255, 512):
        _exp_table[i] = _exp_table[i - 255]

_init_tables()


# ---------------------------------------------------------------------------
# Core GF(256) operations
# ---------------------------------------------------------------------------

def gf_add(a, b):
    """Addition in GF(256) = XOR."""
    return a ^ b

# Subtraction is the same as addition in GF(2^n)
gf_sub = gf_add

def gf_mul(a, b):
    """Multiplication in GF(256) using log/exp tables."""
    if a == 0 or b == 0:
        return 0
    return _exp_table[_log_table[a] + _log_table[b]]

def gf_div(a, b):
    """Division in GF(256):  a / b."""
    if b == 0:
        raise ZeroDivisionError("Division by zero in GF(256)")
    if a == 0:
        return 0
    return _exp_table[(_log_table[a] - _log_table[b]) % 255]

def gf_inv(a):
    """Multiplicative inverse in GF(256):  1 / a."""
    if a == 0:
        raise ZeroDivisionError("Zero has no inverse in GF(256)")
    return _exp_table[255 - _log_table[a]]


# ---------------------------------------------------------------------------
# Matrix helpers (lists of lists, entries are GF(256) bytes)
# ---------------------------------------------------------------------------

def gf_matrix_mul_vec(matrix, vec):
    """
    Multiply a matrix (list of rows) by a column vector.
    Each element of vec is a *byte value* (0-255).
    Returns a list of byte values.
    """
    result = []
    for row in matrix:
        val = 0
        for coeff, v in zip(row, vec):
            val ^= gf_mul(coeff, v)     # accumulate: GF add = XOR
        result.append(val)
    return result


def gf_matrix_invert(matrix):
    """
    Invert a square matrix over GF(256) using Gauss-Jordan elimination.
    Returns the inverted matrix, or raises ValueError if singular.
    
    Works in-place on a copy augmented with the identity.
    """
    n = len(matrix)
    # Augment with identity matrix  [M | I]
    aug = [row[:] + [int(i == j) for j in range(n)] for i, row in enumerate(matrix)]

    for col in range(n):
        # Find pivot (non-zero entry in this column)
        pivot_row = None
        for row in range(col, n):
            if aug[row][col] != 0:
                pivot_row = row
                break
        if pivot_row is None:
            raise ValueError("Matrix is singular — cannot invert")

        # Swap pivot row into position
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]

        # Scale pivot row so that the diagonal element becomes 1
        inv_pivot = gf_inv(aug[col][col])
        aug[col] = [gf_mul(v, inv_pivot) for v in aug[col]]

        # Eliminate all other rows in this column
        for row in range(n):
            if row != col and aug[row][col] != 0:
                factor = aug[row][col]
                aug[row] = [gf_add(aug[row][j], gf_mul(factor, aug[col][j]))
                            for j in range(2 * n)]

    # Extract the right half (the inverse)
    return [row[n:] for row in aug]
