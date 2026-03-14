"""
Gestor de Tareas con Temporizador - Flet App
============================================
Arquitectura modular con separación de responsabilidades:
  - Tarea       → Modelo de datos
  - Temporizador → Lógica de conteo
  - TareaWidget → Componente visual por tarea
  - AppInterfaz  → Orquestador de la UI
"""

import flet as ft
import threading
import time


# ─────────────────────────────────────────────
# CAPA 1: MODELO DE DATOS
# ─────────────────────────────────────────────

class Temporizador:
    """
    Maneja el conteo regresivo de una tarea.
    Corre en un hilo separado para no bloquear la UI.
    """

    def __init__(self, minutos: int, callback_tick, callback_fin):
        self.tiempo_total     = minutos * 60          # segundos totales
        self.tiempo_restante  = self.tiempo_total
        self.activo           = False
        self._hilo            = None
        self._callback_tick   = callback_tick   # se llama cada segundo
        self._callback_fin    = callback_fin    # se llama al llegar a 0

    # ── Controles ──────────────────────────────

    def iniciar(self):
        """Arranca o reanuda el conteo."""
        if self.activo or self.tiempo_restante <= 0:
            return
        self.activo = True
        self._hilo  = threading.Thread(target=self._correr, daemon=True)
        self._hilo.start()

    def pausar(self):
        """Detiene el conteo sin reiniciar el tiempo."""
        self.activo = False

    def reiniciar(self):
        """Vuelve al tiempo original y detiene el conteo."""
        self.activo          = False
        self.tiempo_restante = self.tiempo_total

    # ── Helpers ────────────────────────────────

    def _correr(self):
        """Bucle interno que decrementa cada segundo."""
        while self.activo and self.tiempo_restante > 0:
            time.sleep(1)
            if self.activo:
                self.tiempo_restante -= 1
                self._callback_tick()
        if self.tiempo_restante <= 0:
            self.activo = False
            self._callback_fin()

    def formato_mm_ss(self) -> str:
        """Devuelve el tiempo restante como 'MM:SS'."""
        m, s = divmod(max(self.tiempo_restante, 0), 60)
        return f"{m:02d}:{s:02d}"


class Tarea:
    """
    Modelo de una tarea con sus metadatos y temporizador opcional.
    """

    def __init__(
        self,
        nombre:          str,
        categoria:       str  = "General",
        tiempo_estimado: int  = 25,        # minutos
        usar_temporizador: bool = False,
    ):
        self.nombre           = nombre
        self.categoria        = categoria
        self.tiempo_estimado  = tiempo_estimado
        self.completada       = False
        self.usar_temporizador = usar_temporizador
        self.temporizador: Temporizador | None = None

    # ── Métodos de negocio ─────────────────────

    def marcar_completada(self):
        self.completada = True
        if self.temporizador:
            self.temporizador.pausar()

    def desmarcar_completada(self):
        self.completada = False

    def activar_temporizador(self, callback_tick, callback_fin):
        """Crea e inicia el temporizador si no existe ya."""
        self.usar_temporizador = True
        if self.temporizador is None:
            self.temporizador = Temporizador(
                self.tiempo_estimado, callback_tick, callback_fin
            )

    def desactivar_temporizador(self):
        """Detiene y elimina el temporizador."""
        self.usar_temporizador = False
        if self.temporizador:
            self.temporizador.pausar()
            self.temporizador = None


# ─────────────────────────────────────────────
# CAPA 2: COMPONENTE VISUAL DE UNA TAREA
# ─────────────────────────────────────────────

class TareaWidget:
    """
    Construye y gestiona el widget Flet de una sola tarea.
    Encapsula toda la lógica de renderizado y eventos de esa tarea.
    """

    # Paleta de colores
    COLOR_FONDO        = "#1E1E2E"
    COLOR_SUPERFICIE   = "#2A2A3E"
    COLOR_ACENTO       = "#7C3AED"
    COLOR_ACENTO_SUAVE = "#A78BFA"
    COLOR_TEXTO        = "#E2E8F0"
    COLOR_MUTED        = "#94A3B8"
    COLOR_EXITO        = "#10B981"
    COLOR_PELIGRO      = "#EF4444"
    COLOR_TIMER        = "#F59E0B"

    def __init__(self, tarea: "Tarea", app: "AppInterfaz"):
        self.tarea = tarea
        self.app   = app

        # Controles internos que necesitamos referenciar
        self._lbl_tiempo  = ft.Text("", color=self.COLOR_TIMER, weight=ft.FontWeight.BOLD, size=13)
        self._fila_timer  = ft.Row(visible=False, spacing=4)
        self._container   = self._construir()

    # ── Construcción ───────────────────────────

    def _construir(self) -> ft.Container:
        t = self.tarea

        # Checkbox de completado
        chk = ft.Checkbox(
            value=t.completada,
            on_change=self._toggle_completada,
            active_color=self.COLOR_EXITO,
            check_color="#FFFFFF",
        )

        # Nombre y categoría
        col_info = ft.Column(
            [
                ft.Text(t.nombre,    size=15, weight=ft.FontWeight.W_600,
                        color=self.COLOR_TEXTO),
                ft.Text(t.categoria, size=11, color=self.COLOR_MUTED,
                        italic=True),
            ],
            spacing=1,
            expand=True,
        )

        # Controles del temporizador
        btn_play    = ft.IconButton(ft.Icons.PLAY_ARROW,
                                    icon_color=self.COLOR_EXITO,   icon_size=18,
                                    tooltip="Iniciar", on_click=self._timer_iniciar)
        btn_pausa   = ft.IconButton(ft.Icons.PAUSE,
                                    icon_color=self.COLOR_TIMER,   icon_size=18,
                                    tooltip="Pausar", on_click=self._timer_pausar)
        btn_reset   = ft.IconButton(ft.Icons.REFRESH,
                                    icon_color=self.COLOR_MUTED,   icon_size=18,
                                    tooltip="Reiniciar", on_click=self._timer_reiniciar)
        self._lbl_tiempo.value = self._tiempo_texto()
        self._fila_timer.controls = [
            ft.Icon(ft.Icons.TIMER, color=self.COLOR_TIMER, size=16),
            self._lbl_tiempo,
            btn_play, btn_pausa, btn_reset,
        ]
        self._fila_timer.visible = t.usar_temporizador

        # Toggle para activar/desactivar temporizador
        sw_timer = ft.Switch(
            value=t.usar_temporizador,
            label="⏱",
            label_text_style=ft.TextStyle(color=self.COLOR_MUTED, size=12),
            active_color=self.COLOR_ACENTO,
            on_change=self._toggle_timer,
        )

        # Botón eliminar
        btn_del = ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            icon_color=self.COLOR_PELIGRO,
            icon_size=18,
            tooltip="Eliminar tarea",
            on_click=self._eliminar,
        )

        fila_principal = ft.Row(
            [chk, col_info, sw_timer, btn_del],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        contenido = ft.Column(
            [fila_principal, self._fila_timer],
            spacing=4,
        )

        return ft.Container(
            content=contenido,
            bgcolor=self.COLOR_SUPERFICIE,
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border=ft.border.all(1, "#3A3A5C"),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    # ── Helpers ────────────────────────────────

    def _tiempo_texto(self) -> str:
        if self.tarea.temporizador:
            return self.tarea.temporizador.formato_mm_ss()
        m = self.tarea.tiempo_estimado
        return f"{m:02d}:00"

    def _refrescar_tiempo(self):
        """Llamado cada segundo por el temporizador."""
        self._lbl_tiempo.value = self._tiempo_texto()
        self.app.page.update()

    def _on_fin_timer(self):
        """Llamado cuando el temporizador llega a cero."""
        self._lbl_tiempo.value = "✓ 00:00"
        self.app.page.snack_bar = ft.SnackBar(
            ft.Text(f'⏰ Tiempo completado: "{self.tarea.nombre}"',
                    color="#FFFFFF"),
            bgcolor=self.COLOR_ACENTO,
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()

    # ── Manejadores de eventos ─────────────────

    def _toggle_completada(self, e):
        if e.control.value:
            self.tarea.marcar_completada()
        else:
            self.tarea.desmarcar_completada()
        # Actualiza opacidad del container
        self._container.opacity = 0.5 if self.tarea.completada else 1.0
        self.app.page.update()

    def _toggle_timer(self, e):
        if e.control.value:
            self.tarea.activar_temporizador(
                callback_tick=self._refrescar_tiempo,
                callback_fin=self._on_fin_timer,
            )
        else:
            self.tarea.desactivar_temporizador()
        self._fila_timer.visible = self.tarea.usar_temporizador
        self._lbl_tiempo.value   = self._tiempo_texto()
        self.app.page.update()

    def _timer_iniciar(self, _):
        if self.tarea.temporizador:
            self.tarea.temporizador.iniciar()

    def _timer_pausar(self, _):
        if self.tarea.temporizador:
            self.tarea.temporizador.pausar()

    def _timer_reiniciar(self, _):
        if self.tarea.temporizador:
            self.tarea.temporizador.reiniciar()
            self._lbl_tiempo.value = self._tiempo_texto()
            self.app.page.update()

    def _eliminar(self, _):
        self.app.eliminar_tarea(self)

    # ── Propiedad de control Flet ──────────────

    @property
    def control(self) -> ft.Container:
        return self._container


# ─────────────────────────────────────────────
# CAPA 3: INTERFAZ / ORQUESTADOR
# ─────────────────────────────────────────────

class AppInterfaz:
    """
    Orquesta la interfaz completa: configura la página, crea componentes
    y maneja la lista de tareas.
    """

    # Paleta (misma que TareaWidget para coherencia)
    COLOR_FONDO      = "#1E1E2E"
    COLOR_SUPERFICIE = "#2A2A3E"
    COLOR_ACENTO     = "#7C3AED"
    COLOR_TEXTO      = "#E2E8F0"
    COLOR_MUTED      = "#94A3B8"
    COLOR_EXITO      = "#10B981"

    CATEGORIAS = ["General", "Trabajo", "Estudio", "Hogar", "Salud", "Personal"]

    def __init__(self, page: ft.Page):
        self.page          = page
        self.lista_tareas: list[TareaWidget] = []

        # Campos del formulario (se inicializan en _crear_componentes)
        self._tf_nombre:   ft.TextField   = None
        self._tf_minutos:  ft.TextField   = None
        self._dd_categoria: ft.Dropdown  = None
        self._sw_timer:    ft.Switch      = None
        self._col_lista:   ft.Column     = None

        self._setup_page()
        self._crear_componentes()
        self._construir_ui()

    # ── Configuración de página ────────────────

    def _setup_page(self):
        self.page.title            = "✅ Gestor de Tareas"
        self.page.bgcolor          = self.COLOR_FONDO
        self.page.window_width     = 520
        self.page.window_height    = 760
        self.page.window_resizable = True
        self.page.fonts = {
            "Sora": "https://fonts.gstatic.com/s/sora/v12/xMQbuFFYT72X5wkB_18qmnndmDs.woff2",
        }
        self.page.theme = ft.Theme(font_family="Sora")
        self.page.padding = 0

    # ── Creación de componentes ────────────────

    def _crear_componentes(self):
        """Instancia todos los controles del formulario."""

        self._tf_nombre = ft.TextField(
            hint_text="Nombre de la tarea…",
            bgcolor=self.COLOR_SUPERFICIE,
            border_color="#3A3A5C",
            focused_border_color=self.COLOR_ACENTO,
            color=self.COLOR_TEXTO,
            hint_style=ft.TextStyle(color=self.COLOR_MUTED),
            border_radius=10,
            expand=True,
        )

        self._tf_minutos = ft.TextField(
            hint_text="min",
            value="25",
            bgcolor=self.COLOR_SUPERFICIE,
            border_color="#3A3A5C",
            focused_border_color=self.COLOR_ACENTO,
            color=self.COLOR_TEXTO,
            hint_style=ft.TextStyle(color=self.COLOR_MUTED),
            border_radius=10,
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self._dd_categoria = ft.Dropdown(
            options=[ft.DropdownOption(c) for c in self.CATEGORIAS],
            value="General",
            bgcolor=self.COLOR_SUPERFICIE,
            border_color="#3A3A5C",
            focused_border_color=self.COLOR_ACENTO,
            color=self.COLOR_TEXTO,
            border_radius=10,
            width=140,
        )

        self._sw_timer = ft.Switch(
            label="⏱ Timer",
            label_text_style=ft.TextStyle(color=self.COLOR_MUTED, size=12),
            active_color=self.COLOR_ACENTO,
            value=False,
        )

        self._col_lista = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── Construcción de la UI ──────────────────

    def _construir_ui(self):
        """Ensambla y monta todos los controles en la página."""

        # ── Encabezado ──
        header = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE,
                                    color=self.COLOR_ACENTO, size=28),
                            ft.Text("Gestor de Tareas",
                                    size=22, weight=ft.FontWeight.BOLD,
                                    color=self.COLOR_TEXTO),
                        ],
                        spacing=10,
                    ),
                    ft.Text("Organiza tu día, una tarea a la vez.",
                            size=12, color=self.COLOR_MUTED, italic=True),
                ],
                spacing=4,
            ),
            padding=ft.padding.only(left=20, right=20, top=28, bottom=16),
        )

        # ── Formulario ──
        btn_agregar = ft.ElevatedButton(
            "Agregar",
            icon=ft.Icons.ADD,
            bgcolor=self.COLOR_ACENTO,
            color="#FFFFFF",
            on_click=self._on_agregar,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        )

        formulario = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self._tf_nombre, self._tf_minutos], spacing=8),
                    ft.Row(
                        [self._dd_categoria, self._sw_timer, btn_agregar],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=10,
            ),
            bgcolor=self.COLOR_SUPERFICIE,
            border_radius=14,
            padding=16,
            border=ft.border.all(1, "#3A3A5C"),
            margin=ft.margin.symmetric(horizontal=16),
        )

        # ── Sección de lista ──
        lbl_tareas = ft.Container(
            content=ft.Row(
                [
                    ft.Text("Tareas", size=14, weight=ft.FontWeight.W_600,
                            color=self.COLOR_MUTED),
                    ft.Container(expand=True),
                    ft.Text("", key="contador", size=12, color=self.COLOR_MUTED),
                ],
            ),
            padding=ft.padding.only(left=20, right=20, top=20, bottom=6),
        )

        lista_container = ft.Container(
            content=self._col_lista,
            padding=ft.padding.symmetric(horizontal=16),
            expand=True,
        )

        # ── Footer ──
        footer = ft.Container(
            content=ft.Text(
                "Hecho con ❤ y Flet",
                size=11, color=self.COLOR_MUTED, italic=True,
                text_align=ft.TextAlign.CENTER,
            ),
            padding=ft.padding.only(bottom=12, top=8),
            alignment=ft.Alignment.CENTER,
        )

        # ── Layout raíz ──
        self.page.add(
            ft.Column(
                [header, formulario, lbl_tareas, lista_container, footer],
                expand=True,
                spacing=0,
            )
        )

    # ── Lógica de negocio de la UI ─────────────

    def agregar_tarea(self, tarea: Tarea):
        """Crea el widget y lo añade a la lista visual."""
        widget = TareaWidget(tarea, self)
        if tarea.usar_temporizador:
            tarea.activar_temporizador(
                callback_tick=widget._refrescar_tiempo,
                callback_fin=widget._on_fin_timer,
            )
        self.lista_tareas.append(widget)
        self._col_lista.controls.append(widget.control)
        self._actualizar_interfaz()

    def eliminar_tarea(self, widget: TareaWidget):
        """Elimina una tarea de la lista."""
        widget.tarea.desactivar_temporizador()
        self._col_lista.controls.remove(widget.control)
        self.lista_tareas.remove(widget)
        self._actualizar_interfaz()

    def _actualizar_interfaz(self):
        """Refresca el contador y la página."""
        total      = len(self.lista_tareas)
        completadas = sum(1 for w in self.lista_tareas if w.tarea.completada)
        # Actualiza el texto del contador (buscamos por key)
        for ctrl in self.page.controls[0].controls:
            if isinstance(ctrl, ft.Container) and ctrl.content:
                fila = ctrl.content
                if isinstance(fila, ft.Row):
                    for c in fila.controls:
                        if isinstance(c, ft.Text) and c.key == "contador":
                            c.value = f"{completadas}/{total} completadas"
        self.page.update()

    # ── Manejadores de formulario ──────────────

    def _on_agregar(self, _):
        nombre = self._tf_nombre.value.strip()
        if not nombre:
            self._tf_nombre.error_text = "Escribe un nombre"
            self.page.update()
            return

        self._tf_nombre.error_text = None

        try:
            minutos = int(self._tf_minutos.value or "25")
            minutos = max(1, min(minutos, 999))
        except ValueError:
            minutos = 25

        tarea = Tarea(
            nombre           = nombre,
            categoria        = self._dd_categoria.value or "General",
            tiempo_estimado  = minutos,
            usar_temporizador = self._sw_timer.value,
        )

        self.agregar_tarea(tarea)

        # Limpia el formulario
        self._tf_nombre.value  = ""
        self._sw_timer.value   = False
        self._tf_minutos.value = "25"
        self.page.update()


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

def main(page: ft.Page):
    AppInterfaz(page)


if __name__ == "__main__":
    ft.app(target=main)
