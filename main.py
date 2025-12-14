import flet as ft

def main(page: ft.Page):
    page.title = "My First Python App"
    page.add(ft.Text(value="Hello, World!", size=30))

ft.app(target=main)