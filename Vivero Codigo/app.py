import streamlit as st
import pandas as pd
from fpdf import FPDF
import re
import os
import hashlib
import datetime

# Credenciales predeterminadas para el login
USERNAME = "admin"
PASSWORD = "admin123"

# Roles disponibles
ROLES = ["admin", "vendedor", "bodega"]

# Ruta para los archivos CSV de inventarios
inventory_files = {
    "plantas": "vivero_inventory_plants.csv",
    "herramientas": "vivero_inventory_tools.csv",
    "productos": "vivero_inventory_products.csv",
    "maceteros": "vivero_inventory_pots.csv"
}

# Archivo para guardar los usuarios
USER_FILE = "usuarios.csv"

# Archivo para guardar las ventas
SALES_FILE = "ventas.csv"

# --------------------------------------------------------------------------------
# Función para cargar los usuarios desde el archivo CSV
# --------------------------------------------------------------------------------
def load_users():
    if os.path.exists(USER_FILE):
        users = pd.read_csv(USER_FILE)
    else:
        users = pd.DataFrame(columns=["username", "password", "role"])
        hashed_password = hashlib.sha256(PASSWORD.encode()).hexdigest()
        new_user = pd.DataFrame([[USERNAME, hashed_password, "admin"]], columns=["username", "password", "role"])
        users = pd.concat([users, new_user], ignore_index=True)
        save_users(users)
    return users

# --------------------------------------------------------------------------------
# Función para guardar los usuarios en el archivo CSV
# --------------------------------------------------------------------------------
def save_users(users):
    users.to_csv(USER_FILE, index=False)

# --------------------------------------------------------------------------------
# Función para agregar un nuevo usuario
# --------------------------------------------------------------------------------
def add_user():
    if st.session_state.role != "admin":
        st.error("No tienes permisos para agregar nuevos usuarios.")
        return

    st.subheader("Crear Nuevo Usuario")
    new_username = st.text_input("Nombre de usuario")
    new_password = st.text_input("Contraseña", type="password")
    confirm_password = st.text_input("Confirmar Contraseña", type="password")
    role = st.selectbox("Rol", ROLES)

    if new_password != confirm_password:
        st.error("Las contraseñas no coinciden.")
        return

    if st.button("Crear Usuario"):
        users = load_users()
        if new_username in users["username"].values:
            st.error("El nombre de usuario ya existe.")
        else:
            hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
            new_user = pd.DataFrame([[new_username, hashed_password, role]], columns=["username", "password", "role"])
            users = pd.concat([users, new_user], ignore_index=True)
            save_users(users)
            st.success(f"Usuario {new_username} creado con éxito.")

# --------------------------------------------------------------------------------
# Función para cargar el inventario de cada categoría con semáforo
# --------------------------------------------------------------------------------
def load_inventory_with_colors(category):
    file_path = inventory_files[category]
    if os.path.exists(file_path):
        inventory = pd.read_csv(file_path)
    else:
        if category == "plantas":
            columns = ["ID", "Nombre", "Cantidad", "Precio Unitario", "Descripción"]
        else:
            columns = ["ID", "Nombre", "Cantidad", "Descripción"]
        inventory = pd.DataFrame(columns=columns)

    if "ID" not in inventory.columns:
        inventory["ID"] = None

    # Crear columna 'Estado' para el semáforo
    inventory["Estado"] = inventory["Cantidad"].apply(lambda x: "🔴 Bajo" if x <= 10 else "🟢 Suficiente")
    return inventory

# --------------------------------------------------------------------------------
# Función para mostrar el inventario con semáforo de colores
# --------------------------------------------------------------------------------
def display_inventory_with_colors(inventory):
    if inventory.empty:
        st.warning("El inventario está vacío.")
        return

    # Aplicar estilo condicional para la cantidad
    def highlight_row(row):
        color = "background-color: #ffcccc;" if row["Cantidad"] <= 10 else "background-color: #ccffcc;"
        return [color] * len(row)

    styled_inventory = inventory.style.apply(highlight_row, axis=1)
    st.write("Inventario:")
    st.dataframe(styled_inventory, use_container_width=True)

# --------------------------------------------------------------------------------
# Función para guardar el inventario de cada categoría
# --------------------------------------------------------------------------------
def save_inventory(inventory, category):
    file_path = inventory_files[category]
    inventory.to_csv(file_path, index=False)

# --------------------------------------------------------------------------------
# Función para agregar una nueva entrada
# --------------------------------------------------------------------------------
def add_item(inventory, category):
    code = st.text_input("Código del artículo (ID)")
    name = st.text_input("Nombre del artículo")
    quantity = st.number_input("Cantidad Disponible", min_value=0, step=1)
    description = st.text_area("Descripción del artículo")
    
    if category == "plantas":
        unit_price = st.number_input("Precio Unitario ($)", min_value=0.0, step=0.1)
        new_item = {
            "ID": code,
            "Nombre": name,
            "Cantidad": quantity,
            "Precio Unitario": unit_price,
            "Descripción": description
        }
    else:
        new_item = {
            "ID": code,
            "Nombre": name,
            "Cantidad": quantity,
            "Descripción": description
        }
    
    if st.button(f"Agregar {category[:-1].capitalize()}"):
        if code and name and quantity >= 0:
            new_item_df = pd.DataFrame([new_item])
            new_item_df = new_item_df.reindex(columns=inventory.columns, fill_value=None)
            inventory = pd.concat([inventory, new_item_df], ignore_index=True)
            save_inventory(inventory, category)
            st.success(f"El {category[:-1]} '{name}' ha sido agregado al inventario.")
        else:
            st.error("Por favor, complete todos los campos correctamente.")

# --------------------------------------------------------------------------------
# Función para actualizar un artículo existente
# --------------------------------------------------------------------------------
def update_item(inventory, category):
    if inventory.empty:
        st.warning("No hay artículos en el inventario para actualizar.")
        return

    item_code = st.selectbox(f"Selecciona el ID del {category[:-1]} a actualizar", inventory["ID"])
    item_data = inventory[inventory["ID"] == item_code].iloc[0]

    name = st.text_input("Nombre del artículo", value=item_data["Nombre"])
    quantity = st.number_input("Cantidad Disponible", min_value=0, value=item_data["Cantidad"], step=1)
    description = st.text_area("Descripción del artículo", value=item_data["Descripción"])

    if category == "plantas":
        unit_price = st.number_input("Precio Unitario ($)", min_value=0.0, value=item_data["Precio Unitario"], step=0.1)
    else:
        unit_price = None

    if st.button(f"Actualizar {category[:-1]}"):
        if name and quantity >= 0:
            updated_item = {
                "ID": item_code,
                "Nombre": name,
                "Cantidad": quantity,
                "Descripción": description
            }
            if category == "plantas":
                updated_item["Precio Unitario"] = unit_price

            inventory.loc[inventory["ID"] == item_code, updated_item.keys()] = updated_item.values()
            save_inventory(inventory, category)
            st.success(f"El {category[:-1]} '{name}' ha sido actualizado.")
        else:
            st.error("Por favor, complete todos los campos correctamente.")

# --------------------------------------------------------------------------------
# Función para eliminar un artículo del inventario
# --------------------------------------------------------------------------------
def delete_item(inventory, category):
    item_code = st.selectbox(f"Selecciona el ID del {category[:-1]} a eliminar", inventory["ID"])

    if st.button(f"Eliminar {category[:-1]}"):
        inventory = inventory[inventory["ID"] != item_code]
        save_inventory(inventory, category)
        st.success(f"El {category[:-1]} con ID '{item_code}' ha sido eliminado del inventario.")

# --------------------------------------------------------------------------------
# Función para cargar un archivo CSV y reemplazar el inventario
# --------------------------------------------------------------------------------
def bulk_load_inventory(category):
    st.subheader(f"Carga Masiva de Inventario para {category[:-1].capitalize()}")
    
    uploaded_file = st.file_uploader(f"Cargar archivo CSV para {category[:-1]}", type="csv")
    
    if uploaded_file is not None:
        try:
            new_inventory = pd.read_csv(uploaded_file)
            
            required_columns = load_inventory(category).columns
            if not all(col in new_inventory.columns for col in required_columns):
                st.error(f"El archivo CSV debe contener las siguientes columnas: {', '.join(required_columns)}")
                return
            
            save_inventory(new_inventory, category)
            st.success(f"El inventario de {category[:-1]} ha sido actualizado con los datos del archivo.")
        except Exception as e:
            st.error(f"Ocurrió un error al cargar el archivo: {str(e)}")

# --------------------------------------------------------------------------------
# Función para cargar las ventas desde el archivo CSV
# --------------------------------------------------------------------------------
def load_sales():
    if os.path.exists(SALES_FILE):
        sales = pd.read_csv(SALES_FILE)
    else:
        sales = pd.DataFrame(columns=["Fecha", "Cliente", "Planta", "Cantidad", "Precio Unitario", "Total"])
        sales.to_csv(SALES_FILE, index=False)
    return sales

# --------------------------------------------------------------------------------
# Función para guardar las ventas en el archivo CSV
# --------------------------------------------------------------------------------
def save_sales(sales):
    sales.to_csv(SALES_FILE, index=False)






# --------------------------------------------------------------------------------
# Función para registrar una venta
# --------------------------------------------------------------------------------
def register_sale():
    inventory = load_inventory_with_colors("plantas")  # Cargar inventario de plantas
    
    st.subheader("Registrar Venta de Plantas")
    
    # Aquí agregamos la posibilidad de seleccionar varias plantas
    plant_options = inventory["Nombre"].tolist()
    selected_plants = st.multiselect("Selecciona las plantas a vender", plant_options)
    
    sale_items = []
    for plant_name in selected_plants:
        plant_data = inventory[inventory["Nombre"] == plant_name].iloc[0]
        plant_price = plant_data["Precio Unitario"]
        plant_stock = plant_data["Cantidad"]

        quantity_to_sell = st.number_input(f"Cantidad de {plant_name} a vender", min_value=1, max_value=plant_stock, step=1)
        if quantity_to_sell > 0:
            sale_items.append({
                "Nombre": plant_name,
                "Cantidad": quantity_to_sell,
                "Precio Unitario": plant_price,
                "Total": plant_price * quantity_to_sell
            })

    customer_name = st.text_input("Nombre del Cliente")

    if st.button("Registrar Venta"):
        if sale_items and customer_name:
            total_sale = sum(item["Total"] for item in sale_items)
            # Actualizamos el inventario de las plantas vendidas
            for item in sale_items:
                plant_name = item["Nombre"]
                quantity_sold = item["Cantidad"]
                inventory.loc[inventory["Nombre"] == plant_name, "Cantidad"] -= quantity_sold
            save_inventory(inventory, "plantas")

            # Guardamos la venta
            sale_data = {
                "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Cliente": customer_name,
                "Plantas": ", ".join([item["Nombre"] for item in sale_items]),
                "Cantidad": sum(item["Cantidad"] for item in sale_items),
                "Precio Unitario": ", ".join([str(item["Precio Unitario"]) for item in sale_items]),
                "Total": total_sale
            }

            sales = load_sales()
            sales = pd.concat([sales, pd.DataFrame([sale_data])], ignore_index=True)
            save_sales(sales)

            st.success(f"Venta registrada: {customer_name} compró varias plantas por un total de {total_sale}.")


# --------------------------------------------------------------------------------
# Función para el login
# --------------------------------------------------------------------------------
def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Nombre de Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("Ingresar"):
        users = load_users()
        user_data = users[users["username"] == username]
        if not user_data.empty:
            hashed_password = user_data["password"].values[0]
            if hashlib.sha256(password.encode()).hexdigest() == hashed_password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user_data["role"].values[0]
                st.sidebar.success("¡Has ingresado correctamente!")
            else:
                st.sidebar.error("Contraseña incorrecta.")
        else:
            st.sidebar.error("Usuario no encontrado.")

# --------------------------------------------------------------------------------
# Función para generar la factura en formato PDF
# --------------------------------------------------------------------------------
def generate_invoice(sale_data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Configurar fuente
    pdf.set_font("Arial", size=12)

    # Título de la factura
    pdf.cell(200, 10, txt="Factura de Venta - Vivero Andalucia", ln=True, align='C')
    pdf.ln(10)

    # Detalles del cliente
    pdf.cell(100, 10, txt=f"Cliente: {sale_data['Cliente']}", ln=True)
    pdf.cell(100, 10, txt=f"Fecha: {sale_data['Fecha']}", ln=True)
    pdf.ln(10)

    # Detalles de las plantas vendidas
    pdf.cell(100, 10, txt="Plantas Compradas:", ln=True)
    for plant_name, quantity, price, total in zip(sale_data["Plantas"], sale_data["Cantidad"], sale_data["Precio Unitario"], sale_data["Total"]):
        pdf.cell(100, 10, txt=f"{plant_name} - Cantidad: {quantity} - Precio Unitario: ${price} - Total: ${total}", ln=True)

    pdf.ln(10)
    
    # Total de la venta
    pdf.cell(100, 10, txt=f"Total de la Venta: ${sale_data['TotalVenta']}", ln=True)

    # Reemplazar caracteres no válidos en el nombre del archivo (como los dos puntos)
    valid_filename = f"Factura_{sale_data['Fecha']}_{sale_data['Cliente']}.pdf"
    valid_filename = re.sub(r'[<>:"/\\|?*]', '', valid_filename)  # Eliminar caracteres no válidos

    # Guardar la factura como archivo PDF
    try:
        # Intenta guardar el archivo
        pdf.output(valid_filename)
        print(f"Factura generada correctamente: {valid_filename}")
    except Exception as e:
        print(f"Error al generar el archivo PDF: {e}")
        return None

    return valid_filename

# --------------------------------------------------------------------------------
# Función para visualizar las ventas por fecha con la opción de descargar factura
# --------------------------------------------------------------------------------
def view_sales_by_date():
    st.subheader("Ver Ventas por Fecha")
    sales = load_sales()
    
    # Selector de fecha
    selected_date = st.date_input("Selecciona la fecha", datetime.date.today())
    
    # Filtrar las ventas por la fecha seleccionada
    sales["Fecha"] = pd.to_datetime(sales["Fecha"])
    filtered_sales = sales[sales["Fecha"].dt.date == selected_date]
    
    if not filtered_sales.empty:
        
        
        
        st.write(f"Ventas registradas para el {selected_date}:")
        st.dataframe(filtered_sales)

        # Seleccionar una venta para ver detalles
        sale_id = st.selectbox("Selecciona una venta para ver detalles", filtered_sales.index)
        sale_data = filtered_sales.iloc[sale_id]

        # Mostrar detalles de la venta seleccionada
        st.subheader("Detalles de la Venta")
        st.write(f"**Cliente**: {sale_data['Cliente']}")
        st.write(f"**Plantas**: {sale_data['Plantas']}")
        st.write(f"**Cantidad Total**: {sale_data['Cantidad']}")
        st.write(f"**Precio Unitario**: {sale_data['Precio Unitario']}")
        st.write(f"**Total de la Venta**: {sale_data['Total']}")
        
        # Opción para generar factura en PDF
        if st.button("Generar Factura en PDF"):
            sale_details = {
                "Cliente": sale_data["Cliente"],
                "Fecha": sale_data["Fecha"],
                "Plantas": sale_data["Plantas"].split(', ') if isinstance(sale_data["Plantas"], str) else [sale_data["Plantas"]],
                "Cantidad": [sale_data["Cantidad"]],  # No se aplica split, es un solo valor
                "Precio Unitario": [sale_data["Precio Unitario"]],  # Igual
                "Total": [sale_data["Total"]],  # Igual
                "TotalVenta": sale_data["Total"]
            }
            file_name = generate_invoice(sale_details)
            st.success(f"Factura generada: {file_name}")
            st.download_button("Descargar Factura", file_name, file_name, "application/pdf")
    else:
        st.warning(f"No se encontraron ventas para el {selected_date}.")




# --------------------------------------------------------------------------------
# Función principal para manejar el menú
# --------------------------------------------------------------------------------
def main():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login()
        return

    st.title("Gestión de Inventarios de Vivero Andalucia🌿")

    menu = ["Inventario de Plantas", "Inventario de Herramientas", "Inventario de Productos", "Inventario de Maceteros", "Gestión de Usuarios", "Carga Masiva de Inventario", "Ventas"]
    choice = st.sidebar.selectbox("Selecciona una categoría", menu)

    if choice == "Ventas":
        action = st.radio("Selecciona una opción", ["Registrar Venta", "Ver Ventas por Fecha"])
        
        if action == "Registrar Venta":
            if st.session_state.role in ["admin", "vendedor"]:
                register_sale()
            else:
                st.error("No tienes permisos para registrar ventas.")
        elif action == "Ver Ventas por Fecha":
            view_sales_by_date()
    elif choice == "Gestión de Usuarios":
        add_user()
    elif choice == "Carga Masiva de Inventario":
        category = st.selectbox("Selecciona la categoría de inventario", ["plantas", "herramientas", "productos", "maceteros"])
        bulk_load_inventory(category)
    else:
        if choice == "Inventario de Plantas":
            category = "plantas"
        elif choice == "Inventario de Herramientas":
            category = "herramientas"
        elif choice == "Inventario de Productos":
            category = "productos"
        else:
            category = "maceteros"

        inventory = load_inventory_with_colors(category)

        st.subheader(f"Inventario de {category[:-1].capitalize()}")
        st.dataframe(inventory)

        action = st.radio(f"Selecciona una acción para el {category[:-1]}", ["Agregar", "Actualizar", "Eliminar"])

        if action == "Agregar":
            add_item(inventory, category)
        elif action == "Actualizar":
            update_item(inventory, category)
        elif action == "Eliminar":
            delete_item(inventory, category)

if __name__ == "__main__":
    main()
