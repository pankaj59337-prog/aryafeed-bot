import getpass
import sys
from pathlib import Path
import subprocess
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, BadPassword, ChallengeRequired

SESSION_FILE = Path("data/sessions/instagram_5381201341.json")
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 60)
    print("   INSTAGRAM 1-CLICK AUTHENTICATION FOR REEL MAKER BOT")
    print("=" * 60)
    print("This script logs in directly from your Indian home internet,")
    print("which Instagram trusts, completely bypassing cloud datacenter blocks!\n")
    
    raw_user = input("Instagram Username [press Enter for 'night_thought_12']: ").strip()
    if not raw_user or "python" in raw_user.lower() or ".py" in raw_user.lower() or "connect" in raw_user.lower():
        username = "night_thought_12"
    else:
        username = raw_user.lstrip("@")
    
    print(f"\nTarget Account: @{username}")
    password = getpass.getpass(f"Enter password for @{username}: ").strip()
    
    if not password:
        print("Password cannot be empty!")
        sys.exit(1)
        
    cl = Client()
    cl.delay_range = [1, 3]
    cl.set_country("IN")
    cl.set_country_code(91)
    cl.set_locale("en_IN")
    cl.set_timezone_offset(19800)

    # Clean old dead session to prevent 'user_has_logged_out' conflict
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink()
        except Exception:
            pass
            
    print(f"\nLogging into Instagram as @{username} from your local PC...")
    try:
        cl.login(username, password)
    except TwoFactorRequired:
        print("\nTwo-Factor Authentication (2FA) / SMS OTP Required!")
        code = input("Enter the 6-digit OTP code sent to your phone/authenticator app: ").strip()
        try:
            cl.login(username, password, verification_code=code)
        except Exception as e:
            print(f"2FA verification failed: {e}")
            sys.exit(1)
    except BadPassword:
        print("\nIncorrect password. Please verify your password and run again.")
        sys.exit(1)
    except ChallengeRequired:
        print("\nInstagram security challenge required.")
        print("Please open the Instagram app on your phone, tap 'This Was Me', and run this script again.")
        sys.exit(1)
    except Exception as e:
        print(f"\nDirect API login error: {e}")
        print("Attempting web browser session login...")
        sid = input("\nOptional: If password login is challenged, paste your 'sessionid' cookie from browser (or press Enter to exit): ").strip()
        if sid:
            clean_sid = sid.strip().strip('"').strip("'")
            cl.login_by_sessionid(clean_sid)
        else:
            sys.exit(1)
            
    cl.dump_settings(SESSION_FILE)
    print(f"\nSUCCESS! Authenticated as @{username} (ID: {cl.user_id})!")
    print(f"Session saved to: {SESSION_FILE}")
    
    print("\nSyncing session to Render Cloud...")
    try:
        subprocess.run(["git", "add", str(SESSION_FILE)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: Sync verified local Instagram session to Render"], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "master"], check=True, capture_output=True)
        print("Session successfully pushed to GitHub! Render will auto-deploy in ~60 seconds.")
        print("\nAuto-posting is now 100% READY! You can close this window.")
    except Exception as e:
        print(f"Git sync note: {e}")

if __name__ == "__main__":
    main()
