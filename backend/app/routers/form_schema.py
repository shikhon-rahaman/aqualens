"""Form schema endpoint."""

from fastapi import APIRouter

from app.form_schema import FormSchemaResponse, get_form_schema

router = APIRouter(prefix="/api", tags=["form-schema"])


@router.get("/form-schema", response_model=FormSchemaResponse)
def form_schema() -> FormSchemaResponse:
    return get_form_schema()
