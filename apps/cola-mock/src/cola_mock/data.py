from .models import ApplicationFacts, ApplicationStatus, ApprovedPanel, ColaApplication


WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


def _application(
    application_id: str,
    brand: str,
    class_type: str,
    abv: float,
    volume: int,
    *,
    fanciful: str | None = None,
    status: ApplicationStatus = ApplicationStatus.ASSIGNED,
    imported: bool = False,
    country: str | None = None,
    warning: str = WARNING,
    applicant: str = "Example Spirits Company",
    address: str = "100 Market Street, Louisville, KY 40202",
    aliases: list[str] | None = None,
) -> ColaApplication:
    short_id = application_id.rsplit("_", 1)[-1]
    facts = ApplicationFacts(
        brand_name=brand,
        fanciful_name=fanciful,
        class_type=class_type,
        abv=abv,
        net_contents_ml=volume,
        responsible_party=applicant,
        address=address,
        imported=imported,
        country_of_origin=country,
        government_warning=warning,
    )
    front = "\n".join(filter(None, [brand, fanciful, class_type, f"{abv:g}% ALC/VOL", f"{volume} mL"]))
    back = "\n".join(filter(None, [applicant, address, f"PRODUCT OF {country}" if country else None, warning]))
    return ColaApplication(
        application_id=application_id,
        revision=1,
        status=status,
        serial_number=f"2026-{short_id}",
        permit_number=f"DSP-KY-{short_id.zfill(4)}",
        source="imported" if imported else "domestic",
        applicant_name=applicant,
        facts=facts,
        aliases=aliases or [],
        approved_panels=[
            ApprovedPanel(panel_id="front", panel_type="brand", width_inches=3, height_inches=4, text=front),
            ApprovedPanel(panel_id="back", panel_type="other", width_inches=3, height_inches=4, text=back),
        ],
    )


def seeded_applications() -> list[ColaApplication]:
    """Return fresh synthetic records; no object is shared across demo sessions."""
    return [
        _application("mock_ttb_001", "North Star", "Straight Bourbon Whisky", 40, 750, fanciful="Reserve"),
        _application("mock_ttb_002", "North Star", "Straight Bourbon Whisky", 45, 750, fanciful="Cask Strength"),
        _application("mock_ttb_003", "North Star", "Straight Bourbon Whisky", 40, 1000, fanciful="Reserve"),
        _application(
            "mock_ttb_004", "Harbour Light", "London Dry Gin", 43, 750,
            status=ApplicationStatus.CORRECTED, imported=True, country="United Kingdom",
            applicant="Harbour Imports LLC", address="8 Pier Avenue, Boston, MA 02110",
            aliases=["Harbor Light"],
        ),
        _application(
            "mock_ttb_005", "Harbor Light", "London Dry Gin", 43, 750,
            imported=True, country="Canada", applicant="Harbor Beverage Imports LLC",
            address="12 Pier Avenue, Boston, MA 02110", aliases=["Harbour Light"],
        ),
        _application(
            "mock_ttb_006", "Cedar Ridge", "Vodka", 40, 750,
            warning="GOVERNMENT WARNING: Consumption may impair driving.",
            applicant="Cedar Ridge Distilling", address="7 Cedar Road, Austin, TX 78701",
        ),
        # Mock operational state derived from a public, surrendered COLA sample.
        # The real registry is read-only and never receives prototype decisions.
        _application(
            "sample_ttb_11038001000659", "Seven Fathoms", "Premium Rum", 40, 750,
            status=ApplicationStatus.ASSIGNED, imported=True, country="Cayman Islands",
            applicant="Luxe Vintages, Luxe Collections L.L.C.",
            address="298 NE Wavecrest Ct, Boca Raton, FL 33432",
            aliases=["Seven Fathoms Rum"],
        ),
    ]
