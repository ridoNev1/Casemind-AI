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
            "/reports/severity-mismatch": {
                "get": {
                    "summary": "Severity mismatch report",
                    "tags": ["Reports"],
                    "security": [{"bearerAuth": []}],
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
            "/analytics/casemix": {
                "get": {
                    "summary": "Casemix metrics by province",
                    "tags": ["Analytics"],
                    "security": [{"bearerAuth": []}],
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
                                "model_version": {"type": "string", "example": "iso_v1"},
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
                        "peer": {"$ref": "#/components/schemas/PeerStats"},
                        "model_version": {"type": "string", "example": "iso_v1"},
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
