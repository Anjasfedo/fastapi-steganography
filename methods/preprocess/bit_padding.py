def encode_with_padding_info(bits):
    # Step 1: Calculate how much padding is needed to make the bit length a multiple of 8
    padding_needed = (8 - len(bits) % 8) % 8  # Number of bits to pad
    print(padding_needed)

    # Skip padding if padding_needed is 0 or 8
    if padding_needed == 0 or padding_needed == 8:
        # Convert bits directly to 8-bit chunks and encode as ASCII
        encoded_chars = [chr(int(bits[i:i+8], 2))
                         for i in range(0, len(bits), 8)]
        return ''.join(encoded_chars)

    # Step 2: Define the padding information based on padding_needed
    # Padding info:
    # 1 -> add 6 bits, 2 -> add 7 bits, 3 -> add 8 bits, etc.
    padding_info_map = {
        1: 6,
        2: 7,
        3: 8,
        4: 1,
        5: 2,
        6: 3,
        7: 4,
    }

    # Step 3: Select the correct padding based on padding_needed
    padding_info = padding_info_map[padding_needed]

    # Step 4: Create the first 3 bits to store the padding info
    # 3-bit binary representation of padding info
    padding_info_bits = format(padding_needed, '03b')

    # Step 5: Combine the padding information (3 bits) and the original bits
    full_message = padding_info_bits + bits + '0' * padding_info
    # Step 6: Convert the full message into 8-bit chunks and encode as ASCII
    encoded_chars = [chr(int(full_message[i:i+8], 2))
                     for i in range(0, len(full_message), 8)]

    return ''.join(encoded_chars)


def decode_with_padding_info(encoded):
    # Step 1: Convert the encoded ASCII string back to a bit string
    bits = ''.join(format(ord(c), '08b') for c in encoded)

    # Check if this is an unpadded message (length is multiple of 8 and no padding info)
    if len(bits) % 8 == 0 and len(bits) >= 3:
        # Try to decode as unpadded first
        possible_padding_info = int(bits[:3], 2)
        if possible_padding_info == 0 or possible_padding_info == 8:
            # This might be an unpadded message, return the bits directly
            message_bits = bits
            print(message_bits)
            return message_bits

    # Step 2: Extract the first 3 bits as padding length information
    padding_info_bits = bits[:3]
    padding_info = int(padding_info_bits, 2)

    # Step 3: Extract the actual message bits (without the padding)
    message_bits = bits[3:]  # Exclude the first 3 bits (padding length info)

    # Step 4: Define the padding map to calculate how many bits to remove
    padding_info_map = {
        1: 6,
        2: 7,
        3: 8,
        4: 1,
        5: 2,
        6: 3,
        7: 4,
    }

    # Step 5: Remove the padding bits (remove exactly the number of padding bits)
    message_bits = message_bits[:-padding_info_map[padding_info]]
    # print('lorem')
    print(message_bits)
    return message_bits
