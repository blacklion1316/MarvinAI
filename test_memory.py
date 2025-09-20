#!/usr/bin/env python3
"""
Test script for MARVIN's memory system
"""

import json
import os
from datetime import datetime

# Test the memory functions
MEMORY_FILE = "test_marvin_memory.json"

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
    return save_memory(memory)

def recall_facts(limit=5):
    """Retrieve recent facts from memory"""
    memory = load_memory()
    facts = memory.get("facts", [])
    return facts[-limit:] if facts else []

def test_memory_system():
    """Test the memory system functionality"""
    print("🧠 Testing MARVIN Memory System")
    print("=" * 40)
    
    # Test 1: Save facts
    print("\n1. Testing fact storage...")
    test_facts = [
        "My favorite color is blue",
        "I work as a software developer",
        "I live in New York"
    ]
    
    for fact in test_facts:
        if remember_fact(fact):
            print(f"✅ Stored: {fact}")
        else:
            print(f"❌ Failed to store: {fact}")
    
    # Test 2: Recall facts
    print("\n2. Testing fact recall...")
    stored_facts = recall_facts()
    if stored_facts:
        print("📋 Recalled facts:")
        for i, fact in enumerate(stored_facts, 1):
            print(f"   {i}. {fact['content']} (stored: {fact['timestamp'][:10]})")
    else:
        print("❌ No facts found")
    
    # Test 3: Check memory file
    print("\n3. Checking memory file...")
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            memory_data = json.load(f)
        print(f"✅ Memory file exists with {len(memory_data.get('facts', []))} facts")
        print(f"📅 Created: {memory_data.get('created', 'Unknown')}")
        print(f"📅 Last updated: {memory_data.get('last_updated', 'Unknown')}")
    else:
        print("❌ Memory file not found")
    
    # Cleanup
    print("\n4. Cleaning up test file...")
    try:
        os.remove(MEMORY_FILE)
        print("✅ Test memory file removed")
    except:
        print("⚠️ Could not remove test file")
    
    print("\n🎉 Memory system test completed!")

if __name__ == "__main__":
    test_memory_system()
