def tenant_options(organization_id: int | None) -> dict[str, int]:
    """Keep legacy call signatures; absent scope must never expose stored data."""
    if organization_id is None:
        return {}
    if type(organization_id) is not int or organization_id <= 0:
        raise ValueError("organization_id must be a positive Django integer ID.")
    return {"organization_id": organization_id}
