from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

logger = logging.getLogger(__name__)


class KnativeManager:
    def __init__(self):
        try:
            # For local dev
            config.load_kube_config()
        except:
            # For work in Kubernetes claster
            config.load_incluster_config()

        self.custom_api = client.CustomObjectsApi()
        self.core_v1 = client.CoreV1Api()
        self.metrics_api = client.CustomObjectsApi()

        # Knative API configuration
        self.knative_group = "serving.knative.dev"
        self.knative_version = "v1"
        self.knative_plural = "services"
        self.namespace = "default"

        self.metrics_group = "metrics.k8s.io"
        self.metrics_version = "v1beta1"
        self.metrics_plural = "pods"

    def deploy_function(self, name, image, env_vars=None, min_scale=0, max_scale=5):
        """Деплой функции в Knative"""
        try:
            env_list = []
            if env_vars:
                for key, value in env_vars.items():
                    env_list.append({"name": key, "value": str(value)})

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
                            "annotations": {
                                "autoscaling.knative.dev/minScale": str(min_scale),
                                "autoscaling.knative.dev/maxScale": str(max_scale),
                            }
                        },
                        "spec": {
                            "containers": [{
                                "image": image,
                                "env": env_list,
                                "resources": {
                                    "requests": {
                                        "memory": "128Mi",
                                        "cpu": "100m"
                                    }
                                }
                            }]
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

    def get_function_metrics(self, name):
        """Получение метрик ресурсов для функции"""
        try:
            label_selector = f"serving.knative.dev/service={name}"

            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )

            metrics_data = {
                "function_name": name,
                "pods": [],
                "summary": {
                    "total_cpu_usage": 0,
                    "total_memory_usage": 0,
                    "pod_count": len(pods.items)
                }
            }

            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_metrics = self._get_pod_metrics(pod_name)
                metrics_data["pods"].append(pod_metrics)

                # Суммируем использование ресурсов
                if pod_metrics.get("cpu_usage_nanocores"):
                    metrics_data["summary"]["total_cpu_usage"] += pod_metrics["cpu_usage_nanocores"]
                if pod_metrics.get("memory_usage_bytes"):
                    metrics_data["summary"]["total_memory_usage"] += pod_metrics["memory_usage_bytes"]

            return {"success": True, "data": metrics_data}

        except ApiException as e:
            logger.error(f"Failed to get metrics for function {name}: {e}")
            return {"success": False, "error": str(e)}

    def _get_pod_metrics(self, pod_name):
        """Получение метрик для конкретного pod"""
        try:
            pod_metrics = self.metrics_api.get_namespaced_custom_object(
                group=self.metrics_group,
                version=self.metrics_version,
                namespace=self.namespace,
                plural=self.metrics_plural,
                name=pod_name
            )

            cpu_usage = 0
            memory_usage = 0

            for container in pod_metrics.get("containers", []):
                usage = container.get("usage", {})
                if "cpu" in usage:
                    cpu_quantity = usage["cpu"]
                    if cpu_quantity.endswith("n"):
                        cpu_usage = int(cpu_quantity.rstrip("n"))
                    elif cpu_quantity.endswith("u"):
                        cpu_usage = int(float(cpu_quantity.rstrip("u")) * 1000)
                    elif cpu_quantity.endswith("m"):
                        cpu_usage = int(float(cpu_quantity.rstrip("m")) * 1000000)

                if "memory" in usage:
                    memory_quantity = usage["memory"]
                    if memory_quantity.endswith("Ki"):
                        memory_usage = int(memory_quantity.rstrip("Ki")) * 1024
                    elif memory_quantity.endswith("Mi"):
                        memory_usage = int(memory_quantity.rstrip("Mi")) * 1024 * 1024
                    elif memory_quantity.endswith("Gi"):
                        memory_usage = int(memory_quantity.rstrip("Gi")) * 1024 * 1024 * 1024
                    else:
                        memory_usage = int(memory_quantity.rstrip("Ki"))  # Базовый случай

            return {
                "pod_name": pod_name,
                "cpu_usage_nanocores": cpu_usage,
                "memory_usage_bytes": memory_usage,
                "timestamp": pod_metrics.get("timestamp", "")
            }

        except ApiException as e:
            logger.warning(f"Could not get metrics for pod {pod_name}: {e}")
            return {
                "pod_name": pod_name,
                "error": str(e)
            }
