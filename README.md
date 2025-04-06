# Decaptcha: Bot Access Challenge System

This repository implements an advanced challenge-response system designed to distinguish bots from human users by issuing puzzles that are trivial for automated algorithms yet tedious for humans. The system leverages high-resolution timing, dynamic difficulty adjustments, cryptographic handshakes, and multiple puzzle types to ensure robust access control.

---

## Features

- **High-Resolution Timing Enforcement:**  
  Utilizes both wall-clock timestamps and Python's `time.perf_counter()` to capture precise response times. Bots are expected to solve puzzles within a very narrow time window, while human responses typically fall outside this range.

- **Dynamic Difficulty Adjustment:**  
  Monitors failure counts and adjusts the complexity of the challenges accordingly. For example, after multiple failed attempts, the Proof-of-Work (PoW) difficulty is incremented and arithmetic challenge ranges are widened, making manual solving even more difficult.

- **Integrated Cryptographic Handshake:**  
  Incorporates HMAC-based signatures using a secret key known only to legitimate bots. This additional check ensures that even if a human manages to solve the puzzle, they cannot generate the correct signature without the secret.

- **Behavior Logging and Analysis:**  
  Detailed logs capture metrics such as response times (both wall-clock and high-resolution), client identity, and specific failure reasons. These logs can be analyzed over time to identify suspicious activity and refine challenge parameters.

- **Client Identity Binding:**  
  The challenges are tied to a unique `client_id` (such as an IP address or session ID) to prevent challenge reuse or bypass through multiple clients.

- **Multiple Challenge Types:**  
  Supports a mix of puzzles, including:
  - **Proof of Work (PoW):** A simple hash-based puzzle.
  - **Arithmetic Challenge:** A modular exponentiation problem.
  - **Pattern Challenge:** A Fibonacci sequence puzzle.
  - **Optional String Reversal Challenge:** Randomly included to further complicate manual solving.

---

## Requirements

- **Python 3.x**  
  All libraries used (e.g., `time`, `hmac`, `hashlib`, `random`, `json`, `logging`, `string`) are part of the Python Standard Library, so no additional installations are necessary.

---

## Installation & Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/decaptcha.git
   cd decaptcha
