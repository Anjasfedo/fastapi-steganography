def message_to_bit(message, bit_length=8):
    """
    Convert a text message into a binary string with a specified bit length per character.
    """
    return ''.join(format(ord(char), f'0{bit_length}b') for char in message)

def bit_to_message(bit_string, bit_length=8):
    """
    Convert a binary string back into a text message using the specified bit length per character.
    """
    if len(bit_string) % bit_length != 0:
        raise ValueError("Invalid bit string length for the specified bit length.")

    chars = [bit_string[i:i+bit_length] for i in range(0, len(bit_string), bit_length)]
    return ''.join(chr(int(char, 2)) for char in chars)