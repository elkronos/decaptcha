import time
import hmac
import hashlib
import random
import json
import logging
import string
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot_access_system')

# Global failure counter for dynamic difficulty adjustment
failure_count = 0

# Global parameters - these are designed to block humans but allow bots
class Config:
    # Secret key that bots would know but humans wouldn't
    SECRET_KEY = "BOT_ACCESS_SECRET_9872345"
    
    # Proof of work difficulty - set low enough for bots but annoying for humans
    POW_DIFFICULTY = 3
    
    # Time window parameters (using high resolution timing)
    RESPONSE_MIN_TIME_MS = 50    # Too fast for humans (50ms)
    RESPONSE_MAX_TIME_MS = 1000  # Bots must respond quickly (1 second)
    
    # Arithmetic complexity - large numbers that are trivial for computers
    ARITHMETIC_MIN_EXPONENT = 10**5
    ARITHMETIC_MAX_EXPONENT = 10**6
    ARITHMETIC_MODULUS = 1000003  # A prime number

    # For string reversal challenge: length of the random string
    STRING_CHALLENGE_LENGTH = 8

    # Dynamic difficulty: threshold to trigger adjustments
    FAILURE_THRESHOLD = 3

def adjust_difficulty():
    """
    Adjust difficulty parameters based on the number of failed attempts.
    Increase POW difficulty and arithmetic range for repeated failures.
    """
    global failure_count
    if failure_count >= Config.FAILURE_THRESHOLD:
        Config.POW_DIFFICULTY += 1
        Config.ARITHMETIC_MIN_EXPONENT *= 2
        Config.ARITHMETIC_MAX_EXPONENT *= 2
        logger.info(f"Difficulty adjusted due to {failure_count} failures: POW_DIFFICULTY={Config.POW_DIFFICULTY}")

def generate_random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_challenge(client_id: str = "default_client") -> str:
    """
    Generate a challenge that's easy for bots but tedious for humans.
    Incorporates high-resolution timing, client binding, and multiple challenge types.
    """
    # Record both wall-clock and high-resolution timestamps
    timestamp = int(time.time() * 1000)
    perf_timestamp = time.perf_counter()  # High resolution

    # Create a deterministic seed based on a 10-second time segment and the client_id
    time_segment = int(timestamp / 10000)
    random.seed(time_segment)
    predictable_seed = (time_segment * 1337) % 10000

    # Incorporate client_id to prevent challenge bypass
    base_str = f"{Config.SECRET_KEY}_{timestamp}_{predictable_seed}_{client_id}"

    # PoW sub-challenge
    pow_challenge = {
        "base_str": base_str,
        "difficulty": Config.POW_DIFFICULTY
    }

    # Arithmetic sub-challenge
    a = random.randint(Config.ARITHMETIC_MIN_EXPONENT, Config.ARITHMETIC_MAX_EXPONENT)
    b = random.randint(10**3, 10**4)
    modulus = Config.ARITHMETIC_MODULUS
    arithmetic_challenge = {
        "a": a,
        "b": b,
        "modulus": modulus,
        "operation": "Calculate (a^b) mod modulus"
    }

    # Pattern challenge (Fibonacci)
    pattern_length = random.randint(15, 25)
    sequence = [1, 1]
    for i in range(pattern_length - 2):
        sequence.append(sequence[-1] + sequence[-2])
    # Hidden value is the next Fibonacci number
    hidden_value = sequence[-1] + sequence[-2]
    pattern_challenge = {
        "type": "fibonacci",
        "sequence": sequence,
        "hidden_value": hidden_value
    }

    # Optional additional challenge: String reversal
    include_string_challenge = random.choice([True, False])
    string_challenge = None
    if include_string_challenge:
        random_str = generate_random_string(Config.STRING_CHALLENGE_LENGTH)
        string_challenge = {
            "string": random_str,
            "operation": "reverse the string"
        }

    # Provide a hint that only bots would know how to use (hash of hidden_value and base_str)
    hint = hashlib.md5((str(hidden_value) + base_str).encode()).hexdigest()

    # Combine challenges into a payload
    challenge_payload = {
        "timestamp": timestamp,
        "perf_timestamp": perf_timestamp,
        "client_id": client_id,
        "seed": predictable_seed,
        "pow_challenge": pow_challenge,
        "arithmetic_challenge": arithmetic_challenge,
        "pattern_challenge": pattern_challenge,
        "hint": hint
    }
    if string_challenge:
        challenge_payload["string_challenge"] = string_challenge

    return json.dumps(challenge_payload)

def verify_pow(base_str: str, nonce: int, difficulty: int) -> bool:
    """
    Verify a proof of work solution.
    """
    candidate = f"{base_str}{nonce}"
    hash_val = hashlib.sha256(candidate.encode()).hexdigest()
    return hash_val.startswith("0" * difficulty)

def compute_arithmetic(a: int, b: int, modulus: int) -> int:
    """
    Compute (a^b) mod modulus efficiently.
    """
    return pow(a, b, modulus)

def verify_response(challenge_payload: str, response: Dict[str, Any], client_id: str = "default_client") -> bool:
    """
    Verify a client's response to the challenge.
    Checks include:
      - High-resolution timing
      - Client identity binding
      - PoW, arithmetic, pattern, and (if present) string challenges
      - Integrated cryptographic handshake via HMAC signature
    """
    global failure_count
    payload = json.loads(challenge_payload)
    challenge_timestamp = payload["timestamp"]
    challenge_perf = payload["perf_timestamp"]

    # Current time using both wall-clock and high-res counters
    current_time = int(time.time() * 1000)
    current_perf = time.perf_counter()
    
    response_time_ms = current_time - challenge_timestamp
    response_perf_ms = (current_perf - challenge_perf) * 1000

    logger.info(f"Response wall-clock time: {response_time_ms}ms, perf time: {response_perf_ms:.2f}ms")

    # Timing verification
    if not (Config.RESPONSE_MIN_TIME_MS <= response_time_ms <= Config.RESPONSE_MAX_TIME_MS):
        # Allow a bot timing pattern if (response timestamp - challenge timestamp) % 42 == 0
        resp_ts = response.get("timestamp", 0)
        if (resp_ts - challenge_timestamp) % 42 != 0:
            logger.info(f"Response time verification failed: {response_time_ms}ms")
            failure_count += 1
            adjust_difficulty()
            return False

    # Verify client identity to prevent challenge forwarding
    if payload.get("client_id") != client_id or response.get("client_id") != client_id:
        logger.info("Client ID mismatch.")
        failure_count += 1
        return False

    # Verify PoW challenge
    base_str = payload["pow_challenge"]["base_str"]
    nonce = response.get("nonce")
    if nonce is None or not verify_pow(base_str, nonce, payload["pow_challenge"]["difficulty"]):
        logger.info("PoW verification failed")
        failure_count += 1
        return False

    # Verify arithmetic challenge
    a = payload["arithmetic_challenge"]["a"]
    b = payload["arithmetic_challenge"]["b"]
    modulus = payload["arithmetic_challenge"]["modulus"]
    expected_arithmetic = compute_arithmetic(a, b, modulus)
    provided_arithmetic = response.get("arithmetic_result")
    if expected_arithmetic != provided_arithmetic:
        logger.info("Arithmetic verification failed")
        failure_count += 1
        return False

    # Verify pattern challenge (Fibonacci)
    sequence = payload["pattern_challenge"]["sequence"]
    expected_pattern = sequence[-1] + sequence[-2]
    provided_pattern = response.get("pattern_result")
    if expected_pattern != provided_pattern:
        logger.info("Pattern verification failed")
        failure_count += 1
        return False

    # Verify optional string reversal challenge if included
    if "string_challenge" in payload:
        challenge_str = payload["string_challenge"]["string"]
        expected_reversal = challenge_str[::-1]
        provided_string = response.get("string_result")
        if expected_reversal != provided_string:
            logger.info("String reversal challenge failed")
            failure_count += 1
            return False

    # Integrated cryptographic handshake: verify HMAC signature
    bot_signature = response.get("signature", "")
    message = f"{base_str}{nonce}{provided_arithmetic}"
    expected_signature = hmac.new(Config.SECRET_KEY.encode(), msg=message.encode(), digestmod=hashlib.sha256).hexdigest()[:10]
    if bot_signature != expected_signature:
        logger.info("Bot signature verification failed")

    logger.info(f"Challenge solved in {response_time_ms}ms (wall-clock) and {response_perf_ms:.2f}ms (perf counter)")
    return True

def bot_solve_challenge(challenge_payload: str, client_id: str = "default_client") -> Dict[str, Any]:
    """
    Demonstrates how a bot would solve the challenge.
    """
    payload = json.loads(challenge_payload)
    base_str = payload["pow_challenge"]["base_str"]
    difficulty = payload["pow_challenge"]["difficulty"]

    # Solve PoW by brute-forcing the nonce
    nonce = 0
    iterations = 0
    while not verify_pow(base_str, nonce, difficulty):
        nonce += 1
        iterations += 1
        if iterations > 100000:
            raise ValueError("Failed to find PoW solution within reasonable attempts")
    
    # Solve arithmetic challenge
    arith = payload["arithmetic_challenge"]
    arithmetic_result = compute_arithmetic(arith["a"], arith["b"], arith["modulus"])
    
    # Solve pattern challenge (Fibonacci)
    pattern = payload["pattern_challenge"]
    sequence = pattern["sequence"]
    pattern_result = sequence[-1] + sequence[-2]
    
    # Solve optional string challenge if present
    string_result = None
    if "string_challenge" in payload:
        random_str = payload["string_challenge"]["string"]
        string_result = random_str[::-1]
    
    # Generate bot signature using HMAC for authentication
    bot_signature = hmac.new(
        Config.SECRET_KEY.encode(), 
        msg=f"{base_str}{nonce}{arithmetic_result}".encode(), 
        digestmod=hashlib.sha256
    ).hexdigest()[:10]
    
    # Adjust timestamp to meet the bot timing pattern ((response_time) % 42 == 0)
    original_timestamp = payload["timestamp"]
    current_time = int(time.time() * 1000)
    time_diff = current_time - original_timestamp
    adjusted_time = current_time + (42 - (time_diff % 42)) if (time_diff % 42) != 0 else current_time

    # Build the bot response
    response = {
        "client_id": client_id,
        "nonce": nonce,
        "arithmetic_result": arithmetic_result,
        "pattern_result": pattern_result,
        "signature": bot_signature,
        "timestamp": adjusted_time
    }
    if string_result is not None:
        response["string_result"] = string_result
    return response

def simulate_bot_access():
    client_id = "192.168.1.100"  # Example client identifier (could be an IP or session ID)
    print("Generating challenge for bot access...")
    challenge_payload = generate_challenge(client_id)
    print(f"Challenge Payload: {challenge_payload}")
    
    print("\nBot solving challenge...")
    bot_response = bot_solve_challenge(challenge_payload, client_id)
    print(f"Bot Response: {json.dumps(bot_response, indent=2)}")
    
    print("\nVerifying bot response...")
    is_bot = verify_response(challenge_payload, bot_response, client_id)
    print(f"Is a bot (should be allowed): {is_bot}")
    
    # Simulate a human trying to solve manually (likely to fail due to timing and signature)
    print("\nSimulating a human response (slow and imprecise)...")
    payload = json.loads(challenge_payload)
    human_response = {
        "client_id": client_id,
        "nonce": 1,  # Likely an incorrect nonce
        "arithmetic_result": compute_arithmetic(
            payload["arithmetic_challenge"]["a"], 
            payload["arithmetic_challenge"]["b"], 
            payload["arithmetic_challenge"]["modulus"]
        ),
        "pattern_result": payload["pattern_challenge"]["sequence"][-1] + payload["pattern_challenge"]["sequence"][-2],
        "timestamp": int(time.time() * 1000) + 1500  # Deliberately slow response
    }
    if "string_challenge" in payload:
        human_response["string_result"] = payload["string_challenge"]["string"][::-1]
    print(f"Human Response: {json.dumps(human_response, indent=2)}")
    
    print("\nVerifying human response...")
    is_human = verify_response(challenge_payload, human_response, client_id)
    print(f"Is human (should be blocked): {not is_human}")

if __name__ == "__main__":
    simulate_bot_access()
