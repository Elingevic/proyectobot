#!/bin/bash

# Script de despliegue para el bot de Telegram en VPS
# Este script instala dependencias y configura el bot para ejecutarse

echo "🚀 Iniciando despliegue del bot de Telegram..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Instalando..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Verificar pip3
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 no está instalado. Instalando..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Crear directorio para el bot (si no existe)
BOT_DIR="/opt/telegram-bot"
if [ ! -d "$BOT_DIR" ]; then
    echo "📁 Creando directorio $BOT_DIR..."
    sudo mkdir -p $BOT_DIR
    sudo chown $USER:$USER $BOT_DIR
fi

# Navegar al directorio
cd $BOT_DIR

# Clonar o actualizar el repositorio
if [ -d ".git" ]; then
    echo "🔄 Actualizando código desde Git..."
    git pull origin main
else
    echo "📥 Clonando repositorio..."
    # Reemplazar con tu URL de Git
    git clone https://github.com/Elingevic/proyectobot.git .
fi

# Crear entorno virtual (para evitar problemas con externally-managed-environment)
echo "🐍 Creando entorno virtual..."
python3 -m venv venv

# Instalar dependencias en el entorno virtual
echo "📦 Instalando dependencias de Python..."
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️  Archivo .env no encontrado. Creando plantilla..."
    cat > .env << EOF
TELEGRAM_TOKEN=tu_token_aqui
GEMINI_API_KEY=tu_api_key_aqui
EOF
    echo "📝 Por favor, edita el archivo .env con tus credenciales:"
    echo "   nano $BOT_DIR/.env"
fi

# Crear servicio systemd
echo "⚙️  Configurando servicio systemd..."
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null << EOF
[Unit]
Description=Telegram Bot de Control de Gastos
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=$BOT_DIR/venv/bin/python3 $BOT_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recargar systemd
sudo systemctl daemon-reload

echo "✅ Despliegue completado!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales:"
echo "   nano $BOT_DIR/.env"
echo ""
echo "2. Inicia el servicio:"
echo "   sudo systemctl start telegram-bot"
echo ""
echo "3. Habilita el servicio para que inicie automáticamente:"
echo "   sudo systemctl enable telegram-bot"
echo ""
echo "4. Verifica el estado:"
echo "   sudo systemctl status telegram-bot"
echo ""
echo "5. Ver logs:"
echo "   sudo journalctl -u telegram-bot -f"

