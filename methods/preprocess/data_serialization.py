def serialize_record(record: dict, field_order: list[str]) -> str:
    """
    Mengubah satu dictionary menjadi string dengan format khusus.
    
    - Menggabungkan nilai field dengan separator '#'.
    - Mengganti spasi dengan '%'.
    - Urutan field ditentukan oleh parameter 'field_order'.

    Args:
        record (dict): Dictionary yang berisi data.
        field_order (list[str]): List of string yang menentukan urutan field.

    Returns:
        str: String yang sudah diformat.
    """
    # Ambil nilai dari dict sesuai urutan, gunakan string kosong jika key tidak ada
    field_values = [str(record.get(key, '')) for key in field_order]
    
    merged = '#'.join(field_values)
    return merged.replace(' ', '_').replace('/', '_') + '#'


def serialize_multiple_records(records: list[dict], field_order: list[str]) -> list[str]:
    """
    Menjalankan serialize_record untuk setiap dictionary dalam sebuah list.

    Args:
        records (list[dict]): List of dictionaries yang akan diproses.
        field_order (list[str]): List of string yang menentukan urutan field.

    Returns:
        list[str]: List of string yang sudah diformat.
    """
    return [serialize_record(record, field_order) for record in records]


def deserialize_record(record_string: str, field_order: list[str]) -> dict:
    """
    Mengubah satu string yang diformat khusus kembali menjadi dictionary.

    Args:
        record_string (str): String yang akan di-deserialize.
        field_order (list[str]): List of string yang menentukan urutan field.

    Returns:
        dict: Dictionary yang berisi data KTP.
    """
    try:
        # Lakukan proses kebalikannya: ganti '_' -> ' ', lalu pisah berdasarkan '#'
        values = record_string.replace('_', ' ').split('#')
        # Gabungkan urutan field dengan nilainya menggunakan zip
        return dict(zip(field_order, values))
    except Exception:
        # Kembalikan dict kosong jika ada error saat parsing
        return {}
    
def deserialize_padded_record(padded_string: str, field_order: list[str]) -> dict:
    """
    Mengubah string panjang yang di-padding dan di-serialize kembali menjadi
    satu dictionary data. Fungsi ini akan memotong data padding secara otomatis.

    Args:
        padded_string (str): String panjang yang berisi data asli diikuti padding.
        field_order (list[str]): List of string yang menentukan urutan field.

    Returns:
        dict: Dictionary yang berisi data KTP pertama yang ditemukan.
    """
    try:
        # Hapus spasi kosong di awal/akhir dan ganti '_'
        unpacked_string = padded_string.strip().replace('_', ' ')
        
        # Pisahkan seluruh string menjadi list nilai-nilai
        all_values = unpacked_string.split('#')
        
        # Ambil hanya nilai yang dibutuhkan untuk satu record
        num_fields = len(field_order)
        single_record_values = all_values[:num_fields]
        
        # Gabungkan field dengan nilainya untuk membuat dictionary
        return dict(zip(field_order, single_record_values))
    except Exception:
        return {}