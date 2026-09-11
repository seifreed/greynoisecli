import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote

_PATH_PARAMETER = re.compile(r"{([^}]+)}")


def _command_name(operation_id: str) -> str:
    normalized = operation_id.replace("IPs", "Ips").replace("CVEs", "Cves")
    words = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", normalized)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", words).lower()


@dataclass(frozen=True, slots=True)
class Endpoint:
    operation_id: str
    method: str
    path: str
    summary: str
    accept: str = "application/json"

    @property
    def command(self) -> str:
        return _command_name(self.operation_id)

    @property
    def path_parameters(self) -> tuple[str, ...]:
        return tuple(_PATH_PARAMETER.findall(self.path))

    def format_path(self, values: Mapping[str, str]) -> str:
        expected = set(self.path_parameters)
        missing = expected - values.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Missing path parameter(s): {names}")
        unexpected = values.keys() - expected
        if unexpected:
            names = ", ".join(sorted(unexpected))
            raise ValueError(f"Unexpected path parameter(s): {names}")
        return self.path.format_map(
            {name: quote(value, safe="") for name, value in values.items()}
        )


ENDPOINTS = (
    Endpoint(
        "AcknowledgeFeedEvents",
        "POST",
        "/v3/feeds/{feed_id}/events/ack",
        "Acknowledge a processed feed-event batch",
    ),
    Endpoint("bulkCVELookup", "POST", "/v3/cves", "Bulk CVE Lookup"),
    Endpoint(
        "CallbackExportIPs",
        "POST",
        "/v1/callback/export-ips",
        "Export Callback IPs",
        "text/plain",
    ),
    Endpoint("CallbackGetIP", "GET", "/v1/callback/ip/{ip}", "Callback IP Lookup"),
    Endpoint("CallbackListIPs", "POST", "/v1/callback/ips", "List Callback IPs"),
    Endpoint(
        "CallbackOverview",
        "POST",
        "/v1/callback/overview",
        "Callback Overview Statistics",
    ),
    Endpoint(
        "CreateBlocklist",
        "POST",
        "/v3/workspaces/{workspace_id}/blocklists",
        "Create Blocklist",
    ),
    Endpoint(
        "CreateEventFeedConsumer",
        "POST",
        "/v3/feeds/{feed_id}/consumers",
        "Create a feed-event consumer",
    ),
    Endpoint(
        "DeleteBlocklist",
        "DELETE",
        "/v3/workspaces/{workspace_id}/blocklists/{blocklist_id}",
        "Delete Blocklist",
    ),
    Endpoint(
        "DeleteEventFeedConsumer",
        "DELETE",
        "/v3/feeds/{feed_id}/consumers/{consumer}",
        "Delete a feed-event consumer",
    ),
    Endpoint(
        "exportSessionData",
        "GET",
        "/v3/sessions/{session_id}/export",
        "Export Session Data",
        "application/octet-stream",
    ),
    Endpoint(
        "exportSessionsPcap",
        "GET",
        "/v3/sessions/export",
        "Export PCAP for Multiple Sessions",
        "application/vnd.tcpdump.pcap",
    ),
    Endpoint(
        "FetchFeedEvents",
        "GET",
        "/v3/feeds/{feed_id}/events",
        "Fetch the next feed-event batch",
    ),
    Endpoint(
        "generateRSSFeedToken",
        "POST",
        "/v3/articles/rss-token",
        "Generate RSS Feed URL",
    ),
    Endpoint("getArticle", "GET", "/v3/articles/{id}", "Get Article"),
    Endpoint(
        "GetBlocklist",
        "GET",
        "/v3/workspaces/{workspace_id}/blocklists/{blocklist_id}",
        "Get Blocklist",
    ),
    Endpoint(
        "GetBlocklistIPs",
        "GET",
        "/v3/workspaces/{workspace_id}/blocklists/{blocklist_id}/ips",
        "Get Blocklist IPs",
    ),
    Endpoint("getBSIBulkLookup", "POST", "/v3/bsi/bulk", "BSI Bulk IP Lookup"),
    Endpoint("getBSICategory", "GET", "/v3/bsi/category", "BSI Category Stats"),
    Endpoint("getBSICompany", "GET", "/v3/bsi/company", "BSI Company Stats"),
    Endpoint(
        "getBSIDownload",
        "GET",
        "/v3/bsi/download",
        "BSI Bulk Data Download",
        "application/gzip",
    ),
    Endpoint("getBSILookup", "GET", "/v3/bsi/lookup", "BSI Single-IP Lookup"),
    Endpoint("getBSITrust", "GET", "/v3/bsi/trust", "BSI Trust-Level Stats"),
    Endpoint("getCommunityIP", "GET", "/v3/community/{ip}", "Community API"),
    Endpoint("getCVE", "GET", "/v1/cve/{cve_id}", "Retrieve CVE Information"),
    Endpoint(
        "getIPTimelineFieldSummary",
        "GET",
        "/v3/noise/ips/{ip}/timeline",
        "IP Timeline Field Summary",
    ),
    Endpoint(
        "getPrivateRSSFeed",
        "GET",
        "/v3/articles/rss/{token}",
        "Private RSS Feed",
        "application/rss+xml",
    ),
    Endpoint(
        "getPublicRSSFeed",
        "GET",
        "/v3/articles/rss",
        "Public RSS Feed",
        "application/rss+xml",
    ),
    Endpoint("getRSSFeedToken", "GET", "/v3/articles/rss-token", "Get RSS Feed URL"),
    Endpoint("getSessionById", "GET", "/v3/sessions/{session_id}", "Get Session by ID"),
    Endpoint(
        "getSessionConnections",
        "GET",
        "/v3/sessions/connections",
        "Get Session Connections",
    ),
    Endpoint("getSessionCounts", "GET", "/v3/sessions/counts", "Get Session Counts"),
    Endpoint("getSessionFields", "GET", "/v3/sessions/fields", "Get Session Fields"),
    Endpoint(
        "getSessionPcap",
        "GET",
        "/v3/sessions/{session_id}/frames",
        "Get Session PCAP",
        "application/vnd.tcpdump.pcap",
    ),
    Endpoint(
        "getSessionTimeseries",
        "GET",
        "/v3/sessions/timeseries",
        "Get Session Timeseries",
    ),
    Endpoint(
        "getSessionUniqueValues",
        "GET",
        "/v3/sessions/unique",
        "Get Unique Field Values",
        "text/csv",
    ),
    Endpoint("getSessions", "GET", "/v3/sessions", "Get Sessions"),
    Endpoint(
        "GetTacticsDetection",
        "GET",
        "/v3/workspaces/{workspace_id}/tactics/{detection_id}",
        "Get Tactics Detection",
    ),
    Endpoint(
        "GetTacticsHostArtifactContent",
        "POST",
        "/v3/workspaces/{workspace_id}/host-artifact/content",
        "Get Host Artifact Content",
    ),
    Endpoint(
        "GetUniqueIPsJobStatus",
        "GET",
        "/v3/workspaces/unique-ips/{job_id}",
        "Get Unique IPs Job Status",
    ),
    Endpoint("gnqlTimeSeries", "GET", "/v3/gnql/timeseries", "GNQL V3 Recall"),
    Endpoint(
        "gnqlTimeSeriesStats",
        "GET",
        "/v3/gnql/timeseries/stats",
        "GNQL V3 Recall Stats",
    ),
    Endpoint("gnqlV3Count", "GET", "/v3/gnql/count", "GNQL V3 Count"),
    Endpoint("gnqlV3ExportIPs", "GET", "/v3/gnql/ips", "GNQL V3 IP Export"),
    Endpoint(
        "gnqlV3MetadataQuery", "GET", "/v3/gnql/metadata", "GNQL V3 Metadata Query"
    ),
    Endpoint("gnqlV3Query", "GET", "/v3/gnql", "GNQL V3 Query"),
    Endpoint("gnqlV3Stats", "GET", "/v3/gnql/stats", "GNQL V3 Stats"),
    Endpoint("gnqlV3Validate", "POST", "/v3/gnql/validate", "Validate GNQL Query"),
    Endpoint(
        "listArticleCategories", "GET", "/v3/articles/categories", "List Categories"
    ),
    Endpoint("listArticles", "GET", "/v3/articles", "List Articles"),
    Endpoint(
        "ListBlocklists",
        "GET",
        "/v3/workspaces/{workspace_id}/blocklists",
        "List Blocklists",
    ),
    Endpoint("listCVEs", "GET", "/v3/cves/list", "List CVEs"),
    Endpoint(
        "ListEventFeedConsumers",
        "GET",
        "/v3/feeds/{feed_id}/consumers",
        "List feed-event consumers",
    ),
    Endpoint(
        "ListTacticsDetectionDestinationIPs",
        "GET",
        "/v3/workspaces/{workspace_id}/tactics/{detection_id}/dest-ips",
        "List Tactics Detection Destination IPs",
    ),
    Endpoint(
        "ListTacticsDetectionFiles",
        "POST",
        "/v3/workspaces/{workspace_id}/tactics/{detection_id}/files",
        "List Tactics Detection Files",
    ),
    Endpoint("listTags", "GET", "/v3/tags", "List Tags"),
    Endpoint("ping", "GET", "/ping", "Ping"),
    Endpoint(
        "postPsychicModelDownload",
        "POST",
        "/v1/psychic",
        "Psychic Model Download",
        "application/octet-stream",
    ),
    Endpoint(
        "postPsychicSnapshotDownload",
        "POST",
        "/v1/psychic/snapshots",
        "Psychic Snapshot Download",
        "application/octet-stream",
    ),
    Endpoint(
        "ResetEventFeedConsumer",
        "POST",
        "/v3/feeds/{feed_id}/consumers/{consumer}/reset",
        "Reset a feed-event consumer",
    ),
    Endpoint(
        "SearchFeedEvents",
        "POST",
        "/v3/feeds/events/search",
        "Search retained feed events",
    ),
    Endpoint(
        "SearchTacticsDetections",
        "POST",
        "/v3/workspaces/{workspace_id}/tactics",
        "Search Tactics Detections",
    ),
    Endpoint(
        "StartUniqueIPsJob", "POST", "/v3/workspaces/unique-ips", "Start Unique IPs Job"
    ),
    Endpoint(
        "UpdateBlocklist",
        "PUT",
        "/v3/workspaces/{workspace_id}/blocklists/{blocklist_id}",
        "Update Blocklist",
    ),
    Endpoint("V3IP", "GET", "/v3/ip/{ip}", "IP Lookup"),
    Endpoint("V3MultiIP", "POST", "/v3/ip", "IP Lookup - Multi"),
    Endpoint("WorkspaceDiff", "POST", "/v3/workspaces/diff", "Workspace Diff"),
    Endpoint(
        "WorkspaceStatsDiff",
        "POST",
        "/v3/workspaces/stats-diff",
        "Workspace Stats Diff",
    ),
)

ENDPOINTS_BY_NAME = {endpoint.command: endpoint for endpoint in ENDPOINTS}
ENDPOINTS_BY_ID = {endpoint.operation_id: endpoint for endpoint in ENDPOINTS}


def get_endpoint(name: str) -> Endpoint:
    endpoint = ENDPOINTS_BY_NAME.get(name) or ENDPOINTS_BY_ID.get(name)
    if endpoint is None:
        raise KeyError(f"Unknown GreyNoise operation: {name}")
    return endpoint
