from num2words import num2words

def number_to_words_id(number: int) -> str:
    """
    Mengubah angka integer menjadi format terbilang dalam Bahasa Indonesia.
    Contoh: 125 -> "seratus dua puluh lima"

    Args:
        number (int): Angka yang akan diubah.

    Returns:
        str: Representasi teks dari angka tersebut.
    """
    try:
        # Menggunakan num2words dengan locale Bahasa Indonesia ('id')
        return num2words(number, lang='id')
    except Exception:
        # Fallback jika terjadi error
        return str(number)