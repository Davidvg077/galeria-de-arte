# Despliegue local en Kubernetes

Estos recursos despliegan el sitio estático Astro de GART Gallery en el namespace
`gart-gallery`. El contenedor sirve la web en el puerto 8080; Kubernetes expone
el servicio internamente en el puerto 80. El frontend no incluye el API Gateway.

## Requisitos

- Docker Desktop con Kubernetes habilitado, o Minikube iniciado.
- `kubectl` configurado para apuntar al clúster local.
- Node.js no es necesario en el equipo anfitrión; la imagen compila Astro con Node 20.

Confirma que el contexto es el clúster local correcto antes de aplicar recursos:

```powershell
kubectl config current-context
kubectl get nodes
```

## Construir y desplegar

Desde la raíz del repositorio, construye la imagen:

```powershell
docker build -f Dockerfile.frontend -t gart-gallery-frontend:local .
```

Si se usa Minikube, carga la imagen en el nodo del clúster:

```powershell
minikube image load gart-gallery-frontend:local
```

Aplica los recursos y espera a que ambas réplicas estén disponibles:

```powershell
kubectl apply -f deploy\kubernetes\app.yaml
kubectl rollout status deployment/gart-gallery-frontend -n gart-gallery --timeout=120s
kubectl get pods,services -n gart-gallery -o wide
```

En una terminal aparte, deja abierto el túnel local al Service:

```powershell
kubectl port-forward -n gart-gallery service/gart-gallery-frontend 8080:80
```

La página quedará disponible en <http://127.0.0.1:8080/>.

## Evidencias verificables

Con el `port-forward` aún activo, desde otra terminal ejecuta:

```powershell
.\scripts\capture-kubernetes-evidence.ps1
```

El script comprueba la respuesta HTTP de la página y del endpoint de salud, y
guarda la salida real de `kubectl` junto con los resultados HTTP en
`evidence\kubernetes\`. Los archivos generados sirven como evidencia de la
versión desplegada y deben revisarse antes de publicarse.

## Servicio Works y PostgreSQL

El microservicio Works ofrece búsqueda, filtros por categoría y paginación.
Su Deployment usa una cuenta no privilegiada, probes de salud y límites de
recursos. El StatefulSet de PostgreSQL mantiene los datos en un volumen
persistente de 1 GiB. La base de datos solo se expone dentro del clúster.

Desde la raíz del repositorio, ejecuta el script de despliegue:

```powershell
.\scripts\deploy-works-to-minikube.ps1
```

El script construye y carga la imagen local, genera aleatoriamente las
credenciales en un Secret de Kubernetes (no en el repositorio) y espera a que
PostgreSQL y Works estén listos. Conserva el Secret existente en ejecuciones
posteriores para no desincronizar la contraseña con el volumen de datos.

En una terminal aparte, expón el API:

```powershell
kubectl port-forward -n gart-gallery service/works-service 3002:3002
```

Comprueba el servicio y sus datos de ejemplo en otra terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:3002/health
Invoke-RestMethod http://127.0.0.1:3002/api/works
```

El PostgreSQL local del clúster contiene los datos de este servicio; no es una
base de datos para producción. Mantén el Secret fuera de Git y no uses esta
configuración de desarrollo para datos reales.

Para ver el estado en cualquier momento:

```powershell
kubectl get deployment,pods,services,endpoints -n gart-gallery -o wide
kubectl logs -n gart-gallery deployment/gart-gallery-frontend
```

Para retirar el despliegue:

```powershell
kubectl delete namespace gart-gallery
```
