"""Synthetic READ-ONLY AWS/B2 version inventory for 30d/8w/12m GFS."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import s02_gfs_cloud_inventory_v0_1 as inv
from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as m


ID_A = "backup-" + "a" * 32
ID_B = "backup-" + "b" * 32


def fake_data_key(bid):
    return m.OBJECT_PREFIX + bid + "/" + "f"*64 + ".aesgcm"


class Reader:
    def __init__(self, ids, provider):
        self.ids = ids
        self.provider = provider
        self.calls = []
        self.override = None

    def list_object_versions(self, **params):
        self.calls.append(params)
        if self.override is not None:
            return self.override(params)
        kind = "data" if params["Prefix"] == m.OBJECT_PREFIX else "manifest"
        objects = []
        for n, bid in enumerate(sorted(self.ids)):
            key = fake_data_key(bid) if kind == "data" else m._manifest_key(bid)
            objects.append({
                "Key":key, "VersionId":self.provider + "-ver-" + str(n),
                "IsLatest":True, "Size":120,
            })
        return {"IsTruncated":False, "Versions":objects, "DeleteMarkers":[]}


def test_two_provider_complete_inventory_is_read_only():
    a = Reader({ID_A, ID_B}, "aws")
    b = Reader({ID_A, ID_B}, "b2")
    out = inv.audit_provider_pair(
        aws_reader=a,b2_reader=b,expected_backup_ids={ID_A,ID_B}
    )
    assert out["backup_ids_seen"] == 2
    assert out["aws_object_versions_seen"] == 4
    assert out["b2_object_versions_seen"] == 4
    assert out["exact_versions_enumerated_in_memory"] is True
    assert out["cloud_deletion_authorized"] is False
    assert out["provider_deletions_performed"] == 0
    assert len(a.calls) == len(b.calls) == 2
    assert {x["Prefix"] for x in a.calls} == {
        m.OBJECT_PREFIX,m.MANIFEST_PREFIX
    }
    assert not any("VersionId" in x for x in a.calls)


def test_missing_or_unknown_cloud_backup_forces_hold():
    a=Reader({ID_A,ID_B}, "aws")
    b=Reader({ID_A}, "b2")
    with pytest.raises(inv.CloudInventoryRejected, match="history incomplete"):
        inv.audit_provider_pair(
            aws_reader=a,b2_reader=b,expected_backup_ids={ID_A,ID_B}
        )
    b=Reader({ID_A,ID_B}, "b2")
    with pytest.raises(inv.CloudInventoryRejected, match="history incomplete"):
        inv.audit_provider_pair(
            aws_reader=a,b2_reader=b,expected_backup_ids={ID_A}
        )


@pytest.mark.parametrize("payload", [
    {"IsTruncated":False, "Versions":[{"Key":fake_data_key(ID_A),
                                      "VersionId":"v1","IsLatest":False,"Size":20}]},
    {"IsTruncated":False, "Versions":[], "DeleteMarkers":[{"Key":"unknown"}]},
    {"IsTruncated":False, "Versions":[{"Key":"pilot/vowsig/approved-s02/v1/WRONG",
                                      "VersionId":"v1","IsLatest":True,"Size":20}]},
    {"IsTruncated":False, "Versions":[{"Key":fake_data_key(ID_A),
                                      "VersionId":"v1","IsLatest":True,"Size":0}]},
    {"IsTruncated":True, "Versions":[]},
    {"IsTruncated":"yes", "Versions":[]},
])
def test_malformed_or_ambiguous_version_inventory_fails_closed(payload):
    a=Reader({ID_A},"aws")
    a.override=lambda params: payload
    b=Reader({ID_A},"b2")
    with pytest.raises(inv.CloudInventoryRejected):
        inv.audit_provider_pair(
            aws_reader=a,b2_reader=b,expected_backup_ids={ID_A}
        )


def test_duplicate_object_version_rejected():
    a=Reader({ID_A},"aws")
    one={"Key":fake_data_key(ID_A),"VersionId":"v1","IsLatest":True,"Size":20}
    def dup(params):
        return {"IsTruncated":False,"Versions":[one,dict(one,VersionId="v2")],
                "DeleteMarkers":[]}
    a.override=dup
    with pytest.raises(inv.CloudInventoryRejected):
        inv.audit_provider_pair(aws_reader=a,
            b2_reader=Reader({ID_A},"b2"),expected_backup_ids={ID_A})


def test_failed_list_permission_is_sanitized():
    a=Reader({ID_A},"aws")
    def denied(params):
        raise RuntimeError("private temporary S3 authentication error")
    a.override=denied
    with pytest.raises(inv.CloudInventoryRejected) as exc:
        inv.audit_provider_pair(
            aws_reader=a,b2_reader=Reader({ID_A},"b2"),
            expected_backup_ids={ID_A}
        )
    assert "private temporary" not in str(exc.value)


def test_inventory_never_uses_delete_or_upload_api():
    tree=ast.parse(inspect.getsource(inv))
    forbidden={"delete_object","delete_objects","put_object",
               "put_bucket_lifecycle_configuration"}
    assert not any(
        isinstance(n,ast.Attribute) and n.attr in forbidden
        for n in ast.walk(tree)
    )
