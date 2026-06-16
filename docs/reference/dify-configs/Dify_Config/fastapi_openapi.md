# 在已经开启fastapi服务的url后添加/docs即可查看文档；
# 在已经开启fastapi服务的url后添加/openapi.json即可获取工具格式的api文档；
- 比如：
- 加入Dify需要加上server字段
```json
"servers": [
    {
      "url": "http://127.0.0.1:8081",
      "description": "默认服务器"
    }
  ],
```
如果是使用docker部署，需要查询docker容器的ip地址`ifconfig`中docker0:的网口，将url改为http://172.17.0.1:8001
比如：
```json
"servers": [
    {
      "url": "http://172.17.0.1:8001",
      "description": "默认服务器"
    }
  ],
```
```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "桥梁效应计算API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "http://172.17.0.1:8001",
      "description": "默认服务器"
    }
  ],
  "paths": {
    "/calculate_bridge_effect": {
      "post": {
        "summary": "Api Calculate Bridge Effect",
        "description": "计算桥梁效应比值范围的API端点\n\n参数:\n- loads_ton: 轴重吨数列表\n- spacings: 轴距列表\n- station: 桩号代码\n- highway_code: 高速公路代码（可选，用于更精确地定位桥梁）\n\n返回:\nJSON格式的计算结果",
        "operationId": "api_calculate_bridge_effect_calculate_bridge_effect_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BridgeEffectRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/find_bridges_on_road_section": {
      "post": {
        "summary": "Api Find Bridges On Road Section",
        "description": "根据路段查找桥梁的API端点\n\n参数:\n- junction1: 起点枢纽点名称\n- highway_code: 高速公路代码\n- junction2: 终点枢纽点名称\n\n返回:\nJSON格式的桥梁列表",
        "operationId": "api_find_bridges_on_road_section_find_bridges_on_road_section_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FindBridgesRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/evaluate_road_section_passability": {
      "post": {
        "summary": "Api Evaluate Road Section Passability",
        "description": "评估路段通行性的API端点\n\n参数:\n- junction1: 起点枢纽点名称\n- highway_code: 高速公路代码\n- junction2: 终点枢纽点名称\n- loads_ton: 轴重吨数列表\n- spacings: 轴距列表\n\n返回:\nJSON格式的评估结果",
        "operationId": "api_evaluate_road_section_passability_evaluate_road_section_passability_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/EvaluateRoadSectionRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/evaluate_long_route_passability": {
      "post": {
        "summary": "Api Evaluate Long Route Passability",
        "description": "评估长路段通行性的API端点\n\n参数:\n- route: 路线列表，每个元素包含junction和highway_code\n- loads_ton: 轴重吨数列表\n- spacings: 轴距列表\n\n返回:\nJSON格式的长路段通行性评估结果",
        "operationId": "api_evaluate_long_route_passability_evaluate_long_route_passability_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/EvaluateLongRouteRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/find_bridges_by_k_range": {
      "post": {
        "summary": "Api Find Bridges By K Range",
        "description": "根据k值范围查找桥梁的API端点\n\n参数:\n- highway_code: 高速公路代码\n- start_k: 起点k值\n- end_k: 终点k值\n\n返回:\nJSON格式的桥梁列表",
        "operationId": "api_find_bridges_by_k_range_find_bridges_by_k_range_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FindBridgesByKRangeRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/evaluate_road_section_by_k_range": {
      "post": {
        "summary": "Api Evaluate Road Section By K Range",
        "description": "根据k值范围评估路段通行性的API端点\n\n参数:\n- highway_code: 高速公路代码\n- start_k: 起点k值\n- end_k: 终点k值\n- loads_ton: 轴重吨数列表\n- spacings: 轴距列表\n\n返回:\nJSON格式的路段通行性评估结果",
        "operationId": "api_evaluate_road_section_by_k_range_evaluate_road_section_by_k_range_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/EvaluateRoadSectionByKRangeRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/road_sections": {
      "get": {
        "summary": "Api Get Road Sections",
        "description": "获取所有路段信息\n\n返回:\n- 所有路段信息列表",
        "operationId": "api_get_road_sections_road_sections_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    },
    "/api_find_path": {
      "post": {
        "summary": "Api Find Path",
        "description": "查找两个枢纽点之间的路径\n\n参数:\n- request: 包含起点和终点枢纽点编号的请求\n\n返回:\n- 路径查找结果",
        "operationId": "api_find_path_api_find_path_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FindPathRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api_find_all_paths": {
      "post": {
        "summary": "Api Find All Paths",
        "description": "查找两个枢纽点之间的所有路径\n\n参数:\n- request: 包含起点和终点枢纽点编号的请求，以及可选的最大路径长度限制、是否返回最佳路线和返回的最佳路线数量\n\n返回:\n- 所有路径或最佳路线的查找结果",
        "operationId": "api_find_all_paths_api_find_all_paths_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FindAllPathsRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api_find_and_evaluate_routes": {
      "post": {
        "summary": "Api Find And Evaluate Routes",
        "description": "查找并评估两个枢纽点之间的多条路线\n\n参数:\n- start_junction: 起点枢纽点名称\n- end_junction: 终点枢纽点名称\n- loads_ton: 轴重吨数列表\n- spacings: 轴距列表\n- max_path_length: 最大路径长度（可选，用于限制搜索深度）\n- top_n: 返回的最佳路线数量（默认为3）\n\n返回:\n- 多条路线的查找和评估结果，包括路径、可通行性、效应比值范围等信息",
        "operationId": "api_find_and_evaluate_routes_api_find_and_evaluate_routes_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/FindAndEvaluateRoutesRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/refresh_cache": {
      "get": {
        "summary": "Refresh Cache",
        "description": "刷新桥梁数据缓存\n\n返回:\n- 刷新结果",
        "operationId": "refresh_cache_refresh_cache_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    },
    "/cache_status": {
      "get": {
        "summary": "Cache Status",
        "description": "获取缓存状态信息\n\n返回:\n- 缓存状态信息",
        "operationId": "cache_status_cache_status_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    },
    "/": {
      "get": {
        "summary": "Root",
        "operationId": "root__get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    },
    "/health": {
      "get": {
        "summary": "Health Check",
        "operationId": "health_check_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "BridgeEffectRequest": {
        "properties": {
          "loads_ton": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Loads Ton"
          },
          "spacings": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Spacings"
          },
          "station": {
            "type": "string",
            "title": "Station"
          },
          "highway_code": {
            "type": "string",
            "title": "Highway Code"
          }
        },
        "type": "object",
        "required": [
          "loads_ton",
          "spacings",
          "station"
        ],
        "title": "BridgeEffectRequest"
      },
      "EvaluateLongRouteRequest": {
        "properties": {
          "route": {
            "items": {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            "type": "array",
            "title": "Route"
          },
          "loads_ton": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Loads Ton"
          },
          "spacings": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Spacings"
          }
        },
        "type": "object",
        "required": [
          "route",
          "loads_ton",
          "spacings"
        ],
        "title": "EvaluateLongRouteRequest"
      },
      "EvaluateRoadSectionByKRangeRequest": {
        "properties": {
          "highway_code": {
            "type": "string",
            "title": "Highway Code"
          },
          "start_k": {
            "type": "number",
            "title": "Start K"
          },
          "end_k": {
            "type": "number",
            "title": "End K"
          },
          "loads_ton": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Loads Ton"
          },
          "spacings": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Spacings"
          }
        },
        "type": "object",
        "required": [
          "highway_code",
          "start_k",
          "end_k",
          "loads_ton",
          "spacings"
        ],
        "title": "EvaluateRoadSectionByKRangeRequest"
      },
      "EvaluateRoadSectionRequest": {
        "properties": {
          "junction1": {
            "type": "string",
            "title": "Junction1"
          },
          "highway_code": {
            "type": "string",
            "title": "Highway Code"
          },
          "junction2": {
            "type": "string",
            "title": "Junction2"
          },
          "loads_ton": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Loads Ton"
          },
          "spacings": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Spacings"
          }
        },
        "type": "object",
        "required": [
          "junction1",
          "highway_code",
          "junction2",
          "loads_ton",
          "spacings"
        ],
        "title": "EvaluateRoadSectionRequest"
      },
      "FindAllPathsRequest": {
        "properties": {
          "start_junction": {
            "type": "string",
            "title": "Start Junction"
          },
          "end_junction": {
            "type": "string",
            "title": "End Junction"
          },
          "max_path_length": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Max Path Length"
          },
          "return_best_routes": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Return Best Routes",
            "default": true
          },
          "top_n": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Top N",
            "default": 3
          }
        },
        "type": "object",
        "required": [
          "start_junction",
          "end_junction"
        ],
        "title": "FindAllPathsRequest"
      },
      "FindAndEvaluateRoutesRequest": {
        "properties": {
          "start_junction": {
            "type": "string",
            "title": "Start Junction"
          },
          "end_junction": {
            "type": "string",
            "title": "End Junction"
          },
          "loads_ton": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Loads Ton"
          },
          "spacings": {
            "items": {
              "type": "number"
            },
            "type": "array",
            "title": "Spacings"
          },
          "max_path_length": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Max Path Length"
          },
          "top_n": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Top N",
            "default": 3
          }
        },
        "type": "object",
        "required": [
          "start_junction",
          "end_junction",
          "loads_ton",
          "spacings"
        ],
        "title": "FindAndEvaluateRoutesRequest"
      },
      "FindBridgesByKRangeRequest": {
        "properties": {
          "highway_code": {
            "type": "string",
            "title": "Highway Code"
          },
          "start_k": {
            "type": "number",
            "title": "Start K"
          },
          "end_k": {
            "type": "number",
            "title": "End K"
          }
        },
        "type": "object",
        "required": [
          "highway_code",
          "start_k",
          "end_k"
        ],
        "title": "FindBridgesByKRangeRequest"
      },
      "FindBridgesRequest": {
        "properties": {
          "junction1": {
            "type": "string",
            "title": "Junction1"
          },
          "highway_code": {
            "type": "string",
            "title": "Highway Code"
          },
          "junction2": {
            "type": "string",
            "title": "Junction2"
          }
        },
        "type": "object",
        "required": [
          "junction1",
          "highway_code",
          "junction2"
        ],
        "title": "FindBridgesRequest"
      },
      "FindPathRequest": {
        "properties": {
          "start_junction": {
            "type": "string",
            "title": "Start Junction"
          },
          "end_junction": {
            "type": "string",
            "title": "End Junction"
          }
        },
        "type": "object",
        "required": [
          "start_junction",
          "end_junction"
        ],
        "title": "FindPathRequest"
      },
      "HTTPValidationError": {
        "properties": {
          "detail": {
            "items": {
              "$ref": "#/components/schemas/ValidationError"
            },
            "type": "array",
            "title": "Detail"
          }
        },
        "type": "object",
        "title": "HTTPValidationError"
      },
      "ValidationError": {
        "properties": {
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array",
            "title": "Location"
          },
          "msg": {
            "type": "string",
            "title": "Message"
          },
          "type": {
            "type": "string",
            "title": "Error Type"
          }
        },
        "type": "object",
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError"
      }
    }
  }
}
```