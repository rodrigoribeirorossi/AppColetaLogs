import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import time
import sys  # Import necessário para verificar a plataforma
import ctypes  # Import necessário para manipular o ícone na barra de tarefas
from ConfigServidores import SERVIDORES
from RemoteUtils import copiar_ultimos_logs_remotos, buscar_e_copiar_log_remoto
from PIL import Image, ImageTk # type: ignore
import logging
import os
from datetime import datetime
from tkinter import ttk
from ttkthemes import ThemedTk # type: ignore
import webbrowser

def resource_path(relative_path):
    """Retorna o caminho absoluto para recursos, compatível com PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Crie uma pasta de logs na área de trabalho do usuário
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
log_folder = os.path.join(desktop, "App Coleta Logs", "ConsoleLogs")
os.makedirs(log_folder, exist_ok=True)

# Nome do arquivo de log com data/hora
log_filename = os.path.join(log_folder, f"app_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")

# Configuração básica do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()  # Mantém prints no console também
    ]
)

# Redireciona print para logging.info automaticamente
print = lambda *args, **kwargs: logging.info(" ".join(str(a) for a in args))

# Importa o módulo de logs

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def update_text(self, text):
        self.text = text

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert") if self.widget.winfo_ismapped() else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, background="#fdfdf3", relief="solid", borderwidth=1, font=("Arial", 10))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class Application():
    def __init__(self, janela):
        print("Iniciando Application")
        self.janela = janela
        self.janela.title("[QA] App Coleta de Logs")
        self.janela.geometry("1200x800+500+50")
        self.janela.configure(bg="#f6f4f2")

        # Tema e estilos
        style = ttk.Style(janela)
        style.configure("TButton", font=("Arial", 12))
        style.map("TButton",
            focuscolor=[("focus", "#FF7300")],
            foreground=[("active", "#000000"), ("!active", "black")]
        )
        style.configure("Custom.TFrame", background="#f0f0f0")

        # Ícone
        icon_path = resource_path("files/vivo-gen.ico")
        self.janela.iconbitmap(icon_path)

        # Imagens globais
        self.info_icon = ImageTk.PhotoImage(Image.open(resource_path("files/information.png")).resize((28, 28)))
        self.sucesso_icon = ImageTk.PhotoImage(Image.open(resource_path("files/checkmark.png")).resize((28, 28)))
        self.erro_icon = ImageTk.PhotoImage(Image.open(resource_path("files/found-fail-removebg.png")).resize((28, 28)))
        self.loading_gif = self._carregar_gif(resource_path("files/load-orange.gif"))
        self.varredura_gif = self._carregar_gif(resource_path("files/load-orange.gif"))

        # Faixa fina laranja no topo
        self.faixa_top = tk.Frame(self.janela, bg="#FF7300", height=4)
        self.faixa_top.pack(fill="x", side="top")
        
        # Faixa branca superior (sempre visível)
        self.faixa_branca = tk.Frame(self.janela, bg="white", height=60)
        self.faixa_branca.pack(fill="x", side="top")

        # Imagem e título na faixa branca
        img_path = resource_path("files/vivo-neon-ctech-removebg.png")
        img = Image.open(img_path).resize((40, 40))
        self.img_inicio = ImageTk.PhotoImage(img)
        label_img = tk.Label(self.faixa_branca, image=self.img_inicio, bg="white", borderwidth=0)
        label_img.pack(side="left", padx=(10, 8), pady=8)
        label_titulo = tk.Label(
            self.faixa_branca,
            text="[QA] App Coleta de Logs                                                                                                     Genesys | Middleware",
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#222"
        )
        label_titulo.pack(side="left", padx=(0, 20), pady=8)

        # Cor para o fundo principal (conteúdo)
        cor_fundo_principal = "#f0f0f0"  # <-- ajuste aqui


        # Frame principal (apenas criado, não exibido)
        frame_principal = tk.Frame(self.janela, bg=cor_fundo_principal)
        frame_principal.pack(fill="both", expand=True)

        # Lateral (menu)
        cor_fundo_botao = style.lookup("TButton", "background") or "#f3e9df"
        largura_botao = 180
        largura_faixa = largura_botao + 40
        cor_menu_lateral = "#f0f4ff" #cor_fundo_botao # "#f4f6fd"  # cinza claro, ou use "#f0f4ff" para um azul suave
        self.frame_lateral = tk.Frame(frame_principal, bg=cor_menu_lateral, width=largura_faixa)
        self.frame_lateral.pack(side="left", fill="y")

        self.frame_opcoes = tk.Frame(self.frame_lateral, bg=cor_menu_lateral)
        self.frame_opcoes.pack(pady=(30, 0), padx=0, fill="y")

        # --- SCROLLABLE CONTENT ---
        # Canvas para permitir scroll
        self.canvas = tk.Canvas(frame_principal, bg=cor_fundo_principal, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Frame que conterá todo o conteúdo
        self.frame_conteudo = tk.Frame(self.canvas, bg=cor_fundo_principal)
        self.frame_conteudo_window = self.canvas.create_window((0, 0), window=self.frame_conteudo, anchor="nw")

        # Atualiza o scrollregion sempre que o conteúdo mudar de tamanho
        def on_frame_configure(event):
            bbox = self.canvas.bbox("all")
            if bbox:
                # Limita o scrollregion ao tamanho do conteúdo
                self.canvas.configure(scrollregion=(bbox[0], bbox[1], bbox[2], bbox[3]))

        self.frame_conteudo.bind("<Configure>", on_frame_configure)

        # Permite scroll com a roda do mouse
        def _on_mousewheel(event):
            # Obtém a posição atual do scroll (0.0 = topo, 1.0 = fundo)
            first, last = self.canvas.yview()
            direction = int(-1*(event.delta/120))
            # Só permite subir se não estiver no topo, e só permite descer se não estiver no fundo
            if direction < 0 and first <= 0:
                return  # Já está no topo, não sobe mais
            if direction > 0 and last >= 1:
                return  # Já está no fundo, não desce mais
            self.canvas.yview_scroll(direction, "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Ajusta a largura do frame_conteudo para sempre ocupar toda a largura do canvas
        def on_canvas_configure(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.frame_conteudo_window, width=canvas_width)

        self.canvas.bind("<Configure>", on_canvas_configure)

        # Conteúdo
        #self.frame_conteudo = tk.Frame(frame_principal, bg=cor_fundo_principal)
        #elf.frame_conteudo.pack(side="left", fill="both", expand=True)

        # Frames das interfaces (apenas criados, não exibidos)
        self.frame_inicio = ttk.Frame(self.frame_conteudo)
        self.frame_genesys = ttk.Frame(self.frame_conteudo)
        self.frame_middleware_menu = ttk.Frame(self.frame_conteudo)
        self.frame_menu_ndc = ttk.Frame(self.frame_conteudo)
        self.frame_menu_brn = ttk.Frame(self.frame_conteudo)
        self.frame_midias = ttk.Frame(self.frame_conteudo)
        self.frame_processamento = ttk.Frame(self.frame_conteudo)
        self.frame_roteamento = ttk.Frame(self.frame_conteudo)
        self.frame_voz = ttk.Frame(self.frame_conteudo)
        self.frame_framework = ttk.Frame(self.frame_conteudo)
        self.frame_relatorios = ttk.Frame(self.frame_conteudo)
        self.frame_busca_id = ttk.Frame(self.frame_conteudo)
        self.frame_middleware = ttk.Frame(self.frame_conteudo)
        self.frame_busca_id_middleware = ttk.Frame(self.frame_conteudo)

        # Dicionários de busca
        self.busca_id_to_app_ndc = {
            "Interaction ID": ["ixn_outros_ndc_p", "ixn_ndc_b", "ixn_ndc_p", "gms_ndc_p"],
            "Session ID": ["urs_voz_ndc_p", "urs_mm_ndc_p", "ors_mm_1_ndc_p", "ors_voz_1_ndc_p"],
            "ConnID": ["sipserver_agt_ndc_p", "sipserver_agt_ndc_b", "sipserver_agt_ndc_b", "sipserver_rtr_ndc_p"],
            "Calluuid": ["sipserver_agt_ndc_p", "sipserver_agt_ndc_b", "sipserver_agt_ndc_b", "sipserver_rtr_ndc_p"]    
        }

        self.busca_id_to_app_brn = {
            "Interaction ID": ["ixn_outros_brn_p", "ixn_brn_p", "ixn_email_brn_p", "gms_brn_p"],
            "Session ID": ["urs_voz_brn_p", "urs_mm_brn_p", "ors_mm_1_brn_p", "ors_voz_1_brn_p"],
            "ConnID": ["sipserver_agt_brn_p", "sipserver_rtr_brn_p"],
            "Calluuid": ["sipserver_agt_brn_p", "sipserver_rtr_brn_p"]
        }

        # Botões do menu lateral
        self._criar_botoes_laterais(largura_botao)

        # Crie a interface de início (adiciona widgets no frame_inicio)
        self.criar_interface_inicio()

        # Exiba a tela de início
        self.mostrar_interface_com_lateral(self.frame_inicio)

        
        if sys.platform == "win32":
            try:
                icon_path = resource_path("files/vivo-gen.ico")
                self.janela.iconbitmap(icon_path)
                # Força o ícone na barra de tarefas do Windows
                try:
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"myappid")
                    self.janela.iconbitmap(icon_path)
                except Exception as e:
                    print("Erro ao forçar ícone na barra de tarefas:", e)
            except Exception as e:
                print("Erro ao forçar atualização do ícone:", e)
        
        print("Application inicializada com sucesso")
    
    def mostrar_interface_com_lateral(self, frame_interface):
        """Exibe a interface no frame de conteúdo, mantendo a faixa lateral fixa."""
        for widget in self.frame_conteudo.winfo_children():
            widget.pack_forget()
            widget.grid_forget()
        frame_interface.pack_forget()
        frame_interface.pack(fill="both", expand=True)
    # NÃO chame self.mostrar_interface_com_lateral(self.frame_inicio) aqui!

    def adicionar_cabecalho_padrao(self, frame, titulo, img_path=None, img_size=(36, 36)):
        self.limpar_frame(frame)
        cabecalho = tk.Frame(frame, bg="white", height=50)  # altura padronizada
        cabecalho.pack(fill="x", pady=(10, 0))
        cabecalho.pack_propagate(False)  # impede que o frame diminua de tamanho

        # Use imagem padrão se não for passado outro caminho
        if img_path is None:
            img_path = resource_path("files/genesys-log-fundo-branco-removebg-preview.png")
        self.cabecalho_icon = ImageTk.PhotoImage(Image.open(img_path).resize(img_size))
        label_icon = tk.Label(cabecalho, image=self.cabecalho_icon, bg="white", borderwidth=0)
        label_icon.pack(side="left", padx=(10, 8))

        label_titulo = tk.Label(cabecalho, text=titulo, font=("Arial", 16, "bold"), bg="white", fg="#222")
        label_titulo.pack(side="left", padx=10)

    def mostrar_frame(self, frame):
        """Exibe o frame especificado e oculta os outros."""
        for widget in self.janela.winfo_children():
            widget.pack_forget()
        frame.pack(fill="both", expand=True)

    def limpar_frame(self, frame):
        """Remove todos os widgets de um frame."""
        for widget in frame.winfo_children():
            widget.destroy()

    def criar_interface_genesys(self):
        """Cria a interface (Genesys)."""
        self.limpar_frame(self.frame_genesys)
        self.adicionar_cabecalho_padrao(self.frame_genesys, titulo="Menu Genesys")

        # Frame horizontal para ícone + título (agora opcional, pois já tem cabeçalho)
        # linha_titulo = ttk.Frame(self.frame_genesys)
        # linha_titulo.pack(pady=20)
        # icon_img = Image.open(resource_path("files/genesys-log-fundo-branco-removebg-preview.png"))
        # self.home_icon = ImageTk.PhotoImage(icon_img.resize((48, 48)))
        # label_icon = ttk.Label(linha_titulo, image=self.home_icon)
        # label_icon.pack(side="left", padx=(0, 10))
        # label_home = ttk.Label(linha_titulo, text="Menu de Logs Genesys - QA", font=("Arial", 14, "bold"))
        # label_home.pack(side="left")
        
        
        label_sub = ttk.Label(self.frame_genesys, text="Escolha o ambiente que deseja acessar:", font=("Arial", 12))
        label_sub.pack(pady=20)
        
        botao_ir_para_ndc = ttk.Button(self.frame_genesys, text="Menu NDC", command=lambda:  [self.criar_menu_ndc(), self.mostrar_interface_com_lateral(self.frame_menu_ndc)])
        botao_ir_para_ndc.pack(pady=10)

        botao_ir_para_brn = ttk.Button(self.frame_genesys, text="Menu BRN", command=lambda: [self.criar_menu_brn(), self.mostrar_interface_com_lateral(self.frame_menu_brn)])
        botao_ir_para_brn.pack(pady=10)

        botao_busca_id = ttk.Button(self.frame_genesys, text="Busca por ID", command=lambda:  [self.criar_interface_busca_id(), self.mostrar_interface_com_lateral(self.frame_busca_id)])
        botao_busca_id.pack(pady=10)

        largura_botao = 20
        botao_voltar_inicio = ttk.Button(
            self.frame_genesys,
            text="← Início",
            width=largura_botao,
            command=lambda: [self.criar_interface_inicio(), self.mostrar_interface_com_lateral(self.frame_inicio)]
        )
        botao_voltar_inicio.pack(pady=20)
        #self.mostrar_interface_com_lateral(self.frame_genesys)
        # Botão de voltar para Home com seta para a esquerda

    def criar_interface_middleware_menu(self):
        self.limpar_frame(self.frame_middleware_menu)
        img_path = resource_path("files/md-fundo-removebg-preview.png")
        self.adicionar_cabecalho_padrao(self.frame_middleware_menu, titulo="Menu Middleware", img_path=img_path)

        label_sub = ttk.Label(self.frame_middleware_menu, text="Escolha o ambiente do Middleware:", font=("Arial", 12))
        label_sub.pack(pady=20)

        ambientes = [
            ("CC Interaction Integration", lambda: [self.criar_interface_middleware("cc_interaction_integration"), self.mostrar_interface_com_lateral(self.frame_middleware)]),
            ("CC Business Integration", lambda: [self.criar_interface_middleware("cc_business_integration"), self.mostrar_interface_com_lateral(self.frame_middleware)]),
        ]

        for nome, comando in ambientes:
            ttk.Button(self.frame_middleware_menu, text=nome, width=24, command=comando).pack(pady=10)

        # --- Novo botão Busca por ID Middleware ---
        ttk.Button(
            self.frame_middleware_menu,
            text="Busca por ID",
            width=24,
            command=lambda: [self.criar_interface_busca_id_middleware(), self.mostrar_interface_com_lateral(self.frame_busca_id_middleware)]
        ).pack(pady=10)

        botao_voltar_inicio = ttk.Button(
            self.frame_middleware_menu,
            text="← Início",
            width=14,
            command=lambda: [self.criar_interface_inicio(), self.mostrar_interface_com_lateral(self.frame_inicio)]
        )
        botao_voltar_inicio.pack(pady=20)

    def criar_menu_ndc(self):
        """Cria o menu NDC."""
        self.limpar_frame(self.frame_menu_ndc)
        self.adicionar_cabecalho_padrao(self.frame_menu_ndc, titulo="Menu NDC")

        #label_menu_ndc = ttk.Label(self.frame_menu_ndc, text="Menu NDC", font=("Arial", 14, "bold"))
        #label_menu_ndc.pack(pady=20)

        label_instrucao = ttk.Label(self.frame_menu_ndc, text="Escolha a camada onde esta a aplicação desejada:", font=("Arial", 12))
        label_instrucao.pack(pady=(10, 20))

        largura_botao = 14

        botao_midias = ttk.Button(self.frame_menu_ndc, text="Mídias", width=largura_botao, command=lambda: [self.criar_interface_midias("NDC"), self.mostrar_interface_com_lateral(self.frame_midias)])
        botao_midias.pack(pady=10, padx=40)

        botao_processamento = ttk.Button(self.frame_menu_ndc, text="Processamento", width=largura_botao, command=lambda: [self.criar_interface_processamento("NDC"), self.mostrar_interface_com_lateral(self.frame_processamento)])
        botao_processamento.pack(pady=10, padx=40)

        botao_roteamento = ttk.Button(self.frame_menu_ndc, text="Roteamento", width=largura_botao, command=lambda: [self.criar_interface_roteamento("NDC"), self.mostrar_interface_com_lateral(self.frame_roteamento)])
        botao_roteamento.pack(pady=10, padx=40)

        botao_voz = ttk.Button(self.frame_menu_ndc, text="Voz", width=largura_botao, command=lambda: [self.criar_interface_voz("NDC"), self.mostrar_interface_com_lateral(self.frame_voz)])
        botao_voz.pack(pady=10, padx=40)

        botao_framework = ttk.Button(self.frame_menu_ndc, text="Framework", width=largura_botao, command=lambda: [self.criar_interface_framework("NDC"), self.mostrar_interface_com_lateral(self.frame_framework)])
        botao_framework.pack(pady=10, padx=40)

        botao_relatorios = ttk.Button(self.frame_menu_ndc, text="Relatórios", width=largura_botao, command=lambda: [self.criar_interface_relatorios("NDC"), self.mostrar_interface_com_lateral(self.frame_relatorios)])
        botao_relatorios.pack(pady=10, padx=40)

        botao_voltar = ttk.Button(self.frame_menu_ndc, text="← Voltar", width=largura_botao, command=lambda: [self.criar_interface_genesys(), self.mostrar_interface_com_lateral(self.frame_genesys)])
        botao_voltar.pack(pady=20)

    def criar_menu_brn(self):
        """Cria o menu BRN."""
        self.limpar_frame(self.frame_menu_brn)
        self.adicionar_cabecalho_padrao(self.frame_menu_brn, titulo="Menu BRN")

        #label_menu_brn = ttk.Label(self.frame_menu_brn, text="Menu BRN", font=("Arial", 14, "bold"))
        #label_menu_brn.pack(pady=20)

        label_instrucao = ttk.Label(self.frame_menu_brn, text="Escolha a camada onde esta a aplicação desejada:", font=("Arial", 12))
        label_instrucao.pack(pady=(10, 20))

        largura_botao = 14

        botao_midias = ttk.Button(self.frame_menu_brn, text="Mídias", width=largura_botao, command=lambda: [self.criar_interface_midias("BRN"), self.mostrar_interface_com_lateral(self.frame_midias)])
        botao_midias.pack(pady=10, padx=40)

        botao_processamento = ttk.Button(self.frame_menu_brn, text="Processamento", width=largura_botao, command=lambda: [self.criar_interface_processamento("BRN"), self.mostrar_interface_com_lateral(self.frame_processamento)])
        botao_processamento.pack(pady=10, padx=40)

        botao_roteamento = ttk.Button(self.frame_menu_brn, text="Roteamento", width=largura_botao, command=lambda: [self.criar_interface_roteamento("BRN"), self.mostrar_interface_com_lateral(self.frame_roteamento)])
        botao_roteamento.pack(pady=10, padx=40)

        botao_voz = ttk.Button(self.frame_menu_brn, text="Voz", width=largura_botao, command=lambda: [self.criar_interface_voz("BRN"), self.mostrar_interface_com_lateral(self.frame_voz)])
        botao_voz.pack(pady=10, padx=40)

        botao_framework = ttk.Button(self.frame_menu_brn, text="Framework", width=largura_botao, command=lambda: [self.criar_interface_framework("BRN"), self.mostrar_interface_com_lateral(self.frame_framework)])
        botao_framework.pack(pady=10, padx=40)

        botao_relatorios = ttk.Button(self.frame_menu_brn, text="Relatórios", width=largura_botao, command=lambda:[self.criar_interface_relatorios("BRN"), self.mostrar_interface_com_lateral(self.frame_relatorios)])
        botao_relatorios.pack(pady=10, padx=40)

        botao_voltar = ttk.Button(self.frame_menu_brn, text="← Voltar", width=largura_botao, command=lambda: [self.criar_interface_genesys(), self.mostrar_interface_com_lateral(self.frame_genesys)])
        botao_voltar.pack(pady=20)

    def criar_interface_midias(self, menu):
        """Cria a interface de Mídias para o menu NDC ou BRN."""

        self.limpar_frame(self.frame_midias)
        self.adicionar_cabecalho_padrao(self.frame_midias, titulo=f"Mídias ({menu})")

        # Frame de conteúdo principal, logo abaixo do cabeçalho
        conteudo = ttk.Frame(self.frame_midias, style="Custom.TFrame")
        conteudo.pack(fill="both", expand=True, pady=(10, 0))

        if menu == "NDC":
            aplicacoes = [
                "chat_server_ndc_p",
                "email_server_ndc_p",
                "email_server_ndc_02_p",
                "gms_ndc_p",
                "cassandra_gms_ndc_1",
                "cassandra_mm_ndc_1",
                "classification_server_ndc_p",
                "sms_server_ndc_p"
            ]
            menu_frame = self.frame_menu_ndc
        elif menu == "BRN":
            aplicacoes = [
                "chat_server_brn_p",
                "email_server_brn_p",
                "gms_brn_p",
                "cassandra_gms_brn_1",
                "cassandra_mm_brn_1",
                "classification_server_brn_p",
                "sms_server_brn_p"
            ]
            menu_frame = self.frame_menu_brn

        # Passe o frame de conteúdo para a função de aplicações
        self.criar_interface_aplicacoes(conteudo, f"Mídias ({menu})", aplicacoes, menu_frame)
        #self.mostrar_frame(self.frame_midias)
        self.mostrar_interface_com_lateral(self.frame_midias)

    def criar_interface_processamento(self, menu):
        """Cria a interface de Processamento para o menu NDC ou BRN."""

        self.limpar_frame(self.frame_processamento)
        self.adicionar_cabecalho_padrao(self.frame_processamento, titulo=f"Processamento ({menu})")

        # Frame de conteúdo principal, logo abaixo do cabeçalho
        conteudo = ttk.Frame(self.frame_processamento)
        conteudo.pack(fill="both", expand=True, pady=(10, 0))

        if menu == "NDC":
            aplicacoes = [
                "ucs_ndc_p",
                "ixn_ndc_p",
                "ixn_ndc_b",
                "ixn_outros_ndc_p",
                "ucsproxy_ndc_p",
                "uscproxy_ndc_01",
                "uscproxy_ndc_02",
                "ixnproxy_ndc_01",
                "ixnproxy_ndc_02",
                "ixnproxy_ndc_p",
                "ixnproxy_app_ndc_p"
            ]
            menu_frame = self.frame_menu_ndc
        elif menu == "BRN":
            aplicacoes = [
                "ucs_brn_p",
                "ixn_brn_p",
                "ixn_email_brn_p",
                "ucsproxy_brn_p",
                "ixnproxy_brn_p",
                "ixnproxy_app_brn_p"
            ]
            menu_frame = self.frame_menu_brn
        self.criar_interface_aplicacoes(conteudo, f"Processamento ({menu})", aplicacoes, menu_frame)
        #self.mostrar_frame(self.frame_processamento)
        self.mostrar_interface_com_lateral(self.frame_processamento)

    def criar_interface_roteamento(self, menu):
        self.limpar_frame(self.frame_roteamento)
        self.adicionar_cabecalho_padrao(self.frame_roteamento, titulo=f"Roteamento ({menu})")

        # Frame de conteúdo principal, logo abaixo do cabeçalho
        conteudo = ttk.Frame(self.frame_roteamento)
        conteudo.pack(fill="both", expand=True, pady=(10, 0))

        """Cria a interface de Roteamento para o menu NDC ou BRN."""
        if menu == "NDC":
            aplicacoes = [
                "urs_voz_ndc_p",
                "urs_mm_ndc_p",
                "ors_mm_1_ndc_p",
                "ors_voz_1_ndc_p",
                "sipserver_urs_ndc_p",
                "statserver_urs_mm_ndc_p",
                "statserver_urs_voz_ndc_p",
                "statserver_urs_voz_ndc_b",
                "rules_authoring_ndc_01",
                "rules_engine_ndc_01"
                ]
            menu_frame = self.frame_menu_ndc
        elif menu == "BRN":
            aplicacoes = [
                "urs_voz_brn_p",
                "urs_mm_brn_p",
                "ors_mm_1_brn_p",
                "ors_voz_1_brn_p",
                "statserver_urs_mm_brn_p",
                "statserver_urs_voz_brn_p",
                "rules_authoring_brn_01",
                "rules_engine_brn_01"
            ]
            menu_frame = self.frame_menu_brn
        self.criar_interface_aplicacoes(conteudo, f"Roteamento ({menu})", aplicacoes, menu_frame)
        #self.mostrar_frame(self.frame_roteamento)
        self.mostrar_interface_com_lateral(self.frame_roteamento)

    def criar_interface_voz(self, menu):
        """Cria a interface de Voz para o menu NDC ou BRN."""
        self.limpar_frame(self.frame_voz)
        self.adicionar_cabecalho_padrao(self.frame_voz, titulo=f"Voz ({menu})")

        # Frame de conteúdo principal, logo abaixo do cabeçalho
        conteudo = ttk.Frame(self.frame_voz)
        conteudo.pack(fill="both", expand=True, pady=(10, 0))

        if menu == "NDC":
            aplicacoes = [
                "sipserver_rtr_ndc_p",
                "sipserver_agt_ndc_p",
                "sipserver_agt_ndc_b",
                "sipserver_agt_reserv_p",
                "sipserver_ocs_ndc_p",
                "sipserver_vq_p",
                "tsproxy_ndc_p_816"
            ]
            menu_frame = self.frame_menu_ndc
        elif menu == "BRN":
            aplicacoes = [
                "sipserver_rtr_brn_p",
                "sipserver_agt_brn_p",
                "sipserver_agt_brn_b",
                "sipserver_agt_brn_reserv_p",
                "sipserver_ocs_brn_p",
                "sipserver_vq_b",
                "tsproxy_brn_p_816"
            ]
            menu_frame = self.frame_menu_brn
        self.criar_interface_aplicacoes(conteudo, f"Voz ({menu})", aplicacoes, menu_frame)
        #self.mostrar_frame(self.frame_voz)
        self.mostrar_interface_com_lateral(self.frame_voz)

    def criar_interface_framework(self, menu):
        """Cria a interface de Voz para o menu NDC ou BRN."""
        self.limpar_frame(self.frame_framework)
        self.adicionar_cabecalho_padrao(self.frame_framework, titulo=f"Framework ({menu})")

        # Frame de conteúdo principal, logo abaixo do cabeçalho
        conteudo = ttk.Frame(self.frame_framework)
        conteudo.pack(fill="both", expand=True, pady=(10, 0))

        if menu == "NDC":
            aplicacoes = [
                "gax_ndc",
                "license_manager_1",
                "scs_ndc_p"
            ]
            menu_frame = self.frame_menu_ndc
        elif menu == "BRN":
            aplicacoes = [
                "gax_brn",
                "license_manager_2",
                "scs_brn_p"            
            ]
            menu_frame = self.frame_menu_brn
        self.criar_interface_aplicacoes(conteudo, f"framework ({menu})", aplicacoes, menu_frame)
        #self.mostrar_frame(self.frame_framework)
        self.mostrar_interface_com_lateral(self.frame_framework)

    def criar_interface_relatorios(self, menu):
        """Cria a interface de Relatorios para o menu NDC ou BRN."""
        self.limpar_frame(self.frame_relatorios)
        self.adicionar_cabecalho_padrao(self.frame_relatorios, titulo=f"Relatórios ({menu})")

        # Frame de conteúdo principal, logo abaixo do cabeçalho
        conteudo = ttk.Frame(self.frame_relatorios)
        conteudo.pack(fill="both", expand=True, pady=(10, 0))

        if menu == "NDC":
            aplicacoes = [
                "icon_cfg_ndc_1",
                "icon_mm_ndc_1",
                "icon_ocs_ndc_1",
                "icon_sips_agt_ndc_1",
                "icon_sips_agt_ndc_2",
                "icon_sips_ocs_ndc_1",
                "icon_sips_rtr_ndc_1",
                "icon_sips_vq_1",
                "pulse_col_ndc_p",
                "pulse_ndc",
                "statserver_pulse_ndc_p",
                "statserver_pulse_ndc_b"
            ]
            menu_frame = self.frame_menu_ndc
        elif menu == "BRN":
            aplicacoes = [
                "icon_cfg_brn_1",
                "icon_mm_brn_1",
                "icon_ocs_brn_1",
                "icon_sips_agt_brn_1",
                "icon_sips_agt_brn_2",
                "icon_sips_ocs_brn_1",
                "icon_sips_rtr_brn_1",
                "icon_sips_vq_2",
                "pulse_col_brn_p",
                "pulse_brn",
                "statserver_pulse_brn_p"          
            ]
            menu_frame = self.frame_menu_brn
        self.criar_interface_aplicacoes(conteudo, f"relatorios ({menu})", aplicacoes, menu_frame)
        #self.mostrar_frame(self.frame_relatorios)    
        self.mostrar_interface_com_lateral(self.frame_relatorios)


    def criar_interface_aplicacoes(self, frame, titulo, aplicacoes, menu_frame):
        self.limpar_frame(frame)
        #label_titulo = ttk.Label(frame, text=f"Interface de {titulo}", font=("Arial", 14, "bold"))
        #label_titulo.pack(pady=(20, 10))
        # Label centralizada para instrução
        linha_instrucao = ttk.Frame(frame)
        linha_instrucao.pack(pady=(10, 20))
        label_instrucao = ttk.Label(linha_instrucao, text="Escolha a Aplicação e clique em 'Start' para iniciar a coleta de logs:", font=("Arial", 12))
        label_instrucao.pack(side="left")
        label_info = tk.Label(linha_instrucao, image=self.info_icon)
        label_info.pack(side="left", padx=(20, 8))
        ToolTip(label_info, "Ao iniciar a coleta de logs para a aplicação selecionada, será coletado os 3 arquivos de logs mais recentes encontrados no diretório.")
        container = ttk.Frame(frame)
        container.pack(pady=10)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_columnconfigure(2, weight=1)
        container.grid_columnconfigure(3, weight=1)

        # Dicionário para armazenar widgets por app
        frame.widgets_por_app = {}

        for i, app in enumerate(aplicacoes):
            label_nome_aplicacao = ttk.Label(container, text=app, font=("Arial", 12))
            label_nome_aplicacao.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

            progressbar = ttk.Progressbar(container, orient=tk.HORIZONTAL, length=150, mode='determinate')
            progressbar.grid(row=i, column=2, padx=10, pady=5, sticky="ew")

            imagem_resultado = tk.Label(container, image=self.loading_gif[0], width=28, height=28)
            imagem_resultado.grid(row=i, column=4, padx=10, pady=5, sticky="ew")
            imagem_resultado.tooltip = ToolTip(imagem_resultado, "Transferindo arquivos, aguarde...")
            imagem_resultado.grid_remove()  # Deixa invisível inicialmente

            # Botão de Start, agora passa os widgets corretos
            botao_start = ttk.Button(container, text="Start")
            botao_start.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            # Agora defina o comando depois de criar o botão:
            botao_start.config(command=lambda app=app, pb=progressbar, ir=imagem_resultado, bs=botao_start: self.executar_comando(app, pb, ir, bs))

            # Salva widgets para acesso posterior
            frame.widgets_por_app[app] = {"progressbar": progressbar, "imagem_resultado": imagem_resultado}

        if menu_frame == self.frame_menu_ndc:
            voltar_cmd = lambda: [self.criar_menu_ndc(), self.mostrar_interface_com_lateral(self.frame_menu_ndc)]
        else:
            voltar_cmd = lambda: [self.criar_menu_brn(), self.mostrar_interface_com_lateral(self.frame_menu_brn)]

        botao_voltar = ttk.Button(frame, text="← Voltar", command=voltar_cmd)
        botao_voltar.pack(pady=20)

    def criar_interface_busca_id(self):
        """Cria a interface de Busca por ID."""
        # Limpa o frame antes de criar a interface
        self.limpar_frame(self.frame_busca_id)
        self.adicionar_cabecalho_padrao(self.frame_busca_id, titulo="Busca por ID")

        # Inicializa o dicionário para armazenar inputs por opção
        self.frame_busca_id.inputs_por_opcao = {}

        # Título da interface (opcional, pois já está no cabeçalho)
        # label_titulo = ttk.Label(self.frame_busca_id, text="Busca por ID", font=("Arial", 14, "bold"))
        # label_titulo.pack(pady=(20, 10))

        # Label centralizada para instrução
        label_instrucao = ttk.Label(self.frame_busca_id, text="Digite o ID a ser buscado:", font=("Arial", 12))
        label_instrucao.pack(pady=(10, 20))

        # Frame para organizar as opções
        container = ttk.Frame(self.frame_busca_id)
        container.pack(pady=10)

        # Lista de opções
        opcoes = ["Interaction ID", "Session ID", "ConnID", "Calluuid"]

        for i, opcao in enumerate(opcoes):
            # Label da opção
            label_opcao = ttk.Label(container, text=opcao, font=("Arial", 12))
            label_opcao.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

            # Campo de input de texto com placeholder
            input_text = tk.Entry(container, font=("Arial", 10), width=30)
            placeholders = {
                "Interaction ID": "Ex: 0001AaJRTU3Y20J4",
                "Session ID": "Ex: 011OB0J4B8C278FTEEO822LAES0001IP",
                "ConnID": "Ex: 007e0386358d4569",
                "Calluuid": "Ex: 027Q7T5KC0BMJEH8EEO822LAES0001B5"
            }
            placeholder = placeholders.get(opcao, "Digite o valor")
            input_text.insert(0, placeholder)
            input_text.config(fg="gray")
            input_text.grid(row=i, column=1, padx=10, pady=5, sticky="ew")

            def on_focus_in(event, entry=input_text, ph=placeholder):
                if entry.get() == ph:
                    entry.delete(0, tk.END)
                    entry.config(fg="black")

            def on_focus_out(event, entry=input_text, ph=placeholder):
                if not entry.get():
                    entry.insert(0, ph)
                    entry.config(fg="gray")

            input_text.bind("<FocusIn>", on_focus_in)
            input_text.bind("<FocusOut>", on_focus_out)

            # Combobox do ambiente (NDC/BRN)
            ambiente_var = tk.StringVar(value="NDC")
            combo_ambiente = ttk.Combobox(
                container,
                textvariable=ambiente_var,
                values=["NDC", "BRN"],
                state="readonly",
                width=6
            )
            combo_ambiente.grid(row=i, column=2, padx=5, pady=5, sticky="ew")

            # Botão Start (coluna 3)
            botao_start = ttk.Button(container, text="Start")
            botao_start.grid(row=i, column=3, padx=10, pady=5, sticky="ew")

            # Barra de progresso (coluna 4)
            progressbar = ttk.Progressbar(container, orient=tk.HORIZONTAL, length=150, mode='determinate')
            progressbar.grid(row=i, column=4, padx=10, pady=5, sticky="ew")

            # Imagem de resultado (coluna 5)
            imagem_resultado = tk.Label(container, image=self.loading_gif[0], width=28, height=28)
            imagem_resultado.grid(row=i, column=5, padx=10, pady=5, sticky="ew")
            imagem_resultado.tooltip = ToolTip(imagem_resultado, "Transferindo arquivos, aguarde...")
            imagem_resultado.grid_remove()  # Deixa invisível inicialmente

            # Defina o comando do botão Start
            botao_start.config(
                command=lambda opcao=opcao, entry=input_text, pb=progressbar, ir=imagem_resultado, bs=botao_start, ambiente_var=ambiente_var:
                    self.executar_busca_id(opcao, entry, pb, ir, bs, ambiente_var.get())
            )

            # Armazene os widgets se necessário
            self.frame_busca_id.inputs_por_opcao[opcao] = (input_text, ambiente_var)

        # Adicione este bloco após o container e antes do botão de voltar:
        aviso_box = tk.Label(
            self.frame_busca_id,
            text="Atenção: a busca por ID pode levar alguns minutos, pois será feita uma varredura em mais de uma aplicação.",
            font=("Arial", 10, "bold"),
            bg="#fffdf3",  # cor de fundo suave
            fg="#FF7300",  # cor do texto de aviso
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
            wraplength=600,
            justify="center"
        )
        aviso_box.pack(pady=(10, 20))

        # Botão de voltar para Home
        botao_voltar = ttk.Button(self.frame_busca_id, text="← Voltar", command=lambda: [self.criar_interface_genesys(), self.mostrar_interface_com_lateral(self.frame_genesys)])
        botao_voltar.pack(pady=20)

    def abrir_busca_id(self):
        self.criar_interface_busca_id()  # Sempre recria a interface limpa
        self.mostrar_frame(self.frame_busca_id)

    def executar_comando(self, app, progressbar, imagem_resultado, botao_start):
        def tarefa():
            def progresso_callback(valor, total):
                self.atualizar_progresso(progressbar, valor, total)
            try:
                self.atualizar_progresso(progressbar, 0, 1)
                print(f"[INFO] Iniciando coleta para app: {app}")
                botao_start.config(state="disabled")
                imagem_resultado.grid()
                imagem_resultado.animando = True
                imagem_resultado.config(image=self.loading_gif[0])
                imagem_resultado.image = self.loading_gif[0]
                imagem_resultado.tooltip.update_text("Transferindo arquivos, aguarde...")
                self.animar_loading(imagem_resultado)
                config = SERVIDORES.get(app)
                if not config and hasattr(self, 'busca_id_to_app'):
                    app_key = self.busca_id_to_app.get(app)
                    config = SERVIDORES.get(app_key)
                if not config:
                    print(f"[ERRO] Configuração não encontrada para app: {app}")
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.erro_icon)
                    imagem_resultado.image = self.erro_icon
                    imagem_resultado.tooltip.update_text("Falha na transferência de arquivos.")
                    return
                # Use função especial só para os apps do Middleware
                if app in ("cc_interaction_integration", "cc_business_integration"):
                    from RemoteUtils import copiar_ultimos_logs_e_outs_remotos
                    sucesso, msg = copiar_ultimos_logs_e_outs_remotos(
                        progresso_callback=progresso_callback,
                        **config
                    )
                else:
                    sucesso, msg = copiar_ultimos_logs_remotos(
                        progresso_callback=progresso_callback,
                        **config
                    )
                print(f"[INFO] Resultado da coleta para {app}: {msg}")
                if sucesso:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.sucesso_icon)
                    imagem_resultado.image = self.sucesso_icon
                    imagem_resultado.tooltip.update_text("Transferência concluída com sucesso!")
                else:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.erro_icon)
                    imagem_resultado.image = self.erro_icon
                    imagem_resultado.tooltip.update_text("Falha na transferência de arquivos.")
            except Exception as e:
                print(f"[ERRO] Exceção durante coleta do app {app}: {e}")
                imagem_resultado.animando = False
                imagem_resultado.config(image=self.erro_icon)
                imagem_resultado.image = self.erro_icon
                imagem_resultado.tooltip.update_text("Falha na transferência de arquivos.")
                messagebox.showerror("Erro", f"Ocorreu um erro com {app}: {e}")
            finally:
                botao_start.config(state="normal")
        threading.Thread(target=tarefa).start()

    def executar_busca_id(self, app, entry, progressbar, imagem_resultado, botao_start, ambiente):
        def tarefa():
            mensagens = []
            try:
                self.atualizar_progresso(progressbar, 0, 1)
                print(f"[INFO] Iniciando varredura de arquivos: {app}")
                botao_start.config(state="disabled")
                imagem_resultado.grid()
                imagem_resultado.animando = True
                imagem_resultado.config(image=self.varredura_gif[0])
                imagem_resultado.image = self.varredura_gif[0]
                imagem_resultado.tooltip.update_text("Varredura dos arquivos, aguarde...")
                self.animar_loading_varredura(imagem_resultado)

                # Recupere o placeholder correspondente à opção
                placeholders = {
                    "Interaction ID": "Ex: 0001AaJRTU3Y20J4",
                    "Session ID": "Ex: 011OB0J4B8C278FTEEO822LAES0001IP",
                    "ConnID": "Ex: 007e0386358d4569",
                    "Calluuid": "Ex: 027Q7T5KC0BMJEH8EEO822LAES0001B5"
                }
                placeholder = placeholders.get(app, "Digite o valor")

                valor_busca = entry.get().strip()
                if not valor_busca or valor_busca == placeholder:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.erro_icon)
                    imagem_resultado.image = self.erro_icon
                    imagem_resultado.tooltip.update_text("ID de busca inválido.")
                    messagebox.showerror("Erro","ID de busca inválido.")
                    print(f"[Erro] ID de busca inválido.")
                    return

                # ambiente já é o valor "NDC" ou "BRN"
                if ambiente == "NDC":
                    app_keys = self.busca_id_to_app_ndc.get(app, [])
                else:
                    app_keys = self.busca_id_to_app_brn.get(app, [])
                total = len(app_keys)
                
                # 1. Calcule o total de arquivos de todos os apps
                total_arquivos = 0
                arquivos_por_app = []
                for app_key in app_keys:
                    config = SERVIDORES.get(app_key)
                    if not config:
                        arquivos_por_app.append(0)
                        continue
                    try:
                        import paramiko # type: ignore
                        transport = paramiko.Transport((config["host"], 22))
                        transport.connect(username=config["usuario"], password=config["senha"])
                        sftp = paramiko.SFTPClient.from_transport(transport)
                        arquivos = [f for f in sftp.listdir_attr(config["caminho_remoto"]) if f.filename.endswith('.log')]
                        arquivos.sort(key=lambda x: x.st_mtime, reverse=True)
                        arquivos = arquivos[:10]
                        arquivos_por_app.append(len(arquivos))
                        total_arquivos += len(arquivos)
                        sftp.close()
                        transport.close()
                    except Exception:
                        arquivos_por_app.append(0)

                # 2. Progresso global
                progresso_global = [0]
                def progresso_callback(_unused, _unused2):
                    progresso_global[0] += 1
                    self.atualizar_progresso(progressbar, progresso_global[0], total_arquivos)

                # 3. Faça a busca em todos os apps
                encontrou = False
                for idx, app_key in enumerate(app_keys):
                    config = SERVIDORES.get(app_key)
                    if not config:
                        continue
                    sucesso, msg = buscar_e_copiar_log_remoto(
                        valor_busca,
                        progresso_callback=progresso_callback,
                        **config
                    )
                    mensagens.append(f"{app_key}: {msg}")
                    if sucesso:
                        encontrou = True

                # 4. Exiba o resultado só ao final
                if encontrou:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.sucesso_icon)
                    imagem_resultado.image = self.sucesso_icon
                    imagem_resultado.tooltip.update_text("Busca concluída com sucesso!")
                else:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.erro_icon)
                    imagem_resultado.image = self.erro_icon
                    imagem_resultado.tooltip.update_text("Falha na busca de arquivos.")

            except Exception as e:
                print(f"[ERRO] Exceção durante busca do ID {app}: {e}")
                mensagens.append(str(e))  # Agora mensagens sempre existe
                imagem_resultado.animando = False
                imagem_resultado.config(image=self.erro_icon)
                imagem_resultado.image = self.erro_icon
                imagem_resultado.tooltip.update_text("Falha na busca de arquivos.")
                messagebox.showerror("Erro", f"Ocorreu um erro com {app}: {e}")
            finally:
                botao_start.config(state="normal")
                self.atualizar_progresso(progressbar, total_arquivos, total_arquivos)
        threading.Thread(target=tarefa).start()

    def executar_busca_id_middleware(self, entry, progressbar, imagem_resultado, botao_start):
        valor_busca = entry.get().strip()
        print(f"[DEBUG] Valor digitado para busca: '{valor_busca}'")
        if not valor_busca:
            self.resultado_busca_id_middleware.config(text="Digite um valor para buscar.", fg="red")
            print("[DEBUG] Busca cancelada: valor vazio.")
            return

        self.resultado_busca_id_middleware.config(text="Buscando...", fg="black")
        botao_start.config(state="disabled")
        imagem_resultado.grid()
        imagem_resultado.animando = True
        imagem_resultado.config(image=self.varredura_gif[0])
        imagem_resultado.image = self.varredura_gif[0]
        imagem_resultado.tooltip.update_text("Varredura dos arquivos, aguarde...")
        self.animar_loading_varredura(imagem_resultado)

        def tarefa():
            from ConfigServidores import SERVIDORES
            from RemoteUtils import buscar_e_copiar_log_ou_out_remoto
            import paramiko # type: ignore

            apps = ["cc_interaction_integration", "cc_business_integration"]
            total_arquivos = 0
            arquivos_por_app = []

            # 1. Conte o total de arquivos .log e .out em ambos os diretórios
            for app in apps:
                config = SERVIDORES.get(app)
                if not config:
                    arquivos_por_app.append(0)
                    continue
                try:
                    transport = paramiko.Transport((config["host"], 22))
                    transport.connect(username=config["usuario"], password=config["senha"])
                    sftp = paramiko.SFTPClient.from_transport(transport)
                    arquivos = [f for f in sftp.listdir_attr(config["caminho_remoto"]) if f.filename.endswith('.log') or f.filename.endswith('.out')]
                    arquivos_por_app.append(len(arquivos))
                    total_arquivos += len(arquivos)
                    print(f"[INFO] {app}: {len(arquivos)} arquivos encontrados para varredura.")
                    sftp.close()
                    transport.close()
                except Exception as e:
                    print(f"[ERRO] Falha ao contar arquivos em {app}: {e}")
                    arquivos_por_app.append(0)
                print(f"[INFO] Total de arquivos a serem verificados: {total_arquivos}")

            progresso_global = [0]
            def progresso_callback(valor, total):
                progresso_global[0] += 1
                self.atualizar_progresso(progressbar, progresso_global[0], total_arquivos)

            encontrados = []
            try:
                for idx, app in enumerate(apps):
                    config = SERVIDORES.get(app)
                    print(f"[DEBUG] Buscando em app: {app} | Config encontrada: {bool(config)}")
                    if not config:
                        continue
                    sucesso, msg = buscar_e_copiar_log_ou_out_remoto(
                        valor_busca,
                        progresso_callback=progresso_callback,
                        **config
                    )
                    print(f"[DEBUG] Resultado busca em {app}: sucesso={sucesso}, msg={msg}")
                    if sucesso:
                        encontrados.append(f"{app}: {msg}")
                if encontrados:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.sucesso_icon)
                    imagem_resultado.image = self.sucesso_icon
                    imagem_resultado.tooltip.update_text("Busca concluída com sucesso!")
                    self.resultado_busca_id_middleware.config(
                        text="Encontrado e copiado em:\n" + "\n".join(encontrados), fg="green"
                    )
                    print(f"[DEBUG] Busca concluída com sucesso: {encontrados}")
                else:
                    imagem_resultado.animando = False
                    imagem_resultado.config(image=self.erro_icon)
                    imagem_resultado.image = self.erro_icon
                    imagem_resultado.tooltip.update_text("Falha na busca de arquivos.")
                    self.resultado_busca_id_middleware.config(
                        text="Valor não encontrado nos logs do Middleware.", fg="red"
                    )
                    print("[DEBUG] Valor não encontrado nos logs do Middleware.")
            except Exception as e:
                print(f"[ERRO] Exceção durante busca por ID Middleware: {e}")
                imagem_resultado.animando = False
                imagem_resultado.config(image=self.erro_icon)
                imagem_resultado.image = self.erro_icon
                imagem_resultado.tooltip.update_text("Falha na busca de arquivos.")
                self.resultado_busca_id_middleware.config(
                    text=f"Ocorreu um erro: {e}", fg="red"
                )
            finally:
                botao_start.config(state="normal")
                self.atualizar_progresso(progressbar, total_arquivos, total_arquivos)

        threading.Thread(target=tarefa).start()

    def atualizar_progresso(self, progressbar, valor, total):
        def _atualiza():
            progressbar["maximum"] = total
            progressbar["value"] = valor
        progressbar.after(0, _atualiza)

    def animar_loading(self, label, frame=0):
        if not getattr(label, "animando", False):
            return  # Pare imediatamente se não estiver animando
        if hasattr(self, "loading_gif") and self.loading_gif:
            label.config(image=self.loading_gif[frame])
            label.image = self.loading_gif[frame]
            frame = (frame + 1) % len(self.loading_gif)
            label.after(100, lambda: self.animar_loading(label, frame))

    def animar_loading_varredura(self, label, frame=0):
        if not getattr(label, "animando", False):
            return
        if hasattr(self, "varredura_gif") and self.varredura_gif:
            label.config(image=self.varredura_gif[frame])
            label.image = self.varredura_gif[frame]
            frame = (frame + 1) % len(self.varredura_gif)
            label.after(100, lambda: self.animar_loading_varredura(label, frame))

    def criar_interface_inicio(self):
        self.limpar_frame(self.frame_inicio)

        img_path = resource_path("files/vivo-gen-cetech-offwhite.png")
        img = Image.open(img_path).resize((40, 40))
        self.img_inicio = ImageTk.PhotoImage(img)

        label_bem_vindo = ttk.Label(
            self.frame_inicio,
            text="Bem-vindo ao App Coleta de Logs",
            font=("Sergoe", 18, "bold"),
        )
        label_bem_vindo.pack(pady=40)

        label_instrucao_inicio = ttk.Label(
            self.frame_inicio,
            text="Use o menu lateral para navegar entre as opções.",
            font=("Arial", 13)
        )
        label_instrucao_inicio.pack(pady=0)

        # --- Imagem de capa ---
        capa_path = resource_path("files/BG.png")  # Altere para o nome do arquivo da sua capa
        capa_img = Image.open(capa_path).resize((525, 525))  # Ajuste o tamanho conforme necessário
        self.capa_inicio = ImageTk.PhotoImage(capa_img)
        label_capa = tk.Label(self.frame_inicio, image=self.capa_inicio, bg="#f6f4f2", borderwidth=0)
        label_capa.pack(pady=(0, 1))

    def criar_interface_middleware(self, app_key):
        self.limpar_frame(self.frame_middleware)
        img_path = resource_path("files/md-fundo-removebg-preview.png")
        titulo = "Menu "
        if app_key == "cc_interaction_integration":
            titulo += "Interaction Integration"
            apps = [("CC Interaction Integration", "cc_interaction_integration")]
        else:
            titulo += "Business Integration"
            apps = [("CC Business Integration", "cc_business_integration")]

        self.adicionar_cabecalho_padrao(self.frame_middleware, titulo, img_path=img_path, img_size=(28, 28))

        # Instrução para o usuário
        label_instrucao = ttk.Label(
            self.frame_middleware,
            text="Clique em 'Start' para iniciar a coleta de logs:",
            font=("Arial", 12)
        )
        label_instrucao.pack(pady=(10, 20))

        container = ttk.Frame(self.frame_middleware)
        container.pack(pady=10)

        self.frame_middleware.widgets_por_app = {}

        for i, (label_text, app_key) in enumerate(apps):
            label_app = ttk.Label(container, text=label_text, font=("Arial", 12))
            label_app.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

            botao_start = ttk.Button(container, text="Start")
            botao_start.grid(row=i, column=1, padx=10, pady=5, sticky="ew")

            progressbar = ttk.Progressbar(container, orient=tk.HORIZONTAL, length=150, mode='determinate')
            progressbar.grid(row=i, column=2, padx=10, pady=5, sticky="ew")

            imagem_resultado = tk.Label(container, image=self.loading_gif[0], width=28, height=28)
            imagem_resultado.grid(row=i, column=3, padx=10, pady=5, sticky="ew")
            imagem_resultado.tooltip = ToolTip(imagem_resultado, "Transferindo arquivos, aguarde...")
            imagem_resultado.grid_remove()

            botao_start.config(command=lambda app=app_key, pb=progressbar, ir=imagem_resultado, bs=botao_start: self.executar_comando(app, pb, ir, bs))

            self.frame_middleware.widgets_por_app[app_key] = {"progressbar": progressbar, "imagem_resultado": imagem_resultado}

        botao_voltar = ttk.Button(self.frame_middleware, text="← Voltar", command=lambda: [self.criar_interface_middleware_menu(), self.mostrar_interface_com_lateral(self.frame_middleware_menu)])
        botao_voltar.pack(pady=20)

    def criar_interface_busca_id_middleware(self):
        self.limpar_frame(self.frame_busca_id_middleware)
        self.adicionar_cabecalho_padrao(
            self.frame_busca_id_middleware,
            titulo="Busca por ID",
            img_path=resource_path("files/md-fundo-removebg-preview.png"),
            img_size=(28, 28)
        )

        label_instrucao = ttk.Label(
            self.frame_busca_id_middleware,
            text="Digite o valor a ser buscado nos logs do Middleware:",
            font=("Arial", 12)
        )
        label_instrucao.pack(pady=(10, 20))

        # --- CORREÇÃO: crie o container antes de usá-lo ---
        container = ttk.Frame(self.frame_busca_id_middleware)
        container.pack(pady=10)

        # Campo de input
        label_id = ttk.Label(container, text="ID:", font=("Arial", 12))
        label_id.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        entry = tk.Entry(container, font=("Arial", 10), width=30)
        entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # Botão de busca
        botao_buscar = ttk.Button(
            container,
            text="Buscar",
            command=lambda: self.executar_busca_id_middleware(entry, progressbar, imagem_resultado, botao_buscar)
        )
        botao_buscar.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

        # Barra de progresso
        progressbar = ttk.Progressbar(container, orient=tk.HORIZONTAL, length=150, mode='determinate')
        progressbar.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

        # Imagem de resultado
        imagem_resultado = tk.Label(container, image=self.loading_gif[0], width=28, height=28)
        imagem_resultado.grid(row=0, column=4, padx=10, pady=5, sticky="ew")
        imagem_resultado.tooltip = ToolTip(imagem_resultado, "Transferindo arquivos, aguarde...")
        imagem_resultado.grid_remove()  # Deixa invisível inicialmente

        # Label de resultado
        self.resultado_busca_id_middleware = tk.Label(self.frame_busca_id_middleware, text="", font=("Arial", 11))
        self.resultado_busca_id_middleware.pack(pady=10)

        # Botão de voltar
        botao_voltar = ttk.Button(
            self.frame_busca_id_middleware,
            text="← Voltar",
            command=lambda: [self.criar_interface_middleware_menu(), self.mostrar_interface_com_lateral(self.frame_middleware_menu)]
        )
        botao_voltar.pack(pady=20)

    def _carregar_gif(self, gif_path):
        imagens = []
        try:
            gif = Image.open(gif_path)
            while True:
                frame = gif.copy().convert("RGBA").resize((28, 28))
                imagens.append(ImageTk.PhotoImage(frame))
                gif.seek(len(imagens))
        except EOFError:
            pass
        return imagens

    def _criar_botoes_laterais(self, largura_botao):
        ttk.Button(
            self.frame_opcoes, text="Início", width=20,
            command=lambda: [self.criar_interface_inicio(), self.mostrar_interface_com_lateral(self.frame_inicio)]
        ).pack(pady=10, padx=20)
        ttk.Button(
            self.frame_opcoes, text="Genesys", width=20,
            command=lambda: [self.criar_interface_genesys(), self.mostrar_interface_com_lateral(self.frame_genesys)]
        ).pack(pady=10, padx=20)
        ttk.Button(
            self.frame_opcoes, text="Middleware", width=20,
            command=lambda: [self.criar_interface_middleware_menu(), self.mostrar_interface_com_lateral(self.frame_middleware_menu)]
        ).pack(pady=10, padx=20)

        # --- Botão com ícone e texto no canto inferior esquerdo ---
        # Crie um frame para o rodapé do menu lateral
        frame_footer = tk.Frame(self.frame_lateral, bg=self.frame_lateral["bg"])
        frame_footer.pack(side="bottom", fill="x", pady=20)

        # Carregue o ícone (ajuste o caminho e tamanho conforme necessário)
        sobre_icon = ImageTk.PhotoImage(Image.open(resource_path("files/jira.png")).resize((15, 15)))
        self.sobre_icon = sobre_icon  # Referência para não ser coletado pelo GC

        # Botão com ícone e texto
        ttk.Button(
            frame_footer,
            image=self.sobre_icon,
            text="Wiki",
            style="Accent.TButton",  # Use um estilo para combinar com o tema
            compound="left",  # Ícone à esquerda do texto
            width=8,
            command=lambda: webbrowser.open_new("https://wikicorp.telefonica.com.br/pages/viewpage.action?pageId=557150890")
        ).pack(side="left", padx=(10, 5), anchor="w")

    # "Botão" hiperlink ao lado
        ttk.Button(
            frame_footer,
            text="Info",
            style="Accent.TButton",
            width=8,
            command=self.abrir_sobre  # Implemente este método para mostrar informações
         ).pack(side="left", padx=(0, 10), anchor="w")
    
    def abrir_sobre(self):
        messagebox.showinfo(
            "Sobre",
            "App Coleta de Logs\n\nVersão 1.0\n\nDesenvolvido por Arquitetura Contact Center - Plataforma Genesys Vivo.\n\nContato: gerarquiteturacontactcenter.br@telefonica.com"
        )

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, gif_path):
        super().__init__(parent)
        self.overrideredirect(True)  # Remove bordas

        gif = Image.open(gif_path)
        width, height = gif.resize((400, 300)).size  # Redimensiona o GIF para 400x400
        # Centraliza na tela
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.frames = []
        try:
            while True:
                frame = ImageTk.PhotoImage(gif.copy().convert("RGBA"))
                self.frames.append(frame)
                gif.seek(len(self.frames))
        except EOFError:
            pass
        self.label = tk.Label(self, image=self.frames[0], borderwidth=0, highlightthickness=0)
        self.label.pack(expand=True, fill="both")
        self.frame_index = 0
        self.after(0, self.animate)

    def animate(self):
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.label.config(image=self.frames[self.frame_index])
        self.after(100, self.animate)

def main():
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal até estar pronta

    splash = SplashScreen(root, resource_path("files/original-load.gif"))
    root.update()

    # Simule carregamento (substitua pelo seu setup real)
    import time
    time.sleep(2)  # Aqui você pode carregar recursos, etc.

    splash.destroy()
    root.deiconify()  # Mostra a janela principal
    app = Application(root)
    root.mainloop()

if __name__ == "__main__":
    main()