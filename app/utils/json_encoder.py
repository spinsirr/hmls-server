import json
from datetime import datetime
import pytz

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def dumps(obj):
    return json.dumps(obj, cls=DateTimeEncoder)

def loads(s):
    def datetime_parser(dct):
        for k, v in dct.items():
            if isinstance(v, str):
                try:
                    dct[k] = datetime.fromisoformat(v)
                except (ValueError, TypeError):
                    pass
        return dct
    return json.loads(s, object_hook=datetime_parser) 