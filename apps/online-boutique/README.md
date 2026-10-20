# Online Boutique

Kubernetes manifests are from GoogleCloudPlatform/microservices-demo release v0.10.7:
https://github.com/GoogleCloudPlatform/microservices-demo

The frontend-external Service is set to ClusterIP for this cost-conscious EKS
deployment. Use kubectl port-forward to access the frontend; do not create a
public load balancer for this demo.
