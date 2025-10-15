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

        # Knative API configuration
        self.knative_group = "serving.knative.dev"
        self.knative_version = "v1"
        self.knative_plural = "services"
        self.namespace = "default"

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
