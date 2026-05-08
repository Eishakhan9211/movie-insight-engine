import tkinter as tk

root = tk.Tk()
root.title("Test")
root.geometry("300x200")

label = tk.Label(root, text="If you see this window, Tkinter works!")
label.pack(pady=50)

root.mainloop()