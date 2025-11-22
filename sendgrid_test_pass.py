import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_recovery():
    # Use um e-mail real cadastrado no seu banco 'usuario'
    email_teste = "marcus@subiter.com"
    
    print(f"🧪 Testando recuperação de senha para: {email_teste}")
    
    response = requests.post(
        f"{BASE_URL}/password/recover",
        json={"email": email_teste},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        print("✅ Sucesso! Verifique o e-mail.")
        print("🔐 Agora tente fazer login com a nova senha.")
    else:
        print("❌ Falha na recuperação")

if __name__ == "__main__":
    test_recovery()