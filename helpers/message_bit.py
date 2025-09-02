def message_to_bit(message: str) -> str:
    return ''.join(f'{ord(ch):08b}' for ch in message)

def bit_to_message(bits: str) -> str:
    if len(bits) % 8 != 0:
        bits = bits[:len(bits) - (len(bits) % 8)]
    return ''.join(chr(int(bits[i:i+8], 2)) for i in range(0, len(bits), 8))