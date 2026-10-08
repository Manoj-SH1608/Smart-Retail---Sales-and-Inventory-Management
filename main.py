import sqlite3
import os
import hashlib
import hmac
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

DB_NAME = "retail_store.db"
INVOICE_FOLDER = "invoices"
GST_RATE = 18.0

# Login credentials (password is stored as a SHA-256 hash, not plain text)
AUTH_USER_ID = "Manoj_SH"
AUTH_PASSWORD_HASH = hashlib.sha256("Majok".encode("utf-8")).hexdigest()
MAX_LOGIN_ATTEMPTS = 3

os.makedirs(INVOICE_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            total_quantity INTEGER NOT NULL,
            available_quantity INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_bill REAL NOT NULL,
            subtotal REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            gst REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES sales(transaction_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # Upgrade older database if these columns don't exist.
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN subtotal REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN gst REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# =========================================================
# GLOBAL STATE
# =========================================================

root = tk.Tk()
root.title("Smart Retail - Inventory and Sales Management + Assistant")
root.geometry("1180x760")
root.minsize(1000, 650)


# =========================================================
# THEME (colours, styled buttons, table style)
# =========================================================

BG = "#EEF2F9"
NAV_BG = "#0F172A"
ACCENT = "#4F46E5"
STRIPE = ["#4F46E5", "#0D9488", "#DB2777", "#F59E0B", "#16A34A", "#2563EB"]

# (text contains, background, foreground) - first match wins
BUTTON_COLORS = [
    ("EXIT", "#DC2626", "#FFFFFF"),
    ("DELETE", "#DC2626", "#FFFFFF"),
    ("REMOVE", "#DC2626", "#FFFFFF"),
    ("LOW STOCK", "#EA580C", "#FFFFFF"),
    ("NEW SALE", "#16A34A", "#FFFFFF"),
    ("\u2190", "#475569", "#FFFFFF"),
    ("BACK", "#475569", "#FFFFFF"),
    ("HOME", "#0D9488", "#FFFFFF"),
    ("LOGIN", "#16A34A", "#FFFFFF"),
    ("PROCEED", "#16A34A", "#FFFFFF"),
    ("ADD", "#16A34A", "#FFFFFF"),
    ("CHECKOUT", "#16A34A", "#FFFFFF"),
    ("CONFIRM", "#16A34A", "#FFFFFF"),
    ("SAVE", "#16A34A", "#FFFFFF"),
    ("UPDATE", "#FBBF24", "#1F2937"),
    ("BEST SELLER", "#FBBF24", "#1F2937"),
    ("SEARCH", "#2563EB", "#FFFFFF"),
    ("VIEW ALL", "#7C3AED", "#FFFFFF"),
    ("SALES HISTORY", "#7C3AED", "#FFFFFF"),
    ("TOTAL SALES", "#0891B2", "#FFFFFF"),
    ("CATEGORY", "#0D9488", "#FFFFFF"),
    ("SORT", "#DB2777", "#FFFFFF"),
    ("POINT OF SALE", "#DB2777", "#FFFFFF"),
    ("PRODUCT MANAGEMENT", "#2563EB", "#FFFFFF"),
    ("ANALYSIS", "#0D9488", "#FFFFFF"),
    ("FILTER", "#0D9488", "#FFFFFF"),
    ("INVOICE", "#2563EB", "#FFFFFF"),
    ("VIEW", "#2563EB", "#FFFFFF"),
    ("TRANSACTION", "#0D9488", "#FFFFFF"),
]


def shade(color, amount):
    """amount > 0 blends with white, amount < 0 blends with black."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    target = 255 if amount > 0 else 0
    k = abs(amount)
    r, g, b = (int(c + (target - c) * k) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def pick_button_colors(text):
    t = str(text).upper()
    for key, bg, fg in BUTTON_COLORS:
        if key in t:
            return bg, fg
    return ACCENT, "#FFFFFF"


_BaseButton = tk.Button


class StyledButton(_BaseButton):
    """Flat coloured button with hover effect; colour is chosen from its text."""

    def __init__(self, master=None, **kw):
        bg, fg = pick_button_colors(kw.get("text", ""))
        kw.setdefault("bg", bg)
        kw.setdefault("fg", fg)
        kw.setdefault("activebackground", shade(kw["bg"], -0.15))
        kw.setdefault("activeforeground", kw["fg"])
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        kw.setdefault("cursor", "hand2")
        kw.setdefault("padx", 12)
        kw.setdefault("pady", 6)
        big = int(kw.get("height", 0) or 0) >= 2
        kw.setdefault("font", ("Segoe UI", 11 if big else 10, "bold"))
        super().__init__(master, **kw)
        self._base_bg = kw["bg"]
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        try:
            if str(self["state"]) != "disabled":
                self.config(
                    bg=shade(self._base_bg, 0.18) if on else self._base_bg
                )
        except tk.TclError:
            pass


tk.Button = StyledButton

root.configure(bg=BG)
for _opt, _val in {
    "*Frame.background": BG,
    "*Toplevel.background": BG,
    "*Label.background": BG,
    "*Label.foreground": "#0F172A",
    "*LabelFrame.background": BG,
    "*LabelFrame.foreground": ACCENT,
    "*Entry.relief": "flat",
    "*Entry.highlightThickness": 1,
    "*Entry.highlightBackground": "#CBD5E1",
    "*Entry.highlightColor": ACCENT,
    "*Entry.background": "#FFFFFF",
    "*Entry.foreground": "#0F172A",
    "*Text.background": "#FFFFFF",
    "*Text.foreground": "#0F172A",
    "*Text.relief": "flat",
    "*Text.highlightThickness": 1,
    "*Text.highlightBackground": "#CBD5E1",
}.items():
    root.option_add(_opt, _val)

_style = ttk.Style()
try:
    _style.theme_use("clam")
except tk.TclError:
    pass
_style.configure(
    "Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
    foreground="#0F172A", rowheight=30, font=("Segoe UI", 10),
    bordercolor="#CBD5E1", borderwidth=1
)
_style.configure(
    "Treeview.Heading", background=NAV_BG, foreground="#FFFFFF",
    font=("Segoe UI", 10, "bold"), relief="flat", padding=6
)
_style.map("Treeview.Heading", background=[("active", "#1E293B")])
_style.map(
    "Treeview",
    background=[("selected", ACCENT)],
    foreground=[("selected", "#FFFFFF")]
)
_style.configure(
    "Vertical.TScrollbar", background="#94A3B8", troughcolor=BG,
    bordercolor=BG, arrowcolor="#FFFFFF"
)
_style.configure("TCombobox", padding=4)

cart = []
last_invoice = ""
current_product_rows = []

# Widget globals
product_table = None
search_table = None
cart_table = None
sales_table = None
analysis_table = None
invoice_text = None


# =========================================================
# COMMON
# =========================================================

def clear_screen():
    global product_table, search_table, cart_table, sales_table, analysis_table
    product_table = None
    search_table = None
    cart_table = None
    sales_table = None
    analysis_table = None

    for widget in root.winfo_children():
        widget.destroy()


def create_navigation():
    nav = tk.Frame(root, bg=NAV_BG)
    nav.pack(fill="x")

    tk.Label(
        nav,
        text="\u25C6  SMART RETAIL",
        font=("Segoe UI", 17, "bold"),
        bg=NAV_BG,
        fg="#FFFFFF"
    ).pack(side="left", padx=18, pady=12)

    buttons = [
        ("Home", show_dashboard),
        ("Exit", root.destroy)
    ]

    for text, command in reversed(buttons):
        tk.Button(
            nav,
            text=text,
            width=11,
            command=command
        ).pack(side="right", padx=4, pady=9)

    # multicolour accent strip under the bar
    strip = tk.Frame(root, height=4, bg=BG)
    strip.pack(fill="x")
    for color in STRIPE:
        tk.Frame(strip, height=4, bg=color).pack(
            side="left", fill="x", expand=True
        )

    # Floating AI assistant button - stays at the bottom-right of the page
    assistant_btn = tk.Canvas(
        root, width=66, height=66, bg=BG, highlightthickness=0,
        cursor="hand2"
    )
    assistant_btn.place(relx=0.975, rely=0.94, anchor="center")
    assistant_btn.create_oval(4, 4, 62, 62, fill="#4F46E5", outline="#3730A3", width=2)
    assistant_btn.create_text(33, 32, text="🤖", font=("Segoe UI Emoji", 23))
    assistant_btn.bind("<Button-1>", lambda event: open_assistant_popup())


# =========================================================
# AUTHENTICATION
# =========================================================

login_attempts = 0


def check_credentials(user_id, password):
    id_ok = hmac.compare_digest(
        user_id.encode("utf-8"),
        AUTH_USER_ID.encode("utf-8")
    )
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    pw_ok = hmac.compare_digest(pw_hash, AUTH_PASSWORD_HASH)
    return id_ok and pw_ok


def show_login():
    clear_screen()

    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True)

    center = tk.Frame(frame)
    center.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(
        center,
        text="SMART RETAIL",
        font=("Segoe UI", 34, "bold"), fg="#4F46E5"
    ).pack(pady=5)

    tk.Label(
        center,
        text="Please log in to continue",
        font=("Segoe UI", 16)
    ).pack(pady=(0, 25))

    form = tk.Frame(center)
    form.pack()

    tk.Label(
        form, text="User ID", font=("Segoe UI", 12, "bold")
    ).grid(row=0, column=0, sticky="e", padx=10, pady=8)

    user_entry = tk.Entry(form, width=28, font=("Segoe UI", 12))
    user_entry.grid(row=0, column=1, pady=8)

    tk.Label(
        form, text="Password", font=("Segoe UI", 12, "bold")
    ).grid(row=1, column=0, sticky="e", padx=10, pady=8)

    pass_entry = tk.Entry(form, width=28, font=("Segoe UI", 12), show="*")
    pass_entry.grid(row=1, column=1, pady=8)

    error_label = tk.Label(
        center, text="", fg="red", font=("Segoe UI", 11)
    )
    error_label.pack(pady=8)

    def attempt_login(event=None):
        global login_attempts

        if check_credentials(user_entry.get().strip(), pass_entry.get()):
            login_attempts = 0
            show_welcome()
            return

        login_attempts += 1
        remaining = MAX_LOGIN_ATTEMPTS - login_attempts

        if remaining <= 0:
            messagebox.showerror(
                "Access Denied",
                "Too many failed attempts. The application will close."
            )
            root.destroy()
            return

        pass_entry.delete(0, "end")
        error_label.config(
            text=f"Invalid User ID or Password. "
                 f"{remaining} attempt(s) left."
        )
        pass_entry.focus_set()

    tk.Button(
        center,
        text="LOGIN",
        font=("Segoe UI", 13, "bold"),
        width=20,
        height=2,
        command=attempt_login
    ).pack(pady=8)

    tk.Button(
        center,
        text="EXIT",
        width=20,
        command=root.destroy
    ).pack(pady=4)

    user_entry.bind("<Return>", lambda e: pass_entry.focus_set())
    pass_entry.bind("<Return>", attempt_login)
    user_entry.focus_set()


# =========================================================
# WELCOME / DASHBOARD
# =========================================================

def show_welcome():
    clear_screen()

    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True)

    center = tk.Frame(frame)
    center.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(center, text="WELCOME TO", font=("Segoe UI", 18)).pack(pady=5)
    tk.Label(center, text="SMART RETAIL", font=("Segoe UI", 34, "bold"), fg="#4F46E5").pack(pady=5)
    tk.Label(
        center,
        text="Inventory and Sales Management",
        font=("Segoe UI", 20)
    ).pack(pady=5)
    tk.Label(
        center,
        text="Products • POS • Billing • Inventory • Analytics",
        font=("Segoe UI", 12)
    ).pack(pady=18)

    tk.Button(
        center,
        text="PROCEED TO APP",
        font=("Segoe UI", 14, "bold"),
        width=22,
        height=2,
        command=show_dashboard
    ).pack(pady=15)


def show_dashboard():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="DASHBOARD",
        font=("Segoe UI", 27, "bold")
    ).pack(pady=20)

    tk.Label(
        root,
        text="Select a section to continue.",
        font=("Segoe UI", 14)
    ).pack(pady=30)

    shortcuts = tk.Frame(root)
    shortcuts.pack()

    tk.Button(
        shortcuts,
        text="PRODUCT MANAGEMENT",
        width=22,
        height=3,
        command=show_products_menu
    ).grid(row=0, column=0, padx=12)

    tk.Button(
        shortcuts,
        text="POINT OF SALE",
        width=22,
        height=3,
        command=show_pos
    ).grid(row=0, column=1, padx=12)

    tk.Button(
        shortcuts,
        text="ANALYSIS",
        width=22,
        height=3,
        command=show_analysis
    ).grid(row=0, column=2, padx=12)



# =========================================================
# PRODUCT MANAGEMENT MENU
# =========================================================

def show_products_menu():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="PRODUCT MANAGEMENT",
        font=("Segoe UI", 26, "bold")
    ).pack(pady=25)

    tk.Label(
        root,
        text="What would you like to do?",
        font=("Segoe UI", 15)
    ).pack(pady=5)

    options = tk.Frame(root)
    options.pack(pady=30)

    actions = [
        ("ADD PRODUCT", show_add_product),
        ("SEARCH PRODUCT", show_search_product),
        ("VIEW ALL PRODUCTS", show_all_products),
        ("UPDATE PRODUCT", show_update_product),
        ("DELETE PRODUCT", delete_product_window),
        ("CATEGORY FILTER", show_category_filter),
        ("SORT PRODUCTS", show_sort_products)
    ]

    for i, (text, command) in enumerate(actions):
        tk.Button(
            options,
            text=text,
            width=25,
            height=3,
            font=("Segoe UI", 11, "bold"),
            command=command
        ).grid(row=i // 2, column=i % 2, padx=15, pady=10)

    tk.Button(
        root,
        text="← Back to Dashboard",
        command=show_dashboard
    ).pack(pady=10)


def product_table_view(parent, rows):
    columns = ("ID", "Name", "Category", "Price", "Total Qty", "Available")

    table = ttk.Treeview(parent, columns=columns, show="headings", height=15)

    for col in columns:
        table.heading(col, text=col)
        table.column(col, width=145)

    for row in rows:
        table.insert(
            "",
            "end",
            values=(
                row[0],
                row[1],
                row[2],
                f"₹{row[3]:.2f}",
                row[4],
                row[5]
            )
        )

    table.pack(fill="both", expand=True, padx=25, pady=15)
    return table


# =========================================================
# ADD PRODUCT
# =========================================================

def show_add_product():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="ADD NEW PRODUCT",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=20)

    form = tk.LabelFrame(root, text="Product Details", padx=20, pady=20)
    form.pack(padx=40, pady=10)

    entries = {}

    fields = [
        ("Product Name", 0),
        ("Category", 1),
        ("Price", 2),
        ("Quantity", 3)
    ]

    for label, row in fields:
        tk.Label(form, text=label, font=("Segoe UI", 11)).grid(
            row=row, column=0, padx=10, pady=10, sticky="w"
        )
        entry = tk.Entry(form, width=30)
        entry.grid(row=row, column=1, padx=10, pady=10)
        entries[label] = entry

    def add():
        try:
            name = entries["Product Name"].get().strip()
            category = entries["Category"].get().strip()
            price = float(entries["Price"].get())
            qty = int(entries["Quantity"].get())

            if not name or not category or price < 0 or qty < 0:
                raise ValueError

            conn = get_connection()
            conn.execute("""
                INSERT INTO products
                (name, category, price, total_quantity, available_quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (name, category, price, qty, qty))
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", "Product added successfully!")
            show_products_menu()

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Enter a valid name, category, price and quantity."
            )

    tk.Button(
        root,
        text="ADD PRODUCT",
        width=20,
        height=2,
        command=add
    ).pack(pady=15)

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack()


# =========================================================
# SEARCH PRODUCT
# =========================================================

def show_search_product():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="SEARCH PRODUCT",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=20)

    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Label(
        frame,
        text="Product ID or Name:"
    ).pack(side="left", padx=5)

    entry = tk.Entry(frame, width=30)
    entry.pack(side="left", padx=5)

    result_frame = tk.Frame(root)
    result_frame.pack(fill="both", expand=True)

    def search():
        for widget in result_frame.winfo_children():
            widget.destroy()

        term = entry.get().strip()

        if not term:
            messagebox.showwarning("Search", "Enter a product ID or name.")
            return

        conn = get_connection()

        if term.isdigit():
            rows = conn.execute("""
                SELECT * FROM products
                WHERE product_id = ? OR name LIKE ?
            """, (int(term), f"%{term}%")).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM products
                WHERE name LIKE ?
            """, (f"%{term}%",)).fetchall()

        conn.close()

        if not rows:
            tk.Label(
                result_frame,
                text="No matching product found.",
                font=("Segoe UI", 14)
            ).pack(pady=30)
            return

        product_table_view(result_frame, rows)

    tk.Button(frame, text="SEARCH", command=search).pack(side="left", padx=5)

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack(pady=10)


# =========================================================
# VIEW ALL PRODUCTS
# =========================================================

def show_all_products():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="CURRENT PRODUCT INVENTORY",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=15)

    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
    conn.close()

    if not rows:
        tk.Label(root, text="Inventory is empty.").pack(pady=30)
    else:
        product_table_view(root, rows)

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack(pady=10)


# =========================================================
# UPDATE PRODUCT
# =========================================================

def show_update_product():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="UPDATE PRODUCT",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=20)

    lookup = tk.Frame(root)
    lookup.pack(pady=10)

    tk.Label(lookup, text="Product ID:").pack(side="left")
    id_entry = tk.Entry(lookup, width=15)
    id_entry.pack(side="left", padx=8)

    form = tk.LabelFrame(root, text="Product Specifications", padx=20, pady=20)
    form.pack(pady=20)

    fields = {}
    names = ["Name", "Category", "Price", "Total Quantity", "Available Quantity"]

    for i, name in enumerate(names):
        tk.Label(form, text=name).grid(row=i, column=0, padx=10, pady=8, sticky="w")
        e = tk.Entry(form, width=30)
        e.grid(row=i, column=1, padx=10, pady=8)
        fields[name] = e

    def load():
        try:
            pid = int(id_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid Product ID.")
            return

        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM products WHERE product_id = ?",
            (pid,)
        ).fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Product not found.")
            return

        fields["Name"].delete(0, tk.END)
        fields["Name"].insert(0, row[1])
        fields["Category"].delete(0, tk.END)
        fields["Category"].insert(0, row[2])
        fields["Price"].delete(0, tk.END)
        fields["Price"].insert(0, row[3])
        fields["Total Quantity"].delete(0, tk.END)
        fields["Total Quantity"].insert(0, row[4])
        fields["Available Quantity"].delete(0, tk.END)
        fields["Available Quantity"].insert(0, row[5])

    def update():
        try:
            pid = int(id_entry.get())
            name = fields["Name"].get().strip()
            category = fields["Category"].get().strip()
            price = float(fields["Price"].get())
            total = int(fields["Total Quantity"].get())
            available = int(fields["Available Quantity"].get())

            if not name or not category or price < 0 or total < 0 or available < 0:
                raise ValueError

            conn = get_connection()
            conn.execute("""
                UPDATE products
                SET name=?, category=?, price=?,
                    total_quantity=?, available_quantity=?
                WHERE product_id=?
            """, (name, category, price, total, available, pid))
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", "Product updated successfully.")
            show_products_menu()

        except ValueError:
            messagebox.showerror("Error", "Enter valid product values.")

    tk.Button(lookup, text="LOAD PRODUCT", command=load).pack(side="left")

    tk.Button(
        root,
        text="SAVE CHANGES",
        width=20,
        command=update
    ).pack(pady=10)

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack()


# =========================================================
# DELETE PRODUCT
# =========================================================

def delete_product_window():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="DELETE PRODUCT",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=25)

    frame = tk.Frame(root)
    frame.pack(pady=20)

    tk.Label(frame, text="Product ID:").pack(side="left")
    entry = tk.Entry(frame, width=20)
    entry.pack(side="left", padx=8)

    def delete():
        try:
            pid = int(entry.get())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid Product ID.")
            return

        conn = get_connection()
        row = conn.execute(
            "SELECT name FROM products WHERE product_id=?",
            (pid,)
        ).fetchone()

        if not row:
            conn.close()
            messagebox.showerror("Error", "Product not found.")
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete product '{row[0]}' permanently?"
        ):
            conn.close()
            return

        conn.execute("DELETE FROM products WHERE product_id=?", (pid,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Deleted", "Product deleted successfully.")
        show_products_menu()

    tk.Button(
        frame,
        text="DELETE",
        command=delete
    ).pack(side="left", padx=8)

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack(pady=15)


# =========================================================
# CATEGORY FILTER
# =========================================================

def show_category_filter():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="CATEGORY FILTER",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=20)

    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Label(frame, text="Category:").pack(side="left")
    entry = tk.Entry(frame, width=25)
    entry.pack(side="left", padx=8)

    result = tk.Frame(root)
    result.pack(fill="both", expand=True)

    def filter_category():
        for widget in result.winfo_children():
            widget.destroy()

        term = entry.get().strip()

        conn = get_connection()
        rows = conn.execute("""
            SELECT * FROM products
            WHERE category LIKE ?
            ORDER BY category, name
        """, (f"%{term}%",)).fetchall()
        conn.close()

        if not rows:
            tk.Label(result, text="No products found in this category.").pack(pady=30)
        else:
            product_table_view(result, rows)

    tk.Button(frame, text="FILTER", command=filter_category).pack(side="left")

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack(pady=10)


# =========================================================
# SORT PRODUCTS
# =========================================================

def show_sort_products():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="SORT PRODUCTS",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=20)

    frame = tk.Frame(root)
    frame.pack(pady=10)

    sort_var = tk.StringVar(value="Price: Low to High")

    options = [
        "Price: Low to High",
        "Price: High to Low",
        "Quantity: Low to High",
        "Quantity: High to Low"
    ]

    combo = ttk.Combobox(
        frame,
        textvariable=sort_var,
        values=options,
        state="readonly",
        width=25
    )
    combo.pack(side="left", padx=8)

    result = tk.Frame(root)
    result.pack(fill="both", expand=True)

    def sort():
        for widget in result.winfo_children():
            widget.destroy()

        mapping = {
            "Price: Low to High": "price ASC",
            "Price: High to Low": "price DESC",
            "Quantity: Low to High": "available_quantity ASC",
            "Quantity: High to Low": "available_quantity DESC"
        }

        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM products ORDER BY " + mapping[sort_var.get()]
        ).fetchall()
        conn.close()

        product_table_view(result, rows)

    tk.Button(frame, text="SORT", command=sort).pack(side="left")

    tk.Button(
        root,
        text="← Product Management Menu",
        command=show_products_menu
    ).pack(pady=10)


# =========================================================
# POS
# =========================================================

def show_pos():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="POINT OF SALE",
        font=("Segoe UI", 25, "bold")
    ).pack(pady=15)

    form = tk.LabelFrame(
        root,
        text="Add Product to Cart",
        padx=15,
        pady=15
    )
    form.pack(fill="x", padx=25, pady=10)

    tk.Label(form, text="Product ID / Name").pack(side="left", padx=5)

    identifier = tk.Entry(form, width=25)
    identifier.pack(side="left", padx=5)

    tk.Label(form, text="Quantity").pack(side="left", padx=5)

    quantity = tk.Entry(form, width=10)
    quantity.pack(side="left", padx=5)

    tk.Button(
        form,
        text="ADD TO CART",
        command=lambda: add_to_cart(identifier, quantity)
    ).pack(side="left", padx=10)

    global cart_table
    columns = ("ID", "Product", "Qty", "Unit Price", "Total")

    cart_table = ttk.Treeview(
        root,
        columns=columns,
        show="headings"
    )

    for col in columns:
        cart_table.heading(col, text=col)
        cart_table.column(col, width=170)

    cart_table.pack(
        fill="both",
        expand=True,
        padx=25,
        pady=10
    )

    bottom = tk.Frame(root)
    bottom.pack(fill="x", padx=25, pady=10)

    tk.Button(
        bottom,
        text="REMOVE SELECTED",
        command=remove_from_cart
    ).pack(side="right", padx=5)

    tk.Button(
        bottom,
        text="CHECKOUT →",
        font=("Segoe UI", 11, "bold"),
        command=checkout
    ).pack(side="right", padx=5)

    update_cart_table()


def find_product(identifier):
    conn = get_connection()

    if identifier.isdigit():
        row = conn.execute("""
            SELECT product_id, name, price, available_quantity
            FROM products
            WHERE product_id = ?
        """, (int(identifier),)).fetchone()
    else:
        row = conn.execute("""
            SELECT product_id, name, price, available_quantity
            FROM products
            WHERE name LIKE ?
            ORDER BY name
            LIMIT 1
        """, (f"%{identifier}%",)).fetchone()

    conn.close()
    return row


def add_to_cart(identifier_entry, quantity_entry):
    identifier = identifier_entry.get().strip()

    try:
        qty = int(quantity_entry.get())
        if qty <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Quantity", "Enter a positive quantity.")
        return

    if not identifier:
        messagebox.showerror("Product", "Enter a Product ID or Product Name.")
        return

    product = find_product(identifier)

    if not product:
        messagebox.showerror("Product Not Found", "No matching product found.")
        return

    pid, name, price, available = product

    existing_qty = sum(
        item["qty"] for item in cart if item["id"] == pid
    )

    if existing_qty + qty > available:
        messagebox.showerror(
            "Out of Stock",
            f"Only {available} units of '{name}' are available."
        )
        return

    for item in cart:
        if item["id"] == pid:
            item["qty"] += qty
            update_cart_table()
            identifier_entry.delete(0, tk.END)
            quantity_entry.delete(0, tk.END)
            return

    cart.append({
        "id": pid,
        "name": name,
        "qty": qty,
        "price": price
    })

    identifier_entry.delete(0, tk.END)
    quantity_entry.delete(0, tk.END)
    update_cart_table()


def update_cart_table():
    if cart_table is None:
        return

    for item in cart_table.get_children():
        cart_table.delete(item)

    for item in cart:
        total = item["qty"] * item["price"]

        cart_table.insert(
            "",
            "end",
            values=(
                item["id"],
                item["name"],
                item["qty"],
                f"₹{item['price']:.2f}",
                f"₹{total:.2f}"
            )
        )


def remove_from_cart():
    if cart_table is None:
        return

    selected = cart_table.selection()

    if not selected:
        messagebox.showwarning("Cart", "Select an item to remove.")
        return

    index = cart_table.index(selected[0])
    cart.pop(index)
    update_cart_table()


# =========================================================
# CHECKOUT + INVOICE
# =========================================================

def checkout():
    if not cart:
        messagebox.showwarning("Checkout", "Your cart is empty.")
        return

    subtotal = sum(item["qty"] * item["price"] for item in cart)

    dialog = tk.Toplevel(root)
    dialog.title("Checkout")
    dialog.geometry("430x420")
    dialog.transient(root)
    dialog.grab_set()

    tk.Label(
        dialog,
        text="CHECKOUT",
        font=("Segoe UI", 20, "bold")
    ).pack(pady=15)

    tk.Label(
        dialog,
        text=f"Subtotal: ₹{subtotal:.2f}",
        font=("Segoe UI", 12)
    ).pack(pady=5)

    discount_frame = tk.Frame(dialog)
    discount_frame.pack(pady=10)

    tk.Label(discount_frame, text="Discount %:").pack(side="left")
    discount_entry = tk.Entry(discount_frame, width=10)
    discount_entry.insert(0, "0")
    discount_entry.pack(side="left", padx=8)

    gst_frame = tk.Frame(dialog)
    gst_frame.pack(pady=5)

    tk.Label(gst_frame, text="GST %:").pack(side="left")
    gst_entry = tk.Entry(gst_frame, width=10)
    gst_entry.insert(0, str(GST_RATE))
    gst_entry.pack(side="left", padx=8)

    summary = tk.Label(
        dialog,
        text="",
        font=("Segoe UI", 11, "bold"),
        justify="left"
    )
    summary.pack(pady=15)

    def calculate():
        try:
            discount_rate = float(discount_entry.get())
            gst_rate = float(gst_entry.get())

            if not 0 <= discount_rate <= 100 or gst_rate < 0:
                raise ValueError

            discount_amount = subtotal * discount_rate / 100
            after_discount = subtotal - discount_amount
            gst_amount = after_discount * gst_rate / 100
            grand_total = after_discount + gst_amount

            summary.config(
                text=(
                    f"Subtotal:       ₹{subtotal:.2f}\n"
                    f"Discount:       ₹{discount_amount:.2f}\n"
                    f"After Discount: ₹{after_discount:.2f}\n"
                    f"GST:            ₹{gst_amount:.2f}\n"
                    f"Grand Total:    ₹{grand_total:.2f}"
                )
            )

            return discount_rate, discount_amount, gst_amount, grand_total

        except ValueError:
            messagebox.showerror(
                "Invalid Values",
                "Enter valid discount and GST percentages."
            )
            return None

    def confirm():
        result = calculate()

        if not result:
            return

        discount_rate, discount_amount, gst_amount, grand_total = result

        if not messagebox.askyesno(
            "Confirm Checkout",
            f"Proceed with checkout for ₹{grand_total:.2f}?"
        ):
            return

        dialog.destroy()
        complete_sale(
            subtotal,
            discount_rate,
            discount_amount,
            gst_amount,
            grand_total
        )

    tk.Button(
        dialog,
        text="CALCULATE TOTAL",
        command=calculate
    ).pack(pady=5)

    tk.Button(
        dialog,
        text="CONFIRM CHECKOUT",
        font=("Segoe UI", 11, "bold"),
        width=22,
        command=confirm
    ).pack(pady=10)

    tk.Button(
        dialog,
        text="CANCEL",
        command=dialog.destroy
    ).pack()


def complete_sale(subtotal, discount_rate, discount_amount, gst_amount, grand_total):
    global last_invoice

    conn = get_connection()

    try:
        cur = conn.cursor()
        cur.execute("BEGIN")

        cur.execute("""
            INSERT INTO sales
            (total_bill, subtotal, discount, gst)
            VALUES (?, ?, ?, ?)
        """, (
            grand_total,
            subtotal,
            discount_amount,
            gst_amount
        ))

        transaction_id = cur.lastrowid

        for item in cart:
            cur.execute("""
                INSERT INTO sale_items
                (transaction_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (
                transaction_id,
                item["id"],
                item["qty"],
                item["price"]
            ))

            cur.execute("""
                UPDATE products
                SET available_quantity =
                    available_quantity - ?
                WHERE product_id = ?
            """, (
                item["qty"],
                item["id"]
            ))

        conn.commit()
        conn.close()

        invoice = create_invoice(
            transaction_id,
            cart.copy(),
            subtotal,
            discount_rate,
            discount_amount,
            gst_amount,
            grand_total
        )

        last_invoice = invoice
        cart.clear()

        show_invoice(transaction_id, invoice)

    except Exception as e:
        conn.rollback()
        conn.close()
        messagebox.showerror("Checkout Error", str(e))


def create_invoice(
    transaction_id,
    items,
    subtotal,
    discount_rate,
    discount_amount,
    gst_amount,
    grand_total
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("=" * 58)
    lines.append("                 SMART RETAIL")
    lines.append("             INVENTORY & POS SYSTEM")
    lines.append("=" * 58)
    lines.append(f"Invoice ID : {transaction_id}")
    lines.append(f"Date/Time  : {now}")
    lines.append("-" * 58)
    lines.append(f"{'Product':<25}{'Qty':>6}{'Price':>12}{'Total':>13}")
    lines.append("-" * 58)

    for item in items:
        item_total = item["qty"] * item["price"]
        lines.append(
            f"{item['name'][:25]:<25}"
            f"{item['qty']:>6}"
            f"{item['price']:>12.2f}"
            f"{item_total:>13.2f}"
        )

    lines.append("-" * 58)
    lines.append(f"{'Subtotal':<43}₹{subtotal:>12.2f}")
    lines.append(
        f"{'Discount (' + str(discount_rate) + '%)':<43}"
        f"-₹{discount_amount:>11.2f}"
    )
    lines.append(f"{'GST':<43}₹{gst_amount:>12.2f}")
    lines.append("=" * 58)
    lines.append(f"{'GRAND TOTAL':<43}₹{grand_total:>12.2f}")
    lines.append("=" * 58)
    lines.append("             Thank You For Shopping!")
    lines.append("=" * 58)

    invoice = "\n".join(lines)

    filename = os.path.join(
        INVOICE_FOLDER,
        f"invoice_{transaction_id}.txt"
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(invoice)

    return invoice


def show_invoice(transaction_id, invoice):
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="CHECKOUT COMPLETE — INVOICE",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=15)

    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=80, pady=10)

    global invoice_text

    invoice_text = tk.Text(
        frame,
        font=("Courier New", 11),
        wrap="none"
    )
    invoice_text.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(
        frame,
        orient="vertical",
        command=invoice_text.yview
    )
    scrollbar.pack(side="right", fill="y")

    invoice_text.configure(yscrollcommand=scrollbar.set)
    invoice_text.insert("1.0", invoice)
    invoice_text.config(state="disabled")

    buttons = tk.Frame(root)
    buttons.pack(pady=10)

    tk.Button(
        buttons,
        text="← NEW SALE",
        width=18,
        command=show_pos
    ).grid(row=0, column=0, padx=5)

    tk.Button(
        buttons,
        text="OPEN INVOICE FILE",
        width=20,
        command=lambda: open_invoice_file(transaction_id)
    ).grid(row=0, column=1, padx=5)

    tk.Button(
        buttons,
        text="SALES HISTORY",
        width=18,
        command=show_sales_history
    ).grid(row=0, column=2, padx=5)


def open_invoice_file(transaction_id):
    filename = os.path.abspath(
        os.path.join(INVOICE_FOLDER, f"invoice_{transaction_id}.txt")
    )

    if not os.path.exists(filename):
        messagebox.showerror("Invoice", "Invoice file not found.")
        return

    try:
        os.startfile(filename)
    except AttributeError:
        messagebox.showinfo("Invoice Location", filename)


# =========================================================
# SALES HISTORY / TRANSACTION DETAILS
# =========================================================

def show_sales_history():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="SALES / INVOICE HISTORY",
        font=("Segoe UI", 24, "bold")
    ).pack(pady=15)

    global sales_table

    columns = (
        "Transaction ID",
        "Date / Time",
        "Subtotal",
        "Discount",
        "GST",
        "Total"
    )

    sales_table = ttk.Treeview(
        root,
        columns=columns,
        show="headings"
    )

    for col in columns:
        sales_table.heading(col, text=col)
        sales_table.column(col, width=160)

    sales_table.pack(fill="both", expand=True, padx=25, pady=15)

    conn = get_connection()
    rows = conn.execute("""
        SELECT transaction_id, timestamp,
               COALESCE(subtotal, total_bill),
               COALESCE(discount, 0),
               COALESCE(gst, 0),
               total_bill
        FROM sales
        ORDER BY transaction_id DESC
    """).fetchall()
    conn.close()

    for row in rows:
        sales_table.insert(
            "",
            "end",
            values=(
                row[0],
                row[1],
                f"₹{row[2]:.2f}",
                f"₹{row[3]:.2f}",
                f"₹{row[4]:.2f}",
                f"₹{row[5]:.2f}"
            )
        )

    buttons = tk.Frame(root)
    buttons.pack(pady=10)

    tk.Button(
        buttons,
        text="VIEW SELECTED INVOICE",
        command=view_selected_invoice
    ).pack(side="left", padx=5)

    tk.Button(
        buttons,
        text="TRANSACTION DETAILS",
        command=show_transaction_details
    ).pack(side="left", padx=5)


def selected_transaction_id():
    if sales_table is None:
        return None

    selected = sales_table.selection()

    if not selected:
        messagebox.showwarning("Select", "Select a transaction first.")
        return None

    return int(sales_table.item(selected[0])["values"][0])


def view_selected_invoice():
    tid = selected_transaction_id()

    if tid is None:
        return

    filename = os.path.join(
        INVOICE_FOLDER,
        f"invoice_{tid}.txt"
    )

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            invoice = f.read()
        show_invoice(tid, invoice)
    else:
        messagebox.showwarning(
            "Invoice",
            "Invoice file is not available for this transaction."
        )
def show_transaction_details():
    tid = selected_transaction_id()

    if tid is None:
        return

    show_transaction_details_by_id(tid)


def search_transaction_window():
    tid = simpledialog.askinteger(
        "Transaction Search",
        "Enter Transaction ID:"
    )

    if tid is None:
        return

    conn = get_connection()
    row = conn.execute(
        "SELECT transaction_id FROM sales WHERE transaction_id=?",
        (tid,)
    ).fetchone()
    conn.close()

    if not row:
        messagebox.showerror("Search", "Transaction not found.")
        return

    filename = os.path.join(
        INVOICE_FOLDER,
        f"invoice_{tid}.txt"
    )

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            show_invoice(tid, f.read())
    else:
        show_transaction_details_by_id(tid)


def show_transaction_details_by_id(tid):
    conn = get_connection()

    sale = conn.execute("""
        SELECT transaction_id, timestamp,
               COALESCE(subtotal, total_bill),
               COALESCE(discount, 0),
               COALESCE(gst, 0),
               total_bill
        FROM sales
        WHERE transaction_id=?
    """, (tid,)).fetchone()

    items = conn.execute("""
        SELECT p.name, si.quantity, si.unit_price
        FROM sale_items si
        JOIN products p ON si.product_id=p.product_id
        WHERE si.transaction_id=?
    """, (tid,)).fetchall()

    conn.close()

    if not sale:
        messagebox.showerror("Transaction", "Transaction not found.")
        return

    data = [
        (name, qty, f"₹{price:.2f}", f"₹{qty * price:.2f}")
        for name, qty, price in items
    ]

    show_report_page(
        f"TRANSACTION #{sale[0]}",
        ("Item", "Quantity", "Unit Price", "Line Total"),
        data,
        summary=[
            ("Invoice ID", sale[0]),
            ("Date / Time", sale[1]),
            ("Subtotal", f"₹{sale[2]:.2f}"),
            ("Discount", f"₹{sale[3]:.2f}"),
            ("GST", f"₹{sale[4]:.2f}"),
            ("Total", f"₹{sale[5]:.2f}")
        ],
        empty_message="No items recorded for this transaction.",
        widths=[300, 130, 150, 150]
    )


# =========================================================
# SMART RETAIL ASSISTANT / CHATBOT
# =========================================================

def chatbot_reply(message):
    text = message.strip().lower()
    if not text:
        return "Please type a question. Try: Help, low stock, today's sales, best seller, inventory, or stock of [product]."
    if text in ("hi", "hello", "hey"):
        return "👋 Hi! I'm your Smart Retail Assistant. Ask me about stock, sales, products or transactions."
    if "help" in text or "what can you do" in text:
        return ("🤖 I can help with:\n\n• Low-stock products\n• Best sellers\n• Today's/total sales\n• Inventory summary\n• Out-of-stock products\n• Product availability\n• Transaction details\n• How to add a product or make a sale\n\nTry: 'Show low stock' or 'Stock of laptop'.")

    conn=get_connection()
    if "low stock" in text or "low-stock" in text:
        rows=conn.execute("SELECT name,available_quantity FROM products WHERE available_quantity < 5 ORDER BY available_quantity ASC").fetchall(); conn.close()
        return "⚠️ LOW STOCK PRODUCTS\n\n"+"\n".join(f"• {n} — {q} unit(s) left" for n,q in rows) if rows else "✅ No products are below the 5-unit low-stock threshold."
    if "out of stock" in text:
        rows=conn.execute("SELECT name,category FROM products WHERE available_quantity <= 0 ORDER BY name").fetchall(); conn.close()
        return "🚨 OUT OF STOCK\n\n"+"\n".join(f"• {n} ({c})" for n,c in rows) if rows else "✅ No products are currently out of stock."
    if any(x in text for x in ("best seller","best-selling","bestseller","top seller","top selling")):
        rows=conn.execute("""SELECT p.name,p.category,SUM(si.quantity),SUM(si.quantity*si.unit_price) FROM sale_items si JOIN products p ON si.product_id=p.product_id GROUP BY si.product_id ORDER BY SUM(si.quantity) DESC LIMIT 5""").fetchall(); conn.close()
        return "🏆 TOP SELLERS\n\n"+"\n".join(f"{i}. {n} — {q} sold — ₹{r:.2f}" for i,(n,c,q,r) in enumerate(rows,1)) if rows else "📊 No sales recorded yet."
    if any(x in text for x in ("today's sales","todays sales","today sales","sales today")):
        n,total=conn.execute("SELECT COUNT(*),COALESCE(SUM(total_bill),0) FROM sales WHERE date(timestamp,'localtime')=date('now','localtime')").fetchone(); conn.close()
        return f"📅 TODAY'S SALES\n\nTransactions: {n}\nSales: ₹{total:.2f}"
    if any(x in text for x in ("total sales","total revenue","overall sales","revenue")):
        total,n=conn.execute("SELECT COALESCE(SUM(total_bill),0),COUNT(*) FROM sales").fetchone(); conn.close()
        return f"💰 SALES SUMMARY\n\nTotal sales: ₹{total:.2f}\nTransactions: {n}\nAverage bill: ₹{(total/n if n else 0):.2f}"
    if any(x in text for x in ("inventory","stock count","how many products","product count","stock summary")):
        n,total,avail=conn.execute("SELECT COUNT(*),COALESCE(SUM(total_quantity),0),COALESCE(SUM(available_quantity),0) FROM products").fetchone(); conn.close()
        return f"📦 INVENTORY SUMMARY\n\nDifferent products: {n}\nTotal units: {total}\nAvailable units: {avail}\nUnits sold/used: {total-avail}"
    import re
    m=re.search(r"(?:transaction|invoice|bill)\s*(?:id|number|no\.?)?\s*#?\s*(\d+)",text)
    if m:
        tid=int(m.group(1)); sale=conn.execute("SELECT transaction_id,timestamp,total_bill,COALESCE(subtotal,total_bill),COALESCE(discount,0),COALESCE(gst,0) FROM sales WHERE transaction_id=?",(tid,)).fetchone()
        if not sale: conn.close(); return f"❌ Transaction #{tid} was not found."
        items=conn.execute("SELECT p.name,si.quantity,si.unit_price FROM sale_items si JOIN products p ON si.product_id=p.product_id WHERE si.transaction_id=?",(tid,)).fetchall(); conn.close()
        return (f"🧾 TRANSACTION #{tid}\n\nDate: {sale[1]}\nSubtotal: ₹{sale[3]:.2f}\nDiscount: ₹{sale[4]:.2f}\nGST: ₹{sale[5]:.2f}\nTotal: ₹{sale[2]:.2f}\n\nItems:\n"+"\n".join(f"• {n} × {q} — ₹{q*pr:.2f}" for n,q,pr in items))
    for term in ("stock of ","availability of ","available stock of ","quantity of "):
        if term in text:
            q=text.split(term,1)[1].strip(" ?.!" ); row=conn.execute("SELECT name,category,price,available_quantity,total_quantity FROM products WHERE lower(name) LIKE ? ORDER BY name LIMIT 1",(f"%{q}%",)).fetchone(); conn.close()
            return f"📦 PRODUCT: {row[0]}\n\nCategory: {row[1]}\nPrice: ₹{row[2]:.2f}\nAvailable: {row[3]} unit(s)\nTotal quantity: {row[4]}" if row else f"❌ I couldn't find a product matching '{q}'."
    conn.close()
    if "add product" in text:
        return "🛒 Product Management → ADD PRODUCT → enter details → ADD PRODUCT."
    if "new sale" in text or "make a sale" in text or "billing" in text:
        return "🧾 POINT OF SALE → enter product and quantity → ADD TO CART → CHECKOUT."
    return "🤔 I can help with inventory, low stock, best sellers, sales, products and transactions. Type 'Help' for examples."

def open_assistant_popup():
    # Reuse the existing assistant window if it is already open.
    existing = getattr(root, "assistant_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return

    win = tk.Toplevel(root)
    root.assistant_window = win
    win.title("Smart Retail AI Assistant")
    win.geometry("430x570")
    win.minsize(380, 500)
    win.configure(bg="#F8FAFC")
    win.transient(root)

    def close_window():
        root.assistant_window = None
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", close_window)

    header = tk.Frame(win, bg="#4F46E5", height=72)
    header.pack(fill="x")
    tk.Label(
        header, text="🤖  Smart Retail AI",
        font=("Segoe UI", 16, "bold"), bg="#4F46E5", fg="white"
    ).pack(anchor="w", padx=18, pady=(12, 0))
    tk.Label(
        header, text="Your interactive store assistant",
        font=("Segoe UI", 9), bg="#4F46E5", fg="#E0E7FF"
    ).pack(anchor="w", padx=20, pady=(2, 10))

    frame = tk.Frame(win, bg="white", bd=1, relief="solid")
    frame.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    chat = tk.Text(
        frame, wrap="word", font=("Segoe UI", 10),
        bg="white", fg="#0F172A", padx=12, pady=10,
        relief="flat", state="disabled"
    )
    chat.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(frame, orient="vertical", command=chat.yview)
    sb.pack(side="right", fill="y")
    chat.configure(yscrollcommand=sb.set)
    chat.tag_configure("bot", font=("Segoe UI", 10, "bold"), foreground="#4F46E5")
    chat.tag_configure("user", font=("Segoe UI", 10, "bold"), foreground="#0F172A")

    def add(sender, msg, tag):
        chat.config(state="normal")
        chat.insert("end", sender + "\n", tag)
        chat.insert("end", msg + "\n\n")
        chat.config(state="disabled")
        chat.see("end")

    add(
        "🤖 Retail Assistant",
        "Hi! 👋 Ask me about stock, sales, best sellers, products or transactions.",
        "bot"
    )

    quick = tk.Frame(win, bg="#F8FAFC")
    quick.pack(fill="x", padx=12, pady=(0, 5))

    input_frame = tk.Frame(win, bg="#F8FAFC")
    input_frame.pack(fill="x", padx=12, pady=(0, 10))
    entry = tk.Entry(input_frame, font=("Segoe UI", 11), relief="solid", bd=1)
    entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 7))

    def send(event=None, preset=None):
        q = preset if preset is not None else entry.get().strip()
        if not q:
            return
        if preset is None:
            entry.delete(0, tk.END)
        add("👤 You", q, "user")
        win.after(80, lambda: add("🤖 Retail Assistant", chatbot_reply(q), "bot"))

    tk.Button(
        input_frame, text="SEND", width=8, height=1,
        font=("Segoe UI", 10, "bold"), command=send
    ).pack(side="right")

    for q in ("Low stock", "Today's sales", "Best seller", "Inventory"):
        tk.Button(
            quick, text=q, font=("Segoe UI", 8),
            command=lambda x=q: send(preset=x)
        ).pack(side="left", padx=2)

    tk.Label(
        win, text="Press Enter to send • Click 🤖 anytime to reopen",
        font=("Segoe UI", 8), bg="#F8FAFC", fg="#64748B"
    ).pack(pady=(0, 8))

    entry.bind("<Return>", send)
    entry.focus_set()


def show_chatbot():
    # Kept for compatibility with older code; the assistant is now a popup.
    open_assistant_popup()

# =========================================================
# ANALYSIS
# =========================================================

def show_analysis():
    clear_screen()
    create_navigation()

    tk.Label(
        root,
        text="STORE ANALYSIS & REPORTS",
        font=("Segoe UI", 26, "bold")
    ).pack(pady=25)

    tk.Label(
        root,
        text="Choose a report to open",
        font=("Segoe UI", 15)
    ).pack(pady=5)

    options = tk.Frame(root)
    options.pack(pady=30)

    actions = [
        ("LOW STOCK", show_low_stock),
        ("BEST SELLER", show_best_seller),
        ("TOTAL SALES", show_total_sales),
        ("SALES HISTORY", show_sales_history),
        ("SEARCH TRANSACTION", search_transaction_window)
    ]

    for i, (text, command) in enumerate(actions):
        tk.Button(
            options,
            text=text,
            width=25,
            height=3,
            font=("Segoe UI", 11, "bold"),
            command=command
        ).grid(row=i // 2, column=i % 2, padx=15, pady=10)


def show_report_page(title, columns, rows, summary=None,
                     empty_message="No data available.", widths=None):
    """Show a report as its own full page (table), not a popup."""
    clear_screen()
    create_navigation()

    top = tk.Frame(root)
    top.pack(fill="x", padx=25, pady=(15, 5))

    tk.Label(
        top,
        text=title,
        font=("Segoe UI", 24, "bold")
    ).pack(side="left")

    tk.Button(
        top,
        text="BACK TO ANALYSIS",
        width=20,
        command=show_analysis
    ).pack(side="right")

    if summary:
        box = tk.Frame(root, bd=1, relief="solid")
        box.pack(fill="x", padx=25, pady=10)

        for label, value in summary:
            line = tk.Frame(box)
            line.pack(fill="x", padx=15, pady=3)
            tk.Label(
                line, text=label + ":", width=22, anchor="w",
                font=("Segoe UI", 12, "bold")
            ).pack(side="left")
            tk.Label(
                line, text=str(value), anchor="w",
                font=("Segoe UI", 12)
            ).pack(side="left")

    if columns is None:
        return

    if not rows:
        tk.Label(
            root,
            text=empty_message,
            font=("Segoe UI", 14)
        ).pack(pady=40)
        return

    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=25, pady=10)

    table = ttk.Treeview(frame, columns=columns, show="headings")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)

    for i, col in enumerate(columns):
        table.heading(col, text=col)
        table.column(
            col,
            width=(widths[i] if widths else 160),
            anchor="center"
        )

    for row in rows:
        table.insert("", "end", values=row)

    table.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")


def show_low_stock():
    conn = get_connection()
    rows = conn.execute("""
        SELECT product_id, name, category, available_quantity
        FROM products
        WHERE available_quantity < 5
        ORDER BY available_quantity ASC
    """).fetchall()
    conn.close()

    data = [
        (pid, name, category, qty, "OUT OF STOCK" if qty <= 0 else "LOW")
        for pid, name, category, qty in rows
    ]

    show_report_page(
        "LOW STOCK PRODUCTS",
        ("ID", "Product", "Category", "Units Remaining", "Status"),
        data,
        summary=[
            ("Threshold", "Below 5 units"),
            ("Products affected", len(data))
        ],
        empty_message="No products are currently below the 5-unit threshold.",
        widths=[80, 240, 180, 150, 150]
    )


def show_best_seller():
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.name, p.category, SUM(si.quantity) AS total_sold,
               SUM(si.quantity * si.unit_price) AS revenue
        FROM sale_items si
        JOIN products p ON si.product_id=p.product_id
        GROUP BY si.product_id
        ORDER BY total_sold DESC
        LIMIT 10
    """).fetchall()
    conn.close()

    data = [
        (i, name, category, sold, f"₹{revenue:.2f}")
        for i, (name, category, sold, revenue) in enumerate(rows, start=1)
    ]

    summary = None
    if rows:
        summary = [
            ("Best-selling product", rows[0][0]),
            ("Units sold", rows[0][2])
        ]

    show_report_page(
        "BEST SELLERS",
        ("Rank", "Product", "Category", "Units Sold", "Revenue"),
        data,
        summary=summary,
        empty_message="No sales recorded yet.",
        widths=[70, 260, 180, 130, 150]
    )


def show_total_sales():
    conn = get_connection()
    stats = conn.execute("""
        SELECT COALESCE(SUM(total_bill),0),
               COUNT(*),
               COALESCE(SUM(COALESCE(discount,0)),0),
               COALESCE(SUM(COALESCE(gst,0)),0)
        FROM sales
    """).fetchone()

    daily = conn.execute("""
        SELECT substr(timestamp,1,10) AS day,
               COUNT(*),
               SUM(total_bill)
        FROM sales
        GROUP BY day
        ORDER BY day DESC
    """).fetchall()
    conn.close()

    total, count, discount, gst = stats
    average = total / count if count else 0

    data = [(day, n, f"₹{amount:.2f}") for day, n, amount in daily]

    show_report_page(
        "TOTAL SALES",
        ("Date", "Transactions", "Sales Amount"),
        data,
        summary=[
            ("Cumulative sales", f"₹{total:.2f}"),
            ("Total transactions", count),
            ("Average bill", f"₹{average:.2f}"),
            ("Total discount given", f"₹{discount:.2f}"),
            ("Total GST collected", f"₹{gst:.2f}")
        ],
        empty_message="No sales recorded yet.",
        widths=[220, 200, 220]
    )


# =========================================================
# START
# =========================================================

init_db()
show_login()
root.mainloop()

