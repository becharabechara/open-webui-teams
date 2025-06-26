Lagoon Maintenance Page

A simple Flask-based maintenance page styled like Open WebUI, displaying a maintenance message based on an environment variable.

## Setup

1. **Prerequisites**:
   - Docker and Docker Compose installed for local development.
   - AKS cluster for production deployment.

2. **Local Development**:
   - Create a `.env` file with `DEBUG_MAINTENANCE_STATUS=True` for maintenance mode or `False` for completion.
   - Run `docker-compose up --build` to start the app.
   - Access at `http://localhost:5000`.
   - To use with Cloudflared tunnel, update your tunnel configuration to point to `http://localhost:5000`.

3. **AKS Deployment**:
   - Build and push the Docker image:
     ```bash
     docker build -t yourregistry/lagoon-maintenance:latest .
     docker push yourregistry/lagoon-maintenance:latest
     ```
   - Update your AKS deployment YAML to use the new image:
     ```yaml
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: lagoon-maintenance
     spec:
       replicas: 1
       selector:
         matchLabels:
           app: lagoon-maintenance
       template:
         metadata:
           labels:
             app: lagoon-maintenance
         spec:
           containers:
           - name: lagoon-maintenance
             image: yourregistry/lagoon-maintenance:latest
             ports:
             - containerPort: 5000
             env:
             - name: DEBUG_MAINTENANCE_STATUS
               value: "True" # or "False"
     ---
     apiVersion: v1
     kind: Service
     metadata:
       name: lagoon-maintenance
     spec:
       selector:
         app: lagoon-maintenance
       ports:
       - protocol: TCP
         port: 80
         targetPort: 5000
       type: ClusterIP
     ```
   - Apply the YAML: `kubectl apply -f deployment.yaml`.
   - Update your ingress or service to route traffic from your Open WebUI service to this maintenance service.

4. **Switching Services**:
   - **Local**: Update your Cloudflared tunnel to point to the maintenance container's port (5000).
   - **AKS**: Update your ingress or service routing to point to the `lagoon-maintenance` service instead of Open WebUI during maintenance.

## Environment Variables
- `DEBUG_MAINTENANCE_STATUS`:
  - `True`: Displays "Lagoon is under maintenance please check back".
  - `False`: Displays "Lagoon maintenance is done, if you are still seeing this page please refresh your browser or Teams application".