import pytest

from greynoisecli import ENDPOINTS
from greynoisecli.endpoints import get_endpoint
from tests.support import expect

EXPECTED_ENDPOINT_COUNT = 68
EXPECTED_NON_JSON_ACCEPT = {
    "CallbackExportIPs": "text/plain",
    "exportSessionData": "application/octet-stream",
    "exportSessionsPcap": "application/vnd.tcpdump.pcap",
    "getBSIDownload": "application/gzip",
    "getPrivateRSSFeed": "application/rss+xml",
    "getPublicRSSFeed": "application/rss+xml",
    "getSessionPcap": "application/vnd.tcpdump.pcap",
    "getSessionUniqueValues": "text/csv",
    "postPsychicModelDownload": "application/octet-stream",
    "postPsychicSnapshotDownload": "application/octet-stream",
}


def test_endpoint_catalog() -> None:
    expect(len(ENDPOINTS) == EXPECTED_ENDPOINT_COUNT)
    expect(
        len({endpoint.operation_id for endpoint in ENDPOINTS})
        == EXPECTED_ENDPOINT_COUNT
    )
    commands = [endpoint.command for endpoint in ENDPOINTS]
    expect(len(set(commands)) == EXPECTED_ENDPOINT_COUNT)
    expect(commands == sorted(commands))
    for item in ENDPOINTS:
        expect(
            item.accept
            == EXPECTED_NON_JSON_ACCEPT.get(item.operation_id, "application/json")
        )
    endpoint = get_endpoint("get-community-ip")
    expect(get_endpoint("getCommunityIP") is endpoint)
    expect(endpoint.path_parameters == ("ip",))
    expect(endpoint.format_path({"ip": "1.2.3.4/a"}) == "/v3/community/1.2.3.4%2Fa")
    with pytest.raises(ValueError, match="ip"):
        endpoint.format_path({})
    with pytest.raises(ValueError, match="extra"):
        endpoint.format_path({"ip": "1.2.3.4", "extra": "value"})
    with pytest.raises(KeyError, match="Unknown GreyNoise operation"):
        get_endpoint("missing")
