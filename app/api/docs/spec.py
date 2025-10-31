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
                        "filters": {
                            "type": "object",
                            "additionalProperties": {"nullable": True},
                        },
                    },
                    "required": ["data", "filters"],
                },
                "HighRiskClaim": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "example": "CLAIM-DEMO-001"},
                        "province": {"type": "string", "example": "Papua"},
                        "dx_code": {"type": "string", "example": "B509"},
                        "risk_score": {"type": "number", "format": "float", "example": 0.92},
                        "flags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["short_stay_high_cost", "high_cost_full_paid"],
                        },
                        "peer": {"$ref": "#/components/schemas/PeerStats"},
                    },
                    "required": ["claim_id", "province", "dx_code", "risk_score", "flags", "peer"],
                },
                "PeerStats": {
                    "type": "object",
                    "properties": {
                        "p90": {"type": "number", "format": "float", "example": 1600000},
                        "z": {"type": "number", "format": "float", "example": 2.7},
                    },
                    "required": ["p90", "z"],
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
