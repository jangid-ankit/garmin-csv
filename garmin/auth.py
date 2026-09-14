import getpass
import garth

class AuthenticationError(Exception):
    """Raised when Garmin authentication fails."""
    pass

def authenticate(session_path="~/.garth") -> bool:
    """
    Authenticates with Garmin Connect using saved session tokens or prompts for credentials.
    Uses getpass to securely mask password entry.
    """
    try:
        # Try to resume existing session
        garth.resume(session_path)
        username = garth.client.username
        if username:
            print(f"Resumed existing session for {username}")
            return True
    except Exception:
        pass

    print("No valid session found. Please enter your Garmin credentials.")
    email = input("Enter email address: ").strip()
    password = getpass.getpass("Enter password: ")

    try:
        garth.login(email, password)
        garth.save(session_path)
        print(f"Logged in successfully as {garth.client.username}")
        return True
    except Exception as e:
        raise AuthenticationError(
            f"Login failed: {e}\n"
            "Note: If Garmin requires Cloudflare TLS fingerprinting or MFA, "
            "ensure you have a valid saved Garth session."
        ) from e
