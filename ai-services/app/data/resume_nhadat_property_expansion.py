"""Transport-only URI encoding adapter; frozen collector/plan stay unchanged."""
import json
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import collect_property_expansion as collector
from collect_training_property_evidence import publish_record
from market_observations import canonical


def ascii_path(url):
    parsed = urlsplit(url)
    # Preserve existing escapes. This encodes the same URI, never follows an
    # alternative host/path, and never decodes %2F or other reserved characters.
    path = quote(parsed.path, safe="/%:@!$&'()*+,;=-._~")
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


class AsciiPathClient(collector.SourceClient):
    def fetch(self, url, check=True):
        return super().fetch(ascii_path(url), check)


def main():
    output = collector.ROOT / 'refresh_nhadat24h'
    if not (output / 'plan.json').exists():
        raise ValueError('Resume adapter requires an existing frozen plan')
    note = dict(adapter_sha256=collector.cafe.sha(Path(__file__)),
        collector_sha256=collector.cafe.sha(collector.__file__),
        original_plan_sha256=collector.cafe.sha(output / 'plan.json'),
        semantics='Percent-encode non-ASCII path characters; preserve host, ID, escapes, robots and bounds')
    path = output / 'transport_adapter.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf8')) != note:
            raise ValueError('Transport adapter changed; prior receipt preserved')
    else:
        publish_record(path, note)
    result = collector.refresh('nhadat24h', factory=AsciiPathClient)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['error'] else 0


if __name__ == '__main__':raise SystemExit(main())
