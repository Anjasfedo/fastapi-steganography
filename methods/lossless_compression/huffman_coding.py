import heapq
from collections import Counter


class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


class HuffmanCoding:
    @staticmethod
    def build_frequency_table(text):
        """Build a frequency table for the given text."""
        return Counter(text)

    @staticmethod
    def build_huffman_tree(freq_table):
        """Build the Huffman Tree based on the frequency table."""
        heap = [HuffmanNode(char, freq) for char, freq in freq_table.items()]
        heapq.heapify(heap)

        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            merged = HuffmanNode(None, left.freq + right.freq)
            merged.left = left
            merged.right = right
            heapq.heappush(heap, merged)

        return heap[0] if heap else None

    @staticmethod
    def generate_huffman_codes(node, prefix='', codebook=None):
        """Recursively generate Huffman codes for each character."""
        if codebook is None:
            codebook = {}
        if node is None:
            return codebook

        if node.char is not None:
            codebook[node.char] = prefix
        else:
            HuffmanCoding.generate_huffman_codes(
                node.left, prefix + '0', codebook)
            HuffmanCoding.generate_huffman_codes(
                node.right, prefix + '1', codebook)

        return codebook

    @staticmethod
    def encode(text, codebook):
        """Encode the input text using the Huffman codebook."""
        bitstring = ''.join(codebook[char] for char in text)
        return bitstring

    @staticmethod
    def decode(bitstring, huffman_tree):
        """Decode the encoded bitstring back to the original text."""
        decoded_text = []
        node = huffman_tree

        for bit in bitstring:
            node = node.left if bit == '0' else node.right
            if node.char is not None:
                decoded_text.append(node.char)
                node = huffman_tree

        return ''.join(decoded_text)

    @staticmethod
    def build_huffman(text):
        """Build the Huffman tree, generate codes, and encode the text."""
        freq_table = HuffmanCoding.build_frequency_table(text)

        huffman_tree = HuffmanCoding.build_huffman_tree(freq_table)

        codebook = HuffmanCoding.generate_huffman_codes(huffman_tree)

        encoded_text = HuffmanCoding.encode(text, codebook)

        return encoded_text, huffman_tree, codebook
    
    @staticmethod
    def build_huffman_tree_from_codebook(codebook):
        """Rebuild the Huffman tree from the given codebook."""
        # Start with an empty tree
        huffman_tree = HuffmanNode(None, 0)

        # Insert each character from the codebook into the tree
        for char, code in codebook.items():
            node = huffman_tree
            for bit in code:
                if bit == '0':
                    if not node.left:
                        node.left = HuffmanNode(None, 0)
                    node = node.left
                elif bit == '1':
                    if not node.right:
                        node.right = HuffmanNode(None, 0)
                    node = node.right
            # Leaf node with character
            node.char = char

        return huffman_tree