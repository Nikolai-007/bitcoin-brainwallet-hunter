"""
ACCEPTANCE REQUIREMENT - Must be displayed at first run
"""

def show_license_acceptance():
    """Display license and require explicit acceptance"""
    
    license_text = """
    BITCOIN BRAINWALLET HUNTER - LICENSE ACCEPTANCE REQUIRED
    
    ⚠️  LEGAL AND EDUCATIONAL USE REQUIREMENTS:
    
    1. EDUCATIONAL USE ONLY
       This software is for learning about cryptography and Bitcoin
       mechanics. Not for real-world exploitation.
    
    2. LEGAL COMPLIANCE
       You must comply with all applicable laws. Unauthorized access
       attempts are criminal offenses.
    
    3. FULL RESPONSIBILITY
       You assume complete responsibility for your use of this software
       and any consequences that may result.
    
    4. NO ILLEGAL ACTIVITIES
       Strictly prohibited: attempting to access others' wallets,
       unauthorized testing, or any illegal purposes.
    
    BY TYPING 'I ACCEPT' YOU:
    - Confirm you have read and understand the LICENSE file
    - Accept full responsibility for your use of this software
    - Agree to use this software only for educational purposes
    - Acknowledge that misuse may have serious legal consequences
    """
    
    print("=" * 70)
    print(license_text)
    print("=" * 70)
    
    while True:
        response = input("\nDo you understand and accept these terms? (type 'I ACCEPT' or 'EXIT'): ")
        
        if response.upper() == 'I ACCEPT':
            print("\n✅ Terms accepted. Proceeding with educational software...")
            return True
        elif response.upper() == 'EXIT':
            print("\n🚫 Terms not accepted. Exiting software.")
            exit()
        else:
            print("❌ Please type 'I ACCEPT' to continue or 'EXIT' to quit.")

# Add this to the beginning of main() in bitcoin_hunter.py
if __name__ == "__main__":
    if show_license_acceptance():
        # Proceed with main program
        pass