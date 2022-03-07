import functools

from django.core.cache import cache


def lock(lock_id, timeout=30):
    return cache.add(lock_id, 'true', timeout)


def release(lock_id):
    cache.delete(lock_id)


def lock_run_task(timeout, lock_flag="serial_task"):
    def wrapper(func):
        @functools.wraps(func)
        def lock_run(*args, **kwargs):
            lock_id = "{0}-lock-0".format(lock_flag)
            is_locked = lock(lock_id, timeout)
            try:
                if is_locked:
                    return func(*args, **kwargs)
            finally:
                if is_locked:
                    release(lock_id)
        return lock_run
    return wrapper
