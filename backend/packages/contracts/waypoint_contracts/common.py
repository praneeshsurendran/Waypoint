"""Shared schema utilities."""

from __future__ import annotations


from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, JsonValue

T = TypeVar("T")


class ContractModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class OrmModel(ContractModel):
    model_config = ConfigDict(from_attributes=True)


class Page(ContractModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorDetail(ContractModel):
    code: str
    message: str
    details: dict[str, JsonValue] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ValidationIssue(ContractModel):
    loc: list[str | int]
    msg: str
    type: str


class HttpErrorResponse(ContractModel):
    detail: ErrorDetail | str | list[ValidationIssue]
