"""
Migration Guide for OpusAgent Centralized Configuration

This script demonstrates how to migrate from the old scattered configuration
approach to the new centralized configuration system.
"""

def show_migration_examples():
    """Show side-by-side examples of old vs new configuration usage."""
    
    print("=== OpusAgent Configuration Migration Guide ===\n")
    
    print("1. BASIC CONFIGURATION ACCESS")
    print("=" * 50)
    print("OLD (scattered):")
    print("""
from opusagent.config.constants import DEFAULT_SAMPLE_RATE, VOICE
from opusagent.config.websocket_config import WebSocketConfig
from opusagent.vad.vad_config import load_vad_config
import os

# Getting various configs
sample_rate = DEFAULT_SAMPLE_RATE
voice = VOICE
websocket_config = WebSocketConfig()
vad_config = load_vad_config()
openai_key = os.getenv("OPENAI_API_KEY")
""")
    
    print("NEW (centralized):")
    print("""
from opusagent.config import get_config, audio_config, openai_config, vad_config

# Single source of truth
config = get_config()

# Type-safe access
sample_rate = config.audio.sample_rate
openai_key = config.openai.api_key
vad_settings = config.vad
websocket_settings = config.websocket

# Or use convenience functions
audio = audio_config()
openai = openai_config()
vad = vad_config()
""")
    
    print("\n2. ENVIRONMENT VARIABLE HANDLING")
    print("=" * 50)
    print("OLD (manual):")
    print("""
import os

# Scattered environment variable access
host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", "8000"))
log_level = os.getenv("LOG_LEVEL", "INFO")
vad_enabled = os.getenv("VAD_ENABLED", "true").lower() == "true"
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-realtime-preview-2024-12-17")
""")
    
    print("NEW (automatic):")
    print("""
from opusagent.config import get_config

# All environment variables loaded automatically with type conversion
config = get_config()

host = config.server.host
port = config.server.port  # Already converted to int
log_level = config.logging.level  # Enum type
vad_enabled = config.vad.enabled  # Already converted to bool
openai_model = config.openai.model
""")
    
    print("\n3. VALIDATION")
    print("=" * 50)
    print("OLD (manual):")
    print("""
import os

# Manual validation
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OpenAI API key required")

port = int(os.getenv("PORT", "8000"))
if port <= 0 or port > 65535:
    raise ValueError("Invalid port")
""")
    
    print("NEW (automatic):")
    print("""
from opusagent.config import validate_configuration, get_config

# Automatic validation
errors = validate_configuration()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    exit(1)

# Or just get config (validation happens automatically)
config = get_config()
""")
    
    print("\n4. STATIC DATA ACCESS")
    print("=" * 50)
    print("OLD (manual file handling):")
    print("""
import json
import yaml

# Manual file loading
with open("scenarios.json") as f:
    scenarios = json.load(f)

with open("opusagent/local/audio/phrases_mapping.yml") as f:
    phrases = yaml.safe_load(f)
""")
    
    print("NEW (built-in loaders):")
    print("""
from opusagent.config import load_scenarios, load_phrases_mapping, get_phrases_by_scenario

# Automatic loading with caching
scenarios = load_scenarios()
phrases = load_phrases_mapping()

# Convenient access methods
customer_service_phrases = get_phrases_by_scenario("customer_service")
""")
    
    print("\n5. LEGACY COMPATIBILITY")
    print("=" * 50)
    print("If you need to maintain existing code, you can use legacy compatibility:")
    print("""
from opusagent.config import get_legacy_constants, get_legacy_vad_config

# Get constants in old format
constants = get_legacy_constants()
DEFAULT_SAMPLE_RATE = constants["DEFAULT_SAMPLE_RATE"]

# Get VAD config in old format
vad_config = get_legacy_vad_config()
""")
    
    print("\n6. CONFIGURATION SUMMARY")
    print("=" * 50)
    print("NEW (debugging and monitoring):")
    print("""
from opusagent.config import print_configuration_summary

# Print complete configuration overview
print_configuration_summary()
""")


def show_real_migration_example():
    """Show a real example of migrating a function."""
    
    print("\n\n=== REAL MIGRATION EXAMPLE ===\n")
    
    print("OLD CODE (from websocket_manager.py):")
    print("""
def _is_mock_mode(self) -> bool:
    return os.getenv("OPUSAGENT_USE_MOCK", "false").lower() == "true"

def _get_mock_server_url(self) -> str:
    return os.getenv("OPUSAGENT_MOCK_SERVER_URL", "ws://localhost:8080")
""")
    
    print("NEW CODE (using centralized config):")
    print("""
from opusagent.config import mock_config

def _is_mock_mode(self) -> bool:
    return mock_config().enabled

def _get_mock_server_url(self) -> str:
    return mock_config().server_url
""")
    
    print("\nOLD CODE (from main.py):")
    print("""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
VAD_ENABLED = os.getenv("VAD_ENABLED", "true").lower() in ("true", "1", "yes", "on")
""")
    
    print("NEW CODE (using centralized config):")
    print("""
from opusagent.config import get_config

config = get_config()
OPENAI_API_KEY = config.openai.api_key
PORT = config.server.port
HOST = config.server.host
VAD_ENABLED = config.vad.enabled
""")


if __name__ == "__main__":
    show_migration_examples()
    show_real_migration_example()
    
    print("\n\n=== TESTING THE NEW SYSTEM ===")
    try:
        from opusagent.config import print_configuration_summary
        print_configuration_summary()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Make sure you're running this from the project root directory.")