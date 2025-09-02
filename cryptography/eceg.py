import random

class Point:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y

    def is_infinity(self):
        """Check if the point is the point at infinity."""
        return self.x is None and self.y is None

    def __eq__(self, other):
        """Custom equality check for Point objects."""
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return False

    def __hash__(self):
        """Make Point hashable by defining a unique hash."""
        return hash((self.x, self.y))

    def __repr__(self):
        if self.is_infinity():
            return "Point at Infinity"
        return f"Point({self.x}, {self.y})"

class EllipticCurveElGamal:
  def __init__(self):
    self.a = 214
    self.b = 110
    self.p = 251
    # self.p = 233
    self.base_point = self.generate_random_valid_point()

    self.characters = [chr(i) for i in range(256)]
    # self.characters = [chr(i) for i in range(1, 256)]

    self.valid_points = self.get_all_points()
    self.point_to_char, self.char_to_point = self.create_mappings()

  def elliptic_curve_equation(self, x):
    return (x**3 + self.a*x + self.b) % self.p

  def is_on_curve(self, x, y):
        """Check if a point (x, y) lies on the curve."""
        if x is None or y is None:
            return True
        return (y**2 - (x**3 + self.a * x + self.b)) % self.p == 0

  def generate_random_valid_point(self):
        """Generate a random point that lies on the elliptic curve."""
        while True:
            x = random.randint(0, self.p - 1)
            y_squared = (x**3 + self.a * x + self.b) % self.p

            if pow(y_squared, (self.p - 1) // 2, self.p) == 1:
                for y in range(self.p):
                    if (y**2) % self.p == y_squared:
                        return Point(x, y)

  def calc_point_add(self, P, Q):
    """Calculate the addition of two points P and Q on the elliptic curve."""
    R = Point()

    if P.is_infinity():
        return Q
    if Q.is_infinity():
        return P

    if P.x == Q.x and (P.y != Q.y or P.y == 0):
        return Point()

    # Calculate slope
    if P.x == Q.x and P.y == Q.y:
        slope = (3 * P.x**2 + self.a) * pow(2 * P.y, -1, self.p) % self.p
    else:
        slope = (Q.y - P.y) * pow(Q.x - P.x, -1, self.p) % self.p

    R.x = (slope**2 - P.x - Q.x) % self.p

    R.y = (slope * (P.x - R.x) - P.y) % self.p

    return R

  def calc_point_doubling(self, P):
      """Calculate the point doubling 2P = P + P on the elliptic curve."""
      R = Point()

      if P.is_infinity() or P.y == 0:
          return Point()

      slope = (3 * P.x**2 + self.a) * pow(2 * P.y, -1, self.p) % self.p

      R.x = (slope**2 - 2 * P.x) % self.p

      R.y = (slope * (P.x - R.x) - P.y) % self.p

      return R

  def calc_point_subtraction(self, P, Q):
    """Calculate the subtraction of two points P - Q on the elliptic curve."""
    if Q.is_infinity():
        return P

    if P.is_infinity():
        Q_neg = Point(Q.x, (-Q.y) % self.p)
        return Q_neg

    Q_neg = Point(Q.x, (-Q.y) % self.p)

    return self.calc_point_add(P, Q_neg)


  def calc_point_multiplication(self, P, k):
    """Calculate kP using the double-and-add method."""
    R = Point()
    current_point = P

    while k > 0:
        if k % 2 == 1:
            R = self.calc_point_add(R, current_point)
        current_point = self.calc_point_add(current_point, current_point)
        k //= 2

    return R

  def generate_keys(self, as_int: bool = True):
        """
        Returns (private_key, public_key_point_or_int).
        If as_int=True, public key is returned as an integer 0..255 via the point->char mapping.
        """
        private_key = random.randint(1, self.p - 1)
        public_point = self.calc_point_multiplication(self.base_point, private_key)

        if as_int:
            public_key_int = self.point_to_int(public_point)
            return private_key, public_key_int
        return private_key, public_point

  def encrypt(self, plaintext_point, public_key, k=None):
      """
      Encrypt a point on the elliptic curve using the public key.
      """
      if isinstance(public_key, int):
          public_key = self.int_to_point(public_key)
          
      if k is None:
          k = random.randint(1, self.p - 1)

      C1 = self.calc_point_multiplication(self.base_point, k)

      k_e2 = self.calc_point_multiplication(public_key, k)

      C2 = self.calc_point_add(plaintext_point, k_e2)

      return C1, C2


  def decrypt(self, C1, C2, private_key):
        """
        Decrypt a ciphertext pair (C1, C2) using the private key.
        """
        d_C1 = self.calc_point_multiplication(C1, private_key)

        plaintext_point = self.calc_point_subtraction(C2, d_C1)

        return plaintext_point

  def get_all_points(self):
      """
      Generate all valid points on the elliptic curve.
      """
      points = [Point()]
      for x in range(self.p):
          y_squared = self.elliptic_curve_equation(x)
          for y in range(self.p):
              if (y**2) % self.p == y_squared:
                  points.append(Point(x, y))

      return points

  def create_mappings(self):
    valid_points = [point for point in self.valid_points]

    if len(valid_points) != len(self.characters):
        raise ValueError("Mismatch between the number of valid points and characters.")

    point_to_char = {point: char for point, char in zip(valid_points, self.characters)}

    char_to_point = {char: point for point, char in point_to_char.items()}

    return point_to_char, char_to_point


  def encode_character(self, char):
        """Encode a character to a point on the elliptic curve."""
        if char not in self.char_to_point:
            raise ValueError(f"Character '{char}' not in mapping.")

        return self.char_to_point[char]

  def decode_point(self, point):
        """Decode a point on the elliptic curve to a character."""
        if point not in self.point_to_char:
            raise ValueError(f"Point '{point}' not in mapping.")

        return self.point_to_char[point]

  def encrypt_message(self, message, public_key):
      """
      Encrypt a message using the elliptic curve encryption scheme and return a character-based ciphertext.
      """
      ciphertext = ""

      for char in message:
          plaintext_point = self.encode_character(char)

          C1, C2 = self.encrypt(plaintext_point, public_key)

          encrypted_char_C1 = self.decode_point(C1)
          encrypted_char_C2 = self.decode_point(C2)

          ciphertext += encrypted_char_C1 + encrypted_char_C2

      return ciphertext

  def decrypt_message(self, ciphertext, private_key):
    """
    Decrypt a ciphertext into its plaintext message using the private key.
    """
    if len(ciphertext) % 2 != 0:
        raise ValueError("Ciphertext length must be even to form valid (C1, C2) pairs.")

    plaintext = ""

    for i in range(0, len(ciphertext), 2):
        C1 = self.encode_character(ciphertext[i])
        C2 = self.encode_character(ciphertext[i + 1])

        decrypted_point = self.decrypt(C1, C2, private_key)
        char = self.decode_point(decrypted_point)
        plaintext += char

    return plaintext

  def point_to_int(self, P: Point) -> int:
        """
        Serialize a curve point to an integer [0..255] using point->char mapping.
        """
        ch = self.decode_point(P)  # raises if P not in mapping
        return ord(ch)

  def int_to_point(self, n: int) -> Point:
        """
        Deserialize an integer [0..255] to a curve point using char->point mapping.
        """
        if not (0 <= n <= 255):
            raise ValueError("Public key integer must be in range 0..255")
        ch = chr(n)
        return self.encode_character(ch)