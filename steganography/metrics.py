import cv2
import numpy as np
from skimage.metrics import structural_similarity as skimage_ssim


class StegoMetrics:
    def __init__(self, ori_image):
        """
        Initialize the StegoMetrics class with the original image path.

        Args:
            ori_image (str): Path to the original image.
        """
        self.ori_image = ori_image

    @staticmethod
    def calculate_mse(original, stego):
        """
        Calculate the Mean Squared Error (MSE) between two images.

        Args:
            original (numpy.ndarray): Original image array.
            stego (numpy.ndarray): Stego image array.

        Returns:
            float: The MSE value.
        """
        return np.mean((original - stego) ** 2)

    def calculate_psnr(self, stego_image_path):
        """
        Calculate the Peak Signal-to-Noise Ratio (PSNR) between the original and stego image.

        Args:
            stego_image_path (str): Path to the stego image.

        Returns:
            float: The PSNR value.
        """
        # Read images
        original = cv2.imread(self.ori_image)
        stego = cv2.imread(stego_image_path)

        if original is None:
            raise ValueError(f"Failed to load original image from {self.ori_image}. Ensure the file exists and is a valid image format.")
        if stego is None:
            raise ValueError(f"Failed to load stego image from {stego_image_path}. Ensure the file exists and is a valid image format.")

        # Calculate MSE
        mse = self.calculate_mse(original, stego)
        if mse == 0:  # If images are identical
            return float('inf')

        # Calculate PSNR
        max_pixel_value = 255.0
        psnr = 10 * np.log10((max_pixel_value ** 2) / mse)
        return psnr

    @staticmethod
    def calculate_ssim(original, stego):
        """
        Calculate the Structural Similarity Index (SSIM) between two images.

        Args:
            original (numpy.ndarray): Original image array.
            stego (numpy.ndarray): Stego image array.

        Returns:
            float: The SSIM value.
        """
        original_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        stego_gray = cv2.cvtColor(stego, cv2.COLOR_BGR2GRAY)

        ssim_value, _ = skimage_ssim(original_gray, stego_gray, full=True)
        return ssim_value


    def calculate_metrics(self, stego_image_path):
        """
        Calculate MSE, PSNR, and SSIM between the original and stego image.

        Args:
            stego_image_path (str): Path to the stego image.

        Returns:
            tuple: MSE, PSNR, and SSIM values.
        """
        # Read images
        original = cv2.imread(self.ori_image)
        stego = cv2.imread(stego_image_path)

        if original is None:
            raise ValueError(f"Failed to load original image from {self.ori_image}. Ensure the file exists and is a valid image format.")
        if stego is None:
            raise ValueError(f"Failed to load stego image from {stego_image_path}. Ensure the file exists and is a valid image format.")

        # Calculate metrics
        mse_value = self.calculate_mse(original, stego)
        psnr_value = self.calculate_psnr(stego_image_path)
        ssim_value = self.calculate_ssim(original, stego)

        return mse_value, psnr_value, ssim_value