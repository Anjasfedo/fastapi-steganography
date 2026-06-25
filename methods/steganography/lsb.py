from PIL import Image
import numpy as np

class LeastSignificantBit:
    def __init__(self, k_val=1):
        """
        Initialize the LeastSignificantBit class.

        Args:
            k_val (int): The number of least significant bits to use for embedding.
        """
        if not (1 <= k_val <= 8):
            raise ValueError("k_val must be between 1 and 8.")
        self.k_val = k_val

    def calculate_max_message_size(self, image_path):
        """
        Menghitung jumlah maksimum karakter yang dapat disimpan dalam gambar,
        dan melempar error jika kapasitas melebihi batas header 32-bit.
        """
        image = Image.open(image_path).convert("RGB")
        img_data = np.array(image)

        height, width, channels = img_data.shape
        total_capacity_bits = height * width * channels * self.k_val

        HEADER_SIZE_BITS = 32
        usable_bits = total_capacity_bits - HEADER_SIZE_BITS

        # --- PERUBAHAN UTAMA DI SINI ---
        # Batas maksimum teoretis yang bisa dideskripsikan oleh header 32-bit
        # (2**32 - 1, bukan 2**32 - 32)
        MAX_BITS_SUPPORTED_BY_HEADER = (2**32) - 1

        # 1. Periksa apakah kapasitas gambar melebihi batas header
        if usable_bits > MAX_BITS_SUPPORTED_BY_HEADER:
            raise ValueError(
                f"Kapasitas gambar ({usable_bits} bit) melebihi batas maksimal "
                f"yang didukung oleh header 32-bit ({MAX_BITS_SUPPORTED_BY_HEADER} bit)."
            )

        # 2. Jika tidak, lanjutkan seperti biasa
        if usable_bits < 0:
            usable_bits = 0
            
        max_chars = usable_bits // 8

        return max_chars, usable_bits, width, height

    def message_to_bits(self, message_bits):
        """
        Convert a string message to a bit string, using a dynamically determined bit length for the message size.
        """
        message_length = len(message_bits)

        message_length_bits = format(message_length, f'032b')

        return message_length_bits + message_bits

    def bits_to_message(self, bits):
        """
        Convert a bit string back to a human-readable message, using dynamically encoded message length.
        """
        message_length_bit = bits[:32]

        message_length = int(message_length_bit, 2)

        message_bits = bits[32:32 + message_length]

        return message_bits

    @staticmethod
    def change_n_lsb(binary_number, new_lsbs, k_val):
        """
        Modify the n least significant bits (LSBs) of a binary number.
        """
        binary_literal = int(new_lsbs, 2)
        mask = ~((1 << k_val) - 1) & 0xFF
        return (binary_number & mask) | binary_literal

    def embed_message(self, input_image_path, output_image_path, message):
        """
        Modify pixel values of an image to embed a message.
        """
        message_bits = self.message_to_bits(message)

        image = Image.open(input_image_path).convert("RGB")
        img_data = np.array(image)

        height, width, channels = img_data.shape
        _, max_bits, _, _ = self.calculate_max_message_size(input_image_path)
        if len(message_bits) - 32 > max_bits:
            raise ValueError(f"Message too long! max_bits: {max_bits} bits, Message: {len(message_bits)} bits.")

        bit_idx = 0
        for h in range(height):
            for w in range(width):
                for c in range(channels):
                    if bit_idx < len(message_bits):
                        original_value = img_data[h, w, c]
                        bits_to_embed = message_bits[bit_idx:bit_idx + self.k_val]
                        bits_to_embed = bits_to_embed.ljust(self.k_val, '0')

                        color_type = "Red" if c == 0 else "Green" if c == 1 else "Blue"

                        img_data[h, w, c] = self.change_n_lsb(original_value, bits_to_embed, self.k_val)

                        bit_idx += self.k_val
                if bit_idx >= len(message_bits):
                    break
            if bit_idx >= len(message_bits):
                break

        stego_image = Image.fromarray(img_data)
        stego_image.save(output_image_path, format="PNG")
        return stego_image

    def extract_message(self, stego_image_path):
        """
        Extract a hidden message from an image that uses LSB encoding.
        """
        image = Image.open(stego_image_path).convert("RGB")
        img_data = np.array(image)

        height, width, channels = img_data.shape
        extracted_bits = ""

        for h in range(height):
            for w in range(width):
                for c in range(channels):
                    pixel_value = img_data[h, w, c]
                    lsb_bits = format(pixel_value, '08b')[-self.k_val:]
                    extracted_bits += lsb_bits
        return self.bits_to_message(extracted_bits)