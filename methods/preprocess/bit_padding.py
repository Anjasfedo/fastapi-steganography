def encode_with_padding_info(bits):
    # Step 1: Calculate how much padding is needed to make the bit length a multiple of 8
    padding_needed = (8 - len(bits) % 8) % 8  # Number of bits to pad
    # Step 2: Define the padding information based on padding_needed
    # Padding info:
    # 0 -> add 5 bits, 1 -> add 4 bits, 2 -> add 3 bits, etc.
    padding_info_map = {
        0: 5,
        1: 6,  # '001' -> remove 4 bits
        2: 7,  # '010' -> remove 3 bits
        3: 8,  # '011' -> remove 2 bits
        4: 1,  # '100' -> remove 1 bit
        5: 2,  # '101' -> no padding
        6: 3,  # '110' -> no padding
        7: 4,  # '111' -> no padding
        8: 5,
    }

    # Step 3: Select the correct padding based on padding_needed
    padding_info = padding_info_map[padding_needed]

    # Step 4: Create the first 3 bits to store the padding info
    padding_info_bits = format(padding_needed, '03b')  # 3-bit binary representation of padding info

    # Step 5: Combine the padding information (3 bits) and the original bits
    full_message = padding_info_bits + bits + '0' * padding_info
    # Step 6: Convert the full message into 8-bit chunks and encode as ASCII
    encoded_chars = [chr(int(full_message[i:i+8], 2)) for i in range(0, len(full_message), 8)]

    return ''.join(encoded_chars)

def decode_with_padding_info(encoded):
    # Step 1: Convert the encoded ASCII string back to a bit string
    bits = ''.join(format(ord(c), '08b') for c in encoded)

    # Step 2: Extract the first 3 bits as padding length information
    padding_info_bits = bits[:3]
    padding_info = int(padding_info_bits, 2)

    # Step 3: Extract the actual message bits (without the padding)
    message_bits = bits[3:]  # Exclude the first 3 bits (padding length info)

    # Step 4: Define the padding map to calculate how many bits to remove
    padding_info_map = {
        0: 5,
        1: 6,  # '001' -> remove 4 bits
        2: 7,  # '010' -> remove 3 bits
        3: 8,  # '011' -> remove 2 bits
        4: 1,  # '100' -> remove 1 bit
        5: 2,  # '101' -> no padding
        6: 3,  # '110' -> no padding
        7: 4,  # '111' -> no padding
        8: 5,
    }


    # Step 5: Remove the padding bits (remove exactly the number of padding bits)
    message_bits = message_bits[:-padding_info_map[padding_info]]

    return message_bits