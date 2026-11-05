import time
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.core.config import settings

class AzureLogicAppAdapter:
    """
    Adapter for Azure Logic Apps orchestration.
    When Azure credentials and trigger URL are provided, triggers the Logic App workflow.
    When not configured, runs through the local execution adapter following the exact contract.
    """
    def __init__(self):
        self.trigger_url = settings.AZURE_LOGIC_APP_URL
        self.client_id = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.tenant_id = settings.AZURE_TENANT_ID

    def is_configured(self) -> bool:
        return bool(self.trigger_url)

    def trigger_workflow(self, payload: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
        if self.is_configured():
            headers = {
                "Content-Type": "application/json",
                "x-ms-client-tracking-id": correlation_id
            }
            try:
                resp = requests.post(self.trigger_url, json=payload, headers=headers, timeout=15)
                run_id = resp.headers.get("x-ms-workflow-run-id", f"azure-run-{correlation_id[:8]}")
                return {
                    "mode": "azure_cloud",
                    "status": "triggered" if resp.status_code in [200, 202] else "failed",
                    "status_code": resp.status_code,
                    "azure_run_id": run_id,
                    "response": resp.text[:500]
                }
            except Exception as e:
                return {
                    "mode": "azure_cloud",
                    "status": "error",
                    "error": str(e),
                    "fallback_to_local": True
                }
        else:
            # Local adapter following the Azure Logic App contract
            return {
                "mode": "local_adapter",
                "status": "accepted",
                "contract_version": "2026-04-01",
                "workflow_name": "RetailOrderIntegrationLogicApp",
                "simulated_run_id": f"local-la-{correlation_id[:8]}",
                "timestamp": datetime.utcnow().isoformat()
            }
