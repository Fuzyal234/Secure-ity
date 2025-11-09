import re
from flask import current_app

def validate_password(password):
    """
    Validate password strength per security requirements
    
    Returns:
        tuple: (is_valid, error_message)
    """
    config = current_app.config
    
    if len(password) < config.get('PASSWORD_MIN_LENGTH', 12):
        return False, f"Password must be at least {config.get('PASSWORD_MIN_LENGTH', 12)} characters long"
    
    if config.get('PASSWORD_REQUIRE_UPPERCASE', True) and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if config.get('PASSWORD_REQUIRE_LOWERCASE', True) and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if config.get('PASSWORD_REQUIRE_NUMBERS', True) and not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if config.get('PASSWORD_REQUIRE_SPECIAL', True) and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    # Check for common weak passwords
    common_passwords = ['password', '12345678', 'qwerty', 'admin', 'welcome']
    if password.lower() in common_passwords:
        return False, "Password is too common and easily guessable"
    
    return True, None

def validate_config_data(data):
    """
    Validate configuration data structure
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Configuration data must be a dictionary"
    
    if not data:
        return False, "Configuration data cannot be empty"
    
    # Check for maximum size (e.g., 1MB)
    import json
    data_str = json.dumps(data)
    if len(data_str.encode('utf-8')) > 1024 * 1024:  # 1MB
        return False, "Configuration data exceeds maximum size of 1MB"
    
    return True, None

def sanitize_input(text, max_length=1000):
    """
    Sanitize user input to prevent injection attacks
    
    Args:
        text: Input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        return str(text)
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

