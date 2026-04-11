from fastapi import HTTPException, status


class PropertyNotFoundError(HTTPException):
    def __init__(self, property_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property '{property_id}' not found.",
        )


class AddressNotFoundError(HTTPException):
    def __init__(self, address: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address could not be resolved: '{address}'",
        )


class ValuationNotFoundError(HTTPException):
    def __init__(self, valuation_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valuation '{valuation_id}' not found.",
        )


class ValuationFailedError(HTTPException):
    def __init__(self, reason: str = "Insufficient comparable data."):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Valuation could not be completed: {reason}",
        )


class ReportNotReadyError(HTTPException):
    def __init__(self, valuation_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report for valuation '{valuation_id}' is not yet ready.",
        )


class ExternalAPIError(HTTPException):
    def __init__(self, service: str, detail: str = ""):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream error from {service}. {detail}".strip(),
        )
