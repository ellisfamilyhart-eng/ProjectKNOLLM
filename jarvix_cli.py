#!/usr/bin/env python3
"""
Jarvix NoLLM - CLI Interface
Command-line interface for interacting with Jarvix agent
"""

from jarvix import Jarvix, ResponseGenerator

def main():
    """Main CLI loop"""
    print("=" * 70)
    print("  JARVIX NoLLM v1.0")
    print("  A Modular Self-Learning AI (No LLMs)")
    print("=" * 70)
    print("\nTeach me using format: 'Topic: Fact'")
    print("Commands: /stats, /memory, /analyze TOPIC, /forget, /quit")
    print("-" * 70)
    
    agent = Jarvix()
    
    # Show resume info
    stats = agent.get_stats()
    if stats['total_interactions'] > 0:
        print(f"\n[Resumed] I've had {stats['total_interactions']} conversations.")
        print(f"[Knowledge] {stats['total_facts']} facts in {stats['topics_known']} topics.")
    else:
        print("\n[Born] This is my first awakening. Teach me!")
    
    print()
    
    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
            print(f"\nSaving my mind...")
            agent.memory.save()
            print(f"Goodbye! I learned {agent.get_stats()['total_facts']} facts.")
            break
        
        if user_input.lower() == '/stats':
            print(ResponseGenerator.generate_status_report(agent.memory))
            continue
        
        if user_input.lower() == '/memory':
            print(ResponseGenerator.generate_memory_dump(agent.memory))
            continue
        
        if user_input.lower() == '/summary':
            print(ResponseGenerator.generate_summary(agent))
            continue
        
        if user_input.lower() == '/forget':
            if input("Are you sure? (yes/no): ").lower() == 'yes':
                agent.clear_memory()
                print("[Whoosh] All memories erased. I'm reborn!")
            continue
        
        if user_input.lower().startswith('/analyze'):
            topic = user_input.split(maxsplit=1)[1] if ' ' in user_input else None
            if topic:
                analysis = agent.analyze_topic(topic)
                print(f"\n[Analysis] {topic}")
                print(f"  Facts: {len(analysis['known_facts'])}")
                print(f"  Confidence: {analysis['confidence']:.2f}")
                print(f"  Associated: {', '.join(analysis['associated_topics']) or 'None'}")
            continue
        
        if user_input.lower() == '/thought':
            thought = agent.autonomous_thought()
            if thought:
                print(f"\n*{agent.name} thinks* {thought}\n")
            else:
                print("\n*No thoughts right now...*\n")
            continue
        
        # Normal interaction
        response = agent.process_input(user_input)
        print(f"\n{agent.name} > {response}\n")
        
        # Occasional autonomous thought
        if agent.memory.total_interactions % 5 == 0:
            thought = agent.autonomous_thought()
            if thought:
                print(f"\n*{agent.name} thinks* {thought}\n")

if __name__ == "__main__":
    main()
