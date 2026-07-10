#!/usr/bin/env python3
"""
Batch English Language Tutor for CuriousMind
Teaches English basics and grammar concepts
"""

import sys
import time

def teach_curiousmind(agent, dataset_file):
    """Feed English dataset to CuriousMind"""
    
    print("\n" + "=" * 70)
    print("  ENGLISH LANGUAGE TUTOR FOR CURIOUSMIND")
    print("=" * 70)
    print(f"\nLoading dataset from: {dataset_file}")
    
    try:
        with open(dataset_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {dataset_file} not found!")
        return
    
    total = len(lines)
    print(f"Found {total} language concepts to teach\n")
    
    learned = 0
    errors = 0
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        try:
            # Process each fact
            response = agent.process_input(line)
            learned += 1
            
            # Show progress
            if i % 10 == 0:
                print(f"[{i}/{total}] Taught {learned} concepts... Mood: {agent.brain.emotional_state}")
            
            # Small delay to avoid overwhelming
            time.sleep(0.05)
            
        except Exception as e:
            errors += 1
            print(f"Error at line {i}: {e}")
    
    # Final stats
    print("\n" + "=" * 70)
    print("  TEACHING COMPLETE!")
    print("=" * 70)
    
    stats = agent.get_stats()
    print(f"\n✓ Concepts taught: {learned}")
    print(f"✗ Errors: {errors}")
    print(f"\nAgent Statistics:")
    print(f"  Topics known: {stats['topics_known']}")
    print(f"  Total facts: {stats['total_facts']}")
    print(f"  Learning queue: {stats['learning_queue_size']}")
    print(f"  Associations: {stats['associations']}")
    print(f"  Current mood: {stats['emotional_state']}")
    
    print(f"\n📚 CuriousMind has learned English!\n")

if __name__ == "__main__":
    # Import here to ensure agent is initialized
    from curious_mind import CuriousMind
    
    agent = CuriousMind()
    teach_curiousmind(agent, 'english_basics.txt')
