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
pip install python-telegram-bot python-dotenv google-generativeai requests
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

## Licencia

Este proyecto es de uso personal.

