import paramiko # type: ignore
import os
import shutil
from datetime import datetime

def copiar_ultimos_logs_remotos(host, usuario, senha, caminho_remoto, caminho_local, quantidade=3, progresso_callback=None):
    print(f"[INFO] Iniciando cópia dos últimos {quantidade} arquivos .log de {caminho_remoto} para {caminho_local}")
    try:
        # Pasta central na área de trabalho
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        pasta_central = os.path.join(desktop, "App Coleta Logs")
        if not os.path.exists(pasta_central):
            os.makedirs(pasta_central)

        # Pasta do app dentro da pasta central
        app_folder = os.path.join(pasta_central, os.path.basename(caminho_local))
        if not os.path.exists(app_folder):
            os.makedirs(app_folder)

        # Subpasta com data e hora
        datahora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destino = os.path.join(app_folder, datahora)
        os.makedirs(destino, exist_ok=True)

        transport = paramiko.Transport((host, 22))
        transport.connect(username=usuario, password=senha)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Filtra arquivos .log e ordena por data de modificação (mais recente primeiro)
        arquivos = [f for f in sftp.listdir_attr(caminho_remoto) if f.filename.endswith('.log')]
        arquivos.sort(key=lambda x: x.st_mtime, reverse=True)
        ultimos_logs = arquivos[:quantidade]

        if not ultimos_logs:
            sftp.close()
            transport.close()
            return False, "Nenhum arquivo .log encontrado no diretório remoto."

        total = len(ultimos_logs)
        for idx, arquivo in enumerate(ultimos_logs):
            remote_path = f"{caminho_remoto}/{arquivo.filename}"
            local_path = os.path.join(destino, arquivo.filename)
            sftp.get(remote_path, local_path)
            print(f"[INFO] Copiado: {remote_path} -> {local_path}")
            if progresso_callback:
                progresso_callback(idx + 1, total)

        sftp.close()
        transport.close()
        print(f"[INFO] Cópia finalizada: {len(ultimos_logs)} arquivos copiados para {destino}")
        return True, f"{len(ultimos_logs)} arquivos .log copiados para {destino}"
    except Exception as e:
        print(f"[ERRO] Falha na cópia: {e}")
        return False, str(e)

def buscar_e_copiar_log_remoto(valor_busca, host, usuario, senha, caminho_remoto, caminho_local, quantidade=10, progresso_callback=None):
    print(f"[INFO] Iniciando busca por '{valor_busca}' em {quantidade} arquivos .log de {caminho_remoto}")
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        pasta_central = os.path.join(desktop, "App Coleta Logs")
        if not os.path.exists(pasta_central):
            os.makedirs(pasta_central)
        app_folder = os.path.join(pasta_central, os.path.basename(caminho_local))
        if not os.path.exists(app_folder):
            os.makedirs(app_folder)
        datahora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destino = os.path.join(app_folder, datahora)
        os.makedirs(destino, exist_ok=True)

        transport = paramiko.Transport((host, 22))
        transport.connect(username=usuario, password=senha)
        sftp = paramiko.SFTPClient.from_transport(transport)

        arquivos = [f for f in sftp.listdir_attr(caminho_remoto) if f.filename.endswith('.log')]
        arquivos.sort(key=lambda x: x.st_mtime, reverse=True)
        arquivos = arquivos[:quantidade]

        total = len(arquivos)
        encontrou = False  # <-- Inicialize aqui!
        for idx, arquivo in enumerate(arquivos):
            remote_path = f"{caminho_remoto}/{arquivo.filename}"
            temp_local = os.path.join(destino, f"temp_{arquivo.filename}")
            sftp.get(remote_path, temp_local)
            print(f"[INFO] Baixado temporariamente: {remote_path}")
            with open(temp_local, encoding="utf-8", errors="ignore") as f:
                if valor_busca in f.read():
                    encontrou = True
            # Chame o progresso_callback aqui, APÓS a leitura
            if progresso_callback:
                progresso_callback(idx + 1, total)
            if encontrou:
                os.rename(temp_local, os.path.join(destino, arquivo.filename))
                print(f"[INFO] Encontrado e copiado: {arquivo.filename} para {destino}")
                break
            else:
                os.remove(temp_local)

        sftp.close()
        transport.close()
        if encontrou:
            print(f"[INFO] Busca finalizada: arquivo encontrado e copiado.")
            return True, f"Arquivo '{arquivo.filename}' copiado para {destino}."
        else:
            print(f"[INFO] Busca finalizada: nenhum arquivo encontrado com o valor buscado.")
            # Remove a pasta destino se não encontrou nenhum arquivo
            try:
                shutil.rmtree(destino)
                print(f"[INFO] Pasta temporária removida: {destino}")
            except Exception as e:
                print(f"[WARN] Não foi possível remover a pasta temporária: {e}")
            return False, "Nenhum arquivo encontrado com o valor buscado."
    except Exception as e:
        print(f"[ERRO] Falha na busca/cópia: {e}")
        return False, str(e)

def copiar_ultimos_logs_e_outs_remotos(host, usuario, senha, caminho_remoto, caminho_local, progresso_callback=None):
    print(f"[INFO] Iniciando cópia dos últimos 5 arquivos .log e 5 arquivos .out de {caminho_remoto} para {caminho_local}")
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        pasta_central = os.path.join(desktop, "App Coleta Logs")
        if not os.path.exists(pasta_central):
            os.makedirs(pasta_central)

        app_folder = os.path.join(pasta_central, os.path.basename(caminho_local))
        if not os.path.exists(app_folder):
            os.makedirs(app_folder)

        datahora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destino = os.path.join(app_folder, datahora)
        os.makedirs(destino, exist_ok=True)

        transport = paramiko.Transport((host, 22))
        transport.connect(username=usuario, password=senha)
        sftp = paramiko.SFTPClient.from_transport(transport)

        arquivos_log = [f for f in sftp.listdir_attr(caminho_remoto) if f.filename.endswith('.log')]
        arquivos_out = [f for f in sftp.listdir_attr(caminho_remoto) if f.filename.endswith('.out')]
        arquivos_log.sort(key=lambda x: x.st_mtime, reverse=True)
        arquivos_out.sort(key=lambda x: x.st_mtime, reverse=True)
        ultimos_logs = arquivos_log[:5]
        ultimos_outs = arquivos_out[:5]
        arquivos = ultimos_logs + ultimos_outs

        if not arquivos:
            sftp.close()
            transport.close()
            return False, "Nenhum arquivo .log ou .out encontrado no diretório remoto."

        total = len(arquivos)
        for idx, arquivo in enumerate(arquivos):
            remote_path = f"{caminho_remoto}/{arquivo.filename}"
            local_path = os.path.join(destino, arquivo.filename)
            sftp.get(remote_path, local_path)
            print(f"[INFO] Copiado: {remote_path} -> {local_path}")
            if progresso_callback:
                progresso_callback(idx + 1, total)

        sftp.close()
        transport.close()
        print(f"[INFO] Cópia finalizada: {len(arquivos)} arquivos copiados para {destino}")
        return True, f"{len(arquivos)} arquivos (.log/.out) copiados para {destino}"
    except Exception as e:
        print(f"[ERRO] Falha na cópia: {e}")
        return False, str(e)

def buscar_e_copiar_log_ou_out_remoto(valor_busca, host, usuario, senha, caminho_remoto, caminho_local, quantidade=20, progresso_callback=None):
    print(f"[INFO] Iniciando busca por '{valor_busca}' em arquivos .log e .out de {caminho_remoto}")
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        pasta_central = os.path.join(desktop, "App Coleta Logs")
        if not os.path.exists(pasta_central):
            os.makedirs(pasta_central)
        app_folder = os.path.join(pasta_central, os.path.basename(caminho_local))
        if not os.path.exists(app_folder):
            os.makedirs(app_folder)
        datahora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destino = os.path.join(app_folder, datahora)
        os.makedirs(destino, exist_ok=True)

        transport = paramiko.Transport((host, 22))
        transport.connect(username=usuario, password=senha)
        sftp = paramiko.SFTPClient.from_transport(transport)

        arquivos = [f for f in sftp.listdir_attr(caminho_remoto) if f.filename.endswith('.log') or f.filename.endswith('.out')]
        arquivos.sort(key=lambda x: x.st_mtime, reverse=True)
        arquivos = arquivos[:quantidade]

        total = len(arquivos)
        encontrou = False
        for idx, arquivo in enumerate(arquivos):
            remote_path = f"{caminho_remoto}/{arquivo.filename}"
            temp_local = os.path.join(destino, f"temp_{arquivo.filename}")
            sftp.get(remote_path, temp_local)
            print(f"[INFO] Baixado temporariamente: {remote_path}")
            with open(temp_local, encoding="utf-8", errors="ignore") as f:
                if valor_busca in f.read():
                    encontrou = True
            # Chame o progresso_callback aqui, APÓS a leitura
            if progresso_callback:
                progresso_callback(idx + 1, total)
            if encontrou:
                os.rename(temp_local, os.path.join(destino, arquivo.filename))
                print(f"[INFO] Encontrado e copiado: {arquivo.filename} para {destino}")
                break
            else:
                os.remove(temp_local)

        sftp.close()
        transport.close()
        if encontrou:
            print(f"[INFO] Busca finalizada: arquivo encontrado e copiado.")
            return True, f"Arquivo '{arquivo.filename}' copiado para {destino}."
        else:
            print(f"[INFO] Busca finalizada: nenhum arquivo encontrado com o valor buscado.")
            try:
                shutil.rmtree(destino)
                print(f"[INFO] Pasta temporária removida: {destino}")
            except Exception as e:
                print(f"[WARN] Não foi possível remover a pasta temporária: {e}")
            return False, "Nenhum arquivo encontrado com o valor buscado."
    except Exception as e:
        print(f"[ERRO] Falha na busca/cópia: {e}")
        return False, str(e)