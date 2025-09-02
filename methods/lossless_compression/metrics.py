import math

class CompressionMetrics:
    def __init__(self, original_size_bytes: int, original_length_chars: int = 0):
        """
        Menginisialisasi kelas CompressionMetrics dengan properti data asli.

        Args:
            original_size_bytes (int): Ukuran data asli dalam byte.
            original_length_chars (int): Jumlah karakter dalam data asli (untuk bit rate).
        """
        if original_size_bytes < 0:
            raise ValueError("Ukuran asli tidak boleh negatif.")
        self.original_size_bytes = original_size_bytes
        self.original_length_chars = original_length_chars

    @staticmethod
    def calculate_compression_ratio(original_size_bytes: int, compressed_size_bytes: int) -> float:
        """Menghitung Compression Ratio (CR). Semakin tinggi, semakin baik."""
        if compressed_size_bytes <= 0:
            return float('inf') # Rasio tak terhingga dianggap kompresi sempurna
        if original_size_bytes == 0:
            return 0.0
        return original_size_bytes / compressed_size_bytes

    @staticmethod
    def calculate_space_saving(original_size_bytes: int, compressed_size_bytes: int) -> float:
        """Menghitung Space Saving (SS) dalam persen. Semakin tinggi, semakin baik."""
        if original_size_bytes <= 0:
            return 0.0
        return (1 - (compressed_size_bytes / original_size_bytes)) * 100

    # @staticmethod
    # def calculate_bit_rate(compressed_size_bytes: int, original_length_chars: int) -> float | None:
    #     """Menghitung Bit Rate (bit per karakter). Semakin rendah, semakin baik."""
    #     if original_length_chars <= 0:
    #         return None
    #     compressed_size_bits = compressed_size_bytes * 8
    #     return compressed_size_bits / original_length_chars

    def calculate_all_metrics(self, compressed_size_bytes: int) -> dict:
        """
        Menghitung semua metrik kompresi untuk ukuran terkompresi yang diberikan.

        Args:
            compressed_size_bytes (int): Ukuran data terkompresi dalam byte.

        Returns:
            dict: Sebuah dictionary yang berisi semua metrik yang dihitung.
        """
        if compressed_size_bytes < 0:
            raise ValueError("Ukuran terkompresi tidak boleh negatif.")

        # Panggil metode statis untuk setiap perhitungan
        compression_ratio_value = self.calculate_compression_ratio(self.original_size_bytes, compressed_size_bytes)
        space_saving_percentage_value = self.calculate_space_saving(self.original_size_bytes, compressed_size_bytes)
        # bit_rate = self.calculate_bit_rate(compressed_size_bytes, self.original_length_chars)
        
        return compression_ratio_value, space_saving_percentage_value