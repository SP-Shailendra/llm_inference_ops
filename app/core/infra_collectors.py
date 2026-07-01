import re
from typing import Dict, List, Optional, Tuple

import httpx

from app.config import settings


class InfrastructureCollector:
    """Collects runtime infrastructure metrics from serving framework endpoints.

    This keeps the platform useful even when different frameworks expose
    different metric names by relying on best-effort pattern extraction.
    """

    def _derive_metrics_url(self, base_url: Optional[str]) -> Optional[str]:
        if not base_url:
            return None

        trimmed = base_url.rstrip("/")
        if trimmed.endswith("/v1"):
            trimmed = trimmed[:-3]
        return f"{trimmed}/metrics"

    def _parse_prometheus_text(self, text: str) -> List[Tuple[str, Dict[str, str], float]]:
        rows: List[Tuple[str, Dict[str, str], float]] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            metric_with_labels = parts[0]
            try:
                value = float(parts[-1])
            except ValueError:
                continue

            if "{" in metric_with_labels and metric_with_labels.endswith("}"):
                metric_name, labels_part = metric_with_labels.split("{", 1)
                labels_part = labels_part[:-1]
                labels: Dict[str, str] = {}
                for m in re.finditer(r'(\w+)="([^"]*)"', labels_part):
                    labels[m.group(1)] = m.group(2)
            else:
                metric_name = metric_with_labels
                labels = {}

            rows.append((metric_name, labels, value))

        return rows

    def _sum_matching(self, rows: List[Tuple[str, Dict[str, str], float]], needles: List[str]) -> float:
        return sum(
            value
            for name, _labels, value in rows
            if any(needle in name for needle in needles)
        )

    def _avg_matching(self, rows: List[Tuple[str, Dict[str, str], float]], needles: List[str]) -> Optional[float]:
        vals = [
            value
            for name, _labels, value in rows
            if any(needle in name for needle in needles)
        ]
        if not vals:
            return None
        return sum(vals) / len(vals)

    def _extract_external_node(self, framework: str, rows: List[Tuple[str, Dict[str, str], float]]) -> Optional[dict]:
        active = int(
            self._sum_matching(
                rows,
                ["num_requests_running", "requests_running", "in_flight", "queue_running"],
            )
        )

        gpu_util = self._avg_matching(rows, ["gpu_util", "gpu_utilization", "gpu_usage"])
        kv_usage = self._avg_matching(rows, ["gpu_cache_usage", "kv_cache_usage", "cache_usage"])

        load_percent: float
        if gpu_util is not None:
            load_percent = gpu_util * 100 if gpu_util <= 1.0 else gpu_util
        elif kv_usage is not None:
            load_percent = kv_usage * 100 if kv_usage <= 1.0 else kv_usage
        else:
            load_percent = 10 + (active * 20)

        load_percent = max(0, min(100, round(load_percent, 1)))

        status = "idle"
        if active > 0 and load_percent >= 80:
            status = "overloaded"
        elif active > 0:
            status = "healthy"

        return {
            "model": f"{framework}-runtime",
            "active_connections": active,
            # Keep this field name for frontend compatibility.
            "simulated_gpu_load_percent": load_percent,
            "status": status,
            "source": framework,
            "last_seen_seconds_ago": 0,
        }

    async def collect(self) -> Dict[str, object]:
        targets = []

        vllm_url = settings.VLLM_METRICS_URL or self._derive_metrics_url(settings.VLLM_BASE_URL)
        if vllm_url:
            targets.append(("vLLM", vllm_url))

        tgi_url = settings.TGI_METRICS_URL or self._derive_metrics_url(settings.TGI_BASE_URL)
        if tgi_url:
            targets.append(("TGI", tgi_url))

        if not targets:
            return {"nodes": [], "global_active_requests": 0, "collector_errors": []}

        nodes = []
        errors = []

        async with httpx.AsyncClient(timeout=1.5) as client:
            for framework, url in targets:
                try:
                    resp = await client.get(url)
                    if resp.status_code >= 400:
                        errors.append(f"{framework} metrics endpoint returned HTTP {resp.status_code}")
                        continue

                    rows = self._parse_prometheus_text(resp.text)
                    node = self._extract_external_node(framework, rows)
                    if node:
                        nodes.append(node)
                except Exception as ex:
                    detail = str(ex).strip() or ex.__class__.__name__
                    errors.append(f"{framework} metrics unavailable: {detail}")

        return {
            "nodes": nodes,
            "global_active_requests": sum(int(n.get("active_connections", 0)) for n in nodes),
            "collector_errors": errors,
        }


infra_collector = InfrastructureCollector()
