from collections.abc import Mapping


def build_spec(config: Mapping[str, str], server_url: str) -> dict:
    """Return OpenAPI specification covering current REST endpoints."""
    title = config.get("API_TITLE", "Casemind Claims API")
    version = config.get("API_VERSION", "1.0.0")

    return {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": version,
            "description": (
                "REST API for Casemind AI proof-of-concept. Endpoints expose risk-scored claims, "
                "analytical reports, and health probes. Payloads are anonymised and align with recipes "
                "documented in resource/docs_teknis."
            ),
        },
        "servers": [{"url": server_url}],
        "paths": {
            "/health/ping": {
                "get": {
                    "summary": "Service health probe",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "Service is available",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HealthStatus"}
                                }
                            },
                        }
                    },
                }
            },
            "/auth/register": {
                "post": {
                    "summary": "Register new user account",
                    "tags": ["Auth"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RegisterRequest"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User registered successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/RegisterResponse"}
                                }
                            },
                        },
                        "409": {
                            "description": "Email already registered",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                    },
                }
            },
            "/auth/login": {
                "post": {
                    "summary": "Login to obtain JWT access token",
                    "tags": ["Auth"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/LoginRequest"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Authenticated successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/LoginResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Invalid credentials",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                    },
                }
            },
            "/claims/high-risk": {
                "get": {
                    "summary": "List high-risk claims",
                    "tags": ["Claims"],
                    "parameters": [
                        {
                            "name": "province",
                            "in": "query",
                            "schema": {"type": "string"},
                            "required": False,
                            "description": "Filter by province code",
                        },
                        {
                            "name": "dx",
                            "in": "query",
                            "schema": {"type": "string"},
                            "required": False,
                            "description": "Filter by primary diagnosis code",
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 1},
                            "required": False,
                            "description": "Page number (default 1)",
                        },
                        {
                            "name": "page_size",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 1, "maximum": 200},
                            "required": False,
                            "description": "Page size / limit of records per page (default 50)",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 1, "maximum": 200},
                            "required": False,
                            "description": "Backward-compatible alias for page_size",
                        },
                        {
                            "name": "severity",
                            "in": "query",
                            "schema": {"type": "string", "example": "sedang"},
                            "required": False,
                            "description": "Filter by severity_group (ringan/sedang/berat/fatal)",
                        },
                        {
                            "name": "service_type",
                            "in": "query",
                            "schema": {"type": "string", "example": "RITL"},
                            "required": False,
                            "description": "Filter by service_type (RITL/RJTL/IGD/etc)",
                        },
                        {
                            "name": "min_risk_score",
                            "in": "query",
                            "schema": {"type": "number", "format": "float"},
                            "required": False,
                            "description": "Only include claims with risk_score >= value",
                        },
                        {
                            "name": "max_risk_score",
                            "in": "query",
                            "schema": {"type": "number", "format": "float"},
                            "required": False,
                            "description": "Only include claims with risk_score <= value",
                        },
                        {
                            "name": "min_ml_score",
                            "in": "query",
                            "schema": {"type": "number", "format": "float"},
                            "required": False,
                            "description": "Only include claims with ml_score_normalized >= value",
                        },
                        {
                            "name": "facility_class",
                            "in": "query",
                            "schema": {"type": "string", "example": "RS Kelas C"},
                            "required": False,
                            "description": "Filter by facility_class label",
                        },
                        {
                            "name": "start_date",
                            "in": "query",
                            "schema": {"type": "string", "format": "date", "example": "2022-11-01"},
                            "required": False,
                            "description": "Include claims with admit_dt >= start_date",
                        },
                        {
                            "name": "end_date",
                            "in": "query",
                            "schema": {"type": "string", "format": "date", "example": "2022-11-30"},
                            "required": False,
                            "description": "Include claims with admit_dt <= end_date",
                        },
                        {
                            "name": "discharge_start",
                            "in": "query",
                            "schema": {"type": "string", "format": "date", "example": "2022-11-01"},
                            "required": False,
                            "description": "Include claims with discharge_dt >= discharge_start",
                        },
                        {
                            "name": "discharge_end",
                            "in": "query",
                            "schema": {"type": "string", "format": "date", "example": "2022-11-30"},
                            "required": False,
                            "description": "Include claims with discharge_dt <= discharge_end",
                        },
                        {
                            "name": "refresh_cache",
                            "in": "query",
                            "schema": {"type": "boolean"},
                            "required": False,
                            "description": "Set true to recompute and refresh ML score cache",
                        },
                    ],
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "List of high-risk claims",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HighRiskClaimsResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        }
                    },
                }
            },
            "/claims/{claim_id}/summary": {
                "get": {
                    "summary": "Audit copilot summary for a claim",
                    "tags": ["Claims"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "claim_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Identifier of the claim to summarise",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Structured audit summary",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ClaimSummaryResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                        "404": {
                            "description": "Claim not found",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                    },
                }
            },
            "/claims/{claim_id}/feedback": {
                "post": {
                    "summary": "Submit auditor feedback for a claim",
                    "tags": ["Claims"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "claim_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Identifier of the claim being reviewed",
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AuditFeedbackRequest"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Feedback recorded",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AuditFeedbackResponse"}
                                }
                            },
                        },
                        "400": {
                            "description": "Validation error",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                        "404": {
                            "description": "Claim not found",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                    },
                }
            },
            "/claims/{claim_id}/chat": {
                "get": {
                    "summary": "Retrieve chat history for a claim",
                    "tags": ["Claims"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "claim_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Identifier of the claim whose chat thread is requested",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Chat history ordered ascending by creation time",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ChatHistoryResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                        "404": {
                            "description": "Claim not found",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                    },
                },
                "post": {
                    "summary": "Send a chat message and receive copilot reply",
                    "tags": ["Claims"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "claim_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Identifier of the claim being discussed",
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ChatMessageRequest"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Auditor message stored and copilot reply generated",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ChatInteractionResponse"}
                                }
                            },
                        },
                        "400": {
                            "description": "Missing or invalid message payload",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                        "404": {
                            "description": "Claim not found",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        },
                    },
                },
            },
            "/reports/severity-mismatch": {
                "get": {
                    "summary": "Severity mismatch report",
                    "tags": ["Reports"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1000,
                            },
                            "required": False,
                            "description": "Maximum number of records to return (default 200)",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Claims where severity and cost diverge from peers",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SeverityMismatchResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        }
                    },
                }
            },
            "/reports/duplicates": {
                "get": {
                    "summary": "Duplicate claim report",
                    "tags": ["Reports"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1000,
                            },
                            "required": False,
                            "description": "Maximum number of pairs to return (default 200)",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Potential duplicate claims within 3-day window",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/DuplicateClaimsResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        }
                    },
                }
            },
            "/reports/tariff-insight": {
                "get": {
                    "summary": "Tariff gap insight per facility and casemix group",
                    "tags": ["Reports"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1000,
                            },
                            "required": False,
                            "description": "Maximum rows to return (default 100)",
                        },
                        {
                            "name": "province",
                            "in": "query",
                            "schema": {"type": "string", "example": "KALIMANTAN SELATAN"},
                            "required": False,
                            "description": "Filter by province name (upper-case).",
                        },
                        {
                            "name": "facility_id",
                            "in": "query",
                            "schema": {"type": "string", "example": "6301013"},
                            "required": False,
                            "description": "Filter by facility_id (exact match).",
                        },
                        {
                            "name": "severity",
                            "in": "query",
                            "schema": {"type": "string", "example": "berat"},
                            "required": False,
                            "description": "Filter by severity_group (ringan/sedang/berat/fatal).",
                        },
                        {
                            "name": "service_type",
                            "in": "query",
                            "schema": {"type": "string", "example": "RITL"},
                            "required": False,
                            "description": "Filter by service_type (RITL/RJTL/etc).",
                        },
                        {
                            "name": "dx_group",
                            "in": "query",
                            "schema": {"type": "string", "example": "PROSEDUR KANDUNG KEMIH DAN SALURAN URIN BAWAH SEDANG"},
                            "required": False,
                            "description": "Filter by dx_primary_group.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Tariff insight grouped by facility and casemix group",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TariffInsightResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        }
                    },
                }
            },
            "/analytics/casemix": {
                "get": {
                    "summary": "Casemix metrics by province",
                    "tags": ["Analytics"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 500,
                            },
                            "required": False,
                            "description": "Maximum number of provinces to return (default = all)",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Casemix and risk rates aggregated per province",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CasemixResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        }
                    },
                }
            },
            "/analytics/qc-status": {
                "get": {
                    "summary": "QC status for ML scoring pipeline",
                    "tags": ["Analytics"],
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "QC status payload",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/QCStatusResponse"}
                                }
                            },
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "example": "Token has expired"},
                    },
                    "required": ["error"],
                },
                "UserSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "email": {"type": "string", "format": "email"},
                        "full_name": {"type": "string"},
                        "role": {"type": "string", "example": "auditor"},
                    },
                    "required": ["id", "email", "role"],
                },
                "RegisterRequest": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string", "format": "password"},
                        "full_name": {"type": "string"},
                    },
                    "required": ["email", "password"],
                },
                "RegisterResponse": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "email": {"type": "string", "format": "email"},
                        "full_name": {"type": "string"},
                        "role": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["id", "email", "role"],
                },
                "LoginRequest": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "password": {"type": "string", "format": "password"},
                    },
                    "required": ["email", "password"],
                },
                "LoginResponse": {
                    "type": "object",
                    "properties": {
                        "access_token": {"type": "string"},
                        "token_type": {"type": "string", "example": "bearer"},
                        "expires_in": {"type": "integer", "example": 60},
                        "expires_at": {"type": "string", "format": "date-time"},
                        "user": {"$ref": "#/components/schemas/UserSummary"},
                    },
                    "required": ["access_token", "token_type", "expires_in", "user"],
                },
                "HealthStatus": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "ok"},
                    },
                    "required": ["status"],
                },
                "HighRiskClaimsResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/HighRiskClaim"},
                        },
                        "meta": {
                            "type": "object",
                            "properties": {
                                "total": {"type": "integer", "example": 1176438},
                                "page": {"type": "integer", "example": 1},
                                "page_size": {"type": "integer", "example": 50},
                                "model_version": {"type": "string", "example": "iso_v2"},
                                "ruleset_version": {"type": "string", "example": "RULESET_v1"},
                                "filters": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                },
                            },
                            "required": ["total", "page", "page_size", "model_version", "ruleset_version"],
                        },
                    },
                    "required": ["data", "meta"],
                },
                "HighRiskClaim": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "example": "318510322V002489"},
                        "province_name": {"type": "string", "example": "DKI JAKARTA"},
                        "dx_primary_code": {"type": "string", "example": "P07"},
                        "dx_primary_label": {"type": "string", "example": "Plasmodium falciparum malaria"},
                        "dx_primary_group": {"type": "string", "example": "PROSEDUR/CASEMIX GROUP"},
                        "dx_secondary_codes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["I10", "E119"],
                        },
                        "dx_secondary_labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["I10 Essential (primary) hypertension", "E11 Type 2 diabetes mellitus"],
                        },
                        "facility_names_region": {"type": "string", "example": "RS Umum Daerah Cut Nyak Dhien; RS Tk. IV IM 07.02"},
                        "facility_ownership_names_region": {"type": "string", "example": "Pemkab; Swasta"},
                        "facility_type_names_region": {"type": "string", "example": "Rumah Sakit Umum; RS Khusus"},
                        "facility_class_names_region": {"type": "string", "example": "C; D"},
                        "facility_id": {"type": "string", "nullable": True, "example": "1171110"},
                        "facility_name": {"type": "string", "nullable": True, "example": "RS Umum Daerah Meuraxa"},
                        "facility_match_quality": {
                            "type": "string",
                            "enum": ["exact", "regional", "unmatched"],
                            "example": "exact",
                        },
                        "severity_group": {"type": "string", "example": "sedang"},
                        "service_type": {"type": "string", "example": "RITL"},
                        "facility_class": {"type": "string", "example": "RS Kelas B"},
                        "amount_claimed": {"type": "number", "format": "float", "example": 2500000},
                        "amount_paid": {"type": "number", "format": "float", "example": 1200000},
                        "cost_zscore": {"type": "number", "format": "float", "nullable": True},
                        "los": {"type": "integer", "nullable": True},
                        "bpjs_payment_ratio": {"type": "number", "format": "float", "nullable": True},
                        "risk_score": {"type": "number", "format": "float", "example": 0.97},
                        "rule_score": {"type": "number", "format": "float", "nullable": True},
                        "ml_score": {"type": "number", "format": "float"},
                        "ml_score_normalized": {"type": "number", "format": "float"},
                        "flags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["short_stay_high_cost", "high_cost_full_paid"],
                        },
                        "duplicate_pattern": {"type": "boolean", "example": True},
                        "peer": {"$ref": "#/components/schemas/PeerStats"},
                        "model_version": {"type": "string", "example": "iso_v2"},
                        "ruleset_version": {"type": "string", "example": "RULESET_v1"},
                    },
                    "required": [
                        "claim_id",
                        "province_name",
                        "dx_primary_code",
                        "severity_group",
                        "risk_score",
                        "ml_score",
                        "ml_score_normalized",
                        "flags",
                        "duplicate_pattern",
                        "peer",
                        "model_version",
                        "ruleset_version",
                        "facility_class",
                    ],
                },
                "PeerStats": {
                    "type": "object",
                    "properties": {
                        "mean": {"type": "number", "format": "float", "example": 1800000},
                        "p90": {"type": "number", "format": "float", "example": 2600000},
                    },
                    "required": ["mean", "p90"],
                },
                "ClaimSummaryResponse": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/ClaimSummary"},
                    },
                    "required": ["data"],
                },
                "ClaimSummary": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "example": "318510322V002489"},
                        "generated_at": {"type": "string", "format": "date-time"},
                        "model_version": {"type": "string", "example": "iso_v2"},
                        "ruleset_version": {"type": "string", "example": "RULESET_v1"},
                        "risk_score": {"type": "number", "format": "float", "example": 0.92},
                        "rule_score": {"type": "number", "format": "float", "nullable": True},
                        "ml_score": {"type": "number", "format": "float", "nullable": True},
                        "ml_score_normalized": {"type": "number", "format": "float", "nullable": True},
                        "bpjs_payment_ratio": {"type": "number", "format": "float", "nullable": True},
                        "flags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["short_stay_high_cost", "duplicate_pattern"],
                        },
                        "sections": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SummarySection"},
                        },
                        "narrative": {"type": "string"},
                        "generative_summary": {
                            "type": "string",
                            "nullable": True,
                            "description": "Ringkasan generatif dari LLM (jika tersedia).",
                        },
                        "follow_up_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "llm": {"$ref": "#/components/schemas/CopilotLLMInfo"},
                        "peer": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string", "example": "B50|ringan|RS Kelas C|Papua"},
                                "p90": {"type": "number", "format": "float", "nullable": True},
                                "cost_zscore": {"type": "number", "format": "float", "nullable": True},
                            },
                            "required": ["key"],
                        },
                        "claim": {
                            "type": "object",
                            "properties": {
                                "dx_primary_code": {"type": "string", "example": "B509"},
                                "dx_primary_label": {"type": "string", "example": "Plasmodium falciparum malaria"},
                                "severity_group": {"type": "string", "example": "ringan"},
                                "service_type": {"type": "string", "example": "RITL"},
                                "facility_class": {"type": "string", "example": "RS Kelas C"},
                                "province_name": {"type": "string", "example": "Papua"},
                                "los": {"type": "integer", "nullable": True},
                                "amount_claimed": {"type": "number", "format": "float", "nullable": True},
                                "amount_paid": {"type": "number", "format": "float", "nullable": True},
                                "amount_gap": {"type": "number", "format": "float", "nullable": True},
                            },
                        },
                        "latest_feedback": {
                            "oneOf": [
                                {"$ref": "#/components/schemas/AuditFeedback"},
                                {"type": "null"},
                            ]
                        },
                    },
                    "required": [
                        "claim_id",
                        "generated_at",
                        "model_version",
                        "ruleset_version",
                        "risk_score",
                        "flags",
                        "sections",
                        "narrative",
                        "follow_up_questions",
                        "peer",
                        "claim",
                    ],
                },
                "SummarySection": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "example": "Identitas singkat"},
                        "content": {"type": "string"},
                    },
                    "required": ["title", "content"],
                },
                "CopilotLLMInfo": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean", "example": True},
                        "provider": {"type": "string", "nullable": True, "example": "openai"},
                        "model": {"type": "string", "nullable": True, "example": "gpt-4o-mini"},
                        "cached": {"type": "boolean", "nullable": True, "example": False},
                        "generated_at": {"type": "string", "format": "date-time", "nullable": True},
                        "prompt_version": {"type": "string", "example": "v1"},
                        "error": {"type": "string", "nullable": True},
                    },
                    "required": ["enabled"],
                },
                "SeverityMismatchResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SeverityMismatchRecord"},
                        }
                    },
                    "required": ["data"],
                },
                "SeverityMismatchRecord": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "example": "CLAIM-DEMO-002"},
                        "dx_primary": {"type": "string", "example": "B509"},
                        "facility_class": {"type": "string", "example": "C"},
                        "province": {"type": "string", "example": "Papua"},
                        "los": {"type": "number", "format": "float", "example": 0},
                        "claimed": {"type": "number", "format": "float", "example": 2250000},
                        "peer_p90": {"type": "number", "format": "float", "example": 1600000},
                        "delta_pct": {"type": "number", "format": "float", "example": 40.6},
                    },
                    "required": [
                        "claim_id",
                        "dx_primary",
                        "facility_class",
                        "province",
                        "los",
                        "claimed",
                        "peer_p90",
                        "delta_pct",
                    ],
                },
                "DuplicateClaimsResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/DuplicateClaimRecord"},
                        }
                    },
                    "required": ["data"],
                },
                "DuplicateClaimRecord": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "example": "CLAIM-DEMO-003"},
                        "matched_claim_id": {"type": "string", "example": "CLAIM-DEMO-004"},
                        "dx_primary": {"type": "string", "example": "O80"},
                        "procedure_code": {"type": "string", "example": "9059"},
                        "episode_gap_days": {"type": "integer", "example": 2},
                    },
                    "required": ["claim_id", "matched_claim_id", "dx_primary", "procedure_code", "episode_gap_days"],
                },
                "TariffInsightResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/TariffInsightRecord"},
                        }
                    },
                    "required": ["data"],
                },
                "TariffInsightRecord": {
                    "type": "object",
                    "properties": {
                        "facility_id": {"type": "string", "nullable": True, "example": "6301013"},
                        "facility_name": {"type": "string", "example": "RS UMUM DAERAH H. BOEJASIN PELAIHARI"},
                        "facility_match_quality": {
                            "type": "string",
                            "enum": ["exact", "regional", "unmatched"],
                            "example": "exact",
                        },
                        "province_name": {"type": "string", "example": "KALIMANTAN SELATAN"},
                        "district_name": {"type": "string", "example": "TANAH LAUT"},
                        "dx_primary_group": {
                            "type": "string",
                            "example": "SIMPLE PNEUMONIA & WHOOPING COUGH SEDANG",
                        },
                        "claim_count": {"type": "integer", "example": 145},
                        "total_claimed": {"type": "number", "format": "float", "example": 285000000},
                        "total_paid": {"type": "number", "format": "float", "example": 210000000},
                        "total_gap": {"type": "number", "format": "float", "example": 75000000},
                        "avg_gap": {"type": "number", "format": "float", "example": 517241.38},
                        "avg_cost_zscore": {"type": "number", "format": "float", "nullable": True, "example": 0.8},
                        "avg_payment_ratio": {"type": "number", "format": "float", "nullable": True, "example": 1.35},
                    },
                    "required": [
                        "facility_name",
                        "facility_match_quality",
                        "province_name",
                        "district_name",
                        "dx_primary_group",
                        "claim_count",
                        "total_claimed",
                        "total_paid",
                        "total_gap",
                        "avg_gap",
                    ],
                },
                "CasemixResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/CasemixRecord"},
                        }
                    },
                    "required": ["data"],
                },
                "CasemixRecord": {
                    "type": "object",
                    "properties": {
                        "province": {"type": "string", "example": "Papua"},
                        "claim_count": {"type": "integer", "example": 1200},
                        "avg_los": {"type": "number", "format": "float", "example": 1.4},
                        "median_claim_to_paid_ratio": {"type": "number", "format": "float", "example": 1.12},
                        "high_risk_rate": {"type": "number", "format": "float", "example": 0.07},
                    },
                    "required": [
                        "province",
                        "claim_count",
                        "avg_los",
                        "median_claim_to_paid_ratio",
                        "high_risk_rate",
                    ],
                },
                "QCStatusResponse": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["ok", "alert", "no_data"],
                            "example": "alert",
                        },
                        "message": {"type": "string", "example": "los_le_1_ratio_top_k 0.02 < 0.05"},
                        "thresholds": {"$ref": "#/components/schemas/QCThresholds"},
                        "metrics": {"$ref": "#/components/schemas/QCMetrics"},
                        "top_provinces": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/QCCountItem"},
                        },
                        "top_severity": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/QCCountItem"},
                        },
                        "top_flags": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/QCCountItem"},
                        },
                    },
                    "required": ["status", "thresholds", "metrics"],
                },
                "QCThresholds": {
                    "type": "object",
                    "properties": {
                        "risk_score_min": {"type": "number", "format": "float", "example": 0.7},
                        "los_le_1_ratio_min": {"type": "number", "format": "float", "example": 0.05},
                    },
                    "required": ["risk_score_min", "los_le_1_ratio_min"],
                },
                "QCMetrics": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string", "example": "20251106T092350Z"},
                        "total_rows": {"type": "integer", "example": 1176438},
                        "top_k": {"type": "integer", "example": 50},
                        "risk_score_top_k_mean": {"type": "number", "format": "float", "example": 0.94},
                        "ml_score_top_k_mean": {"type": "number", "format": "float", "example": 0.94},
                        "los_le_1_ratio_top_k": {"type": "number", "format": "float", "example": 0.02},
                        "amount_claimed_top_k_mean": {"type": "number", "format": "float", "example": 4.22},
                    },
                    "required": ["top_k"],
                },
                "QCCountItem": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "example": "DKI JAKARTA"},
                        "count": {"type": "integer", "example": 32},
                    },
                    "required": ["name", "count"],
                },
                "ChatMessage": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "claim_id": {"type": "string", "example": "18591122V003624"},
                        "sender": {"type": "string", "example": "ridolaurent021123@gmail.com"},
                        "role": {"type": "string", "example": "user"},
                        "content": {"type": "string"},
                        "metadata": {
                            "type": "object",
                            "description": "Additional attributes such as origin or LLM metadata",
                        },
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["id", "claim_id", "sender", "role", "content", "created_at"],
                },
                "ChatHistoryResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ChatMessage"},
                        }
                    },
                    "required": ["data"],
                },
                "ChatMessageRequest": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Jelaskan klaim ini kenapa dianggap fraud?",
                        }
                    },
                    "required": ["message"],
                },
                "ChatInteractionResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "user_message": {"$ref": "#/components/schemas/ChatMessage"},
                                "bot_message": {"$ref": "#/components/schemas/ChatMessage"},
                            },
                            "required": ["user_message", "bot_message"],
                        }
                    },
                    "required": ["data"],
                },
                "AuditFeedbackRequest": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": ["approved", "partial", "rejected"],
                            "example": "partial",
                        },
                        "correction_ratio": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "example": 0.35,
                        },
                        "notes": {"type": "string", "example": "Butuh koreksi tarif obat 35%"},
                    },
                    "required": ["decision"],
                },
                "AuditFeedbackResponse": {
                    "type": "object",
                    "properties": {
                        "data": {"$ref": "#/components/schemas/AuditFeedback"},
                    },
                    "required": ["data"],
                },
                "AuditFeedback": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "claim_id": {"type": "string"},
                        "decision": {"type": "string", "example": "partial"},
                        "correction_ratio": {"type": "number", "format": "float", "nullable": True},
                        "notes": {"type": "string", "nullable": True},
                        "reviewer_id": {"type": "string", "format": "uuid", "nullable": True},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["id", "claim_id", "decision", "created_at", "updated_at"],
                },
            }
        },
        "tags": [
            {"name": "Auth"},
            {"name": "Health"},
            {"name": "Claims"},
            {"name": "Reports"},
            {"name": "Analytics"},
        ],
    }
