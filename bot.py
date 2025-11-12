import json
import os
import csv
import uuid
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from dotenv import load_dotenv
import google.generativeai as genai

# Cargar variables de entorno
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f" Archivo .env cargado desde: {env_path}")
else:
    load_dotenv()
    print(f" Intentando cargar .env desde directorio actual")
    if not os.path.exists('.env'):
        print(f" Archivo .env no encontrado en: {os.getcwd()}")

# Configurar Gemini AI
try:
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        model_name = None
        try:
            gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            model_name = 'gemini-2.5-flash'
        except:
            try:
                gemini_model = genai.GenerativeModel('gemini-2.5-pro')
                model_name = 'gemini-2.5-pro'
            except:
                try:
                    gemini_model = genai.GenerativeModel('gemini-pro-latest')
                    model_name = 'gemini-pro-latest'
                except:
                    gemini_model = genai.GenerativeModel('gemini-pro')
                    model_name = 'gemini-pro'
        
        gemini_enabled = True
        print(f" Gemini AI configurado correctamente (modelo: {model_name})")
    else:
        print("Advertencia: GEMINI_API_KEY no encontrada en .env")
        gemini_model = None
        gemini_enabled = False
except Exception as e:
    print(f"Error al configurar Gemini: {e}")
    import traceback
    traceback.print_exc()
    gemini_model = None
    gemini_enabled = False

# Archivos
GASTOS_FILE = "gastos.json"
PRESUPUESTOS_FILE = "presupuestos.json"
INTERCAMBIOS_FILE = "intercambios.json"
INGRESOS_FILE = "ingresos.json"

# Categorías disponibles
CATEGORIAS = [
    "comida", "transporte", "servicios", "entretenimiento", 
    "salud", "educacion", "ropa", "tecnologia", "hogar", "otros"
]

def get_dollar_rate():
    """Obtiene el tipo de cambio del dólar oficial desde la API"""
    try:
        response = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data.get("promedio") or data.get("venta") or data.get("compra")
        if rate:
            return float(rate)
        return None
    except Exception as e:
        print(f"Error al obtener tipo de cambio: {e}")
        return None

def get_parallel_rate():
    """Obtiene el tipo de cambio paralelo (Binance/USDT) desde la API"""
    try:
        response = requests.get("https://ve.dolarapi.com/v1/dolares/paralelo", timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data.get("promedio") or data.get("venta") or data.get("compra")
        if rate:
            return float(rate)
        return None
    except Exception as e:
        print(f"Error al obtener tipo de cambio paralelo: {e}")
        return None

def load_gastos():
    """Carga los gastos desde el archivo JSON"""
    if os.path.exists(GASTOS_FILE):
        try:
            with open(GASTOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_gastos(gastos):
    """Guarda los gastos en el archivo JSON"""
    with open(GASTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(gastos, f, ensure_ascii=False, indent=2)

def load_presupuestos():
    """Carga los presupuestos desde el archivo JSON"""
    if os.path.exists(PRESUPUESTOS_FILE):
        try:
            with open(PRESUPUESTOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_presupuestos(presupuestos):
    """Guarda los presupuestos en el archivo JSON"""
    with open(PRESUPUESTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(presupuestos, f, ensure_ascii=False, indent=2)

def load_intercambios():
    """Carga los intercambios Bs->USDT desde el archivo JSON"""
    if os.path.exists(INTERCAMBIOS_FILE):
        try:
            with open(INTERCAMBIOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_intercambios(intercambios):
    """Guarda los intercambios en el archivo JSON"""
    with open(INTERCAMBIOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(intercambios, f, ensure_ascii=False, indent=2)

def load_ingresos():
    """Carga los ingresos mensuales desde el archivo JSON"""
    if os.path.exists(INGRESOS_FILE):
        try:
            with open(INGRESOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_ingresos(ingresos):
    """Guarda los ingresos en el archivo JSON"""
    with open(INGRESOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ingresos, f, ensure_ascii=False, indent=2)

def add_intercambio(user_id, amount_bs, tasa_paralela, descripcion=""):
    """Registra un intercambio de Bs a USDT (compra de divisa, NO es gasto)"""
    intercambios = load_intercambios()
    
    if str(user_id) not in intercambios:
        intercambios[str(user_id)] = {}
    
    month_key = get_current_month_key()
    if month_key not in intercambios[str(user_id)]:
        intercambios[str(user_id)][month_key] = []
    
    amount_usdt = amount_bs / tasa_paralela
    intercambio_id = str(uuid.uuid4())[:8]
    
    intercambio = {
        "id": intercambio_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bolivares": amount_bs,
        "usdt": round(amount_usdt, 4),
        "tasa_paralela": tasa_paralela,
        "descripcion": descripcion
    }
    
    intercambios[str(user_id)][month_key].append(intercambio)
    save_intercambios(intercambios)
    
    return amount_usdt, intercambio_id

def get_intercambios_month(user_id, month_key=None):
    """Obtiene intercambios del mes"""
    if month_key is None:
        month_key = get_current_month_key()
    
    intercambios = load_intercambios()
    if str(user_id) not in intercambios or month_key not in intercambios[str(user_id)]:
        return []
    
    return intercambios[str(user_id)][month_key]

def set_ingreso_mensual(user_id, amount_bs, tasa_paralela=None):
    """Establece el ingreso mensual del usuario"""
    if tasa_paralela is None:
        tasa_paralela = get_parallel_rate() or get_dollar_rate() or 0
    
    ingresos = load_ingresos()
    if str(user_id) not in ingresos:
        ingresos[str(user_id)] = {}
    
    month_key = get_current_month_key()
    amount_usdt = amount_bs / tasa_paralela if tasa_paralela > 0 else 0
    
    ingresos[str(user_id)][month_key] = {
        "bolivares": amount_bs,
        "usdt": round(amount_usdt, 4),
        "tasa_paralela": tasa_paralela,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    save_ingresos(ingresos)
    return amount_usdt

def get_ingreso_mensual(user_id, month_key=None):
    """Obtiene el ingreso mensual del usuario"""
    if month_key is None:
        month_key = get_current_month_key()
    
    ingresos = load_ingresos()
    if str(user_id) not in ingresos or month_key not in ingresos[str(user_id)]:
        return None
    
    return ingresos[str(user_id)][month_key]

def get_saldo_disponible(user_id, month_key=None):
    """Calcula el saldo disponible del mes (ingreso - gastos - intercambios)"""
    if month_key is None:
        month_key = get_current_month_key()
    
    ingreso = get_ingreso_mensual(user_id, month_key)
    if not ingreso:
        return None, None, None, None
    
    # Gastos del mes
    total_bs_gastos, total_usd_gastos, gastos = get_month_summary(user_id, month_key)
    total_bs_gastos = total_bs_gastos or 0
    total_usd_gastos = total_usd_gastos or 0
    
    # Intercambios del mes (Bs convertidos a USDT)
    intercambios = get_intercambios_month(user_id, month_key)
    total_bs_intercambios = sum(i["bolivares"] for i in intercambios)
    total_usdt_intercambios = sum(i["usdt"] for i in intercambios)
    
    # Calcular saldo disponible
    saldo_bs = ingreso["bolivares"] - total_bs_gastos - total_bs_intercambios
    saldo_usdt = ingreso["usdt"] - total_usd_gastos - total_usdt_intercambios
    
    return saldo_bs, saldo_usdt, total_bs_intercambios, total_usdt_intercambios

def get_current_month_key():
    """Obtiene la clave del mes actual (YYYY-MM)"""
    return datetime.now().strftime("%Y-%m")

def get_previous_month_key():
    """Obtiene la clave del mes anterior"""
    last_month = datetime.now() - timedelta(days=datetime.now().day)
    return last_month.strftime("%Y-%m")

def add_gasto(user_id, amount_bs, dollar_rate, categoria="otros", descripcion=""):
    """Agrega un gasto al registro del usuario"""
    gastos = load_gastos()
    
    if str(user_id) not in gastos:
        gastos[str(user_id)] = {}
    
    month_key = get_current_month_key()
    if month_key not in gastos[str(user_id)]:
        gastos[str(user_id)][month_key] = []
    
    amount_usd = amount_bs / dollar_rate
    gasto_id = str(uuid.uuid4())[:8]
    gasto = {
        "id": gasto_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bolivares": amount_bs,
        "dolares": round(amount_usd, 2),
        "tipo_cambio": dollar_rate,
        "categoria": categoria.lower(),
        "descripcion": descripcion
    }
    
    gastos[str(user_id)][month_key].append(gasto)
    save_gastos(gastos)
    
    return amount_usd, gasto_id

def get_gasto_by_id(user_id, gasto_id):
    """Obtiene un gasto por su ID"""
    gastos = load_gastos()
    if str(user_id) not in gastos:
        return None, None, None
    
    for month_key, month_gastos in gastos[str(user_id)].items():
        for gasto in month_gastos:
            if gasto.get("id") == gasto_id:
                return gasto, month_key, month_gastos
    return None, None, None

def delete_gasto(user_id, gasto_id):
    """Elimina un gasto por su ID"""
    gastos = load_gastos()
    if str(user_id) not in gastos:
        return False
    
    for month_key, month_gastos in gastos[str(user_id)].items():
        for i, gasto in enumerate(month_gastos):
            if gasto.get("id") == gasto_id:
                del month_gastos[i]
                save_gastos(gastos)
                return True
    return False

def edit_gasto(user_id, gasto_id, new_amount_bs=None, new_categoria=None, new_descripcion=None):
    """Edita un gasto existente"""
    gasto, month_key, month_gastos = get_gasto_by_id(user_id, gasto_id)
    if not gasto:
        return False
    
    if new_amount_bs is not None:
        dollar_rate = gasto.get("tipo_cambio", get_dollar_rate())
        if dollar_rate:
            gasto["bolivares"] = new_amount_bs
            gasto["dolares"] = round(new_amount_bs / dollar_rate, 2)
    
    if new_categoria:
        gasto["categoria"] = new_categoria.lower()
    
    if new_descripcion is not None:
        gasto["descripcion"] = new_descripcion
    
    save_gastos(load_gastos())
    return True

def get_month_summary(user_id, month_key=None):
    """Obtiene el resumen de gastos del mes especificado o actual"""
    gastos = load_gastos()
    if month_key is None:
        month_key = get_current_month_key()
    
    if str(user_id) not in gastos or month_key not in gastos[str(user_id)]:
        return None, None, []
    
    month_gastos = gastos[str(user_id)][month_key]
    total_bs = sum(g["bolivares"] for g in month_gastos)
    total_usd = sum(g["dolares"] for g in month_gastos)
    
    return total_bs, total_usd, month_gastos

def get_all_gastos(user_id):
    """Obtiene todos los gastos del usuario"""
    gastos = load_gastos()
    if str(user_id) not in gastos:
        return []
    
    all_gastos = []
    for month_key, month_gastos in gastos[str(user_id)].items():
        for gasto in month_gastos:
            gasto["month_key"] = month_key
            all_gastos.append(gasto)
    return all_gastos

def get_gastos_by_date(user_id, fecha):
    """Obtiene gastos de una fecha específica"""
    all_gastos = get_all_gastos(user_id)
    # Convertir fecha a string si es datetime.date o datetime
    if isinstance(fecha, datetime):
        fecha_str = fecha.strftime("%Y-%m-%d")
    elif isinstance(fecha, type(datetime.now().date())):
        fecha_str = fecha.strftime("%Y-%m-%d")
    else:
        fecha_str = str(fecha)
    
    # Buscar gastos que empiecen con la fecha (formato: "YYYY-MM-DD HH:MM:SS")
    return [g for g in all_gastos if g.get("fecha", "").startswith(fecha_str)]

def get_gastos_by_range(user_id, min_amount=None, max_amount=None):
    """Obtiene gastos por rango de montos"""
    all_gastos = get_all_gastos(user_id)
    filtered = []
    for g in all_gastos:
        if min_amount is not None and g["bolivares"] < min_amount:
            continue
        if max_amount is not None and g["bolivares"] > max_amount:
            continue
        filtered.append(g)
    return filtered

def get_statistics(user_id):
    """Obtiene estadísticas avanzadas del mes actual"""
    total_bs, total_usd, gastos = get_month_summary(user_id)
    
    if not gastos:
        return None
    
    amounts_bs = [g["bolivares"] for g in gastos]
    amounts_usd = [g["dolares"] for g in gastos]
    
    # Estadísticas básicas
    stats = {
        "total_bs": total_bs,
        "total_usd": total_usd,
        "count": len(gastos),
        "promedio_diario_bs": total_bs / datetime.now().day if datetime.now().day > 0 else 0,
        "promedio_diario_usd": total_usd / datetime.now().day if datetime.now().day > 0 else 0,
        "max_bs": max(amounts_bs),
        "min_bs": min(amounts_bs),
        "max_usd": max(amounts_usd),
        "min_usd": min(amounts_usd),
    }
    
    # Gasto máximo y mínimo
    max_gasto = max(gastos, key=lambda x: x["bolivares"])
    min_gasto = min(gastos, key=lambda x: x["bolivares"])
    stats["max_gasto"] = max_gasto
    stats["min_gasto"] = min_gasto
    
    # Gastos por categoría
    by_category = {}
    for g in gastos:
        cat = g.get("categoria", "otros")
        if cat not in by_category:
            by_category[cat] = {"bs": 0, "usd": 0, "count": 0}
        by_category[cat]["bs"] += g["bolivares"]
        by_category[cat]["usd"] += g["dolares"]
        by_category[cat]["count"] += 1
    stats["by_category"] = by_category
    
    # Gastos por día
    by_day = {}
    for g in gastos:
        fecha = g["fecha"].split()[0]
        if fecha not in by_day:
            by_day[fecha] = {"bs": 0, "usd": 0, "count": 0}
        by_day[fecha]["bs"] += g["bolivares"]
        by_day[fecha]["usd"] += g["dolares"]
        by_day[fecha]["count"] += 1
    
    max_day = max(by_day.items(), key=lambda x: x[1]["bs"]) if by_day else None
    stats["max_day"] = max_day
    
    return stats

def get_presupuesto(user_id, month_key=None):
    """Obtiene el presupuesto del usuario para un mes"""
    if month_key is None:
        month_key = get_current_month_key()
    
    presupuestos = load_presupuestos()
    user_presupuestos = presupuestos.get(str(user_id), {})
    return user_presupuestos.get(month_key)

def set_presupuesto(user_id, amount_usd, month_key=None):
    """Establece el presupuesto del usuario para un mes"""
    if month_key is None:
        month_key = get_current_month_key()
    
    presupuestos = load_presupuestos()
    if str(user_id) not in presupuestos:
        presupuestos[str(user_id)] = {}
    
    presupuestos[str(user_id)][month_key] = amount_usd
    save_presupuestos(presupuestos)

def export_to_csv(user_id):
    """Exporta los gastos del usuario a CSV"""
    all_gastos = get_all_gastos(user_id)
    if not all_gastos:
        return None
    
    filename = f"gastos_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(script_dir, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Fecha', 'Bolívares', 'Dólares', 'Tipo Cambio', 'Categoría', 'Descripción'])
        for g in all_gastos:
            writer.writerow([
                g.get("id", ""),
                g.get("fecha", ""),
                g.get("bolivares", 0),
                g.get("dolares", 0),
                g.get("tipo_cambio", 0),
                g.get("categoria", "otros"),
                g.get("descripcion", "")
            ])
    
    return filepath

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start - Mensaje de bienvenida"""
    ai_status = "Activada" if gemini_enabled else "No disponible"
    welcome_message = (
        f"Hola {update.effective_user.first_name}\n\n"
        "Bot de Control de Gastos con IA\n\n"
        "Comandos principales:\n"
        "/gasto <cantidad> [categoria] [descripcion] - Registra un gasto\n"
        "/resumen - Resumen del mes\n"
        "/listar [n] - Lista ultimos gastos\n"
        "/estadisticas - Estadisticas avanzadas\n"
        "/dolar - Tipo de cambio actual\n"
        "/presupuesto [monto] - Ver o establecer presupuesto\n"
        "/comparar - Comparar con mes anterior\n"
        "/buscar <fecha|rango> - Buscar gastos\n"
        "/gastos_hoy - Gastos del dia actual\n"
        "/exportar - Exportar a CSV\n"
        "/eliminar <id> - Eliminar gasto\n"
        "/editar <id> <monto> - Editar gasto\n\n"
        "Sistema de Ingresos:\n"
        "/ingreso <cantidad_bs> [tasa] - Registrar ingreso mensual\n\n"
        "Intercambios (Binance/USDT):\n"
        "/binance_rate - Tasa paralela (Binance)\n"
        "/cambiar <bs> [tasa] - Intercambiar Bs a USDT\n\n"
        "/dolar - Tipo de cambio oficial\n"
        "/ai <pregunta> - Pregunta a la IA\n\n"
        f"IA: {ai_status}\n\n"
        "Categorias disponibles: comida, transporte, servicios, entretenimiento, salud, educacion, ropa, tecnologia, hogar, otros"
    )
    await update.message.reply_text(welcome_message)

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /gasto - Registra un gasto"""
    if not context.args:
        await update.message.reply_text(
            "Por favor, indica la cantidad en bolivares.\n"
            "Ejemplo: /gasto 22000\n"
            "Ejemplo con categoria: /gasto 22000 comida\n"
            "Ejemplo completo: /gasto 22000 comida almuerzo"
        )
        return
    
    try:
        amount_bs = float(context.args[0].replace(',', '.'))
        
        if amount_bs <= 0:
            await update.message.reply_text("La cantidad debe ser mayor a 0")
            return
        
        categoria = "otros"
        descripcion = ""
        
        if len(context.args) > 1:
            if context.args[1].lower() in CATEGORIAS:
                categoria = context.args[1].lower()
                if len(context.args) > 2:
                    descripcion = " ".join(context.args[2:])
            else:
                descripcion = " ".join(context.args[1:])
        
        dollar_rate = get_dollar_rate()
        if dollar_rate is None or dollar_rate == 0:
            await update.message.reply_text(
                "Error al obtener el tipo de cambio. Intenta mas tarde."
            )
            return
        
        amount_usd, gasto_id = add_gasto(
            update.effective_user.id, 
            amount_bs, 
            dollar_rate, 
            categoria, 
            descripcion
        )
        
        message = (
            f"Gasto registrado (ID: {gasto_id})\n\n"
            f"{amount_bs:,.2f} Bs\n"
            f"${amount_usd:,.2f} USD\n"
            f"Tipo de cambio: {dollar_rate:,.2f} Bs/$\n"
            f"Categoria: {categoria}\n"
        )
        if descripcion:
            message += f"Descripcion: {descripcion}"
        
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un numero valido.\n"
            "Ejemplo: /gasto 22000"
        )

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /listar - Lista los ultimos gastos"""
    n = 10
    if context.args:
        try:
            n = int(context.args[0])
            if n < 1 or n > 50:
                n = 10
        except:
            pass
    
    total_bs, total_usd, gastos = get_month_summary(update.effective_user.id)
    
    if not gastos:
        await update.message.reply_text("No hay gastos registrados este mes.")
        return
    
    gastos_recientes = gastos[-n:]
    message = f"Ultimos {len(gastos_recientes)} gastos:\n\n"
    
    for g in reversed(gastos_recientes):
        fecha = g["fecha"].split()[0]
        hora = g["fecha"].split()[1] if len(g["fecha"].split()) > 1 else ""
        message += (
            f"ID: {g.get('id', 'N/A')}\n"
            f"Fecha: {fecha} {hora}\n"
            f"Monto: {g['bolivares']:,.2f} Bs (${g['dolares']:,.2f} USD)\n"
            f"Categoria: {g.get('categoria', 'otros')}\n"
        )
        if g.get("descripcion"):
            message += f"Descripcion: {g['descripcion']}\n"
        message += "\n"
    
    await update.message.reply_text(message)

async def eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /eliminar - Elimina un gasto"""
    if not context.args:
        await update.message.reply_text(
            "Por favor, indica el ID del gasto a eliminar.\n"
            "Ejemplo: /eliminar abc12345\n"
            "Usa /listar para ver los IDs de tus gastos."
        )
        return
    
    gasto_id = context.args[0]
    gasto, _, _ = get_gasto_by_id(update.effective_user.id, gasto_id)
    
    if not gasto:
        await update.message.reply_text("Gasto no encontrado. Verifica el ID.")
        return
    
    if delete_gasto(update.effective_user.id, gasto_id):
        await update.message.reply_text(
            f"Gasto eliminado:\n"
            f"{gasto['bolivares']:,.2f} Bs (${gasto['dolares']:,.2f} USD)\n"
            f"Fecha: {gasto['fecha']}"
        )
    else:
        await update.message.reply_text("Error al eliminar el gasto.")

async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /editar - Edita un gasto"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Uso: /editar <id> <nuevo_monto> [categoria] [descripcion]\n"
            "Ejemplo: /editar abc12345 25000\n"
            "Ejemplo: /editar abc12345 25000 comida"
        )
        return
    
    gasto_id = context.args[0]
    try:
        new_amount = float(context.args[1].replace(',', '.'))
    except ValueError:
        await update.message.reply_text("El monto debe ser un numero valido.")
        return
    
    new_categoria = None
    new_descripcion = None
    
    if len(context.args) > 2:
        if context.args[2].lower() in CATEGORIAS:
            new_categoria = context.args[2].lower()
            if len(context.args) > 3:
                new_descripcion = " ".join(context.args[3:])
        else:
            new_descripcion = " ".join(context.args[2:])
    
    gasto, _, _ = get_gasto_by_id(update.effective_user.id, gasto_id)
    if not gasto:
        await update.message.reply_text("Gasto no encontrado.")
        return
    
    dollar_rate = gasto.get("tipo_cambio", get_dollar_rate())
    if edit_gasto(update.effective_user.id, gasto_id, new_amount, new_categoria, new_descripcion):
        new_usd = round(new_amount / dollar_rate, 2)
        await update.message.reply_text(
            f"Gasto editado:\n"
            f"Nuevo monto: {new_amount:,.2f} Bs (${new_usd:,.2f} USD)\n"
            f"ID: {gasto_id}"
        )
    else:
        await update.message.reply_text("Error al editar el gasto.")

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /resumen - Muestra el resumen completo del mes"""
    # Ingreso mensual
    ingreso = get_ingreso_mensual(update.effective_user.id)
    
    # Gastos
    total_bs_gastos, total_usd_gastos, gastos = get_month_summary(update.effective_user.id)
    total_bs_gastos = total_bs_gastos or 0
    total_usd_gastos = total_usd_gastos or 0
    gastos = gastos or []
    
    # Intercambios (compra de USDT, NO son gastos)
    intercambios = get_intercambios_month(update.effective_user.id)
    total_bs_intercambios = sum(i["bolivares"] for i in intercambios)
    total_usdt_intercambios = sum(i["usdt"] for i in intercambios)
    
    # Saldo disponible
    saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(update.effective_user.id)
    
    message = f"Resumen del mes ({get_current_month_key()})\n\n"
    
    # Ingreso
    if ingreso:
        message += (
            f"Ingreso mensual:\n"
            f"{ingreso['bolivares']:,.2f} Bs (${ingreso['usdt']:,.4f} USDT)\n"
            f"Tasa: {ingreso['tasa_paralela']:,.2f} Bs/USDT\n\n"
        )
    else:
        message += "Ingreso mensual: No registrado\n\n"
    
    # Gastos
    if len(gastos) > 0:
        message += (
            f"Gastos:\n"
            f"{total_bs_gastos:,.2f} Bs (${total_usd_gastos:,.2f} USD)\n"
            f"Numero de gastos: {len(gastos)}\n\n"
        )
    else:
        message += "Gastos: 0\n\n"
    
    # Intercambios (compra de divisa)
    if len(intercambios) > 0:
        message += (
            f"Intercambios (Bs -> USDT):\n"
            f"{total_bs_intercambios:,.2f} Bs -> {total_usdt_intercambios:,.4f} USDT\n"
            f"Numero de intercambios: {len(intercambios)}\n\n"
        )
    
    # Saldo disponible
    if saldo_bs is not None:
        message += (
            f"Saldo disponible:\n"
            f"{saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)\n\n"
        )
    elif ingreso:
        # Si hay ingreso pero no se puede calcular saldo (error en cálculo)
        message += "Saldo disponible: Error en calculo\n\n"
    
    # Por categoría (solo si hay gastos)
    if len(gastos) > 0:
        by_category = {}
        for g in gastos:
            cat = g.get("categoria", "otros")
            if cat not in by_category:
                by_category[cat] = {"bs": 0, "usd": 0}
            by_category[cat]["bs"] += g["bolivares"]
            by_category[cat]["usd"] += g["dolares"]
        
        if by_category:
            categoria_info = "Por categoria:\n"
            for cat, amounts in sorted(by_category.items(), key=lambda x: x[1]["usd"], reverse=True):
                categoria_info += f"{cat}: {amounts['bs']:,.2f} Bs (${amounts['usd']:,.2f} USD)\n"
            message += categoria_info
    
    # Presupuesto (si existe)
    presupuesto = get_presupuesto(update.effective_user.id)
    if presupuesto:
        porcentaje = (total_usd_gastos / presupuesto * 100) if presupuesto > 0 else 0
        message += f"\nPresupuesto: ${presupuesto:,.2f} USD (Usado: {porcentaje:.1f}%)"
    
    await update.message.reply_text(message)

async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /estadisticas - Muestra estadisticas avanzadas"""
    stats = get_statistics(update.effective_user.id)
    
    if not stats:
        await update.message.reply_text("No hay gastos registrados este mes.")
        return
    
    message = (
        f"Estadisticas del mes ({get_current_month_key()})\n\n"
        f"Total: {stats['total_bs']:,.2f} Bs (${stats['total_usd']:,.2f} USD)\n"
        f"Numero de gastos: {stats['count']}\n"
        f"Promedio diario: {stats['promedio_diario_bs']:,.2f} Bs (${stats['promedio_diario_usd']:,.2f} USD)\n\n"
        f"Gasto maximo: {stats['max_bs']:,.2f} Bs (${stats['max_usd']:,.2f} USD)\n"
        f"Fecha: {stats['max_gasto']['fecha']}\n"
        f"Categoria: {stats['max_gasto'].get('categoria', 'otros')}\n\n"
        f"Gasto minimo: {stats['min_bs']:,.2f} Bs (${stats['min_usd']:,.2f} USD)\n"
        f"Fecha: {stats['min_gasto']['fecha']}\n"
        f"Categoria: {stats['min_gasto'].get('categoria', 'otros')}\n"
    )
    
    if stats.get("max_day"):
        fecha, datos = stats["max_day"]
        message += (
            f"\nDia con mas gastos: {fecha}\n"
            f"Total: {datos['bs']:,.2f} Bs (${datos['usd']:,.2f} USD)\n"
            f"Gastos: {datos['count']}"
        )
    
    await update.message.reply_text(message)

async def presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /presupuesto - Ver o establecer presupuesto"""
    if not context.args:
        presupuesto = get_presupuesto(update.effective_user.id)
        if presupuesto:
            total_bs, total_usd, _ = get_month_summary(update.effective_user.id)
            porcentaje = (total_usd / presupuesto * 100) if presupuesto > 0 else 0
            restante = presupuesto - total_usd if total_usd else presupuesto
            
            message = (
                f"Presupuesto del mes ({get_current_month_key()})\n\n"
                f"Presupuesto: ${presupuesto:,.2f} USD\n"
                f"Gastado: ${total_usd:,.2f} USD ({porcentaje:.1f}%)\n"
                f"Restante: ${restante:,.2f} USD"
            )
            if porcentaje >= 100:
                message += "\n\nPRESUPUESTO EXCEDIDO"
            elif porcentaje >= 80:
                message += "\n\nCerca del limite"
        else:
            message = "No hay presupuesto establecido para este mes.\nUsa: /presupuesto <monto_en_usd>"
        await update.message.reply_text(message)
        return
    
    try:
        amount_usd = float(context.args[0].replace(',', '.'))
        if amount_usd <= 0:
            await update.message.reply_text("El presupuesto debe ser mayor a 0.")
            return
        
        set_presupuesto(update.effective_user.id, amount_usd)
        await update.message.reply_text(
            f"Presupuesto establecido: ${amount_usd:,.2f} USD para el mes {get_current_month_key()}"
        )
    except ValueError:
        await update.message.reply_text("Por favor, ingresa un numero valido.\nEjemplo: /presupuesto 500")

async def comparar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /comparar - Compara mes actual con mes anterior"""
    current_month = get_current_month_key()
    previous_month = get_previous_month_key()
    
    total_bs_curr, total_usd_curr, gastos_curr = get_month_summary(update.effective_user.id, current_month)
    total_bs_prev, total_usd_prev, gastos_prev = get_month_summary(update.effective_user.id, previous_month)
    
    if total_bs_curr is None and total_bs_prev is None:
        await update.message.reply_text("No hay datos para comparar.")
        return
    
    message = "Comparacion de meses\n\n"
    
    if total_bs_prev is not None:
        message += (
            f"Mes anterior ({previous_month}):\n"
            f"Total: {total_bs_prev:,.2f} Bs (${total_usd_prev:,.2f} USD)\n"
            f"Gastos: {len(gastos_prev)}\n\n"
        )
    else:
        message += f"Mes anterior ({previous_month}): Sin datos\n\n"
    
    if total_bs_curr is not None:
        message += (
            f"Mes actual ({current_month}):\n"
            f"Total: {total_bs_curr:,.2f} Bs (${total_usd_curr:,.2f} USD)\n"
            f"Gastos: {len(gastos_curr)}\n\n"
        )
    else:
        message += f"Mes actual ({current_month}): Sin datos\n\n"
    
    if total_bs_prev is not None and total_bs_curr is not None:
        diff_bs = total_bs_curr - total_bs_prev
        diff_usd = total_usd_curr - total_usd_prev
        diff_percent = (diff_usd / total_usd_prev * 100) if total_usd_prev > 0 else 0
        
        message += (
            f"Diferencia:\n"
            f"{diff_bs:+,.2f} Bs (${diff_usd:+,.2f} USD)\n"
            f"{diff_percent:+.1f}%"
        )
    
    await update.message.reply_text(message)

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /buscar - Busca gastos por fecha o rango"""
    if not context.args:
        await update.message.reply_text(
            "Uso: /buscar <fecha> o /buscar <min> <max>\n"
            "Ejemplo: /buscar 2025-11-11\n"
            "Ejemplo: /buscar 1000 50000"
        )
        return
    
    if len(context.args) == 1:
        # Buscar por fecha
        try:
            fecha_str = context.args[0]
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            gastos = get_gastos_by_date(update.effective_user.id, fecha)
        except ValueError:
            await update.message.reply_text("Formato de fecha invalido. Usa YYYY-MM-DD")
            return
    elif len(context.args) == 2:
        # Buscar por rango
        try:
            min_amount = float(context.args[0].replace(',', '.'))
            max_amount = float(context.args[1].replace(',', '.'))
            gastos = get_gastos_by_range(update.effective_user.id, min_amount, max_amount)
        except ValueError:
            await update.message.reply_text("Los montos deben ser numeros validos.")
            return
    else:
        await update.message.reply_text("Formato invalido. Ver /start para ayuda.")
        return
    
    if not gastos:
        await update.message.reply_text("No se encontraron gastos.")
        return
    
    total_bs = sum(g["bolivares"] for g in gastos)
    total_usd = sum(g["dolares"] for g in gastos)
    
    message = (
        f"Gastos encontrados: {len(gastos)}\n"
        f"Total: {total_bs:,.2f} Bs (${total_usd:,.2f} USD)\n\n"
    )
    
    for g in gastos[:10]:
        message += (
            f"ID: {g.get('id', 'N/A')}\n"
            f"Fecha: {g['fecha']}\n"
            f"Monto: {g['bolivares']:,.2f} Bs (${g['dolares']:,.2f} USD)\n"
            f"Categoria: {g.get('categoria', 'otros')}\n\n"
        )
    
    if len(gastos) > 10:
        message += f"... y {len(gastos) - 10} mas"
    
    await update.message.reply_text(message)

async def gastos_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /gastos_hoy - Muestra gastos del dia actual"""
    hoy = datetime.now().date()
    gastos = get_gastos_by_date(update.effective_user.id, hoy)
    
    if not gastos:
        await update.message.reply_text("No hay gastos registrados hoy.")
        return
    
    total_bs = sum(g["bolivares"] for g in gastos)
    total_usd = sum(g["dolares"] for g in gastos)
    
    message = (
        f"Gastos de hoy ({hoy.strftime('%Y-%m-%d')})\n\n"
        f"Total: {total_bs:,.2f} Bs (${total_usd:,.2f} USD)\n"
        f"Numero de gastos: {len(gastos)}\n\n"
    )
    
    for g in gastos:
        hora = g["fecha"].split()[1] if len(g["fecha"].split()) > 1 else ""
        message += (
            f"{hora} - {g['bolivares']:,.2f} Bs (${g['dolares']:,.2f} USD)\n"
            f"Categoria: {g.get('categoria', 'otros')}\n"
        )
        if g.get("descripcion"):
            message += f"Descripcion: {g['descripcion']}\n"
        message += "\n"
    
    await update.message.reply_text(message)

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /exportar - Exporta gastos a CSV"""
    filepath = export_to_csv(update.effective_user.id)
    
    if not filepath:
        await update.message.reply_text("No hay gastos para exportar.")
        return
    
    try:
        with open(filepath, 'rb') as f:
            await update.message.reply_document(document=f, filename=os.path.basename(filepath))
        os.remove(filepath)
    except Exception as e:
        await update.message.reply_text(f"Error al exportar: {e}")

async def dolar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /dolar - Muestra el tipo de cambio actual"""
    dollar_rate = get_dollar_rate()
    
    if dollar_rate is None or dollar_rate == 0:
        await update.message.reply_text(
            "Error al obtener el tipo de cambio. Intenta mas tarde."
        )
        return
    
    message = (
        f"Tipo de cambio del dolar oficial:\n\n"
        f"{dollar_rate:,.2f} Bs = 1 USD"
    )
    await update.message.reply_text(message)

async def binance_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /binance_rate - Muestra el tipo de cambio paralelo (Binance/USDT)"""
    parallel_rate = get_parallel_rate()
    
    if parallel_rate is None or parallel_rate == 0:
        await update.message.reply_text(
            "Error al obtener el tipo de cambio paralelo. Intenta mas tarde."
        )
        return
    
    official_rate = get_dollar_rate() or 0
    diferencia = parallel_rate - official_rate if official_rate > 0 else 0
    diferencia_porcentaje = (diferencia / official_rate * 100) if official_rate > 0 else 0
    
    message = (
        f"Tipo de cambio paralelo (Binance/USDT):\n\n"
        f"{parallel_rate:,.2f} Bs = 1 USDT\n\n"
        f"Comparacion:\n"
        f"Oficial: {official_rate:,.2f} Bs/$\n"
        f"Diferencia: {diferencia:+,.2f} Bs ({diferencia_porcentaje:+.1f}%)"
    )
    await update.message.reply_text(message)

async def cambiar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /cambiar - Intercambia bolívares a USDT (compra de divisa, NO es gasto)"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Uso: /cambiar <cantidad_bs> [tasa] [descripcion]\n"
            "Ejemplo: /cambiar 100000\n"
            "Ejemplo: /cambiar 100000 320\n"
            "Ejemplo: /cambiar 100000 320 compra de usdt\n\n"
            "Si no especificas la tasa, se usara la tasa paralela actual de la API."
        )
        return
    
    try:
        amount_bs = float(context.args[0].replace(',', '.'))
        
        if amount_bs <= 0:
            await update.message.reply_text("La cantidad debe ser mayor a 0")
            return
        
        # Verificar si hay tasa manual
        tasa_paralela = None
        descripcion = ""
        
        if len(context.args) > 1:
            # Intentar parsear como tasa
            try:
                tasa_paralela = float(context.args[1].replace(',', '.'))
                if len(context.args) > 2:
                    descripcion = " ".join(context.args[2:])
            except ValueError:
                # No es número, es descripción
                descripcion = " ".join(context.args[1:])
        
        # Si no se especificó tasa, usar la de la API
        if tasa_paralela is None or tasa_paralela <= 0:
            tasa_paralela = get_parallel_rate()
            if tasa_paralela is None or tasa_paralela == 0:
                await update.message.reply_text(
                    "Error al obtener el tipo de cambio paralelo. Especifica la tasa manualmente.\n"
                    "Ejemplo: /cambiar 100000 320"
                )
                return
        
        # Registrar intercambio (NO es gasto, es compra de divisa)
        amount_usdt, intercambio_id = add_intercambio(
            update.effective_user.id,
            amount_bs,
            tasa_paralela,
            descripcion
        )
        
        # Calcular saldo disponible
        saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(update.effective_user.id)
        
        message = (
            f"Intercambio registrado (ID: {intercambio_id})\n\n"
            f"Bolivares: {amount_bs:,.2f} Bs\n"
            f"USDT recibido: {amount_usdt:,.4f} USDT\n"
            f"Tasa usada: {tasa_paralela:,.2f} Bs/USDT\n"
        )
        
        if saldo_bs is not None:
            message += (
                f"\nSaldo disponible:\n"
                f"{saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)"
            )
        
        if descripcion:
            message += f"\n\nDescripcion: {descripcion}"
        
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa numeros validos.\n"
            "Ejemplo: /cambiar 100000\n"
            "Ejemplo: /cambiar 100000 320"
        )

async def ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /ingreso - Registra el ingreso mensual"""
    if not context.args:
        ingreso_actual = get_ingreso_mensual(update.effective_user.id)
        if ingreso_actual:
            saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(update.effective_user.id)
            message = (
                f"Ingreso mensual ({get_current_month_key()})\n\n"
                f"Ingreso: {ingreso_actual['bolivares']:,.2f} Bs\n"
                f"Equivalente: {ingreso_actual['usdt']:,.4f} USDT\n"
                f"Tasa usada: {ingreso_actual['tasa_paralela']:,.2f} Bs/USDT\n"
            )
            if saldo_bs is not None:
                message += (
                    f"\nSaldo disponible:\n"
                    f"{saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)"
                )
        else:
            message = (
                "No hay ingreso registrado para este mes.\n\n"
                "Uso: /ingreso <cantidad_bs> [tasa]\n"
                "Ejemplo: /ingreso 120000\n"
                "Ejemplo: /ingreso 120000 330\n\n"
                "Si no especificas la tasa, se usara la tasa paralela actual."
            )
        await update.message.reply_text(message)
        return
    
    try:
        amount_bs = float(context.args[0].replace(',', '.'))
        
        if amount_bs <= 0:
            await update.message.reply_text("El ingreso debe ser mayor a 0")
            return
        
        # Verificar si hay tasa manual
        tasa_paralela = None
        if len(context.args) > 1:
            try:
                tasa_paralela = float(context.args[1].replace(',', '.'))
            except ValueError:
                pass
        
        # Si no se especificó tasa, usar la de la API
        if tasa_paralela is None or tasa_paralela <= 0:
            tasa_paralela = get_parallel_rate() or get_dollar_rate()
            if tasa_paralela is None or tasa_paralela == 0:
                await update.message.reply_text(
                    "Error al obtener el tipo de cambio. Especifica la tasa manualmente.\n"
                    "Ejemplo: /ingreso 120000 330"
                )
                return
        
        amount_usdt = set_ingreso_mensual(update.effective_user.id, amount_bs, tasa_paralela)
        
        message = (
            f"Ingreso mensual registrado\n\n"
            f"Ingreso: {amount_bs:,.2f} Bs\n"
            f"Equivalente: {amount_usdt:,.4f} USDT\n"
            f"Tasa usada: {tasa_paralela:,.2f} Bs/USDT\n\n"
            f"El bot ahora llevara cuenta de tus gastos e intercambios contra este ingreso."
        )
        
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un numero valido.\n"
            "Ejemplo: /ingreso 120000\n"
            "Ejemplo: /ingreso 120000 330"
        )

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /ai - Pregunta a la IA"""
    if not gemini_enabled:
        await update.message.reply_text(
            "La IA no esta disponible. Verifica que GEMINI_API_KEY este configurada en el archivo .env"
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "Por favor, haz una pregunta despues del comando.\n"
            "Ejemplo: /ai Cuanto es 1000 bolivares en dolares?"
        )
        return
    
    question = " ".join(context.args)
    
    dollar_rate = None
    question_lower = question.lower()
    dollar_keywords = ['dolar', 'dólar', 'dollar', 'tasa', 'tipo de cambio', 'cambio', 'bs', 'bolivar', 'bolívar', 'usd', 'precio']
    if any(keyword in question_lower for keyword in dollar_keywords):
        dollar_rate = get_dollar_rate()
    
    thinking_msg = await update.message.reply_text("Pensando...")
    
    ai_response = await ask_gemini(question, dollar_rate, update.effective_user.id)
    
    await thinking_msg.delete()
    
    if ai_response:
        await update.message.reply_text(ai_response)
    else:
        await update.message.reply_text(
            "Error al consultar la IA. Intenta mas tarde."
        )

async def ask_gemini(prompt, dollar_rate=None, user_id=None):
    """Hace una pregunta a Gemini AI con acceso a los datos del usuario"""
    if not gemini_enabled or not gemini_model:
        return None
    
    try:
        prompt_lower = prompt.lower()
        is_dollar_question = any(word in prompt_lower for word in [
            'dolar', 'dólar', 'dollar', 'tasa', 'tipo de cambio', 'cambio', 
            'usd', 'precio del dolar', 'cotizacion', 'cotización'
        ]) or ('tasa' in prompt_lower and ('cual' in prompt_lower or 'cuál' in prompt_lower or 'que' in prompt_lower or 'qué' in prompt_lower or 'hay' in prompt_lower or 'hoy' in prompt_lower))
        
        is_expense_question = any(word in prompt_lower for word in [
            'gasto', 'gasté', 'gastado', 'gastos', 'resumen', 'resumen del mes', 'resumen mensual',
            'cuanto he gastado', 'cuánto he gastado', 'cuanto gasté', 'cuánto gasté',
            'total', 'balance', 'saldo', 'llevo gastado', 'he gastado', 'mis gastos'
        ])
        
        if is_dollar_question and dollar_rate is None:
            dollar_rate = get_dollar_rate()
        
        expenses_info = ""
        if is_expense_question and user_id:
            # Ingreso mensual
            ingreso = get_ingreso_mensual(user_id)
            
            # Gastos
            total_bs, total_usd, gastos = get_month_summary(user_id)
            current_rate = get_dollar_rate() or dollar_rate
            
            # Intercambios (compra de USDT, NO son gastos)
            intercambios = get_intercambios_month(user_id)
            total_bs_intercambios = sum(i["bolivares"] for i in intercambios)
            total_usdt_intercambios = sum(i["usdt"] for i in intercambios)
            
            # Saldo disponible
            saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(user_id)
            
            expenses_info = "\n\nINFORMACIÓN FINANCIERA DEL USUARIO (mes actual):\n"
            
            if ingreso:
                expenses_info += f"- Ingreso mensual: {ingreso['bolivares']:,.2f} Bs (${ingreso['usdt']:,.4f} USDT)\n"
            
            if total_bs is not None:
                expenses_info += f"- Total gastado: {total_bs:,.2f} Bs (${total_usd:,.2f} USD)\n"
                expenses_info += f"- Número de gastos: {len(gastos)}\n"
            
            if len(intercambios) > 0:
                expenses_info += f"- Intercambios (Bs->USDT): {total_bs_intercambios:,.2f} Bs -> {total_usdt_intercambios:,.4f} USDT\n"
                expenses_info += f"- Número de intercambios: {len(intercambios)}\n"
            
            if saldo_bs is not None:
                expenses_info += f"- Saldo disponible: {saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)\n"
            
            if current_rate:
                expenses_info += f"- Tipo de cambio oficial actual: {current_rate:,.2f} Bs/$\n"
            
            if len(gastos) > 0:
                expenses_info += f"\nÚltimos gastos:\n"
                for i, gasto in enumerate(gastos[-5:], 1):
                    expenses_info += f"{i}. {gasto['fecha']}: {gasto['bolivares']:,.2f} Bs (${gasto['dolares']:,.2f} USD)\n"
            
            if len(intercambios) > 0:
                expenses_info += f"\nÚltimos intercambios:\n"
                for i, intercambio in enumerate(intercambios[-5:], 1):
                    expenses_info += f"{i}. {intercambio['fecha']}: {intercambio['bolivares']:,.2f} Bs -> {intercambio['usdt']:,.4f} USDT (tasa: {intercambio['tasa_paralela']:,.2f})\n"
        
        context_info = ""
        if dollar_rate and is_dollar_question:
            context_info = f"\n\nINFORMACIÓN ACTUAL DEL DÓLAR:\n- Tipo de cambio oficial: {dollar_rate:,.2f} bolívares = 1 dólar USD\n- Esta información es actualizada en tiempo real.\n"
        
        context_prompt = (
            f"Eres un asistente profesional para un bot de Telegram que ayuda a llevar control de gastos en Venezuela. "
            f"El usuario pregunta: {prompt}\n\n"
            f"{context_info}"
            f"{expenses_info}"
            f"INSTRUCCIONES IMPORTANTES:\n"
            f"- Responde de forma SERIA, PROFESIONAL y DIRECTA\n"
            f"- NO uses lenguaje informal, slang, o expresiones coloquiales\n"
            f"- NO uses emojis en absoluto. Prohibido usar cualquier emoji.\n"
            f"- NO uses frases como 'mi pana', 'hermano', 'pa que', etc.\n"
            f"- Sé CONCISO y CLARO en tus respuestas\n"
            f"- Si la pregunta es sobre el dólar o tipo de cambio, usa la información actual proporcionada de forma precisa\n"
            f"- Si la pregunta es sobre los gastos del usuario, usa EXACTAMENTE los números de la información proporcionada arriba\n"
            f"- IMPORTANTE: Los intercambios (compra de USDT) NO son gastos, son compra de divisa. Diferencia entre gastos e intercambios.\n"
            f"- Si pregunta por resumen, total, o cuánto ha gastado, proporciona los números exactos sin rodeos\n"
            f"- Si pregunta sobre saldo disponible, usa la información de ingreso menos gastos menos intercambios\n"
            f"- Mantén un tono profesional y objetivo en todas tus respuestas\n"
            f"- NUNCA uses emojis, símbolos decorativos, o caracteres especiales innecesarios"
        )
        response = gemini_model.generate_content(context_prompt)
        
        if hasattr(response, 'text') and response.text:
            return response.text
        elif hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                if text_parts:
                    return ' '.join(text_parts)
        
        return None
    except Exception as e:
        print(f"Error al consultar Gemini: {e}")
        import traceback
        traceback.print_exc()
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de texto que no son comandos"""
    text = update.message.text.lower()
    original_text = update.message.text
    import re
    
    # Detectar compra/intercambio de USDT
    # Formatos: "compre 20 usdt a 320", "compre 20 usdt", "cambie 6400", "cambie 6400 a 320"
    if any(word in text for word in ["compre", "compré", "comprar", "cambie", "cambié", "cambiar"]):
        numbers = re.findall(r'\d+[.,]?\d*', text)
        if len(numbers) >= 1:
            try:
                # Si menciona USDT explícitamente
                if "usdt" in text:
                    # Formato: "compre 20 usdt a 320" o "compre 20 usdt"
                    amount_usdt = float(numbers[0].replace(',', '.'))
                    tasa_paralela = None
                    
                    if len(numbers) >= 2:
                        # Hay tasa especificada
                        tasa_paralela = float(numbers[1].replace(',', '.'))
                        amount_bs = amount_usdt * tasa_paralela
                    else:
                        # No hay tasa, usar la de la API
                        tasa_paralela = get_parallel_rate()
                        if tasa_paralela is None or tasa_paralela == 0:
                            await update.message.reply_text(
                                "Error al obtener tasa. Especifica la tasa.\n"
                                "Ejemplo: compre 20 usdt a 320"
                            )
                            return
                        amount_bs = amount_usdt * tasa_paralela
                    
                    # Registrar intercambio
                    amount_usdt_calc, intercambio_id = add_intercambio(
                        update.effective_user.id,
                        amount_bs,
                        tasa_paralela,
                        f"Compra de {amount_usdt} USDT"
                    )
                    
                    saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(update.effective_user.id)
                    
                    message = (
                        f"Intercambio registrado (ID: {intercambio_id})\n\n"
                        f"USDT comprado: {amount_usdt:,.4f} USDT\n"
                        f"Bolivares: {amount_bs:,.2f} Bs\n"
                        f"Tasa usada: {tasa_paralela:,.2f} Bs/USDT\n"
                    )
                    
                    if saldo_bs is not None:
                        message += (
                            f"\nSaldo disponible:\n"
                            f"{saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)"
                        )
                    
                    await update.message.reply_text(message)
                    return
                
                # Si dice "cambie 6400" o "cambie 6400 a 320" (sin mencionar USDT, asumimos que es Bs a USDT)
                elif any(word in text for word in ["cambie", "cambié", "cambiar"]) and not "gast" in text:
                    amount_bs = float(numbers[0].replace(',', '.'))
                    tasa_paralela = None
                    
                    if len(numbers) >= 2:
                        # Hay tasa especificada
                        tasa_paralela = float(numbers[1].replace(',', '.'))
                    else:
                        # No hay tasa, usar la de la API
                        tasa_paralela = get_parallel_rate()
                        if tasa_paralela is None or tasa_paralela == 0:
                            await update.message.reply_text(
                                "Error al obtener tasa. Especifica la tasa.\n"
                                "Ejemplo: cambie 6400 320"
                            )
                            return
                    
                    # Registrar intercambio
                    amount_usdt, intercambio_id = add_intercambio(
                        update.effective_user.id,
                        amount_bs,
                        tasa_paralela,
                        "Intercambio Bs a USDT"
                    )
                    
                    saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(update.effective_user.id)
                    
                    message = (
                        f"Intercambio registrado (ID: {intercambio_id})\n\n"
                        f"Bolivares: {amount_bs:,.2f} Bs\n"
                        f"USDT recibido: {amount_usdt:,.4f} USDT\n"
                        f"Tasa usada: {tasa_paralela:,.2f} Bs/USDT\n"
                    )
                    
                    if saldo_bs is not None:
                        message += (
                            f"\nSaldo disponible:\n"
                            f"{saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)"
                        )
                    
                    await update.message.reply_text(message)
                    return
                    
            except (ValueError, IndexError):
                pass
    
    # Detectar gasto(s) - puede haber múltiples gastos en un mensaje
    if "gast" in text or "gasté" in text or "gaste" in text:
        # Buscar todos los números en el mensaje
        numbers = re.findall(r'\d+[.,]?\d*', text)
        if numbers:
            try:
                dollar_rate = get_dollar_rate()
                if not dollar_rate or dollar_rate == 0:
                    await update.message.reply_text(
                        "Error al obtener el tipo de cambio. Intenta mas tarde."
                    )
                    return
                
                # Detectar múltiples gastos
                # Patrón: número seguido de "bs" o contexto de gasto
                gastos_detectados = []
                
                # Buscar patrones como "50bs", "100 en", "400 en", etc.
                # Dividir por comas o "y" para detectar múltiples gastos
                # También considerar números seguidos de "bs" o "en"
                partes = re.split(r'[,y]\s*', text)
                
                # Si no se dividió bien, intentar detectar números seguidos de "bs" o "en"
                if len(partes) == 1 or len(numbers) > len(partes):
                    # Buscar patrones: número + "bs" o número + "en"
                    patrones = re.findall(r'(\d+[.,]?\d*)\s*(?:bs|en)', text, re.IGNORECASE)
                    if patrones:
                        # Reconstruir partes basadas en los patrones encontrados
                        partes = []
                        for patron in patrones:
                            # Buscar el contexto alrededor de cada número
                            idx = text.lower().find(patron[0])
                            if idx != -1:
                                # Extraer desde el número hasta la siguiente coma o fin
                                resto = text[idx:]
                                if ',' in resto:
                                    parte = resto[:resto.find(',')]
                                elif ' y ' in resto:
                                    parte = resto[:resto.find(' y ')]
                                else:
                                    parte = resto
                                partes.append(parte.strip())
                
                for parte in partes:
                    if any(word in parte for word in ["gast", "bs", "en"]):
                        # Buscar número en esta parte
                        nums_en_parte = re.findall(r'\d+[.,]?\d*', parte)
                        if nums_en_parte:
                            try:
                                amount = float(nums_en_parte[0].replace(',', '.'))
                                if amount > 0:
                                    # Intentar detectar categoría o descripción
                                    categoria = "otros"
                                    descripcion = ""
                                    
                                    # Buscar categorías conocidas
                                    for cat in CATEGORIAS:
                                        if cat in parte:
                                            categoria = cat
                                            break
                                    
                                    # Extraer descripción (texto después del número)
                                    palabras = parte.split()
                                    if len(palabras) > 1:
                                        # Buscar texto descriptivo después de "en"
                                        if "en" in parte:
                                            idx_en = parte.find("en")
                                            descripcion = parte[idx_en+2:].strip()
                                    
                                    gastos_detectados.append({
                                        "amount": amount,
                                        "categoria": categoria,
                                        "descripcion": descripcion
                                    })
                            except ValueError:
                                continue
                
                # Si no se detectaron múltiples, usar el primer número como antes
                if not gastos_detectados and numbers:
                    amount_bs = float(numbers[0].replace(',', '.'))
                    if amount_bs > 0:
                        gastos_detectados.append({
                            "amount": amount_bs,
                            "categoria": "otros",
                            "descripcion": ""
                        })
                
                # Registrar todos los gastos detectados
                if gastos_detectados:
                    total_bs = 0
                    total_usd = 0
                    mensajes_gastos = []
                    
                    for gasto_info in gastos_detectados:
                        amount_bs = gasto_info["amount"]
                        categoria = gasto_info["categoria"]
                        descripcion = gasto_info["descripcion"]
                        
                        amount_usd, gasto_id = add_gasto(
                            update.effective_user.id,
                            amount_bs,
                            dollar_rate,
                            categoria,
                            descripcion
                        )
                        
                        total_bs += amount_bs
                        total_usd += amount_usd
                        
                        msg_gasto = f"{amount_bs:,.2f} Bs (${amount_usd:,.2f} USD)"
                        if categoria != "otros":
                            msg_gasto += f" - {categoria}"
                        if descripcion:
                            msg_gasto += f" - {descripcion}"
                        mensajes_gastos.append(msg_gasto)
                    
                    # Mensaje de confirmación
                    if len(gastos_detectados) == 1:
                        message = (
                            f"Gasto registrado:\n\n"
                            f"{mensajes_gastos[0]}\n"
                            f"Tipo de cambio: {dollar_rate:,.2f} Bs/$\n"
                        )
                    else:
                        message = (
                            f"{len(gastos_detectados)} gastos registrados:\n\n"
                        )
                        for i, msg in enumerate(mensajes_gastos, 1):
                            message += f"{i}. {msg}\n"
                        message += (
                            f"\nTotal: {total_bs:,.2f} Bs (${total_usd:,.2f} USD)\n"
                            f"Tipo de cambio: {dollar_rate:,.2f} Bs/$\n"
                        )
                    
                    saldo_bs, saldo_usdt, _, _ = get_saldo_disponible(update.effective_user.id)
                    if saldo_bs is not None:
                        message += (
                            f"\nSaldo disponible:\n"
                            f"{saldo_bs:,.2f} Bs (${saldo_usdt:,.2f} USD equivalente)"
                        )
                    
                    await update.message.reply_text(message)
                    return
            
            except ValueError:
                pass
    
    # Detectar preguntas sobre gastos de hoy específicamente
    hoy_keywords = ['hoy', 'cuanto gaste hoy', 'cuánto gasté hoy', 'gastos de hoy', 'gaste hoy']
    is_hoy_question = any(keyword in text for keyword in hoy_keywords) and any(word in text for word in ['gast', 'gasté', 'gaste'])
    
    if is_hoy_question:
        hoy = datetime.now().date()
        gastos = get_gastos_by_date(update.effective_user.id, hoy)
        
        if not gastos:
            await update.message.reply_text("No hay gastos registrados hoy.")
            return
        
        total_bs = sum(g["bolivares"] for g in gastos)
        total_usd = sum(g["dolares"] for g in gastos)
        
        message = (
            f"Gastos de hoy ({hoy.strftime('%Y-%m-%d')})\n\n"
            f"Total: {total_bs:,.2f} Bs (${total_usd:,.2f} USD)\n"
            f"Numero de gastos: {len(gastos)}\n\n"
        )
        
        for g in gastos:
            hora = g["fecha"].split()[1] if len(g["fecha"].split()) > 1 else ""
            message += (
                f"{hora} - {g['bolivares']:,.2f} Bs (${g['dolares']:,.2f} USD)\n"
            )
            if g.get("categoria") and g.get("categoria") != "otros":
                message += f"Categoria: {g.get('categoria')}\n"
            if g.get("descripcion"):
                message += f"Descripcion: {g['descripcion']}\n"
            message += "\n"
        
        await update.message.reply_text(message)
        return
    
    if gemini_enabled:
        dollar_keywords = ['dolar', 'dólar', 'dollar', 'tasa', 'tipo de cambio', 'cambio', 'usd', 'precio del dolar', 'cotizacion', 'cotización']
        is_dollar_question = any(keyword in text for keyword in dollar_keywords) or ('tasa' in text and ('cual' in text or 'cuál' in text or 'que' in text or 'qué' in text or 'hay' in text or 'hoy' in text))
        
        dollar_rate = None
        if is_dollar_question:
            dollar_rate = get_dollar_rate()
            print(f"Pregunta detectada sobre dólar: '{original_text}'. Tipo de cambio: {dollar_rate}")
        
        thinking_msg = await update.message.reply_text("Pensando...")
        
        try:
            ai_response = await ask_gemini(original_text, dollar_rate, update.effective_user.id)
            
            await thinking_msg.delete()
            
            if ai_response:
                await update.message.reply_text(ai_response)
                return
            else:
                if is_dollar_question and dollar_rate:
                    await update.message.reply_text(
                        f"Tipo de cambio del dolar oficial:\n\n"
                        f"{dollar_rate:,.2f} Bs = 1 USD\n\n"
                        f"Esta es la tasa oficial actualizada."
                    )
                    return
        except Exception as e:
            await thinking_msg.delete()
            print(f"Error en handle_message: {e}")
            import traceback
            traceback.print_exc()
            if is_dollar_question:
                dollar_rate = get_dollar_rate()
                if dollar_rate:
                    await update.message.reply_text(
                        f"Tipo de cambio del dolar oficial:\n\n"
                        f"{dollar_rate:,.2f} Bs = 1 USD"
                    )
                    return
    
    await update.message.reply_text(
        "Para registrar un gasto, escribe:\n"
        "/gasto <cantidad>\n\n"
        "O escribe: 'gasté 22000'\n\n"
        "Tambien puedes hacer preguntas sobre el dolar, tipo de cambio, o cualquier otra cosa.\n\n"
        "Otros comandos:\n"
        "/resumen - Ver resumen del mes\n"
        "/dolar - Ver tipo de cambio\n"
        "/ai <pregunta> - Pregunta a la IA\n"
        "Usa /start para ver todos los comandos disponibles."
    )

# Configuración del bot
telegram_token = os.getenv('TELEGRAM_TOKEN')
if not telegram_token:
    print("Error: TELEGRAM_TOKEN no encontrada en .env")
    print(f"Directorio actual: {os.getcwd()}")
    print(f"Ruta del script: {script_dir}")
    print(f"Buscando .env en: {env_path}")
    print(f"Existe .env: {os.path.exists(env_path)}")
    if os.path.exists(env_path):
        print("Contenido de .env:")
        with open(env_path, 'r') as f:
            print(f.read())
    exit(1)

app = ApplicationBuilder().token(telegram_token).build()

# Agregar handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("gasto", gasto))
app.add_handler(CommandHandler("resumen", resumen))
app.add_handler(CommandHandler("dolar", dolar))
app.add_handler(CommandHandler("ai", ai_command))
app.add_handler(CommandHandler("listar", listar))
app.add_handler(CommandHandler("eliminar", eliminar))
app.add_handler(CommandHandler("editar", editar))
app.add_handler(CommandHandler("estadisticas", estadisticas))
app.add_handler(CommandHandler("presupuesto", presupuesto))
app.add_handler(CommandHandler("comparar", comparar))
app.add_handler(CommandHandler("buscar", buscar))
app.add_handler(CommandHandler("gastos_hoy", gastos_hoy))
app.add_handler(CommandHandler("exportar", exportar))
app.add_handler(CommandHandler("binance_rate", binance_rate))
app.add_handler(CommandHandler("cambiar", cambiar))
app.add_handler(CommandHandler("ingreso", ingreso))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    print("Bot iniciado...")
    app.run_polling()
