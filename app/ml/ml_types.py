from typing import Any
from datetime import datetime


# Can have any configuration like timestamp, baselines, multipliers, etc.
InternalState = dict[str, Any]

# Format: (timestamp, impressions, clicks, conversions)
DataPacket = tuple[datetime, int, int, int]