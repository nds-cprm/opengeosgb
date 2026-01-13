# Notes

## URLs as UUID5

```Python
import uuid

namespace = uuid.NAMESPACE_URL
name = 'https://geosgb.sgb.gov.br/geosgb/wms.html'

uuid5_value = uuid.uuid5(namespace, name)

print(f"UUID5: {uuid5_value}")
# UUID5: 2f7258dc-2f0e-55c1-810f-4d7ec929db52
```

## UUID discussion on DSpace REST
- https://github.com/DSpace/RestContract/issues/1

## PyOAI (Best suited OAP-PMH Client)
- PyPI: https://pypi.org/project/pyoai/
- Client example: https://github.com/infrae/pyoai/blob/master/doc/oaiclient.py
- DSpace Docs: https://wiki.lyrasis.org/pages/viewpage.action?pageId=315720673

