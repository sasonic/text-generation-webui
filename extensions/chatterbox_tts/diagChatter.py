print("--- Starting Chatterbox Diagnostic ---")
try:
    import chatterbox
    print("✅ Successfully imported the 'chatterbox' module.")
    print("\n")

    # Print the location of the module file
    print("🔎 The module was loaded from this file:")
    # Use getattr to avoid an error if __file__ doesn't exist
    print(f"   {getattr(chatterbox, '__file__', 'Location not found')}")
    print("\n")

    # Print all attributes available in the module
    print("📋 Here are all the available attributes in the module:")
    print(dir(chatterbox))
    print("\n")

    # Check for the specific 'Chatterbox' class
    if 'ChatterboxTTS' in dir(chatterbox):
        print("✔️ SUCCESS: The required 'Chatterbox' class (with a capital C) was found!")
    else:
        print("❌ FAILURE: The required 'Chatterbox' class (with a capital C) is MISSING from this module.")

except ImportError:
    print("❌ FATAL: Could not import the 'chatterbox' module at all. It is not installed correctly.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("\n--- End of Diagnostic ---")