# Bot de Telegram para Control de Gastos

Bot de Telegram desarrollado en Python para llevar control de gastos personales en Venezuela, con conversión automática a USD y soporte para intercambios Binance/USDT.

## Características

- ✅ Registro de gastos en bolívares con conversión automática a USD
- ✅ Seguimiento de ingresos mensuales
- ✅ Sistema de intercambios Bs ↔ USDT (Binance)
- ✅ Categorización de gastos
- ✅ Estadísticas avanzadas y resúmenes mensuales
- ✅ Presupuestos mensuales
- ✅ Comparación mes a mes
- ✅ Búsqueda y filtros de gastos
- ✅ Exportación a CSV
- ✅ Integración con Gemini AI para consultas inteligentes
- ✅ Detección automática de múltiples gastos en un mensaje
- ✅ Registro de saldo disponible (ingreso - gastos - intercambios)

## Requisitos

- Python 3.7+
- Token de Telegram Bot (obtener en [@BotFather](https://t.me/botfather))
- API Key de Google Gemini (opcional, para funcionalidad de IA)

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/Elingevic/proyectobot.git
cd proyectobot
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Crear archivo `.env` en la raíz del proyecto:
```
TELEGRAM_TOKEN=tu_token_de_telegram
GEMINI_API_KEY=tu_api_key_de_gemini
```

## Uso

1. Ejecutar el bot:
```bash
python bot.py
```

2. Comandos disponibles:
- `/start` - Ver todos los comandos disponibles
- `/gasto <cantidad> [categoria] [descripcion]` - Registrar un gasto
- `/ingreso <cantidad_bs> [tasa]` - Registrar ingreso mensual
- `/cambiar <cantidad_bs> [tasa]` - Intercambiar Bs a USDT
- `/resumen` - Ver resumen del mes
- `/estadisticas` - Estadísticas avanzadas
- `/gastos_hoy` - Gastos del día actual
- `/binance_rate` - Tasa paralela (Binance/USDT)
- `/dolar` - Tipo de cambio oficial
- `/ai <pregunta>` - Pregunta a la IA

## Ejemplos de uso

### Registrar gastos
```
/gasto 22000 comida almuerzo
gasté 50bs en el pasaje, 100 en una galleta
```

### Registrar ingreso mensual
```
/ingreso 120000 330
```

### Intercambiar a USDT
```
/cambiar 6400 320
compre 20 usdt a 320
```

### Consultar gastos
```
cuanto gaste hoy?
/resumen
/gastos_hoy
```

## API Externa

El bot utiliza la API de [dolarapi.com](https://dolarapi.com) para obtener:
- Tipo de cambio oficial del dólar
- Tipo de cambio paralelo (Binance/USDT)

## Estructura de Archivos

- `bot.py` - Código principal del bot
- `.env` - Variables de entorno (no incluido en el repo)
- `gastos.json` - Base de datos de gastos (generado automáticamente)
- `intercambios.json` - Base de datos de intercambios (generado automáticamente)
- `ingresos.json` - Base de datos de ingresos (generado automáticamente)

## Notas

- Los archivos `.json` contienen información personal y no deben compartirse
- El archivo `.env` contiene credenciales sensibles y no debe subirse al repositorio
- El bot diferencia entre **gastos** (consumo) e **intercambios** (compra de divisa)

## Despliegue en VPS

### Opción 1: Script automático
```bash
chmod +x deploy.sh
./deploy.sh
```

### Opción 2: Manual

1. Clonar el repositorio en el servidor:
```bash
cd /opt
sudo mkdir telegram-bot
sudo chown $USER:$USER telegram-bot
cd telegram-bot
git clone https://github.com/Elingevic/proyectobot.git .
```

2. Instalar dependencias:
```bash
pip3 install -r requirements.txt
```

3. Crear archivo `.env`:
```bash
nano .env
# Agregar:
# TELEGRAM_TOKEN=tu_token
# GEMINI_API_KEY=tu_api_key
```

4. Ejecutar el bot (prueba):
```bash
python3 bot.py
```

5. Configurar como servicio systemd (para que se ejecute automáticamente):
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Agregar:
```ini
[Unit]
Description=Telegram Bot de Control de Gastos
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/opt/telegram-bot
ExecStart=/usr/bin/python3 /opt/telegram-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

6. Activar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl start telegram-bot
sudo systemctl enable telegram-bot
sudo systemctl status telegram-bot
```

7. Ver logs:
```bash
sudo journalctl -u telegram-bot -f
```

**Nota:** El bot usa polling, no requiere puerto web. No hay conflicto con otros servicios que usen puertos HTTP.

## Licencia

Este proyecto es de uso personal.

