"""
Basic usage example - EDUCATIONAL PURPOSES ONLY
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bitcoin_hunter import generate_brainwallet_addresses

def demo_address_generation():
    print("⚠️  EDUCATIONAL DEMONSTRATION ONLY")
    
    test_phrases = ["bitcoin", "test phrase", "crypto"]
    
    for phrase in test_phrases:
        print(f"\nPhrase: '{phrase}'")
        addresses = generate_brainwallet_addresses(phrase)
        
        if addresses:
            print(f"Legacy: {addresses['legacy_compressed']['addr']}")
            print(f"SegWit: {addresses['p2sh']['addr']}")

if __name__ == "__main__":
    print("Bitcoin Brainwallet Demo - FOR LEARNING ONLY")
    demo_address_generation()