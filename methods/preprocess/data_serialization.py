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
    return merged.replace(' ', '%')


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