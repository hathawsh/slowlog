
"""Stack formatter that stops at __slowlog_barrier__."""

import traceback
import linecache


def print_stack(f, limit,
                file):  # @ReservedAssignment
    """Print the stack trace of a frame."""
    traceback.print_list(extract_stack(f, limit), file)


def extract_stack(f, limit):
    """Extract the raw traceback from the current stack frame."""
    res = []
    n = 0
    while f is not None and (limit is None or n < limit):
        lineno = f.f_lineno
        co = f.f_code
        filename = co.co_filename
        name = co.co_name
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        line = line.strip() if line else None
        res.append((filename, lineno, name, line))
        if f.f_locals.get('__slowlog_barrier__'):
            break
        f = f.f_back
        n = n + 1
    res.reverse()
    return res
