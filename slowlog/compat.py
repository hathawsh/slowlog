
import sys

if sys.version_info[0] >= 3:  # pragma no cover
    # Python 3
    from _thread import get_ident
    from io import StringIO
    from queue import Empty
    from queue import Queue
    from urllib.parse import quote

else:  # pragma no cover
    # Python 2
    from thread import get_ident
    from cStringIO import StringIO
    from Queue import Empty
    from Queue import Queue
    from urllib import quote
