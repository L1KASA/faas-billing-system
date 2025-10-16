from datetime import datetime, timezone

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

from faas_billing.config import config as app_config

logger = logging.getLogger(__name__)


class KnativeManager:
    def __init__(self):
        try:
            # For local dev
            config.load_kube_config()
        except:
            # For work in Kubernetes cluster
            config.load_incluster_config()

        self.custom_api = client.CustomObjectsApi()
        self.core_v1 = client.CoreV1Api()
        self.metrics_api = client.CustomObjectsApi()

        # Knative API configuration from config
        self.knative_group = app_config.KNATIVE_GROUP
        self.knative_version = app_config.KNATIVE_VERSION
        self.knative_plural = app_config.KNATIVE_PLURAL
        self.namespace = app_config.KUBERNETES_NAMESPACE

        self.metrics_group = app_config.METRICS_GROUP
        self.metrics_version = app_config.METRICS_VERSION
        self.metrics_plural = app_config.METRICS_PLURAL

    def deploy_function(self, name, image, env_vars=None, min_scale=None, max_scale=None):
        """Деплой функции"""
        try:
            env_list = []
            if env_vars:
                for key, value in env_vars.items():
                    env_list.append({"name": key, "value": str(value)})

            # Получаем значения из конфига
            if min_scale is None:
                min_scale = app_config.DEFAULT_MIN_SCALE
            if max_scale is None:
                max_scale = app_config.DEFAULT_MAX_SCALE

            knative_service = {
                "apiVersion": f"{self.knative_group}/{self.knative_version}",
                "kind": "Service",
                "metadata": {
                    "name": name,
                    "namespace": self.namespace
                },
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": app_config.get_default_annotations(min_scale, max_scale)
                        },
                        "spec": {
                            "containers": [
                                app_config.get_default_container_spec(image, env_list)
                            ]
                        }
                    }
                }
            }

            # Create Knative Service
            result = self.custom_api.create_namespaced_custom_object(
                group=self.knative_group,
                version=self.knative_version,
                namespace=self.namespace,
                plural=self.knative_plural,
                body=knative_service
            )

            logger.info(f"Function {name} deployed successfully")
            return {"success": True, "data": result}

        except ApiException as e:
            logger.error(f"Failed to deploy function {name}: {e}")
            return {"success": False, "error": str(e)}

    def get_function_status(self, name):
        """Get status of function"""
        try:
            result = self.custom_api.get_namespaced_custom_object(
                group=self.knative_group,
                version=self.knative_version,
                namespace=self.namespace,
                plural=self.knative_plural,
                name=name
            )
            return {"success": True, "data": result}
        except ApiException as e:
            return {"success": False, "error": str(e)}

    def delete_function(self, name):
        """Delete functions"""
        try:
            result = self.custom_api.delete_namespaced_custom_object(
                group=self.knative_group,
                version=self.knative_version,
                namespace=self.namespace,
                plural=self.knative_plural,
                name=name
            )
            return {"success": True, "data": result}
        except ApiException as e:
            return {"success": False, "error": str(e)}

    def list_functions(self):
        """List of all functions"""
        try:
            result = self.custom_api.list_namespaced_custom_object(
                group=self.knative_group,
                version=self.knative_version,
                namespace=self.namespace,
                plural=self.knative_plural
            )
            return {"success": True, "data": result.get('items', [])}
        except ApiException as e:
            return {"success": False, "error": str(e)}

    def _convert_resource_quantity(self, quantity, resource_type):
        """Конвертирует строковое представление ресурсов Kubernetes в стандартные единицы."""
        if not quantity:
            return 0

        quantity_str = str(quantity)

        if resource_type == 'cpu':
            factors = app_config.CPU_CONVERSION_FACTORS
            if quantity_str.endswith("n"):
                return int(quantity_str.rstrip("n")) * factors['n']
            elif quantity_str.endswith("u"):
                return int(float(quantity_str.rstrip("u")) * factors['u'])
            elif quantity_str.endswith("m"):
                return int(float(quantity_str.rstrip("m")) * factors['m'])
            else:
                return int(float(quantity_str)) * factors['default']

        elif resource_type == 'memory':
            factors = app_config.MEMORY_CONVERSION_FACTORS
            if quantity_str.endswith("Ki"):
                return int(quantity_str.rstrip("Ki")) * factors['Ki']
            elif quantity_str.endswith("Mi"):
                return int(quantity_str.rstrip("Mi")) * factors['Mi']
            elif quantity_str.endswith("Gi"):
                return int(quantity_str.rstrip("Gi")) * factors['Gi']
            elif quantity_str.endswith("K"):
                return int(quantity_str.rstrip("K")) * factors['K']
            elif quantity_str.endswith("M"):
                return int(quantity_str.rstrip("M")) * factors['M']
            elif quantity_str.endswith("G"):
                return int(quantity_str.rstrip("G")) * factors['G']
            else:
                return int(quantity_str) * factors['default']

        return 0

    def _get_pod_metrics(self, pod_name):
        """Получение метрик для конкретного pod, включая данные из CoreV1Api для биллинга."""

        try:
            pod_info = self.core_v1.read_namespaced_pod(
                name=pod_name,
                namespace=self.namespace
            )
        except ApiException as e:
            logger.error(f"Failed to get pod info for {pod_name}: {e}")
            return {"pod_name": pod_name, "error": f"Failed to get pod info: {str(e)}"}

        cpu_req_nanocores = 0
        memory_req_bytes = 0
        pod_uptime_seconds = 0
        cold_start_time_seconds = 0

        try:
            container = pod_info.spec.containers[0]

            requests = container.resources.requests
            if requests:
                if 'cpu' in requests:
                    cpu_req_nanocores = self._convert_resource_quantity(requests['cpu'], 'cpu')
                if 'memory' in requests:
                    memory_req_bytes = self._convert_resource_quantity(requests['memory'], 'memory')

            now = datetime.now(timezone.utc)
            creation_time = pod_info.metadata.creation_timestamp.astimezone(timezone.utc)
            pod_uptime_seconds = (now - creation_time).total_seconds()

            start_time = None
            if pod_info.status.container_statuses:
                for status in pod_info.status.container_statuses:
                    if status.state and status.state.running:
                        start_time = status.state.running.started_at.astimezone(timezone.utc)
                        break

            if start_time and creation_time:
                cold_start_time_seconds = (start_time - creation_time).total_seconds()

        except Exception as e:
            logger.warning(f"Error processing resource requests/times for pod {pod_name}: {e}")
            pass

        cpu_usage = 0
        memory_usage = 0
        timestamp = ""

        try:
            pod_metrics = self.metrics_api.get_namespaced_custom_object(
                group=self.metrics_group,
                version=self.metrics_version,
                namespace=self.namespace,
                plural=self.metrics_plural,
                name=pod_name
            )

            timestamp = pod_metrics.get("timestamp", "")

            for container in pod_metrics.get("containers", []):
                usage = container.get("usage", {})
                if "cpu" in usage:
                    cpu_usage = self._convert_resource_quantity(usage["cpu"], 'cpu')
                if "memory" in usage:
                    memory_usage = self._convert_resource_quantity(usage["memory"], 'memory')

        except ApiException as e:
            logger.warning(f"Could not get consumption metrics for pod {pod_name}: {e}")

        return {
            "pod_name": pod_name,
            "cpu_usage_nanocores": cpu_usage,
            "memory_usage_bytes": memory_usage,
            "cpu_request_nanocores": cpu_req_nanocores,
            "memory_request_bytes": memory_req_bytes,
            "pod_uptime_seconds": pod_uptime_seconds,
            "cold_start_time_seconds": cold_start_time_seconds,
            "timestamp": timestamp
        }

    def get_function_metrics(self, name):
        """Получение метрик ресурсов для функции, включая новые данные для биллинга."""
        try:
            label_selector = app_config.get_service_label_selector(name)

            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )

            metrics_data = {
                "function_name": name,
                "pods": [],
                "summary": {
                    "pod_count": len(pods.items),
                    "total_cpu_usage": 0,
                    "total_memory_usage": 0,
                    "total_cpu_request": 0,
                    "total_memory_request": 0,
                    "total_pod_uptime_seconds": 0,
                    "max_cold_start_time_seconds": 0
                }
            }

            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_metrics = self._get_pod_metrics(pod_name)
                metrics_data["pods"].append(pod_metrics)

                if pod_metrics.get("cpu_usage_nanocores"):
                    metrics_data["summary"]["total_cpu_usage"] += pod_metrics["cpu_usage_nanocores"]
                if pod_metrics.get("memory_usage_bytes"):
                    metrics_data["summary"]["total_memory_usage"] += pod_metrics["memory_usage_bytes"]

                if pod_metrics.get("cpu_request_nanocores"):
                    metrics_data["summary"]["total_cpu_request"] += pod_metrics["cpu_request_nanocores"]
                if pod_metrics.get("memory_request_bytes"):
                    metrics_data["summary"]["total_memory_request"] += pod_metrics["memory_request_bytes"]
                if pod_metrics.get("pod_uptime_seconds"):
                    metrics_data["summary"]["total_pod_uptime_seconds"] += pod_metrics["pod_uptime_seconds"]

                if pod_metrics.get("cold_start_time_seconds"):
                    current_cold_start = pod_metrics["cold_start_time_seconds"]
                    if current_cold_start > metrics_data["summary"]["max_cold_start_time_seconds"]:
                        metrics_data["summary"]["max_cold_start_time_seconds"] = current_cold_start

            return {"success": True, "data": metrics_data}

        except ApiException as e:
            logger.error(f"Failed to get metrics for function {name}: {e}")
            return {"success": False, "error": str(e)}
