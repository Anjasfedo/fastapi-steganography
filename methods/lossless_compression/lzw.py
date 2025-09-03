import math


class LZW:
    def _get_initial_dictionary(self):
        """Membuat kamus awal dengan 256 karakter ASCII."""
        return {chr(i): i for i in range(256)}

    def _determine_max_code(self, input_string: str) -> int:
        """
        LANGKAH 1: Menjalankan simulasi kompresi untuk menemukan kode terbesar
        yang akan dihasilkan, yang akan menentukan lebar bit yang dibutuhkan.
        """
        dictionary = self._get_initial_dictionary()
        next_code = 256
        current_string = ""

        for char in input_string:
            current_string_plus_char = current_string + char
            if current_string_plus_char in dictionary:
                current_string = current_string_plus_char
            else:
                # Tambahkan entri baru ke kamus
                dictionary[current_string_plus_char] = next_code
                next_code += 1
                current_string = char

        # next_code - 1 adalah kode maksimum yang digunakan
        return next_code - 1

    def _perform_compression(self, input_string: str) -> list[int]:
        """
        LANGKAH 2: Menjalankan kompresi sebenarnya dan menghasilkan list of codes.
        """
        dictionary = self._get_initial_dictionary()
        next_code = 256
        current_string = ""
        compressed_codes = []

        for char in input_string:
            current_string_plus_char = current_string + char
            if current_string_plus_char in dictionary:
                current_string = current_string_plus_char
            else:
                compressed_codes.append(dictionary[current_string])
                dictionary[current_string_plus_char] = next_code
                next_code += 1
                current_string = char

        if current_string:
            compressed_codes.append(dictionary[current_string])

        return compressed_codes

    def compress(self, input_string: str) -> tuple[str, int]:
        """
        Mengompresi string menggunakan LZW dua-langkah.

        Returns:
            tuple[str, int]: String biner hasil kompresi dan lebar bit yang digunakan.
        """
        if not input_string:
            return "", 8

        # Langkah 1: Tentukan kode maksimum untuk mendapatkan lebar bit
        max_code = self._determine_max_code(input_string)
        # Hitung lebar bit yang diperlukan. Default minimal 8.
        bit_width = max(8, math.ceil(math.log2(max_code + 1)))

        # Langkah 2: Lakukan kompresi
        compressed_codes = self._perform_compression(input_string)

        # Format output menjadi string biner dengan lebar bit yang sudah ditentukan
        bit_output = ''.join(
            format(code, f'0{bit_width}b') for code in compressed_codes)

        return bit_output, bit_width

    def decompress(self, compressed_bits: str, bit_width: int) -> str:
        """
        Mendekompresi string biner LZW menggunakan lebar bit yang diberikan.
        """
        if not compressed_bits:
            return ""

        # Potong string biner menjadi kode-kode integer
        codes = [
            int(compressed_bits[i:i + bit_width], 2)
            for i in range(0, len(compressed_bits), bit_width)
        ]

        dictionary = {i: chr(i) for i in range(256)}
        next_code = 256

        # Proses dekompresi
        current_string = dictionary.get(codes[0], "")
        if not current_string:
            raise ValueError("Compressed data contains invalid code.")

        decompressed_string = current_string

        for code in codes[1:]:
            entry = ""
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                entry = current_string + current_string[0]
            else:
                raise ValueError(f"Bad compressed code: {code}")

            decompressed_string += entry
            dictionary[next_code] = current_string + entry[0]
            next_code += 1
            current_string = entry

        return decompressed_string
