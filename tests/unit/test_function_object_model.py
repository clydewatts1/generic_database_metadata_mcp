"""Unit tests for FunctionObject model creation and validation.

Tests verify:
- FunctionObject creation with valid inputs
- Name validation (PascalCase, max 100 chars, reserved words)
- Logic description validation (max 500 chars)
- JSON Schema validation for input/output schemas
- Domain scoping and profile tracking
- Timestamp and version initialization
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from src.models.base import FunctionObjectCreate, FunctionObject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_function_create() -> FunctionObjectCreate:
    """Create a valid FunctionObjectCreate instance for testing."""
    return FunctionObjectCreate(
        name="ExtractPersonalData",
        logic_description="Extracts personally identifiable information from raw user records.",
        input_schema={
            "type": "object",
            "properties": {
                "raw_record": {"type": "string"},
                "include_emails": {"type": "boolean"}
            },
            "required": ["raw_record"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "names": {"type": "array", "items": {"type": "string"}},
                "emails": {"type": "array", "items": {"type": "string"}}
            }
        },
        profile_id="user_finance_team"
    )


# ---------------------------------------------------------------------------
# T065.1a – FunctionObject Creation Tests
# ---------------------------------------------------------------------------

def test_create_function_object_with_valid_inputs():
    """Verify FunctionObjectCreate accepts valid inputs."""
    data = _valid_function_create()
    
    assert data.name == "ExtractPersonalData"
    assert data.logic_description == "Extracts personally identifiable information from raw user records."
    assert data.profile_id == "user_finance_team"
    assert "raw_record" in data.input_schema["required"]


def test_function_object_full_model_initialization():
    """Verify FunctionObject (full model) initializes with all fields."""
    data = _valid_function_create()
    
    # Convert to full model
    func_obj = FunctionObject(
        name=data.name,
        logic_description=data.logic_description,
        input_schema=data.input_schema,
        output_schema=data.output_schema,
        created_by_profile_id=data.profile_id
    )
    
    # Verify all fields initialized
    assert func_obj.id  # auto-generated UUID
    assert len(func_obj.id) == 36  # UUID v4 format
    assert func_obj.name == "ExtractPersonalData"
    assert func_obj.created_by_profile_id == "user_finance_team"
    assert func_obj.domain_scope == "Global"  # default
    assert func_obj.version == 1  # default
    assert isinstance(func_obj.created_at, datetime)
    assert func_obj.created_at.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# T065.1b – Name Validation Tests
# ---------------------------------------------------------------------------

def test_function_name_must_be_pascal_case():
    """Verify function names must be PascalCase (start with uppercase, alphanumeric+underscore)."""
    # Valid names
    valid_names = [
        "ExtractPersonalData",
        "Transform_SalaryToUSD",
        "MergeUserRecords2024",
        "A",  # single letter OK
    ]
    for name in valid_names:
        data = FunctionObjectCreate(
            name=name,
            logic_description="Valid name test",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
        assert data.name == name


def test_function_name_rejects_lowercase_start():
    """Verify function names cannot start with lowercase."""
    with pytest.raises(ValidationError) as exc_info:
        FunctionObjectCreate(
            name="extractPersonalData",  # lowercase start
            logic_description="Invalid name",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
    assert "string should match pattern" in str(exc_info.value).lower()


def test_function_name_rejects_invalid_chars():
    """Verify function names reject special characters (except underscore)."""
    invalid_names = [
        "Extract-Personal-Data",  # hyphens
        "Extract.PersonalData",   # dots
        "Extract PersonalData",   # spaces
        "Extract@PersonalData",   # special chars
    ]
    for name in invalid_names:
        with pytest.raises(ValidationError):
            FunctionObjectCreate(
                name=name,
                logic_description="Invalid name test",
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )


def test_function_name_rejects_reserved_names():
    """Verify reserved function names are rejected."""
    reserved = ["FunctionObject", "MetaType", "ObjectNode", "StigmergicEdge"]
    for reserved_name in reserved:
        with pytest.raises(ValidationError) as exc_info:
            FunctionObjectCreate(
                name=reserved_name,
                logic_description="Reserved name test",
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )
        assert "reserved" in str(exc_info.value).lower()


def test_function_name_max_length_100():
    """Verify function names are limited to 100 characters."""
    # Valid: exactly 100 chars
    valid_name = "A" + "B" * 99  # 100 chars total
    data = FunctionObjectCreate(
        name=valid_name,
        logic_description="Max length test",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    assert len(data.name) == 100
    
    # Invalid: 101 chars
    invalid_name = "A" + "B" * 100  # 101 chars total
    with pytest.raises(ValidationError):
        FunctionObjectCreate(
            name=invalid_name,
            logic_description="Too long",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )


# ---------------------------------------------------------------------------
# T065.1c – Logic Description Validation
# ---------------------------------------------------------------------------

def test_logic_description_required_and_max_500():
    """Verify logic_description is required and limited to 500 chars."""
    # Valid: 500 chars
    valid_desc = "X" * 500
    data = FunctionObjectCreate(
        name="ValidFunction",
        logic_description=valid_desc,
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    assert len(data.logic_description) == 500
    
    # Invalid: empty
    with pytest.raises(ValidationError):
        FunctionObjectCreate(
            name="InvalidFunction",
            logic_description="",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
    
    # Invalid: 501 chars
    with pytest.raises(ValidationError):
        FunctionObjectCreate(
            name="InvalidFunction",
            logic_description="X" * 501,
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )


# ---------------------------------------------------------------------------
# T065.1d – JSON Schema Validation Tests
# ---------------------------------------------------------------------------

def test_input_output_schemas_validate_json_schema_format():
    """Verify input/output schemas must be valid JSON Schema objects."""
    # Valid schemas (different formats)
    valid_schemas = [
        {"type": "object"},
        {"type": "string"},
        {"$ref": "#/definitions/User"},
        {"properties": {"name": {"type": "string"}}},
        {"items": {"type": "integer"}},
        {"oneOf": [{"type": "string"}, {"type": "integer"}]},
        {"anyOf": [{"type": "null"}, {"type": "object"}]},
    ]
    
    for schema in valid_schemas:
        data = FunctionObjectCreate(
            name="ValidSchema",
            logic_description="Valid schema test",
            input_schema=schema,
            output_schema=schema
        )
        assert data.input_schema == schema
        assert data.output_schema == schema


def test_input_output_schemas_reject_invalid_formats():
    """Verify invalid JSON Schema objects are rejected."""
    # Invalid: dict with no schema keywords
    invalid_schema = {"foo": "bar", "baz": 123}
    
    with pytest.raises(ValidationError) as exc_info:
        FunctionObjectCreate(
            name="InvalidSchema",
            logic_description="Invalid schema",
            input_schema=invalid_schema,
            output_schema={"type": "object"}
        )
    error_msg = str(exc_info.value).lower()
    assert "json schema" in error_msg


def test_input_output_schemas_require_dict():
    """Verify input and output schemas must be dictionaries."""
    # Invalid: list instead of dict
    with pytest.raises(ValidationError):
        FunctionObjectCreate(
            name="InvalidSchema",
            logic_description="List is not valid schema",
            input_schema=["type", "string"],
            output_schema={"type": "object"}
        )
    
    # Invalid: string instead of dict
    with pytest.raises(ValidationError):
        FunctionObjectCreate(
            name="InvalidSchema",
            logic_description="String is not valid schema",
            input_schema="string",
            output_schema={"type": "object"}
        )


# ---------------------------------------------------------------------------
# T065.1e – Domain Scoping and Profile Tracking
# ---------------------------------------------------------------------------

def test_function_object_domain_scope_defaults_to_global():
    """Verify domain_scope defaults to 'Global'."""
    func_obj = FunctionObject(
        name="TestFunction",
        logic_description="Test domain scope",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    assert func_obj.domain_scope == "Global"


def test_function_object_domain_scope_can_be_set():
    """Verify domain_scope can be set for domain-specific functions."""
    func_obj = FunctionObject(
        name="FinanceTransform",
        logic_description="Finance-specific transformation",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        domain_scope="Finance"
    )
    assert func_obj.domain_scope == "Finance"


def test_function_object_tracks_created_by_profile_id():
    """Verify created_by_profile_id tracks the originating user/profile."""
    func_obj = FunctionObject(
        name="UserCreatedFunc",
        logic_description="Created by user",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        created_by_profile_id="user_alice_finance"
    )
    assert func_obj.created_by_profile_id == "user_alice_finance"


def test_function_object_created_by_profile_defaults_to_system():
    """Verify created_by_profile_id defaults to SYSTEM for programmatic creation."""
    func_obj = FunctionObject(
        name="SystemFunc",
        logic_description="System-created function",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    assert func_obj.created_by_profile_id == "SYSTEM"


# ---------------------------------------------------------------------------
# T065.1f – Timestamps and Versioning
# ---------------------------------------------------------------------------

def test_function_object_created_at_auto_generated():
    """Verify created_at timestamp is automatically set to current UTC."""
    before = datetime.now(timezone.utc)
    func_obj = FunctionObject(
        name="TimestampTest",
        logic_description="Timestamp test",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    after = datetime.now(timezone.utc)
    
    assert before <= func_obj.created_at <= after
    assert func_obj.created_at.tzinfo == timezone.utc


def test_function_object_version_defaults_to_1():
    """Verify version defaults to 1 for new FunctionObjects."""
    func_obj = FunctionObject(
        name="VersionTest",
        logic_description="Version test",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    assert func_obj.version == 1


def test_function_object_version_can_be_incremented():
    """Verify version can be set and incremented for schema updates."""
    func_obj = FunctionObject(
        name="VersionUpdate",
        logic_description="Updated function",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        version=2
    )
    assert func_obj.version == 2


# ---------------------------------------------------------------------------
# T065.1g – Complex Scenario Tests
# ---------------------------------------------------------------------------

def test_complex_function_object_with_nested_schemas():
    """Verify FunctionObject handles complex nested JSON schemas."""
    complex_input = {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "profile": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "contact": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "phone": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "required": ["users"]
    }
    
    func_obj = FunctionObject(
        name="ProcessUserProfiles",
        logic_description="Process complex user profile data with nested structure",
        input_schema=complex_input,
        output_schema={
            "type": "array",
            "items": {"type": "object"}
        },
        domain_scope="UserManagement"
    )
    
    assert func_obj.name == "ProcessUserProfiles"
    assert func_obj.domain_scope == "UserManagement"
    assert func_obj.input_schema["properties"]["users"]["items"]["properties"]["profile"]


def test_multiple_function_objects_have_unique_ids():
    """Verify each FunctionObject gets a unique UUID."""
    func1 = FunctionObject(
        name="Function1",
        logic_description="First function",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    func2 = FunctionObject(
        name="Function2",
        logic_description="Second function",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    
    assert func1.id != func2.id
    assert len(func1.id) == len(func2.id) == 36  # UUID v4 format
