def encode_with_padding_info(bits):
    # Step 1: Calculate the padding needed to make the bit length a multiple of 8
    padding_needed = (8 - len(bits) % 8) % 8  # Number of bits to pad

    # Step 2: Embed the padding length in the first 8 bits
    padding_length_bits = format(padding_needed, '08b')  # 8-bit binary representation of padding length

    # Step 3: Pad the message with zeroes (if any padding is needed)
    padded_bits = bits + '0' * padding_needed

    # Step 4: Combine the padding information and the padded bits
    full_message = padding_length_bits + padded_bits

    # Step 5: Convert the full message into 8-bit chunks and encode as ASCII
    encoded_chars = [chr(int(full_message[i:i+8], 2)) for i in range(0, len(full_message), 8)]

    return ''.join(encoded_chars)

def decode_with_padding_info(encoded):
    # Step 1: Convert the encoded ASCII string back to a bit string
    bits = ''.join(format(ord(c), '08b') for c in encoded)

    # Step 2: Extract the first 8 bits as padding length
    padding_length_bits = bits[:8]
    padding_length = int(padding_length_bits, 2)

    # Step 3: Extract the actual message bits (without the padding)
    message_bits = bits[8:]  # Exclude the first 8 bits (padding length)

    # Step 4: Remove the padding bits
    message_bits = message_bits[:-padding_length] if padding_length > 0 else message_bits

    return message_bits