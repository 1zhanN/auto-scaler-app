import requests
import time
from kubernetes import client, config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Kubernetes config
config.load_incluster_config()
v1 = client.AppsV1Api()

PROMETHEUS_URL = "http://prometheus:9090"
NAMESPACE = "default"
DEPLOYMENT = "resnet-deployment"
MIN_REPLICAS = 3
MAX_REPLICAS = 10
CHECK_INTERVAL = 10  # seconds

# Queue depth thresholds
QUEUE_DEPTH_THRESHOLDS = {
    5: 3,      # queue <= 5, keep 3 replicas
    10: 5,     # queue <= 10, scale to 5
    20: 7,     # queue <= 20, scale to 7
    50: 10,    # queue > 20, scale to 10
}

def get_queue_depth():
    """Query Prometheus for current queue size"""
    try:
        query = "dispatcher_queue_size"
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        data = response.json()
        
        if data["status"] == "success" and data["data"]["result"]:
            queue_size = float(data["data"]["result"][0]["value"][1])
            logger.info(f"Queue size: {queue_size}")
            return queue_size
        return 0
    except Exception as e:
        logger.error(f"Failed to query Prometheus: {e}")
        return 0

def calculate_target_replicas(queue_depth):
    """Calculate target replicas based on queue depth"""
    for threshold, replicas in sorted(QUEUE_DEPTH_THRESHOLDS.items()):
        if queue_depth <= threshold:
            return max(MIN_REPLICAS, replicas)
    return MAX_REPLICAS

def get_current_replicas():
    """Get current replica count"""
    try:
        deployment = v1.read_namespaced_deployment(DEPLOYMENT, NAMESPACE)
        return deployment.spec.replicas
    except Exception as e:
        logger.error(f"Failed to get deployment: {e}")
        return MIN_REPLICAS

def scale_deployment(target_replicas):
    """Scale deployment to target replicas"""
    try:
        deployment = v1.read_namespaced_deployment(DEPLOYMENT, NAMESPACE)
        deployment.spec.replicas = target_replicas
        v1.patch_namespaced_deployment(DEPLOYMENT, NAMESPACE, deployment)
        logger.info(f"Scaled {DEPLOYMENT} to {target_replicas} replicas")
        return True
    except Exception as e:
        logger.error(f"Failed to scale deployment: {e}")
        return False

def autoscale_loop():
    """Main autoscaler loop"""
    logger.info("Custom Autoscaler started")
    
    while True:
        try:
            queue_depth = get_queue_depth()
            current_replicas = get_current_replicas()
            target_replicas = calculate_target_replicas(queue_depth)
            
            logger.info(
                f"Queue: {queue_depth} | Current: {current_replicas} replicas | "
                f"Target: {target_replicas} replicas"
            )
            
            if target_replicas != current_replicas:
                scale_deployment(target_replicas)
            
        except Exception as e:
            logger.error(f"Error in autoscale loop: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    autoscale_loop()