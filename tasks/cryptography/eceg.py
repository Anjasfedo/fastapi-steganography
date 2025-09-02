from main_celery import celery
from methods.cryptography.eceg import EllipticCurveElGamal  # Assuming this is your cryptographic algorithm
from helpers.response_wrapper import api_response

# Initialize your cryptographic class
eceg = EllipticCurveElGamal()

# Generate keys and return them
@celery.task(name="tasks.cryptography.eceg.generate_keys_task", bind=True)
def generate_keys_task(self):
    """Generate and return ElGamal private and public keys."""
    try:
        private_key, public_key = eceg.generate_keys(as_int=True)  # Generate keys
        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "private_key": private_key,
            "public_key": public_key
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e

@celery.task(name="tasks.cryptography.eceg.encrypt_task", bind=True)
def encrypt_task(self, *, message: str, public_key: int):
    """Encrypt a message using the ElGamal public key."""
    self.update_state(state="STARTED", meta={"progress": 10})
    try:
        # Encrypt message
        encrypted_message = eceg.encrypt_message(message, public_key)

        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "encrypted_message": encrypted_message
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e

@celery.task(name="tasks.cryptography.eceg.decrypt_task", bind=True)
def decrypt_task(self, *, ciphertext: str, private_key: int):
    """Decrypt a message using the ElGamal private key."""
    self.update_state(state="STARTED", meta={"progress": 10})
    try:
        # Decrypt message
        decrypted_message = eceg.decrypt_message(ciphertext, private_key)

        self.update_state(meta={"stage": "finalizing", "progress": 95})
        return {
            "decrypted_message": decrypted_message
        }
    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "exc_type": type(e).__name__, 
            "exc_message": str(e),
            "progress": 100
        })
        raise e
