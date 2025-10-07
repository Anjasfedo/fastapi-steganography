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

    def generate_nik(self):
        """Generate a dummy NIK (Indonesian identity number)."""
        province_code = random.randint(10, 34)  # Random province code
        regency_code = random.randint(1, 99)   # Random regency code
        district_code = random.randint(1, 99)  # Random district code
        date_of_birth = self.faker.date_of_birth()
        birth_date_part = date_of_birth.strftime('%d%m%y')  # Format DDMMYY
        random_sequence = random.randint(
            1000, 9999)       # Random sequence number
        return f"{province_code:02}{regency_code:02}{district_code:02}{birth_date_part}{random_sequence:04}"

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
        Replace spaces with '%'.
        """
        return [DummyKTPGenerator.merge_ktp_data(ktp) for ktp in ktps]
