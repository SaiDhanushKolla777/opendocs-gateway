"""Metrics and benchmark stats (single-GPU observability)."""
from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque, Dict

_lock = Lock()
_request_latencies: Deque[float] = deque(maxlen=1000)
_request_count = 0
_error_count = 0
_active_requests = 0
_schema_valid_count = 0
_schema_invalid_count = 0
_total_input_tokens = 0
_total_output_tokens = 0
_token_calls = 0


def record_request_start() -> None:
    global _active_requests, _request_count
    with _lock:
        _active_requests += 1
        _request_count += 1


def record_request_end(latency_sec: float, schema_valid: bool | None = None) -> None:
    global _active_requests
    with _lock:
        _active_requests = max(0, _active_requests - 1)
        _request_latencies.append(latency_sec)
        if schema_valid is True:
            global _schema_valid_count
            _schema_valid_count += 1
        elif schema_valid is False:
            global _schema_invalid_count
            _schema_invalid_count += 1


def record_error() -> None:
    global _error_count
    with _lock:
        _error_count += 1


def record_tokens(input_tokens: int, output_tokens: int) -> None:
    global _total_input_tokens, _total_output_tokens, _token_calls
    with _lock:
        _total_input_tokens += input_tokens
        _total_output_tokens += output_tokens
        _token_calls += 1


def record_schema_result(valid: bool) -> None:
    global _schema_valid_count, _schema_invalid_count
    with _lock:
        if valid:
            _schema_valid_count += 1
        else:
            _schema_invalid_count += 1


def _percentile(sorted_list: list, p: float) -> float:
    if not sorted_list:
        return 0.0
    idx = min(int(p * len(sorted_list)), len(sorted_list) - 1)
    return sorted_list[idx]


def get_metrics() -> Dict:
    with _lock:
        latencies = sorted(_request_latencies)
        total_schema = _schema_valid_count + _schema_invalid_count
        total_requests = _request_count or 1

    return {
        "request_count": _request_count,
        "active_requests": _active_requests,
        "p50_latency_sec": round(_percentile(latencies, 0.5), 2),
        "p95_latency_sec": round(_percentile(latencies, 0.95), 2),
        "p99_latency_sec": round(_percentile(latencies, 0.99), 2),
        "avg_input_tokens": round(_total_input_tokens / _token_calls, 0) if _token_calls else 0,
        "avg_output_tokens": round(_total_output_tokens / _token_calls, 0) if _token_calls else 0,
        "total_tokens": _total_input_tokens + _total_output_tokens,
        "total_input_tokens": _total_input_tokens,
        "total_output_tokens": _total_output_tokens,
        "error_count": _error_count,
        "error_rate": round(_error_count / total_requests, 4),
        "schema_valid_rate": round(_schema_valid_count / total_schema, 4) if total_schema else 1.0,
        "llm_calls": _token_calls,
    }


class LatencyTimer:
    def __init__(self, schema_valid: bool | None = None):
        self.schema_valid = schema_valid
        self.start = 0.0

    def __enter__(self) -> "LatencyTimer":
        record_request_start()
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, *args) -> None:
        latency = time.perf_counter() - self.start
        if exc_type is not None:
            record_error()
        record_request_end(latency, self.schema_valid)
