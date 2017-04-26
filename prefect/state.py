import functools
import prefect


def set_state_from(source_states):
    """
    Method decorator that indicates valid source states for a state transition

    @set_state_from(['A'])
    def to_b(self):
        return 'B'

    assert obj.state == 'A'
    obj.to_b()  # works

    assert obj.state == 'C'
    obj.to_b()  # fails
    """
    if isinstance(source_states, str):
        source_states = [source_states]

    def decorator(method):

        @functools.wraps(method)
        def inner(self, *args, **kwargs):
            old_state = self.state
            new_state = method(self, *args, **kwargs)
            if old_state not in source_states:
                raise ValueError(
                    "Can't change state from {} to {}".format(
                        old_state, new_state))
            self.state = new_state
            self.after_state_change(old_state, new_state)

        return inner

    return decorator


class State:

    _default_state = ''

    def __init__(self, initial_state=None, after_state_change=None):
        if not hasattr(type(self), '_default_state'):
            'State classes require a `_default_state` state class attribute.'

        if initial_state is None:
            initial_state = self._default_state
        self.state = initial_state
        self.after_state_change = after_state_change or (lambda *args: True)

    def __eq__(self, other):
        return (
            # match other State types
            (type(self) == type(other) and self.state == other.state)
            # match strings directly
            or (isinstance(other, str) and str(self) == other))

    def __str__(self):
        return self.state

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, self.state)


class FlowState(State):
    ACTIVE = 'ACTIVE'
    PAUSED = 'PAUSED'
    ARCHIVED = 'ARCHIVED'

    if prefect.config.get('flows', 'default_active'):
        _default_state = ACTIVE
    else:
        _default_state = PAUSED

    _all_states = set([
        ACTIVE,
        PAUSED,
        ARCHIVED,
    ])

    _unarchived_states = set([ACTIVE, PAUSED])

    @set_state_from(PAUSED)
    def activate(self):
        return self.ACTIVE

    @set_state_from(ACTIVE)
    def pause(self):
        return self.PAUSED

    @set_state_from(_unarchived_states)
    def archive(self):
        return self.ARCHIVED

    @set_state_from(ARCHIVED)
    def unarchive(self):
        return self.PAUSED


class TaskRunState(State):

    PENDING = _default_state = 'PENDING'
    PENDING_RETRY = 'PENDING_RETRY'
    SCHEDULED = 'SCHEDULED'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'
    SHUTDOWN = 'SHUTDOWN'

    _all_states = set(
        [
            SCHEDULED,
            PENDING,
            PENDING_RETRY,
            RUNNING,
            SUCCESS,
            FAILED,
            SKIPPED,
            SHUTDOWN,
        ])
    _started_states = set([RUNNING, SUCCESS, FAILED])
    _pending_states = set([PENDING, PENDING_RETRY, SCHEDULED])
    _running_states = set([RUNNING])
    _finished_states = set([SUCCESS, FAILED, SKIPPED, SHUTDOWN])
    _skipped_states = set([SKIPPED])
    _successful_states = set([SUCCESS, SKIPPED])
    _failed_states = set([FAILED])

    @set_state_from(_pending_states)
    def start(self):
        return self.RUNNING

    @set_state_from(_pending_states.union(_running_states))
    def succeed(self):
        return self.SUCCESS

    @set_state_from(_pending_states.union(_running_states))
    def fail(self):
        return self.FAILED

    @set_state_from(_pending_states)
    def skip(self):
        return self.SKIPPED

    @set_state_from(FAILED)
    def retry(self):
        return self.PENDING_RETRY

    @set_state_from(_pending_states)
    def schedule(self):
        return self.SCHEDULED

    @set_state_from(_all_states)
    def shutdown(self):
        return self.SHUTDOWN

    def is_started(self):
        return str(self) in self._started_states

    def is_pending(self):
        return str(self) in self._pending_states

    def is_running(self):
        return str(self) in self._running_states

    def is_finished(self):
        return str(self) in self._finished_states

    def is_successful(self):
        return str(self) in self._successful_states

    def is_skipped(self):
        return str(self) in self._skipped_states

    def is_failed(self):
        return str(self) in self._failed_states


class FlowRunState(State):
    _default_state = 'CREATED'
    SCHEDULED = 'SCHEDULED'
    PENDING = _default_state = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    SHUTDOWN = 'SHUTDOWN'

    _all_states = set(
        [
            SCHEDULED,
            PENDING,
            RUNNING,
            SUCCESS,
            FAILED,
            SHUTDOWN,
        ])

    _pending_states = set([SCHEDULED, PENDING])

    @set_state_from(_pending_states)
    def start(self):
        return self.RUNNING

    @set_state_from(_pending_states)
    def schedule(self):
        return self.SCHEDULED

    @set_state_from(_pending_states.union([RUNNING]))
    def succeed(self):
        return self.SUCCESS

    @set_state_from(_pending_states.union([RUNNING]))
    def fail(self):
        return self.FAILED

    @set_state_from(_all_states)
    def shutdown(self):
        return self.SHUTDOWN