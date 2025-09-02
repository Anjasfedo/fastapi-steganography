def pad_message_to_capacity(message: str, max_chars: int) -> str:
    """
    Mengulang sebuah pesan hingga panjangnya mencapai kapasitas maksimum yang ditentukan.

    Args:
        message (str): Pesan asli yang akan diulang.
        max_chars (int): Jumlah karakter target.

    Returns:
        str: Pesan baru yang sudah diulang sesuai kapasitas.
    
    Raises:
        ValueError: Jika pesan input kosong.
    """
    # Validasi untuk memastikan pesan tidak kosong
    if not message or len(message) == 0:
        raise ValueError("Pesan tidak boleh kosong untuk proses padding.")
    
    repetitions = max_chars // len(message)
    remainder = max_chars % len(message)
    padded_message = (message * repetitions) + message[:remainder]
    
    return padded_message