# Docker: sitio redundante y microservicios

El despliegue local usa Docker Compose para arrancar el frontend principal, una
copia de respaldo, un proxy con failover automático, los servicios Works,
Gallery, Auth, Purchase y Content, y PostgreSQL con almacenamiento persistente.

## Desplegar y comprobar failover

Desde PowerShell, en la raíz del proyecto:

```powershell
.\back\scripts\deploy-compose.ps1
```

El script genera `back/.env.docker` localmente con una contraseña aleatoria para
PostgreSQL y un pepper criptográfico para los códigos OTP. Ese archivo está
excluido de Git; no compartas ni subas sus credenciales. Los valores se
conservan entre reinicios y deben respaldarse de forma segura junto con la base.

Al finalizar, el script comprueba el sitio y la API, detiene temporalmente el
frontend principal para verificar el failover hacia la copia y vuelve a iniciar
el principal. Guarda el estado de los contenedores y los resultados de ambas
API antes y durante el failover en `back\evidence\docker\`, sin incluir secretos.

| Servicio | URL |
| --- | --- |
| Sitio principal con failover automático | <http://127.0.0.1:8080/> |
| Copia de respaldo directa | <http://127.0.0.1:8081/> |
| API Works | <http://127.0.0.1:3002/docs> |
| API Gallery | <http://127.0.0.1:3001/docs> |
| API Auth | <http://127.0.0.1:3003/docs> |
| API Purchase | <http://127.0.0.1:3004/docs> |
| API Content | <http://127.0.0.1:3005/docs> |
| Salud de Works | <http://127.0.0.1:3002/health> |
| Obras a través del sitio | <http://127.0.0.1:8080/api/works?limit=4> |
| Galerías a través del sitio | <http://127.0.0.1:8080/api/galleries> |
| Auth, Content y Purchase | Se enrutan por `/api/` en el puerto 8080 |

El proxy envía tráfico al frontend principal; si este falla, reintenta contra la
copia. Ambos usan la misma imagen, pero se ejecutan como contenedores distintos.
Docker Desktop muestra nueve contenedores: proxy, dos frontends, cinco
microservicios y PostgreSQL. Los
servicios Auth, Purchase y Content también están disponibles detrás del proxy.
Los puertos directos de los microservicios están enlazados solo a `127.0.0.1`
para facilitar pruebas locales; el frontend debe usar el proxy del puerto 8080.
Si se ejecuta Astro en modo desarrollo (puerto 4321), configura
`FRONTEND_ORIGIN=http://localhost:4321` en el entorno de los servicios.

## Cuentas y verificaciones de demostración

No se crea una cuenta de administrador con credenciales predeterminadas. Para
provisionar el administrador local antes del primer arranque, configura
`ADMIN_PASSWORD` (al menos 12 caracteres) y, opcionalmente, `ADMIN_USER` en el
entorno desde el que ejecutas el script. Si el administrador anterior usaba la
contraseña predeterminada `admin123`, la migración lo desactiva; configura una
nueva contraseña para volver a habilitarlo.

El correo y el teléfono están en `Modo demostración`: no se configura SMTP,
Mailpit, SMS ni un proveedor externo, y no se envían mensajes reales. Los OTP
temporales se muestran únicamente a la sesión autenticada que los solicita;
sus hashes se guardan en la base de datos, expiran, son de un solo uso y están
limitados a cinco intentos. La recuperación de contraseña por correo está
deshabilitada en este modo. `TOKEN_PEPPER` se genera localmente; en Render debe
configurarse como un secreto aleatorio de al menos 32 caracteres. Un pedido
confirmado queda en `pending_payment`; no se integra un proveedor de pagos ni
se realiza ningún cobro.

La sesión se almacena en una cookie `HttpOnly`, `SameSite=Strict`, con duración
de 12 horas; en este HTTP local, `COOKIE_SECURE=false` permite probarla. En
producción usa `COOKIE_SECURE=true` y HTTPS.

## Comandos útiles

```powershell
docker compose --env-file back/.env.docker -f back/compose.yaml ps
docker compose --env-file back/.env.docker -f back/compose.yaml logs --follow
docker compose --env-file back/.env.docker -f back/compose.yaml stop
docker compose --env-file back/.env.docker -f back/compose.yaml up --detach
```

Los datos de Works persisten en el volumen Docker `gart-gallery-postgres-data`.
Para detener el despliegue sin borrar datos, usa `stop`. Para borrar también la
base de datos y su volumen, ejecuta `docker compose --env-file back/.env.docker -f back/compose.yaml down --volumes`; esta
última operación es destructiva.
