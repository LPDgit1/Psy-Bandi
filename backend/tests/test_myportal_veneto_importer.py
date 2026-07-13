import httpx

from app.importers.myportal_veneto import TREVISO, _attachment_refs, _fetch_records, _official_url


def test_attachment_refs_keep_public_bando_and_exclude_candidate_materials() -> None:
    attachments = _attachment_refs(
        TREVISO,
        [
            {
                "dyn_str_autobind_allegati_name": "bando psicologo.pdf",
                "dyn_str_association_allegati_uuid": "doc-1",
            },
            {
                "dyn_str_autobind_allegati_name": "elenco candidati ammessi.pdf",
                "dyn_str_association_allegati_uuid": "doc-2",
            },
        ],
    )

    assert attachments == [
        {
            "title": "bando psicologo.pdf",
            "url": (
                "https://www.comune.treviso.it/myportal/C_L407/api/content/download"
                "?id=doc-1"
            ),
            "file_type": "pdf",
        }
    ]


def test_fetch_records_uses_paginated_public_catalog() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["type"] == "AT_myp_bandi_concorso"
        assert request.url.params["parent"].endswith("/InAtto")
        page = request.url.params["pageIndex"]
        entities = [{"id": f"record-{page}"}] if page in {"1", "2"} else []
        return httpx.Response(
            200,
            json={"page": {"entities": entities, "entitiesCount": 2}},
        )

    with httpx.Client(
        base_url=TREVISO.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        records = _fetch_records(client, TREVISO)

    assert [record["id"] for record in records] == ["record-1", "record-2"]


def test_official_url_uses_public_canonical_detail() -> None:
    assert _official_url(
        TREVISO,
        {"sys_canonical_url": "/amministrazionetrasparente-info/bando-psicologo"},
    ) == "https://www.comune.treviso.it/amministrazionetrasparente-info/bando-psicologo"
