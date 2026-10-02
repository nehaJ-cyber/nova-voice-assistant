import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ellie.main import EllieAssistant

# Suppress debug logs for cleaner chat
logging.getLogger().setLevel(logging.ERROR)

def main():
    print("========================================")
    print("        Ellie Text Chat Mode            ")
    print("========================================")
    print("Type your commands below. Type 'exit' to quit.\n")
    
    assistant = EllieAssistant()
    
    while True:
        try:
            command = input("\nYou: ")
            if command.lower() in ['exit', 'quit']:
                break
            if not command.strip():
                continue
                
            print("Ellie: Thinking...")
            res = assistant._on_command(command)
            if res:
                output = res.get("feedback") or res.get("text") or res.get("reason") or f"Executed: {res.get('action') or res.get('intent') or 'Done'}"
                print(f"Ellie: {output}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
