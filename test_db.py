# Teste direto do service dentro do pacote correto
from app.services.UsuarioService import UsuarioService

def test_usuario_service():
    print("🔍 Testando UsuarioService diretamente...")
    try:
        service = UsuarioService()
        result = service.criar_usuario("test@example.com", "123456", True)
        print("✅ UsuarioService funcionando!")
        print(f"Resultado: {result}")
    except Exception as e:
        print(f"❌ Erro no UsuarioService: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_usuario_service()