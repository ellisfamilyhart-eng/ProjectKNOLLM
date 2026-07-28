"""
dynamic_ability_engine.py

Jarvix Self-Modification & Autonomous Skill Compiler
- Allows Jarvix to draft new Python code safely.
- Validates syntax using Abstract Syntax Trees (AST).
- Persists code to disk for permanent memory.
- Injects new capabilities into the runtime AbilityBrain on the fly.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
import types
from typing import Any, Callable, Dict, Optional

# Import the core Ability and Brain abstractions
try:
    from ability_brain_v2036 import Ability, AbilityBrain
except ImportError:
    from ability_brain import Ability, AbilityBrain


class DynamicAbilityEngine:
    def __init__(self, brain_instance: AbilityBrain, storage_dir: str = "custom_abilities"):
        self.brain = brain_instance
        self.storage_dir = storage_dir
        
        # Ensure the directory for custom self-written abilities exists
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        # Ensure directory has an __init__.py so Python treats it as a package
        init_path = os.path.join(self.storage_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write("# Jarvix Self-Synthesized Capabilities Store\n")

        # Load any existing self-written abilities from disk on startup
        self.load_persisted_abilities()

    # --------------------------------------------------
    # 1. Syntax & Safety Validation
    # --------------------------------------------------

    def validate_code_safety(self, python_code: str) -> bool:
        """Parses source code into an AST to ensure it contains no syntax errors."""
        try:
            ast.parse(python_code)
            return True
        except SyntaxError as e:
            print(f"[Self-Update Error] Invalid Python syntax generated: {e}")
            return False

    # --------------------------------------------------
    # 2. Dynamic Runtime Injection
    # --------------------------------------------------

    def compile_and_inject(self, module_name: str, python_code: str) -> Optional[types.ModuleType]:
        """Compiles raw Python text string into an in-memory module."""
        if not self.validate_code_safety(python_code):
            return None

        try:
            compiled_code = compile(python_code, filename=f"<jarvix_dynamic_{module_name}>", mode="exec")
            module = types.ModuleType(module_name)
            exec(compiled_code, module.__dict__)
            return module
        except Exception as e:
            print(f"[Self-Update Error] Runtime compilation failed: {e}")
            return None

    # --------------------------------------------------
    # 3. Permanent Self-Modification
    # --------------------------------------------------

    def learn_new_ability(
        self,
        ability_name: str,
        python_code: str,
        description: str,
        semantic_tags: list[str]
    ) -> bool:
        """
        Synthesizes a new ability, writes it to disk, loads it into runtime,
        and registers it to Jarvix's AbilityBrain.
        """
        clean_name = re.sub(r"\W+", "_", ability_name.lower())
        file_path = os.path.join(self.storage_dir, f"{clean_name}.py")

        # Step 1: Validate Syntax
        if not self.validate_code_safety(python_code):
            return False

        # Step 2: Write to Disk (Persistent Memory)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(python_code)
        except IOError as e:
            print(f"[Self-Update Error] Could not write ability file to disk: {e}")
            return False

        # Step 3: Inject In-Memory Module
        module = self.compile_and_inject(clean_name, python_code)
        if not module:
            return False

        # Step 4: Extract the Handler Function
        # Expects the script to define a handler function matching 'run' or the ability name
        handler = getattr(module, "run", None) or getattr(module, clean_name, None)
        
        if not callable(handler):
            print(f"[Self-Update Error] Code in {clean_name}.py must contain a callable 'run' or '{clean_name}' function.")
            return False

        # Step 5: Register new capability directly into the live brain
        new_ability = Ability(
            name=clean_name,
            description=description,
            handler=handler,
            semantic_tags=semantic_tags,
            complexity_score=0.5
        )

        self.brain.register(new_ability)
        print(f"[Jarvix Self-System] Learned and bound new capability: '{clean_name}'")
        return True

    # --------------------------------------------------
    # 4. Persistence Reloading
    # --------------------------------------------------

    def load_persisted_abilities(self):
        """Scans custom_abilities directory and loads saved code upon app startup."""
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                file_path = os.path.join(self.storage_dir, filename)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        handler = getattr(module, "run", None) or getattr(module, module_name, None)
                        if callable(handler):
                            ability = Ability(
                                name=module_name,
                                description=getattr(module, "DESCRIPTION", "Auto-restored self-written ability."),
                                handler=handler,
                                semantic_tags=getattr(module, "TAGS", [module_name])
                            )
                            self.brain.register(ability)
                except Exception as e:
                    print(f"[Self-Update Loader] Failed to load {filename}: {e}")