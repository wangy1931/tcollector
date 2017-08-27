# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import platform
import re
import uuid

# 3p
import yaml  # noqa, let's guess, probably imported somewhere

# These classes are now in utils/, they are just here for compatibility reasons,
# if a user actually uses them in a custom check
# If you're this user, please use utils/* instead
# FIXME: remove them at a point (6.x)

COLON_NON_WIN_PATH = re.compile(':(?!\\\\)')

log = logging.getLogger(__name__)

NumericTypes = (float, int, long)




def cast_metric_val(val):
    # ensure that the metric value is a numeric type
    if not isinstance(val, NumericTypes):
        # Try the int conversion first because want to preserve
        # whether the value is an int or a float. If neither work,
        # raise a ValueError to be handled elsewhere
        for cast in [int, float]:
            try:
                val = cast(val)
                return val
            except ValueError:
                continue
        raise ValueError
    return val

_IDS = {}




