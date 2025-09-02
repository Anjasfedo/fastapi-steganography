class LZW:
    def __init__(self):
        self.dictionary_size = 256
        self.bit_size = 8 

    def compress(self, input_string):
        """
        Compress a string using LZW algorithm and return a self.bit_size-bit encoded bit string.
        """
        if not input_string:
            return ""

        # Initialize dictionary
        dictionary = {chr(i): i for i in range(self.dictionary_size)}
        next_code = self.dictionary_size

        current_string = ""
        compressed_data = []

        for char in input_string:
            current_string_plus_char = current_string + char
            if current_string_plus_char in dictionary:
                current_string = current_string_plus_char
            else:
                compressed_data.append(dictionary[current_string])
                dictionary[current_string_plus_char] = next_code
                next_code += 1

                # Adjust bit_size if the dictionary exceeds the current bit size limit
                if next_code >= (1 << self.bit_size):
                    self.bit_size += 1

                current_string = char

        if current_string:
            compressed_data.append(dictionary[current_string])
        # Convert compressed codes to self.bit_size-bit binary strings
        bit_output = ''.join(format(code, f'0{self.bit_size}b') for code in compressed_data)
        return bit_output

    def decompress(self, compressed_bits):
        """
        Decompress a self.bit_size-bit encoded bit string back into the original message.
        """
        if not compressed_bits:
            return ""

        # Convert self.bit_size-bit binary chunks back to integer codes
        compressed_data = [int(compressed_bits[i:i + self.bit_size], 2) for i in range(0, len(compressed_bits), self.bit_size)]

        # Initialize dictionary
        dictionary = {i: chr(i) for i in range(self.dictionary_size)}
        next_code = self.dictionary_size

        current_code = compressed_data[0]
        decompressed_string = dictionary[current_code]
        current_string = decompressed_string

        for code in compressed_data[1:]:
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                entry = current_string + current_string[0]
            decompressed_string += entry

            dictionary[next_code] = current_string + entry[0]
            next_code += 1

            # Adjust bit_size if the dictionary exceeds the current bit size limit
            if next_code >= (1 << self.bit_size):
                self.bit_size += 1

            current_string = entry

        return decompressed_string
