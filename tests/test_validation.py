"""Test password and username validation"""

from app.utils.validators import validate_password, validate_username


def test_password_validation():
    """Test password validation"""
    print("Testing Password Validation:")
    print("-" * 50)
    
    test_cases = [
        ("weak", False, "Too short"),
        ("weakpass", False, "No uppercase, digit, or special char"),
        ("Weakpass", False, "No digit or special char"),
        ("Weakpass1", False, "No special char"),
        ("Weak@123", True, "Valid strong password"),
        ("Admin@123456!", True, "Valid strong password"),
        ("MyP@ssw0rd", True, "Valid strong password"),
    ]
    
    for password, expected, description in test_cases:
        is_valid, msg = validate_password(password)
        status = "✅" if is_valid == expected else "❌"
        print(f"{status} {description}: '{password}' - {msg}")


def test_username_validation():
    """Test username validation"""
    print("\n\nTesting Username Validation:")
    print("-" * 50)
    
    test_cases = [
        ("ab", False, "Too short"),
        ("a" * 31, False, "Too long"),
        ("user@name", False, "Invalid character @"),
        ("user name", False, "Invalid character space"),
        ("-username", False, "Starts with hyphen"),
        ("username_", False, "Ends with underscore"),
        ("user123", True, "Valid username"),
        ("user_name", True, "Valid username with underscore"),
        ("user-name", True, "Valid username with hyphen"),
        ("User123", True, "Valid username with mixed case"),
        (None, True, "Username is optional"),
    ]
    
    for username, expected, description in test_cases:
        is_valid, msg = validate_username(username)
        status = "✅" if is_valid == expected else "❌"
        print(f"{status} {description}: '{username}' - {msg if msg else 'Valid'}")


if __name__ == "__main__":
    test_password_validation()
    test_username_validation()
