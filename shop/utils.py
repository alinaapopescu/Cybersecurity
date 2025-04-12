import base64

def complex_encode(s, shift=5):
    reversed_str = s[::-1]
    ciphered = ''.join(
        chr((ord(char) - 32 + shift) % 95 + 32) if 32 <= ord(char) <= 126 else char
        for char in reversed_str
    )
    encoded = base64.b64encode(ciphered.encode()).decode()
    return encoded
