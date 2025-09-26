import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def criar_usuario(email, senha, recebe=True):
    r = requests.post(f"{BASE_URL}/usuario", json={
        "email": email,
        "senha": senha,
        "recebe_boletim": recebe
    })
    try:
        data = r.json()
    except Exception:
        print("Falha ao decodificar criação:", r.status_code, r.text)
        return None
    if not data.get("success"):
        print(f"⚠️ Falha ao criar {email}: {data}")
    return data

def buscar_usuario_por_email(email: str):
    r = requests.get(f"{BASE_URL}/usuarios")
    try:
        data = r.json()
    except Exception:
        print("Falha ao decodificar lista:", r.status_code, r.text)
        return None
    if not data.get("success"):
        return None
    for u in data.get("usuarios", []):
        if u["email"] == email:
            return u
    return None

def testar_alteracao_status_boletim():
    print("🧪 Testando alteração de recebe_boletim")

    # Gera emails únicos a cada execução
    suffix = int(time.time())  # segundos atuais
    admin_email = f"admin_task_{suffix}@test.com"
    alvo_email = f"alvo_task_{suffix}@test.com"

    admin_resp = criar_usuario(admin_email, "123456", True)
    if not admin_resp or not admin_resp.get("success"):
        # Se já existisse (não deve pelo timestamp) tenta localizar
        admin_user = buscar_usuario_por_email(admin_email)
        if not admin_user:
            print("Falha ao criar ou localizar admin")
            return
        admin_id = admin_user["id"]
    else:
        admin_id = admin_resp["usuario"]["id"]

    alvo_resp = criar_usuario(alvo_email, "123456", True)
    if not alvo_resp or not alvo_resp.get("success"):
        alvo_user = buscar_usuario_por_email(alvo_email)
        if not alvo_user:
            print("Falha ao criar ou localizar usuário alvo")
            return
        user_id = alvo_user["id"]
    else:
        user_id = alvo_resp["usuario"]["id"]

    print(f"➡️  Alterando recebe_boletim do user {user_id} para False")
    payload = {
        "user_id": user_id,
        "recebe_boletim": False,
        "admin_user_id": admin_id
    }
    resp = requests.put(f"{BASE_URL}/usuario/status-boletim", json=payload)
    print("PUT status:", resp.status_code)
    print("PUT body:", resp.text)

    print("➡️  Consultando status após alteração")
    get_resp = requests.get(f"{BASE_URL}/usuario/{user_id}/status-boletim")
    print("GET status:", get_resp.status_code)
    print("GET body:", get_resp.text)

def testar_fluxo_completo():
    print("🚀 Iniciando teste completo da API de Status do Boletim\n")
    # (mantido) criação simples de admin inicial
    admin_data = {
        "email": "admin@test.com",
        "senha": "123456",
        "recebe_boletim": True
    }
    response = requests.post(f"{BASE_URL}/usuario", json=admin_data)
    print(f"Status: {response.status_code}")
    print(f"Raw response: {response.text}")
    if response.status_code == 500:
        print("❌ Erro 500")
        return
    try:
        admin_result = response.json()
        if admin_result.get("success"):
            print("✅ Admin fluxo completo criado\n")
        else:
            print("❌ Erro ao criar admin\n")
    except:
        print("Erro JSON admin")

if __name__ == "__main__":
    try:
        print("🔍 Testando raiz...")
        r = requests.get(f"{BASE_URL}/")
        print("Raiz:", r.status_code, r.text, "\n")
        testar_alteracao_status_boletim()
    except requests.exceptions.ConnectionError:
        print("Servidor não responde em", BASE_URL)