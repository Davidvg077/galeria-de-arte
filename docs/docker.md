# Docker: sitio redundante y servicio Works

El despliegue local usa Docker Compose para arrancar el frontend principal, una
copia de respaldo, un proxy con failover automático, el microservicio Works y
PostgreSQL con almacenamiento persistente.

## Desplegar y comprobar failover

Desde PowerShell, en la raíz del proyecto:

```powershell
.\scripts\deploy-docker.ps1
```

El script genera `.env.docker` localmente con una contraseña aleatoria si aún no
existe. Ese archivo está excluido de Git; no compartas ni subas sus credenciales.
La contraseña se conserva para que una base de datos ya inicializada pueda
reiniciarse con su volumen existente.

Al finalizar, el script comprueba el sitio y la API, detiene temporalmente el
frontend principal para verificar el failover hacia la copia y vuelve a iniciar
el principal.

| Servicio | URL |
| --- | --- |
| Sitio principal con failover automático | <http://127.0.0.1:8080/> |
| Copia de respaldo directa | <http://127.0.0.1:8081/> |
| API Works | <http://127.0.0.1:3002/docs> |
| Salud de Works | <http://127.0.0.1:3002/health> |

El proxy envía tráfico al frontend principal; si este falla, reintenta contra la
copia. Ambos usan la misma imagen, pero se ejecutan como contenedores distintos.
Docker Desktop muestra cinco contenedores: proxy, frontend principal, copia,
Works y PostgreSQL.

## Comandos útiles

```powershell
docker compose --env-file .env.docker -f compose.yaml ps
docker compose --env-file .env.docker -f compose.yaml logs --follow
docker compose --env-file .env.docker -f compose.yaml stop
docker compose --env-file .env.docker -f compose.yaml up --detach
```

Los datos de Works persisten en el volumen Docker `gart-gallery-postgres-data`.
Para detener el despliegue sin borrar datos, usa `stop`. Para borrar también la
base de datos y su volumen, ejecuta `docker compose ... down --volumes`; esta
última operación es destructiva.
