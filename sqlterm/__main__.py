"""
module sqlterm.__main__

Default entrypoint when sqlterm is invoked on the console by a user.
Calls the main() function in sqlterm.entrypoint
"""

import sys

from .entrypoint import main

sys.exit(main())
