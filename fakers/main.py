from faker import Faker
from methods.preprocess.data_serialization import serialize_record
import random

KTP_FIELD_ORDER = [
    'NIK', 'Nama', 'Tempat_Tgl_Lahir', 'Jenis_Kelamin', 'Gol_Darah', 'Alamat',
    'RT_RW', 'Kel_Desa', 'Kecamatan', 'Agama', 'Status_Perkawinan',
    'Pekerjaan', 'Kewarganegaraan', 'Berlaku_Hingga'
]


class DummyKTPGenerator:
    def __init__(self):
        self.faker = Faker('id_ID')  # Use Indonesian locale
        self.indonesian_jobs = [
            "Guru", "Dokter", "Petani", "Nelayan", "Pegawai Negeri", "Karyawan Swasta",
            "Wiraswasta", "Mahasiswa", "Pelajar", "Pengacara", "Arsitek", "Insinyur",
            "Pedagang", "Polisi", "Tentara", "Seniman", "Penulis", "Pilot", "Supir",
            "Teknisi", "Pemadam Kebakaran", "Apoteker"
        ]
        self.generated_niks = set()  # Set to track generated NIKs
        self.indonesian_districts = [
            "Menteng", "Kebayoran Baru", "Setiabudi", "Mampang Prapatan", "Tebet", "Cilandak",
            "Pasar Minggu", "Kebayoran Lama", "Kebon Jeruk", "Kembangan", "Cengkareng",
            "Grogol Petamburan", "Taman Sari", "Tambora", "Sawah Besar", "Kemayoran",
            "Senen", "Cempaka Putih", "Menteng", "Tanah Abang", "Jatinegara", "Duren Sawit",
            "Kramat Jati", "Pasar Rebo", "Ciracas", "Cipayung", "Makasar", "Pancoran",
            "Jagakarsa", "Tebet", "Setiabudi", "Mampang Prapatan", "Pasar Minggu",
            "Kebayoran Lama", "Kebayoran Baru", "Cilandak", "Pesanggrahan", "Kebon Jeruk",
            "Kalideres", "Koja", "Kelapa Gading", "Cilincing", "Pademangan", "Penjaringan",
            "Tanjung Priok", "Cengkareng", "Grogol Petamburan", "Tambora", "Sawah Besar",
            "Kemayoran", "Senen", "Cempaka Putih", "Menteng", "Tanah Abang", "Matraman",
            "Pulo Gadung", "Jatinegara", "Duren Sawit", "Kramat Jati", "Pasar Rebo",
            "Ciracas", "Cipayung", "Makasar", "Pancoran", "Jagakarsa"
        ]

    def generate_ktp(self):
        """Generate a single dummy KTP record."""
        nik = self.generate_nik()
        name = self.faker.name()
        birth_place = self.faker.city()
        birth_date = self.faker.date_of_birth().strftime('%d-%m-%Y')
        gender = random.choice(['Laki-Laki', 'Perempuan'])
        blood_type = random.choice(['A', 'B', 'AB', 'O'])
        address = self.faker.address().replace('\n', ', ')
        rt_rw = f"{random.randint(1, 20)}/{random.randint(1, 20)}"
        kelurahan = self.faker.city_suffix()
        # Added kecamatan field
        kecamatan = random.choice(self.indonesian_districts)
        religion = random.choice(
            ['Islam', 'Kristen', 'Katolik', 'Hindu', 'Buddha', 'Konghucu'])
        marital_status = random.choice(
            ['Belum Kawin', 'Kawin', 'Cerai Hidup', 'Cerai Mati'])
        # Select random Indonesian job
        occupation = random.choice(self.indonesian_jobs)
        nationality = 'WNI'  # Assuming all generated data is Indonesian
        valid_until = 'SEUMUR HIDUP'

        return {
            'NIK': nik,
            'Nama': name,
            'Tempat_Tgl_Lahir': f"{birth_place}, {birth_date}",
            'Jenis_Kelamin': gender,
            'Gol_Darah': blood_type,
            'Alamat': address,
            'RT_RW': rt_rw,
            'Kel_Desa': kelurahan,
            'Kecamatan': kecamatan,  # Added kecamatan field
            'Agama': religion,
            'Status_Perkawinan': marital_status,
            'Pekerjaan': occupation,
            'Kewarganegaraan': nationality,
            'Berlaku_Hingga': valid_until,
        }

    def generate_unique_nik(self):
        """Generate a unique NIK (Indonesian identity number)."""
        while True:
            province_code = random.randint(10, 34)  # Random province code
            regency_code = random.randint(1, 99)   # Random regency code
            district_code = random.randint(1, 99)  # Random district code
            date_of_birth = self.faker.date_of_birth()
            birth_date_part = date_of_birth.strftime('%d%m%y')  # Format DDMMYY
            random_sequence = random.randint(1000, 9999)       # Random sequence number
            nik = f"{province_code:02}{regency_code:02}{district_code:02}{birth_date_part}{random_sequence:04}"

            # Ensure that the NIK is unique by checking against the generated_niks set
            if nik not in self.generated_niks:
                self.generated_niks.add(nik)
                return nik

    def generate_nik(self):
        """Generate a dummy NIK (Indonesian identity number)."""
        return self.generate_unique_nik()

    @staticmethod
    def merge_ktp_data(ktp):
        """
        Merge a single KTP dictionary into a formatted string with '#' as a separator.
        Replace spaces with '%'.
        """
        fields = [
            ktp.get('NIK', ''),
            ktp.get('Nama', ''),
            ktp.get('Tempat_Tgl_Lahir', ''),
            ktp.get('Jenis_Kelamin', ''),
            ktp.get('Gol_Darah', ''),
            ktp.get('Alamat', ''),
            ktp.get('RT_RW', ''),
            ktp.get('Kel_Desa', ''),
            ktp.get('Kecamatan', ''),  # Added kecamatan field
            ktp.get('Agama', ''),
            ktp.get('Status_Perkawinan', ''),
            ktp.get('Pekerjaan', ''),
            ktp.get('Kewarganegaraan', ''),
            ktp.get('Berlaku_Hingga', '')
        ]

        return serialize_record(fields, KTP_FIELD_ORDER)

    @staticmethod
    def merge_multiple_ktps(ktps):
        """
        Merge multiple KTP dictionaries into formatted strings with '#' as a separator.
        Replace spaces with '_'.
        """
        return [DummyKTPGenerator.merge_ktp_data(ktp) for ktp in ktps]

    def generate_multiple_ktps(self, count=1):
        """Generate multiple dummy KTP records and ensure uniqueness."""
        ktps = []
        for _ in range(count):
            ktps.append(self.generate_ktp())
        return ktps

    def generate_ktp_based_on_target_length(self, max_chars, max_bits, additional_length=0, generation_type='unique'):
        """
        Generate unique KTP data based on the target message length (max_chars) and maximum bit size (max_bits).
        It will trim the KTP data if the bit size exceeds the limit and ensure uniqueness of the data.

        :param additional_length: Optional additional length to extend max_chars and max_bits
        :param generation_type: 'unique' to generate different KTPs each loop, 'repeat' to repeat the same KTP
        """
        # Increase max_chars and max_bits by the additional_length
        max_chars += additional_length
        max_bits += additional_length * 8  # 8 bits per character

        # Calculate max_characters allowed based on max_bits
        max_characters_allowed = max_bits // 8  # 1 byte = 8 bits

        # To accumulate the repeated data
        repeated_data = ""
        generated_ktp = None

        if generation_type == 'repeat':
            generated_ktp = self.generate_ktp()

        # Keep generating unique KTPs and appending to repeated_data until we reach max_chars
        while len(repeated_data) < max_characters_allowed - 4:  # Leave space for the final trim
            if generation_type == 'unique':
                generated_ktp = self.generate_ktp()

            merged_ktp = self.merge_ktp_data(generated_ktp)

            # If the generated KTP exceeds max_chars, trim it
            if len(merged_ktp) > max_characters_allowed:
                merged_ktp = merged_ktp[:max_characters_allowed]

            # Add this unique KTP to the repeated data, with $ as a separator
            repeated_data += merged_ktp + '$'

        # Ensure that the total length does not exceed max_characters_allowed
        repeated_data = repeated_data[:max_characters_allowed - 4]

        return repeated_data

    def check_unique_ktps(self, generated_data):
        """
        Check if the KTPs in the generated data are unique.

        :param generated_data: The generated data (string) containing KTPs separated by '$'
        :return: True if all KTPs are unique, False if there are duplicates.
        """
        # Split the data by the '$' separator to get individual KTPs
        ktps = generated_data.split('$')

        # Remove empty strings from the list
        ktps = [ktp for ktp in ktps if ktp.strip()]

        # Use a set to check for duplicates
        unique_ktps = set(ktps)

        # If the length of the set is equal to the length of the list, all KTPs are unique
        return len(unique_ktps) == len(ktps)
