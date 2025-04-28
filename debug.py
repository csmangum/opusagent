from app.transitions.registry import TransitionRegistry
from app.transitions.base import BaseTransition

class MockTransition(BaseTransition):
    def __init__(self, source_state, target_state, priority=0, description=''):
        super().__init__(source_state, target_state, priority, description)
    
    def evaluate(self, context):
        return 1.0

registry = TransitionRegistry()
t1 = MockTransition('state1', 'state2', 5)
t2 = MockTransition('state1', 'state3', 3)
t3 = MockTransition('state2', 'state3', 1)
t4 = MockTransition('state3', 'state1', 2)

registry.register_many([t1, t2, t3, t4])
errors = registry.validate()

print(f'Number of errors: {len(errors)}')
for error in errors:
    print(f'Error: {error}')

# Print information about registered transitions and validation logic
print("\nRegistered transitions:")
for t in registry.get_all_transitions():
    print(f"- {t.source_state} -> {t.target_state} (priority {t.priority})")

print("\nChecking potential cycles:")
for t in registry.get_all_transitions():
    reverse_transitions = registry.get_transitions_between_states(t.target_state, t.source_state)
    if reverse_transitions:
        print(f"Found reverse for {t.source_state}->{t.target_state} (priority {t.priority}):")
        for rev in reverse_transitions:
            is_problematic = rev.priority > t.priority
            print(f"  - {rev.source_state}->{rev.target_state} (priority {rev.priority})")
            print(f"  - Is problematic: {is_problematic}")
            if is_problematic:
                print(f"  - Would report: Possible priority cycle between '{rev.source_state}' and '{rev.target_state}'") 