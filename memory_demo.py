#!/usr/bin/env python3
"""
MARVIN Memory Demo - Testing memory system without OpenAI dependency
"""

import json
import os
from datetime import datetime

# Memory system functions
MEMORY_FILE = "marvin_memory.json"

def load_memory():
    """Load persistent memory from JSON file"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")
    return {
        "facts": [],
        "preferences": {},
        "notes": [],
        "conversation_history": [],
        "created": datetime.now().isoformat()
    }

def save_memory(memory_data):
    """Save memory data to JSON file"""
    try:
        memory_data["last_updated"] = datetime.now().isoformat()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def remember_fact(fact):
    """Store a fact in long-term memory"""
    memory = load_memory()
    fact_entry = {
        "content": fact,
        "timestamp": datetime.now().isoformat(),
        "source": "user_input"
    }
    memory["facts"].append(fact_entry)
    if save_memory(memory):
        print(f"✅ Remembered: {fact}")
        return True
    return False

def remember_note(note):
    """Store a note in memory"""
    memory = load_memory()
    note_entry = {
        "content": note,
        "timestamp": datetime.now().isoformat(),
        "source": "user_input"
    }
    memory["notes"].append(note_entry)
    if save_memory(memory):
        print(f"📝 Noted: {note}")
        return True
    return False

def set_preference(key, value):
    """Store a user preference"""
    memory = load_memory()
    memory["preferences"][key] = {
        "value": value,
        "timestamp": datetime.now().isoformat()
    }
    if save_memory(memory):
        print(f"⚙️ Preference set: {key} = {value}")
        return True
    return False

def recall_facts(limit=5):
    """Retrieve recent facts from memory"""
    memory = load_memory()
    facts = memory.get("facts", [])
    return facts[-limit:] if facts else []

def recall_notes(limit=5):
    """Retrieve recent notes from memory"""
    memory = load_memory()
    notes = memory.get("notes", [])
    return notes[-limit:] if notes else []

def get_preferences():
    """Get all user preferences"""
    memory = load_memory()
    return memory.get("preferences", {})

def get_memory_summary():
    """Get a summary of all stored information"""
    memory = load_memory()
    fact_count = len(memory.get("facts", []))
    note_count = len(memory.get("notes", []))
    pref_count = len(memory.get("preferences", {}))
    
    return f"Memory contains: {fact_count} facts, {note_count} notes, {pref_count} preferences"

def demo_memory_system():
    """Interactive demo of the memory system"""
    print("🧠 MARVIN Memory System Demo")
    print("=" * 50)
    print("Commands:")
    print("  remember <fact>     - Store a fact")
    print("  note <note>         - Store a note") 
    print("  prefer <key> <val>  - Set preference")
    print("  recall              - Show recent facts")
    print("  notes               - Show recent notes")
    print("  preferences         - Show preferences")
    print("  summary             - Memory summary")
    print("  clear               - Clear all memory")
    print("  quit                - Exit demo")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n💬 Enter command: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() == "quit":
                print("👋 Goodbye!")
                break
                
            elif user_input.lower() == "recall":
                facts = recall_facts()
                if facts:
                    print("📋 Recent facts:")
                    for i, fact in enumerate(facts, 1):
                        print(f"   {i}. {fact['content']}")
                else:
                    print("🤔 No facts stored yet")
                    
            elif user_input.lower() == "notes":
                notes = recall_notes()
                if notes:
                    print("📝 Recent notes:")
                    for i, note in enumerate(notes, 1):
                        print(f"   {i}. {note['content']}")
                else:
                    print("📝 No notes stored yet")
                    
            elif user_input.lower() == "preferences":
                prefs = get_preferences()
                if prefs:
                    print("⚙️ Preferences:")
                    for key, data in prefs.items():
                        print(f"   {key}: {data['value']}")
                else:
                    print("⚙️ No preferences set yet")
                    
            elif user_input.lower() == "summary":
                summary = get_memory_summary()
                print(f"📊 {summary}")
                
            elif user_input.lower() == "clear":
                confirm = input("⚠️ Clear all memory? (yes/no): ")
                if confirm.lower() == "yes":
                    if os.path.exists(MEMORY_FILE):
                        os.remove(MEMORY_FILE)
                        print("🗑️ Memory cleared!")
                    else:
                        print("🤔 No memory file to clear")
                        
            elif user_input.startswith("remember "):
                fact = user_input[9:].strip()
                if fact:
                    remember_fact(fact)
                else:
                    print("❌ Please provide a fact to remember")
                    
            elif user_input.startswith("note "):
                note = user_input[5:].strip()
                if note:
                    remember_note(note)
                else:
                    print("❌ Please provide a note to store")
                    
            elif user_input.startswith("prefer "):
                parts = user_input[7:].strip().split(" ", 1)
                if len(parts) == 2:
                    key, value = parts
                    set_preference(key, value)
                else:
                    print("❌ Usage: prefer <key> <value>")
                    
            else:
                print("❌ Unknown command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    demo_memory_system()
