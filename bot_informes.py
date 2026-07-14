import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler, 
    filters, ContextTypes
)
from fpdf import FPDF
import uuid

# --- ESTADOS ---
(CLIENTE, CONTACTO, TELEFONO, PLANTA, CANTIDAD, NOMBRE_EQUIPO, ACTIVIDAD_DESC, 
 FOTO_ANTES, FOTO_DESPUES, CONCLUSIONES, MENU_ACTIVIDAD) = range(11)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename: str) -> str:
    return os.path.join(BASE_DIR, filename)


# --- CLASE PDF ---
class PDF_Informe(FPDF):
    def header(self):
        self.set_draw_color(0, 0, 0)
        self.rect(10, 10, 190, 20)
        marca_path = asset_path('marca.png')
        if os.path.exists(marca_path):
            self.image(marca_path, 12, 12, 45, 16)
        self.line(60, 10, 60, 30)
        self.line(160, 10, 160, 30)
        self.set_font('Arial', 'B', 12)
        self.set_xy(60, 10)
        self.cell(100, 20, 'INFORME SERVICIO TÉCNICO', 0, 0, 'C')
        self.set_font('Arial', 'B', 8)
        self.set_xy(160, 10)
        self.cell(40, 6.66, 'CÓDIGO: ST-DR-01', 1, 2, 'L')
        self.set_x(160)
        self.cell(40, 6.66, 'EMISIÓN: 02/06/21', 1, 2, 'L')
        self.set_x(160)
        self.cell(40, 6.66, 'VERSIÓN: 01', 1, 0, 'L')
        self.ln(25)

    def footer(self):
        self.set_y(-30)
        self.set_text_color(150, 150, 150)
        self.set_font('Arial', '', 6)
        texto_legal = (
            "NOTA: Al imprimir el presente documento, se convierte en COPIA NO CONTROLADA, "
            "a menos que la Gerencia lo identifique como COPIA CONTROLADA U ORIGINAL. "
            "Cualquier reproducción total o parcial será sometida a las autoridades legales."
        )
        self.multi_cell(0, 3, texto_legal)
        self.set_text_color(0, 0, 0)
        self.set_y(-15)
        self.set_font('Arial', '', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- FUNCIONES DE CONVERSACIÓN ---
async def start(update, context):
    context.user_data.clear()
    context.user_data.update({'equipos': []})
    await update.message.reply_text("Iniciando nuevo informe. Nombre del Cliente:")
    return CLIENTE

async def recibir_cliente(update, context):
    context.user_data['cliente'] = update.message.text
    await update.message.reply_text("Nombre del contacto:")
    return CONTACTO

async def recibir_contacto(update, context):
    context.user_data['contacto'] = update.message.text
    await update.message.reply_text("Teléfono:")
    return TELEFONO

async def recibir_telefono(update, context):
    context.user_data['telefono'] = update.message.text
    await update.message.reply_text("Nombre de la planta:")
    return PLANTA

async def recibir_planta(update, context):
    context.user_data['planta'] = update.message.text
    await update.message.reply_text("¿Cuántos equipos?")
    return CANTIDAD

async def recibir_cantidad(update, context):
    try:
        cantidad = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Ingrese un número válido de equipos.")
        return CANTIDAD

    context.user_data['cantidad_equipos'] = cantidad
    context.user_data['equipos_cargados'] = 0
    context.user_data['equipo_temporal'] = {'nombre': '', 'actividades': []}
    await update.message.reply_text("Nombre del equipo:")
    return NOMBRE_EQUIPO

async def recibir_nombre(update, context):
    context.user_data['equipo_temporal']['nombre'] = update.message.text
    context.user_data['actividad_temporal'] = {}
    await update.message.reply_text("Descripción de la actividad:")
    return ACTIVIDAD_DESC

async def recibir_actividad_desc(update, context):
    context.user_data['actividad_temporal']['descripcion'] = update.message.text
    await update.message.reply_text("Foto ANTES:")
    return FOTO_ANTES
async def recibir_foto_antes(update, context):
    file = await update.message.photo[-1].get_file()
    # Nombre único con uuid para evitar sobrescrituras
    unique_id = str(uuid.uuid4())
    path = os.path.join(BASE_DIR, f"antes_{unique_id}.jpg")
    await file.download_to_drive(path)
    context.user_data['actividad_temporal']['foto_antes'] = path
    await update.message.reply_text("Foto DESPUÉS:")
    return FOTO_DESPUES

async def recibir_foto_despues(update, context):
    file = await update.message.photo[-1].get_file()
    unique_id = str(uuid.uuid4())
    path = os.path.join(BASE_DIR, f"despues_{unique_id}.jpg")
    await file.download_to_drive(path)
    context.user_data['actividad_temporal']['foto_despues'] = path
    await update.message.reply_text("Conclusiones:")
    return CONCLUSIONES

async def recibir_conclusiones(update, context):
    context.user_data['actividad_temporal']['conclusiones'] = update.message.text
    context.user_data['equipo_temporal']['actividades'].append(context.user_data['actividad_temporal'].copy())
    await update.message.reply_text("¿Otra actividad? (Si/No)")
    return MENU_ACTIVIDAD

async def procesar_menu_actividad(update, context):
    if "si" in update.message.text.lower():
        await update.message.reply_text("Descripción de la actividad:")
        return ACTIVIDAD_DESC

    context.user_data['equipos'].append(context.user_data['equipo_temporal'].copy())
    context.user_data['equipos_cargados'] = context.user_data.get('equipos_cargados', 0) + 1

    cantidad = context.user_data.get('cantidad_equipos', 0)
    if context.user_data.get('equipos_cargados', 0) < cantidad:
        context.user_data['equipo_temporal'] = {'nombre': '', 'actividades': []}
        await update.message.reply_text("Nombre del siguiente equipo:")
        return NOMBRE_EQUIPO

    return await generar_pdf(update, context)

async def generar_pdf(update, context):
    nombre_pdf = f"Informe_{update.message.from_user.id}.pdf"
    pdf = PDF_Informe()
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    # 1. PORTADA
    pdf.add_page()
    pdf.set_font("Arial", 'B', 24)
    pdf.ln(80)
    pdf.cell(0, 20, "INFORME DE SERVICIO", 0, 1, 'R')
    pdf.cell(0, 20, f"PLANTA {context.user_data.get('planta')}", 0, 1, 'R')
    pdf.set_font("Arial", '', 14)
    pdf.cell(0, 10, f"Cliente: {context.user_data.get('cliente')}", 0, 1, 'L')
    pdf.cell(0, 10, f"Contacto: {context.user_data.get('contacto')}", 0, 1, 'L')
    pdf.cell(0, 10, f"Teléfono: {context.user_data.get('telefono')}", 0, 1, 'L')
    pdf.cell(0, 10, f"Fecha: {fecha_actual}", 0, 1, 'L')
    pdf.ln(50)
    pdf.set_font("Arial", '', 6)
    texto = (
        "Responsabilidades y Aclaraciones:\n\n"
        "Todas las piezas y materiales que ingresan al Departamento de Servicio técnico de ETS Ingeniería para su respectiva revisión y/o diagnóstico, se someten a pruebas técnicas según los parámetros indicados por nuestros fabricantes, garantizando un análisis de desempeño según sea el caso y la disponibilidad de repuestos originales. La información contenida en este informe es confidencial y está destinada únicamente para el uso del cliente mencionado. Cualquier divulgación, copia o distribución no autorizada de este informe está estrictamente prohibida.\n\n"
        "Nuestra mano de obra está garantizada. Sin embargo, NO reemplaza todas las otras garantías y/o garantías expresas o implícitas por parte del fabricante. ETS se libra de cualquier garantía de comerciabilidad o idoneidad para este propósito y de todas las demás obligaciones por responsabilidades de desempeño de los equipos, incluida, sus limitaciones, y responsabilidades por daños ya sean directos o indirectos y consecuenciales de otro tipo.\n\n"
        "ETS Ingeniería realiza sus reparaciones con repuestos originales de las marcas Rexroth, Hydac, Aventics y Metal Work y acuerda garantía en reparaciones por un período de seis (6) meses a partir de la fecha de entrega de cualquier trabajo de reparación, realizado en relación con la orden de trabajo indicada a continuación, las garantías de ETS Ingeniería no se aplican a los defectos en dichos equipos, tales como resultado de: abuso, accidente, alteración, negligencia, desgaste, mantenimiento inadecuado y uso no razonable de dicho equipo o un inadecuado desmontaje."
    )
    pdf.multi_cell(0, 3, texto)
    # 2. TABLA DE CONTENIDO
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "TABLA DE CONTENIDO", 0, 1, 'C')
    pdf.ln(10)

    lista_indices = []
    pagina_equipo = 3
    for equipo in context.user_data['equipos']:
        lista_indices.append((equipo['nombre'], pagina_equipo))
        pagina_equipo += 1

    for nombre, num_pag in lista_indices:
        pdf.set_font("Arial", '', 12)
        pdf.cell(150, 10, nombre, 0, 0, 'L')
        pdf.cell(40, 10, f"Pág. {num_pag}", 0, 1, 'R')

    # 3. CONTENIDO
    for equipo in context.user_data['equipos']:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(190, 10, f"EQUIPO: {equipo['nombre'].upper()}", 1, 1, 'L', fill=True)
        
        for act in equipo['actividades']:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(190, 8, "ACTIVIDAD", 1, 1, 'C', fill=True)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(190, 8, act['descripcion'])
            
            y = pdf.get_y()
            pdf.cell(95, 60, "ANTES", 1, 0, 'C')
            pdf.cell(95, 60, "DESPUÉS", 1, 1, 'C')
            if os.path.exists(act['foto_antes']):
                pdf.image(act['foto_antes'], 15, y+7, 80, 30)
            if os.path.exists(act['foto_despues']):
                pdf.image(act['foto_despues'], 110, y+7, 85, 30)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(190, 8, "CONCLUSIONES", 1, 1, 'L', fill=True)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(190, 8, act['conclusiones'])
            pdf.ln(5)

    # 4. CONCLUSIONES FINALES
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "CONCLUSIONES FINALES", 0, 1, 'L')
    pdf.ln(20)
    pdf.set_x(70)
    pdf.cell(70, 0, "", "T", 1, "C")
    pdf.set_x(70)
    pdf.cell(70, 8, "Firma del Técnico", 0, 1, "C")
    firma_path = asset_path('firma.png')
    if os.path.exists(firma_path):
        pdf.image(firma_path, 80, pdf.get_y() - 25, 50)

    output_path = asset_path(nombre_pdf)
    pdf.output(output_path)

    with open(output_path, 'rb') as f:
        await update.message.reply_document(document=f)
    if os.path.exists(output_path):
        os.remove(output_path)
    context.user_data.clear()
    return ConversationHandler.END
async def cancelar(update, context):
    await update.message.reply_text("Cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

def main():
    TOKEN = "8745648230:AAH-pwNzsx_-YBulKTYZaHSESZ4LxSpLTUQ"
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('(?i)^iniciar$'), start)],
        states={
            CLIENTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cliente)],
            CONTACTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_contacto)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)],
            PLANTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_planta)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cantidad)],
            NOMBRE_EQUIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
            ACTIVIDAD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_actividad_desc)],
            FOTO_ANTES: [MessageHandler(filters.PHOTO, recibir_foto_antes)],
            FOTO_DESPUES: [MessageHandler(filters.PHOTO, recibir_foto_despues)],
            CONCLUSIONES: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_conclusiones)],
            MENU_ACTIVIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_menu_actividad)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )
    app.add_handler(conv)
    print("Bot en marcha...")
    app.run_polling()

if __name__ == '__main__':
    main()