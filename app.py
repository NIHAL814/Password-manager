import customtkinter as ctk
import random
import string
import sqlite3
from tkinter import messagebox
from cryptography.fernet import Fernet
import os
import csv
import shutil

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "SafeKey Pro - Secure Password Manager"

# ---------------- ENCRYPTION ---------------- #

if not os.path.exists("secret.key"):
    key = Fernet.generate_key()
    with open("secret.key", "wb") as f:
        f.write(key)

with open("secret.key", "rb") as f:
    key = f.read()

fernet = Fernet(key)

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("passwords.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS passwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    website TEXT,
    username TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    master_password TEXT
)
""")

conn.commit()

# ---------------- MASTER PASSWORD INIT ---------------- #

cursor.execute("SELECT master_password FROM settings WHERE id=1")
result = cursor.fetchone()

if not result:
    default_master = fernet.encrypt("admin123".encode()).decode()
    cursor.execute("INSERT INTO settings (id, master_password) VALUES (1, ?)", (default_master,))
    conn.commit()

def verify_master(input_password):
    cursor.execute("SELECT master_password FROM settings WHERE id=1")
    stored = cursor.fetchone()[0]
    decrypted = fernet.decrypt(stored.encode()).decode()
    return input_password == decrypted

def change_master(new_password):
    encrypted = fernet.encrypt(new_password.encode()).decode()
    cursor.execute("UPDATE settings SET master_password=? WHERE id=1", (encrypted,))
    conn.commit()

# ---------------- LOGIN WINDOW ---------------- #

def login():
    if verify_master(login_entry.get()):
        login_window.destroy()
        open_main()
    else:
        messagebox.showerror("Error", "Wrong Master Password")

login_window = ctk.CTk()
login_window.geometry("400x280")
login_window.title(APP_NAME)
login_window.iconbitmap("icon.ico")

ctk.CTkLabel(login_window, text="SafeKey Pro", font=("Arial", 22)).pack(pady=20)

login_entry = ctk.CTkEntry(login_window, show="*", width=250, placeholder_text="Master Password")
login_entry.pack(pady=10)

ctk.CTkButton(login_window, text="Login", command=login).pack(pady=15)

# ---------------- MAIN APP ---------------- #

def open_main():
    app = ctk.CTk()
    app.geometry("750x800")
    app.title(APP_NAME)
    app.iconbitmap("icon.ico")

    ctk.CTkLabel(app, text="SafeKey Pro", font=("Arial", 26)).pack(pady=20)

    # -------- INPUT FRAME -------- #
    input_frame = ctk.CTkFrame(app)
    input_frame.pack(pady=10, padx=20, fill="x")

    website_entry = ctk.CTkEntry(input_frame, placeholder_text="Website")
    website_entry.pack(pady=5, padx=20, fill="x")

    username_entry = ctk.CTkEntry(input_frame, placeholder_text="Username")
    username_entry.pack(pady=5, padx=20, fill="x")

    password_entry = ctk.CTkEntry(input_frame, show="*")
    password_entry.pack(pady=5, padx=20, fill="x")

    show_var = ctk.BooleanVar()

    def toggle_password():
        password_entry.configure(show="" if show_var.get() else "*")

    ctk.CTkCheckBox(input_frame, text="Show Password",
                    variable=show_var,
                    command=toggle_password).pack(pady=5)

    # -------- STRENGTH -------- #

    strength_label = ctk.CTkLabel(app, text="")
    strength_label.pack()

    def check_strength(pw):
        if len(pw) < 8:
            return "Weak"
        elif len(pw) < 14:
            return "Medium"
        else:
            return "Strong"

    # -------- SLIDER -------- #

    length_label = ctk.CTkLabel(app, text="Password Length: 12")
    length_label.pack(pady=5)

    def update_length(value):
        length_label.configure(text=f"Password Length: {int(value)}")

    slider = ctk.CTkSlider(app, from_=6, to=32, command=update_length)
    slider.set(12)
    slider.pack(pady=10)

    # -------- GENERATE -------- #

    def generate_password():
        length = int(slider.get())
        characters = string.ascii_letters + string.digits + string.punctuation
        pw = "".join(random.choice(characters) for _ in range(length))
        password_entry.delete(0, "end")
        password_entry.insert(0, pw)
        strength_label.configure(text=f"Strength: {check_strength(pw)}")

    # -------- SAVE -------- #

    def save_password():
        website = website_entry.get()
        username = username_entry.get()
        password = password_entry.get()

        if website and username and password:
            encrypted = fernet.encrypt(password.encode()).decode()
            cursor.execute("INSERT INTO passwords (website, username, password) VALUES (?, ?, ?)",
                           (website, username, encrypted))
            conn.commit()
            backup_database()
            messagebox.showinfo("Saved", "Password Saved Securely")
        else:
            messagebox.showwarning("Warning", "Fill all fields")

    # -------- BACKUP -------- #

    def backup_database():
        shutil.copy("passwords.db", "backup_passwords.db")

    # -------- EXPORT CSV -------- #

    def export_csv():
        cursor.execute("SELECT website, username, password FROM passwords")
        records = cursor.fetchall()

        with open("export_passwords.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Website", "Username", "Password"])
            for record in records:
                decrypted = fernet.decrypt(record[2].encode()).decode()
                writer.writerow([record[0], record[1], decrypted])

        messagebox.showinfo("Exported", "Passwords exported to export_passwords.csv")

    # -------- VIEW + SEARCH + DELETE -------- #

    def open_saved_window():
        window = ctk.CTkToplevel(app)
        window.geometry("700x500")
        window.title("Saved Passwords")
        window.iconbitmap("icon.ico")

        search_entry = ctk.CTkEntry(window, placeholder_text="Search by website")
        search_entry.pack(pady=10, padx=20, fill="x")

        scroll_frame = ctk.CTkScrollableFrame(window)
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        def load_data(filter_text=""):
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            if filter_text:
                cursor.execute("SELECT id, website, username, password FROM passwords WHERE website LIKE ?",
                               ('%' + filter_text + '%',))
            else:
                cursor.execute("SELECT id, website, username, password FROM passwords")

            records = cursor.fetchall()

            for record in records:
                decrypted = fernet.decrypt(record[3].encode()).decode()
                text = f"{record[1]} | {record[2]} | {decrypted}"

                frame = ctk.CTkFrame(scroll_frame)
                frame.pack(fill="x", pady=5)

                ctk.CTkLabel(frame, text=text, anchor="w").pack(side="left", padx=10)

                def delete_record(record_id=record[0]):
                    cursor.execute("DELETE FROM passwords WHERE id=?", (record_id,))
                    conn.commit()
                    load_data()

                ctk.CTkButton(frame, text="Delete", width=70,
                              command=delete_record).pack(side="right", padx=5)

        def search():
            load_data(search_entry.get())

        ctk.CTkButton(window, text="Search", command=search).pack(pady=5)

        load_data()

    # -------- CHANGE MASTER -------- #

    def open_change_master():
        window = ctk.CTkToplevel(app)
        window.geometry("400x250")
        window.title("Change Master Password")
        window.iconbitmap("icon.ico")

        new_entry = ctk.CTkEntry(window, placeholder_text="New Master Password")
        new_entry.pack(pady=20)

        def update_master():
            if new_entry.get():
                change_master(new_entry.get())
                messagebox.showinfo("Success", "Master Password Changed")
                window.destroy()

        ctk.CTkButton(window, text="Update", command=update_master).pack(pady=10)

    # -------- BUTTON FRAME -------- #

    button_frame = ctk.CTkFrame(app)
    button_frame.pack(pady=20)

    ctk.CTkButton(button_frame, text="Generate", command=generate_password).grid(row=0, column=0, padx=10)
    ctk.CTkButton(button_frame, text="Save", command=save_password).grid(row=0, column=1, padx=10)
    ctk.CTkButton(button_frame, text="View Saved", command=open_saved_window).grid(row=0, column=2, padx=10)
    ctk.CTkButton(button_frame, text="Export CSV", command=export_csv).grid(row=0, column=3, padx=10)
    ctk.CTkButton(button_frame, text="Change Master", command=open_change_master).grid(row=0, column=4, padx=10)

    app.mainloop()

login_window.mainloop()