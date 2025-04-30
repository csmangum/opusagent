from fastagent.transitions.registry import TransitionRegistry
from fastagent.transitions.base import BaseTransition

class MockTransition(BaseTransition):
    def __init__(self, source_state, target_state, priority=0, description=''):
        super().__init__(source_state, target_state, priority, description)
    
    def evaluate(self, context):
        return 1.0

registry = TransitionRegistry()
t1 = MockTransition('state1', 'state2', 5, 'Transition 1')
circular = MockTransition('state2', 'state1', 6, 'High priority circular')

registry.register_many([t1, circular])
errors = registry.validate()

print(f'Number of errors: {len(errors)}')
for error in errors:
    print(f'Error: {error}')

print("\nRegistered transitions:")
for t in registry.get_all_transitions():
    print(f"- {t.source_state} -> {t.target_state} (priority {t.priority})")

print("\nChecking potential cycles:")
for t in registry.get_all_transitions():
    reverse_transitions = registry.get_transitions_between_states(t.target_state, t.source_state)
    if reverse_transitions:
        print(f"Found reverse for {t.source_state}->{t.target_state} (priority {t.priority}):")
        for rev in reverse_transitions:
            is_problematic = rev.priority - t.priority >= 2 or rev.priority >= 6 or t.priority >= 6
            print(f"  - {rev.source_state}->{rev.target_state} (priority {rev.priority})")
            print(f"  - Is problematic: {is_problematic}")
            if is_problematic:
                print(f"  - Would report: Possible priority cycle between '{rev.source_state}' and '{rev.target_state}'") 